<template>
  <div class="page dt-page">
    <div class="dt-toolbar">
      <div class="dt-title">
        <div class="dt-title-main">
          <span class="dt-emoji">🗓️</span>
          <h2>每日任务</h2>
        </div>
        <p class="dt-sub">今日：{{ todayISO() }} · 点击切换完成状态，隔日自动重置</p>
      </div>
      <div class="dt-actions">
        <input v-model="filters.keyword" class="dt-search" placeholder="搜索名称 / 详情 / 软件 / 必做…" @input="loadList" />
        <input v-model="filters.owner" class="dt-search narrow" placeholder="所属用户筛选" @input="loadList" />
        <button v-if="pausedTotal" class="dt-paused-entry" @click="enterPaused">⏸ 已暂停 {{ pausedTotal }} 个 · 点击恢复</button>
        <button class="dt-add" @click="openCreate">+ 新增任务</button>
      </div>
    </div>

    <div v-if="view === 'active' && (list.length || pausedTotal)" class="dt-summary">
      <div class="dt-stat">
        <span class="dt-stat-num">{{ list.length }}</span>
        <span class="dt-stat-label">总任务</span>
      </div>
      <div class="dt-stat done">
        <span class="dt-stat-num">{{ doneCount }}</span>
        <span class="dt-stat-label">已完成</span>
      </div>
      <div class="dt-stat overdue" v-if="overdueCount">
        <span class="dt-stat-num">{{ overdueCount }}</span>
        <span class="dt-stat-label">已截止</span>
      </div>
      <div class="dt-stat pending">
        <span class="dt-stat-num">{{ pendingCount }}</span>
        <span class="dt-stat-label">未完成</span>
      </div>
      <div class="dt-summary-actions">
        <button class="dt-bulk" @click="completeAll">全部完成</button>
        <button class="dt-bulk ghost" @click="resetToday">重置今日</button>
      </div>
    </div>
    <div v-else-if="view === 'paused'" class="dt-summary paused-bar">
      <button class="dt-bulk" @click="enterActive">← 返回进行中</button>
      <span class="dt-sub">已暂停的任务不展示、不提醒，可随时恢复后继续</span>
    </div>

    <div class="dt-scroll">
      <div v-if="list.length" class="dt-grid">
        <article v-for="(it, idx) in list" :key="it.id" class="dt-card"
          :class="{ dragging: dragIndex === idx, 'drag-over': dragOverIndex === idx }"
          @dragenter.prevent="onDragEnter(idx)"
          @dragover.prevent="onDragOver($event)"
          @drop.prevent="onDrop(idx)"
          @dragend="onDragEnd">
          <div class="dt-card-head">
            <div class="dt-card-name"><span v-if="view === 'active'" class="dt-handle" title="拖拽排序" draggable="true" @dragstart="onDragStart(idx, $event)">⠿</span>{{ it.name }}</div>
            <button
              class="dt-toggle"
              draggable="false"
              :class="statusOf(it)"
              @click.stop="it.status === 'paused' ? resume(it) : toggle(it)"
            >{{ statusLabel(statusOf(it)) }}</button>
          </div>

          <div class="dt-card-meta" v-if="it.software">
            <span class="dt-meta-soft">📱 {{ it.software }}</span>
          </div>

          <div class="dt-card-summary" v-if="it.detail"><span class="dt-sum-tag">📝</span>{{ it.detail }}</div>

          <div class="dt-card-must" v-if="it.must_do">📌 必做：{{ it.must_do }}</div>

          <div class="dt-card-points" v-if="it.points">
            <span class="dt-pt-num">+{{ it.points }} 积分</span>
            <span class="dt-pt-mode" :class="it.points_mode === 'daily' ? 'daily' : 'cum'">
              {{ it.points_mode === 'daily' ? '每日清空' : '累加永久' }}
            </span>
          </div>

          <div class="dt-card-deadline" :class="deadlineClass(it)">
            ⏰
            <template v-if="it.task_date && dlParts(it)">
              <span>{{ dlParts(it).prefix }}</span>
              <b class="dt-dl-num" v-if="dlParts(it).num">{{ dlParts(it).num }}</b>
              <span>{{ dlParts(it).suffix }}</span>
            </template>
            <span v-else>长期有效</span>
          </div>

          <div class="dt-card-ops" @click.stop>
            <button class="dt-op" draggable="false" @click="openView(it)">查看</button>
            <button class="dt-op" draggable="false" @click="openEdit(it)">编辑</button>
            <button class="dt-op warn" v-if="it.status !== 'paused'" draggable="false" @click="pause(it)">暂停</button>
            <button class="dt-op ok" v-else draggable="false" @click="resume(it)">恢复</button>
            <button class="dt-op danger" draggable="false" @click="remove(it)">删除</button>
          </div>
        </article>
      </div>
      <div v-else class="dt-empty">
        <template v-if="view === 'paused'">暂无已暂停任务</template>
        <template v-else-if="filters.keyword || filters.owner">没有匹配的任务</template>
        <template v-else>暂无每日任务，点击右上角「+ 新增任务」开始吧</template>
      </div>
    </div>

    <!-- 新增 / 编辑 弹窗 -->
    <div class="dt-mask" v-if="showForm" @mousedown="onMaskMouseDown" @click="onMaskClick($event, closeForm)">
      <div class="dt-modal">
        <div class="dt-modal-head">
          <h3>{{ form.id ? '编辑任务' : '新增任务' }}</h3>
          <button class="dt-close" @click="closeForm">×</button>
        </div>
        <div class="dt-modal-body">
          <div class="fld">
            <label>名称 <span class="req">*</span></label>
            <input v-model="form.name" placeholder="如：即梦每日签到" />
          </div>
          <div class="fld-row">
            <div class="fld">
              <label>所属用户</label>
              <input v-model="form.owner" placeholder="如：苏小沫" />
            </div>
            <div class="fld">
              <label>操作软件</label>
              <input v-model="form.software" placeholder="如：谷歌浏览器/workbuddy桌面版" />
            </div>
          </div>
          <div class="fld">
            <label>任务摘要</label>
            <input v-model="form.detail" placeholder="默认：每日签到领积分" />
          </div>
          <div class="fld">
            <label>主体账号</label>
            <input v-model="form.login_account" placeholder="手机号/邮箱" />
          </div>
          <div class="fld">
            <label>其他账号（可多个，手机号 / 邮箱）</label>
            <div class="acc-edit">
              <div class="acc-item" v-for="(a, i) in form.operation_accounts" :key="i">
                <input v-model="form.operation_accounts[i]" placeholder="手机号 / 邮箱" />
                <button class="acc-del" @click="form.operation_accounts.splice(i, 1)">×</button>
              </div>
              <button class="acc-add" @click="form.operation_accounts.push('')">+ 添加一个账号</button>
            </div>
          </div>
          <div class="fld">
            <label>必做事情</label>
            <input v-model="form.must_do" placeholder="如：制作 1 个视频消耗今日免费积分" />
          </div>
          <div class="fld">
            <label>网站链接</label>
            <input v-model="form.link" placeholder="如：https://www.douyin.com/user/xxx" />
          </div>
          <div class="fld">
            <label>截止日期（选填，留空表示长期有效）</label>
            <input type="date" v-model="form.task_date" />
          </div>
          <div class="fld-row">
            <div class="fld">
              <label>积分数量</label>
              <input type="number" min="0" step="1" v-model.number="form.points" placeholder="0" />
            </div>
            <div class="fld">
              <label>积分清零方式</label>
              <select v-model="form.points_mode">
                <option value="cumulative">累加 · 永久可用</option>
                <option value="daily">每日领取 · 当日清空</option>
              </select>
            </div>
          </div>
        </div>
        <div class="dt-modal-foot">
          <button class="dt-cancel" @click="closeForm">取消</button>
          <button class="dt-save" @click="save">保存</button>
        </div>
      </div>
    </div>

    <!-- 查看 弹窗 -->
    <div class="dt-mask" v-if="viewItem" @mousedown="onMaskMouseDown" @click="onMaskClick($event, () => viewItem = null)">
      <div class="dt-modal">
          <div class="dt-modal-head">
            <h3>任务详情</h3>
            <button class="dt-close" @click="viewItem = null">×</button>
          </div>
        <div class="dt-modal-body">
          <div class="dt-view-grid">
            <div class="dt-view-cell"><span class="vk">名称</span><span class="vv">{{ viewItem.name }}</span></div>
            <div class="dt-view-cell"><span class="vk">操作软件</span><span class="vv">{{ viewItem.software || '—' }}</span></div>
            <div class="dt-view-cell"><span class="vk">任务摘要</span><span class="vv">{{ viewItem.detail }}</span></div>
            <div class="dt-view-cell">
              <span class="vk">主体账号</span>
              <div class="dt-copy-row">
                <span class="vv">{{ viewItem.login_account || '—' }}</span>
                <button v-if="viewItem.login_account" class="dt-copy mini" @click="copyText(viewItem.login_account)">复制</button>
              </div>
            </div>
            <div class="dt-view-cell"><span class="vk">日期</span><span class="vv">今日 {{ todayISO() }}</span></div>
            <div class="dt-view-cell"><span class="vk">今日完成</span><span class="vv">
              <span class="badge" :class="viewItem.completed_today ? 'ok' : 'warn'">{{ viewItem.completed_today ? '已完成' : '未完成' }}</span>
            </span></div>
            <div class="dt-view-cell"><span class="vk">截止日期</span><span class="vv">{{ viewItem.task_date ? deadlineRelative(viewItem.task_date) : '长期有效' }}</span></div>
            <div class="dt-view-cell"><span class="vk">积分</span>            <span class="vv">
              <template v-if="viewItem.points">+{{ viewItem.points }} ·
                <span class="dt-view-pt-mode" :class="viewItem.points_mode === 'daily' ? 'daily' : 'cum'">
                  {{ viewItem.points_mode === 'daily' ? '每日清空' : '累加永久' }}
                </span>
              </template>
              <template v-else>—</template>
            </span></div>
          </div>
          <div class="dt-view-accs">
            <div class="vk">其他账号（{{ viewItem.operation_accounts.length }}）</div>
            <div class="dt-accs">
              <span v-for="(a, i) in viewItem.operation_accounts" :key="i" class="dt-acc clickable" title="点击复制" @click="copyText(a)">{{ a }}</span>
              <span v-if="!viewItem.operation_accounts.length" class="dt-muted">—</span>
            </div>
          </div>
          <div class="dt-view-must">
            <div class="vk">必做事情</div>
            <div class="dt-must-body">{{ viewItem.must_do || '—' }}</div>
          </div>
          <div v-if="viewItem.link" class="dt-view-link">
            <div class="vk">网站链接</div>
            <div class="dt-link-row">
              <a :href="safeUrl(viewItem.link)" target="_blank" rel="noopener" class="dt-linkout">{{ viewItem.link }}</a>
              <button class="dt-copy" @click="copyText(viewItem.link)">复制链接</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { api } from '../common/http.js'
