<template>
  <!-- 爆款收集·方案 C：独立浏览器窗口路由 /viral-browser 不渲染侧边栏与应用外壳，纯全屏浏览器 -->
  <div v-if="isBrowserWin" class="bw-standalone">
    <router-view />
    <ErrorToasts />
  </div>
  <div v-else class="app-shell" :data-theme="appTheme">
    <aside v-if="auth.user" class="sidebar">
      <!-- 品牌 -->
      <div class="brand">
        <span class="brand-dot"></span>
        <span class="brand-name">suxiaomo<span class="brand-accent">·studio</span></span>
      </div>

      <nav class="nav">
        <!-- 首页 -->
        <router-link to="/home" class="nav-item">
          <span class="nav-icon">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
              <polyline points="9 22 9 12 15 12 15 22" />
            </svg>
          </span>
          <span class="nav-label">首页</span>
        </router-link>

        <!-- 漫剧创作（可折叠分组，默认折叠；点击展开 / 折叠） -->
        <div class="nav-group" :class="{ open: novelOpen }">
          <div class="nav-group-head" @click="novelOpen = !novelOpen">
            <span class="nav-icon">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
                <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
              </svg>
            </span>
            <span class="nav-label">漫剧创作</span>
            <span class="nav-caret">{{ novelOpen ? '▾' : '▸' }}</span>
          </div>
          <div class="nav-group-body">
            <router-link v-for="it in groupItems('漫剧创作')" :key="it.key" :to="it.route" class="nav-sub">
              <span class="nav-emoji">{{ it.emoji }}</span><span>{{ it.label }}</span>
            </router-link>
          </div>
        </div>

        <!-- 工具箱（折叠分组，默认折叠） -->
        <div class="nav-group" :class="{ open: toolboxOpen }">
          <div class="nav-group-head" @click="toolboxOpen = !toolboxOpen">
            <span class="nav-icon">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M14.7 6.3a4 4 0 0 0-5.4 5.4L3 18v3h3l6.3-6.3a4 4 0 0 0 5.4-5.4l-2.6 2.6-2-2 2.6-2.6z" />
              </svg>
            </span>
            <span class="nav-label">工具箱</span>
            <span class="nav-caret">{{ toolboxOpen ? '▾' : '▸' }}</span>
          </div>
          <div class="nav-group-body">
            <router-link v-for="it in groupItems('工具箱')" :key="it.key" :to="it.route" class="nav-sub">
              <span class="nav-emoji">{{ it.emoji }}</span><span>{{ it.label }}</span>
            </router-link>
          </div>
        </div>

        <!-- AI工具（折叠分组，默认折叠） -->
        <div class="nav-group" :class="{ open: createOpen }">
          <div class="nav-group-head" @click="createOpen = !createOpen">
            <span class="nav-icon">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M12 19l7-7 3 3-7 7-3-3z" /><path d="M18 13l-1.5-7.5L2 2l3.5 14.5L13 18l5-5z" /><path d="M2 2l7.586 7.586" /><circle cx="11" cy="11" r="2" />
              </svg>
            </span>
            <span class="nav-label">AI工具</span>
            <span class="nav-caret">{{ createOpen ? '▾' : '▸' }}</span>
          </div>
          <div class="nav-group-body">
            <router-link v-for="it in groupItems('AI工具')" :key="it.key" :to="it.route" class="nav-sub">
              <span class="nav-emoji">{{ it.emoji }}</span><span>{{ it.label }}</span>
            </router-link>
          </div>
        </div>

        <!-- 设置与帮助（折叠分组，默认折叠） -->
        <div class="nav-group" :class="{ open: helpOpen }">
          <div class="nav-group-head" @click="helpOpen = !helpOpen">
            <span class="nav-icon">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="12" cy="12" r="3" />
                <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1V13a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 .51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1V13a2 2 0 0 1-2 2 2 2 0 0 1-2-2h-.09a1.65 1.65 0 0 0-1.51 1z" />
              </svg>
            </span>
            <span class="nav-label">设置与帮助</span>
            <span class="nav-caret">{{ helpOpen ? '▾' : '▸' }}</span>
          </div>
          <div class="nav-group-body">
            <router-link v-for="it in groupItems('设置与帮助')" :key="it.key" :to="it.route" class="nav-sub">
              <span class="nav-emoji">{{ it.emoji }}</span><span>{{ it.label }}</span>
            </router-link>
          </div>
        </div>

        <!-- 日志查看（仅开发版可见） -->
        <router-link v-if="isDev" to="/log-viewer" class="nav-item">
          <span class="nav-icon">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
              <line x1="8" y1="13" x2="16" y2="13" />
              <line x1="8" y1="17" x2="16" y2="17" />
              <line x1="10" y1="9" x2="10" y2="9" />
            </svg>
          </span>
          <span class="nav-label">日志查看</span>
        </router-link>

        <!-- 发布版本（仅开发版可见） -->
        <router-link v-if="isDev" to="/packaging" class="nav-item">
          <span class="nav-icon">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <line x1="16.5" y1="9.4" x2="7.5" y2="4.21" />
              <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />
              <polyline points="3.27 6.96 12 12.01 20.73 6.96" />
              <line x1="12" y1="22.08" x2="12" y2="12" />
            </svg>
          </span>
          <span class="nav-label">发布版本</span>
        </router-link>
      </nav>

      <!-- 底部用户卡 -->
      <div class="side-foot">
        <div class="user">
          <div class="avatar">{{ userInitial }}</div>
          <div class="user-meta">
            <div class="user-name">{{ auth.user.display_name || auth.user.username }}</div>
            <div class="user-handle">@{{ auth.user.username }}</div>
          </div>
        </div>
        <div class="side-foot-actions">
          <button class="foot-btn restart" title="重启应用（开发版 / 正式版通用）" @click="restartApp">重启</button>
          <button class="foot-btn logout" @click="logout">退出</button>
        </div>
      </div>
    </aside>

    <main class="content">
      <router-view />
      <!-- 全局非阻塞错误/提示浮层：仅当前功能内容区右上角，不阻塞侧边栏与其他功能 -->
      <ErrorToasts />
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from './login/auth-store.js'
import { isEnabled, registry } from './common/features.js'
import ErrorToasts from './common/ErrorToasts.vue'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

