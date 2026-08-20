<template>
  <div class="kv-page">
    <!-- 顶部固定区：标题栏 + 筛选条 + 管理条 -->
    <div class="kv-top">
      <header class="kv-head">
        <div class="kv-title">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="3" y="11" width="18" height="11" rx="2" />
            <path d="M7 11V7a5 5 0 0 1 10 0v4" />
          </svg>
          <div>
            <h1>AI 密钥库</h1>
            <p class="kv-sub">集中管理各厂商的平台 / 账号 / 密钥；模型配置可直接引用，不必再散贴密钥</p>
          </div>
        </div>
        <div class="kv-actions">
          <button class="btn ghost" :class="{ active: manageMode }" @click="manageMode = !manageMode">
            {{ manageMode ? '退出管理' : '管理' }}
          </button>
          <button class="btn primary" @click="openCreate">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="M12 5v14M5 12h14"/></svg>
            新建密钥
          </button>
        </div>
      </header>

      <!-- 筛选条 -->
      <section class="kv-filters">
        <select v-model="filters.category" class="sel">
          <option value="全部">模型分类</option>
          <option v-for="c in categories" :key="c" :value="c">{{ c }}</option>
        </select>
        <input v-model="filters.keyword" class="inp" placeholder="搜索名称 / 平台 / 账号" @keyup.enter="loadList" />
        <button class="btn ghost sm" @click="loadList">查询</button>
        <span v-if="manageMode" class="sel-hint">已选 {{ selectedIds.length }} 项</span>
      </section>

      <!-- 管理工具条 -->
      <section v-if="manageMode" class="kv-mbar">
        <label class="chk"><input type="checkbox" :checked="allSelected" @change="toggleAll" /> 全选</label>
        <button class="btn ghost sm" @click="importInput?.click()">导入</button>
        <button class="btn ghost sm" :disabled="!list.length" @click="exportAll">导出全部</button>
        <button class="btn ghost sm" :disabled="!selectedIds.length" @click="exportSelected">导出选中</button>
        <button class="btn danger sm" :disabled="!selectedIds.length" @click="batchDelete">批量删除</button>
      </section>
    </div>

    <!-- 列表（表格）滚动区 -->
    <div class="kv-body">
      <section class="kv-list">
        <table class="kv-table" v-if="list.length">
        <thead>
          <tr>
            <th v-if="manageMode" class="col-sel"></th>
            <th class="cell-name">API Key 名称</th><th class="cell-provider">平台</th><th class="cell-cat">归类</th><th class="cell-addr">接口地址</th>
            <th class="cell-key">API Key</th><th class="cell-key">Secret</th><th class="cell-account">账号</th><th class="cell-dev">开发者平台</th><th class="cell-ops">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in list" :key="item.id" :class="{ 'row-sel': manageMode && isSelected(item.id) }">
            <td v-if="manageMode" class="col-sel">
              <input type="checkbox" :checked="isSelected(item.id)" @change="toggleSelect(item.id)" />
            </td>
            <td class="cell-name">
              <div class="nm">{{ item.name }}</div>
            </td>
            <td>{{ item.provider }}</td>
            <td class="cell-cat"><span class="pill">{{ item.category }}</span></td>
            <td class="cell-addr">
              <div class="cell-inner">
                <span class="url-text">{{ item.base_url || '—' }}</span>
                <button v-if="item.base_url" class="mini copy-end" title="复制接口地址" @click="copyText(item.base_url, '接口地址')">复</button>
              </div>
            </td>
            <td class="cell-key">
              <div class="cell-inner">
                <span class="key-mask">{{ maskKey(item.api_key) }}</span>
                <button class="mini copy-end" title="复制明文" @click="copyText(item.api_key, 'API Key')">复</button>
              </div>
            </td>
            <td class="cell-key">
              <div class="cell-inner">
                <span class="key-mask">{{ maskKey(item.secret_key) }}</span>
                <button v-if="item.secret_key" class="mini copy-end" title="复制明文" @click="copyText(item.secret_key, 'Secret Key')">复</button>
              </div>
            </td>
            <td>{{ item.account || '—' }}</td>
            <td class="cell-dev">
              <div class="cell-inner">
                <a v-if="item.dev_url" :href="item.dev_url" target="_blank" rel="noopener" class="link" :title="item.dev_url">打开</a>
                <span v-else>—</span>
                <button v-if="item.dev_url" class="mini copy-end" title="复制链接" @click="copyText(item.dev_url, '开发者平台链接')">复</button>
              </div>
            </td>
            <td class="cell-ops">
              <button class="op" @click="openEdit(item)">编辑</button>
              <button class="op danger" @click="remove(item)">删除</button>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-else class="kv-empty">
        <p>还没有任何密钥条目。</p>
        <button class="btn primary" @click="openCreate">新建第一个密钥</button>
      </div>
    </section>
    </div>

    <!-- 隐藏文件选择器（常驻 DOM，供「导入」按钮与弹窗内按钮共用） -->
    <input ref="importInput" type="file" accept=".xlsx,.xls" hidden @change="onImportPicked" />

    <!-- 导入弹窗 -->
    <div v-if="showImport" class="modal-mask" @click.self="showImport = false">
      <div class="modal">
        <div class="modal-head"><h2>从 Excel 导入</h2><button class="x" @click="showImport = false">✕</button></div>
        <div class="modal-body">
          <p class="kv-hint">支持 .xlsx，自动识别「API Key 名称 / 平台 / 归类 / 接口地址 / API Key / Secret Key / 登录账号 / 开发者平台」等列。</p>
          <p class="kv-hint">导入以「名称 + 平台 + 账号」为键：三者均不同则新建，否则更新。</p>
          <button class="btn ghost" @click="importInput?.click()">选择 Excel 文件</button>
          <span class="kv-fname">{{ importFileName || '未选择' }}</span>
        </div>
        <div class="modal-foot">
          <button class="btn ghost" @click="showImport = false">取消</button>
          <button class="btn primary" :disabled="!importFile || importing" @click="submitImport">开始导入</button>
        </div>
      </div>
    </div>

    <!-- 新建 / 编辑弹窗 -->
    <div v-if="showForm" class="modal-mask" @click.self="closeForm">
      <div class="modal wide">
        <div class="modal-head"><h2>{{ form.id ? '编辑密钥' : '新建密钥' }}</h2><button class="x" @click="closeForm">✕</button></div>
        <div class="modal-body grid2">
          <label class="fld"><span>API Key 名称 *</span><input v-model="form.name" class="inp" placeholder="如：DeepSeek 主号" /></label>
          <label class="fld"><span>平台 / 厂商 *</span><input v-model="form.provider" class="inp" placeholder="DeepSeek / Kimi / 即梦 / 可灵 …" /></label>
          <label class="fld"><span>归类 *</span>
            <select v-model="form.category" class="sel">
              <option v-for="c in categories" :key="c" :value="c">{{ c }}</option>
            </select>
          </label>
          <label class="fld"><span>接口地址 *</span><input v-model="form.base_url" class="inp" placeholder="https://api.deepseek.com/v1" /></label>
          <label class="fld"><span>API Key *</span>
            <div class="pw-row">
              <input v-model="form.api_key" :type="showApiKey ? 'text' : 'password'" class="inp" placeholder="sk-..." />
              <button type="button" class="pw-eye" :title="showApiKey ? '隐藏 API Key' : '显示 API Key'" @click="showApiKey = !showApiKey">
                <svg v-if="showApiKey" viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/>
                  <line x1="1" y1="1" x2="23" y2="23"/>
                </svg>
                <svg v-else viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                  <circle cx="12" cy="12" r="3"/>
                </svg>
              </button>
            </div>
          </label>
          <label class="fld"><span>Secret Key</span>
            <div class="pw-row">
              <input v-model="form.secret_key" :type="showSecret ? 'text' : 'password'" class="inp" placeholder="（部分平台需要）" />
              <button type="button" class="pw-eye" :title="showSecret ? '隐藏 Secret Key' : '显示 Secret Key'" @click="showSecret = !showSecret">
                <svg v-if="showSecret" viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/>
                  <line x1="1" y1="1" x2="23" y2="23"/>
                </svg>
                <svg v-else viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                  <circle cx="12" cy="12" r="3"/>
                </svg>
              </button>
            </div>
          </label>
          <label class="fld"><span>登录账号 *</span><input v-model="form.account" class="inp" placeholder="邮箱 / 手机号" /></label>
          <label class="fld"><span>开发者平台 *</span><input v-model="form.dev_url" class="inp" placeholder="https://platform.deepseek.com/usage" /></label>
        </div>
        <div class="modal-foot">
          <button class="btn ghost" @click="closeForm">取消</button>
          <button class="btn primary" :disabled="!form.name.trim() || saving" @click="submitForm">{{ saving ? '保存中…' : '保存' }}</button>
        </div>
      </div>
    </div>

    <div class="toast" v-if="toast">{{ toast }}</div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { api, apiUpload } from '../common/http.js'
