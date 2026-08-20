import { createApp } from 'vue'
import { createPinia } from 'pinia'
import './styles/global.css'
import './styles/tokens.css'
import App from './App.vue'
import router from './router/index.js'
import { useAuthStore } from './login/auth-store.js'
import { reportClientError } from './common/http.js'
import { useErrorStore } from './common/error-store.js'

const scopeNow = () => (typeof location !== 'undefined' ? location.pathname : '')

// 兜底：仅在「应用尚未挂载完成」这种极端情况下才退化为整页提示（极少触发）
function showFatal(msg) {
  const el = document.getElementById('app')
  if (el) {
    el.innerHTML =
      '<div style="font-family:system-ui;max-width:760px;margin:60px auto;padding:24px;' +
      'border:1px solid #e25757;border-radius:12px;background:#fff5f5;color:#7a1f1f;line-height:1.6">' +
      '<h2 style="margin:0 0 10px;color:#e25757">页面加载出错</h2>' +
      '<pre style="white-space:pre-wrap;word-break:break-all;font-size:13px;margin:0">' +
      String(msg).replace(/</g, '&lt;') + '</pre></div>'
  }
}

// 统一的「非阻塞浮层」呈现：只在当前功能内容区右上角提示，绝不整页替换、不阻塞侧边栏
function pushError(msg, opts = {}) {
  try {
    useErrorStore().push(msg, { scope: scopeNow(), ...opts })
  } catch {
    showFatal(msg) // store 未就绪（极早期）才走这里
  }
}

window.addEventListener('error', (e) => {
  // 资源加载失败（img/script 等）无 e.error，仅静默上报，避免噪声
  if (e && e.error) {
    const msg = e.error.stack || e.message
    pushError(msg, { kind: 'error' })
    reportClientError(msg, { stack: e.error.stack, url: scopeNow() })
  } else if (e && e.target && e.target !== window) {
    reportClientError('resource load error: ' + (e.target.src || e.target.href || 'unknown'), {
      url: scopeNow(),
    })
  }
})

window.addEventListener('unhandledrejection', (e) => {
  const reason = e.reason
  const msg = (reason && reason.stack) || reason
  pushError(msg, { kind: 'error' })
  reportClientError(msg, { stack: reason && reason.stack, url: scopeNow() })
})

try {
const app = createApp(App)
const pinia = createPinia()
app.use(pinia)

// 组件渲染/生命周期里的未捕获异常：脱敏上报（不影响页面显示）
app.config.errorHandler = (err, instance, info) => {
  const msg = (err && err.stack) || String(err)
  reportClientError(`[vue] ${info}: ${msg}`, { stack: msg, url: location.pathname })
}

// Pinia 激活后再取 store，刷新时若已有 token 则去 /me 校验并还原用户信息。
// 必须 await 完再挂载：否则 token 过期时页面会先按旧 token 渲染，点进功能页才踢登录。
const auth = useAuthStore()
;(async () => {
  try {
    await auth.restore()
  } catch {
    // restore 内部已处理 logout，这里继续挂载即可
  }
  app.use(router)
  app.mount('#app')
})()
} catch (err) {
  showFatal((err && err.stack) || err)
}
