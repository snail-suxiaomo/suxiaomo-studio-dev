// common/http.js —— 统一请求封装：自动带 token，401 跳登录
import { useAuthStore } from '../login/auth-store.js'
import router from '../router/index.js'

function authHeaders(extra = {}) {
  const auth = useAuthStore()
  const h = { ...extra }
  if (auth.token) h['Authorization'] = `Bearer ${auth.token}`
  return h
}

// 401 统一处理：仅当确实持有 token 时才清除登录态，跳转交给 router（避免整页硬刷新打断操作）
// 打包接口（/api/build/*）是纯本地操作，不应触发退登
function handleUnauthorized(requestPath) {
  // 打包/发布 API 不走退登逻辑（按接口路径判断，比页面路径更可靠）
  if (requestPath && requestPath.startsWith('/build/')) return
  const auth = useAuthStore()
  if (auth.token) auth.logout()
  if (router.currentRoute.value.path !== '/login') {
    router.replace('/login')
  }
  throw new Error('登录已过期')
}

export async function api(path, method = 'GET', body, signal) {
  const res = await fetch(`/api${path}`, {
    method,
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: body ? JSON.stringify(body) : undefined,
    signal,
  })
  if (res.status === 401) return handleUnauthorized(path)
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    const detail = err.detail || '请求失败'
    // 脱敏上报：只报 路径 + 状态码 + 摘要，不报请求体/文件内容
    if (res.status !== 401) {
      reportClientError(`${method} ${path} -> ${res.status}: ${detail}`, {
        url: location.pathname,
      })
    }
    throw new Error(detail)
  }
  return res.json()
}

// 多文件上传（multipart/form-data）：data 是 FormData
export async function apiUpload(path, formData) {
  const res = await fetch(`/api${path}`, {
    method: 'POST',
    headers: authHeaders(),
    body: formData,
  })
  if (res.status === 401) return handleUnauthorized(path)
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    const detail = err.detail || '上传失败'
    if (res.status !== 401) {
      reportClientError(`POST ${path} -> ${res.status}: ${detail}`, {
        url: location.pathname,
      })
    }
    throw new Error(detail)
  }
  return res.json()
}

// 前端错误上报：脱敏 + fire-and-forget + 防递归（上报接口自身失败不再上报）
let _reporting = false
export function reportClientError(message, ctx = {}) {
  if (_reporting) return
  _reporting = true
  try {
    const payload = {
      message: String(message).slice(0, 2000),
      url: String(ctx.url || (typeof location !== 'undefined' ? location.pathname : '')).slice(0, 300),
      stack: ctx.stack ? String(ctx.stack).slice(0, 2000) : undefined,
      time: new Date().toISOString(),
    }
    fetch('/api/logs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }).catch(() => {})
  } finally {
    _reporting = false
  }
}
