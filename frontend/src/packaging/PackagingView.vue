<template>
  <div class="page">
    <header class="page-head">
      <div>
        <h1 class="title">发布版本</h1>
        <p class="subtitle">
          仅开发版可用。设置版本号、勾选要纳入本次发布的功能，点击「开始打包」即可生成可双击运行的 exe。
          打包在<strong>后台进行</strong>，你可以继续操作其他功能，进度与日志实时更新。
        </p>
      </div>
    </header>

    <!-- 不可用提示（非开发版 / 缺前端源码） -->
    <div v-if="!available" class="unavail">
      当前环境不支持打包（仅开发版可用，需检测到前端源码与依赖）。
    </div>

    <div v-else class="body">
      <!-- 版本号 -->
      <section class="card section">
        <h3 class="sec-title">版本号</h3>
        <div class="ver-row">
          <input
            class="ver-input"
            v-model.trim="version"
            placeholder="如 1.0.0"
            maxlength="20"
            @input="versionError = ''"
          />
          <button class="ver-refresh" type="button" @click="loadVersionInfo" title="重新获取代码版本与发布历史">
            刷新
          </button>
          <span v-if="latestRelease" class="ver-prev">历史最新 v{{ latestRelease }}</span>
        </div>
        <div class="ver-hint">将生成目录：<code>suxiaomo-studio-v{{ cleanVersion }}</code></div>
        <p v-if="versionError" class="ver-err">{{ versionError }}</p>
        <p v-else-if="latestRelease || codeVersion" class="ver-tip">
          已根据历史版本自动建议下一版本（可手动修改）
        </p>
      </section>

      <!-- 打包输出目录 -->
      <section class="card section">
        <h3 class="sec-title">打包输出目录</h3>
        <p class="sec-desc">
          产物（<code>suxiaomo-studio-vX.Y.Z</code>）将生成到此目录；默认 <code>F:\suxiaomo-studio-release</code>，可改为任意位置。
        </p>
        <div class="dir-row">
          <input
            class="dir-input"
            v-model.trim="outputDir"
            placeholder="如 F:\suxiaomo-studio-release"
            @input="dirSaved = false"
          />
          <button class="dir-browse" type="button" v-if="canPickFolder" @click="pickFolder">选择文件夹</button>
          <button class="dir-save" type="button" :disabled="dirSaved" @click="saveOutputDir">保存</button>
        </div>
      </section>

      <!-- 功能清单 -->
      <section class="card section">
        <div class="sec-head">
          <h3 class="sec-title">功能清单</h3>
          <span class="sec-count">已选 {{ selectedCount }} / {{ totalCount }} 个</span>
        </div>
        <p class="sec-desc">勾选要纳入本次发布的功能；清单会记录到发布目录的 <code>feature-manifest.json</code>，便于追溯版本包含范围。</p>

        <div class="groups">
          <div class="group" v-for="g in groups" :key="g.name">
            <div class="group-head">
              <span class="group-name">{{ g.name }}</span>
              <div class="group-actions">
                <button class="mini" @click="toggleGroup(g, true)">全选</button>
                <button class="mini" @click="toggleGroup(g, false)">全不选</button>
              </div>
            </div>
            <div class="items">
              <label class="item" v-for="it in g.items" :key="it.key">
                <input type="checkbox" v-model="selected[it.key]" />
                <span>{{ it.label }}</span>
              </label>
            </div>
          </div>
        </div>
      </section>

      <!-- 发布历史（可折叠，避免条数过多撑满页面） -->
      <section class="card section" v-if="releaseHistory.length">
        <div class="sec-head history-head" @click="historyOpen = !historyOpen">
          <div class="history-title">
            <h3 class="sec-title">发布历史</h3>
            <span class="history-caret">{{ historyOpen ? '▾' : '▸' }}</span>
          </div>
          <span class="sec-count">共 {{ releaseHistory.length }} 条</span>
        </div>
        <ul class="rel-list" :class="{ collapsed: !historyOpen }">
          <li v-for="rel in releaseHistory" :key="rel.id" class="rel-item">
            <span class="rel-ver">v{{ rel.version }}</span>
            <span class="rel-time">{{ rel.release_at }}</span>
            <span class="rel-feat">{{ rel.features.length }} 个功能</span>
          </li>
        </ul>
      </section>

      <!-- 开始打包 -->
      <section class="card section">
        <div class="build-row">
          <div class="build-meta">
            <div class="build-status" :class="{ ok: buildDone, err: buildError, run: building }">
              <template v-if="building">打包进行中（后台执行，可继续操作其他功能）</template>
              <template v-else-if="buildDone">✓ 打包完成，产物在 {{ outputDir }}/suxiaomo-studio-v{{ builtVersion }}</template>
              <template v-else-if="buildError">✕ 打包失败，请查看下方日志</template>
              <template v-else>点击下方按钮开始打包</template>
            </div>
          </div>
          <button class="build-btn" :disabled="building || !!versionError || selectedCount === 0" @click="startBuild">
            {{ building ? '打包中…' : '开始打包' }}
          </button>
        </div>
        <div class="log-wrap">
          <button class="copy-btn" v-if="buildLog" @click="copyLog" title="复制日志">复制日志</button>
          <pre class="build-log">{{ buildLog || '（暂无日志）' }}</pre>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount } from 'vue'
