<template>
  <div class="manju" @click="ctxMenu.show = false">
    <!-- 顶部：子功能切换 + 右侧页面操作 -->
    <div class="sub-bar">
      <div class="sub-bar-left">
        <button
          v-for="sub in subs"
          :key="sub.key"
          class="sub-btn"
          :class="{ active: activeSub === sub.key, [`cat-${sub.key}`]: true }"
          :style="subBtnStyle(sub.key)"
          @click="selectSub(sub.key)"
        >
          <span class="sub-emoji">{{ subEmojiOf(sub.key) }}</span>
          <span class="sub-label">{{ sub.label }}</span>
        </button>
        <button
          v-if="manageMode"
          class="sub-btn cat-manage-btn"
          title="重命名 / 新增 / 删除分类"
          @click="openCatManager()"
        >
          <span class="sub-emoji">⚙️</span>
          <span class="sub-label">分类</span>
        </button>
      </div>
      <div class="sub-bar-right">
        <button v-if="sidebarCollapsed" class="sub-op-btn" @click="sidebarCollapsed = false">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"></polyline></svg>
          <span>展开网站列表</span>
        </button>
        <template v-else>
          <button
            class="sub-op-btn"
            :style="{ background: 'var(--sx-bg-card)', color: 'var(--sx-text-strong)', borderColor: 'var(--sx-border)', fontWeight: '600', fontSize: '13px' }"
            @click="manageMode = !manageMode"
          >{{ manageMode ? '完成' : '管理' }}</button>
          <button
            v-if="manageMode"
            class="sub-op-btn"
            :style="{ background: 'var(--sx-bg-card)', color: 'var(--sx-text-strong)', borderColor: 'var(--sx-border)', fontWeight: '600', fontSize: '13px' }"
            @click="resetDefaults()"
            title="恢复被删除的系统默认网站"
          >↺ 恢复默认</button>
          <button
            class="sub-op-btn"
            :style="{ background: 'linear-gradient(135deg, #ff7a3a, #7b5cff)', color: '#fff', borderColor: 'transparent', fontWeight: '800', fontSize: '14px', textShadow: '0 1px 3px rgba(0,0,0,.45)', boxShadow: '0 4px 14px rgba(255,122,58,.45)' }"
            @click="openEditor()"
          >+ 添加</button>
          <button class="sub-op-btn" @click="sidebarCollapsed = true" title="收起网站列表">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"></polyline></svg>
          </button>
        </template>
      </div>
    </div>

    <div class="manju-body">
      <!-- 左侧网站边栏 -->
      <aside v-if="!sidebarCollapsed" class="site-sidebar">
        <div class="sidebar-head">
          <div class="sidebar-title">
            <span class="st-dot" :style="{ background: catColor(activeSub) }"></span>
            <span>{{ activeSub }}</span>
          </div>
          <button class="sb-collapse" @click="sidebarCollapsed = true" title="收起">
            <span>收起</span>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"></polyline></svg>
          </button>
        </div>

        <div class="site-list">
          <div
            v-for="s in sites"
            :key="s.id"
            class="site-row"
            :class="{ active: isActiveSite(s) }"
            @click="openSite(s)"
            @contextmenu.prevent="openContextMenu($event, s)"
            :title="s.url || '未配置网址'"
          >
            <span class="sr-dot" :style="{ background: s.tag ? tagColor(s.tag) : catColor(activeSub) }"></span>
            <span class="sr-name">{{ s.name }}</span>
            <span v-if="s.is_default" class="sr-badge" title="系统默认">默认</span>
            <span v-if="s.tag && !manageMode" class="sr-tag">{{ s.tag }}</span>
            <div v-if="manageMode" class="sr-ops" @click.stop>
              <button class="op-mini" @click="openEditor(s)" title="编辑" aria-label="编辑">
                <span class="op-icon">✎</span>
              </button>
              <button class="op-mini danger" @click="removeSite(s)" title="删除" aria-label="删除">
                <span class="op-icon">🗑</span>
              </button>
            </div>
          </div>
          <div v-if="!sites.length" class="site-empty">
            <span class="se-emoji">🗂️</span>
            暂无网站<br /><span class="se-tip">点下方「+ 添加」</span>
          </div>
        </div>

        <div class="sidebar-foot">
          <button
            class="foot-btn"
            :style="{ background: 'var(--sx-bg-card)', color: 'var(--sx-text-strong)', borderColor: 'var(--sx-border)', fontWeight: '700', fontSize: '13px' }"
            @click="manageMode = !manageMode"
          >{{ manageMode ? '完成' : '管理' }}</button>
          <button
            class="foot-btn"
            :style="{ background: 'linear-gradient(135deg, #ff7a3a, #7b5cff)', color: '#fff', borderColor: 'transparent', fontWeight: '800', fontSize: '14px', textShadow: '0 1px 3px rgba(0,0,0,.45)', boxShadow: '0 4px 14px rgba(255,122,58,.45)' }"
            @click="openEditor()"
          >+ 添加</button>
        </div>
      </aside>

      <!-- 内置浏览器 -->
      <div class="browser">
        <div class="browser-main">
          <div class="tab-bar">
            <div
              v-for="t in openTabs"
              :key="t.id"
              class="tab"
              :class="{ active: t.id === activeTabId }"
              @click="activeTabId = t.id"
            >
              <span class="tab-dot" :style="{ background: catColor(t.cat) }"></span>
              <span class="tab-name">{{ t.name }}</span>
              <span class="tab-close" @click.stop="closeTab(t.id)">×</span>
            </div>
            <div v-if="!openTabs.length" class="tab-empty">点击左侧网站打开标签，可同时开多个</div>
          </div>
          <div class="browser-view">
            <template v-if="isElectron">
              <webview
                v-for="t in openTabs"
                :key="t.id"
                v-show="t.id === activeTabId"
                :src="t.url"
                :partition="'persist:' + t.cat"
                class="webview"
                allowpopups
              ></webview>
              <div v-if="!openTabs.length" class="browser-empty">点击左侧网站打开标签</div>
            </template>
            <div v-else class="browser-fallback">
              内置浏览器需在「桌面版」中使用。点击左侧网站将在新标签页打开。
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 右键菜单 -->
    <div
      v-if="ctxMenu.show"
      class="ctx-menu"
      :style="{ left: ctxMenu.x + 'px', top: ctxMenu.y + 'px' }"
      @click.stop
    >
      <div class="ctx-item" @click="ctxEdit">编辑</div>
      <div class="ctx-item" @click="ctxOpenNew">在新标签打开</div>
      <div class="ctx-item danger" @click="ctxDelete">删除</div>
    </div>

    <!-- 添加 / 编辑弹窗 -->
    <div v-if="showEditor" class="modal-mask" @click.self="showEditor = false">
      <div class="modal">
        <h3 class="modal-title">{{ editor.id ? '编辑网站' : '添加网站' }}</h3>
        <label class="modal-label">分类</label>
        <select v-model="editor.category" class="modal-input">
          <option v-for="c in categoriesList" :key="c.id" :value="c.name">{{ c.name }}</option>
        </select>
        <label class="modal-label">名称（如 椒图AI-人物 / 即梦）</label>
        <input v-model="editor.name" class="modal-input" placeholder="名称" />
        <label class="modal-label">标签（如 人物 / 场景 / 道具 / 配音）</label>
        <input v-model="editor.tag" class="modal-input" placeholder="标签" />
        <label class="modal-label">网址 URL</label>
        <input v-model="editor.url" class="modal-input" placeholder="https://" />
        <div class="modal-ops">
          <button class="op-btn" @click="showEditor = false">取消</button>
          <button class="op-btn primary" @click="saveEditor">{{ editor.id ? '保存' : '添加' }}</button>
        </div>
      </div>
    </div>

    <!-- 轻提示 -->
    <transition name="toast">
      <div v-if="toast.show" class="toast" :class="toast.type">
        <span class="toast-icon">{{ toast.type === 'error' ? '✕' : toast.type === 'success' ? '✓' : '!' }}</span>
        <span class="toast-text">{{ toast.text }}</span>
      </div>
    </transition>

    <!-- 确认弹窗 -->
    <div v-if="confirmBox.show" class="modal-mask" @click.self="confirmBox.show = false">
      <div class="modal confirm-modal">
        <h3 class="modal-title">确认</h3>
        <p class="confirm-text">{{ confirmBox.text }}</p>
        <div class="modal-ops">
          <button class="op-btn" @click="confirmCancel">取消</button>
          <button class="op-btn primary" @click="confirmOk">确定</button>
        </div>
      </div>
    </div>

    <!-- 分类管理弹窗：重命名 / 新增 / 删除分类 -->
    <div v-if="showCatManager" class="modal-mask" @click.self="showCatManager = false">
      <div class="modal">
        <h3 class="modal-title">管理分类</h3>
        <div class="cat-list">
          <div v-for="c in categoriesList" :key="c.id" class="cat-row">
            <span class="cat-dot" :style="{ background: catColor(c.name) }"></span>
            <input
              class="modal-input cat-input"
              v-model="catEdit[c.name]"
              @keyup.enter="saveCatName(c.name)"
              @keyup.esc="catEdit[c.name] = c.name"
              placeholder="分类名"
            />
            <button
              class="op-mini success"
              :disabled="!catEdit[c.name] || catEdit[c.name].trim() === c.name"
              @click="saveCatName(c.name)"
              title="保存分类名"
            >✓</button>
            <button
              class="op-mini"
              :disabled="catEdit[c.name] === c.name"
              @click="catEdit[c.name] = c.name"
              title="取消修改"
            >↺</button>
            <button class="op-mini danger" @click="deleteCat(c.name)" title="删除分类">🗑</button>
          </div>
        </div>
        <div class="cat-add">
          <input class="modal-input" v-model="newCatName" placeholder="新分类名" @keyup.enter="addCat()" />
          <button class="op-btn primary" @click="addCat()">+ 新增</button>
        </div>
        <p class="cat-tip">提示：重命名 / 删除非空分类会同步影响该分类下的网站，请先处理其下网站。</p>
        <div class="modal-ops">
          <button class="op-btn" @click="showCatManager = false">关闭</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'

