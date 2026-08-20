<template>
  <div class="settings-page">
    <header class="settings-head">
      <h1 class="settings-title">设置</h1>
      <p class="settings-desc">管理界面外观与数据存储路径</p>
    </header>

    <section class="settings-card">
      <div class="card-header">
        <div class="card-icon">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="5" />
            <path d="M12 1v2" />
            <path d="M12 21v2" />
            <path d="M4.22 4.22l1.42 1.42" />
            <path d="M18.36 18.36l1.42 1.42" />
            <path d="M1 12h2" />
            <path d="M21 12h2" />
            <path d="M4.22 19.78l1.42-1.42" />
            <path d="M18.36 5.64l1.42-1.42" />
          </svg>
        </div>
        <div>
          <h2 class="card-title">界面外观</h2>
          <p class="card-subtitle">切换整体工作区背景风格</p>
        </div>
      </div>

      <div class="theme-options">
        <label
          v-for="opt in themeOptions"
          :key="opt.value"
          class="theme-option"
          :class="{ active: theme === opt.value }"
          @click="setTheme(opt.value)"
        >
          <div class="theme-preview" :class="opt.value">
            <div class="theme-sidebar"></div>
            <div class="theme-content">
              <div class="theme-bar"></div>
              <div class="theme-card"></div>
            </div>
          </div>
          <div class="theme-info">
            <span class="theme-name">{{ opt.label }}</span>
            <span class="theme-desc">{{ opt.desc }}</span>
          </div>
          <span v-if="theme === opt.value" class="theme-check">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="20 6 9 17 4 12" />
            </svg>
          </span>
        </label>
      </div>
    </section>

    <section class="settings-card">
      <div class="card-header">
        <div class="card-icon">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
          </svg>
        </div>
        <div>
          <h2 class="card-title">工作空间路径</h2>
          <p class="card-subtitle">所有数据都在这里，可复制保存，切换版本支持永久使用</p>
        </div>
      </div>

      <div class="path-section">
        <div class="path-current">
          <span class="path-label">当前工作空间</span>
          <span class="path-value">{{ pathDisplay }}</span>
          <button class="path-btn open-btn" @click="openDataDir" title="在文件管理器中打开当前正在使用的工作空间">打开当前工作空间</button>
        </div>

        <div class="path-options">
          <label class="path-option" :class="{ active: pathMode === 'default' }" @click="selectPathMode('default')">
            <span class="path-radio"></span>
            <span class="path-name">默认工作路径</span>
            <span class="path-desc">使用软件所在目录下的 workspace 文件夹（含数据库与项目文件，随软件一起移动）</span>
          </label>

          <label class="path-option" :class="{ active: pathMode === 'custom' }" @click="selectPathMode('custom')">
            <span class="path-radio"></span>
            <span class="path-name">自定义路径</span>
            <span class="path-desc">指定到其他磁盘或文件夹，方便统一管理</span>
          </label>
        </div>

        <div v-if="pathMode === 'custom'" class="path-input-wrap">
          <input v-model="customPath" type="text" class="path-input" placeholder="例如：D:/suxiaomo-data" @input="pathDirty = true" />
          <button class="path-btn" @click="choosePath">选择文件夹</button>
        </div>

        <div class="path-actions">
          <button class="path-btn save-btn" :disabled="!pathDirty" @click="savePathSettings">
            {{ pathDirty ? '保存路径设置' : '已保存' }}
          </button>
          <span v-if="pathDirty" class="path-dirty-hint">路径已修改，保存后需重启生效</span>
        </div>

        <div class="path-hint">
          <strong>注意：</strong>所有数据（数据库、项目文件、配置等）都存储在工作空间路径下。复制整个文件夹即可备份；切换版本时将文件夹放到新版本同级目录即可继续使用。修改路径后需重启软件生效。
        </div>
      </div>
    </section>

  </div>

  <!-- 重启确认弹窗 -->
  <div v-if="showRestartDialog" class="dialog-overlay" @click.self="showRestartDialog = false">
    <div class="dialog-box">
      <h3 class="dialog-title">需要重启应用</h3>
      <p class="dialog-body">数据路径已保存，必须重启应用后才会生效。是否立即重启？</p>
      <div class="dialog-actions">
        <button class="dialog-btn secondary" @click="showRestartDialog = false">稍后手动重启</button>
        <button class="dialog-btn primary" @click="restartApp">立即重启</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'

