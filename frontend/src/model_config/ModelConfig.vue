<template>
  <div class="mc">
    <div class="head">
      <h2>AI模型配置</h2>
      <button class="btn primary" @click="openCreate">新增配置</button>
    </div>

    <div class="card-grid">
      <div
        v-for="c in list"
        :key="c.id"
        class="config-card"
        :class="{ active: c.is_active, dragging: dragId === c.id }"
        draggable="true"
        @dragstart="onDragStart(c, $event)"
        @dragover="onDragOver($event)"
        @drop="onDrop(c, $event)"
        @dragend="onDragEnd($event)"
      >
        <div class="card-top">
          <div class="card-title">
            <span class="provider-badge">{{ providerLabel(c.provider_key || c.provider) }}</span>
            <strong>{{ c.name }}</strong>
          </div>
          <div class="card-top-actions">
            <span class="status-badge" :class="c.is_active ? 'on' : 'off'">
              {{ c.is_active ? '默认模型' : '非默认' }}
            </span>
          </div>
        </div>
        <div class="card-body">
          <div class="info-row"><span class="label">模型</span><span class="value">{{ c.model_name }}</span></div>
          <div class="info-row"><span class="label">模式</span><span class="value">{{ modeLabel(c) }}</span></div>
          <div class="info-row"><span class="label">接口</span><span class="value mono" :title="c.base_url">{{ c.base_url }}</span></div>
          <div class="info-row"><span class="label">温度</span><span class="value">{{ c.temperature }}{{ c.temperature_locked ? '（锁定）' : '' }}</span></div>
          <div class="info-row"><span class="label">超时</span><span class="value">{{ c.timeout_sec }}s</span></div>
          <div class="tags">
            <span v-if="c.thinking_enabled" class="tag think">专家模式</span>
            <span v-else class="tag fast">快速模式</span>
            <span v-if="c.profile?.supports_vision ?? c.supports_vision" class="tag vision">图片输入</span>
            <span v-if="c.profile?.supports_files ?? c.supports_files" class="tag files">文件上传</span>
            <span v-if="c.thinking_enabled" class="tag effort">强度 {{ effortLabel(c.reasoning_effort) }}</span>
          </div>
        </div>
        <div class="card-ops">
          <button class="btn-sm" :disabled="testingId === c.id" @click="testRow(c.id)">
            {{ testingId === c.id ? '测试中…' : '测试' }}
          </button>
          <button v-if="!c.is_active" class="btn-sm primary" @click="activate(c.id)">设为默认</button>
          <button class="btn-sm edit" @click="edit(c)">编辑</button>
          <button class="btn-sm danger" @click="remove(c.id)">删除</button>
        </div>
      </div>
      <div v-if="!list.length" class="empty-card">
        <div class="empty-icon">🤖</div>
        <div class="empty-title">还没有模型配置</div>
        <div class="empty-desc">点右上角「新增配置」添加你的第一个大模型接口</div>
      </div>
    </div>

    <!-- 新建/编辑弹窗 -->
    <div v-if="showForm" class="modal-mask" @click.self="closeForm">
      <div class="modal form-modal">
        <div class="modal-head">
          <h3>{{ editingId ? '编辑AI模型配置' : '新建AI模型配置' }}</h3>
          <button class="x" @click="closeForm">✕</button>
        </div>
        <div class="modal-body">
          <div class="form-grid">
            <label>
              <span class="label-text">名称（建议跟模型名称保持一致）<span class="required">*</span></span>
              <input v-model="form.name" placeholder="如 deepseek官方" />
            </label>

            <label>
              <span class="label-text">厂商<span class="required">*</span></span>
              <select v-model="form.provider_key" @change="onProviderChange">
                <option v-for="p in providers" :key="p.key" :value="p.key">{{ p.name }}</option>
              </select>
            </label>

            <label>
              <span class="label-text">接口地址<span class="required">*</span></span>
              <input v-model="form.base_url" :placeholder="currentProvider?.base_url || 'https://...'" />
            </label>

            <label v-if="form.provider_key !== 'custom'">模型
              <select v-model.number="form.model_profile_id" @change="onProfileChange">
                <option v-for="p in filteredProfiles" :key="p.id" :value="p.id">{{ p.display_name }}</option>
              </select>
            </label>

            <label v-if="form.provider_key !== 'custom' && currentProfile?.modes?.length">模式
              <select v-model="form.mode" @change="onModeChange">
                <option v-for="m in currentProfile.modes" :key="m.key" :value="m.key">{{ m.name }}</option>
              </select>
            </label>
            <p v-if="modeNotes" class="hint">{{ modeNotes }}</p>

            <label v-if="form.provider_key !== 'custom' && showEffortSelect">思考强度
              <select v-model="form.reasoning_effort">
                <option v-for="o in effortOptions" :key="o.value" :value="o.value">{{ o.label }}</option>
              </select>
            </label>
            <p v-else-if="form.provider_key !== 'custom' && currentMode?.thinking" class="hint">该模型在专家模式下没有可调强度档位，将按模型默认强度生效。</p>

            <label v-if="form.provider_key === 'custom'">
              <span class="label-text">模型名<span class="required">*</span></span>
              <input v-model="form.model_name" placeholder="实际 API 模型名" />
            </label>

            <label>
              <span class="label-text">从 AI 密钥库拉取</span>
              <div class="vault-row">
                <select v-model="form.key_vault_id" @change="onVaultChange">
                  <option :value="null">不拉取（手动填写）</option>
                  <option v-for="v in vaults" :key="v.id" :value="v.id">
                    {{ v.name }}（{{ v.provider }}）
                  </option>
                </select>
                <button
                  v-if="form.key_vault_id && editingId"
                  type="button"
                  class="btn-sm refresh-vault"
                  :disabled="refreshingId === editingId"
                  @click="refreshFromVault(editingId)"
                >
                  {{ refreshingId === editingId ? '拉取中…' : '重新拉取' }}
                </button>
              </div>
            </label>
            <p v-if="form.key_vault_id" class="hint">
              已选择「{{ vaultName }}」。保存时会将该条目的接口地址、API Key、Secret Key（如有）填充到上方对应字段，你仍可手动修改。
            </p>

            <label>
              <span class="label-text">API Key<span class="required">*</span></span>
              <div class="key-row">
                <input
                  v-model="form.api_key"
                  :type="showKey ? 'text' : 'password'"
                  autocomplete="off"
                  :placeholder="apiKeyPlaceholder"
                />
                <button type="button" class="key-btn" @click="showKey = !showKey">
                  {{ showKey ? '隐藏' : '查看' }}
                </button>
                <button type="button" class="key-btn" v-if="form.api_key" @click="copyKey">
                  复制
                </button>
              </div>
            </label>
            <p v-if="editingId" class="hint">
              编辑时该字段已显示已保存的 Key。点「查看」可临时显示明文，「复制」直接拷贝完整 Key。
            </p>

            <label>
              Secret Key
              <div class="key-row">
                <input
                  v-model="form.secret_key"
                  :type="showSecret ? 'text' : 'password'"
                  autocomplete="off"
                  placeholder="部分厂商需要第二密钥，没有则留空"
                />
                <button type="button" class="key-btn" @click="showSecret = !showSecret">
                  {{ showSecret ? '隐藏' : '查看' }}
                </button>
                <button type="button" class="key-btn" v-if="form.secret_key" @click="copySecret">
                  复制
                </button>
              </div>
            </label>

            <label v-if="showTemperature">温度
              <input v-model.number="form.temperature" type="number" step="0.1" min="0" max="1" :disabled="temperatureLocked" />
            </label>
            <p v-if="temperatureLocked" class="hint">该模型官方固定 temperature，不支持修改。</p>

            <label>最大输出 tokens <input v-model.number="form.max_tokens" type="number" min="256" step="256" /></label>
            <p v-if="currentProfile && currentProfile.max_tokens_field !== 'max_tokens'" class="hint">该厂商使用字段「{{ currentProfile.max_tokens_field }}」控制最大输出长度。</p>

            <label>超时(秒) <input v-model.number="form.timeout_sec" type="number" min="5" /></label>

            <template v-if="form.provider_key === 'custom'">
              <label class="ck"><input v-model="form.thinking_enabled" type="checkbox" /> 开启思考（专家模式）</label>
              <label v-if="form.thinking_enabled">模型强度
                <select v-model="form.reasoning_effort">
                  <option value="low">低</option>
                  <option value="medium">中</option>
                  <option value="high">高</option>
                </select>
              </label>
              <label>推理参数格式
                <select v-model="form.reasoning_format">
                  <option value="thinking_block">thinking 块（OpenAI / DeepSeek 兼容）</option>
                  <option value="top_level_effort">顶层 reasoning_effort（Kimi 等）</option>
                </select>
              </label>
              <label class="ck"><input v-model="form.supports_vision" type="checkbox" /> 支持图片/视觉输入</label>
              <label class="ck"><input v-model="form.supports_files" type="checkbox" /> 支持文件/文档上传</label>
            </template>
            <template v-else>
              <div class="cap-tags" v-if="currentProfile">
                <span :class="['cap-tag', currentProfile.supports_vision ? 'on' : 'off']">
                  {{ currentProfile.supports_vision ? '支持图片/视觉输入' : '不支持图片/视觉输入' }}
                </span>
                <span :class="['cap-tag', currentProfile.supports_files ? 'on' : 'off']">
                  {{ currentProfile.supports_files ? '支持文件/文档上传' : '不支持文件/文档上传' }}
                </span>
              </div>
            </template>

            <label class="ck"><input v-model="form.is_active" type="checkbox" /> 设为默认模型</label>
          </div>

          <div class="form-actions">
            <button class="btn success" @click="save">{{ editingId ? '保存修改' : '创建' }}</button>
            <button class="btn test" :disabled="formTesting" @click="testForm">
              {{ formTesting ? '测试中…' : '测试联通' }}
            </button>
            <button class="btn" @click="closeForm">取消</button>
          </div>
        </div>
      </div>
    </div>

    <!-- 测试结果弹窗 -->
    <div v-if="resultModal" class="modal-mask" @click.self="closeResultModal">
      <div class="result-modal" :class="resultModal.ok ? 'ok' : 'bad'">
        <div class="rm-icon">{{ resultModal.ok ? '✅' : '❌' }}</div>
        <div class="rm-title">{{ resultModal.ok ? '联通成功' : '联通失败' }}</div>
        <div class="rm-msg">{{ resultModal.message }}</div>
        <div v-if="resultModal.latency_ms" class="rm-lat">延迟：{{ resultModal.latency_ms }} ms</div>
        <div v-if="resultModal.sent_payload" class="rm-diag">
          <div class="rm-diag-row" v-if="resultModal.has_reasoning_content !== undefined">
            <span class="rm-diag-label">思考实际生效</span>
            <span class="rm-diag-val" :class="resultModal.has_reasoning_content ? 'good' : 'warn'">
              {{ resultModal.has_reasoning_content ? '是（模型返回了 reasoning_content）' : '未检测到 reasoning_content' }}
            </span>
          </div>
          <div class="rm-diag-row" v-if="resultModal.response_fields && resultModal.response_fields.length">
            <span class="rm-diag-label">模型返回字段</span>
            <span class="rm-diag-val mono">{{ resultModal.response_fields.join(', ') }}</span>
          </div>
          <details class="rm-payload" open>
            <summary>实际发出的请求 payload</summary>
            <div class="rm-payload-bar">
              <button class="rm-copy" @click="copyPayload">{{ copied ? '已复制 ✓' : '复制' }}</button>
            </div>
            <pre>{{ JSON.stringify(resultModal.sent_payload, null, 2) }}</pre>
          </details>
        </div>
        <button class="btn primary rm-close" @click="closeResultModal">知道了</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, computed, watch } from 'vue'