import { confirm } from '../common/useConfirm.js'
import { useAuthStore } from '../login/auth-store.js'

const auth = useAuthStore()
const categories = ['纯文本', '图文理解', '文生图', '文生视频', '音频语音', 'Code编程', '其他']

const list = ref([])
const filters = reactive({ category: '全部', keyword: '' })
const manageMode = ref(false)
const selected = ref(new Set())
const toast = ref('')
let toastTimer = null

const showImport = ref(false)
const importFile = ref(null)
const importFileName = ref('')
const importing = ref(false)
const importInput = ref(null)

const showForm = ref(false)
const saving = ref(false)
const showApiKey = ref(false)
const showSecret = ref(false)
const form = reactive({
  id: null, name: '', provider: '', category: '纯文本', base_url: '',
  api_key: '', secret_key: '', account: '', dev_url: '',
})
const formInput = ref(null)

function showToast(msg) {
  toast.value = msg
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => { toast.value = '' }, 2000)
}

// ---------- 数据加载 ----------
async function loadList() {
  try {
    const q = new URLSearchParams({
      category: filters.category,
      keyword: filters.keyword,
    }).toString()
    list.value = await api(`/key-vault/list?${q}`, 'GET')
  } catch (e) {
    showToast(e.message || '加载失败')
  }
}

