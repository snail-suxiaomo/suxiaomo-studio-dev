<template>
  <div class="arm-page">
    <!-- 顶部固定区：标题 + 操作 + 双 Tab -->
    <div class="arm-top">
      <header class="arm-head">
        <div class="arm-title">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M4 4h16v6H4zM4 14h16v6H4z" />
            <path d="M8 7h.01M8 17h.01" />
          </svg>
          <div>
            <h1>AI 调用规则</h1>
            <p class="arm-sub">两类规则分开管理：<b>参考规则</b>是系统自带、仅查看不可改；<b>我的规则</b>是真正在用的，可改、可删、可单条重置。</p>
          </div>
        </div>
        <div class="arm-actions">
          <button v-if="activeTab === 'mine'" class="btn primary" @click="newRule">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="M12 5v14M5 12h14" /></svg>
            新建规则
          </button>
        </div>
      </header>
      <div class="arm-tabbar">
          <button :class="['arm-tab', { active: activeTab === 'ref' }]" @click="activeTab = 'ref'">
          参考规则 <span class="tab-count">{{ references.length }}</span>
        </button>
        <button :class="['arm-tab', { active: activeTab === 'mine' }]" @click="activeTab = 'mine'">
          我的规则 <span class="tab-count">{{ myRules.length }}</span>
        </button>
      </div>
    </div>

    <!-- 主体：左列表 + 右详情/编辑 -->
    <div class="arm-body">
      <!-- 左：列表 -->
      <aside class="arm-list">
        <!-- 参考 Tab -->
        <template v-if="activeTab === 'ref'">
          <div class="arm-list-hint">系统自带、仅查看不可改。点「复制使用」即可变成你的规则。</div>
          <div v-if="!references.length" class="arm-empty-list">暂无参考规则（workspace/AI调用规则/ 为空）。</div>
          <div v-for="grp in refTree" :key="grp.name" class="tree-scope">
            <div class="tree-scope-name">{{ grp.name }}</div>
            <div v-for="fn in grp.fns" :key="fn.name" class="tree-fn">
              <div class="tree-fn-name">{{ fn.name || '（未归类）' }}</div>
              <div
                v-for="r in fn.rules"
                :key="r.ref_path"
                class="tree-rule"
                :class="{ active: selRef === r.ref_path }"
                @click="selectRef(r.ref_path)"
              >
                <span class="tree-badge role">{{ roleLabel(r.role) }}</span>
                <span class="tree-rule-name">{{ r.name }}</span>
                <button class="mini-btn" :disabled="saving" @click.stop="copyRef(r.ref_path)">
                  复制使用
                </button>
              </div>
            </div>
          </div>
        </template>

        <!-- 我的 Tab -->
        <template v-else>
          <div class="arm-list-hint">你正在使用的规则：从参考复制或新建而来，可改、可删、可单条重置。</div>
          <div v-if="!myRules.length" class="arm-empty-list">还没有规则。点右上「新建规则」，或从「默认参考规则」复制一条。</div>
          <div v-for="grp in mineTree" :key="grp.name" class="tree-scope">
            <div class="tree-scope-name">{{ grp.name }}</div>
            <div v-for="fn in grp.fns" :key="fn.name" class="tree-fn">
              <div class="tree-fn-name">{{ fn.name || '（未归类）' }}</div>
              <div
                v-for="r in fn.rules"
                :id="'rule-' + r.id"
                :key="r.id"
                class="tree-rule"
                :class="{ active: selMineId === r.id, off: !r.enabled }"
                @click="selectMine(r.id)"
              >
                <span class="tree-badge role">{{ roleLabel(r.role) }}</span>
                <span class="tree-rule-name">{{ r.name }}</span>
                <span v-if="r.ref_path" class="tree-badge src" :title="'来自参考规则：' + r.ref_path + '（可单条重置，删除后仍可重新复制）'">来自默认参考</span>
                <span v-else class="tree-badge manual" title="手动新建，无来源文件，删除后无法恢复">手动新建</span>
              </div>
            </div>
          </div>
        </template>
      </aside>

      <!-- 右：详情/编辑 -->
      <section class="arm-detail">
        <!-- 参考详情（只读） -->
        <template v-if="activeTab === 'ref'">
          <div v-if="selRefObj" class="arm-ref-view">
            <div class="arm-edit-head">
              <span class="arm-edit-tag ref">参考规则（只读）</span>
            </div>
            <div class="arm-ref-grid">
              <div class="arm-ro"><label>名称</label><span>{{ selRefObj.name }}</span></div>
              <div class="arm-ro"><label>菜单</label><span>{{ selRefObj.menu }}</span></div>
              <div class="arm-ro"><label>功能</label><span>{{ selRefObj.function_key || '（未归类）' }}</span></div>
              <div class="arm-ro"><label>角色</label><span>{{ roleLabel(selRefObj.role) }}</span></div>
              <div class="arm-ro"><label>模型配置</label><span>{{ mcName(selRefObj.model_config_id) }}</span></div>
              <div class="arm-ro"><label>思考模式</label><span>{{ thinkingLabel(selRefObj.thinking) }}</span></div>
              <div class="arm-ro"><label>强度</label><span>{{ strengthLabel(selRefObj.strength) }}</span></div>
              <div class="arm-ro"><label>启用</label><span>{{ selRefObj.enabled ? '是' : '否' }}</span></div>
            </div>
            <div class="arm-field">
              <label>正文（content / system_prompt）</label>
              <pre class="arm-ref-content">{{ selRefObj.content }}</pre>
            </div>
            <div class="arm-edit-ops">
              <button class="btn primary big" :disabled="saving" @click="copyRef(selRefObj.ref_path)">
                复制使用规则
              </button>
            </div>
          </div>
          <div v-else class="arm-empty">
            <div class="arm-empty-inner">
              <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M4 4h16v6H4zM4 14h16v6H4z" /></svg>
              <p>从左侧选择一条参考规则查看详情。</p>
            </div>
          </div>
        </template>

        <!-- 我的规则编辑 -->
        <template v-else>
          <div v-if="selMineId" class="arm-edit">
            <div class="arm-edit-head">
              <span class="arm-edit-tag" :class="selMine?.ref_path ? 'src' : 'manual'">{{ isNew ? '新建规则' : (selMine?.ref_path ? '来自默认参考（可重置）' : '手动新建（无来源）') }}</span>
            </div>

            <div class="arm-field">
              <label>名称</label>
              <input v-model="form.name" class="inp" placeholder="如：默认-整理文本为多条提示词" />
            </div>

            <div class="arm-row">
              <div class="arm-field">
                <label>菜单</label>
                <select v-model="form.menu" class="sel">
                  <option v-for="s in menuOptions" :key="s" :value="s">{{ s }}</option>
                </select>
              </div>
              <div class="arm-field">
                <label>功能（function_key）</label>
                <input v-model="form.function_key" class="inp" placeholder="如：导入外部提示词 / 06-改写" />
              </div>
            </div>

            <div class="arm-row">
              <div class="arm-field">
                <label>角色（role）</label>
                <select v-model="form.role" class="sel">
                  <option v-for="r in ROLES" :key="r" :value="r">{{ roleLabel(r) }}</option>
                </select>
              </div>
              <div class="arm-field">
                <label>模型配置</label>
                <select v-model="form.model_config_id" class="sel" @change="onModelConfigChange">
                  <option :value="null">跟随默认模型</option>
                  <option v-for="m in modelConfigs" :key="m.id" :value="m.id">{{ m.name }}</option>
                </select>
              </div>
            </div>

            <div class="arm-row">
              <div class="arm-field">
                <label>思考模式</label>
                <select v-model="form.thinking" class="sel">
                  <option v-for="t in thinkingOptions" :key="t.value" :value="t.value">{{ t.label }}</option>
                </select>
              </div>
              <div class="arm-field" v-if="showStrengthSelect">
                <label>思考强度</label>
                <select v-model="form.strength" class="sel">
                  <option v-for="s in strengthOptions" :key="s.value" :value="s.value">{{ s.label }}</option>
                </select>
              </div>
              <div class="arm-field" v-else-if="selectedMode">
                <label>思考强度</label>
                <p style="margin:7px 0 0;font-size:12.5px;color:var(--sx-text);">当前模式不思考，无需设置强度</p>
              </div>
            </div>

            <div class="arm-field">
              <label class="arm-switch">
                <input type="checkbox" v-model="form.enabled" />
                <span>启用（调用方只列出启用的规则）</span>
              </label>
            </div>

            <div class="arm-field">
              <label>正文（content / system_prompt）</label>
              <textarea v-model="form.content" class="arm-content" rows="12" placeholder="规则正文，作为 system_prompt 下发给模型"></textarea>
            </div>

            <div class="arm-edit-ops">
              <button class="btn primary" :disabled="saving" @click="saveRule">{{ saving ? '保存中…' : '保存' }}</button>
              <button v-if="!isNew && selMine?.ref_path" class="btn ghost" :disabled="saving" @click="resetMine">重置（用来源文件）</button>
              <button v-if="!isNew" class="btn danger" :disabled="saving" @click="deleteRule">删除</button>
              <button class="btn ghost" @click="cancelEdit">取消</button>
            </div>
          </div>
          <div v-else class="arm-empty">
            <div class="arm-empty-inner">
              <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M4 4h16v6H4zM4 14h16v6H4z" /></svg>
              <p>从左侧选择一条规则，或点右上「新建规则」。</p>
            </div>
          </div>
        </template>
      </section>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, nextTick, watch } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '../common/http.js'