import { confirm, alert } from '../common/useConfirm.js'

const list = ref([])
const filters = reactive({ keyword: '', owner: '' })
const view = ref('active') // active | paused
const pausedTotal = ref(0)
const showForm = ref(false)
const viewItem = ref(null)
const dragIndex = ref(-1)
const dragOverIndex = ref(-1)
const loadedDate = ref(todayISO()) // 当前已加载数据对应的日期，用于跨天自动重置检测
let dayCheckTimer = null

// 状态枚举：done 已完成 / overdue 已截止（逾期且未完成）/ paused 已暂停 / pending 未完成
function statusOf(it) {
  if (it.status === 'paused') return 'paused'
  if (it.completed_today) return 'done'
  if (it.task_date && it.task_date < todayISO()) return 'overdue'
  return 'pending'
}
function statusLabel(s) {
  if (s === 'done') return '已完成'
  if (s === 'overdue') return '已截止'
  if (s === 'paused') return '已暂停'
  return '未完成'
}
const doneCount = computed(() => list.value.filter((i) => i.completed_today).length)
const overdueCount = computed(() =>
  list.value.filter((i) => !i.completed_today && i.task_date && i.task_date < todayISO()).length
)
const pendingCount = computed(() => list.value.length - doneCount.value - overdueCount.value)

