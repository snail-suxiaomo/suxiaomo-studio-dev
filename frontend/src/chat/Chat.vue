<template>
  <div class="chat">
    <!-- 会话侧栏 -->
    <aside class="session-panel" :class="{ collapsed: sidebarCollapsed }">
      <div class="sp-head">
        <button class="sp-new" @click="newSession">＋ 新建会话</button>
        <button class="sp-toggle" :title="sidebarCollapsed ? '展开' : '收起'" @click="sidebarCollapsed = !sidebarCollapsed">{{ sidebarCollapsed ? '»' : '«' }}</button>
      </div>
      <div class="sp-list">
        <template v-for="g in groupedSessions" :key="g.label">
          <div class="sp-group-label" v-if="g.items.length">{{ g.label }}</div>
          <div v-for="s in g.items" :key="s.id" class="sp-item" :class="{ active: s.id === currentSessionId }" @click="openSession(s)">
            <span class="sp-title" @dblclick="renameSession(s)" :title="s.title">{{ s.title }}</span>
            <button class="sp-more" @click.stop="toggleMenu(s, $event)" title="更多">⋯</button>
            <div v-if="activeMenuId === s.id" class="sp-menu" @click.stop>
              <div class="sp-menu-item" @click="openSessionFolder(s)">
                <span class="sp-menu-icon">📁</span>
                <span>打开文件夹</span>
              </div>
              <div class="sp-menu-item" @click="renameSession(s)">
                <span class="sp-menu-icon">✏️</span>
                <span>重命名</span>
              </div>
              <div class="sp-menu-item danger" @click="deleteSession(s)">
                <span class="sp-menu-icon">🗑</span>
                <span>删除</span>
              </div>
            </div>
          </div>
        </template>
        <div v-if="!sessions.length" class="sp-empty">还没有会话，点「新建会话」开始</div>
      </div>
    </aside>

    <!-- 主区 -->
    <div class="chat-main">
      <div class="chat-topbar">
        <button v-if="sidebarCollapsed" class="sp-toggle" @click="sidebarCollapsed = !sidebarCollapsed" title="展开">«</button>
        <span class="cur-session">{{ currentSession?.title || '未选择会话' }}</span>
      </div>

      <div class="box" ref="boxRef">
      <div v-for="(m, i) in messages" :key="i" class="msg" :class="m.role">
        <div class="who">{{ m.role === 'user' ? '我' : '模型' }}</div>
        <div class="body">
          <div v-if="m.files && m.files.length" class="msg-files">
            <div v-for="(f, fi) in m.files" :key="fi" class="mf-item" :class="f.type">
              <img v-if="f.type === 'image'" :src="f.preview" alt="" />
              <a v-else :href="f.src" :download="f.name" class="mf-name">📄 {{ f.name }}</a>
            </div>
          </div>
          <div v-if="m.reasoning" class="reasoning">
            <details>
              <summary>思考过程</summary>
              <pre>{{ m.reasoning }}</pre>
            </details>
          </div>
          <pre>{{ m.text }}</pre>
        </div>
      </div>
      <div v-if="loading" class="msg bot"><div class="who">模型</div><div class="body">思考中…</div></div>
      <div v-if="lastError" class="err">⚠️ {{ lastError }}</div>
    </div>

    <div class="config-bar">
      <label class="cb-item">
        <span class="cb-label">模型</span>
        <select v-model="selModelId" @change="onSelectModel" :disabled="!modelList.length">
          <option v-for="m in modelList" :key="m.id" :value="m.id">{{ m.name }}</option>
        </select>
      </label>
      <label class="cb-item cb-switch" :class="{ disabled: thinkingLocked }" :title="thinkingLocked ? '该模型只支持专家/思考模式' : ''">
        <input type="checkbox" v-model="thinking" @change="onThinking" :disabled="thinkingLocked" />
        <span class="cb-label">{{ currentProfile?.reasoning_format === 'top_level_effort' ? '推理强度' : '思考模式' }}</span>
      </label>
      <label class="cb-item">
        <span class="cb-label">强度</span>
        <select v-model="effort" @change="onEffort">
          <option value="low">low（低）</option>
          <option value="medium">medium（中）</option>
          <option value="high">high（高）</option>
        </select>
      </label>
      <span v-if="!modelList.length" class="cb-empty">请先到「模型配置」添加一条</span>
    </div>

    <div class="input-area">
      <div class="input-toolbar">
        <button type="button" class="tool-btn" :class="{ disabled: !canUseImage }" :disabled="!canUseImage" @click="pickImages" :title="canUseImage ? '上传图片' : '当前模型未开启图片/视觉能力'">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>
          <span>图片</span>
        </button>
        <button type="button" class="tool-btn" :class="{ disabled: !canUseFiles }" :disabled="!canUseFiles" @click="pickTexts" :title="canUseFiles ? '上传文本文件' : '当前模型未开启文件上传能力'">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>
          <span>文本</span>
        </button>
        <input ref="imgInput" type="file" accept="image/*" multiple style="display:none" @change="onImagesSelected" />
        <input ref="txtInput" type="file" accept=".txt,.md,.py,.js,.ts,.vue,.json,.yaml,.yml,.sql,.log" multiple style="display:none" @change="onTextsSelected" />
      </div>
      <div v-if="selectedImages.length || selectedTexts.length" class="input-files">
        <div v-for="(f, i) in selectedImages" :key="'img'+i" class="if-thumb">
          <img :src="imagePreview(f)" alt="" />
          <button type="button" class="if-del" @click="removeImage(i)">×</button>
        </div>
        <div v-for="(f, i) in selectedTexts" :key="'txt'+i" class="if-doc">
          <span>📄 {{ f.name }}</span>
          <button type="button" class="if-del" @click="removeText(i)">×</button>
        </div>
      </div>
      <div class="input-row">
        <textarea v-model="input" placeholder="输入提示词，回车发送（Shift+回车换行）"
          @keydown.enter.exact.prevent="send" @keydown.shift.enter="(e)=>{}" ref="taRef"></textarea>
        <button class="btn primary" :disabled="loading || !canSend" @click="send">发送</button>
      </div>
    </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, watch, onMounted, onUnmounted } from 'vue'
