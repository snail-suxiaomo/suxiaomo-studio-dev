<template>
  <div class="apps-launcher">
    <div class="apps-home-header">
      <div class="head">
        <h2>🚀 应用中心</h2>
        <button class="add-btn" @click="openAdd">＋ 添加应用</button>
      </div>
      <p class="sub">把常用软件钉在这里，一键启动。只存快捷方式，不扫描、不修改任何文件。</p>
    </div>

    <div class="apps-home-body">
      <div v-if="apps.length === 0" class="empty">
        还没有应用，点「添加应用」把常用软件（如微信、IDE、浏览器）加进来。
      </div>

      <div v-for="(g, gi) in groups" :key="g.name" class="cat-block">
        <div class="cat-head">
          <span class="cat-dot" :style="{ background: g.color }"></span>
          <span class="cat-name">{{ g.name }}</span>
          <span class="cat-count">{{ g.items.length }}</span>
        </div>
        <div class="grid">
          <div
            v-for="(a, ii) in g.items"
            :key="a.id"
            class="tile"
            :class="{ 'drag-target': dragFrom && dragFrom.gi === gi && dragOverIndex === ii }"
            draggable="true"
            @dragstart="dragStart(gi, ii, $event)"
            @dragenter.prevent="dragEnter(gi, ii)"
            @dragleave="dragLeave(gi, ii)"
            @dragover.prevent
            @drop="drop(gi, ii)"
            @click="onTileClick(a, $event)"
          >
            <div class="tile-icon-wrap">
              <div class="tile-icon">
                <img
                  v-if="a.icon_path && iconLoaded[a.id] !== false"
                  :src="a.icon_path"
                  class="tile-icon-img"
                  :alt="a.name"
                  @error="iconLoaded[a.id] = false"
                />
                <span v-else class="rocket">{{ a.name.slice(0, 1) }}</span>
              </div>
              <span
                class="status-dot"
                :class="runningStatus[a.id] ? 'on' : 'off'"
                :title="runningStatus[a.id] ? '运行中' : '未启动'"
              ></span>
              <span class="tile-name" :title="a.name">{{ a.name }}</span>
              <div class="tile-ops" @click.stop>
                <button class="op-launch" @click.stop="launch(a)" title="启动 / 切换到窗口">▶</button>
                <button class="op-new" @click.stop="launch(a, true)" title="再开一个新窗口/实例（Shift+点卡片同效）">＋</button>
                <button class="op-edit" @click.stop="editApp(a)" title="编辑">✎</button>
                <button class="op-del" @click.stop="delApp(a)" title="删除">×</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 启动提示 -->
    <transition name="fade">
      <div v-if="toast" class="toast">{{ toast }}</div>
    </transition>

    <!-- 添加/编辑弹窗 -->
    <div v-if="showForm" class="mask" @click.self="closeForm">
      <div class="modal" @click.stop>
        <h3>{{ editingApp ? '编辑应用' : '添加应用' }}</h3>
        <div class="form-row">
          <label>应用名</label>
          <input v-model="newName" placeholder="如 微信 / VS Code" />
        </div>
        <div class="form-row">
          <label>可执行文件路径（.exe）</label>
          <input v-model="newExe" placeholder="如 C:\Program Files\...\wechat.exe" />
        </div>
        <div class="form-row">
          <label>启动参数（可选）</label>
          <input v-model="newArgs" placeholder="如 --fullscreen（留空则无）" />
        </div>
        <div class="form-row">
          <label>状态检测端口（可选，网页型应用用）</label>
          <input v-model="newPort" placeholder="如 7860（TTS/ComfyUI 等 webui 的端口，填后状态灯按端口检测）" />
        </div>
        <div class="form-row">
          <label>分类</label>
          <div class="chips">
            <button
              v-for="c in ['社交','AI','浏览器','工具','开发','其他']"
              :key="c"
              type="button"
              class="chip"
              :class="{ on: newCategory === c }"
              @click="newCategory = c"
            >{{ c }}</button>
          </div>
          <input v-model="newCategory" placeholder="或输入自定义分类名" style="margin-top:8px" />
        </div>
        <div class="form-row">
          <label>备注（可选）</label>
          <input v-model="newNote" placeholder="写点备注…" />
        </div>
        <div class="modal-actions">
          <button type="button" :disabled="!newName || !newExe" @click.stop="saveApp">保存</button>
          <button type="button" class="ghost" @click.stop="closeForm">取消</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { api } from '../common/http.js'
