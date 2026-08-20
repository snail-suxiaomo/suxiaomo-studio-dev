<template>
  <div class="page">
    <div class="crumb">
      <router-link to="/novel_project">← 小说项目</router-link>
      <span class="sep">/</span>
      <span class="cur">{{ proj.current ? proj.current.name : '未选择项目' }}</span>
      <span class="sep">/</span>
      <span class="cur">00-拆分</span>
    </div>

    <div class="card head">
      <div class="hrow">
        <div class="title">
          <h2>上传并拆分小说</h2>
          <span class="badge">00-拆分</span>
        </div>
        <button class="ghost" @click="goBack">返回项目</button>
      </div>
      <p class="desc">当前项目：{{ proj.current ? proj.current.name : '未选择' }}</p>
    </div>

    <ActiveRuleBar function-key="00-拆分" />

    <div v-if="!proj.current" class="card no-project">
      <p class="warn">未选择项目。请先从「小说项目」中选择一个项目，再进入 00-拆分。</p>
      <button class="primary" @click="goList">去项目列表</button>
    </div>

    <template v-else>
      <!-- ── 拆分参数（可折叠） ── -->
      <div class="card config-card">
        <div class="cfg-header" @click="cfgOpen = !cfgOpen">
          <h3>⚙ 拆分参数</h3>
          <span class="toggle">{{ cfgOpen ? '收起 ▲' : '展开 ▼' }}</span>
        </div>
        <div v-show="cfgOpen" class="cfg-body">
          <div class="cfg-row">
            <label>迷你章阈值（字）</label>
            <input v-model.number="cfg.min_chars" type="number" min="50" max="5000" />
            <span class="hint">正文少于此字数标为「迷你章」</span>
          </div>
          <div class="cfg-row">
            <label>巨型章阈值（字）</label>
            <input v-model.number="cfg.max_chars" type="number" min="1000" max="99999" />
            <span class="hint">正文超过此字数标为「巨型章」</span>
          </div>
          <button class="primary sm" @click="saveConfig">保存参数</button>
          <span v-if="cfgMsg" class="cfg-msg" :class="{ ok: cfgOk }">{{ cfgMsg }}</span>
        </div>
      </div>

      <!-- ── 步骤1：导入小说 ── -->
      <div class="card">
        <h3>步骤 1：导入小说</h3>
        <p class="tip">选择本地小说文件（支持 .txt / .epub），点「导入并诊断」分析章节质量。</p>

        <div class="row">
          <label class="upload-btn" :class="{ active: file }">
            <input type="file" accept=".txt,.epub" @change="onFile" />
            <span v-if="file">{{ file.name }}</span>
            <span v-else>📄 选择小说文件</span>
          </label>
          <button :disabled="!file || importing" class="primary" @click="importDiag">
            {{ importing ? '诊断中…' : '导入并诊断' }}
          </button>
        </div>
        <p v-if="diagMsg" class="msg" :class="{ err: diagErr }">{{ diagMsg }}</p>
      </div>

      <!-- ── 诊断面板 ── -->
      <div v-if="diag" class="card">
        <h3>诊断结果</h3>

        <!-- 诊断方式与 AI 状态指示 -->
        <div class="diag-status-bar">
          <span class="diag-method" title="本次诊断由本地 Python 规则执行，未调用 AI 模型，不消耗积分">
            🟢 诊断方式：Python 规则分析（不消耗 AI）
          </span>
          <span class="sep">|</span>
          <span class="diag-model" :class="{ active: aiOpen || aiConfirmed }"
                title="AI 辅助分析配置：如需使用请展开下方 AI 面板">
            🤖 AI 辅助：{{ aiConfirmed ? ('已确认 - ' + modelName) : (aiOpen ? ('分析中 - ' + modelName) : '点击展开下方') }}
          </span>
        </div>

        <!-- 摘要 -->
        <div class="diag-summary">
          <span class="tag">格式：{{ diag.format || '未识别' }}</span>
          <span class="tag">总章节：{{ diag.total_chapters }}</span>
          <span class="tag">正文：{{ diag.body_count }}</span>
          <span class="tag" v-if="diag.extra_count">番外：{{ diag.extra_count }}</span>
          <span v-if="diag.char_stats.min" class="tag">字数：{{ diag.char_stats.min }}~{{ diag.char_stats.max }}（均 {{ diag.char_stats.avg }}）</span>
          <span class="tag" v-if="diag.preface_present">含前言</span>
        </div>

        <!-- 硬异常（阻断） -->
        <div v-if="visibleHard.length" class="issue-block hard">
          <h4>🔴 必须处理（{{ visibleHard.length }} 项）</h4>
          <ul>
            <li v-for="(h, i) in visibleHard" :key="i">
              <strong>{{ h.type }}</strong>：{{ h.detail }}
              <span v-if="h.chapter">（第 {{ h.chapter }} 章）</span>
              <button class="dismiss-btn" @click="dismissIssue(h._id)" title="忽略此问题">✕</button>
            </li>
          </ul>
        </div>
        <div v-else-if="diag.issues.hard.length" class="issue-block ok">
          <h4>🟢 硬性问题已全部忽略</h4>
          <button class="ghost sm" @click="undoAllHard">撤销全部忽略</button>
        </div>
        <div v-else class="issue-block ok">
          <h4>🟢 无硬性问题</h4>
        </div>

        <!-- 软警告（仅提示） -->
        <div v-if="visibleSoft.length" class="issue-block soft">
          <h4>🟡 注意事项（{{ visibleSoft.length }} 项）</h4>
          <ul>
            <li v-for="(s, i) in visibleSoft" :key="i">
              <strong>{{ issueLabel(s.type) }}</strong>：{{ s.detail }}
              <span v-if="s.chapter">（第 {{ s.chapter }} 章）</span>
              <button class="dismiss-btn" @click="dismissIssue(s._id)" title="忽略此条">✕</button>
            </li>
          </ul>
        </div>

        <!-- 逐章明细 -->
        <details class="ch-detail">
          <summary>📋 逐章明细（{{ diag.detailed.length }} 章）</summary>
          <table class="chtbl">
            <thead><tr><th>序号</th><th>标题</th><th>类型</th><th>字数</th><th>警告</th></tr></thead>
            <tbody>
              <tr v-for="c in diag.detailed" :key="c.idx"
                  :class="{ extra: c.type === 'extra', warn: c.warnings.length }">
                <td>{{ c.idx }}</td>
                <td>{{ c.title }}</td>
                <td><span :class="'type-' + c.type">{{ c.type === 'extra' ? '番外' : '正文' }}</span></td>
                <td>{{ c.chars }}字</td>
                <td class="warns">
                  <span v-for="(w, wi) in c.warnings" :key="wi" class="warn-tag">{{ w }}</span>
                  <span v-if="!c.warnings.length">—</span>
                </td>
              </tr>
            </tbody>
          </table>
        </details>

        <!-- 首尾采样预览 -->
        <details class="preview-detail">
          <summary>📄 首尾采样预览</summary>
          <div v-if="diag.preview.preface_500" class="preview-box">
            <h5>📖 前言（前 500 字）</h5>
            <p class="preview-text">{{ diag.preview.preface_500 }}</p>
          </div>
          <div class="preview-box">
            <h5>📖 首章「{{ diag.preview.first_title }}」（前 500 字）</h5>
            <p class="preview-text">{{ diag.preview.first_500 }}</p>
          </div>
          <div v-if="diag.preview.last_title" class="preview-box">
            <h5>📖 末章「{{ diag.preview.last_title }}」（后 500 字）</h5>
            <p class="preview-text">{{ diag.preview.last_500 }}</p>
          </div>
        </details>

        <!-- 素材文件 -->
        <p class="asset-hint" v-if="diag.source_file">
          📦 素材已保存：<code>{{ diag.source_file }}</code>
        </p>

        <!-- ── AI 辅助分析（可折叠聊天框） ── -->
        <div class="card ai-card">
          <div class="ai-header" @click="aiOpen = !aiOpen">
            <h3>🤖 AI 辅助分析</h3>
            <span class="toggle">{{ aiOpen ? '收起 ▲' : '展开 ▼' }}</span>
          </div>
          <div v-show="aiOpen" class="ai-body">
            <div class="ai-info">
              <select v-model="aiModelId" class="ai-model-select" title="临时切换模型（不保存到指令配置）">
                <option v-for="m in modelList" :key="m.id" :value="m.id">
                  {{ m.name || m.model_name }}
                </option>
              </select>
              <label class="ai-thinking-toggle" title="临时切换思考模式">
                <input type="checkbox" v-model="aiThinkingMode" />
                <span>{{ aiThinkingMode ? '🧠 思考模式' : '💬 非思考模式' }}</span>
              </label>
            </div>

            <!-- 聊天记录 -->
            <div class="ai-messages" ref="msgBox">
              <div v-for="(m, i) in aiMessages" :key="i" :class="'msg-' + m.role">
                <div class="msg-avatar">{{ m.role === 'user' ? '🧑' : '🤖' }}</div>
                <div class="msg-content" style="white-space:pre-wrap">{{ m.content }}</div>
              </div>
              <div v-if="aiThinking" class="msg-ai thinking">
                <div class="msg-avatar">🤖</div>
                <div class="msg-content">思考中…</div>
              </div>
            </div>

            <!-- 输入区 -->
            <div class="ai-input-row">
              <input v-model="aiInput" @keyup.enter="sendAiMessage"
                     placeholder="询问 AI 关于章节结构的问题…" :disabled="aiThinking" />
              <button :disabled="!aiInput.trim() || aiThinking" class="primary sm"
                      @click="sendAiMessage">发送</button>
            </div>

            <!-- 确认完成 -->
            <div class="ai-confirm-row">
              <button v-if="!aiConfirmed" class="primary" @click="confirmAi" :disabled="aiThinking">
                ✅ 确认分析完成
              </button>
              <span v-else class="ai-confirmed-badge">✅ 已确认分析完成，可执行拆分</span>
            </div>
          </div>
        </div>

        <!-- 操作按钮 -->
        <div class="diag-actions">
          <button class="primary" :disabled="splitDisabled || splitting"
                  @click="doSplit" :title="splitDisabledTip">
            {{ splitting ? '拆分中…' : splitBtnLabel }}
          </button>
          <span v-if="splitBtnHint" class="msg hint">{{ splitBtnHint }}</span>
          <span v-if="splitMsg" class="msg" :class="{ err: splitErr }">{{ splitMsg }}</span>
        </div>
      </div>

      <!-- ── 拆分结果 ── -->
      <div v-if="result" class="card">
        <h3>✅ 拆分完成</h3>
        <div class="result-info">
          <p>格式：<strong>{{ result.format }}</strong>，共 <strong>{{ result.chapters }}</strong> 章</p>
          <p class="path">输出目录：{{ result.out_dir }}</p>
        </div>
      </div>

      <!-- ── 已拆分章节 ── -->
      <div class="card" v-if="chapters.length">
        <h3>📁 已拆分章节（00-拆分/）</h3>
        <ul class="chlist">
          <li v-for="c in chapters" :key="c">{{ c }}</li>
        </ul>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { api, apiUpload } from '../common/http.js'