// ---------- 选择 ----------
const selectedIds = computed(() => Array.from(selected.value))
const allSelected = computed(() => list.value.length > 0 && list.value.every(i => selected.value.has(i.id)))
function isSelected(id) { return selected.value.has(id) }
function toggleSelect(id) {
  const s = new Set(selected.value)
  s.has(id) ? s.delete(id) : s.add(id)
  selected.value = s
}
function toggleAll(e) {
  if (e.target.checked) selected.value = new Set(list.value.map(i => i.id))
  else selected.value = new Set()
}

// ---------- 密钥掩码 ----------
function maskKey(k) {
  if (!k) return '—'
  const s = String(k)
  if (s.length <= 8) return '••••••••'
  return s.slice(0, 4) + '••••••••' + s.slice(-4)
}
async function copyText(text, what) {
  if (!text) { showToast('无内容'); return }
  try {
    await navigator.clipboard.writeText(text)
    showToast(`${what} 已复制`)
  } catch (e) {
    showToast('复制失败')
  }
}

// ---------- 新建 / 编辑 ----------
function resetForm() {
  Object.assign(form, {
    id: null, name: '', provider: '', category: '纯文本', base_url: '',
    api_key: '', secret_key: '', account: '', dev_url: '',
  })
  showApiKey.value = false
  showSecret.value = false
}
function openCreate() { resetForm(); showForm.value = true }
function openEdit(item) {
  resetForm()
  Object.assign(form, {
    id: item.id, name: item.name, provider: item.provider, category: item.category,
    base_url: item.base_url || '', api_key: item.api_key || '', secret_key: item.secret_key || '',
    account: item.account || '', dev_url: item.dev_url || '',
  })
  showForm.value = true
}
function closeForm() { showForm.value = false }
async function submitForm() {
  const required = [
    ['name', 'API Key 名称'],
    ['provider', '平台 / 厂商'],
    ['category', '归类'],
    ['base_url', '接口地址'],
    ['api_key', 'API Key'],
    ['account', '登录账号'],
    ['dev_url', '开发者平台'],
  ]
  for (const [key, label] of required) {
    if (!String(form[key] || '').trim()) {
      showToast(`请填写${label}`)
      return
    }
  }
  saving.value = true
  try {
    const payload = { ...form }
    if (form.id) await api(`/key-vault/${form.id}`, 'PUT', payload)
    else await api('/key-vault/', 'POST', payload)
    showForm.value = false
    await loadList()
    showToast('已保存')
  } catch (e) {
    showToast(e.message || '保存失败')
  } finally {
    saving.value = false
  }
}