import { api } from '../common/http.js'
import { registry } from '../common/features.js'

// 功能清单从功能注册表自动派生：取 checklist:true 的功能，按 group 归入侧边栏分组。
// 与导航栏分类一一对应；注册表新增功能时，清单自动同步，无需手动维护。
const checklistFeatures = Object.entries(registry.features).filter(([, f]) => f.checklist)
const groups = (registry.groups || []).map((name) => ({
  name,
  items: checklistFeatures
    .filter(([, f]) => f.group === name)
    .map(([key, f]) => ({ key, label: f.label })),
})).filter((g) => g.items.length)

const allKeys = groups.flatMap((g) => g.items.map((i) => i.key))

// 默认全选
const selected = reactive({})
for (const k of allKeys) selected[k] = true

const available = ref(false)
const version = ref('')
const versionError = ref('')
const codeVersion = ref('')     // 当前代码版本（desktop/package.json）
const latestRelease = ref('')   // 历史最新已发布版本（app_releases 表）
const releaseHistory = ref([])  // 最近若干条发布记录
const historyOpen = ref(false)  // 发布历史默认折叠
const building = ref(false)
const buildDone = ref(false)
const buildError = ref(false)
const buildLog = ref('')
const outputDir = ref('')
const dirSaved = ref(true)
const canPickFolder = ref(false)
const builtVersion = ref('')  // 记录本次实际打包版本号，避免轮询刷新时 version 输入被建议版本覆盖导致顶部提示错位
let timer = null

const selectedKeys = computed(() => allKeys.filter((k) => selected[k]))
const selectedCount = computed(() => selectedKeys.value.length)
const totalCount = computed(() => allKeys.length)

// 版本号清洗：仅保留数字与点，用于目录名展示
const cleanVersion = computed(() => {
  const m = String(version.value || '').match(/^[\d]+(\.[\d]+)*/)
  return m ? m[0] : '1.0.0'
})

function validateVersion() {
  if (!/^\d+\.\d+\.\d+$/.test(version.value)) {
    versionError.value = '版本号请使用 主.次.修订 格式，例如 1.0.0'
    return false
  }
  versionError.value = ''
  return true
}

function toggleGroup(g, val) {
  for (const it of g.items) selected[it.key] = val
}

async function checkAvailable() {
  try {
    const r = await api('/build/available')
    available.value = !!r.available
  } catch (e) {
    available.value = false
  }
}

async function loadSelection() {
  try {
    const r = await api('/build/selection')
    if (Array.isArray(r.features) && r.features.length) {
      for (const k of allKeys) selected[k] = r.features.includes(k)
    }
  } catch (e) {
    // 读取失败用默认值，不影响打包
  }
}