import { confirm as uiConfirm } from '../common/useConfirm.js'

// 菜单（menu）下拉候选：左侧栏一级功能（方案 B，不含漫剧创作子项、日志查看、发布版本）
const MENU_OPTIONS = [
  '提示词库',
  '爆款收集',
  '小说改写',
  '推文助手',
  '羊毛管理',
  '每日任务',
  '文件管理',
  '应用中心',
  '网址导航',
  '账号矩阵',
  'AI助手',
  'AI指令库',
  'AI密钥库',
  'AI模型配置',
  'AI调用规则',
  '设置',
  '用户管理',
  '清除缓存',
  '通用',
]
// 下拉项动态包含当前值（兼容历史数据中不在候选里的 menu）
const menuOptions = computed(() => {
  const cur = (form.menu || '').trim()
  return MENU_OPTIONS.includes(cur) ? MENU_OPTIONS : [cur, ...MENU_OPTIONS]
})

const ROLES = ['system', 'generate', 'optimize', 'split', 'organize', 'format', 'review']
// 强度档位中文标签（与模型配置页一致，不含 ultra；具体档位由所选模型的 effort_mapping 动态生成）
const EFFORT_LABELS = { low: '低', medium: '中', high: '高' }
function roleLabel(r) {
  return ({ system: '系统', generate: '生成', optimize: '优化', split: '拆分', organize: '整理', format: '格式', review: '审核' })[r] || r
}
function thinkingLabel(t) {
  return ({
    follow: '跟随模型配置',
    fast: '快速',
    expert: '专家（思考）',
    enabled: '专家（思考）',     // 旧值兼容
    disabled: '快速',           // 旧值兼容
  })[t] || t || '跟随模型配置'
}
function strengthLabel(s) {
  if (s == null || s === '' || s === 'follow') return '跟随模型配置'
  return ({ low: '低', medium: '中', high: '高', ultra: '超高' })[s] || s
}
function mcById(id) {
  return modelConfigs.value.find((m) => m.id === id) || null
}
// 把 DB 里的旧 thinking 值（enabled/disabled/follow/具体 mode key）规范化为当前模型支持的 key
function coerceThinkingValue(raw, modelConfig) {
  if (raw == null || raw === '' || raw === 'follow') return 'follow'
  const modes = modelConfig?.profile?.modes || []
  // 兼容旧数据：enabled -> expert，disabled -> fast
  let target = raw
  if (raw === 'enabled') target = 'expert'
  if (raw === 'disabled') target = 'fast'
  if (modes.some((m) => m.key === target)) return target
  // 若旧值在当前模型已不存在，回落到跟随模型配置
  return 'follow'
}