import { api } from '../common/http.js'
import { askApi } from './ai-api.js'
import { confirm, prompt } from '../common/useConfirm.js'

const messages = ref([])
const input = ref('')
const loading = ref(false)
const lastError = ref('')
const boxRef = ref(null)
const taRef = ref(null)
const imgInput = ref(null)
const txtInput = ref(null)

// —— 模型 / 思考 / 强度 选择（方案 A：默认跟随配置，允许临时覆盖）——
const modelList = ref([])
const selModelId = ref(null)
const thinking = ref(false)
const effort = ref('high')

const LS_ID = 'chat_sel_model_id'
const LS_THINK = 'chat_thinking'
const LS_EFF = 'chat_effort'
const VALID_EFFORTS = ['low', 'medium', 'high']

async function loadModels() {
  try {
    modelList.value = await api('/model_config')
  } catch (e) {
    modelList.value = []
    return
  }
  const savedId = localStorage.getItem(LS_ID)
  let m = savedId ? modelList.value.find(x => String(x.id) === savedId) : null
  if (!m) m = modelList.value.find(x => x.is_active) || modelList.value[0]
  if (!m) return
  selModelId.value = m.id
  // 思考/强度：优先 localStorage 覆盖，否则跟随该配置默认
  const svT = localStorage.getItem(LS_THINK)
  const desiredThink = svT !== null ? svT === '1' : !!m.thinking_enabled
  thinking.value = thinkingLocked.value ? true : desiredThink
  const svE = localStorage.getItem(LS_EFF)
  effort.value = svE && VALID_EFFORTS.includes(svE) ? svE : (VALID_EFFORTS.includes(m.reasoning_effort) ? m.reasoning_effort : 'medium')
}