import ActiveRuleBar from '../common/ActiveRuleBar.vue'
import { useProjectStore } from '../common/project-store.js'

const pid = ref(null)
const file = ref(null)
const diag = ref(null)
const result = ref(null)
const chapters = ref([])

const importing = ref(false)
const splitting = ref(false)

const diagMsg = ref('')
const diagErr = ref(false)
const splitMsg = ref('')
const splitErr = ref(false)

const cfgOpen = ref(false)
const cfg = ref({ min_chars: 300, max_chars: 8000 })
const cfgMsg = ref('')
const cfgOk = ref(false)

const proj = useProjectStore()
const router = useRouter()

// ── AI 聊天框 ──
const aiOpen = ref(false)
const aiInput = ref('')
const aiMessages = ref([])
const aiThinking = ref(false)
const aiConfirmed = ref(false)
const modelName = ref('')
const modelThinking = ref(false)
const msgBox = ref(null)
const modelList = ref([])
const aiModelId = ref(null)
const aiThinkingMode = ref(true)

// ── 诊断问题忽略 ──
const dismissedIssues = ref(new Set())
// 忽略集是响应式的，用字符串 ID 存："hard-0" / "soft-1" / "ch-warn-章节idx-警告idx"

function goBack() {
  router.push(proj.current ? '/novel_project/' + proj.current.id : '/novel_project')
}
function goList() {
  router.push('/novel_project')
}