import { api } from '../common/http.js'
import { confirm, alert } from '../common/useConfirm.js'
import { confirmStore } from '../common/confirmStore.js'

const list = ref([])
const providers = ref([])
const profiles = ref([])
const vaults = ref([])
const showForm = ref(false)
const editingId = ref(null)
const resultModal = ref(null)
const testingId = ref(null)
const formTesting = ref(false)
const dragId = ref(null)

function closeResultModal() { resultModal.value = null }
async function showAlert(message, title = '提示') {
  if (confirmStore.open) {
    return confirmStore.open({ type: 'alert', title, message, confirmText: '知道了' })
  }
  return alert(message, { title })
}
const copied = ref(false)
async function copyPayload() {
  if (!resultModal.value?.sent_payload) return
  const text = JSON.stringify(resultModal.value.sent_payload, null, 2)
  try {
    await navigator.clipboard.writeText(text)
  } catch {
    const ta = document.createElement('textarea')
    ta.value = text
    document.body.appendChild(ta)
    ta.select()
    try { document.execCommand('copy') } catch {}
    document.body.removeChild(ta)
  }
  copied.value = true
  setTimeout(() => { copied.value = false }, 1500)
}

function onDragStart(c, e) {
  dragId.value = c.id
  e.dataTransfer.effectAllowed = 'move'
  e.dataTransfer.setData('text/plain', String(c.id))
}