function onSelectModel() {
  const m = modelList.value.find(x => x.id === selModelId.value)
  if (!m) return
  // 切模型：重置思考/强度为该配置默认，并清掉覆盖
  thinking.value = thinkingLocked.value ? true : !!m.thinking_enabled
  effort.value = VALID_EFFORTS.includes(m.reasoning_effort) ? m.reasoning_effort : 'medium'
  localStorage.removeItem(LS_THINK)
  localStorage.removeItem(LS_EFF)
  localStorage.setItem(LS_ID, String(m.id))
}
function onThinking() {
  localStorage.setItem(LS_THINK, thinking.value ? '1' : '0')
}
function onEffort() {
  localStorage.setItem(LS_EFF, effort.value)
}

const selectedImages = ref([])
const selectedTexts = ref([])

const currentModel = computed(() => modelList.value.find(m => m.id === selModelId.value))
const currentProfile = computed(() => currentModel.value?.profile || null)
const canSend = computed(() => input.value.trim() || selectedImages.value.length || selectedTexts.value.length)
// 图片/文件能力以模型档案为准；旧数据无档案时才回退到配置行本身的开关
const canUseImage = computed(() => {
  if (!currentModel.value) return false
  if (currentProfile.value) return !!currentProfile.value.supports_vision
  return !!currentModel.value.supports_vision
})
const canUseFiles = computed(() => {
  if (!currentModel.value) return false
  if (currentProfile.value) return !!currentProfile.value.supports_files
  return !!currentModel.value.supports_files
})
// 如果模型档案里所有模式都是 thinking=true（没有快速模式），则思考开关锁定为开
const thinkingLocked = computed(() => {
  if (!currentProfile.value) return false
  const modes = currentProfile.value.modes || []
  if (!modes.length) return false
  return modes.every(m => m.thinking)
})

function imagePreview(file) {
  return URL.createObjectURL(file)
}

function pickImages() {
  if (!canUseImage.value) {
    lastError.value = `当前模型「${currentModel.value?.name || '未知'}」未开启图片/视觉能力，无法上传图片。请到「模型配置」中勾选「支持图片/视觉输入」。`
    return
  }
  imgInput.value?.click()
}
function pickTexts() {
  if (!canUseFiles.value) {
    lastError.value = `当前模型「${currentModel.value?.name || '未知'}」未开启文件上传能力，无法上传文本文件。请到「模型配置」中切换为支持文件上传的模型。`
    return
  }
  txtInput.value?.click()
}

function onImagesSelected(e) {
  const files = Array.from(e.target.files || [])
  selectedImages.value.push(...files)
  e.target.value = ''
}
function onTextsSelected(e) {
  const files = Array.from(e.target.files || [])
  selectedTexts.value.push(...files)
  e.target.value = ''
}
function removeImage(i) { selectedImages.value.splice(i, 1) }
function removeText(i) { selectedTexts.value.splice(i, 1) }

async function send() {
  if (!canSend.value || loading.value) return
  if (!currentSessionId.value) {
    await newSession()
  }
  const text = input.value.trim()
  const imgs = selectedImages.value.slice()
  const txs = selectedTexts.value.slice()

  if (imgs.length && !canUseImage.value) {
    lastError.value = `当前模型「${currentModel.value?.name || '未知'}」未开启图片/视觉能力，请先移除图片或切换到支持图片的模型。`
    return
  }
  if (txs.length && !canUseFiles.value) {
    lastError.value = `当前模型「${currentModel.value?.name || '未知'}」未开启文件上传能力，请先移除文本文件或切换到支持文件上传的模型。`
    return
  }

  const userMsg = { role: 'user', text: text || '（仅附件）', files: [] }
  imgs.forEach(f => userMsg.files.push({ type: 'image', name: f.name, preview: URL.createObjectURL(f) }))
  txs.forEach(f => userMsg.files.push({ type: 'text', name: f.name }))
  messages.value.push(userMsg)

  input.value = ''
  selectedImages.value = []
  selectedTexts.value = []
  loading.value = true
  lastError.value = ''
  scrollToBottom()

  try {
    const r = await askApi(text, undefined, imgs, txs, {
      modelConfigId: selModelId.value,
      thinking: thinking.value,
      reasoningEffort: effort.value,
      sessionId: currentSessionId.value,
    })
    if (r.error) lastError.value = r.error
    messages.value.push({ role: 'bot', text: r.reply || '（无返回）', reasoning: r.reasoning })
  } catch (e) {
    lastError.value = e.message
  } finally {
    loading.value = false
    nextTick(scrollToBottom)
  }
}

