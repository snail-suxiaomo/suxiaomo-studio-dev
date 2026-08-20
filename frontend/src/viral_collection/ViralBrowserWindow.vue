<template>
  <div class="vbw">
    <!-- 顶部工具栏：前进/后退/刷新 + 地址栏 + 快捷站点 -->
    <div class="vbw-bar">
      <button class="vbw-ico" title="后退" @click="wvGoBack">‹</button>
      <button class="vbw-ico" title="前进" @click="wvGoForward">›</button>
      <button class="vbw-ico" title="刷新" @click="wvReload">⟳</button>
      <input
        class="vbw-url"
        v-model="urlInput"
        @keydown.enter="goUrl"
        placeholder="输入网址，回车打开"
      />
      <button class="vbw-go" @click="goUrl">前往</button>
      <div class="vbw-quick">
        <button v-for="s in QUICK_SITES" :key="s.name" class="vbw-chip" @click="goSite(s.url)">
          {{ s.name }}
        </button>
      </div>
    </div>

    <!-- 浏览器视图 -->
    <div ref="wvWrap" class="vbw-view">
      <webview
        ref="wv"
        :src="wvSrc"
        class="vbw-webview"
        partition="persist:viral"
        :useragent="UA"
        @dom-ready="onWvReady"
        @will-navigate="onWvNavigate"
        @will-redirect="onWvNavigate"
        @new-window="onWvNewWindow"
      ></webview>
      <div v-if="!wvSrc" class="vbw-placeholder">
        <p>输入网址或点上方快捷站点开始浏览。</p>
        <p class="tip">登录状态会保存，下次打开不用重新扫码。</p>
      </div>
    </div>

    <!-- 底部：截图操作（截图自动发回「爆款收集」暂存区） -->
    <div class="vbw-foot">
      <span class="vbw-hint">截图会自动发回「爆款收集」暂存区</span>
      <button class="btn ghost sm" :disabled="!wvSrc" @click="captureView">截取浏览器</button>
      <button class="btn ghost sm" @click="captureScreen">截整屏</button>
      <button class="btn ghost sm" @click="captureRegion">框选截图</button>
    </div>

    <!-- 框选截图遮罩 -->
    <div v-if="showRegion" class="vbw-region" @mousedown="regionStart" @mousemove="regionMove" @mouseup="regionEnd">
      <img class="vbw-region-bg" :src="regionBg" draggable="false" />
      <div class="vbw-region-mask"></div>
      <div class="vbw-region-box" :style="regionBoxStyle"></div>
      <div class="vbw-region-tip">按住鼠标拖选区域，松开即截图（按 Esc 取消）</div>
    </div>

    <div v-if="sentToast" class="vbw-toast">已发送截图回「爆款收集」</div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'

const el = () => window.electronAPI || null

// 桌面 UA：浏览器窗口本来就是大窗口，按正常桌面站点渲染（内容不再被挤）
const UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'
const QUICK_SITES = [
  { name: '抖音', url: 'https://www.douyin.com/' },
  { name: '红果', url: 'https://www.hongguoduanju.com/' },
  { name: '快手', url: 'https://www.kuaishou.com/' },
  { name: '视频号', url: 'https://channels.weixin.qq.com/' },
  { name: 'B站', url: 'https://www.bilibili.com/' },
]
const HTTP_RE = /^https?:\/\//i

// 初始 URL 直接作为 webview src，避免先空后设导致 ERR_ABORTED
function getInitUrl() {
  try {
    const init = new URLSearchParams(window.location.search).get('url')
    return normalizeUrl(init)
  } catch (_) { return '' }
}

const wv = ref(null)
const wvWrap = ref(null)
const initUrl = getInitUrl()
const urlInput = ref(initUrl)
const wvSrc = ref(initUrl)
const currentUrl = ref(initUrl)
const capturing = ref(false)
const sentToast = ref('')
let sentTimer = null