function onDragOver(e) {
  e.preventDefault()
  if (e.dataTransfer) e.dataTransfer.dropEffect = 'move'
}

async function onDrop(c, e) {
  e.preventDefault()
  const fromId = dragId.value
  if (!fromId || fromId === c.id) return
  const from = list.value.findIndex(x => x.id === fromId)
  const to = list.value.findIndex(x => x.id === c.id)
  if (from < 0 || to < 0) return
  const [moved] = list.value.splice(from, 1)
  list.value.splice(to, 0, moved)
  dragId.value = null
  try {
    await api('/model_config/reorder', 'POST', { ids: list.value.map(x => x.id) })
  } catch (err) {
    await alert('排序保存失败：' + err.message)
    await load()
  }
}

function onDragEnd(e) {
  dragId.value = null
}

const showKey = ref(false)
const showSecret = ref(false)
const refreshingId = ref(null)

function blank() {
  return {
    name: '',
    provider_key: 'deepseek',
    model_profile_id: null,
    mode: 'expert',
    base_url: '',
    model_name: '',
    api_key: '',
    secret_key: '',
    temperature: 0.7,
    timeout_sec: 60,
    is_active: false,
    thinking_enabled: true,
    reasoning_effort: 'medium',
    max_tokens: 2048,
    supports_vision: false,
    supports_files: false,
    reasoning_format: 'thinking_block',
    key_vault_id: null,
  }
}
const form = ref(blank())

const currentProvider = computed(() => providers.value.find(p => p.key === form.value.provider_key))
const filteredProfiles = computed(() => profiles.value.filter(p => p.provider_key === form.value.provider_key))
const currentProfile = computed(() => profiles.value.find(p => p.id === form.value.model_profile_id))
const currentMode = computed(() => (currentProfile.value?.modes || []).find(m => m.key === form.value.mode))
const modeNotes = computed(() => currentMode.value?.notes || '')
// 思考强度选项：跟随当前模型的 effort_mapping 动态生成（如 low/medium/high），不含 ultra
const EFFORT_LABELS = { low: '低', medium: '中', high: '高' }
const effortOptions = computed(() => {
  const map = currentProfile.value?.effort_mapping || {}
  return Object.keys(map).map(k => ({ value: k, label: EFFORT_LABELS[k] || k }))
})
// 仅在「专家（思考）模式」且模型档案定义了强度档位时才显示强度下拉；
// 快速（不思考）模式、或只有布尔开关的模型（effort_mapping 为空）都不显示。
const showEffortSelect = computed(() => {
  return !!currentMode.value?.thinking && Object.keys(currentProfile.value?.effort_mapping || {}).length > 0
})
const temperatureLocked = computed(() => {
  if (form.value.provider_key === 'custom') return false
  return !!currentProfile.value?.temperature_locked
})
const showTemperature = computed(() => {
  if (form.value.provider_key === 'custom') return true
  return !currentMode.value?.thinking || !temperatureLocked.value
})
const apiKeyPlaceholder = computed(() => {
  if (currentProvider.value?.api_key_required === 0) return '该厂商可留空'
  return editingId.value ? '已保存，修改会直接覆盖' : '远程接口必填'
})
const vaultName = computed(() => {
  const v = vaults.value.find(x => x.id === form.value.key_vault_id)
  return v ? `${v.name}（${v.provider}）` : ''
})
async function onVaultChange() {
  const id = form.value.key_vault_id
  if (!id) return
  const v = vaults.value.find(x => x.id === id)
  if (!v) return
  // 从 AI 密钥库带出接口地址、API Key 与 Secret Key（保存时后端会再同步一次）
  if (v.base_url) form.value.base_url = v.base_url
  if (v.api_key) form.value.api_key = v.api_key
  if (v.secret_key) form.value.secret_key = v.secret_key
  await showAlert('已从 AI 密钥库拉取接口地址与密钥。请核对上方「厂商」「模型」「模式」是否与该密钥对应，确认无误后再保存。')
}