const route = useRoute()

const activeTab = ref('mine')
const references = ref([])
const myRules = ref([])
const modelConfigs = ref([])
const selRef = ref(null)
const selMineId = ref(null)
const saving = ref(false)

const isNew = computed(() => selMineId.value === '__new__')
const selRefObj = computed(() => references.value.find((r) => r.ref_path === selRef.value) || null)
const selMine = computed(() => myRules.value.find((r) => r.id === selMineId.value) || null)

function mcName(id) {
  const m = modelConfigs.value.find((x) => x.id === id)
  return m ? m.name : '跟随默认模型'
}

const refTree = computed(() => groupTree(references.value))
const mineTree = computed(() => groupTree(myRules.value))

function groupTree(list) {
  const byMenu = {}
  for (const r of list) {
    byMenu[r.menu] = byMenu[r.menu] || {}
    byMenu[r.menu][r.function_key || ''] = byMenu[r.menu][r.function_key || ''] || []
    byMenu[r.menu][r.function_key || ''].push(r)
  }
  return Object.entries(byMenu)
    .sort((a, b) => a[0].localeCompare(b[0]))
    .map(([name, fns]) => ({
      name,
      fns: Object.entries(fns)
        .sort((a, b) => a[0].localeCompare(b[0]))
        .map(([fnName, arr]) => ({
          name: fnName,
          rules: arr.slice().sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0)),
        })),
    }))
}

