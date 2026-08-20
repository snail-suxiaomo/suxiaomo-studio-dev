<template>
  <div class="page">
    <header class="page-head">
      <div>
        <h1 class="title">日志查看</h1>
        <p class="subtitle">只记录报错（后端 / 前端 / 桌面启动），点进来即可看最新，复制发我即可定位问题。</p>
      </div>
      <div class="head-actions">
        <label class="switch">
          <input type="checkbox" v-model="autoRefresh" />
          <span>自动刷新</span>
        </label>
        <button class="btn ghost" @click="load" :disabled="loading">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M23 4v6h-6" /><path d="M1 20v-6h6" /><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" /></svg>
          刷新
        </button>
      </div>
    </header>

    <!-- 筛选条 -->
    <div class="toolbar">
      <div class="filters">
        <button
          v-for="f in filters"
          :key="f.value"
          class="chip"
          :class="{ active: source === f.value }"
          @click="source = f.value; load()"
        >{{ f.label }}</button>
      </div>
      <div class="stats">
        <span class="count">共 {{ lines.length }} 条</span>
        <button class="btn ghost" @click="copyAll" :disabled="!lines.length">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2" /><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" /></svg>
          复制全部
        </button>
        <button class="btn ghost" @click="exportTxt" :disabled="!lines.length">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="7 10 12 15 17 10" /><line x1="12" y1="15" x2="12" y2="3" /></svg>
          导出 txt
        </button>
        <button class="btn danger" @click="clearLogs" :disabled="!lines.length">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6" /><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" /></svg>
          清空
        </button>
      </div>
    </div>

    <!-- 日志区 -->
    <div class="log-box" ref="logBox">
      <div v-if="loading" class="empty">读取中…</div>
      <div v-else-if="!lines.length" class="empty">
        暂无报错日志。遇到问题时，错误会自动出现在这里，复制发给我即可。
      </div>
      <div
        v-for="(row, i) in lines"
        :key="i"
        class="log-row"
      >
        <span class="badge" :class="'badge-' + row.source">{{ sourceLabel(row.source) }}</span>
        <pre class="log-text">{{ row.text }}</pre>
        <button
          class="btn icon copy-btn"
          title="复制该条"
          @click="copyRow(row)"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2" /><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" /></svg>
        </button>
      </div>
    </div>

    <Teleport to="body">
      <div v-if="toast" class="log-toast">{{ toast }}</div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { api } from '../common/http.js'
import { confirm, alert } from '../common/useConfirm.js'

const filters = [
  { label: '全部', value: 'all' },
  { label: '后端', value: 'backend' },
  { label: '前端', value: 'frontend' },
  { label: '启动', value: 'electron' },
]

const source = ref('all')
const lines = ref([])
const loading = ref(false)
const autoRefresh = ref(true)
const logBox = ref(null)
const toast = ref('')
let timer = null
let toastTimer = null

function sourceLabel(s) {
  return { backend: '后端', frontend: '前端', electron: '启动' }[s] || s
}

async function load() {
  loading.value = true
  try {
    const data = await api(`/logs?source=${source.value}&lines=500`)
    lines.value = data.lines || []
    await nextTick()
    if (logBox.value) logBox.value.scrollTop = 0
  } catch (e) {
    // 读取失败不阻塞页面（已经有全局错误上报）
  } finally {
    loading.value = false
  }
}

function allText() {
  return lines.value.map((r) => `[${sourceLabel(r.source)}] ${r.text}`).join('\n\n')
}

function rowText(row) {
  return `[${sourceLabel(row.source)}] ${row.text}`
}

function showToast(msg) {
  toast.value = msg
  if (toastTimer) clearTimeout(toastTimer)
  toastTimer = setTimeout(() => (toast.value = ''), 1800)
}

async function copyToClipboard(text) {
  // 1. 优先用现代 Clipboard API
  if (navigator.clipboard && window.isSecureContext) {
    try {
      await navigator.clipboard.writeText(text)
      return true
    } catch (e) {
      // 降级
    }
  }
  // 2. 降级：execCommand（兼容桌面版 / 未聚焦等情况）
  const ta = document.createElement('textarea')
  ta.value = text
  ta.setAttribute('readonly', '')
  ta.style.cssText = 'position:fixed;left:-9999px;top:-9999px;opacity:0;'
  document.body.appendChild(ta)
  ta.focus()
  ta.setSelectionRange(0, text.length)
  let ok = false
  try {
    ok = document.execCommand('copy')
  } catch (e) {
    ok = false
  }
  document.body.removeChild(ta)
  return ok
}

async function copyAll() {
  const ok = await copyToClipboard(allText())
  showToast(ok ? '已复制全部日志' : '复制失败，请手动选择文本复制')
}

async function copyRow(row) {
  const ok = await copyToClipboard(rowText(row))
  showToast(ok ? '已复制该条日志' : '复制失败，请手动选择文本复制')
}