function scrollToBottom() {
  const el = boxRef.value
  if (el) el.scrollTop = el.scrollHeight
}

watch(messages, () => nextTick(scrollToBottom), { deep: true })

// ---------------- 会话持久化 ----------------
const sessions = ref([])
const currentSessionId = ref(null)
const currentSession = computed(() => sessions.value.find(s => s.id === currentSessionId.value) || null)
const sidebarCollapsed = ref(false)
const activeMenuId = ref(null)

function toggleMenu(s, e) {
  e && e.stopPropagation()
  activeMenuId.value = activeMenuId.value === s.id ? null : s.id
}

function closeMenu() {
  activeMenuId.value = null
}

async function openSessionFolder(s) {
  closeMenu()
  try {
    await api(`/chat/sessions/${s.id}/open-folder`, 'POST')
  } catch (e) {
    lastError.value = '打开文件夹失败：' + (e.message || e)
  }
}

function attachmentUrl(sid, stored) {
  return `/api/chat/attachments/${sid}/${stored}`
}

function toDisplayMsg(m) {
  const files = []
  ;(m.images || []).forEach(meta => {
    const u = attachmentUrl(m.session_id, meta.stored)
    files.push({ type: 'image', name: meta.name, preview: u, src: u })
  })
  ;(m.texts || []).forEach(meta => {
    const u = attachmentUrl(m.session_id, meta.stored)
    files.push({ type: 'text', name: meta.name, preview: '', src: u })
  })
  return { role: m.role, text: m.content, reasoning: m.reasoning, files }
}

async function loadSessions() {
  try {
    sessions.value = await api('/chat/sessions')
  } catch (e) {
    sessions.value = []
  }
}

async function newSession() {
  try {
    const s = await api('/chat/sessions', 'POST', { model_config_id: selModelId.value })
    sessions.value.unshift(s)
    currentSessionId.value = s.id
    messages.value = []
    return s
  } catch (e) {
    lastError.value = '新建会话失败：' + (e.message || e)
    return null
  }
}

async function openSession(s) {
  currentSessionId.value = s.id
  try {
    const msgs = await api(`/chat/sessions/${s.id}/messages`)
    messages.value = msgs.map(toDisplayMsg)
  } catch (e) {
    messages.value = []
    lastError.value = '加载历史失败：' + (e.message || e)
  }
}

async function deleteSession(s) {
  closeMenu()
  const ok = await confirm(`确定删除会话「${s.title}」？该操作不可恢复。`, {
    title: '删除确认',
    confirmText: '删除',
    cancelText: '取消',
    variant: 'danger',
  })
  if (!ok) return
  try {
    await api(`/chat/sessions/${s.id}`, 'DELETE')
    sessions.value = sessions.value.filter(x => x.id !== s.id)
    if (currentSessionId.value === s.id) {
      currentSessionId.value = null
      messages.value = []
    }
  } catch (e) {
    lastError.value = '删除失败：' + (e.message || e)
  }
}

async function renameSession(s) {
  closeMenu()
  const t = await prompt('修改会话标题', {
    title: '重命名会话',
    inputValue: s.title,
    inputPlaceholder: '请输入会话标题',
    confirmText: '保存',
    cancelText: '取消',
  })
  if (t === false || t === null || t === undefined) return
  const title = String(t).trim()
  if (!title || title === s.title) return
  try {
    await api(`/chat/sessions/${s.id}`, 'PATCH', { title })
    s.title = title
  } catch (e) {
    lastError.value = '改名失败：' + (e.message || e)
  }
}