// ---------- 删除 ----------
async function remove(item) {
  if (!(await confirm(`确定删除「${item.name}」？此操作不可撤销。`, { title: '删除密钥' }))) return
  try {
    await api(`/key-vault/${item.id}`, 'DELETE')
    selected.value.delete(item.id)
    await loadList()
    showToast('已删除')
  } catch (e) {
    showToast(e.message || '删除失败')
  }
}
async function batchDelete() {
  if (!selectedIds.value.length) return
  if (!(await confirm(`确定批量删除选中的 ${selectedIds.value.length} 条密钥？`, { title: '批量删除' }))) return
  try {
    await api('/key-vault/batch-delete', 'POST', { ids: selectedIds.value })
    selected.value = new Set()
    await loadList()
    showToast('已删除选中项')
  } catch (e) {
    showToast(e.message || '删除失败')
  }
}

// ---------- 导出 ----------
async function doExport(ids) {
  const resp = await fetch('/api/key-vault/export', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...(auth.token ? { Authorization: `Bearer ${auth.token}` } : {}) },
    body: JSON.stringify({ ids: ids && ids.length ? ids : null }),
  })
  if (!resp.ok) { showToast('导出失败 ' + resp.status); return }
  const blob = await resp.blob()
  const ts = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19)
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = `AI密钥库_${ts}.xlsx`
  document.body.appendChild(a); a.click(); a.remove()
  setTimeout(() => URL.revokeObjectURL(a.href), 1000)
  showToast('已导出（含密钥明文，请妥善保管）')
}
function exportAll() { doExport(null) }
function exportSelected() {
  const ids = selectedIds.value
  if (!ids.length) { showToast('请先选择'); return }
  doExport(ids)
}

// ---------- 导入 ----------
function onImportPicked(e) {
  const f = e.target.files && e.target.files[0]
  if (!f) return
  importFile.value = f
  importFileName.value = f.name
  showImport.value = true
}
async function submitImport() {
  if (!importFile.value) { showToast('请选择文件'); return }
  importing.value = true
  try {
    const fd = new FormData()
    fd.append('file', importFile.value)
    const r = await apiUpload('/key-vault/import', fd)
    const parts = [`新建 ${r.created || 0}`, r.updated ? `覆盖 ${r.updated}` : null, r.skipped ? `跳过 ${r.skipped}` : null]
      .filter(Boolean).join('，')
    showImport.value = false
    importFile.value = null
    importFileName.value = ''
    await loadList()
    showToast(`导入完成（${parts}）${r.errors && r.errors.length ? '，有错误见控制台' : ''}`)
    if (r.errors && r.errors.length) console.warn('密钥导入错误：', r.errors)
  } catch (e) {
    showToast(e.message || '导入失败')
  } finally {
    importing.value = false
  }
}

onMounted(loadList)
</script>

