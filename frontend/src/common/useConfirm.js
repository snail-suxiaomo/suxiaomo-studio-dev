import { h, render } from 'vue'
import ConfirmDialog from './ConfirmDialog.vue'
import { confirmStore } from './confirmStore.js'
import { useErrorStore } from './error-store.js'

let _instance = null
let _vm = null

function ensureMounted() {
  if (_vm) return _vm
  const container = document.createElement('div')
  document.body.appendChild(container)
  _vm = h(ConfirmDialog)
  render(_vm, container)
  // 兜底：若 ConfirmDialog 尚未在 onMounted 注册 open，则尝试从实例上取
  const exposed = _vm.component.exposed
  const proxy = _vm.component.proxy
  _instance = (exposed && exposed.open) || (proxy && proxy.open) || null
  confirmStore.open = confirmStore.open || _instance
  return _vm
}

function confirm(message, options = {}) {
  ensureMounted()
  const openFn = confirmStore.open || _instance
  return openFn({
    type: 'confirm',
    message,
    title: options.title || '删除确认',
    confirmText: options.confirmText || '确定',
    cancelText: options.cancelText || '取消',
    variant: options.variant || 'danger',
  })
}

function prompt(message, options = {}) {
  ensureMounted()
  const openFn = confirmStore.open || _instance
  return openFn({
    type: 'prompt',
    message,
    title: options.title || '请输入',
    confirmText: options.confirmText || '确定',
    cancelText: options.cancelText || '取消',
    variant: options.variant || 'default',
    inputValue: options.inputValue || '',
    inputPlaceholder: options.inputPlaceholder || '',
  })
}

function alert(message, options = {}) {
  // 改为「当前功能内容区内的非阻塞浮层」，不再弹整页遮罩、不再阻塞侧边栏与其他功能
  try {
    const kind = options.variant === 'danger' ? 'error' : options.kind || 'warning'
    useErrorStore().push(message, {
      kind,
      title: options.title || (kind === 'error' ? '操作失败' : '提示'),
      scope: typeof location !== 'undefined' ? location.pathname : '',
    })
    return Promise.resolve(undefined)
  } catch (e) {
    // store 不可用（极早期）时退化为原弹窗
    ensureMounted()
    const openFn = confirmStore.open || _instance
    if (openFn)
      return openFn({
        type: 'alert',
        message,
        title: options.title || '提示',
        confirmText: options.confirmText || '知道了',
        variant: options.variant || 'default',
      })
    return Promise.resolve(undefined)
  }
}

// 兼容：也作为组合式函数返回
export function useConfirm() {
  return { confirm, alert, prompt }
}

// 推荐：直接导入使用
export { confirm, alert, prompt }
export default { confirm, alert, prompt }