async function loadOutputDir() {
  try {
    const r = await api('/build/output-dir')
    if (r.ok && r.output_dir) outputDir.value = r.output_dir
  } catch (e) {
    // 读取失败保留空，由占位提示兜底
  }
}

async function loadVersionInfo() {
  try {
    const rel = await api('/build/releases')
    releaseHistory.value = Array.isArray(rel.list) ? rel.list : []
  } catch (e) {
    releaseHistory.value = []
  }
  try {
    const r = await api('/build/version-info')
      if (r.ok) {
        codeVersion.value = r.code_version || ''
        latestRelease.value = r.latest_release || ''
        if (r.suggested && /^\d+\.\d+\.\d+$/.test(r.suggested)) {
          // 只在输入框为空或非法时才自动填充建议版本，避免覆盖用户已输入/已构建的版本
          if (!version.value || !/^\d+\.\d+\.\d+$/.test(version.value)) {
            version.value = r.suggested
          }
        }
      }
  } catch (e) {
    // 读取失败不影响打包，保留已有输入
  }
}

async function saveOutputDir() {
  const d = outputDir.value.trim()
  if (!d) return
  try {
    const r = await api('/build/output-dir', 'POST', { output_dir: d })
    if (r.ok) {
      outputDir.value = r.output_dir
      dirSaved.value = true
    }
  } catch (e) {
    // 保存失败静默，用户可重试
  }
}

function pickFolder() {
  if (window.electronAPI && window.electronAPI.selectFolder) {
    window.electronAPI.selectFolder().then((p) => {
      if (p) {
        outputDir.value = p
        dirSaved.value = false
      }
    })
  }
}

async function startBuild() {
  if (!validateVersion()) return
  if (selectedCount.value === 0) {
    buildError.value = true
    building.value = false
    buildLog.value = '请至少勾选一个功能'
    return
  }
  building.value = true
  buildDone.value = false
  buildError.value = false
  builtVersion.value = version.value
  buildLog.value = '已提交打包任务，后端正在后台执行…（可继续操作其他功能，进度实时更新）'

  // 1) 通知后端后台启动 build.js（不退出应用），传入版本 / 功能 / 输出目录
  try {
    const r = await api('/build/start', 'POST', {
      features: selectedKeys.value,
      version: version.value,
      outputDir: outputDir.value,
    })
    if (!r.ok) {
      buildError.value = true
      building.value = false
      buildLog.value = r.msg || '启动失败'
      return
    }
  } catch (e) {
    buildError.value = true
    building.value = false
    buildLog.value = '[启动失败] ' + (e.message || '未知错误')
    return
  }

  // 2) 轮询后端 /build/status，日志与进度同屏显示
  poll()
}

function poll() {
  if (timer) clearInterval(timer)
  timer = setInterval(async () => {
    try {
      const s = await api('/build/status')
      buildLog.value = s.log || ''
      if (s.done) {
        building.value = false
        buildDone.value = true
        // 优先使用后端返回的本次打包版本号，确保顶部提示与实际产物一致
        builtVersion.value = s.version || builtVersion.value
        clearInterval(timer)
        loadVersionInfo() // 刷新历史最新版本，便于下次打包建议
      } else if (s.error) {
        building.value = false
        buildError.value = true
        clearInterval(timer)
      }
    } catch (e) {
      // 网络抖动不立即判定失败，保留已有日志继续轮询
    }
  }, 1500)
}

function copyLog() {
  navigator.clipboard.writeText(buildLog.value).then(() => {
    const btn = document.querySelector('.copy-btn')
    const orig = btn.textContent
    btn.textContent = '已复制 ✓'
    setTimeout(() => { btn.textContent = orig }, 1500)
  }).catch(() => {
    // fallback: textarea
    const ta = document.createElement('textarea')
    ta.value = buildLog.value
    document.body.appendChild(ta)
    ta.select()
    document.execCommand('copy')
    document.body.removeChild(ta)
    alert('日志已复制')
  })
}