import { confirm, alert } from '../common/useConfirm.js'

const apps = ref([])
const showForm = ref(false)
const editingApp = ref(null)
const newName = ref('')
const newExe = ref('')
const newArgs = ref('')
const newCategory = ref('社交')
const newNote = ref('')
const newPort = ref('')

const dragFrom = ref(null)
const dragOverIndex = ref(null)

// ===== 分类分组 =====
const CAT_ORDER = ['社交', 'AI', '浏览器', '工具', '开发', '其他', '未分类']
const catPalette = [
  'linear-gradient(135deg,#34c759,#7be38a)', // 社交-绿
  'linear-gradient(135deg,#a855f7,#d8b4fe)', // AI-紫
  'linear-gradient(135deg,#ff7a59,#ffb259)', // 浏览器-橙
  'linear-gradient(135deg,#2bb6ff,#36e0c8)', // 工具-青蓝
  'linear-gradient(135deg,#6a5cff,#9b7bff)', // 开发-靛紫
  'linear-gradient(135deg,#8b5cf6,#c084fc)', // 其他-紫粉
  'linear-gradient(135deg,#ff5c8a,#ff9f0a)', // 未分类-粉
]
function catColor(name, idx) {
  const i = CAT_ORDER.indexOf(name)
  return i >= 0 ? catPalette[i] : catPalette[(CAT_ORDER.length + idx) % catPalette.length]
}
const groups = computed(() => {
  const map = new Map()
  for (const r of apps.value) {
    if (!map.has(r.category)) map.set(r.category, [])
    map.get(r.category).push(r)
  }
  const names = []
  for (const c of CAT_ORDER) if (map.has(c)) names.push(c)
  for (const c of map.keys()) if (!CAT_ORDER.includes(c)) names.push(c)
  return names.map((name, idx) => ({
    name,
    color: catColor(name, idx),
    items: map.get(name),
  }))
})

function shortPath(p) {
  if (!p) return ''
  const parts = p.split(/[\\/]/)
  const name = parts[parts.length - 1]
  if (name.length <= 22) return name
  return '…' + name.slice(-21)
}

function normalizeCategory(c) {
  // 旧数据里的"其它"统一展示为"其他"
  if (c === '其它') return '其他'
  return c || '未分类'
}

async function loadApps() {
  try {
    const list = await api('/apps_launcher/apps')
    apps.value = list.map(a => ({ ...a, category: normalizeCategory(a.category) }))
    // 重置图标加载状态：有 icon_path 的先尝试显示，加载失败由 @error 回退
    const map = {}
    for (const a of apps.value) {
      if (a.icon_path) map[a.id] = true
    }
    iconLoaded.value = map
  } catch (e) {
    console.error('加载应用失败：', e)
  }
}

// 运行中状态：{ [appId]: true/false }，定时轮询后端真实进程检测
const runningStatus = ref({})
// 图标加载状态：若图片 404/失败则回退首字母色块
const iconLoaded = ref({})
let statusTimer = null
async function refreshStatus() {
  try {
    const tasks = apps.value.map(a =>
      api('/apps_launcher/status/' + a.id).then(r => [a.id, !!(r && r.running)]).catch(() => [a.id, false])
    )
    const results = await Promise.all(tasks)
    const map = {}
    for (const [id, running] of results) map[id] = running
    runningStatus.value = map
  } catch (e) {
    /* 忽略轮询错误 */
  }
}