// 子功能分类：从后端 /info 接口动态获取（支持重命名/新增/删除）
const infoData = ref({ categories: [] })
const categoriesList = computed(() => infoData.value.categories || [])
const subs = computed(() => categoriesList.value.map((c) => ({ key: c.name, label: c.name })))
const subEmoji = {
  '去重': '🧹', '剧本': '🎭', '资产': '🎨', '分镜': '🎞️',
  '生图': '🖼️', '音色': '🎵', '生视频': '🎬', '其他': '📂'
}
function subEmojiOf(key) { return subEmoji[key] || '📂' }

// 分类 / 标签配色（未知分类按名字哈希稳定分配一个颜色，保证可辨识）
const CAT_COLORS = {
  '去重': '#7b5cff', '剧本': '#e0392f', '资产': '#1f9d55', '分镜': '#5b8def',
  '生图': '#7b5cff', '音色': '#1f9d55', '生视频': '#ff7a3a', '其他': '#5b8def'
}
const TAG_COLORS = {
  '人物': '#ff7a3a', '场景': '#1f9d55', '道具': '#7b5cff',
  '配音': '#e0392f', 'TTS': '#5b8def'
}
function hashColor(str) {
  let h = 0
  for (let i = 0; i < (str || '').length; i++) h = (h * 31 + str.charCodeAt(i)) >>> 0
  const hue = h % 360
  return `hsl(${hue}, 62%, 52%)`
}
function catColor(c) { return CAT_COLORS[c] || hashColor(c) }
function tagColor(t) { return TAG_COLORS[t] || '#8a8f99' }