function providerLabel(k) {
  const p = providers.value.find(x => x.key === (k || '').toLowerCase())
  return p ? p.name : (k || '自定义')
}
function effortLabel(e) {
  const map = { low: '低', medium: '中', high: '高' }
  return map[e] || e || '中'
}
function modeLabel(cfg) {
  if (cfg.provider_key && cfg.profile?.modes) {
    const m = cfg.profile.modes.find(x => x.key === cfg.mode)
    if (m) return m.name
  }
  return cfg.thinking_enabled ? '专家模式' : '快速模式'
}

async function load() {
  const [cfgList, pList, profList, vaultList] = await Promise.all([
    api('/model_config'),
    api('/model_config/providers'),
    api('/model_config/profiles'),
    api('/key-vault/list').catch(() => []),
  ])
  list.value = cfgList
  providers.value = pList
  profiles.value = profList
  vaults.value = Array.isArray(vaultList) ? vaultList : []
}

function resetForm() { editingId.value = null; form.value = blank(); showKey.value = false; showSecret.value = false }
function openCreate() {
  resetForm()
  initFormDefaults()
  showForm.value = true
}
function closeForm() {
  showForm.value = false
  resetForm()
}

function initFormDefaults() {
  // 新增时默认选第一个厂商的第一个模型/模式
  const p = providers.value[0]
  if (!p) return
  form.value.provider_key = p.key
  onProviderChange(false)
}

function onProviderChange(shouldDefault = true) {
  const p = currentProvider.value
  // 切换厂商时，接口地址必须同步为当前厂商默认地址，避免残留上一家错误地址
  if (p) {
    form.value.base_url = p.base_url || ''
  }
  if (form.value.provider_key === 'custom') {
    form.value.model_profile_id = null
    form.value.mode = 'fast'
    return
  }
  // 自动选该厂商第一个模型
  const profs = filteredProfiles.value
  if (profs.length) {
    form.value.model_profile_id = profs[0].id
    onProfileChange(shouldDefault)
  }
}

function onProfileChange(shouldDefault = true, applyThinking = true) {
  const prof = currentProfile.value
  if (!prof) return
  if (!form.value.base_url || form.value.base_url === currentProvider.value?.base_url) {
    form.value.base_url = currentProvider.value?.base_url || ''
  }
  const modes = prof.modes || []
  if (modes.length) {
    if (shouldDefault) {
      form.value.mode = prof.default_mode || modes[0].key
    } else if (!modes.find(m => m.key === form.value.mode)) {
      form.value.mode = modes[0].key
    }
  }
  syncFromProfile(applyThinking)
}

function onModeChange() {
  syncFromProfile(true)
}

function syncFromProfile(applyThinking = true) {
  const prof = currentProfile.value
  const mode = currentMode.value
  if (!prof || !mode) return
  form.value.model_name = prof.model_name
  // 思考开关/强度作为独立控件：仅在「切换模型档案/模式、且允许套用默认」时覆盖，
  // 编辑已有配置时不覆盖（尊重用户已保存的覆盖值）。
  if (applyThinking) {
    form.value.thinking_enabled = mode.thinking ? 1 : 0
    form.value.reasoning_effort = mode.effort || 'medium'
  }
  // 强度下拉隐藏时（快速模式 / 模型无强度档位）清空残留强度值，避免把旧档位发给不支持的模型
  if (!showEffortSelect.value) {
    form.value.reasoning_effort = ''
  }
  form.value.reasoning_format = prof.reasoning_format
  form.value.supports_vision = !!prof.supports_vision
  form.value.supports_files = !!prof.supports_files
  if (prof.temperature_locked) {
    form.value.temperature = prof.temperature
  }
  if (!form.value.max_tokens || form.value.max_tokens === 2048) {
    form.value.max_tokens = prof.max_tokens
  }
}

async function copyKey() {
  const v = form.value.api_key || ''
  try {
    await navigator.clipboard.writeText(v)
    await alert('API Key 已复制到剪贴板')
  } catch (e) {
    await alert('复制失败：' + e.message)
  }
}
async function copySecret() {
  const v = form.value.secret_key || ''
  try {
    await navigator.clipboard.writeText(v)
    await alert('Secret Key 已复制到剪贴板')
  } catch (e) {
    await alert('复制失败：' + e.message)
  }
}