// /viral-browser 是独立浏览器窗口（方案 C），不走应用外壳/侧边栏
const isBrowserWin = computed(() => route.path === '/viral-browser')

// 漫剧创作分组：默认折叠；仅用户点击分组头部时展开 / 折叠
// 其他带折叠分组的导航也采用同一规则：首次启动不展开，点击才展开
const novelOpen = ref(false)
// 日志查看仅开发版可见（打包版不暴露入口）
const isDev = import.meta.env.DEV

// 侧边栏数据驱动：从功能注册表派生，仅渲染「已启用 + 顶层(parent=null) + 有 emoji」的功能。
// 禁用功能不显示入口（与路由、后端接口一致：完全从包里移除）。
const navItems = Object.entries(registry.features)
  .filter(([k, f]) => !f.core && f.parent === null && f.emoji && isEnabled(k))
  .map(([key, f]) => ({ key, label: f.label, route: f.route, group: f.group, emoji: f.emoji, dev: f.dev, sortOrder: f.sort_order || 0 }))
const groupItems = (name) => {
  const items = navItems.filter((i) => i.group === name)
  // 仅当该分组内有项声明了 sort_order 时才按序排列，避免影响未配置分组的既有顺序
  if (items.some((i) => i.sortOrder)) items.sort((a, b) => a.sortOrder - b.sortOrder || a.label.localeCompare(b.label))
  return items
}

// 主题：读取 localStorage 持久化，并同步到 document 根元素
const appTheme = ref('light')
function loadTheme() {
  try {
    const raw = localStorage.getItem('sxm_settings')
    const s = raw ? JSON.parse(raw) : {}
    const stored = s.theme
    if (stored === 'light' || stored === 'dark' || stored === 'system') {
      let resolved = stored
      if (stored === 'system') {
        resolved = (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) ? 'dark' : 'light'
      }
      appTheme.value = resolved
    }
  } catch (e) {
    // ignore
  }
  document.documentElement.setAttribute('data-theme', appTheme.value)
}
onMounted(loadTheme)

const userInitial = computed(() => {
  const name = auth.user?.display_name || auth.user?.username || ''
  return name.charAt(0).toUpperCase()
})

function logout() {
  // 只清登录态 + 置 manualLogout=true（内存标志，应用重启自然归 false）。
  // 登录页据此：退出后停在登录页、账号下拉/勾选状态原样保留，不自动登回；
  // 应用重启（relaunch）时 manualLogout 自然 false → 自动登录照常。
  auth.logout()
  router.push('/login')
}

// 三个新分组的展开状态（默认折叠，点击头部展开 / 折叠）
const createOpen = ref(false)
const toolboxOpen = ref(false)
const helpOpen = ref(false)

// 一键重启应用：开发版 / 正式版通用（主进程 app:restart = relaunch + quit）
function restartApp() {
  if (window.electronAPI && window.electronAPI.restartApp) {
    window.electronAPI.restartApp()
  } else {
    location.reload() // 纯网页版兜底：刷新
  }
}
</script>