// 子功能按钮 inline style：active 用分类色，绕过任何 CSS 缓存
function subBtnStyle(key) {
  const isActive = activeSub.value === key
  if (!isActive) {
    return {
      background: 'transparent',
      color: 'var(--sx-text)',
      borderColor: 'transparent',
      fontWeight: '500',
      boxShadow: 'none',
    }
  }
  const c = CAT_COLORS[key] || '#7b5cff'
  return {
    background: '#ffffff',
    color: c,
    borderColor: c,
    fontWeight: '600',
    boxShadow: `inset 3px 0 0 0 ${c}, 0 1px 4px rgba(0,0,0,.06)`,
  }
}

const activeSub = ref('')

// 从后端拉取分类（含 id），替代原硬编码常量
async function loadInfo() {
  try {
    const res = await fetch('/api/manju-generate/info')
    const data = await res.json()
    infoData.value = data
    if (!categoriesList.value.some((c) => c.name === activeSub.value)) {
      activeSub.value = categoriesList.value.length ? categoriesList.value[0].name : ''
    }
  } catch (_) { /* 接口异常时保持空，降级为全部网站 */ }
}
function catIdOf(name) {
  const f = categoriesList.value.find((c) => c.name === name)
  return f ? f.id : null
}

// 分类管理（重命名 / 新增 / 删除）
const showCatManager = ref(false)
const catEdit = ref({})
const newCatName = ref('')
function openCatManager() {
  const e = {}
  categoriesList.value.forEach((c) => { e[c.name] = c.name })
  catEdit.value = e
  showCatManager.value = true
}
async function afterCatChange() {
  await loadInfo()
  await loadSites()
}
async function saveCatName(oldName) {
  const newName = (catEdit.value[oldName] || '').trim()
  if (!newName) { showToast('分类名不能为空', 'warning'); return }
  if (newName === oldName) return
  const id = catIdOf(oldName)
  if (!id) return
  try {
    const res = await fetch(`/api/manju-generate/categories/${id}`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: newName }),
    })
    const data = await res.json()
    if (!data.ok) { showToast(data.detail || '重命名失败', 'error'); return }
  } catch (_) { showToast('重命名失败', 'error'); return }
  if (activeSub.value === oldName) activeSub.value = newName
  await afterCatChange()
}
async function deleteCat(name) {
  const id = catIdOf(name)
  if (!id) return
  const ok = await showConfirm(`确认删除分类「${name}」？\n（该分类下还有网站时会被拦截，请先将这些网站改到其他分类或删除）`)
  if (!ok) return
  try {
    const res = await fetch(`/api/manju-generate/categories/${id}`, { method: 'DELETE' })
    const data = await res.json()
    if (!data.ok) { showToast(data.detail || '删除失败', 'error'); return }
  } catch (_) { showToast('删除失败', 'error'); return }
  await afterCatChange()
}
async function addCat() {
  const name = newCatName.value.trim()
  if (!name) { showToast('分类名不能为空', 'warning'); return }
  try {
    const res = await fetch('/api/manju-generate/categories', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name }),
    })
    const data = await res.json()
    if (!data.ok) { showToast(data.detail || '新增失败', 'error'); return }
  } catch (_) { showToast('新增失败', 'error'); return }
  newCatName.value = ''
  await afterCatChange()
}