function edit(c) {
  editingId.value = c.id
  showKey.value = false
  form.value = {
    ...blank(),
    name: c.name,
    provider_key: c.provider_key || c.provider || 'custom',
    model_profile_id: c.model_profile_id || null,
    mode: c.mode || 'fast',
    base_url: c.base_url,
    model_name: c.model_name,
    api_key: c.api_key || '',
    secret_key: c.secret_key || '',
    temperature: c.temperature,
    timeout_sec: c.timeout_sec,
    is_active: !!c.is_active,
    reasoning_effort: c.reasoning_effort || 'medium',
    thinking_enabled: c.thinking_enabled ? 1 : 0,
    max_tokens: c.max_tokens,
    supports_vision: !!(c.profile?.supports_vision ?? c.supports_vision),
    supports_files: !!(c.profile?.supports_files ?? c.supports_files),
    reasoning_format: c.reasoning_format || 'thinking_block',
    key_vault_id: c.key_vault_id ?? null,
  }
  // 确保 profiles 已加载后再回填模式相关字段；不覆盖思考开关/强度（尊重用户已保存值）
  nextTick(() => {
    onProfileChange(false, false)
  })
  showForm.value = true
}

async function save() {
  const trimmedName = (form.value.name || '').trim()
  if (!trimmedName) {
    await showAlert('请输入配置名称')
    return
  }
  const trimmedBaseUrl = (form.value.base_url || '').trim()
  if (!trimmedBaseUrl) {
    await showAlert('请输入接口地址')
    return
  }
  const trimmedKey = (form.value.api_key || '').trim()
  if (!trimmedKey) {
    await showAlert('请输入 API Key')
    return
  }
  const trimmedSecret = (form.value.secret_key || '').trim()

  const payload = {
    ...form.value,
    name: trimmedName,
    base_url: trimmedBaseUrl,
    is_active: form.value.is_active ? 1 : 0,
    supports_vision: form.value.supports_vision ? 1 : 0,
    supports_files: form.value.supports_files ? 1 : 0,
    thinking_enabled: form.value.thinking_enabled ? 1 : 0,
    api_key: trimmedKey,
    secret_key: trimmedSecret,
  }

  try {
    if (editingId.value) await api(`/model_config/${editingId.value}`, 'PUT', payload)
    else await api('/model_config', 'POST', payload)
    showForm.value = false
    await load()
  } catch (e) {
    const msg = (e.message || '').toString()
    // 数据完整性冲突（如唯一约束）给出更友好的提示，而不是把底层报错甩给用户
    if (/UNIQUE|constraint|唯一|重复|已存在/i.test(msg)) {
      await showAlert('保存失败：名称已存在或与其他配置冲突，请换一个名称再保存。', '保存失败')
    } else {
      await showAlert('保存失败：' + msg, '保存失败')
    }
  }
}
async function activate(id) { await api(`/model_config/${id}/activate`, 'POST'); await load() }
async function remove(id) { if (await confirm('确定删除这条配置？', { title: '删除确认' })) { await api(`/model_config/${id}`, 'DELETE'); await load() } }
async function refreshFromVault(id) {
  refreshingId.value = id
  try {
    const row = await api(`/model_config/${id}/refresh_key_vault`, 'POST')
    if (row) {
      form.base_url = row.base_url || ''
      form.api_key = row.api_key || ''
      form.secret_key = row.secret_key || ''
    }
    await load()
    await showAlert('已从 AI 密钥库重新拉取并更新')
  } catch (e) {
    await showAlert('拉取失败：' + e.message, '拉取失败')
  } finally {
    refreshingId.value = null
  }
}

async function testRow(id) {
  testingId.value = id
  resultModal.value = null
  const ctrl = new AbortController()
  const timer = setTimeout(() => ctrl.abort(), 20000)
  try {
    resultModal.value = await api(`/model_config/${id}/test`, 'POST', undefined, ctrl.signal)
  } catch (e) {
    resultModal.value = { ok: false, latency_ms: 0, message: e.name === 'AbortError' ? '测试超时，请检查网络或模型接口' : e.message }
  } finally {
    clearTimeout(timer)
    testingId.value = null
  }
}

async function testForm() {
  if (!form.value.base_url || !form.value.model_name || !form.value.api_key) {
    resultModal.value = { ok: false, latency_ms: 0, message: '请先填好接口地址、模型名和 API Key' }
    return
  }
  formTesting.value = true
  resultModal.value = null
  const payload = {
    ...form.value,
    is_active: form.value.is_active ? 1 : 0,
    supports_vision: form.value.supports_vision ? 1 : 0,
    supports_files: form.value.supports_files ? 1 : 0,
    thinking_enabled: form.value.thinking_enabled ? 1 : 0,
  }
  const ctrl = new AbortController()
  const timer = setTimeout(() => ctrl.abort(), 20000)
  try {
    resultModal.value = await api('/model_config/test', 'POST', payload, ctrl.signal)
  } catch (e) {
    resultModal.value = { ok: false, latency_ms: 0, message: e.name === 'AbortError' ? '测试超时，请检查网络或模型接口' : e.message }
  } finally {
    clearTimeout(timer)
    formTesting.value = false
  }
}

onMounted(async () => {
  await load()
})
</script>