const themeOptions = [
  { value: 'light', label: '默认浅色', desc: '明亮清爽，适合白天使用' },
  { value: 'dark', label: '深色模式', desc: '柔和暗色，夜间更护眼' },
  { value: 'system', label: '跟随系统', desc: '根据系统外观自动切换' }
]

const theme = ref('light')
const pathMode = ref('default')
const customPath = ref('')
const currentDataDir = ref('')
const pathDirty = ref(false)
const showRestartDialog = ref(false)

// 当前路径展示：默认模式不暴露完整文件系统路径，只显示友好说明；
// 自定义模式才显示用户指定的实际路径。
const pathDisplay = computed(() => {
  if (pathMode.value === 'default') {
    return '软件所在目录下的 workspace 文件夹'
  }
  return currentDataDir.value || customPath.value || '（未设置）'
})

async function loadSettings() {
  let s = {}
  // 桌面版由主进程统一读写 settings.json；浏览器环境兜底 localStorage
  if (window.electronAPI && window.electronAPI.loadSettings) {
    try { s = await window.electronAPI.loadSettings() } catch (e) { s = {} }
  } else {
    try {
      const raw = localStorage.getItem('sxm_settings')
      if (raw) s = JSON.parse(raw)
    } catch (e) { /* ignore */ }
  }
  if (s.theme && themeOptions.some(o => o.value === s.theme)) theme.value = s.theme
  if (s.pathMode) pathMode.value = s.pathMode
  if (s.customPath) customPath.value = s.customPath

  // 桌面版由主进程告知当前数据目录；浏览器环境兜底显示默认位置
  if (window.electronAPI && window.electronAPI.getDataDir) {
    try {
      const d = await window.electronAPI.getDataDir()
      currentDataDir.value = d || '默认位置'
    } catch (e) { currentDataDir.value = '默认位置' }
  } else {
    currentDataDir.value = '默认位置'
  }
}

async function saveSettings() {
  const s = { theme: theme.value, pathMode: pathMode.value, customPath: customPath.value }
  if (window.electronAPI && window.electronAPI.saveSettings) {
    try { await window.electronAPI.saveSettings(s) } catch (e) { /* ignore */ }
  } else {
    localStorage.setItem('sxm_settings', JSON.stringify(s))
  }
}

function setTheme(val) {
  theme.value = val
  applyTheme(val)
  saveSettings()
}

function systemPrefersDark() {
  return !!(window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches)
}

// 跟随系统：挂一个 matchMedia 监听，OS 切换时实时换肤
let themeMediaWatcher = null
function onSystemChange(e) {
  document.documentElement.setAttribute('data-theme', e.matches ? 'dark' : 'light')
}

function applyTheme(val) {
  // 切换前清理上一次的系统监听，避免重复绑定
  if (themeMediaWatcher) {
    themeMediaWatcher.removeEventListener('change', onSystemChange)
    themeMediaWatcher = null
  }
  if (val === 'system') {
    document.documentElement.setAttribute('data-theme', systemPrefersDark() ? 'dark' : 'light')
    themeMediaWatcher = window.matchMedia('(prefers-color-scheme: dark)')
    themeMediaWatcher.addEventListener('change', onSystemChange)
  } else {
    document.documentElement.setAttribute('data-theme', val)
  }
}

async function choosePath() {
  // 桌面版可通过 electronAPI 调原生对话框；浏览器环境仅提示
  if (window.electronAPI && window.electronAPI.selectFolder) {
    const p = await window.electronAPI.selectFolder()
    if (p) {
      customPath.value = p
      pathDirty.value = true
    }
  } else {
    alert('请在输入框中手动填写完整路径，或在桌面版中使用选择文件夹功能。')
  }
}

function selectPathMode(mode) {
  if (pathMode.value !== mode) {
    pathMode.value = mode
    pathDirty.value = true
  }
}

async function savePathSettings() {
  if (!pathDirty.value) return
  const s = { theme: theme.value, pathMode: pathMode.value, customPath: customPath.value }
  if (window.electronAPI && window.electronAPI.saveSettings) {
    try {
      await window.electronAPI.saveSettings(s)
      pathDirty.value = false
      showRestartDialog.value = true
    } catch (e) {
      alert('保存失败：' + (e.message || '未知错误'))
    }
  } else {
    localStorage.setItem('sxm_settings', JSON.stringify(s))
    pathDirty.value = false
    showRestartDialog.value = true
  }
}