// 管理开关：开启时每行显示编辑/删除（替换 tag 位置）
const manageMode = ref(false)

// 网站列表折叠（持久化）
const SIDEBAR_COLLAPSED_KEY = 'sxm_manju_sidebar_collapsed'
const sidebarCollapsed = ref(false)
function loadSidebarState() {
  try {
    const saved = localStorage.getItem(SIDEBAR_COLLAPSED_KEY)
    sidebarCollapsed.value = saved === null ? false : saved === '1'
  } catch (_) { /* ignore */ }
}
function saveSidebarState() {
  try { localStorage.setItem(SIDEBAR_COLLAPSED_KEY, sidebarCollapsed.value ? '1' : '0') } catch (_) { /* ignore */ }
}

// 右键菜单
const ctxMenu = ref({ show: false, x: 0, y: 0, site: null })
function openContextMenu(e, site) {
  ctxMenu.value = { show: true, x: e.clientX, y: e.clientY, site }
}
function ctxEdit() {
  if (ctxMenu.value.site) openEditor(ctxMenu.value.site)
  ctxMenu.value.show = false
}
function ctxOpenNew() {
  if (ctxMenu.value.site) openSiteNewTab(ctxMenu.value.site)
  ctxMenu.value.show = false
}
function ctxDelete() {
  if (ctxMenu.value.site) removeSite(ctxMenu.value.site)
  ctxMenu.value.show = false
}
// 右键「新标签打开」：即使非 Electron 也开一个独立标签（不替换当前）
function openSiteNewTab(site) {
  const u = (site.url || '').trim()
  if (!u || u === 'https://' || u === 'http://') {
    showToast('该网站尚未配置网址，请先「编辑」填写 URL', 'warning')
    openEditor(site)
    return
  }
  const tab = {
    id: genId(),
    cat: site.category,
    siteId: site.id,
    name: site.name,
    tag: site.tag,
    url: u,
  }
  openTabs.value.push(tab)
  activeTabId.value = tab.id
  persistTabUpsert(tab, openTabs.value.length - 1)
}

const isElectron = typeof navigator !== 'undefined' && navigator.userAgent.includes('Electron')

// 自定义轻提示（替代系统 alert）
const toast = ref({ show: false, text: '', type: 'info' })
let toastTimer = null
function showToast(text, type = 'info', duration = 2200) {
  toast.value = { show: true, text, type }
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => { toast.value.show = false }, duration)
}

// 自定义确认弹窗（替代系统 confirm）
const confirmBox = ref({ show: false, text: '', resolve: null })
function showConfirm(text) {
  return new Promise((resolve) => {
    confirmBox.value = { show: true, text, resolve }
  })
}
function confirmOk() {
  confirmBox.value.show = false
  if (confirmBox.value.resolve) confirmBox.value.resolve(true)
}
function confirmCancel() {
  confirmBox.value.show = false
  if (confirmBox.value.resolve) confirmBox.value.resolve(false)
}

// 当前子功能下的网站列表
const sites = ref([])
async function loadSites() {
  try {
    const res = await fetch(`/api/manju-generate/sites?category=${encodeURIComponent(activeSub.value)}`)
    const data = await res.json()
    sites.value = data.sites || []
  } catch (e) {
    sites.value = []
  }
}

// 已打开标签（永驻：存后端数据库 manju_open_tabs 表；webview 登录态由 Electron persist partition 缓存）
const openTabs = ref([])
const activeTabId = ref(null)

function genId() {
  return 't' + Date.now() + '-' + Math.floor(Math.random() * 1000)
}
const openSiteIds = computed(() => new Set(openTabs.value.map((t) => t.siteId)))
function isActiveSite(s) { return openSiteIds.value.has(s.id) }