function normalizeUrl(u) {
  const s = String(u || '').trim()
  if (!s) return ''
  if (/^https?:\/\//i.test(s)) return s
  return 'https://' + s
}
function navTo(u) {
  const url = normalizeUrl(u)
  if (!url) return
  urlInput.value = url
  currentUrl.value = url
  if (wv.value && typeof wv.value.loadURL === 'function') {
    try { wv.value.loadURL(url); return } catch (e) { /* 落到重建 */ }
  }
  wvSrc.value = url
}
function goUrl() { navTo(urlInput.value) }
function goSite(url) { navTo(url) }

function wvGoBack() { try { wv.value?.goBack() } catch (e) { /* ignore */ } }
function wvGoForward() { try { wv.value?.goForward() } catch (e) { /* ignore */ } }
function wvReload() { try { wv.value?.reload() } catch (e) { /* ignore */ } }

// 主进程把 window.open 的 http(s) URL 发回，让本窗口 webview 内打开（替代新窗口）
function onOpenInSameWebview(_event, url) {
  if (!url) return
  navTo(url)
}

function onWvReady() {
  // 只用于同步 webview 真实 URL，不再重复 addEventListener（模板已绑定）
  try { currentUrl.value = wv.value?.getURL?.() || currentUrl.value } catch (_) {}
}
function onWvNavigate(e) {
  const url = e?.url || ''
  if (url) currentUrl.value = url
  if (!HTTP_RE.test(url)) {
    try { e.preventDefault?.() } catch (_) {}
    console.log('[vbw] blocked non-http navigation:', url)
  }
}
function onWvNewWindow(e) {
  const url = e?.url || ''
  if (!HTTP_RE.test(url)) {
    try { e.preventDefault?.() } catch (_) {}
    console.log('[vbw] blocked non-http new-window:', url)
  }
}

// 截图后统一发回主窗口暂存区
async function sendScreenshot(dataUrl) {
  const api = el()
  if (!dataUrl) return
  if (api && api.sendTrayScreenshot) {
    api.sendTrayScreenshot(dataUrl)
  }
  sentToast.value = '已发送截图回「爆款收集」'
  clearTimeout(sentTimer)
  sentTimer = setTimeout(() => { sentToast.value = '' }, 2000)
}

// 截取浏览器区域（webview 那一块）
async function captureView() {
  if (!el()?.capturePage) { return }
  const box = wvWrap.value?.getBoundingClientRect()
  capturing.value = true
  try {
    const rect = box ? { x: box.left, y: box.top, width: box.width, height: box.height } : null
    const dataUrl = await el().capturePage(rect)
    if (!dataUrl) return
    await sendScreenshot(dataUrl)
  } catch (e) {
    console.error('[vbw] captureView failed', e)
  } finally {
    capturing.value = false
  }
}

// 截整屏
async function captureScreen() {
  if (!el()?.captureScreen) return
  capturing.value = true
  try {
    const dataUrl = await el().captureScreen()
    if (!dataUrl) return
    await sendScreenshot(dataUrl)
  } finally {
    capturing.value = false
  }
}

// 框选截图：先截整屏，弹出遮罩让用户拖选区域，松开后裁剪该区域发回
const showRegion = ref(false)
const regionBg = ref('')
const regionRect = reactive({ x: 0, y: 0, w: 0, h: 0 })
let regionStartPt = null
const regionBoxStyle = computed(() => ({
  left: regionRect.x + 'px',
  top: regionRect.y + 'px',
  width: regionRect.w + 'px',
  height: regionRect.h + 'px',
}))
async function captureRegion() {
  if (!el()?.captureScreen) return
  const dataUrl = await el().captureScreen()
  if (!dataUrl) return
  regionBg.value = dataUrl
  regionRect.x = regionRect.y = regionRect.w = regionRect.h = 0
  regionStartPt = null
  showRegion.value = true
}
function regionStart(e) {
  regionStartPt = { x: e.clientX, y: e.clientY }
  regionRect.x = e.clientX
  regionRect.y = e.clientY
  regionRect.w = 0
  regionRect.h = 0
}
function regionMove(e) {
  if (!regionStartPt) return
  const x = Math.min(e.clientX, regionStartPt.x)
  const y = Math.min(e.clientY, regionStartPt.y)
  regionRect.x = x
  regionRect.y = y
  regionRect.w = Math.abs(e.clientX - regionStartPt.x)
  regionRect.h = Math.abs(e.clientY - regionStartPt.y)
}
async function regionEnd() {
  if (!regionStartPt) return
  const sx = regionRect.x
  const sy = regionRect.y
  const sw = regionRect.w
  const sh = regionRect.h
  regionStartPt = null
  showRegion.value = false
  if (sw < 4 || sh < 4) return
  const dpr = window.devicePixelRatio || 1
  try {
    const img = new Image()
    img.src = regionBg.value
    await new Promise((res) => { img.onload = res })
    const canvas = document.createElement('canvas')
    canvas.width = Math.round(sw * dpr)
    canvas.height = Math.round(sh * dpr)
    const ctx = canvas.getContext('2d')
    ctx.drawImage(img, sx * dpr, sy * dpr, sw * dpr, sh * dpr, 0, 0, canvas.width, canvas.height)
    const cropped = canvas.toDataURL('image/png')
    await sendScreenshot(cropped)
  } catch (err) {
    console.error('[vbw] region crop failed', err)
  }
}
function cancelRegion() { showRegion.value = false; regionStartPt = null }

function onRegionKey(e) {
  if (e.key === 'Escape') cancelRegion()
}

onMounted(() => {
  if (el() && el().onOpenInSameWebview) {
    el().onOpenInSameWebview(onOpenInSameWebview)
  }
  window.addEventListener('keydown', onRegionKey)
})
onBeforeUnmount(() => {
  window.removeEventListener('keydown', onRegionKey)
  if (el() && el().offOpenInSameWebview) {
    el().offOpenInSameWebview(onOpenInSameWebview)
  }
  clearTimeout(sentTimer)
})
</script>

<style scoped>
.vbw { display: flex; flex-direction: column; height: 100vh; width: 100vw; background: #f5f6f8; }
.vbw-bar {
  display: flex; align-items: center; gap: 8px; padding: 8px 12px;
  background: #fff; border-bottom: 1px solid #e6e8eb;
}
.vbw-ico {
  width: 32px; height: 32px; border: 1px solid #d8dbe0; background: #fff; border-radius: 8px;
  font-size: 18px; line-height: 1; cursor: pointer; color: #333;
}
.vbw-ico:hover { background: #f0f2f5; }
.vbw-url {
  flex: 1; min-width: 120px; height: 32px; padding: 0 12px; border: 1px solid #d8dbe0;
  border-radius: 8px; font-size: 13px; outline: none;
}
.vbw-url:focus { border-color: #4c8dff; }
.vbw-go {
  height: 32px; padding: 0 14px; border: 0; border-radius: 8px; background: #4c8dff; color: #fff;
  cursor: pointer; font-size: 13px;
}
.vbw-quick { display: flex; gap: 6px; }
.vbw-chip {
  height: 30px; padding: 0 10px; border: 1px solid #d8dbe0; background: #fff; border-radius: 16px;
  font-size: 12px; cursor: pointer; color: #333; white-space: nowrap;
}
.vbw-chip:hover { background: #f0f2f5; }

.vbw-view { position: relative; flex: 1; min-height: 0; background: #fff; }
.vbw-webview { width: 100%; height: 100%; display: inline-flex; border: 0; }
.vbw-placeholder {
  position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center;
  color: #888; font-size: 13px; gap: 6px; text-align: center;
}
.vbw-placeholder .tip { color: #aaa; font-size: 12px; }

.vbw-foot {
  display: flex; align-items: center; gap: 10px; padding: 8px 12px; background: #fff;
  border-top: 1px solid #e6e8eb;
}
.vbw-hint { font-size: 12px; color: #999; margin-right: auto; }

.vbw-region { position: fixed; inset: 0; z-index: 9999; cursor: crosshair; }
.vbw-region-bg { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: none; user-select: none; }
.vbw-region-mask { position: absolute; inset: 0; background: rgba(0,0,0,0.45); }
.vbw-region-box {
  position: absolute; border: 2px solid #4c8dff; background: rgba(76,141,255,0.12);
  pointer-events: none;
}
.vbw-region-tip {
  position: absolute; left: 50%; top: 16px; transform: translateX(-50%);
  background: rgba(0,0,0,0.7); color: #fff; padding: 6px 12px; border-radius: 6px; font-size: 12px;
}

.vbw-toast {
  position: fixed; left: 50%; bottom: 64px; transform: translateX(-50%);
  background: rgba(0,0,0,0.8); color: #fff; padding: 8px 16px; border-radius: 8px; font-size: 13px; z-index: 10000;
}
</style>