async function restartApp() {
  if (window.electronAPI && window.electronAPI.restartApp) {
    try { await window.electronAPI.restartApp() } catch (e) { /* ignore */ }
  } else {
    alert('请手动刷新或重启浏览器页面以使新路径生效。')
  }
}

async function openDataDir() {
  // 桌面版由主进程调用系统文件管理器打开数据根；浏览器环境提示
  if (window.electronAPI && window.electronAPI.openDataDir) {
    try { await window.electronAPI.openDataDir() } catch (e) { /* ignore */ }
  } else {
    alert('桌面版中可一键打开当前工作空间；当前为浏览器环境，请手动前往软件所在目录下的 workspace 文件夹。')
  }
}

onMounted(() => {
  loadSettings().then(() => {
    pathDirty.value = false
    applyTheme(theme.value) // 等 settings.json 里的主题加载完再真正应用
  })
})

onBeforeUnmount(() => {
  if (themeMediaWatcher) {
    themeMediaWatcher.removeEventListener('change', onSystemChange)
    themeMediaWatcher = null
  }
})
</script>

<style scoped>
.settings-page {
  width: 100%;
  min-height: 100%;
  padding-bottom: 40px;
  background: var(--sx-bg-page);
}

.settings-head {
  margin-bottom: 24px;
}
.settings-title {
  font-size: 26px;
  font-weight: 700;
  color: var(--sx-text-strong);
  margin: 0 0 6px;
}
.settings-desc {
  margin: 0;
  color: var(--sx-text);
  font-size: 14px;
}

.settings-card {
  background: var(--sx-bg-surface);
  border: 1px solid var(--sx-border);
  border-radius: 16px;
  padding: 22px;
  margin-bottom: 18px;
  box-shadow: var(--sx-shadow-card);
}
.card-header {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 20px;
}
.card-icon {
  width: 42px;
  height: 42px;
  border-radius: 12px;
  background: var(--sx-icon-bg);
  color: var(--sx-icon-fg);
  display: flex;
  align-items: center;
  justify-content: center;
}
.card-title {
  font-size: 17px;
  font-weight: 700;
  color: var(--sx-text-strong);
  margin: 0 0 2px;
}
.card-subtitle {
  margin: 0;
  font-size: 13px;
  color: var(--sx-text);
}