async function loadTabs() {
  try {
    const res = await fetch('/api/manju-generate/tabs')
    const data = await res.json()
    const tabs = (data.tabs || []).map((t) => ({
      id: t.client_id,
      cat: t.category,
      siteId: t.site_id,
      name: t.name,
      tag: t.tag,
      url: t.url,
    }))
    openTabs.value = tabs
    if (tabs.length) activeTabId.value = tabs[tabs.length - 1].id
  } catch (_) { /* ignore */ }
}

async function persistTabUpsert(tab, sortOrder) {
  try {
    await fetch('/api/manju-generate/tabs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        client_id: tab.id,
        category: tab.cat,
        site_id: tab.siteId,
        name: tab.name,
        tag: tab.tag,
        url: tab.url,
        sort_order: sortOrder || 0,
      }),
    })
  } catch (_) { /* ignore */ }
}

async function persistTabDelete(id) {
  try {
    await fetch(`/api/manju-generate/tabs/${encodeURIComponent(id)}`, { method: 'DELETE' })
  } catch (_) { /* ignore */ }
}

async function persistTabsBySiteDelete(siteId) {
  try {
    await fetch(`/api/manju-generate/tabs/replace-by-site/${siteId}`, { method: 'POST' })
  } catch (_) { /* ignore */ }
}

function selectSub(key) {
  activeSub.value = key
  manageMode.value = false
  loadSites()
}

function openSite(site) {
  const u = (site.url || '').trim()
  if (!u || u === 'https://' || u === 'http://') {
    showToast('该网站尚未配置网址，请先「编辑」填写 URL', 'warning')
    openEditor(site)
    return
  }
  if (!isElectron) {
    window.open(u, '_blank')
    return
  }
  const tab = {
    id: genId(),
    cat: site.category,
    siteId: site.id,
    name: site.name,
    tag: site.tag,
    url: u,
  }
  openTabs.value.push(tab)
  activeTabId.value = tab.id
  persistTabUpsert(tab, openTabs.value.length - 1)
}

function closeTab(id) {
  const idx = openTabs.value.findIndex((t) => t.id === id)
  if (idx < 0) return
  openTabs.value.splice(idx, 1)
  persistTabDelete(id)
  if (activeTabId.value === id) {
    activeTabId.value = openTabs.value.length
      ? openTabs.value[Math.min(idx, openTabs.value.length - 1)].id
      : null
  }
}