function openAdd() {
  editingApp.value = null
  newName.value = ''
  newExe.value = ''
  newArgs.value = ''
  newCategory.value = '社交'
  newNote.value = ''
  newPort.value = ''
  showForm.value = true
}

function editApp(a) {
  editingApp.value = a
  newName.value = a.name
  newExe.value = a.exe_path
  newArgs.value = a.args || ''
  newCategory.value = a.category || '未分类'
  newNote.value = a.note || ''
  newPort.value = a.detect_port || ''
  showForm.value = true
}

function closeForm() {
  showForm.value = false
  editingApp.value = null
  newName.value = ''
  newExe.value = ''
  newArgs.value = ''
  newCategory.value = '社交'
  newNote.value = ''
  newPort.value = ''
}

async function saveApp() {
  if (!newName.value || !newExe.value) return
  const port = newPort.value === '' ? null : parseInt(newPort.value, 10)
  if (newPort.value !== '' && (isNaN(port) || port <= 0 || port > 65535)) {
    await alert('状态检测端口必须是 1-65535 的数字')
    return
  }
  try {
    if (editingApp.value) {
      await api('/apps_launcher/apps/' + editingApp.value.id, 'PUT', {
        name: newName.value,
        exe_path: newExe.value,
        args: newArgs.value || null,
        category: newCategory.value || '未分类',
        note: newNote.value,
        detect_port: port === null ? 0 : port,  // 0 = 清除端口
      })
    } else {
      await api('/apps_launcher/apps', 'POST', {
        name: newName.value,
        exe_path: newExe.value,
        args: newArgs.value || null,
        category: newCategory.value || '未分类',
        note: newNote.value,
        detect_port: port,
      })
    }
    closeForm()
    await loadApps()
  } catch (e) {
    await alert('保存失败：' + (e.message || e))
  }
}

async function delApp(a) {
  if (!(await confirm('删除应用「' + a.name + '」？', { title: '删除确认' }))) return
  try {
    await api('/apps_launcher/apps/' + a.id, 'DELETE')
    await loadApps()
  } catch (e) {
    await alert('删除失败：' + (e.message || e))
  }
}

// 轻量 toast 提示
const toast = ref('')
let toastTimer = null
function showToast(msg) {
  toast.value = msg
  if (toastTimer) clearTimeout(toastTimer)
  toastTimer = setTimeout(() => (toast.value = ''), 2600)
}

async function launch(a, forceNew = false) {
  try {
    // 后端每次都会真实检测：在运行就置顶（不重复启动），没运行就启动；
    // forceNew=true 时跳过检测直接再开一个新实例/窗口
    const url = '/apps_launcher/launch/' + a.id + (forceNew ? '?force_new=true' : '')
    const res = await api(url, 'POST')
    const action = res && res.action
    if (action === 'activate') {
      showToast('已切换到：' + a.name + '（窗口已置顶）')
    } else {
      showToast((forceNew ? '已新开：' : '已启动：') + a.name + '，已切到该窗口')
    }
  } catch (e) {
    await alert('启动失败：' + (e.message || e))
  }
}

function onTileClick(a, ev) {
  // Shift+点击 = 强制新开一个实例/窗口
  launch(a, !!(ev && ev.shiftKey))
}