function showToast(msg) {
  const el = document.createElement('div')
  el.textContent = msg
  el.style.cssText =
    'position:fixed;left:50%;bottom:32px;transform:translateX(-50%);background:rgba(27,31,59,.9);color:#fff;padding:9px 16px;border-radius:10px;font-size:13px;z-index:9999;box-shadow:0 8px 30px rgba(0,0,0,.25)'
  document.body.appendChild(el)
  setTimeout(() => el.remove(), 2200)
}

async function loadReferences() {
  try {
    const list = await api('/ai-rules/references', 'GET')
    references.value = Array.isArray(list) ? list : []
  } catch (e) {
    showToast('加载参考规则失败：' + (e?.message || e))
  }
}
async function loadMine() {
  try {
    const list = await api('/ai-rules/', 'GET')
    myRules.value = Array.isArray(list) ? list : []
  } catch (e) {
    showToast('加载规则失败：' + (e?.message || e))
  }
}
async function loadModelConfigs() {
  try {
    const list = await api('/model_config', 'GET')
    modelConfigs.value = Array.isArray(list) ? list : []
  } catch (e) {
    /* 失败不阻断 */
  }
}

function selectRef(refPath) {
  selRef.value = refPath
}

// 切到「默认参考规则」Tab 时重新拉取，保证状态最新（避免删除我的规则后残留旧标记）
watch(activeTab, (v) => {
  if (v === 'ref') loadReferences()
})
function selectMine(id) {
  selMineId.value = id
  fillFormFromMine()
}
function fillFormFromMine() {
  const r = selMine.value
  if (!r) return
  Object.assign(form, {
    name: r.name,
    menu: r.menu,
    function_key: r.function_key,
    role: r.role,
    content: r.content,
    model_config_id: r.model_config_id,
    thinking: coerceThinkingValue(r.thinking, mcById(r.model_config_id)),
    strength: (r.strength == null || r.strength === '' || r.strength === 'follow') ? 'follow' : r.strength,
    enabled: !!r.enabled,
  })
}

const form = reactive({
  name: '',
  menu: '提示词库',
  function_key: '',
  role: 'organize',
  content: '',
  model_config_id: null,
  thinking: 'follow',
  strength: 'follow',
  enabled: true,
})

// 选中模型配置后，动态生成该模型支持的思考模式与思考强度档位
const selectedModel = computed(() => modelConfigs.value.find(m => m.id === form.model_config_id) || null)
const selectedProfile = computed(() => selectedModel.value?.profile || null)
const modelModes = computed(() => selectedProfile.value?.modes || [])

const thinkingOptions = computed(() => {
  const opts = [{ value: 'follow', label: '跟随模型配置' }]
  for (const m of modelModes.value) {
    opts.push({ value: m.key, label: m.name || m.key })
  }
  return opts
})