function exportTxt() {
  const blob = new Blob([allText()], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  const ts = new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-')
  a.href = url
  a.download = `suxiaomo-logs-${ts}.txt`
  a.click()
  URL.revokeObjectURL(url)
}

async function clearLogs() {
  if (!(await confirm('确定清空日志？此操作不可恢复（仅清空本地日志文件）。', { title: '清空确认' }))) return
  try {
    await api(`/logs?source=${source.value}`, 'DELETE')
    lines.value = []
  } catch (e) {
    await alert('清空失败：' + (e.message || e))
  }
}

onMounted(() => {
  load()
  if (autoRefresh.value) startTimer()
})

function startTimer() {
  stopTimer()
  timer = setInterval(() => {
    if (autoRefresh.value && document.visibilityState === 'visible') load()
  }, 15000)
}
function stopTimer() {
  if (timer) clearInterval(timer)
  timer = null
}

// 自动刷新开关变化即同步定时器
import { watch } from 'vue'
watch(autoRefresh, (v) => (v ? startTimer() : stopTimer()))

onBeforeUnmount(stopTimer)
</script>

<style scoped>
.page {
  width: 100%;
  max-width: none;
  margin: 0;
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.page-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}
.title {
  margin: 0;
  font-size: 22px;
  font-weight: 700;
  color: var(--ink);
}
.subtitle {
  margin: 6px 0 0;
  font-size: 13px;
  color: var(--ink2);
  max-width: 640px;
  line-height: 1.5;
}
.head-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}
.switch {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--ink2);
  cursor: pointer;
  user-select: none;
}
.switch input {
  width: 16px;
  height: 16px;
  accent-color: var(--brand1);
}

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  background: #fff;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 10px 12px;
  box-shadow: var(--shadow-card);
}
.filters {
  display: flex;
  gap: 8px;
}
.chip {
  padding: 6px 14px;
  border-radius: 999px;
  border: 1px solid var(--line-strong);
  background: var(--field);
  color: var(--ink2);
  font-size: 13px;
  cursor: pointer;
  transition: .15s;
}
.chip:hover {
  border-color: var(--brand1);
  color: var(--brand1);
}
.chip.active {
  background: var(--grad);
  color: #fff;
  border-color: transparent;
  box-shadow: var(--shadow-btn);
}
.stats {
  display: flex;
  align-items: center;
  gap: 8px;
}
.count {
  font-size: 12px;
  color: var(--muted);
  margin-right: 4px;
}

.btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 7px 12px;
  font-size: 13px;
  border-radius: 9px;
  cursor: pointer;
  border: 1px solid var(--line-strong);
  background: #fff;
  color: var(--ink2);
  transition: .15s;
}
.btn:hover:not(:disabled) {
  border-color: var(--brand1);
  color: var(--brand1);
}
.btn:disabled {
  opacity: .5;
  cursor: not-allowed;
}
.btn.ghost {
  background: var(--field);
}
.btn.danger:hover:not(:disabled) {
  border-color: #e25757;
  color: #e25757;
  background: #fff5f5;
}

.log-box {
  background: #1b1f2e;
  border-radius: var(--radius-lg);
  padding: 14px 16px;
  flex: 1;
  min-height: 0;
  overflow: auto;
  box-shadow: var(--shadow-card);
}
.empty {
  color: #a0a8c0;
  font-size: 13px;
  padding: 40px 10px;
  text-align: center;
  line-height: 1.7;
}
.log-row {
  display: flex;
  gap: 10px;
  padding: 10px 0;
  border-bottom: 1px solid rgba(255, 255, 255, .08);
  align-items: flex-start;
  position: relative;
}
.log-row:last-child {
  border-bottom: none;
}
.log-row:hover {
  background: rgba(255, 255, 255, .03);
  border-radius: 6px;
  margin: 0 -6px;
  padding-left: 6px;
  padding-right: 6px;
}
.badge {
  flex-shrink: 0;
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 6px;
  margin-top: 2px;
  color: #fff !important;
}
.badge-backend { background: #e25757 !important; }
.badge-frontend { background: #4f7cff !important; }
.badge-electron { background: #f59e0b !important; }
.log-text {
  margin: 0;
  font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
  font-size: 13px;
  line-height: 1.6;
  color: #f0f4ff;
  white-space: pre-wrap;
  word-break: break-all;
  flex: 1;
  /* 覆盖全局 pre 的浅色背景 */
  background: transparent !important;
  border: none !important;
  border-radius: 0 !important;
  padding: 0 !important;
}
.btn.icon {
  padding: 5px;
  border-radius: 6px;
  min-width: 28px;
  min-height: 28px;
  justify-content: center;
}
.copy-btn {
  opacity: .35;
  color: #c9d0e6;
  background: rgba(255, 255, 255, .08);
  border-color: rgba(255, 255, 255, .12);
  transition: .15s;
}
.log-row:hover .copy-btn,
.copy-btn:active {
  opacity: 1;
}
.copy-btn:hover {
  color: #fff;
  background: rgba(255, 255, 255, .18);
  border-color: rgba(255, 255, 255, .25);
}
.log-toast {
  position: fixed;
  left: 50%;
  bottom: 40px;
  transform: translateX(-50%);
  background: rgba(30, 34, 50, .95);
  color: #fff;
  padding: 9px 18px;
  border-radius: 999px;
  font-size: 13px;
  box-shadow: 0 6px 24px rgba(0, 0, 0, .25);
  z-index: 9999;
  pointer-events: none;
}

@media (max-width: 640px) {
  .copy-btn {
    opacity: .8;
  }
  .log-row:hover {
    margin: 0;
    padding-left: 0;
    padding-right: 0;
  }
}
</style>