function _dayLabel(dateStr) {
  if (!dateStr) return '更早'
  const d = dateStr.slice(0, 10)
  const now = new Date()
  const pad = n => String(n).padStart(2, '0')
  const today = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`
  const y = new Date(now.getTime() - 86400000)
  const yest = `${y.getFullYear()}-${pad(y.getMonth() + 1)}-${pad(y.getDate())}`
  if (d === today) return '今天'
  if (d === yest) return '昨天'
  return '更早'
}

const groupedSessions = computed(() => {
  const groups = { '今天': [], '昨天': [], '更早': [] }
  for (const s of sessions.value) groups[_dayLabel(s.updated_at)].push(s)
  return ['今天', '昨天', '更早'].map(label => ({ label, items: groups[label] }))
})

function onDocClick(e) {
  if (activeMenuId.value && !e.target.closest('.sp-item')) {
    activeMenuId.value = null
  }
}

onMounted(() => {
  loadModels()
  loadSessions()
  document.addEventListener('click', onDocClick)
})
onUnmounted(() => {
  document.removeEventListener('click', onDocClick)
})
</script>

<style scoped>
.chat {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: row;
  overflow: hidden;
}
.box {
  flex: 1;
  overflow-y: auto;
  border: 1px solid #ececec;
  border-radius: 14px;
  padding: 18px 20px;
  background: #fafbfc;
}

/* 消息行：用户右对齐，模型左对齐 */
.msg {
  display: flex;
  flex-direction: column;
  margin-bottom: 18px;
  max-width: 78%;
}
.msg.user { align-self: flex-end; margin-left: auto; }
.msg.bot, .msg.assistant { align-self: flex-start; margin-right: auto; }

.msg .who {
  font-size: 11px;
  color: #8a90a8;
  margin-bottom: 5px;
  padding: 0 4px;
}
.msg.user .who { text-align: right; }

/* 气泡主体（默认：浅灰底、深字；子类型覆盖，不使用 !important 避免互相覆盖） */
.msg .body {
  padding: 12px 16px;
  border-radius: 16px;
  white-space: pre-wrap;
  line-height: 1.65;
  font-size: 14px;
  background: #f0f1f7;
  color: #2d2f3a;
  box-shadow: 0 2px 10px rgba(20, 22, 40, .05);
  border: 1px solid #e4e6f0;
}

/* 用户消息：浅薰衣草背景 + 深紫字，柔和不突兀 */
.msg.user .body {
  background: #ede9f6;
  color: #4a3f6b;
  border-color: #dcd6f0;
  box-shadow: 0 4px 12px rgba(120, 110, 170, .12);
  border-bottom-right-radius: 4px;
}

/* 模型消息：白底深字（live 'bot' 与历史 'assistant' 共用） */
.msg.bot .body, .msg.assistant .body {
  background: #ffffff;
  color: #2d2f3a;
  border-color: #e8eaf2;
  border-bottom-left-radius: 4px;
}

/* 附件 */
.msg-files { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 8px; }
.mf-item { border-radius: 8px; overflow: hidden; background: rgba(255,255,255,.20); }
.mf-item.image { width: 96px; height: 96px; }
.mf-item.image img { width: 100%; height: 100%; object-fit: cover; border-radius: 8px; }
.mf-item.text { padding: 5px 10px; font-size: 12px; }
.mf-name { color: inherit; opacity: .9; }

/* 错误提示 */
.err {
  color: #c0392b;
  font-size: 13px;
  margin-top: 8px;
  padding: 8px 12px;
  background: #fdecec;
  border-radius: 8px;
  border: 1px solid #f5c6c6;
}

/* 模型 / 思考 / 强度 配置栏 */
.config-bar {
  flex: none;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 18px;
  margin-top: 12px;
  padding: 10px 14px;
  background: #fff;
  border: 1px solid #e4e6f0;
  border-radius: 14px;
  box-shadow: 0 2px 10px rgba(20, 22, 40, .04);
}
.cb-item { display: inline-flex; align-items: center; gap: 8px; font-size: 13px; color: #5b6080; }
.cb-label { font-weight: 600; color: #5b6080; white-space: nowrap; }
.cb-item select {
  padding: 7px 10px; font-size: 13px; color: #2d2f3a;
  background: #f8f9fc; border: 1.5px solid #e3e6ef; border-radius: 9px;
  transition: border-color .15s, background .15s;
  min-width: 200px;
}
.cb-item:first-child select { min-width: 280px; }
.cb-item select:focus { outline: none; border-color: #8b7ec8; background: #fff; }
.cb-item.disabled { opacity: .45; pointer-events: none; }
.cb-switch input { width: 16px; height: 16px; accent-color: #7c6fae; cursor: pointer; }
.cb-switch.disabled { opacity: .45; cursor: not-allowed; }
.cb-switch.disabled input { cursor: not-allowed; }
.cb-empty { font-size: 12.5px; color: #c0392b; }

/* 输入区 */
.input-area {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  margin-top: 12px;
  background: #fff;
  border: 1px solid #e4e6f0;
  border-radius: 14px;
  padding: 12px 14px;
  box-shadow: 0 2px 10px rgba(20, 22, 40, .04);
}
.input-toolbar { display: flex; gap: 8px; margin-bottom: 8px; }
.tool-btn {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 6px 12px; border-radius: 8px; border: 1px solid #e4e6f0;
  background: #f7f8fb; color: #5b6080; font-size: 12.5px; cursor: pointer;
  transition: .15s;
}
.tool-btn:hover { background: #efeef7; border-color: #c8c0e0; color: #6b5b9e; }
.tool-btn.disabled { opacity: .45; cursor: not-allowed; background: #f4f5f8; border-color: #e4e6f0; color: #9aa0b8; }
.tool-btn.disabled:hover { background: #f4f5f8; border-color: #e4e6f0; color: #9aa0b8; }
.input-files { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 8px; }
.if-thumb { position: relative; width: 64px; height: 64px; border-radius: 7px; overflow: hidden; border: 1px solid #ececec; }
.if-thumb img { width: 100%; height: 100%; object-fit: cover; }
.if-doc {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 5px 10px; border-radius: 7px; background: #f3f2f9; color: #5b6080; font-size: 12px;
}
.if-del {
  position: absolute; top: 2px; right: 2px; width: 16px; height: 16px;
  border: 0; border-radius: 50%; background: rgba(20,22,40,.55); color: #fff;
  font-size: 10px; line-height: 1; cursor: pointer; display: flex; align-items: center; justify-content: center;
}
.if-del:hover { background: #e25757; }
.if-doc .if-del { position: static; width: 15px; height: 15px; font-size: 10px; background: transparent; color: #9aa0c0; }
.if-doc .if-del:hover { color: #e25757; background: rgba(226,87,87,.10); }

.input-row { display: flex; gap: 10px; flex: 1; min-height: 0; }
.input-row textarea {
  flex: 1;
  height: 100%;
  resize: none;
  padding: 12px 14px;
  border: 1px solid #d8dbe6;
  border-radius: 10px;
  font-size: 14px;
  font-family: inherit;
  color: #2d2f3a;
  background: #fafbfc;
  transition: border-color .15s, box-shadow .15s, background .15s;
}
.input-row textarea::placeholder { color: #a0a6b8; }
.input-row textarea:focus {
  background: #fff;
  border-color: #8b7ec8;
  outline: none;
  box-shadow: 0 0 0 3px rgba(139, 126, 200, .15);
}

/* 发送按钮：紫渐变 */
.btn {
  padding: 0 24px;
  border: none;
  border-radius: 10px;
  background: linear-gradient(135deg, #7c6fae 0%, #5b4f8c 100%);
  color: #fff;
  cursor: pointer;
  font-size: 14px;
  font-weight: 600;
  transition: transform .1s, box-shadow .15s;
}
.btn:hover { transform: translateY(-1px); box-shadow: 0 8px 18px rgba(92, 79, 140, .30); }
.btn:disabled { opacity: .5; cursor: default; transform: none; box-shadow: none; }

/* 全局 global.css 给 pre 加了白底 !important，这里按消息类型强制覆盖 */
pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: inherit;
}
.msg.user pre {
  background: transparent !important;
  border: none !important;
  color: #4a3f6b !important;
}
.msg.bot pre {
  background: transparent !important;
  border: none !important;
  color: inherit !important;
}

/* 会话侧栏 + 主区 */
.session-panel {
  width: 240px;
  flex: 0 0 240px;
  border-right: 1px solid #ececec;
  display: flex;
  flex-direction: column;
  background: #fafbfc;
  overflow: hidden;
  transition: width .15s ease;
}
.session-panel.collapsed { width: 0; flex-basis: 0; border-right: none; }
.sp-head { display: flex; gap: 8px; padding: 10px; border-bottom: 1px solid #ececec; }
.sp-new {
  flex: 1; padding: 7px 10px; border: none; border-radius: 8px;
  background: #534ab7; color: #fff; font-size: 13px; cursor: pointer;
}
.sp-new:hover { background: #3c3489; }
.sp-toggle {
  width: 30px; border: 1px solid #ddd; border-radius: 8px; background: #fff;
  cursor: pointer; font-size: 14px; color: #555;
}
.sp-list { flex: 1; overflow-y: auto; padding: 6px; }
.sp-group-label { font-size: 11px; color: #9aa0ad; margin: 10px 6px 4px; }
.sp-item {
  position: relative;
  display: flex; align-items: center; gap: 4px; padding: 7px 8px;
  border-radius: 8px; cursor: pointer;
}
.sp-item:hover { background: #eef0f5; }
.sp-item.active { background: #e8eefc; }
.sp-title {
  flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  font-size: 13px; color: #2c2c2a;
}
.sp-more {
  border: none; background: transparent; color: #9aa0ad; cursor: pointer;
  font-size: 16px; line-height: 1; padding: 2px 4px; border-radius: 5px;
  opacity: .7; transition: .15s;
}
.sp-more:hover { color: #5b6080; background: #e8eaf2; opacity: 1; }
.sp-item.active .sp-more:hover { background: #d4dff5; }

.sp-menu {
  position: absolute;
  right: 6px;
  top: 30px;
  z-index: 100;
  min-width: 140px;
  background: #fff;
  border: 1px solid #e4e6f0;
  border-radius: 10px;
  box-shadow: 0 10px 30px rgba(20, 22, 40, .14);
  padding: 6px 0;
  font-size: 13px;
}
.sp-menu-item {
  display: flex; align-items: center; gap: 8px;
  padding: 8px 14px; cursor: pointer; color: #2d2f3a;
  transition: background .12s;
}
.sp-menu-item:hover { background: #f3f4f8; }
.sp-menu-item.danger { color: #c0392b; }
.sp-menu-item.danger:hover { background: #fdecec; }
.sp-menu-icon { font-size: 14px; width: 18px; text-align: center; }
.sp-empty { color: #9aa0ad; font-size: 12px; padding: 16px 10px; text-align: center; }

.chat-main { flex: 1; display: flex; flex-direction: column; min-width: 0; overflow: hidden; }
.chat-topbar {
  display: flex; align-items: center; gap: 8px; padding: 8px 14px;
  border-bottom: 1px solid #ececec; font-size: 13px; color: #555;
}
.cur-session { font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.reasoning {
  font-size: 12px; color: #8b92a8; background: #f3f4f8;
  border-radius: 8px; padding: 6px 10px; margin-bottom: 6px;
}
.reasoning summary { cursor: pointer; user-select: none; }
.reasoning pre { white-space: pre-wrap; word-break: break-word; margin: 4px 0 0; font-size: 12px; }

/* ===== 深色模式精准覆盖 ===== */
:global([data-theme="dark"]) .chat { color: #e8eaf6; }
:global([data-theme="dark"]) .session-panel {
  background: #1c2030 !important; border-color: #2e3454 !important;
}
:global([data-theme="dark"]) .sp-head { border-color: #2e3454; }
:global([data-theme="dark"]) .sp-new { background: #4f7cff; color: #fff; }
:global([data-theme="dark"]) .sp-new:hover { background: #3a66e0; }
:global([data-theme="dark"]) .sp-toggle {
  background: #232740; border-color: #3a4163; color: #a6acc9;
}
:global([data-theme="dark"]) .sp-group-label { color: #767c9e; }
:global([data-theme="dark"]) .sp-item:hover { background: #232740; }
:global([data-theme="dark"]) .sp-item.active { background: #2a2f4d; }
:global([data-theme="dark"]) .sp-title { color: #e8eaf6; }
:global([data-theme="dark"]) .sp-more { color: #767c9e; }
:global([data-theme="dark"]) .sp-more:hover { color: #e8eaf6; background: #3a4163; }
:global([data-theme="dark"]) .sp-menu {
  background: #1c2030; border-color: #2e3454;
  box-shadow: 0 10px 30px rgba(0, 0, 0, .35);
}
:global([data-theme="dark"]) .sp-menu-item { color: #e8eaf6; }
:global([data-theme="dark"]) .sp-menu-item:hover { background: #232740; }
:global([data-theme="dark"]) .sp-menu-item.danger { color: #ff8a8a; }
:global([data-theme="dark"]) .sp-menu-item.danger:hover { background: rgba(226, 91, 91, .12); }
:global([data-theme="dark"]) .sp-empty { color: #767c9e; }

:global([data-theme="dark"]) .chat-main { background: transparent; }
:global([data-theme="dark"]) .chat-topbar {
  border-color: #2e3454; color: #a6acc9;
}
:global([data-theme="dark"]) .cur-session { color: #e8eaf6; }
:global([data-theme="dark"]) .box {
  background: #131523 !important; border-color: #2e3454 !important;
}
:global([data-theme="dark"]) .msg .who { color: #767c9e; }
:global([data-theme="dark"]) .msg .body {
  background: #1c2030 !important; border-color: #2e3454 !important;
  color: #e8eaf6 !important;
}
:global([data-theme="dark"]) .msg.user .body {
  background: #2a2540 !important; border-color: #4a3f7a !important;
  color: #e0d9ff !important;
}
:global([data-theme="dark"]) .msg.user pre { color: #e0d9ff !important; }
:global([data-theme="dark"]) .msg.bot pre,
:global([data-theme="dark"]) .msg.assistant pre { color: #e8eaf6 !important; }
:global([data-theme="dark"]) .reasoning {
  background: #232740; color: #a6acc9;
}
:global([data-theme="dark"]) .mf-item { background: rgba(255, 255, 255, .08); }
:global([data-theme="dark"]) .mf-name { color: inherit; }
:global([data-theme="dark"]) .err {
  background: rgba(226, 91, 91, .12); border-color: rgba(226, 91, 91, .35);
  color: #ff8a8a;
}
:global([data-theme="dark"]) .config-bar {
  background: #1c2030 !important; border-color: #2e3454 !important;
}
:global([data-theme="dark"]) .cb-label { color: #a6acc9; }
:global([data-theme="dark"]) .cb-empty { color: #ff8a8a; }
:global([data-theme="dark"]) .cb-item select { background: #131523 !important; }
:global([data-theme="dark"]) .input-area {
  background: #1c2030 !important; border-color: #2e3454 !important;
}
:global([data-theme="dark"]) .tool-btn {
  background: #232740; border-color: #3a4163; color: #a6acc9;
}
:global([data-theme="dark"]) .tool-btn:hover { background: #2a2f4d; border-color: #4f7cff; color: #4f7cff; }
:global([data-theme="dark"]) .tool-btn.disabled { background: #1c2030; border-color: #2e3454; color: #5a6072; }
:global([data-theme="dark"]) .input-files .if-doc {
  background: #232740; color: #a6acc9;
}
:global([data-theme="dark"]) .if-thumb { border-color: #2e3454; }
:global([data-theme="dark"]) .if-del { background: rgba(255, 255, 255, .15); }
:global([data-theme="dark"]) .if-del:hover { background: #e25b5b; }
:global([data-theme="dark"]) .if-doc .if-del { color: #767c9e; background: transparent; }
:global([data-theme="dark"]) .if-doc .if-del:hover { color: #ff8a8a; background: rgba(226, 91, 91, .12); }
</style>