<style>
/* ===== 全局主题变量 ===== */
:root {
  --bg-shell: #f4f6fb;
  --bg-content: #f4f6fb;
  --bg-card: #ffffff;
  --bg-input: #ffffff;
  --bg-elevated: #ffffff;
  --text-primary: #1b1f3b;
  --text-secondary: #6e7391;
  --text-muted: #9aa0b8;
  --border-card: #e7e9f2;
  --border-soft: #eef0f6;
  --shadow-card: 0 3px 14px rgba(30, 34, 56, .04);
}
[data-theme="dark"] {
  --bg-shell: #131523;
  --bg-content: #181b2e;
  --bg-card: #232740;
  --bg-input: #1c2036;
  --bg-elevated: #2a2f4d;
  --text-primary: #e8eaf6;
  --text-secondary: #a6acc9;
  --text-muted: #767c9e;
  --border-card: #2e3454;
  --border-soft: #262b45;
  --shadow-card: 0 3px 14px rgba(0, 0, 0, .35);
}
</style>

<style scoped>
.app-shell {
  font-family: system-ui, -apple-system, "Segoe UI", Roboto, "PingFang SC", "Microsoft YaHei", sans-serif;
  --sidebar-width: 200px;
  height: 100vh;
  display: flex;
  background: var(--bg-shell);
  overflow: hidden;
}

/* ===== 深墨侧栏（藏蓝→紫，承载蓝紫身份） ===== */
.sidebar {
  width: var(--sidebar-width);
  flex-shrink: 0;
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: linear-gradient(180deg, #1b1f3b 0%, #241a52 100%);
  color: #e8eaf6;
  box-shadow: 4px 0 24px rgba(20, 22, 40, .12);
  overflow: hidden;
}

.brand {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 18px 16px 14px;
}
.brand-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: linear-gradient(135deg, #7b5cff 0%, #4f7cff 100%);
  box-shadow: 0 0 10px rgba(123, 92, 255, .85);
}
.brand-name {
  font-weight: 700;
  font-size: 15px;
  color: #fff;
  letter-spacing: .3px;
}
.brand-accent {
  color: #a99bff;
  font-weight: 600;
}

/* ===== 导航 ===== */
.nav {
  flex: 1;
  padding: 5px 10px;
  overflow-y: auto;
  /* Firefox */
  scrollbar-width: thin;
  scrollbar-color: rgba(255, 255, 255, .15) transparent;
}
.nav::-webkit-scrollbar { width: 6px; }
.nav::-webkit-scrollbar-track { background: transparent; }
.nav::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, .15);
  border-radius: 3px;
}
.nav::-webkit-scrollbar-thumb:hover { background: rgba(255, 255, 255, .3); }

.nav-item,
.nav-group-head {
  display: flex;
  align-items: center;
  gap: 11px;
  padding: 9px 12px;
  margin: 3px 0;
  border-radius: 10px;
  color: #c3c7e0;
  font-size: 13.5px;
  text-decoration: none !important;
  cursor: pointer;
  transition: background .15s, color .15s;
  user-select: none;
}
.nav-item:hover,
.nav-group-head:hover {
  background: rgba(255, 255, 255, .06);
  color: #fff;
}
.nav-icon {
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #8b90c0;
  flex-shrink: 0;
  transition: color .15s;
}
.nav-item:hover .nav-icon,
.nav-group-head:hover .nav-icon {
  color: #a99bff;
}
.nav-label {
  flex: 1;
}
.nav-caret {
  font-size: 10px;
  color: #7c82b0;
}

/* 选中态：柔和极光药丸（左侧 accent 竖条 + 半透明渐变填充） */
.nav-item.router-link-active {
  background: rgba(124, 92, 255, .16);
  color: #fff;
  box-shadow: inset 3px 0 0 0 #7b5cff;
}
.nav-item.router-link-active .nav-icon {
  color: #b7a6ff;
}

