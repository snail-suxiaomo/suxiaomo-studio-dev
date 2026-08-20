<template>
  <div v-if="visible" class="lb-mask" @click.self="close">
    <button class="lb-close" @click="close" title="关闭 (Esc)">
      <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6L6 18M6 6l12 12"/></svg>
    </button>
    <button v-if="count > 1" class="lb-nav lb-prev" @click.stop="prev" title="上一张 (←)">
      <svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
    </button>
    <button v-if="count > 1" class="lb-nav lb-next" @click.stop="next" title="下一张 (→)">
      <svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>
    </button>

    <div class="lb-stage">
      <img v-if="cur && isImage(cur)" :src="mediaUrl(cur)" class="lb-img" alt="" />
      <video v-else-if="cur && cur.type === 'video'" :src="mediaUrl(cur)" controls autoplay class="lb-video"></video>
      <audio v-else-if="cur && cur.type === 'audio'" :src="mediaUrl(cur)" controls class="lb-audio"></audio>
      <div v-else class="lb-unsupported">该类型（{{ cur && cur.type }}）暂不支持预览</div>
    </div>

    <div v-if="cur" class="lb-bar">
      <span class="lb-name" :title="cur.name">{{ cur.name }}</span>
      <span class="lb-idx" v-if="count > 1">{{ index + 1 }} / {{ count }}</span>
    </div>
  </div>
</template>

<script setup>
import { computed, watch, onBeforeUnmount } from 'vue'

const props = defineProps({
  visible: { type: Boolean, default: false },
  items: { type: Array, default: () => [] },   // [{ name, type, path }]
  index: { type: Number, default: 0 },
})
const emit = defineEmits(['close', 'update:index'])

const count = computed(() => props.items.length)
const cur = computed(() => props.items[props.index] || null)

// 未明确指定 type 时，默认按图片渲染（多数灯箱场景是图片预览）
function isImage(it) {
  if (!it) return false
  if (it.type === 'image') return true
  if (it.type === 'video' || it.type === 'audio') return false
  return true
}

function mediaUrl(it) {
  // 通用化：优先用调用方直接给好的 url（各功能图片接口不同），
  // 否则回退到文件空间流接口（兼容 FileSpace 旧用法）。
  if (it && it.url) return it.url
  return '/api/filespace/stream?path=' + encodeURIComponent(it.path)
}
function prev() {
  if (count.value <= 1) return
  emit('update:index', (props.index - 1 + count.value) % count.value)
}
function next() {
  if (count.value <= 1) return
  emit('update:index', (props.index + 1) % count.value)
}
function close() { emit('close') }

function onKey(e) {
  if (!props.visible) return
  if (e.key === 'Escape') { e.preventDefault(); close() }
  else if (e.key === ' ' || e.key === 'Spacebar') { e.preventDefault(); close() }  // 空格切换关闭
  else if (e.key === 'ArrowLeft') { e.preventDefault(); prev() }
  else if (e.key === 'ArrowRight') { e.preventDefault(); next() }
}

watch(() => props.visible, (v) => {
  if (v) document.addEventListener('keydown', onKey)
  else document.removeEventListener('keydown', onKey)
})
onBeforeUnmount(() => document.removeEventListener('keydown', onKey))
</script>

<style scoped>
.lb-mask {
  position: fixed;
  left: var(--sidebar-width, 248px); top: 0; right: 0; bottom: 0;
  z-index: 2000;
  background: rgba(12, 14, 26, .92);
  display: flex; align-items: center; justify-content: center;
  padding: 24px;
}
.lb-stage { max-width: 100%; max-height: 100%; display: flex; align-items: center; justify-content: center; }
.lb-img { max-width: 100%; max-height: 76vh; object-fit: contain; border-radius: 8px; box-shadow: 0 12px 50px rgba(0,0,0,.5); }
.lb-video { max-width: 100%; max-height: 76vh; border-radius: 8px; background: #000; }
.lb-audio { width: 60%; max-width: 680px; }
.lb-unsupported { color: #cfd3e6; font-size: 14px; }
.lb-mask button.lb-close {
  position: fixed; top: 20px; right: 60px;
  width: 48px; height: 48px; border-radius: 50%;
  background: rgba(255,255,255,.12) !important;
  color: #fff !important;
  border: 1px solid rgba(255,255,255,.3) !important;
  cursor: pointer; z-index: 2001;
  display: flex; align-items: center; justify-content: center;
  padding: 0 !important;
  box-sizing: border-box;
  box-shadow: none !important;
  transform: none !important;
  transition: background .15s !important;
}
.lb-mask button.lb-close:hover {
  background: rgba(255,255,255,.24) !important;
  transform: none !important;
  box-shadow: none !important;
}
.lb-mask button.lb-nav {
  position: fixed; top: 50%;
  width: 56px; height: 56px; border-radius: 50%;
  background: rgba(255,255,255,.12) !important;
  color: #fff !important;
  border: 1px solid rgba(255,255,255,.3) !important;
  cursor: pointer; z-index: 2001;
  display: flex; align-items: center; justify-content: center;
  padding: 0 !important;
  box-sizing: border-box;
  box-shadow: none !important;
  transform: translateY(-50%) !important;
  transition: background .15s !important;
}
.lb-mask button.lb-nav:hover {
  background: rgba(255,255,255,.24) !important;
  transform: translateY(-50%) !important;
  box-shadow: none !important;
}
.lb-prev { left: calc(var(--sidebar-width, 248px) + 56px); }
.lb-next { right: 56px; }
.lb-bar {
  position: fixed; left: var(--sidebar-width, 248px); right: 0; bottom: 18px;
  display: flex; align-items: center; justify-content: center; gap: 14px;
  color: #fff; font-size: 13px; pointer-events: none;
}
.lb-name { max-width: 60vw; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; opacity: .92; }
.lb-idx { background: rgba(255,255,255,.14); padding: 2px 10px; border-radius: 12px; }
</style>
