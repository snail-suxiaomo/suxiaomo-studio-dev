// common/error-store.js —— 全局非阻塞错误/提示浮层状态
// 设计要点：
// 1. 每条消息都带 scope（= 当前功能路由 path），浮层只显示「当前功能」的消息，
//    切到别的功能（免费资源 / 文件空间 …）时互不干扰。
// 2. 浮层本身 pointer-events:none，绝不阻塞侧边栏或其他任何功能操作。
// 3. 自动消失 + 手动关闭，不堆积。
import { defineStore } from 'pinia'

let _seq = 0
const MAX_ITEMS = 5 // 同屏最多显示条数，防止刷屏
const AUTO_DISMISS_MS = 8000

function defaultTitle(kind) {
  if (kind === 'success') return '成功'
  if (kind === 'warning') return '提示'
  if (kind === 'info') return '信息'
  return '操作失败'
}

export const AUTO_DISMISS_MS_EXPORT = AUTO_DISMISS_MS

export const useErrorStore = defineStore('global-messages', {
  state: () => ({
    items: [], // { id, message, title, kind, scope, time }
  }),
  actions: {
    push(message, opts = {}) {
      const scope =
        opts.scope || (typeof location !== 'undefined' ? location.pathname : '')
      const kind = opts.kind || 'error' // error | warning | info | success
      const text = String(message == null ? '' : message)
      if (!text.trim()) return null
      const now = Date.now()
      // 去重：同作用域 + 同文案，3s 内不重复弹
      const dup = this.items.find(
        (i) => i.scope === scope && i.message === text && now - i.time < 3000
      )
      if (dup) return dup.id
      const id = ++_seq
      this.items.push({
        id,
        message: text,
        title: opts.title || defaultTitle(kind),
        kind,
        scope,
        time: now,
      })
      if (this.items.length > MAX_ITEMS) {
        this.items.splice(0, this.items.length - MAX_ITEMS)
      }
      return id
    },
    dismiss(id) {
      this.items = this.items.filter((i) => i.id !== id)
    },
    clearScope(scope) {
      if (!scope) return
      this.items = this.items.filter((i) => i.scope !== scope)
    },
    clearAll() {
      this.items = []
    },
  },
})