/* ===== 分组折叠 ===== */
.nav-group-body {
  overflow: hidden;
  max-height: 0;
  transition: max-height .25s ease;
}
.nav-group.open .nav-group-body {
  max-height: 400px;
}
.nav-sub {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px 8px 32px;
  margin: 2px 0;
  border-radius: 9px;
  color: #b6bae0;
  font-size: 12px;
  text-decoration: none !important;
  transition: background .15s, color .15s;
  white-space: nowrap;
}
.nav-sub > span:not(.nav-emoji) {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.nav-sub:hover {
  background: rgba(255, 255, 255, .06);
  color: #fff;
}
.nav-sub.router-link-active {
  background: rgba(124, 92, 255, .14);
  color: #fff;
}
.nav-emoji {
  font-size: 14px;
}

/* ===== 底部用户卡 ===== */
.side-foot {
  padding: 12px 14px;
  border-top: 1px solid rgba(255, 255, 255, .08);
}
.user {
  display: flex;
  align-items: center;
  gap: 9px;
  margin-bottom: 9px;
}
.avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: linear-gradient(135deg, #4f7cff 0%, #7b5cff 100%);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 14px;
  flex-shrink: 0;
}
.user-meta {
  min-width: 0;
}
.user-name {
  font-size: 12.5px;
  font-weight: 600;
  color: #fff;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.user-handle {
  font-size: 10.5px;
  color: #8b90c0;
}
.side-foot-actions {
  display: flex;
  gap: 8px;
}
.foot-btn {
  flex: 1;
  padding: 7px 0;
  font-size: 12.5px;
  border-radius: 9px;
  background: rgba(255, 255, 255, .05);
  border: 1px solid rgba(255, 255, 255, .12);
  color: #b8bdd9;
  cursor: pointer;
  transition: .15s;
}
.foot-btn:hover {
  background: rgba(255, 255, 255, .12);
  border-color: rgba(255, 255, 255, .22);
  color: #fff;
}
.foot-btn.restart:hover,
.foot-btn.logout:hover {
  background: rgba(255, 255, 255, .12);
  border-color: rgba(255, 255, 255, .22);
  color: #fff;
}

/* 清除缓存按钮（在「设置与帮助」分组内，复用 nav-sub 外观） */
.cache-btn {
  background: transparent !important;
  border: 0 !important;
  font: inherit;
  text-align: left;
  width: 100%;
  cursor: pointer;
}
.cache-btn:hover { background: #f5f7fd !important; color: #4f7cff !important; }

/* ===== 内容区 ===== */
.content {
  flex: 1;
  min-width: 0;
  height: 100vh;
  padding: 22px 20px;
  overflow-y: auto;
  background: var(--bg-content);
  color: var(--text-primary);
  /* Firefox */
  scrollbar-width: thin;
  scrollbar-color: rgba(123, 92, 255, .35) rgba(20, 22, 40, .04);
}
[data-theme="dark"] .content {
  scrollbar-color: rgba(123, 92, 255, .45) rgba(0, 0, 0, .2);
}
/* WebKit 自定义滚动条 */
.content::-webkit-scrollbar { width: 8px; }
.content::-webkit-scrollbar-track {
  background: rgba(20, 22, 40, .04);
  border-radius: 4px;
}
[data-theme="dark"] .content::-webkit-scrollbar-track {
  background: rgba(0, 0, 0, .2);
}
.content::-webkit-scrollbar-thumb {
  background: rgba(123, 92, 255, .35);
  border-radius: 4px;
  border: 2px solid transparent;
  background-clip: content-box;
}
.content::-webkit-scrollbar-thumb:hover {
  background: rgba(123, 92, 255, .55);
  border-radius: 4px;
  border: 2px solid transparent;
  background-clip: content-box;
}
[data-theme="dark"] .content::-webkit-scrollbar-thumb {
  background: rgba(123, 92, 255, .45);
}

/* ===== 深色模式全局兜底：覆盖子页面写死的浅色基元 ===== */
[data-theme="dark"] .content {
  background: var(--bg-content);
  color: var(--text-primary);
}
/* 输入框 / 下拉统一深色 */
[data-theme="dark"] .content input,
[data-theme="dark"] .content textarea,
[data-theme="dark"] .content select {
  background: var(--bg-input) !important;
  color: var(--text-primary) !important;
  border-color: var(--border-card) !important;
}
[data-theme="dark"] .content input::placeholder,
[data-theme="dark"] .content textarea::placeholder {
  color: var(--text-muted) !important;
}
/* 高频白底容器 → 深色卡片（覆盖写死的 #fff 背景） */
[data-theme="dark"] .content .settings-card,
[data-theme="dark"] .content .card,
[data-theme="dark"] .content .panel,
[data-theme="dark"] .content .stat,
[data-theme="dark"] .content .info-card,
[data-theme="dark"] .content .modal,
[data-theme="dark"] .content .dialog,
[data-theme="dark"] .content .confirm,
[data-theme="dark"] .content .confirm-box,
[data-theme="dark"] .content .tool-card,
[data-theme="dark"] .content .res-card,
[data-theme="dark"] .content .app-card,
[data-theme="dark"] .content .cat-card,
[data-theme="dark"] .content .card-section,
[data-theme="dark"] .content .section,
[data-theme="dark"] .content .bg-card {
  background: var(--bg-card) !important;
  border-color: var(--border-card) !important;
  color: var(--text-primary) !important;
  box-shadow: var(--shadow-card) !important;
}

/* 独立浏览器窗口（方案 C）：不渲染应用外壳，纯全屏浏览器 */
.bw-standalone {
  height: 100vh;
  width: 100vw;
  overflow: hidden;
  background: var(--bg-content);
}
</style>