const splitDisabledTip = computed(() => {
  if (!diag.value) return '请先导入并诊断'
  const remainHard = diag.value.issues.hard.filter((_, i) => !dismissedIssues.value.has('hard-' + i))
  if (remainHard.length && !aiConfirmed.value) return '有硬性问题未处理，忽略或使用 AI 分析'
  return ''
})

const splitDisabled = computed(() => {
  if (!diag.value) return true
  const remainHard = diag.value.issues.hard.filter((_, i) => !dismissedIssues.value.has('hard-' + i))
  return remainHard.length > 0 && !aiConfirmed.value
})

const splitBtnLabel = computed(() => {
  if (aiConfirmed.value) return '✅ 已 AI 分析，确认拆分'
  const allHardDismissed = diag.value.issues.hard.every((_, i) => dismissedIssues.value.has('hard-' + i))
  if (allHardDismissed && diag.value.issues.hard.length) return '✅ 已忽略全部硬性问题，执行拆分'
  if (!diag.value.issues.hard.length) return '✅ 确认并拆分'
  return '✅ 确认并拆分'
})

const splitBtnHint = computed(() => {
  if (aiConfirmed.value && diag.value.issues.hard.length) {
    const remainHard = diag.value.issues.hard.filter((_, i) => !dismissedIssues.value.has('hard-' + i))
    if (remainHard.length) return '⚠️ AI 已确认，硬性问题将记录在报告但不阻断'
  }
  const allHardDismissed = diag.value.issues.hard.every((_, i) => dismissedIssues.value.has('hard-' + i))
  if (allHardDismissed && diag.value.issues.hard.length) return '⚠️ 已忽略硬性问题，异常将不阻断拆分'
  return ''
})