const selectedMode = computed(() => {
  if (form.thinking === 'follow') return null
  return modelModes.value.find((m) => m.key === form.thinking) || null
})

const showStrengthSelect = computed(() => !!selectedMode.value && selectedMode.value.thinking)

const currentEffortMapping = computed(() => selectedProfile.value?.effort_mapping || {})
const strengthOptions = computed(() => {
  const opts = [{ value: 'follow', label: '跟随模型配置' }]
  for (const k of Object.keys(currentEffortMapping.value)) {
    opts.push({ value: k, label: EFFORT_LABELS[k] || k })
  }
  return opts
})

// 当不需要强度时，自动把强度回落到跟随模型配置
watch(showStrengthSelect, (show) => {
  if (!show) form.strength = 'follow'
})

// 选了具体模型配置后，思考模式与强度默认落「跟随模型配置」，避免选到该模型不存在的档位
function onModelConfigChange() {
  form.thinking = 'follow'
  form.strength = 'follow'
}

function newRule() {
  activeTab.value = 'mine'
  selMineId.value = '__new__'
  Object.assign(form, {
    name: '',
    menu: '提示词库',
    function_key: '',
    role: 'organize',
    content: '',
    model_config_id: null,
    thinking: 'follow',
    strength: 'follow',
    enabled: true,
  })
}
function cancelEdit() {
  selMineId.value = null
}

async function copyRef(refPath) {
  saving.value = true
  try {
    const created = await api('/ai-rules/copy-reference', 'POST', { ref_path: refPath })
    await loadReferences()
    await loadMine()
    activeTab.value = 'mine'
    if (created && created.id) {
      selMineId.value = created.id
      fillFormFromMine()
    }
    showToast('已复制为「我的规则」')
  } catch (e) {
    showToast('复制失败：' + (e?.message || e))
  } finally {
    saving.value = false
  }
}

async function saveRule() {
  if (!form.name.trim()) return showToast('请填写名称')
  if (!form.menu.trim()) return showToast('请选择菜单')
  if (!form.function_key.trim()) return showToast('请填写功能 function_key')
  if (!form.role.trim()) return showToast('请填写角色 role')
  if (!ROLES.includes(form.role)) return showToast('role 取值不合法')
  if (!thinkingOptions.value.some((t) => t.value === form.thinking)) return showToast('思考模式不合法')
  if (showStrengthSelect.value) {
    if (form.strength !== 'follow' && !Object.keys(currentEffortMapping.value).includes(form.strength)) return showToast('思考强度取值不合法')
  } else if (form.strength !== 'follow') {
    return showToast('当前模式不思考，思考强度只能选「跟随模型配置」')
  }
  if (!form.content.trim()) return showToast('正文（content）不能为空')
  // 名称全局唯一（排除自身）
  const dup = myRules.value.find((r) => r.id !== selMineId.value && r.name === form.name.trim())
  if (dup) return showToast('名称「' + form.name.trim() + '」已存在，请换一个')

  saving.value = true
  const body = {
    name: form.name.trim(),
    menu: form.menu.trim(),
    function_key: form.function_key.trim(),
    role: form.role,
    content: form.content,
    model_config_id: form.model_config_id || null,
    thinking: form.thinking,
    strength: form.strength === 'follow' ? null : form.strength,
    enabled: form.enabled ? 1 : 0,
  }
  try {
    if (isNew.value) {
      const created = await api('/ai-rules/', 'POST', body)
      await loadMine()
      if (created && created.id) selMineId.value = created.id
      showToast('已新建规则')
    } else {
      await api('/ai-rules/' + selMineId.value, 'PUT', body)
      await loadMine()
      showToast('已保存')
    }
    fillFormFromMine()
  } catch (e) {
    showToast('保存失败：' + (e?.message || e))
  } finally {
    saving.value = false
  }
}

