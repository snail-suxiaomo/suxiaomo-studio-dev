// login/auth-api.js —— 调后端 /api/auth/* 的薄封装
const BASE = '/api/auth'

async function request(url, method, body) {
  let res
  try {
    res = await fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: body ? JSON.stringify(body) : undefined,
    })
  } catch (netErr) {
    // fetch 抛异常：网络断开、CORS、地址不可达等
    throw new Error('网络请求失败：' + (netErr?.message || netErr))
  }
  if (!res.ok) {
    let text = ''
    try {
      text = await res.text()
    } catch (_) {}
    let detail = ''
    try {
      detail = JSON.parse(text).detail || ''
    } catch (_) {}
    throw new Error(
      detail ||
      (text ? `[HTTP ${res.status}] ${text.slice(0, 120)}` : `请求失败 (HTTP ${res.status})`)
    )
  }
  return res.json()
}

export function loginApi(username, password) {
  return request(`${BASE}/login`, 'POST', { username, password })
}

export function registerApi(username, password, display_name) {
  return request(`${BASE}/register`, 'POST', { username, password, display_name })
}

export async function meApi(token) {
  const res = await fetch(`${BASE}/me`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!res.ok) throw new Error('获取当前用户失败')
  return res.json()
}

// ── 记住的账号（多账号下拉 / 记住密码 / 自动登录）──
export function listRemembered() {
  return request(`${BASE}/remembered-accounts`, 'GET')
}

export function getRemembered(username) {
  return request(`${BASE}/remembered-accounts/${encodeURIComponent(username)}`, 'GET')
}

export function saveRemembered(payload) {
  return request(`${BASE}/remembered-accounts`, 'POST', payload)
}

export function deleteRemembered(username) {
  return request(`${BASE}/remembered-accounts/${encodeURIComponent(username)}`, 'DELETE')
}

// 修改当前登录用户的账号名 / 密码 / 昵称（需鉴权）
export async function updateProfile(data) {
  const token = localStorage.getItem('sx_token')
  const res = await fetch(`${BASE}/profile`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(data),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || '修改失败')
  }
  return res.json()
}

// ── 用户管理：查看所有用户、修改任意用户、删除用户（需鉴权）──
export async function listUsers() {
  const token = localStorage.getItem('sx_token')
  const res = await fetch(`${BASE}/users`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!res.ok) throw new Error('获取用户列表失败')
  return res.json()
}

export async function adminUpdateUser(uid, data) {
  const token = localStorage.getItem('sx_token')
  const res = await fetch(`${BASE}/users/${uid}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(data),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || '修改失败')
  }
  return res.json()
}

export async function deleteUser(uid) {
  const token = localStorage.getItem('sx_token')
  const res = await fetch(`${BASE}/users/${uid}`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!res.ok) throw new Error('删除失败')
  return res.json()
}