// ── 可见异常（排除已忽略的） ──
const visibleHard = computed(() => {
  if (!diag.value) return []
  return diag.value.issues.hard
    .map((h, i) => ({ ...h, _id: 'hard-' + i }))
    .filter(h => !dismissedIssues.value.has(h._id))
})
const visibleSoft = computed(() => {
  if (!diag.value) return []
  return diag.value.issues.soft
    .map((s, i) => ({ ...s, _id: 'soft-' + i }))
    .filter(s => !dismissedIssues.value.has(s._id))
})

// ── 诊断 ──

function onFile(e) {
  file.value = e.target.files[0] || null
  // 换文件时清旧诊断
  diag.value = null
  result.value = null
  diagMsg.value = ''
  splitMsg.value = ''
  dismissedIssues.value = new Set()
  aiConfirmed.value = false
  aiMessages.value = []
}

async function importDiag() {
  if (!pid.value || !file.value) return
  importing.value = true
  diagMsg.value = ''
  diagErr.value = false
  diag.value = null
  result.value = null
  dismissedIssues.value = new Set()
  aiConfirmed.value = false
  aiMessages.value = []
  try {
    const fd = new FormData()
    fd.append('project_id', String(pid.value))
    fd.append('file', file.value)
    diag.value = await apiUpload('/novel_split/import', fd)
  } catch (e) {
    diagErr.value = true
    diagMsg.value = e.message
  } finally {
    importing.value = false
  }
}

// ── AI 聊天 ──

async function sendAiMessage() {
  const msg = aiInput.value.trim()
  if (!msg) return
  aiMessages.value.push({ role: 'user', content: msg })
  aiInput.value = ''
  aiThinking.value = true
  try {
    const body = {
      diagnosis: diag.value,
      user_message: msg,
    }
    if (aiModelId.value) body.model_config_id = aiModelId.value
    if (aiThinkingMode.value !== null) body.thinking_enabled = aiThinkingMode.value ? 1 : 0
    const r = await api('/novel_split/ai_analyze?project_id=' + pid.value, 'POST', body)
    aiMessages.value.push({ role: 'ai', content: r.reply })
  } catch (e) {
    aiMessages.value.push({ role: 'ai', content: '❌ ' + e.message })
  } finally {
    aiThinking.value = false
    scrollToBottom()
  }
}

function confirmAi() {
  aiConfirmed.value = true
}

function dismissIssue(id) {
  const s = new Set(dismissedIssues.value)
  s.add(id)
  dismissedIssues.value = s
}

function undoDismiss(id) {
  const s = new Set(dismissedIssues.value)
  s.delete(id)
  dismissedIssues.value = s
}

function isDismissed(id) {
  return dismissedIssues.value.has(id)
}

function undoAllHard() {
  const s = new Set(dismissedIssues.value)
  for (const k of s) {
    if (k.startsWith('hard-')) s.delete(k)
  }
  dismissedIssues.value = s
}