// ===== 拖拽排序 =====
function dragStart(gi, ii, ev) {
  dragFrom.value = { gi, ii }
  ev.dataTransfer.effectAllowed = 'move'
  ev.dataTransfer.setData('text/plain', String(ii))
}
function dragEnter(gi, ii) {
  if (dragFrom.value && dragFrom.value.gi === gi) dragOverIndex.value = ii
}
function dragLeave(gi, ii) {
  if (dragOverIndex.value === ii) dragOverIndex.value = null
}
async function drop(gi, ii) {
  dragOverIndex.value = null
  const from = dragFrom.value
  dragFrom.value = null
  if (!from || from.gi !== gi) return
  const gs = groups.value.map(g => ({ ...g, items: g.items.slice() }))
  const [moved] = gs[gi].items.splice(from.ii, 1)
  gs[gi].items.splice(ii, 0, moved)
  const flat = gs.flatMap(g => g.items)
  apps.value = flat
  try {
    await api('/apps_launcher/apps/reorder', 'POST', { ids: flat.map(a => a.id) })
  } catch (e) {
    await alert('保存排序失败：' + (e.message || e))
    await loadApps()
  }
}

onMounted(() => {
  loadApps()
  refreshStatus()
  statusTimer = setInterval(refreshStatus, 5000) // 每 5 秒刷新一次运行状态
})
</script>