onMounted(() => {
  checkAvailable()
  loadSelection()
  loadOutputDir()
  loadVersionInfo()
  canPickFolder.value = !!(window.electronAPI && window.electronAPI.selectFolder)
  // 若后端已有进行中的打包，自动恢复轮询（切回本页时也能看到进度）
  try {
    api('/build/status').then((s) => {
      if (s && s.running) poll()
    }).catch(() => {})
  } catch (e) { /* ignore */ }
})
onBeforeUnmount(() => timer && clearInterval(timer))
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
.page-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; flex-wrap: wrap; }
.title { margin: 0; font-size: 22px; font-weight: 700; color: var(--sx-text-strong); }
.subtitle { margin: 6px 0 0; font-size: 13px; color: var(--sx-text); max-width: 720px; line-height: 1.6; }
.subtitle code, .sec-desc code, .ver-hint code {
  display: inline-block; font-family: ui-monospace, Menlo, Consolas, monospace; font-size: 12px;
  background: var(--sx-bg-surface-2); color: var(--sx-accent); padding: 1px 6px; border-radius: 6px;
  border: 1px solid var(--sx-border-strong); word-break: break-all;
}
.body { display: flex; flex-direction: column; gap: 16px; }
.section { background: var(--sx-bg-surface); border: 1px solid var(--sx-border); border-radius: var(--sx-radius-lg); padding: 18px 20px; box-shadow: var(--sx-shadow-card); }