function scrollToBottom() {
  // 确保最后一条消息可见
  setTimeout(() => {
    if (msgBox.value) msgBox.value.scrollTop = msgBox.value.scrollHeight
  }, 50)
}

async function loadModelInfo() {
  try {
    modelList.value = await api('/model_config')
    // 从 AI调用规则 读取 00-拆分 review 规则：自建规则优先，无则读参考规则
    let rule = null
    const dbRules = await api('/ai-rules?menu=' + encodeURIComponent('小说改写') + '&function_key=' + encodeURIComponent('00-拆分') + '&role=review&enabled=1')
    if (dbRules && dbRules.length) {
      rule = dbRules[0]
    } else {
      const refs = await api('/ai-rules/references')
      rule = (refs || []).find(r => r.menu === '小说改写' && r.function_key === '00-拆分' && r.role === 'review')
    }
    if (rule && rule.model_config_id) {
      aiModelId.value = rule.model_config_id
      const found = modelList.value.find(m => m.id === rule.model_config_id)
      if (found) modelName.value = found.model_name || found.name || '默认'
    } else if (modelList.value.length) {
      aiModelId.value = modelList.value[0].id
      modelName.value = modelList.value[0].model_name || modelList.value[0].name || '默认'
    }
    const t = (rule && rule.thinking) ? rule.thinking : 'follow'
    aiThinkingMode.value = !['disabled', 'standard', 'fast'].includes(t)
  } catch {
    modelName.value = '默认'
  }
}

// ── 拆分 ──

async function doSplit() {
  if (!pid.value || !diag.value) return
  const remainHard = diag.value.issues.hard.filter((_, i) => !dismissedIssues.value.has('hard-' + i))
  if (remainHard.length && !aiConfirmed.value) return
  splitting.value = true
  splitMsg.value = ''
  splitErr.value = false
  try {
    const fd = new FormData()
    fd.append('project_id', String(pid.value))
    fd.append('source_file', diag.value.source_file)
    fd.append('ai_confirmed', aiConfirmed.value ? '1' : '0')
    fd.append('remaining_hard', JSON.stringify(remainHard))
    const remainSoft = diag.value.issues.soft.filter((_, i) => !dismissedIssues.value.has('soft-' + i))
    fd.append('remaining_soft', JSON.stringify(remainSoft))
    result.value = await apiUpload('/novel_split/split', fd)
    splitMsg.value = '拆分成功 ✅'
    await listChapters()
  } catch (e) {
    splitErr.value = true
    splitMsg.value = e.message
  } finally {
    splitting.value = false
  }
}

// ── 配置 ──

async function loadConfig() {
  if (!pid.value) return
  try {
    const c = await api('/novel_split/config?project_id=' + pid.value)
    cfg.value = c
  } catch {
    // 用默认值
  }
}

async function saveConfig() {
  cfgMsg.value = ''
  try {
    await api('/novel_split/config?project_id=' + pid.value, 'PUT', {
      min_chars: cfg.value.min_chars,
      max_chars: cfg.value.max_chars,
    })
    cfgOk.value = true
    cfgMsg.value = '参数已保存 ✅'
  } catch (e) {
    cfgOk.value = false
    cfgMsg.value = '保存失败：' + e.message
  }
}

// ── 已拆分章节 ──

async function listChapters() {
  if (!pid.value) return
  try {
    chapters.value = await api('/novel_split/files?project_id=' + pid.value)
  } catch {
    chapters.value = []
  }
}

// ── 工具 ──

function issueLabel(type) {
  const map = {
    giant_chapter: '巨型章',
    chapter_gap: '章节缺失',
    format_not_supported: '格式不支持',
  }
  return map[type] || type
}

// ── 初始化 ──

onMounted(async () => {
  if (!proj.current) {
    pid.value = null
    return
  }
  pid.value = proj.current.id
  await loadConfig()
  await loadModelInfo()
  await listChapters()
})
</script>

<style scoped>
.page { max-width: 960px; }