async function deleteRule() {
  if (!selMine.value) return
  const isManual = !selMine.value.ref_path
  const tip = isManual
    ? '这是手动新建的规则，删除后无法恢复（没有来源文件可重载）。确定删除？'
    : '该规则复制自参考规则，删除后仍可从参考规则重新复制。确定删除？'
  const ok = await uiConfirm(tip, {
    title: isManual ? '删除手动新建规则' : '删除规则',
    variant: 'danger',
    confirmText: '删除',
  })
  if (!ok) return
  saving.value = true
  try {
    await api('/ai-rules/' + selMineId.value, 'DELETE')
    await loadMine()
    await loadReferences()
    selMineId.value = null
    showToast('已删除')
  } catch (e) {
    showToast('删除失败：' + (e?.message || e))
  } finally {
    saving.value = false
  }
}

async function resetMine() {
  if (!selMine.value || !selMine.value.ref_path) return
  const ok = await uiConfirm('重置将用来源文件内容覆盖当前规则，你的修改会丢失。继续？', {
    title: '重置规则',
    variant: 'danger',
    confirmText: '继续重置',
  })
  if (!ok) return
  saving.value = true
  const keepId = selMineId.value
  try {
    await api('/ai-rules/' + keepId + '/reset', 'POST')
    await loadMine()
    selMineId.value = keepId
    fillFormFromMine()
    showToast('已重置为来源文件内容')
  } catch (e) {
    showToast('重置失败：' + (e?.message || e))
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  await Promise.all([loadReferences(), loadMine(), loadModelConfigs()])
  // 锚点定位：调用方带 ?ruleId= 跳来时，自动切到「我的规则」并选中
  const rid = route.query.ruleId
  if (rid) {
    const id = Number(rid)
    const r = myRules.value.find((x) => x.id === id)
    if (r) {
      activeTab.value = 'mine'
      selectMine(id)
      await nextTick()
      const dom = document.getElementById('rule-' + id)
      if (dom) dom.scrollIntoView({ behavior: 'smooth', block: 'center' })
      return
    }
  }
  // 从「小说改写」管线卡片 deep-link 过来：?menu=小说改写&function_key=00-拆分&tab=ref
  const qMenu = route.query.menu
  const qFn = route.query.function_key
  if (qMenu && qFn) {
    const qTab = route.query.tab === 'mine' ? 'mine' : 'ref'
    activeTab.value = qTab
    form.menu = qMenu
    form.function_key = qFn
    if (qTab === 'ref') {
      const r = references.value.find((x) => x.menu === qMenu && x.function_key === qFn)
      if (r) selRef.value = r.ref_path
    } else {
      const r = myRules.value.find((x) => x.menu === qMenu && x.function_key === qFn)
      if (r) {
        selectMine(r.id)
      } else {
        // 我的规则没有该功能时，自动回退到参考规则
        activeTab.value = 'ref'
        const rr = references.value.find((x) => x.menu === qMenu && x.function_key === qFn)
        if (rr) selRef.value = rr.ref_path
      }
    }
  }
})
</script>

<style scoped>
.arm-page {
  height: calc(100vh - 44px);
  display: flex;
  flex-direction: column;
  background: var(--sx-bg-page);
  color: var(--sx-text-strong);
}
.arm-top {
  flex-shrink: 0;
  padding: 18px 22px 0;
  border-bottom: 1px solid var(--sx-border);
  background: var(--sx-bg-surface);
}
.arm-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}
.arm-title {
  display: flex;
  gap: 12px;
  align-items: center;
  color: var(--sx-accent-strong);
}
.arm-title h1 {
  font-size: 18px;
  margin: 0;
  color: var(--sx-text-strong);
}
.arm-sub {
  margin: 4px 0 0;
  font-size: 12.5px;
  color: var(--sx-text);
  max-width: 760px;
}
.arm-sub b {
  color: var(--sx-accent-strong);
}
.arm-actions {
  display: flex;
  gap: 10px;
  flex-shrink: 0;
}

