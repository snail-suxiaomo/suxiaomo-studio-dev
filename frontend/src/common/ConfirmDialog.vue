<template>
  <Teleport to="body">
    <Transition name="cd-fade">
      <div v-if="visible" class="cd-overlay" @click.self="onCancel">
        <div class="cd-card" role="dialog" aria-modal="true">
          <div class="cd-header">
            <span class="cd-icon" v-html="iconSvg"></span>
            <h3 class="cd-title">{{ title }}</h3>
          </div>
          <div class="cd-body">
            <p class="cd-message">{{ message }}</p>
            <input
              v-if="type === 'prompt'"
              ref="inputRef"
              v-model="inputValue"
              type="text"
              class="cd-input"
              :placeholder="inputPlaceholder"
              @keydown.enter.prevent="onConfirm"
            />
          </div>
          <div class="cd-actions">
            <button :class="['cd-btn', confirmClass]" @click="onConfirm">
              {{ confirmText }}
            </button>
            <button v-if="type !== 'alert'" class="cd-btn cd-btn-secondary" @click="onCancel">
              {{ cancelText }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { computed, reactive, toRefs, onMounted, onUnmounted, ref, nextTick, watch } from 'vue'
import { confirmStore } from './confirmStore.js'

const state = reactive({
  visible: false,
  type: 'confirm', // confirm | alert | prompt
  title: '提示',
  message: '',
  confirmText: '确定',
  cancelText: '取消',
  variant: 'default', // default | danger
  inputValue: '',
  inputPlaceholder: '',
  resolve: null,
  reject: null,
})

const inputRef = ref(null)

const { visible, type, title, message, confirmText, cancelText, variant, inputValue, inputPlaceholder } = toRefs(state)

const confirmClass = computed(() =>
  variant.value === 'danger' ? 'cd-btn-danger' : 'cd-btn-primary'
)

const iconSvg = computed(() => {
  if (variant.value === 'danger') {
    // trash-2
    return `<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path><line x1="10" y1="11" x2="10" y2="17"></line><line x1="14" y1="11" x2="14" y2="17"></line></svg>`
  }
  // alert-circle
  return `<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>`
})

function open(options = {}) {
  return new Promise((resolve, reject) => {
    state.type = options.type || 'confirm'
    state.title = options.title || (state.type === 'alert' ? '提示' : '请确认')
    state.message = options.message || ''
    state.confirmText = options.confirmText || '确定'
    state.cancelText = options.cancelText || '取消'
    state.variant = options.variant || 'default'
    state.inputValue = options.inputValue || ''
    state.inputPlaceholder = options.inputPlaceholder || ''
    state.resolve = resolve
    state.reject = reject
    state.visible = true
    if (state.type === 'prompt') {
      nextTick(() => inputRef.value?.focus())
    }
  })
}

watch(visible, (v) => {
  if (!v) state.inputValue = ''
})

function close(result) {
  state.visible = false
  if (state.resolve) state.resolve(result)
  state.resolve = null
  state.reject = null
}

function onConfirm() {
  if (state.type === 'prompt') {
    close(state.inputValue.trim())
    return
  }
  close(true)
}

function onCancel() {
  if (state.type === 'alert') {
    close(undefined)
    return
  }
  close(false)
}

// 按 Esc 关闭
function onKey(e) {
  if (e.key === 'Escape' && state.visible) onCancel()
}
onMounted(() => {
  window.addEventListener('keydown', onKey)
  // 注册 open 方法到共享 store，供 useConfirm 直接调用（绕过 exposed/proxy 访问问题）
  confirmStore.open = open
})
onUnmounted(() => window.removeEventListener('keydown', onKey))

defineExpose({ open })
</script>

<style>
.cd-overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.cd-card {
  background: #fff;
  border-radius: 16px;
  width: 100%;
  max-width: 420px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.2);
  overflow: hidden;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}

.cd-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 22px 24px 10px;
}

.cd-icon {
  display: flex;
  color: #7c3aed;
}

.cd-title {
  margin: 0;
  font-size: 17px;
  font-weight: 600;
  color: #1f2937;
  line-height: 1.3;
}

.cd-body {
  padding: 4px 24px 22px;
}

.cd-message {
  margin: 0;
  font-size: 14px;
  line-height: 1.7;
  color: #4b5563;
  white-space: pre-line;
}

.cd-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 0 24px 24px;
}

.cd-input {
  width: 100%;
  margin-top: 12px;
  padding: 10px 12px;
  border: 1.5px solid #e5e7eb;
  border-radius: 10px;
  font-size: 14px;
  color: #1f2937;
  background: #f9fafb;
  transition: border-color .15s, box-shadow .15s, background .15s;
  box-sizing: border-box;
}

.cd-input:focus {
  outline: none;
  border-color: #8b5cf6;
  background: #fff;
  box-shadow: 0 0 0 3px rgba(139, 92, 246, .18);
}

.cd-btn {
  min-width: 80px;
  padding: 9px 18px;
  border-radius: 10px;
  border: none;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: transform 0.08s, box-shadow 0.15s, background 0.15s;
}

.cd-btn:active {
  transform: translateY(1px);
}

.cd-btn-primary {
  background: #7c3aed;
  color: #fff;
}

.cd-btn-primary:hover {
  background: #6d28d9;
  box-shadow: 0 4px 12px rgba(124, 58, 237, 0.28);
}

.cd-btn-danger {
  background: #ef4444;
  color: #fff;
}

.cd-btn-danger:hover {
  background: #dc2626;
  box-shadow: 0 4px 12px rgba(239, 68, 68, 0.28);
}

.cd-btn-secondary {
  background: #f3f4f6 !important;
  color: #374151 !important;
  border: 1px solid #e5e7eb !important;
}

.cd-btn-secondary:hover {
  background: #e5e7eb !important;
  border-color: #d1d5db !important;
  color: #1f2937 !important;
}

.cd-fade-enter-active,
.cd-fade-leave-active {
  transition: opacity 0.2s ease;
}

.cd-fade-enter-from,
.cd-fade-leave-to {
  opacity: 0;
}

.cd-fade-enter-active .cd-card,
.cd-fade-leave-active .cd-card {
  transition: transform 0.2s ease, opacity 0.2s ease;
}

.cd-fade-enter-from .cd-card,
.cd-fade-leave-to .cd-card {
  transform: scale(0.96);
  opacity: 0;
}

@media (max-width: 480px) {
  .cd-actions {
    flex-direction: column;
  }

  .cd-btn {
    width: 100%;
  }
}
</style>