<style scoped>
/* 卡片容器（接语义 token：浅色 = 白卡片，深色 = 暗卡片） */
.mc {
  max-width: 100%; margin: 8px auto 0; padding: 26px 28px 30px; overflow-x: auto;
  background: var(--sx-bg-surface); border: 1px solid var(--sx-border); border-radius: 18px;
  box-shadow: var(--sx-shadow-card);
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
}
/* 标题栏 */
.head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 18px; }
.head h2 { margin: 0; font-size: 22px; font-weight: 600; color: var(--sx-text-strong); letter-spacing: .3px; }

/* 表单卡片 */
.form {
  background: var(--sx-bg-surface-2); padding: 18px 20px; border: 1px solid var(--sx-border);
  border-radius: 12px; margin: 14px 0; display: grid; gap: 14px;
}
.form label { display: flex; flex-direction: column; font-size: 12.5px; color: var(--sx-text-emphasis); font-weight: 600; gap: 6px; }
.form input, .form select {
  width: 100%; box-sizing: border-box;
  padding: 11px 13px; font-size: 14px; color: var(--sx-text-strong);
  background: var(--sx-bg-surface); border: 1.5px solid var(--sx-border-input); border-radius: 10px;
  transition: border-color .15s, background .15s, box-shadow .15s;
}
.form input::placeholder, .form select::placeholder { color: var(--sx-text-faint); }
.form input:focus, .form select:focus {
  outline: none; border-color: var(--sx-accent); background: var(--sx-bg-surface);
  box-shadow: 0 0 0 3px var(--sx-accent-soft);
}
.form input:disabled {
  background: var(--sx-disabled-bg); color: var(--sx-disabled-text); cursor: not-allowed;
}
.form .ck { flex-direction: row; align-items: center; gap: 8px; font-weight: 500; color: var(--sx-text-strong); }
.form .ck input { width: auto; padding: 0; border: none; background: none; }
/* API Key 行：输入框 + 查看/复制按钮 */
.key-row { display: flex; gap: 8px; align-items: stretch; }
.key-row input { flex: 1; width: auto; }
.key-btn {
  flex: none; padding: 0 12px; font-size: 13px; font-weight: 600; cursor: pointer;
  color: var(--sx-btn-secondary-text); background: var(--sx-btn-secondary-bg); border: 1px solid var(--sx-btn-secondary-border); border-radius: 10px;
  transition: background .15s, border-color .15s;
}
.key-btn:hover { background: var(--sx-btn-secondary-bg-hover); border-color: var(--sx-btn-secondary-border); }
.form-actions { display: flex; gap: 10px; margin-top: 2px; }

/* 弹窗（新建/编辑） */
.modal {
  background: var(--sx-bg-elevated); border-radius: 16px; width: 100%; max-width: 640px;
  box-shadow: var(--sx-shadow-pop); border: 1.5px solid var(--sx-border);
  display: flex; flex-direction: column; max-height: calc(100vh - 40px);
}
.modal-head {
  display: flex; justify-content: space-between; align-items: center;
  padding: 16px 20px; border-bottom: 1px solid var(--sx-border);
}
.modal-head h3 { margin: 0; font-size: 17px; font-weight: 700; color: var(--sx-text-strong); }
.modal-head .x {
  background: none; border: none; font-size: 18px; color: var(--sx-text-muted); cursor: pointer;
  padding: 4px 8px; border-radius: 8px; transition: background .12s, color .12s;
}
.modal-head .x:hover { color: var(--sx-accent); background: var(--sx-bg-surface-2); }
.modal-body {
  padding: 18px 20px; overflow-y: auto;
}
.form-grid {
  display: grid; gap: 14px;
}
.form-grid label { display: flex; flex-direction: column; font-size: 12.5px; color: var(--sx-text-emphasis); font-weight: 600; gap: 6px; }
.form-grid input, .form-grid select {
  width: 100%; box-sizing: border-box;
  padding: 11px 13px; font-size: 14px; color: var(--sx-text-strong);
  background: var(--sx-bg-surface); border: 1.5px solid var(--sx-border-input); border-radius: 10px;
  transition: border-color .15s, background .15s, box-shadow .15s;
}
.form-grid input::placeholder, .form-grid select::placeholder { color: var(--sx-text-faint); }
.form-grid input:focus, .form-grid select:focus {
  outline: none; border-color: var(--sx-accent); background: var(--sx-bg-surface);
  box-shadow: 0 0 0 3px var(--sx-accent-soft);
}
.form-grid .ck { flex-direction: row; align-items: center; gap: 8px; font-weight: 500; color: var(--sx-text-strong); }
.form-grid .ck input { width: auto; padding: 0; border: none; background: none; }
.form-grid label .label-text { display: inline-flex; align-items: center; gap: 4px; }
.form-grid label .required { color: #f56c6c; font-weight: 700; line-height: 1; }
.vault-row { display: flex; align-items: center; gap: 10px; }
.vault-row select { flex: 1; min-width: 0; }
.refresh-vault {
  flex-shrink: 0; white-space: nowrap;
  padding: 9px 13px; font-size: 13px; font-weight: 500; cursor: pointer;
  color: var(--sx-btn-secondary-text); background: var(--sx-btn-secondary-bg); border: 1px solid var(--sx-btn-secondary-border); border-radius: 9px;
  transition: background .15s, transform .1s;
}
.refresh-vault:hover:not(:disabled) { background: var(--sx-btn-secondary-bg-hover); transform: translateY(-1px); }
.refresh-vault:disabled { opacity: .6; cursor: not-allowed; transform: none; }

/* 卡片右上角操作 */
.card-top-actions { display: flex; align-items: center; gap: 8px; }
.spinner {
  width: 14px; height: 14px; border: 2px solid var(--sx-btn-secondary-border);
  border-top-color: var(--sx-accent); border-radius: 50%;
  animation: spin .8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* 按钮 */
.btn {
  padding: 9px 16px; font-size: 14px; font-weight: 500; cursor: pointer;
  color: var(--sx-text); background: var(--sx-bg-surface); border: 1px solid var(--sx-border-strong); border-radius: 10px;
  transition: border-color .15s, color .15s, transform .1s, box-shadow .15s;
}
.btn:hover { border-color: var(--sx-accent); color: var(--sx-accent); }
.btn.primary {
  color: #fff; border: none; font-weight: 600; padding: 10px 18px;
  background: var(--sx-btn-primary-bg);
  box-shadow: var(--sx-btn-primary-shadow);
}
.btn.primary:hover { transform: translateY(-1px); box-shadow: var(--sx-btn-primary-shadow-hover); }
.btn.success {
  color: #fff !important; border: none !important; font-weight: 600 !important; padding: 10px 18px !important;
  background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%) !important;
  box-shadow: 0 8px 20px rgba(34, 197, 94, .3) !important;
}
.btn.success:hover { transform: translateY(-1px) !important; box-shadow: 0 12px 26px rgba(34, 197, 94, .42) !important; }
.btn.test {
  color: #fff !important; border: none !important; font-weight: 600 !important; padding: 10px 18px !important;
  background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%) !important;
  box-shadow: 0 8px 20px rgba(139, 92, 246, .3) !important;
}
.btn.test:hover { transform: translateY(-1px) !important; box-shadow: 0 12px 26px rgba(139, 92, 246, .42) !important; }

