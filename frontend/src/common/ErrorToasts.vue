<template>
  <div class="toast-layer" aria-live="polite">
    <transition-group name="toast" tag="div" class="toast-stack">
      <div
        v-for="item in visible"
        :key="item.id"
        class="toast"
        :class="'toast--' + item.kind"
        @click="dismiss(item.id)"
        role="alert"
      >
        <span class="toast-ic" v-html="iconFor(item.kind)"></span>
        <div class="toast-main">
          <div class="toast-title">{{ item.title }}</div>
          <div class="toast-msg">{{ item.message }}</div>
        </div>
        <button class="toast-x" @click.stop="dismiss(item.id)" aria-label="关闭">×</button>
      </div>
    </transition-group>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { useErrorStore, AUTO_DISMISS_MS_EXPORT } from './error-store.js'

const errors = useErrorStore()
const route = useRoute()

// 只显示「当前功能」作用域内的消息：切到免费资源 / 文件空间等互不影响
const visible = computed(() =>
  errors.items.filter((i) => i.scope === route.path)
)

function dismiss(id) {
  errors.dismiss(id)
}

function iconFor(kind) {
  if (kind === 'success') {
    return '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>'
  }
  if (kind === 'warning' || kind === 'info') {
    return '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>'
  }
  return '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>'
}

let timer = null
function tick() {
  const now = Date.now()
  const expired = errors.items
    .filter((i) => now - i.time > AUTO_DISMISS_MS_EXPORT)
    .map((i) => i.id)
  expired.forEach((id) => errors.dismiss(id))
}
onMounted(() => {
  timer = setInterval(tick, 1000)
})
onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<style scoped>
/* 关键：整层 pointer-events:none，不阻挡下方任何点击（侧边栏 / 其他功能照常可操作） */
.toast-layer {
  position: fixed;
  top: 16px;
  right: 18px;
  z-index: 9000; /* 低于 confirm 弹窗(9999)，高于普通内容 */
  pointer-events: none;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 10px;
  width: min(360px, calc(100vw - 280px)); /* 不越过左侧 248px 侧边栏 */
  max-height: 70vh;
}

.toast {
  pointer-events: auto; /* 浮层自身可点击关闭，但不影响周围 */
  display: flex;
  align-items: flex-start;
  gap: 10px;
  width: 100%;
  padding: 12px 12px 12px 14px;
  border-radius: 12px;
  background: #fff;
  border: 1px solid #e7e9f2;
  border-left: 4px solid #e25757;
  box-shadow: 0 10px 30px rgba(20, 22, 40, 0.14);
  cursor: pointer;
  color: #1b1f3b;
  font-family: system-ui, -apple-system, "Segoe UI", Roboto, "PingFang SC", "Microsoft YaHei", sans-serif;
}
.toast--success { border-left-color: #2faa6a; }
.toast--warning,
.toast--info { border-left-color: #f0a020; }
.toast--error { border-left-color: #e25757; }

.toast-ic {
  flex-shrink: 0;
  width: 20px;
  height: 20px;
  margin-top: 1px;
  display: inline-flex;
}
.toast--error .toast-ic { color: #e25757; }
.toast--success .toast-ic { color: #2faa6a; }
.toast--warning .toast-ic,
.toast--info .toast-ic { color: #f0a020; }

.toast-main { flex: 1; min-width: 0; }
.toast-title {
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 2px;
}
.toast-msg {
  font-size: 13px;
  line-height: 1.5;
  color: #4b5168;
  word-break: break-word;
  white-space: pre-line;
}
.toast-x {
  flex-shrink: 0;
  border: none;
  background: transparent;
  color: #9aa0b5;
  font-size: 18px;
  line-height: 1;
  cursor: pointer;
  padding: 0 2px;
}
.toast-x:hover { color: #4b5168; }

.toast-enter-active,
.toast-leave-active {
  transition: opacity 0.22s ease, transform 0.22s ease;
}
.toast-enter-from {
  opacity: 0;
  transform: translateX(16px);
}
.toast-leave-to {
  opacity: 0;
  transform: translateX(16px);
}
</style>