.arm-tabbar {
  display: flex;
  gap: 4px;
  margin-top: 14px;
}
.arm-tab {
  border: none;
  background: transparent;
  color: var(--sx-text);
  font-size: 13.5px;
  font-weight: 600;
  padding: 9px 16px;
  border-radius: 10px 10px 0 0;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  border-bottom: 2px solid transparent;
}
.arm-tab:hover {
  background: var(--sx-accent-soft);
}
.arm-tab.active {
  color: var(--sx-accent-strong);
  border-bottom-color: var(--sx-accent);
  background: var(--sx-bg-page);
}
.tab-count {
  font-size: 11px;
  font-weight: 700;
  background: rgba(0, 0, 0, 0.45);
  color: #fff;
  border-radius: 999px;
  padding: 2px 8px;
}
.arm-tab.active .tab-count {
  background: #fff;
  color: var(--sx-accent-strong);
}

.arm-body {
  flex: 1;
  min-height: 0;
  display: flex;
  overflow: hidden;
}
.arm-list {
  width: 360px;
  flex-shrink: 0;
  border-right: 1px solid var(--sx-border);
  background: var(--sx-bg-surface-2);
  overflow-y: auto;
  padding: 12px 10px;
}
.arm-list-hint {
  font-size: 11.5px;
  color: var(--sx-text-muted);
  padding: 2px 8px 10px;
  line-height: 1.7;
  border-bottom: 1px dashed var(--sx-border);
  margin-bottom: 8px;
}
.arm-empty-list {
  font-size: 13px;
  color: var(--sx-text-muted);
  padding: 16px 8px;
  line-height: 1.6;
}
.tree-scope {
  margin-bottom: 12px;
}
.tree-scope-name {
  font-size: 12px;
  font-weight: 700;
  color: #fff;
  background: var(--sx-accent-strong);
  padding: 4px 10px;
  border-radius: 6px;
  display: inline-block;
  text-transform: uppercase;
  letter-spacing: 0.4px;
}
.tree-fn {
  margin: 6px 0 8px 6px;
}
.tree-fn-name {
  font-size: 12px;
  font-weight: 700;
  color: var(--sx-accent-strong);
  background: var(--sx-accent-soft);
  padding: 3px 10px;
  border-radius: 6px;
  display: inline-block;
}
.tree-rule {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  font-size: 13px;
  padding: 7px 10px;
  margin: 2px 0;
  border-radius: 8px;
  cursor: pointer;
  color: var(--sx-text-strong);
  border: 1px solid transparent;
}
.tree-rule:hover {
  background: var(--sx-accent-soft);
}
.tree-rule.active {
  background: var(--sx-accent-soft);
  border-color: var(--sx-accent);
  font-weight: 600;
}
.tree-rule.off {
  opacity: 0.5;
}
.tree-rule-name {
  min-width: 0;
  white-space: normal;
  word-break: break-word;
  line-height: 1.35;
  text-align: left;
  flex: 1;
}
.tree-badge {
  display: inline-block;
  font-size: 10.5px;
  line-height: 1;
  padding: 2px 6px;
  border-radius: 5px;
  font-weight: 600;
  flex-shrink: 0;
}
.tree-badge.role {
  background: var(--sx-bg-surface);
  color: var(--sx-text);
  border: 1px solid var(--sx-border-strong);
  margin-right: 4px;
}
.tree-badge.src {
  background: var(--sx-accent-soft);
  color: var(--sx-accent-strong);
}
.tree-badge.manual {
  background: rgba(245, 158, 11, 0.16);
  color: #d97706;
  border: 1px solid rgba(245, 158, 11, 0.4);
}
.mini-btn {
  border: 1px solid var(--sx-accent);
  background: var(--sx-accent);
  color: #fff;
  font-size: 11px;
  font-weight: 600;
  padding: 3px 8px;
  border-radius: 6px;
  cursor: pointer;
  flex-shrink: 0;
}
.mini-btn:hover {
  background: var(--sx-accent-hover);
}
.mini-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.arm-detail,
.arm-empty {
  flex: 1;
  min-width: 0;
  overflow-y: auto;
  padding: 18px 24px;
}
.arm-edit-head {
  margin-bottom: 12px;
}
.arm-edit-tag {
  font-size: 12px;
  color: var(--sx-accent-strong);
  background: var(--sx-accent-soft);
  padding: 3px 10px;
  border-radius: 999px;
}
.arm-edit-tag.ref {
  color: var(--sx-text);
  background: var(--sx-bg-surface-2);
  border: 1px solid var(--sx-border);
}
.arm-edit-tag.src {
  color: var(--sx-accent-strong);
  background: var(--sx-accent-soft);
}
.arm-edit-tag.manual {
  color: #d97706;
  background: rgba(245, 158, 11, 0.16);
  border: 1px solid rgba(245, 158, 11, 0.4);
}
.arm-field {
  margin-bottom: 14px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.arm-row {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}
.arm-row .arm-field {
  flex: 1;
  min-width: 220px;
}
.arm-field label {
  font-size: 12.5px;
  color: var(--sx-text);
  font-weight: 600;
}
.arm-strength-val {
  color: var(--sx-accent-strong);
  font-weight: 700;
  margin-left: 4px;
}
.inp,
.sel {
  border: 1px solid var(--sx-border-strong);
  border-radius: 8px;
  padding: 8px 10px;
  font-size: 13.5px;
  background: var(--sx-bg-surface);
  color: var(--sx-text-strong);
  box-sizing: border-box;
  width: 100%;
}
.inp:focus,
.sel:focus {
  outline: none;
  border-color: var(--sx-accent);
  box-shadow: 0 0 0 3px var(--sx-accent-soft);
}
.arm-range {
  width: 100%;
  accent-color: var(--sx-accent);
}
.arm-switch {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 500 !important;
  cursor: pointer;
}
.arm-content {
  width: 100%;
  min-height: 320px;
  resize: vertical;
  border: 1px solid var(--sx-border-strong);
  border-radius: 8px;
  padding: 10px 12px;
  font-size: 13px;
  line-height: 1.6;
  font-family: ui-monospace, Menlo, Consolas, monospace;
  color: var(--sx-text-strong);
  background: var(--sx-bg-surface);
  box-sizing: border-box;
}
.arm-content:focus {
  outline: none;
  border-color: var(--sx-accent);
  box-shadow: 0 0 0 3px var(--sx-accent-soft);
}
.arm-edit-ops {
  display: flex;
  gap: 10px;
  margin-top: 8px;
  flex-wrap: wrap;
}
.arm-empty {
  display: flex;
  align-items: center;
  justify-content: center;
}
.arm-empty-inner {
  text-align: center;
  color: var(--sx-text-muted);
}
.arm-empty-inner p {
  margin-top: 10px;
  font-size: 13.5px;
}
.btn {
  border: 1px solid var(--sx-border-strong);
  background: var(--sx-bg-surface);
  color: var(--sx-text-strong);
  border-radius: 9px;
  padding: 8px 14px;
  font-size: 13px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.btn:hover {
  border-color: var(--sx-border-hover);
}
.btn.primary {
  background: var(--sx-accent);
  border-color: var(--sx-accent);
  color: #fff;
}
.btn.primary:hover {
  background: var(--sx-accent-hover);
}
.btn.big {
  padding: 10px 18px;
  font-size: 13.5px;
}
.btn.ghost {
  background: transparent;
}
.btn.danger {
  background: transparent;
  border-color: var(--sx-accent-pink, #ff3d63);
  color: var(--sx-accent-pink, #ff3d63);
}
.btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

/* 参考只读详情 */
.arm-ref-view {
  max-width: 760px;
}
.arm-ref-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px 24px;
  margin-bottom: 16px;
}
.arm-ro {
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding: 8px 10px;
  background: var(--sx-bg-surface);
  border: 1px solid var(--sx-border);
  border-radius: 8px;
}
.arm-ro label {
  font-size: 11px;
  color: var(--sx-text-muted);
  font-weight: 600;
}
.arm-ro span {
  font-size: 13px;
  color: var(--sx-text-strong);
}
.arm-ref-content {
  white-space: pre-wrap;
  word-break: break-word;
  width: 100%;
  min-height: 220px;
  border: 1px solid var(--sx-border-strong);
  border-radius: 8px;
  padding: 10px 12px;
  font-size: 13px;
  line-height: 1.6;
  font-family: ui-monospace, Menlo, Consolas, monospace;
  color: var(--sx-text-strong);
  background: var(--sx-bg-surface);
  box-sizing: border-box;
  margin: 0;
}
</style>
