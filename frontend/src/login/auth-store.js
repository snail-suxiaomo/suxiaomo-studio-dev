// login/auth-store.js —— Pinia 存 token + 当前用户（含 localStorage 持久化）
import { defineStore, acceptHMRUpdate } from 'pinia'
import { meApi } from './auth-api.js'

const TOKEN_KEY = 'sx_token'
const USER_KEY = 'sx_user'

function load(key, def) {
  try { return JSON.parse(localStorage.getItem(key)) ?? def } catch { return def }
}

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem(TOKEN_KEY) || '',
    user: load(USER_KEY, null),
    // 本次会话是否主动退出登录（内存态，应用重启自然归 false）。
    // 作用：区分「应用启动」与「用户主动退出」——
    //   - 主动退出后，即使勾了自动登录也不应再自动登回（停在登录页）；
    //   - 应用重启（relaunch）是全新进程，本标志自然 false → 自动登录照常触发。
    manualLogout: false,
  }),
  getters: {
    isLoggedIn: (s) => !!s.token,
  },
  actions: {
    setSession(token, user) {
      this.token = token
      this.user = user
      this.manualLogout = false
      localStorage.setItem(TOKEN_KEY, token)
      localStorage.setItem(USER_KEY, JSON.stringify(user))
    },
    async restore() {
      // 启动/刷新时只要本地有 token，就必须去 /me 校验；
      // 否则过期 token 会骗过前端，点进功能页才被后端 401 踢登录。
      if (this.token) {
        try {
          this.user = await meApi(this.token)
        } catch {
          this.logout()
        }
      }
    },
    logout() {
      this.token = ''
      this.user = null
      this.manualLogout = true
      localStorage.removeItem(TOKEN_KEY)
      localStorage.removeItem(USER_KEY)
    },
    updateUser(user) {
      this.user = user
      localStorage.setItem(USER_KEY, JSON.stringify(user))
    },
  },
})

// 开发版热更新时保留登录态，避免 HMR 重建 store 导致误退出登录
if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useAuthStore, import.meta.hot))
}