<style scoped>
.kv-page { display: flex; flex-direction: column; height: calc(100vh - 44px); padding: 18px 22px 0; }
.kv-top { flex-shrink: 0; position: sticky; top: 0; z-index: 10; background: var(--sx-bg-page); padding-bottom: 12px; }
.kv-body { flex: 1; min-height: 0; overflow-y: auto; padding-bottom: 60px; }
.kv-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; flex-wrap: wrap; margin-bottom: 14px; }
.kv-title { display: flex; gap: 12px; align-items: center; color: var(--sx-accent); }
.kv-title h1 { margin: 0; font-size: 20px; color: var(--sx-text-strong); }
.kv-sub { margin: 2px 0 0; font-size: 13px; color: var(--sx-text); }
.kv-actions { display: flex; gap: 8px; flex-wrap: wrap; }
.kv-filters { display: flex; gap: 10px; align-items: center; margin: 0; flex-wrap: wrap; }
.kv-filters .sel, .kv-filters .inp { padding: 8px 10px; border: 1px solid var(--sx-border); border-radius: 9px; background: var(--sx-bg-surface); color: var(--sx-text-strong); font-size: 14px; }
.kv-filters .sel { width: 120px; flex-shrink: 0; }
.kv-filters .inp { width: 260px; flex-shrink: 0; }
.sel-hint { font-size: 13px; color: var(--sx-text); margin-left: auto; }
.kv-mbar { display: flex; align-items: center; gap: 14px; background: var(--sx-bg-surface-2); border: 1px solid var(--sx-border); border-radius: 10px; padding: 8px 14px; margin-bottom: 10px; }
.chk { display: flex; align-items: center; gap: 6px; font-size: 14px; color: var(--sx-text-strong); }
.kv-list { overflow-x: auto; }
.kv-table { width: 100%; min-width: 1100px; border-collapse: collapse; background: var(--sx-bg-surface); border: 1px solid var(--sx-border); border-radius: 12px; overflow: hidden; table-layout: fixed; }
.kv-table th, .kv-table td { padding: 10px 12px; text-align: left; border-bottom: 1px solid var(--sx-border-faint); font-size: 13px; vertical-align: top; overflow: hidden; color: var(--sx-text-strong); }
.kv-table th { background: var(--sx-bg-surface-2); color: var(--sx-text-emphasis); font-weight: 600; }
.kv-table tr:hover { background: var(--sx-row-hover); }
.row-sel { background: var(--sx-row-selected-bg) !important; }
.col-sel { width: 36px; text-align: center; }
.cell-name { width: 16%; }
.cell-name .nm { font-weight: 600; color: var(--sx-text-strong); }
.cell-provider { width: 10%; }
.cell-cat { width: 90px; }
.cell-addr { width: 28%; color: var(--sx-text); vertical-align: middle; }
.cell-addr .cell-inner { display: flex; align-items: center; gap: 6px; }
.cell-addr .url-text { flex: 1; min-width: 0; word-break: break-all; overflow-wrap: anywhere; }
.cell-key { width: 15%; white-space: nowrap; vertical-align: middle; }
.cell-key .cell-inner { display: flex; align-items: center; gap: 6px; }
.cell-key .key-mask { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; }
.mini.copy-end { flex-shrink: 0; margin-left: 0; }
.cell-account { width: 12%; }
.cell-dev { width: 110px; white-space: nowrap; vertical-align: middle; }
.cell-dev .cell-inner { display: flex; align-items: center; gap: 6px; }
.cell-dev .link { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; }
.cell-ops { width: 110px; white-space: nowrap; }
.key-mask { font-family: ui-monospace, Menlo, Consolas, monospace; color: var(--sx-text); }
.mini { margin-left: 6px; padding: 2px 7px; border: 1px solid var(--sx-border-strong); border-radius: 6px; background: var(--sx-bg-surface); cursor: pointer; font-size: 11px; color: var(--sx-text); }
.mini:hover { background: var(--sx-row-hover); }
.pill { display: inline-block; padding: 2px 9px; border-radius: 999px; background: var(--sx-tag-info-bg); color: var(--sx-tag-info-text); border: 1px solid var(--sx-tag-info-border); font-size: 12px; }
.cell-ops { white-space: nowrap; }
.op { padding: 4px 10px; border: 1px solid var(--sx-border-strong); border-radius: 7px; background: var(--sx-bg-surface); cursor: pointer; font-size: 12px; margin-right: 4px; color: var(--sx-text-strong); }
.op:hover { background: var(--sx-row-hover); }
.op.danger:hover { background: #c94242; border-color: #c94242; color: #fff; }
.kv-empty { text-align: center; padding: 60px 20px; color: var(--sx-text-muted); }
.kv-empty p { margin-bottom: 14px; }

/* 弹窗 */
.modal-mask { position: fixed; inset: 0; background: var(--sx-overlay); display: flex; align-items: center; justify-content: center; z-index: 50; padding: 20px; }
.modal { background: var(--sx-bg-elevated); border-radius: 14px; width: 460px; max-width: 100%; max-height: 90vh; overflow: auto; box-shadow: var(--sx-shadow-pop); color: var(--sx-text-strong); }
.modal.wide { width: 720px; }
.modal-head { display: flex; align-items: center; justify-content: space-between; padding: 16px 20px; border-bottom: 1px solid var(--sx-border); }
.modal-head h2 { margin: 0; font-size: 17px; color: var(--sx-text-strong); }
.x { border: none; background: transparent; font-size: 18px; cursor: pointer; color: var(--sx-text-muted); }
.x:hover { color: var(--sx-accent-strong); }
.modal-body { padding: 18px 20px; }
.modal-body.grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 12px 16px; }
.fld { display: flex; flex-direction: column; gap: 6px; font-size: 13px; color: var(--sx-text-emphasis); }
.fld span { font-weight: 600; }
.fld.span2 { grid-column: 1 / -1; }
.modal-body .inp, .modal-body .sel { width: 100%; box-sizing: border-box; padding: 10px 12px; border: 1.5px solid var(--sx-border-input); border-radius: 10px; background: var(--sx-bg-surface-2); color: var(--sx-text-strong); font-size: 14px; transition: border-color .15s, background .15s, box-shadow .15s; }
.modal-body .inp:focus, .modal-body .sel:focus { outline: none; border-color: var(--sx-accent); background: var(--sx-bg-surface); box-shadow: 0 0 0 3px var(--sx-accent-soft); }
.pw-row { position: relative; display: flex; align-items: center; }
.pw-row .inp { width: 100%; padding-right: 38px; }
.pw-eye {
  position: absolute; right: 8px; top: 50%; transform: translateY(-50%);
  width: 26px !important; height: 26px !important;
  border: none; background: transparent; cursor: pointer;
  display: flex !important; align-items: center; justify-content: center;
  padding: 0 !important; border-radius: 6px;
  color: var(--sx-text-muted);
}
.pw-eye svg { display: block; }
.pw-eye:hover { color: var(--sx-accent-strong); }
.link { color: var(--sx-link); text-decoration: none; font-weight: 600; }
.link:hover { text-decoration: underline; }
.kv-hint { font-size: 12px; color: var(--sx-text); margin: 0 0 12px; line-height: 1.6; }
.kv-fname { font-size: 12px; color: var(--sx-text-muted); margin-left: 8px; }
.modal-foot { display: flex; justify-content: flex-end; gap: 10px; padding: 14px 20px; border-top: 1px solid var(--sx-border); }