/* 卡片列表 */
.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
  margin-top: 16px;
}
.config-card {
  background: var(--sx-bg-surface);
  border: 1.5px solid var(--sx-border);
  border-radius: 14px;
  padding: 16px 18px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  transition: transform .12s, box-shadow .15s, border-color .15s, opacity .15s;
  cursor: grab;
  user-select: none;
}
.config-card:active {
  cursor: grabbing;
}
.config-card.dragging {
  opacity: .55;
  transform: scale(.985);
  box-shadow: var(--sx-shadow-pop);
}
.config-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--sx-shadow-card);
  border-color: var(--sx-border-strong);
}
.config-card.active {
  border-color: var(--sx-card-active-border);
  background: var(--sx-card-active-bg);
  box-shadow: var(--sx-card-active-shadow);
}
.card-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 10px;
}
.card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}
.card-title strong {
  font-size: 16px;
  font-weight: 700;
  color: var(--sx-text-strong);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.provider-badge {
  flex: none;
  padding: 3px 8px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 700;
  color: var(--sx-tag-default-text);
  background: var(--sx-tag-default-bg);
  border: 1px solid var(--sx-tag-default-border);
  text-transform: uppercase;
}
.status-badge {
  flex: none;
  padding: 3px 9px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 700;
}
.status-badge.on {
  color: var(--sx-tag-success-text);
  background: var(--sx-tag-success-bg);
  border: 1px solid var(--sx-tag-success-border);
}
.status-badge.off {
  color: var(--sx-tag-default-text);
  background: var(--sx-tag-default-bg);
  border: 1px solid var(--sx-tag-default-border);
}
.card-body {
  display: flex;
  flex-direction: column;
  gap: 7px;
}
.info-row {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
}
.info-row .label {
  flex: none;
  width: 38px;
  color: var(--sx-text-muted);
  font-weight: 600;
}
.info-row .value {
  flex: 1;
  min-width: 0;
  color: var(--sx-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.mono { font-family: ui-monospace, monospace; font-size: 12px; color: var(--sx-text-emphasis); }
.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 4px;
}
.tag {
  padding: 3px 8px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 600;
}
.tag.think { color: var(--sx-tag-info-text); background: var(--sx-tag-info-bg); border: 1px solid var(--sx-tag-info-border); }
.tag.fast { color: var(--sx-tag-success-text); background: var(--sx-tag-success-bg); border: 1px solid var(--sx-tag-success-border); }
.tag.vision { color: var(--sx-tag-purple-text); background: var(--sx-tag-purple-bg); border: 1px solid var(--sx-tag-purple-border); }
.tag.files { color: var(--sx-tag-warn-text); background: var(--sx-tag-warn-bg); border: 1px solid var(--sx-tag-warn-border); }
.tag.effort { color: var(--sx-tag-default-text); background: var(--sx-tag-default-bg); border: 1px solid var(--sx-tag-default-border); }
.card-ops {
  display: flex;
  gap: 8px;
  margin-top: 4px;
  padding-top: 12px;
  border-top: 1px dashed var(--sx-border);
}
.btn-sm {
  flex: 1;
  padding: 7px 0 !important;
  font-size: 13px !important;
  font-weight: 600 !important;
  cursor: pointer !important;
  color: var(--sx-btn-secondary-text) !important;
  background: var(--sx-btn-secondary-bg) !important;
  border: 1px solid var(--sx-btn-secondary-border) !important;
  border-radius: 8px !important;
  transition: background .15s, transform .1s !important;
}
.btn-sm:hover {
  background: var(--sx-btn-secondary-bg-hover) !important;
  transform: translateY(-1px) !important;
}
.btn-sm:disabled {
  opacity: .6 !important;
  cursor: not-allowed !important;
  transform: none !important;
}
.btn-sm.primary {
  color: #fff !important;
  background: var(--sx-btn-primary-bg) !important;
  border: none !important;
  box-shadow: var(--sx-btn-primary-shadow) !important;
}
.btn-sm.primary:hover {
  box-shadow: var(--sx-btn-primary-shadow-hover) !important;
}
.btn-sm.danger {
  color: var(--sx-btn-danger-text) !important;
  background: var(--sx-btn-danger-bg) !important;
  border-color: var(--sx-btn-danger-border) !important;
}
.btn-sm.danger:hover {
  background: var(--sx-btn-danger-bg-hover) !important;
}
.btn-sm.edit {
  color: #fff !important;
  background: var(--sx-btn-edit-bg) !important;
  border: none !important;
  box-shadow: var(--sx-btn-edit-shadow) !important;
}
.btn-sm.edit:hover {
  box-shadow: var(--sx-btn-edit-shadow-hover) !important;
}
.empty-card {
  grid-column: 1 / -1;
  text-align: center;
  padding: 48px 20px;
  color: var(--sx-text-muted);
  background: var(--sx-bg-surface-2);
  border: 1.5px dashed var(--sx-border);
  border-radius: 14px;
}
.empty-icon { font-size: 38px; margin-bottom: 10px; }
.empty-title { font-size: 15px; font-weight: 700; color: var(--sx-text-emphasis); margin-bottom: 5px; }
.empty-desc { font-size: 13px; }

/* 测试结果弹窗 */
.modal-mask {
  position: fixed; inset: 0; z-index: 1000;
  background: var(--sx-overlay);
  display: flex; align-items: center; justify-content: center;
  padding: 20px;
}
.result-modal {
  background: var(--sx-bg-elevated); border-radius: 16px; padding: 28px 32px;
  width: 100%; max-width: 420px; text-align: center;
  box-shadow: var(--sx-shadow-pop);
  border: 1.5px solid var(--sx-border);
}
.result-modal.ok { border-color: var(--sx-tag-success-border); background: linear-gradient(180deg, var(--sx-tag-success-bg) 0%, var(--sx-bg-elevated) 100%); }
.result-modal.bad { border-color: var(--sx-btn-danger-border); background: linear-gradient(180deg, var(--sx-btn-danger-bg) 0%, var(--sx-bg-elevated) 100%); }
.rm-icon { font-size: 42px; margin-bottom: 10px; }
.rm-title { font-size: 18px; font-weight: 700; color: var(--sx-text-strong); margin-bottom: 10px; }
.rm-msg { font-size: 14px; color: var(--sx-text); line-height: 1.6; word-break: break-word; margin-bottom: 6px; }
.rm-lat { font-family: ui-monospace, monospace; font-size: 12.5px; color: var(--sx-text-emphasis); margin-bottom: 14px; }
.rm-close { width: 100%; padding: 10px 0 !important; }
/* 诊断区：让思考模式是否真生效一眼可见 */
.rm-diag {
  text-align: left;
  background: var(--sx-bg-surface-2);
  border: 1px solid var(--sx-border);
  border-radius: 10px;
  padding: 12px 14px;
  margin: 14px 0 18px;
  font-size: 12.5px;
}
.rm-diag-row { display: flex; gap: 8px; padding: 4px 0; align-items: baseline; }
.rm-diag-label { flex: none; width: 92px; color: var(--sx-text-muted); font-weight: 600; }
.rm-diag-val { flex: 1; min-width: 0; color: var(--sx-text); word-break: break-word; }
.rm-diag-val.good { color: #1f7a3c; font-weight: 600; }
.rm-diag-val.warn { color: #c98a00; font-weight: 600; }
.rm-payload { margin-top: 8px; }
.rm-payload summary { cursor: pointer; color: var(--sx-accent); font-weight: 600; user-select: none; }
.rm-payload-bar { display: flex; justify-content: flex-end; margin-top: 8px; }
.rm-copy {
  font-size: 12px; padding: 4px 12px; border-radius: 7px; cursor: pointer;
  background: var(--sx-btn-secondary-bg); color: var(--sx-btn-secondary-text); border: 1px solid var(--sx-btn-secondary-border); font-weight: 600;
  transition: background .12s;
}
.rm-copy:hover { background: var(--sx-btn-secondary-bg-hover); }
.rm-payload pre {
  margin-top: 8px; max-height: 220px; overflow: auto;
  background: var(--sx-bg-surface-2); color: var(--sx-text-strong); padding: 10px 12px;
  border: 1px solid var(--sx-border); border-radius: 8px; font-size: 12px; line-height: 1.55;
  font-family: ui-monospace, monospace; white-space: pre-wrap; word-break: break-word;
}
.hint {
  font-size: 12px; color: var(--sx-text-muted); line-height: 1.5; margin: 0;
}
.cap-tags {
  display: flex; flex-wrap: wrap; gap: 8px; margin-top: 4px;
}
.cap-tag {
  padding: 4px 10px; border-radius: 10px; font-size: 11.5px; font-weight: 600;
}
.cap-tag.on { color: var(--sx-tag-success-text); background: var(--sx-tag-success-bg); border: 1px solid var(--sx-tag-success-border); }
.cap-tag.off { color: var(--sx-tag-default-text); background: var(--sx-tag-default-bg); border: 1px solid var(--sx-tag-default-border); }
</style>