// 截止日期相对化：今天截止 / 还剩 N 天 / 已逾期 N 天
function dayDiff(a, b) {
  const da = new Date(a + 'T00:00:00')
  const db = new Date(b + 'T00:00:00')
  return Math.round((db - da) / 86400000)
}
function deadlineRelative(dateStr) {
  if (!dateStr) return ''
  const today = todayISO()
  if (dateStr === today) return '今天截止'
  const diff = dayDiff(dateStr, today) // = 今天 - 截止日（正=已过期）
  if (diff > 0) return `已逾期 ${diff} 天`
  return `还剩 ${-diff} 天`
}
// 截止日期拆分：prefix / 数字(num) / suffix，方便给数字单独上色
function dlParts(it) {
  if (!it.task_date) return null
  const today = todayISO()
  if (it.task_date === today) return { prefix: '今天截止', num: '', suffix: '' }
  const diff = dayDiff(it.task_date, today) // = 今天 - 截止日（正=已过期）
  if (diff > 0) return { prefix: '已逾期 ', num: String(diff), suffix: ' 天' }
  return { prefix: '还剩 ', num: String(-diff), suffix: ' 天' }
}
function deadlineClass(it) {
  if (!it.task_date) return ''
  if (it.task_date === todayISO()) return 'today'
  if (it.task_date < todayISO()) return 'expired'
  return ''
}

// 避免拖拽/选中文本时误关弹窗：只有 mousedown 也在遮罩上，click 才关闭
const maskMouseDownInside = ref(false)
function onMaskMouseDown(e) {
  // 如果按下的目标是遮罩本身，说明后续 click 可以关闭；否则标记为在弹窗内部按下
  maskMouseDownInside.value = !e.target.classList.contains('dt-mask')
}
function onMaskClick(e, closeFn) {
  if (e.target.classList.contains('dt-mask') && !maskMouseDownInside.value) {
    closeFn()
  }
}