<style scoped>
.apps-launcher { width: 100%; height: calc(100vh - 44px); display: flex; flex-direction: column; overflow: hidden; }
.apps-home-header { flex-shrink: 0; position: sticky; top: 0; z-index: 3; background: var(--sx-bg-page); }
.apps-home-body { flex: 1; overflow-y: auto; min-height: 0; }
.head { margin-bottom: 8px; display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.head h2 { font-size: 20px; margin: 0; }
.add-btn {
  background: var(--sx-accent); color: #fff; border: none; border-radius: 10px;
  padding: 9px 16px; font-size: 13px; font-weight: 600; cursor: pointer; flex-shrink: 0;
}
.add-btn:hover { background: var(--sx-accent-hover); }
.sub { color: var(--sx-text-soft); font-size: 13px; margin: 0 0 18px; line-height: 1.6; }
.empty { color: var(--sx-text-muted); text-align: center; padding: 36px 20px; }

.cat-block { margin-bottom: 22px; }
.cat-head { display: flex; align-items: center; gap: 6px; margin-bottom: 8px; }
.cat-dot { width: 8px; height: 8px; border-radius: 3px; flex-shrink: 0; }
.cat-name { font-weight: 700; font-size: 13px; color: var(--sx-text-strong); }
.cat-count {
  font-size: 10px; color: var(--sx-count-text); background: var(--sx-count-bg); border-radius: 8px;
  padding: 0 6px; font-weight: 600;
}

.grid { display: grid; grid-template-columns: repeat(12, 1fr); gap: 12px; }
.tile {
  position: relative;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  min-height: 118px;
  background: var(--sx-bg-surface); border: 1px solid var(--sx-border-soft); border-radius: 12px;
  overflow: hidden; cursor: grab; user-select: none;
  box-shadow: var(--sx-shadow-tile);
  transition: transform .15s, box-shadow .15s;
}
.tile:active { cursor: grabbing; }
.tile:hover { transform: translateY(-1px); box-shadow: var(--sx-shadow-tile-hover); }
.tile.drag-target {
  outline: 2px dashed var(--sx-accent); outline-offset: -3px;
  box-shadow: 0 0 0 3px var(--sx-accent-soft);
}
.tile-icon-wrap {
  position: relative;
  width: 100%; flex: 1;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 8px;
}
.tile-icon {
  width: 56px; height: 56px; border-radius: 14px; flex-shrink: 0;
  background: linear-gradient(135deg,#6a5cff,#9b7bff);
  display: flex; align-items: center; justify-content: center; font-size: 22px;
  overflow: hidden;
}
.tile-icon-img {
  width: 100%; height: 100%; object-fit: contain;
  background: #fff; border-radius: 8px;
}
.rocket {
  font-size: 18px; font-weight: 700; color: #fff; line-height: 1;
}
.status-dot {
  position: absolute; top: 6px; right: 6px;
  width: 10px; height: 10px; border-radius: 50%;
  border: 2px solid #fff;
  box-shadow: 0 1px 3px rgba(0,0,0,.3);
}
.status-dot.on { background: #2ec27e; }   /* 绿色：运行中 */
.status-dot.off { background: #b8bcc9; }  /* 灰色：未启动 */
.tile-name {
  position: absolute; left: 0; right: 0; bottom: 6px;
  text-align: center;
  font-weight: 600; font-size: 12px; color: var(--sx-text-strong);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  padding: 0 8px;
  transition: opacity .15s ease;
}
.tile:hover .tile-name { opacity: 0; }
.tile-ops {
  position: absolute; left: 0; right: 0; bottom: 0; height: 28px;
  display: flex; gap: 10px; align-items: center; justify-content: center;
  background: var(--sx-tileops-bg);
  opacity: 0; transform: translateY(2px);
  transition: opacity .15s ease, transform .15s ease;
  border-radius: 0 0 12px 12px;
}
.tile:hover .tile-ops { opacity: 1; transform: translateY(0); }
.tile-ops button {
  width: auto !important; height: auto !important;
  border: none !important; background: transparent !important; border-radius: 0 !important;
  padding: 0 !important; margin: 0;
  font-size: 13px !important; line-height: 1; font-weight: 700 !important;
  display: inline-flex; align-items: center; justify-content: center;
  cursor: pointer; transition: transform .12s;
}
.tile-ops button:hover { transform: scale(1.25); }
.op-launch { color: #1da864 !important; }
.op-new    { color: #3b8cff !important; }
.op-edit   { color: #5a5f75 !important; }
.op-del    { color: #f0407e !important; }

/* 弹窗 */
.mask {
  position: fixed; inset: 0; background: var(--sx-overlay);
  display: flex; align-items: center; justify-content: center; z-index: 1000;
}
.toast {
  position: fixed; left: 50%; top: 24px; transform: translateX(-50%);
  background: var(--sx-toast-dark-bg); color: #fff; padding: 10px 18px;
  border-radius: 10px; font-size: 13px; z-index: 2000;
  box-shadow: 0 8px 24px rgba(0, 0, 0, .25);
}
.fade-enter-active, .fade-leave-active { transition: opacity .25s, transform .25s; }
.fade-enter-from, .fade-leave-to { opacity: 0; transform: translateX(-50%) translateY(-8px); }
.modal {
  background: var(--sx-bg-elevated); border-radius: 16px; padding: 24px 26px;
  width: 480px; max-width: 92vw; box-shadow: var(--sx-shadow-pop);
}
.modal h3 { font-size: 18px; margin: 0 0 16px; }
.form-row { margin-bottom: 14px; }
.form-row label { display: block; font-weight: 600; margin-bottom: 6px; color: var(--sx-chip-text); font-size: 13px; }
.form-row input { width: 100%; padding: 9px 11px; border: 1px solid var(--sx-border-strong); border-radius: 9px; font-size: 13px; }
.modal-actions { display: flex; gap: 10px; justify-content: flex-end; margin-top: 8px; }
.chips { display: flex; flex-wrap: wrap; gap: 8px; }
.chip {
  background: var(--sx-chip-bg); color: var(--sx-chip-text); border: 1px solid var(--sx-border-strong); border-radius: 20px;
  padding: 5px 14px; font-size: 13px; cursor: pointer;
}
.chip.on { background: var(--sx-accent); color: #fff; border-color: var(--sx-accent); }

/* 按钮 */
button {
  padding: 7px 14px; font-size: 13px; border-radius: 9px; cursor: pointer;
  background: var(--sx-accent); color: #fff; border: 1px solid var(--sx-accent); transition: .15s;
}
button:hover { background: var(--sx-accent-hover); }
button:disabled { opacity: .5; cursor: not-allowed; }
button.ghost { background: var(--sx-bg-surface); color: var(--sx-chip-text); border: 1px solid var(--sx-border-strong); }
button.ghost:hover { background: var(--sx-chip-bg); }
</style>