/* 按钮 */
.btn { display: inline-flex; align-items: center; gap: 6px; padding: 8px 14px; border-radius: 9px; border: 1px solid var(--sx-border-strong); background: var(--sx-bg-surface); color: var(--sx-text-strong); cursor: pointer; font-size: 14px; transition: background .15s, border-color .15s, color .15s; }
.btn:hover { background: var(--sx-row-hover); }
.btn.primary { background: var(--sx-accent); border-color: var(--sx-accent); color: #fff; }
.btn.primary:hover { background: var(--sx-accent-hover); border-color: var(--sx-accent-hover); }
.btn.ghost { background: var(--sx-bg-surface); }
.btn.ghost.active { background: var(--sx-accent-soft); border-color: var(--sx-accent); color: var(--sx-accent-strong); }
.btn.danger { background: #d4453b; border-color: #d4453b; color: #fff; }
.btn.danger:hover { background: #c0392b; border-color: #c0392b; }
.btn.sm { padding: 6px 10px; font-size: 13px; }
.btn:disabled { opacity: .5; cursor: not-allowed; }
.toast { position: fixed; bottom: 28px; left: 50%; transform: translateX(-50%); background: var(--sx-toast-bg); color: var(--sx-toast-text); padding: 10px 18px; border-radius: 10px; z-index: 80; font-size: 14px; box-shadow: var(--sx-shadow-pop); }
</style>