.theme-options {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
}
.theme-option {
  flex: 0 0 auto;
  width: 220px;
  border: 2px solid var(--sx-border);
  border-radius: 14px;
  padding: 14px;
  cursor: pointer;
  transition: .15s;
  display: flex;
  flex-direction: column;
  gap: 12px;
  position: relative;
  background: var(--sx-bg-surface);
}
.theme-option:hover {
  border-color: var(--sx-border-hover);
}
.theme-option.active {
  border-color: var(--sx-accent);
  background: var(--sx-accent-soft);
}
.theme-preview {
  height: 86px;
  width: 100%;
  border-radius: 10px;
  overflow: hidden;
  display: flex;
  border: 1px solid var(--sx-border);
}
.theme-preview.light {
  background: #f4f6fb;
}
.theme-preview.dark {
  background: #1a1d2e;
}
.theme-sidebar {
  width: 28%;
  height: 100%;
}
.theme-preview.light .theme-sidebar {
  background: linear-gradient(180deg, #1b1f3b 0%, #241a52 100%);
}
.theme-preview.dark .theme-sidebar {
  background: linear-gradient(180deg, #121424 0%, #1a122e 100%);
}
.theme-content {
  flex: 1;
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.theme-preview.light .theme-content {
  background: #f4f6fb;
}
.theme-preview.dark .theme-content {
  background: #121424;
}
.theme-bar {
  height: 10px;
  border-radius: 5px;
}
.theme-preview.light .theme-bar {
  background: #e7e9f2;
}
.theme-preview.dark .theme-bar {
  background: #2d3147;
}
.theme-card {
  flex: 1;
  border-radius: 6px;
}
.theme-preview.light .theme-card {
  background: #fff;
  border: 1px solid #e7e9f2;
}
.theme-preview.dark .theme-card {
  background: #242842;
  border: 1px solid #30344d;
}
.theme-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.theme-name {
  font-size: 15px;
  font-weight: 700;
  color: var(--sx-text-strong);
}
.theme-desc {
  font-size: 12px;
  color: var(--sx-text);
}
.theme-check {
  position: absolute;
  top: 12px;
  right: 12px;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: var(--sx-accent);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
}

.path-current {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 16px;
  padding: 12px 14px;
  background: var(--sx-bg-surface-2);
  border-radius: 10px;
}
.path-label {
  font-size: 12px;
  color: var(--sx-text);
}
.path-value {
  font-size: 14px;
  color: var(--sx-text-strong);
  word-break: break-all;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}
.open-btn {
  align-self: flex-start;
  margin-top: 6px;
}
.path-options {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 16px;
}
.path-option {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 14px;
  border: 2px solid var(--sx-border);
  border-radius: 12px;
  cursor: pointer;
  transition: .15s;
  background: var(--sx-bg-surface);
}
.path-option:hover {
  border-color: var(--sx-border-hover);
}
.path-option.active {
  border-color: var(--sx-accent);
  background: var(--sx-accent-soft);
}
.path-radio {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  border: 2px solid var(--sx-border-strong);
  margin-top: 1px;
  flex-shrink: 0;
  position: relative;
}
.path-option.active .path-radio {
  border-color: var(--sx-accent);
}
.path-option.active .path-radio::after {
  content: '';
  position: absolute;
  top: 3px;
  left: 3px;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--sx-accent);
}
.path-name {
  display: block;
  font-size: 14px;
  font-weight: 700;
  color: var(--sx-text-strong);
  margin-bottom: 2px;
}
.path-desc {
  font-size: 12px;
  color: var(--sx-text);
}
.path-input-wrap {
  display: flex;
  gap: 10px;
  margin-bottom: 14px;
}
.path-input {
  flex: 1;
  min-width: 0;
  padding: 10px 12px;
  border: 1px solid var(--sx-border-strong);
  border-radius: 10px;
  font-size: 14px;
  color: var(--sx-text-strong);
  background: var(--sx-bg-surface-2);
}
.path-input:focus {
  outline: none;
  border-color: var(--sx-accent);
  box-shadow: 0 0 0 3px var(--sx-accent-soft);
}
.path-btn {
  padding: 10px 16px;
  border: none;
  border-radius: 10px;
  background: var(--sx-accent);
  color: #fff;
  font-size: 14px;
  cursor: pointer;
  white-space: nowrap;
  transition: .15s;
}
.path-btn:hover {
  background: var(--sx-accent-hover);
}
.path-hint {
  font-size: 12px;
  color: #8b6c3e;
  background: #fff9e6;
  border: 1px solid #f3e2b3;
  border-radius: 10px;
  padding: 10px 12px;
  line-height: 1.5;
}
.path-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 14px;
  flex-wrap: wrap;
}
.path-btn:disabled {
  background: var(--sx-text-muted);
  cursor: not-allowed;
}
.path-dirty-hint {
  font-size: 13px;
  color: var(--sx-accent);
}

/* 重启确认弹窗 */
.dialog-overlay {
  position: fixed;
  inset: 0;
  background: var(--sx-overlay);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}
.dialog-box {
  width: 90%;
  max-width: 400px;
  background: var(--sx-bg-elevated);
  border-radius: 16px;
  padding: 22px;
  box-shadow: var(--sx-shadow-pop);
}
.dialog-title {
  margin: 0 0 10px;
  font-size: 17px;
  font-weight: 700;
  color: var(--sx-text-strong);
}
.dialog-body {
  margin: 0 0 20px;
  font-size: 14px;
  color: var(--sx-text);
  line-height: 1.6;
}
.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
.dialog-btn {
  padding: 9px 16px;
  border-radius: 10px;
  font-size: 14px;
  cursor: pointer;
  border: none;
  transition: .15s;
}
.dialog-btn.secondary {
  background: var(--sx-bg-surface-2);
  color: var(--sx-text);
}
.dialog-btn.secondary:hover {
  background: var(--sx-border);
}
.dialog-btn.primary {
  background: var(--sx-accent);
  color: #fff;
}
.dialog-btn.primary:hover {
  background: var(--sx-accent-hover);
}

@media (max-width: 640px) {
  .theme-options {
    flex-direction: column;
  }
  .path-input-wrap {
    flex-direction: column;
  }
}

</style>