.sec-head { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
.sec-title { margin: 0 0 4px; font-size: 16px; font-weight: 700; color: var(--sx-text-strong); }
.sec-count { font-size: 12px; color: var(--sx-text-muted); }
.sec-desc { margin: 0 0 14px; font-size: 13px; color: var(--sx-text); line-height: 1.6; }

/* 版本号 */
.ver-row { display: flex; align-items: center; gap: 14px; flex-wrap: wrap; }
.ver-input {
  width: 160px;
  font-size: 18px;
  font-weight: 700;
  letter-spacing: .5px;
  padding: 8px 14px;
  border: 2px solid var(--sx-border-strong);
  border-radius: 10px;
  outline: none;
  transition: border-color 0.2s;
  background: var(--sx-bg-surface);
  color: var(--sx-text-strong);
}
.ver-input:focus { border-color: var(--sx-accent); }
.ver-refresh {
  display: inline-flex; align-items: center; justify-content: center;
  height: 36px; padding: 0 12px;
  border: 1px solid var(--sx-border-strong);
  border-radius: 10px;
  background: var(--sx-bg-surface);
  color: var(--sx-text);
  font-size: 13px; font-weight: 600;
  cursor: pointer;
  transition: border-color .2s, color .2s, background .2s;
}
.ver-refresh:hover { border-color: var(--sx-accent); color: var(--sx-accent); background: var(--sx-bg-surface-2); }
.ver-prev {
  font-size: 13px;
  font-weight: 600;
  color: var(--sx-text-muted);
  background: var(--sx-bg-surface-2);
  padding: 4px 12px;
  border-radius: 8px;
  border: 1px solid var(--sx-border);
  white-space: nowrap;
}
.ver-hint { font-size: 13px; color: var(--sx-text); }
.ver-err { margin: 8px 0 0; font-size: 12.5px; color: #e25b5b; }
.ver-tip { margin: 8px 0 0; font-size: 12.5px; color: var(--sx-text); }

/* 打包输出目录 */
.dir-row { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.dir-input {
  flex: 1; min-width: 240px;
  font-size: 13px;
  padding: 8px 12px;
  border: 1px solid var(--sx-border-strong);
  border-radius: 10px;
  outline: none;
  background: var(--sx-bg-surface);
  color: var(--sx-text-strong);
}
.dir-input:focus { border-color: var(--sx-accent); }
.dir-browse, .dir-save {
  height: 36px; padding: 0 14px;
  border: 1px solid var(--sx-border-strong);
  border-radius: 10px;
  background: var(--sx-bg-surface);
  color: var(--sx-text);
  font-size: 13px; font-weight: 600;
  cursor: pointer;
  transition: border-color .2s, color .2s, background .2s;
}
.dir-browse:hover, .dir-save:hover { border-color: var(--sx-accent); color: var(--sx-accent); background: var(--sx-bg-surface-2); }
.dir-save { color: var(--sx-accent); border-color: var(--sx-accent); }
.dir-save:disabled { opacity: .5; cursor: not-allowed; }

/* 发布历史 */
.history-head { cursor: pointer; user-select: none; }
.history-title { display: flex; align-items: center; gap: 8px; }
.history-caret { font-size: 12px; color: var(--sx-text-muted); }
.rel-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 8px; overflow: hidden; transition: max-height .25s ease, opacity .2s ease; max-height: 2000px; opacity: 1; }
.rel-list.collapsed { max-height: 0; opacity: 0; }
.rel-item { display: flex; align-items: center; gap: 14px; padding: 8px 12px; background: var(--sx-bg-surface-2); border: 1px solid var(--sx-border); border-radius: var(--sx-radius); font-size: 13px; }
.rel-ver { font-weight: 700; color: var(--sx-accent); font-family: ui-monospace, Menlo, Consolas, monospace; }
.rel-time { color: var(--sx-text-muted); }
.rel-feat { color: var(--sx-text); margin-left: auto; }

/* 功能清单 */
.groups { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 14px; }
.group { border: 1px solid var(--sx-border); border-radius: var(--sx-radius); padding: 12px 14px; background: var(--sx-bg-surface-2); }
.group-head { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-bottom: 10px; }
.group-name { font-weight: 600; font-size: 13.5px; color: var(--sx-text-strong); }
.group-actions { display: flex; gap: 6px; }
.mini {
  padding: 3px 10px !important; font-size: 12px !important; font-weight: 500 !important;
  color: var(--sx-accent) !important; background: var(--sx-bg-surface) !important; border: 1px solid var(--sx-border-strong) !important;
  border-radius: 7px !important; box-shadow: none !important;
}
.mini:hover { border-color: var(--sx-accent) !important; }
.items { display: flex; flex-direction: column; gap: 8px; }
.item { display: flex; align-items: center; gap: 8px; font-size: 13.5px; color: var(--sx-text); cursor: pointer; }
.item input { margin: 0 !important; }

/* 打包区 */
.build-row { display: flex; align-items: center; justify-content: space-between; gap: 14px; flex-wrap: wrap; margin-bottom: 12px; }
.build-status { font-size: 13.5px; font-weight: 600; }
.build-status.run { color: var(--sx-accent); }
.build-status.ok { color: var(--sx-tag-success-text); }
.build-status.err { color: #e25b5b; }
.build-btn { padding: 10px 26px !important; font-size: 15px !important; font-weight: 600 !important; }
.build-btn:disabled { opacity: .5 !important; cursor: not-allowed !important; }
.log-wrap { position: relative; }
.copy-btn {
  position: absolute; top: 8px; right: 8px; z-index: 2;
  padding: 4px 12px !important; font-size: 12px !important;
  font-weight: 500 !important; color: #c9d1d9 !important;
  background: rgba(255,255,255,0.1) !important; border: 1px solid rgba(255,255,255,0.15) !important;
  border-radius: 6px !important; cursor: pointer; transition: all 0.15s;
  box-shadow: 0 1px 3px rgba(0,0,0,0.2); line-height: 1.6;
}
.copy-btn:hover { background: rgba(255,255,255,0.18) !important; color: #fff !important; border-color: var(--sx-accent) !important; }
.build-log {
  background: #0d1117 !important; color: #c9d1d9 !important; font-size: 12px; line-height: 1.5; border-radius: var(--sx-radius);
  padding: 12px; height: 300px; overflow: auto; white-space: pre-wrap; word-break: break-all;
  margin: 0; font-family: ui-monospace, Menlo, Consolas, monospace;
  position: relative; z-index: 1;
  border: 1px solid rgba(255,255,255,0.08) !important;
}

.unavail {
  background: var(--sx-tag-warn-bg, #fff7ed); border: 1px solid var(--sx-tag-warn-border, #fed7aa); color: var(--sx-tag-warn-text, #b45309);
  border-radius: var(--sx-radius); padding: 14px 16px; font-size: 13.5px;
}
</style>