function todayISO() {
  const d = new Date()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${d.getFullYear()}-${m}-${day}`
}

function blankForm() {
  return {
    id: null,
    name: '',
    owner: '',
    software: '',
    detail: '每日签到领积分',
    login_account: '',
    operation_accounts: [''],
    must_do: '',
    link: '',
    points: 0,
    points_mode: 'cumulative',
    task_date: '',
  }
}
const form = reactive(blankForm())

async function loadList() {
  try {
    const q = [`status=${view.value}`]
    if (filters.keyword) q.push(`keyword=${encodeURIComponent(filters.keyword)}`)
    if (filters.owner) q.push(`owner=${encodeURIComponent(filters.owner)}`)
    const data = await api(`/daily-tasks/list${q.length ? '?' + q.join('&') : ''}`)
    list.value = data
    loadedDate.value = todayISO()
    refreshPausedCount()
  } catch (e) {
    console.error('[DailyTasks] loadList failed', e)
  }
}

async function enterPaused() {
  view.value = 'paused'
  filters.keyword = ''
  filters.owner = ''
  await loadList()
}

async function enterActive() {
  view.value = 'active'
  await loadList()
}

async function refreshPausedCount() {
  try {
    const data = await api('/daily-tasks/list?status=paused')
    pausedTotal.value = data.length
  } catch (e) {
    console.error('[DailyTasks] refreshPausedCount failed', e)
  }
}

function openCreate() {
  Object.assign(form, blankForm())
  showForm.value = true
}

function openEdit(it) {
  Object.assign(form, {
    id: it.id,
    name: it.name,
    owner: it.owner || '',
    software: it.software || '',
    detail: it.detail,
    login_account: it.login_account || '',
    operation_accounts: it.operation_accounts.length ? [...it.operation_accounts] : [''],
    must_do: it.must_do || '',
    link: it.link || '',
    points: Number(it.points) || 0,
    points_mode: it.points_mode || 'cumulative',
    task_date: it.task_date || '',
  })
  showForm.value = true
}

function closeForm() {
  showForm.value = false
}

function openView(it) {
  viewItem.value = it
}

async function save() {
  const payload = {
    name: form.name.trim(),
    owner: form.owner.trim(),
    software: form.software.trim(),
    detail: form.detail.trim() || '每日签到领积分',
    login_account: form.login_account.trim(),
    operation_accounts: form.operation_accounts.map((x) => x.trim()).filter(Boolean),
    must_do: form.must_do.trim(),
    link: form.link.trim(),
    points: Number(form.points) || 0,
    points_mode: form.points_mode || 'cumulative',
    task_date: form.task_date.trim(),
  }
    try {
    if (form.id) {
      await api(`/daily-tasks/${form.id}`, 'PUT', payload)
    } else {
      await api('/daily-tasks/', 'POST', payload)
    }
    closeForm()
    if (view.value === 'paused') view.value = 'active'
    await loadList()
  } catch (e) {
    console.error('[DailyTasks] save failed', e)
    window.lastSaveError = e
    await alert('保存失败：' + (e.message || '未知错误'))
  }
}

async function toggle(it) {
  try {
    const next = !it.completed_today
    await api(`/daily-tasks/${it.id}/toggle`, 'POST', { done: next })
    it.completed_today = next
  } catch (e) {
    console.error('[DailyTasks] toggle failed', e)
    await alert('切换失败：' + (e.message || '未知错误'))
  }
}

// 一键批量：全部完成（今天）/ 重置今日
async function completeAll() {
  try {
    await api('/daily-tasks/bulk', 'POST', { action: 'complete_all' })
    await loadList()
  } catch (e) {
    console.error('[DailyTasks] completeAll failed', e)
    await alert('操作失败：' + (e.message || '未知错误'))
  }
}
async function resetToday() {
  try {
    await api('/daily-tasks/bulk', 'POST', { action: 'reset_today' })
    await loadList()
  } catch (e) {
    console.error('[DailyTasks] resetToday failed', e)
    await alert('操作失败：' + (e.message || '未知错误'))
  }
}

async function pause(it) {
  let ok = false
  try {
    ok = await confirm(`确定暂停任务「${it.name}」吗？\n暂停后任务会隐藏，可在工具栏「已暂停」入口恢复。`, { title: '暂停确认' })
  } catch (e) {
    console.error('[DailyTasks] confirm failed', e)
    return
  }
  if (!ok) return
  try {
    await api('/daily-tasks/pause', 'POST', { id: it.id })
    await loadList()
  } catch (e) {
    console.error('[DailyTasks] pause failed', e)
    await alert('暂停失败：' + (e.message || '未知错误'))
  }
}

async function resume(it) {
  try {
    await api('/daily-tasks/resume', 'POST', { id: it.id })
    await loadList()
  } catch (e) {
    console.error('[DailyTasks] resume failed', e)
    await alert('恢复失败：' + (e.message || '未知错误'))
  }
}

async function remove(it) {
  let ok = false
  try {
    ok = await confirm(`确认删除任务「${it.name}」？`, { title: '删除确认' })
  } catch (e) {
    console.error('[DailyTasks] confirm failed', e)
    return
  }
  if (!ok) return
  try {
    await api(`/daily-tasks/${it.id}`, 'DELETE')
    await loadList()
  } catch (e) {
    console.error('[DailyTasks] delete failed', e)
    await alert('删除失败：' + (e.message || '未知错误'))
  }
}

async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text)
    await alert('已复制')
  } catch (e) {
    // 兜底：旧浏览器 / 非安全上下文
    const ta = document.createElement('textarea')
    ta.value = text
    document.body.appendChild(ta)
    ta.select()
    try { document.execCommand('copy') } catch (_) {}
    document.body.removeChild(ta)
    await alert('已复制')
  }
}

function safeUrl(u) {
  const s = String(u || '').trim()
  if (/^https?:\/\//i.test(s)) return s
  if (/^[\w.-]+\.[a-z]{2,}/i.test(s)) return 'https://' + s
  return '#'
}

function shortUrl(u) {
  const s = String(u || '').trim()
  return s.replace(/^https?:\/\//i, '').replace(/\/$/, '')
}

onMounted(() => {
  loadList()
  // 跨天自动重置：桌面版常驻时，若本地日期已变更则重新拉取，完成态按新日期归零
  dayCheckTimer = setInterval(() => {
    const t = todayISO()
    if (t !== loadedDate.value) {
      loadedDate.value = t
      loadList()
    }
  }, 60 * 1000)
})
onUnmounted(() => {
  if (dayCheckTimer) clearInterval(dayCheckTimer)
})

// —— 拖拽排序 ——
function onDragStart(idx, e) {
  dragIndex.value = idx
  e.dataTransfer.effectAllowed = 'move'
  e.dataTransfer.setData('text/plain', String(idx))
}
function onDragEnter(idx) {
  dragOverIndex.value = idx
}
function onDragOver(e) {
  e.dataTransfer.dropEffect = 'move'
}
function onDrop(idx) {
  const from = dragIndex.value
  if (from < 0 || from === idx) { resetDrag(); return }
  const arr = list.value
  const moved = arr.splice(from, 1)[0]
  arr.splice(idx, 0, moved)
  resetDrag()
  saveOrder()
}
function onDragEnd() {
  resetDrag()
}
function resetDrag() {
  dragIndex.value = -1
  dragOverIndex.value = -1
}
async function saveOrder() {
  try {
    const order = list.value.map((x) => x.id)
    await api('/daily-tasks/reorder', 'POST', { order })
  } catch (e) {
    console.error('[DailyTasks] reorder failed', e)
    await alert('拖拽排序保存失败：' + (e.message || '未知错误'))
    loadList()
  }
}
</script>

<style scoped>
.dt-page {
  width: 100%;
  max-width: none;
  margin: 0;
  height: calc(100vh - 44px);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.dt-scroll {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  padding-top: 16px;
  padding-bottom: 20px;
}
.dt-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 18px; }
.dt-card {
  background: var(--sx-bg-surface);
  border: 1px solid var(--sx-border);
  border-radius: var(--sx-radius-lg);
  padding: 18px 18px 48px;
  display: flex; flex-direction: column; gap: 14px;
  position: relative;
  box-shadow: var(--sx-shadow-card);
  transition: .15s;
}
.dt-card:hover { border-color: var(--sx-accent); box-shadow: var(--sx-card-active-shadow); transform: translateY(-2px); }
.dt-card.dragging { opacity: .4; }
.dt-card.drag-over { border-color: var(--sx-accent); box-shadow: 0 0 0 2px var(--sx-accent-soft); }
.dt-card-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.dt-card-name { font-size: 16px; font-weight: 700; color: var(--sx-text-strong); }
.dt-handle { cursor: grab; color: var(--sx-text-faint); margin-right: 6px; font-size: 15px; user-select: none; }
.dt-card.dragging .dt-handle { cursor: grabbing; }
.dt-card-meta {
  font-size: 13px; color: var(--sx-text); margin-top: 4px;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.dt-meta-soft { display: inline; font-weight: 600; }
.dt-card-must {
  font-size: 13.5px; color: var(--sx-status-must-text); font-weight: 600; margin-top: 2px;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.dt-card-points {
  display: flex; align-items: center; gap: 8px; margin-top: 6px; flex-wrap: wrap;
}
.dt-pt-num {
  font-size: 13px; font-weight: 800; color: var(--sx-points-text);
  background: var(--sx-points-bg); border: 1px solid var(--sx-points-border); border-radius: var(--sx-radius-pill);
  padding: 2px 10px;
}
.dt-pt-mode {
  font-size: 11.5px; font-weight: 700; padding: 2px 8px; border-radius: 6px;
}
.dt-pt-mode.cum { color: var(--sx-points-cum-text); background: var(--sx-points-cum-bg); border: 1px solid var(--sx-points-cum-border); }
.dt-pt-mode.daily { color: var(--sx-points-daily-text); background: var(--sx-points-daily-bg); border: 1px solid var(--sx-points-daily-border); }
.dt-card-summary {
  font-size: 13px; color: var(--sx-text); line-height: 1.65;
  margin-top: 2px; padding: 10px 12px;
  background: var(--sx-summary-bg); border-left: 3px solid var(--sx-summary-border);
  border-radius: var(--sx-radius);
  display: -webkit-box; -webkit-line-clamp: 3;
  -webkit-box-orient: vertical; overflow: hidden;
}
.dt-sum-tag { font-weight: 700; margin-right: 4px; }
.dt-card-deadline {
  font-size: 13px; color: var(--sx-text-muted); display: flex; align-items: center; gap: 4px;
  white-space: nowrap;
}
.dt-card-deadline .dt-dl-num { font-weight: 700; }
.dt-card-deadline.today { color: var(--sx-status-today-text); font-weight: 600; }
.dt-card-deadline.expired { color: var(--sx-status-expired-text); font-weight: 600; }
.dt-card-deadline.expired .dt-dl-num { color: var(--sx-status-expired-num-text); }
.dt-card-deadline:not(.today):not(.expired) { color: var(--sx-status-neutral-text); }
.dt-card-deadline:not(.today):not(.expired) .dt-dl-num { color: var(--sx-status-today-text); }
.dt-card-ops {
  position: absolute; left: 18px; right: 18px; bottom: 14px;
  display: flex; gap: 8px;
  opacity: 0; pointer-events: none;
  transform: translateY(6px);
  transition: opacity .15s, transform .15s;
}
.dt-card:hover .dt-card-ops { opacity: 1; pointer-events: auto; transform: translateY(0); }
.dt-op {
  flex: 1; display: inline-flex; align-items: center; justify-content: center;
  padding: 7px 6px; border-radius: var(--sx-radius); border: 1px solid var(--sx-border-strong);
  background: var(--sx-bg-surface);
  color: var(--sx-text-emphasis); font-size: 13px; cursor: pointer; transition: .15s;
}
.dt-op:hover { background: var(--sx-bg-surface-2); color: var(--sx-accent); border-color: var(--sx-accent); }
.dt-op.danger:hover { background: var(--sx-btn-danger-bg); color: var(--sx-btn-danger-text); border-color: var(--sx-btn-danger-border); }
.dt-op.warn:hover { background: var(--sx-tag-warn-bg); color: var(--sx-tag-warn-text); border-color: var(--sx-tag-warn-border); }
.dt-op.ok:hover { background: var(--sx-tag-success-bg); color: var(--sx-tag-success-text); border-color: var(--sx-tag-success-border); }

.dt-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}
.dt-title { display: flex; flex-direction: column; align-items: flex-start; gap: 6px; }
.dt-title-main { display: flex; align-items: center; gap: 12px; }
.dt-emoji { font-size: 30px; line-height: 1; }
.dt-title h2 { margin: 0; font-size: 22px; color: var(--sx-text-strong); }
.dt-sub {
  margin: 0;
  color: var(--sx-subtle-info-text);
  font-size: 13px;
  font-weight: 600;
  background: var(--sx-subtle-info-bg);
  border: 1px solid var(--sx-subtle-info-border);
  padding: 5px 11px;
  border-radius: var(--sx-radius-sm);
}
.dt-actions { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
.dt-search { width: 280px; }
.dt-search.narrow { width: 150px; }
@media (max-width: 768px) {
  .dt-search,
  .dt-search.narrow { width: 100%; }
}
.dt-add {
  background: var(--sx-btn-primary-bg) !important;
  color: #fff !important;
  font-weight: 600 !important;
  padding: 10px 18px !important;
  box-shadow: var(--sx-btn-primary-shadow) !important;
}
.dt-paused-entry {
  background: var(--sx-tag-warn-bg) !important;
  color: var(--sx-tag-warn-text) !important;
  border: 1px solid var(--sx-tag-warn-border) !important;
  box-shadow: none !important;
  font-weight: 600 !important;
  font-size: 13px !important;
  padding: 9px 14px !important;
  border-radius: var(--sx-radius-sm) !important;
  cursor: pointer;
  white-space: nowrap;
  transition: .15s;
}
.dt-paused-entry:hover { filter: brightness(.97); }

.dt-accs { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 6px; }
.dt-acc {
  font-size: 11px;
  background: var(--sx-bg-surface-2);
  color: var(--sx-text-emphasis);
  border: 1px solid var(--sx-border);
  border-radius: 6px;
  padding: 1px 7px;
}
.dt-muted { color: var(--sx-text-muted); }

/* 完成状态开关 */
.dt-toggle {
  padding: 6px 16px !important;
  font-size: 14px !important;
  font-weight: 600 !important;
  border-radius: var(--sx-radius-pill) !important;
  border: 1px solid transparent !important;
  transform: none !important;
}
.dt-toggle.done { background: var(--sx-tag-success-bg) !important; color: var(--sx-tag-success-text) !important; border-color: var(--sx-tag-success-border) !important; }
.dt-toggle.pending { background: var(--sx-tag-default-bg) !important; color: var(--sx-tag-default-text) !important; border-color: var(--sx-tag-default-border) !important; }
.dt-toggle.overdue { background: var(--sx-status-overdue-bg) !important; color: var(--sx-status-overdue-text) !important; border-color: var(--sx-status-overdue-border) !important; }
.dt-toggle.paused { background: var(--sx-status-paused-bg) !important; color: var(--sx-status-paused-text) !important; border-color: var(--sx-status-paused-border) !important; }
.dt-toggle:hover { transform: none !important; }

/* 顶部汇总条 */
.dt-summary { display: flex; gap: 12px; margin-bottom: 0; flex-wrap: wrap; }
.dt-stat {
  display: flex; align-items: baseline; gap: 6px;
  background: var(--sx-bg-surface); border: 1px solid var(--sx-border); border-radius: 12px;
  padding: 10px 16px; box-shadow: var(--sx-shadow-card);
}
.dt-stat-num { font-size: 20px; font-weight: 800; line-height: 1; color: var(--sx-text-strong); }
.dt-stat-label { font-size: 12px; color: var(--sx-text-muted); }
.dt-stat.done { border-left: 3px solid var(--sx-tag-success-text); }
.dt-stat.overdue { border-left: 3px solid var(--sx-status-overdue-text); }
.dt-stat.pending { border-left: 3px solid var(--sx-status-pending-accent); }
.dt-stat.points { border-left: 3px solid var(--sx-points-accent); }
.dt-stat.points.cum { border-left-color: var(--sx-points-cum-accent); }
.dt-stat.done .dt-stat-num { color: var(--sx-tag-success-text); }
.dt-stat.overdue .dt-stat-num { color: var(--sx-status-overdue-text); }
.dt-stat.pending .dt-stat-num { color: var(--sx-text-muted); }
.dt-stat.points .dt-stat-num { color: var(--sx-points-accent); }
.dt-stat.points.cum .dt-stat-num { color: var(--sx-points-cum-accent); }

/* 汇总条右侧批量操作 */
.dt-summary-actions { margin-left: auto; display: flex; gap: 8px; align-items: center; }
.dt-bulk {
  background: var(--sx-btn-primary-bg) !important; color: #fff !important; font-weight: 600 !important;
  padding: 7px 14px !important; border-radius: var(--sx-radius-sm) !important; box-shadow: var(--sx-btn-primary-shadow) !important;
  font-size: 13px !important; cursor: pointer; transition: .15s;
}
.dt-bulk.ghost { background: var(--sx-btn-ghost-bg) !important; color: var(--sx-btn-ghost-text) !important; box-shadow: none !important; border: 1px solid var(--sx-btn-ghost-border) !important; }
.dt-bulk.muted { background: var(--sx-bg-surface-2) !important; color: var(--sx-text-muted) !important; box-shadow: none !important; border: 1px solid var(--sx-border) !important; }
.dt-bulk:hover { transform: none !important; filter: brightness(1.05); }
.dt-bulk.ghost:hover { background: var(--sx-btn-ghost-bg-hover) !important; }
.dt-bulk.muted:hover { background: var(--sx-row-hover) !important; color: var(--sx-accent); border-color: var(--sx-accent) !important; }
.dt-summary.paused-bar { align-items: center; background: var(--sx-bg-surface); border: 1px solid var(--sx-border); border-radius: 12px; padding: 10px 16px; box-shadow: var(--sx-shadow-card); }
.dt-summary.paused-bar .dt-sub { margin: 0 0 0 8px; background: transparent; border: none; padding: 0; }

@media (max-width: 640px) {
  .dt-grid { grid-template-columns: 1fr; }
}
.dt-empty { padding: 48px 20px; text-align: center; color: var(--sx-text-muted); }

/* 弹窗 */
.dt-mask {
  position: fixed;
  inset: 0;
  background: var(--sx-overlay);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
}
.dt-modal {
  width: 560px;
  max-width: 100%;
  max-height: 90vh;
  overflow: auto;
  background: var(--sx-bg-elevated);
  border-radius: var(--sx-radius-lg);
  box-shadow: var(--sx-shadow-pop);
}
.dt-modal-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--sx-border);
}
.dt-modal-head h3 { margin: 0; color: var(--sx-text-strong); }
.dt-close {
  width: 32px; height: 32px;
  display: inline-flex; align-items: center; justify-content: center;
  border-radius: 50% !important;
  border: none !important;
  background: transparent !important;
  color: var(--sx-text-muted) !important;
  box-shadow: none !important;
  font-size: 22px !important;
  padding: 0 !important;
  line-height: 1;
  transition: background .15s, color .15s;
}
.dt-close:hover {
  background: var(--sx-btn-danger-bg) !important;
  color: var(--sx-btn-danger-text) !important;
}
.dt-modal-body { padding: 18px 20px; }
.dt-modal-foot {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 14px 20px;
  border-top: 1px solid var(--sx-border);
}
.dt-cancel { background: var(--sx-btn-ghost-bg) !important; color: var(--sx-btn-ghost-text) !important; box-shadow: none !important; border: 1px solid var(--sx-btn-ghost-border) !important; }
.dt-cancel:hover { background: var(--sx-btn-ghost-bg-hover) !important; }
.dt-save { background: var(--sx-btn-primary-bg) !important; color: #fff !important; font-weight: 600 !important; box-shadow: var(--sx-btn-primary-shadow) !important; }

.fld { margin-bottom: 14px; display: flex; flex-direction: column; gap: 6px; }
.fld > label { font-size: 13px; font-weight: 600; color: var(--sx-text-emphasis); }
.fld > label .req { color: var(--sx-btn-danger-text); }
.fld input { width: 100%; }
.fld-row { display: flex; gap: 14px; }
.fld-row .fld { flex: 1; }

.acc-edit { display: flex; flex-direction: column; gap: 8px; }
.acc-item { display: flex; gap: 8px; align-items: center; }
.acc-item input { flex: 1; }
.acc-del {
  background: var(--sx-btn-danger-bg) !important;
  color: var(--sx-btn-danger-text) !important;
  border: 1px solid var(--sx-btn-danger-border) !important;
  box-shadow: none !important;
  width: 34px !important;
  height: 34px !important;
  flex-shrink: 0;
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  padding: 0 !important;
  font-size: 16px !important;
  line-height: 1 !important;
  border-radius: var(--sx-radius-sm) !important;
}
.acc-add {
  align-self: flex-start;
  background: var(--sx-btn-ghost-bg) !important;
  color: var(--sx-btn-ghost-text) !important;
  box-shadow: none !important;
  font-size: 13px !important;
  padding: 6px 12px !important;
  border: 1px solid var(--sx-btn-ghost-border) !important;
}

/* 查看弹窗 */
.dt-view-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px 20px;
}
.dt-view-cell { display: flex; flex-direction: column; gap: 3px; }
.dt-view-cell .vk { font-size: 12px; color: var(--sx-text-muted); }
.dt-view-cell .vv { font-size: 14px; color: var(--sx-text-strong); word-break: break-word; }
.dt-view-accs { margin-top: 16px; }
.dt-view-accs .vk { font-size: 12px; color: var(--sx-text-muted); margin-bottom: 6px; }
.dt-view-must { margin-top: 16px; }
.dt-view-must .vk { font-size: 12px; color: var(--sx-text-muted); margin-bottom: 6px; }
.dt-must-body {
  font-size: 14px; color: var(--sx-text); line-height: 1.6;
  padding: 10px 12px; background: var(--sx-tag-warn-bg);
  border-left: 3px solid var(--sx-tag-warn-border); border-radius: var(--sx-radius-sm);
  word-break: break-word; white-space: pre-wrap;
}
.dt-view-link { margin-top: 16px; padding-top: 14px; border-top: 1px dashed var(--sx-border); }
.dt-view-link .vk { font-size: 12px; color: var(--sx-text-muted); margin-bottom: 6px; }
.dt-link-row { display: flex; align-items: flex-start; gap: 8px; }
.dt-link-row .dt-copy { flex-shrink: 0; white-space: nowrap; align-self: flex-start; }
.dt-linkout { flex: 1 1 auto; min-width: 0; word-break: break-all; line-height: 1.5; color: var(--sx-link); }
.dt-copy-row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.dt-copy {
  background: var(--sx-btn-ghost-bg) !important;
  color: var(--sx-btn-ghost-text) !important;
  border: 1px solid var(--sx-btn-ghost-border) !important;
  box-shadow: none !important;
  font-size: 12px !important;
  padding: 2px 10px !important;
  border-radius: 6px !important;
  cursor: pointer;
}
.dt-copy.mini { padding: 1px 7px !important; font-size: 11px !important; }
.dt-copy:hover { background: var(--sx-btn-ghost-bg-hover) !important; }
.dt-acc.clickable {
  cursor: pointer;
  transition: .15s;
}
.dt-acc.clickable:hover {
  background: var(--sx-row-hover);
  border-color: var(--sx-accent);
  color: var(--sx-accent);
}
.dt-view-pt-mode { font-weight: 700; }
.dt-view-pt-mode.cum { color: var(--sx-points-cum-text); }
.dt-view-pt-mode.daily { color: var(--sx-points-daily-text); }
</style>