// 添加 / 编辑
const showEditor = ref(false)
const editor = ref({ id: null, category: '生图', name: '', tag: '', url: '' })
function openEditor(site) {
  if (site) {
    editor.value = { id: site.id, category: site.category, name: site.name, tag: site.tag, url: site.url }
  } else {
    editor.value = { id: null, category: activeSub.value, name: '', tag: '', url: '' }
  }
  showEditor.value = true
}
async function saveEditor() {
  const e = editor.value
  if (!e.name || !e.name.trim()) { showToast('名称不能为空', 'warning'); return }
  if (e.id) {
    const res = await fetch(`/api/manju-generate/sites/${e.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ category: e.category, name: e.name.trim(), tag: e.tag, url: e.url }),
    })
    const data = await res.json()
    if (data.ok) {
      openTabs.value.forEach((t) => {
        if (t.siteId === e.id) {
          t.name = data.site.name
          t.cat = data.site.category
          t.url = data.site.url
          t.tag = data.site.tag
          persistTabUpsert(t, openTabs.value.indexOf(t))
        }
      })
    }
  } else {
    await fetch('/api/manju-generate/sites', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ category: e.category, name: e.name.trim(), tag: e.tag, url: e.url }),
    })
  }
  showEditor.value = false
  loadSites()
}
async function removeSite(site) {
  const ok = await showConfirm(`确认删除「${site.name}」？${site.is_default ? '\n（这是系统默认项，删后可在「管理 → 恢复默认」中找回）' : ''}`)
  if (!ok) return
  await fetch(`/api/manju-generate/sites/${site.id}`, { method: 'DELETE' })
  // 后端会同步删除该 site 的所有 open tab
  await persistTabsBySiteDelete(site.id)
  openTabs.value = openTabs.value.filter((t) => t.siteId !== site.id)
  if (activeTabId.value && !openTabs.value.find((t) => t.id === activeTabId.value)) {
    activeTabId.value = openTabs.value.length ? openTabs.value[0].id : null
  }
  loadSites()
}

async function resetDefaults() {
  const ok = await showConfirm('恢复被删除的系统默认网站？（不会删除你自建的网站）')
  if (!ok) return
  await fetch('/api/manju-generate/reset-defaults', { method: 'POST' })
  loadSites()
}

onMounted(async () => {
  loadSidebarState()
  await loadInfo()
  loadTabs()
  loadSites()
})
onUnmounted(() => {
  saveSidebarState()
})
</script>

<style scoped>
.manju {
  height: calc(100vh - 44px);
  display: flex;
  flex-direction: column;
  color: var(--sx-text-strong);
  padding: 18px;
  gap: 16px;
}

/* ===== 顶部：子功能切换 ===== */
.sub-bar {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 10px;
}
.sub-bar-left {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px;
}
.sub-bar-right {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 8px;
}
.sub-btn {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border-radius: 9px;
  border: 1px solid transparent;
  background: transparent;
  color: var(--sx-text);
  font-size: 13px;
  cursor: pointer;
  transition: .18s;
}
.sub-btn:hover {
  background: var(--sx-bg-surface-2);
  color: var(--sx-text-strong);
}
/* active：白卡 + 左侧分类色条 + 分类色文字（无任何渐变填充） */
.sub-btn.active {
  font-weight: 600;
  background: var(--sx-bg-card);
  border-color: var(--sx-border);
  color: var(--sx-text-strong);
  box-shadow: 0 1px 4px rgba(0, 0, 0, .06);
}
.sub-btn.active::before {
  content: '';
  position: absolute;
  left: -1px;
  top: 22%;
  bottom: 22%;
  width: 3px;
  border-radius: 3px;
  background: var(--sx-cat-color, #7b5cff);
}
/* 各分类 active 色条与文字色（与 CAT_COLORS 对齐） */
.sub-btn.active.cat-去重,
.sub-btn.active.cat-生图 { --sx-cat-color: #7b5cff; color: #7b5cff; }
.sub-btn.active.cat-剧本 { --sx-cat-color: #e0392f; color: #e0392f; }
.sub-btn.active.cat-资产,
.sub-btn.active.cat-音色 { --sx-cat-color: #1f9d55; color: #1f9d55; }
.sub-btn.active.cat-分镜,
.sub-btn.active.cat-其他 { --sx-cat-color: #5b8def; color: #5b8def; }
.sub-btn.active.cat-生视频 { --sx-cat-color: #ff7a3a; color: #ff7a3a; }
.sub-emoji { font-size: 15px; line-height: 1; }

/* ===== 主体 ===== */
.manju-body {
  flex: 1;
  min-height: 0;
  display: flex;
  gap: 16px;
}

/* ===== 左侧网站边栏 ===== */
.site-sidebar {
  flex-shrink: 0;
  width: 248px;
  display: flex;
  flex-direction: column;
  background: var(--sx-bg-surface);
  border: 1px solid var(--sx-border);
  border-radius: 16px;
  box-shadow: var(--sx-shadow-card);
  overflow: hidden;
}
.sidebar-head {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 14px 12px;
  border-bottom: 1px solid var(--sx-border);
}
.sidebar-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 700;
  color: var(--sx-text-strong);
}
.st-dot {
  width: 10px; height: 10px; border-radius: 50%;
  flex-shrink: 0;
}
.sb-collapse {
  display: inline-flex; align-items: center; gap: 4px;
  height: 26px; padding: 0 9px;
  border-radius: 999px;
  border: 1px solid var(--sx-border); background: transparent;
  color: var(--sx-text); font-size: 12px; cursor: pointer;
  transition: .14s;
}
.sb-collapse svg { opacity: .75; }
.sb-collapse:hover { border-color: var(--sx-accent); color: var(--sx-accent); background: rgba(123, 92, 255, .06); }
.sb-collapse:hover svg { opacity: 1; }

.site-list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.site-row {
  position: relative;
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid transparent;
  background: var(--sx-bg-card);
  cursor: pointer;
  transition: .14s;
}
.site-row::before {
  content: '';
  position: absolute;
  left: 0; top: 18%; bottom: 18%;
  width: 3px; border-radius: 3px;
  background: transparent;
  transition: .14s;
}
.site-row:hover { border-color: var(--sx-border); background: var(--sx-bg-surface-2); }
.site-row.active {
  background: rgba(123,92,255,.10);
  border-color: rgba(123,92,255,.30);
}
.site-row.active::before { background: linear-gradient(180deg, #ff7a3a, #7b5cff); }
.sr-dot {
  width: 9px; height: 9px; border-radius: 50%;
  flex-shrink: 0;
}
.sr-name {
  flex: 1;
  min-width: 0;
  font-size: 13.5px;
  font-weight: 600;
  color: var(--sx-text-strong);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.sr-tag {
  flex-shrink: 0;
  font-size: 10.5px;
  padding: 2px 8px;
  border-radius: 999px;
  background: var(--sx-bg-surface-2);
  color: var(--sx-text);
}
.sr-badge {
  flex-shrink: 0;
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 999px;
  background: rgba(123, 92, 255, .14);
  color: #7b5cff;
  border: 1px solid rgba(123, 92, 255, .35);
  font-weight: 600;
}
/* 编辑/删除按钮：管理态下在行内常显，彩色胶囊 */
.sr-ops {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
  margin-left: auto;
}
.op-mini {
  display: inline-flex; align-items: center; justify-content: center;
  width: 24px; height: 24px;
  border-radius: 6px;
  background: #7b5cff;
  color: #fff;
  cursor: pointer;
  padding: 0;
  border: none;
  transition: .14s;
  box-shadow: 0 2px 6px rgba(123, 92, 255, .25);
}
.op-mini:hover { filter: brightness(1.08); }
.op-mini.danger {
  background: #e0392f;
  box-shadow: 0 2px 6px rgba(224, 57, 47, .25);
}
.op-icon { font-size: 13px; line-height: 1; pointer-events: none; }

.site-empty {
  margin: auto;
  text-align: center;
  color: var(--sx-text);
  font-size: 13px;
  line-height: 1.8;
  padding: 20px 0;
}
.se-emoji { font-size: 26px; display: block; margin-bottom: 4px; }
.se-tip { font-size: 11.5px; color: var(--sx-text); opacity: .7; }

.sidebar-foot {
  flex-shrink: 0;
  display: flex;
  gap: 8px;
  padding: 12px;
  border-top: 1px solid var(--sx-border);
}
.foot-btn {
  flex: 1;
  padding: 9px 0;
  border-radius: 9px;
  border: 1px solid var(--sx-border);
  background: var(--sx-bg-card);
  color: var(--sx-text-strong);
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  transition: .15s;
}
.foot-btn:hover { border-color: var(--sx-text); color: var(--sx-text-strong); background: var(--sx-bg-surface-2); }
.foot-btn.primary {
  background: linear-gradient(135deg, #ff7a3a, #7b5cff);
  color: #fff; border-color: transparent;
  font-weight: 700;
  text-shadow: 0 1px 2px rgba(0,0,0,.25);
  box-shadow: 0 3px 10px rgba(123,92,255,.25);
}
.foot-btn.primary:hover { filter: brightness(1.05); }

/* 折叠态已删除 rail 元素，改用顶部「› 展开网站列表」按钮 */

/* ===== 占位提示 ===== */
.placeholder {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 0 32px;
}
.big-word {
  font-size: 52px;
  font-weight: 800;
  letter-spacing: 4px;
  background: linear-gradient(135deg, #ff7a3a, #7b5cff);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  text-align: center;
}
.sub-tip { font-size: 15px; color: var(--sx-text); text-align: center; max-width: 560px; }
.reason-list {
  margin: 8px 0 0; padding: 0; list-style: none;
  display: flex; flex-direction: column; gap: 6px;
  font-size: 13.5px; color: var(--sx-text); text-align: center;
}
.reason-list li::before { content: '· '; color: var(--sx-accent); font-weight: 700; }

/* ===== 右侧浏览器 ===== */
.browser { flex: 1; min-width: 0; min-height: 0; display: flex; }
.browser-main { flex: 1; min-width: 0; display: flex; flex-direction: column; }
.tab-bar {
  flex-shrink: 0;
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  padding-bottom: 10px;
  min-height: 36px;
  align-items: center;
}
.tab {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 6px 12px;
  border-radius: 10px 10px 0 0;
  border: 1px solid var(--sx-border);
  border-bottom: none;
  background: var(--sx-bg-surface);
  color: var(--sx-text);
  font-size: 13px;
  cursor: pointer;
  transition: .14s;
}
.tab:hover { border-color: var(--sx-accent); }
.tab.active {
  background: var(--sx-bg-card);
  color: var(--sx-text-strong);
  font-weight: 600;
  box-shadow: 0 -2px 0 0 var(--sx-accent) inset;
}
.tab-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.tab-name { white-space: nowrap; }
.tab-close { font-size: 15px; line-height: 1; opacity: .6; }
.tab-close:hover { opacity: 1; color: #e0392f; }
.tab-empty { color: var(--sx-text); font-size: 13px; }
.browser-view {
  flex: 1;
  min-height: 0;
  border: 1px solid var(--sx-border);
  border-radius: 14px;
  background: var(--sx-bg-card);
  position: relative;
  overflow: hidden;
  box-shadow: var(--sx-shadow-card);
}
.webview { width: 100%; height: 100%; border: none; }
.browser-empty, .browser-fallback {
  position: absolute; inset: 0;
  display: flex; align-items: center; justify-content: center;
  color: var(--sx-text); font-size: 14px; text-align: center; padding: 0 20px;
}

/* ===== 右键菜单 ===== */
.ctx-menu {
  position: fixed; z-index: 2500; min-width: 132px;
  background: var(--sx-bg-elevated); border: 1px solid var(--sx-border);
  border-radius: 10px; box-shadow: 0 8px 28px rgba(0,0,0,.22); padding: 5px;
}
.ctx-item {
  padding: 8px 12px; border-radius: 7px; font-size: 13px; color: var(--sx-text-strong);
  cursor: pointer;
}
.ctx-item:hover { background: var(--sx-bg-surface-2); }
.ctx-item.danger { color: #e0392f; }

/* ===== 弹窗 ===== */
.modal-mask {
  position: fixed; inset: 0; z-index: 2000; background: rgba(20,22,40,.45);
  display: flex; align-items: center; justify-content: center; padding: 20px;
}
.modal {
  width: 100%; max-width: 420px; background: var(--sx-bg-elevated, #fff);
  border-radius: 14px; padding: 22px; box-shadow: 0 10px 40px rgba(0,0,0,.25);
}
.modal-title { margin: 0 0 14px; font-size: 17px; color: var(--sx-text-strong); }
.modal-label { display: block; font-size: 12.5px; color: var(--sx-text); margin: 10px 0 4px; }
.modal-input {
  width: 100%; padding: 8px 10px; border-radius: 8px;
  border: 1px solid var(--sx-border); background: var(--sx-bg-surface); color: var(--sx-text-strong);
  font-size: 14px; box-sizing: border-box;
}
.modal-ops { display: flex; gap: 10px; margin-top: 18px; }
.modal-ops .op-btn { flex: 1; padding: 9px 0; font-size: 14px; }
.confirm-modal { max-width: 360px; }
.confirm-text { margin: 0 0 18px; font-size: 14px; line-height: 1.6; color: var(--sx-text); }

/* 弹窗按钮 */
.op-btn {
  padding: 8px 18px; border-radius: 9px; border: 1px solid var(--sx-border);
  background: var(--sx-bg-surface); color: var(--sx-text); font-size: 14px; cursor: pointer;
  transition: .15s;
}
.op-btn:hover { border-color: var(--sx-accent); color: var(--sx-accent); }
.op-btn.primary { background: linear-gradient(135deg, #ff7a3a, #7b5cff); color: #fff; border-color: transparent; font-weight: 600; }
.op-btn.primary:hover { filter: brightness(1.05); }

/* ===== 分类管理弹窗 ===== */
.cat-list { display: flex; flex-direction: column; gap: 8px; max-height: 46vh; overflow-y: auto; padding: 2px; }
.cat-row { display: flex; align-items: center; gap: 8px; }
.cat-dot { flex-shrink: 0; width: 10px; height: 10px; border-radius: 50%; }
.cat-input { flex: 1; }
.cat-add { display: flex; gap: 8px; margin-top: 14px; }
.cat-add .modal-input { flex: 1; }
.cat-tip { margin: 12px 0 0; font-size: 12px; line-height: 1.6; color: var(--sx-text-soft); }
.op-mini.success { background: #1f9d55; box-shadow: 0 2px 6px rgba(31, 157, 85, .25); }
.op-mini:disabled { opacity: .45; cursor: not-allowed; filter: none !important; }

/* 左侧管理分类按钮：与普通分类同高，但用虚线边框+灰调背景，明显区分 */
.cat-manage-btn {
  border: 1.5px dashed var(--sx-border) !important;
  background: var(--sx-bg-surface) !important;
  color: var(--sx-text) !important;
  box-shadow: none !important;
}
.cat-manage-btn:hover {
  border-color: var(--sx-accent) !important;
  color: var(--sx-accent) !important;
  background: rgba(123, 92, 255, .06) !important;
}

/* ===== 轻提示 ===== */
.toast {
  position: fixed;
  top: 24px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 3000;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 22px;
  border-radius: 10px;
  background: var(--sx-bg-elevated);
  color: var(--sx-text-strong);
  font-size: 14px;
  box-shadow: 0 8px 30px rgba(0,0,0,.22);
  border: 1px solid var(--sx-border);
}
.toast-icon {
  width: 22px; height: 22px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 12px; font-weight: 800; color: #fff; flex-shrink: 0;
}
.toast.warning .toast-icon { background: #f5a623; }
.toast.error .toast-icon { background: #e0392f; }
.toast.success .toast-icon { background: #1f9d55; }
.toast.info .toast-icon { background: var(--sx-accent); }

.toast-enter-active, .toast-leave-active { transition: all .22s ease; }
.toast-enter-from, .toast-leave-to { opacity: 0; transform: translateX(-50%) translateY(-12px); }
</style>