/* 面包屑 */
.crumb { font-size: 13px; color: #888; margin-bottom: 14px; }
.crumb a { color: #4f7cff; text-decoration: none; }
.crumb a:hover { text-decoration: underline; }
.crumb .sep { margin: 0 8px; }
.crumb .cur { color: #333; }

/* 顶部卡片 */
.head h2 { margin: 0 0 8px; font-size: 20px; }
.title { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.hrow { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; }
.desc { color: #555; margin: 12px 0 0; line-height: 1.6; }
.badge { padding: 2px 10px; border-radius: 10px; font-size: 12px; background: #e6f0ff; color: #4f7cff; }

/* 卡片通用 */
.card { background: #fff; border: 1px solid #ececec; border-radius: 12px; padding: 18px 20px; margin-bottom: 16px; }
.card h3 { margin: 0 0 10px; font-size: 16px; color: #2b2f44; }
.tip { color: #666; font-size: 14px; line-height: 1.7; margin: 0 0 14px; }

/* 操作区 */
.row { display: flex; gap: 12px; flex-wrap: wrap; align-items: center; margin-top: 6px; }

.upload-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border: 1px dashed #c2c8d6;
  border-radius: 8px;
  background: #f8f9fb;
  color: #5a6072;
  font-size: 14px;
  cursor: pointer;
  transition: all .2s;
}
.upload-btn:hover {
  border-color: #4f7cff;
  color: #4f7cff;
  background: #f0f4ff;
}
.upload-btn.active {
  border-style: solid;
  border-color: #4f7cff;
  color: #2b2f44;
  background: #eef3ff;
}
.upload-btn input[type=file] { display: none; }

button {
  padding: 8px 18px;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  transition: all .2s;
}
button.primary {
  background: #4f7cff;
  color: #fff;
}
button.primary:hover:not(:disabled) {
  background: #3b6af5;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(79, 124, 255, .2);
}
button:disabled {
  background: #b9c6e8 !important;
  color: #fff !important;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}
button.sm { padding: 6px 14px; font-size: 13px; }
button.ghost { background: #eef1f8; color: #445; }
button.ghost:hover:not(:disabled) { background: #e4e9f4; }

.msg { margin-top: 8px; font-size: 13px; }
.msg.err { color: #e25b5b; }

/* ── 参数折叠卡 ── */
.config-card { padding-bottom: 10px; }
.cfg-header { display: flex; justify-content: space-between; align-items: center; cursor: pointer; user-select: none; }
.cfg-header h3 { margin: 0; font-size: 15px; }
.toggle { font-size: 12px; color: #888; }
.cfg-body { margin-top: 14px; border-top: 1px solid #eee; padding-top: 14px; }
.cfg-row { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; flex-wrap: wrap; }
.cfg-row label { min-width: 120px; font-size: 13px; color: #555; }
.cfg-row input { width: 90px; padding: 4px 8px; border: 1px solid #d0d5e0; border-radius: 6px; font-size: 13px; }
.cfg-row .hint { font-size: 12px; color: #999; }
.cfg-msg { margin-left: 10px; font-size: 12px; }
.cfg-msg.ok { color: #2a9d8f; }

/* ── 诊断面板 ── */
/* 诊断方式状态条 */
.diag-status-bar { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; padding: 6px 12px; background: #f5f7fa; border-radius: 8px; font-size: 13px; }
.diag-status-bar .sep { color: #d0d5e0; }
.diag-method { color: #2a9d8f; }
.diag-model { color: #888; }

.diag-summary { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 14px; }
.tag { padding: 4px 10px; border-radius: 6px; background: #f0f4ff; color: #4f7cff; font-size: 13px; }

.issue-block { margin: 10px 0; padding: 12px; border-radius: 8px; }
.issue-block h4 { margin: 0 0 6px; font-size: 14px; }
.issue-block ul { margin: 0; padding-left: 18px; font-size: 13px; line-height: 1.8; }
.issue-block.hard { background: #fff3f0; border: 1px solid #ffcdc0; color: #b0302a; }
.issue-block.soft { background: #fffbe6; border: 1px solid #ffe58f; color: #8c6b00; }
.issue-block.ok { background: #f0faf0; border: 1px solid #b7eb8f; color: #2d6e2d; }

/* 逐章明细 */
.ch-detail, .preview-detail { margin-top: 12px; }
.ch-detail summary, .preview-detail summary { cursor: pointer; font-size: 14px; color: #4f7cff; padding: 4px 0; }
.chtbl { width: 100%; border-collapse: collapse; margin-top: 8px; font-size: 13px; }
.chtbl th, .chtbl td { padding: 6px 8px; border-bottom: 1px solid #ececec; text-align: left; }
.chtbl th { background: #f8f9fb; color: #555; font-weight: 500; }
.chtbl tr.extra { background: #f9f6ff; }
.chtbl tr.warn td { border-bottom-color: #ffe58f; }
.type-body { color: #2b2f44; }
.type-extra { color: #7b61ff; font-weight: 500; }
.warns { max-width: 240px; }
.warn-tag { display: inline-block; padding: 1px 6px; margin: 1px 2px; border-radius: 4px; background: #fff3e0; color: #b05a00; font-size: 11px; white-space: nowrap; }

/* 预览 */
.preview-box { margin: 8px 0; }
.preview-box h5 { margin: 4px 0; font-size: 13px; color: #555; }
.preview-text { background: #f8f9fb; border: 1px solid #ececec; border-radius: 6px; padding: 10px; font-size: 13px; color: #444; line-height: 1.6; max-height: 200px; overflow-y: auto; white-space: pre-wrap; word-break: break-all;}

.asset-hint { margin-top: 10px; font-size: 13px; color: #666; }
.asset-hint code { background: #f0f0f0; padding: 1px 6px; border-radius: 4px; }

.diag-actions { margin-top: 14px; padding-top: 14px; border-top: 1px solid #eee; display: flex; gap: 10px; align-items: center; }

/* 结果 */
.result-info p { margin: 4px 0; }
.path { color: #888; font-size: 13px; }

/* 章节列表 */
.chlist { columns: 3; font-size: 13px; color: #555; margin: 0; padding-left: 18px; }

/* 无项目 */
.no-project { text-align: center; padding: 36px 20px; }
.warn { color: #9a6b00; margin-bottom: 16px; }

/* ── AI 聊天框 ── */
.ai-card { margin-top: 12px; padding-bottom: 10px; border: 1px solid #e0e4f0; }
.ai-header { display: flex; justify-content: space-between; align-items: center; cursor: pointer; user-select: none; }
.ai-header h3 { margin: 0; font-size: 15px; }
.ai-body { margin-top: 12px; border-top: 1px solid #eee; padding-top: 12px; }
.ai-info { display: flex; gap: 8px; margin-bottom: 10px; flex-wrap: wrap; }

.ai-messages { max-height: 320px; overflow-y: auto; margin-bottom: 10px; border: 1px solid #ececec; border-radius: 8px; padding: 10px; background: #fafbfc; }
.ai-messages .msg-user,
.ai-messages .msg-ai { display: flex; gap: 8px; margin-bottom: 10px; }
.ai-messages .msg-ai.thinking .msg-content { color: #888; font-style: italic; }
.msg-avatar { flex-shrink: 0; width: 28px; height: 28px; display: flex; align-items: center; justify-content: center; font-size: 16px; }
.msg-content { background: #fff; border: 1px solid #ececec; border-radius: 8px; padding: 8px 12px; font-size: 13px; line-height: 1.6; max-width: 85%; color: #333; }
.msg-user .msg-content { background: #eef3ff; border-color: #d0ddf5; }

.ai-input-row { display: flex; gap: 8px; margin-bottom: 10px; }
.ai-input-row input { flex: 1; padding: 8px 12px; border: 1px solid #d0d5e0; border-radius: 8px; font-size: 13px; outline: none; }
.ai-input-row input:focus { border-color: #4f7cff; }
.ai-input-row input:disabled { background: #f5f5f5; }

.ai-confirm-row { border-top: 1px solid #eee; padding-top: 10px; display: flex; align-items: center; gap: 10px; }
.ai-confirmed-badge { color: #2a9d8f; font-size: 14px; font-weight: 500; }

.diag-model.active { color: #4f7cff; font-weight: 500; }
.bypass-hint { color: #9a6b00; font-size: 12px; }

/* ── 忽略按钮 ── */
.dismiss-btn { float: right; background: none; border: none; color: #cc6; cursor: pointer; padding: 0 4px; font-size: 13px; line-height: 1; }
.dismiss-btn:hover { color: #e25b5b; }
.hint { color: #8c6b00; font-size: 12px; }

/* ── AI 模型下拉 ── */
.ai-model-select { padding: 4px 8px; border: 1px solid #d0d5e0; border-radius: 6px; font-size: 13px; background: #fff; cursor: pointer; }
.ai-thinking-toggle { display: inline-flex; align-items: center; gap: 4px; font-size: 13px; color: #555; cursor: pointer; }
.ai-thinking-toggle input { margin: 0; }
</style>
