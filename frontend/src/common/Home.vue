<template>
  <div class="home">
    <div class="home-header">
      <h2>欢迎，{{ auth.user?.display_name || auth.user?.username }}</h2>
      <p class="tip">无人扶我青云志，我自踏雪至山巅</p>
      <div class="cards">
        <router-link
          v-for="f in orderedCards"
          :key="f.key"
          :to="f.route"
          class="card"
          :class="{ dragging: dragKey === f.key, 'drag-over': dragOverKey === f.key }"
          draggable="true"
          @dragstart="onDragStart($event, f.key)"
          @dragend="onDragEnd"
          @dragover.prevent="onDragOver($event, f.key)"
          @dragleave="onDragLeave"
          @drop.prevent="onDrop($event, f.key)"
        >
          <div class="card-title">{{ f.emoji }} {{ f.label }}</div>
          <div class="card-desc">{{ descriptions[f.key] || '' }}</div>
        </router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '../login/auth-store.js'
import { registry, isEnabled } from './features.js'

const auth = useAuthStore()

// 不在首页显示的顶层功能（未完善 / 仅开发版）
const EXCLUDED_KEYS = new Set([
  'novel_create',   // 小说创作：未完善
  'script_create',  // 剧本创作：未完善
  'novel_project',  // 小说改写：未完善
  'log_viewer',     // 日志查看：仅开发版
  'packaging',      // 发布版本：仅开发版
])

const descriptions = {
  prompt_library: '沉淀常用提示词，按分类快速复用',
  viral_collection: '追踪热门短剧/漫剧/小说素材，沉淀爆款结构与标签',
  free_resources: '薅羊毛站点：免费额度、操作步骤、截图收藏',
  novel_tweet: '第三方平台发布回填，推文矩阵管理与数据登记',
  daily_tasks: '签到 / 必做事项打卡，按登录日期判定完成',
  filespace: '本地文件书签、分类、备注与快速打开',
  apps_launcher: '常用工具 / 软件快捷启动',
  web_nav: '常用网站快捷入口，一键跳转',
  social_accounts: '管理多平台账号、登录态与运营矩阵',
  chat: '随时和大模型对话、试提示词',
  key_vault: '集中管理 API Key，支持多厂商密钥切换',
  model_config: '填 API Key / 接口地址 / 模型名，启用一条',
  ai_call_rule: '配置模型、提示词与调用策略的绑定规则',
  settings: '主题、数据目录、版本与通用偏好',
  user_management: '创建/编辑用户、分配角色与权限',
  clear_cache: '清理本地缓存与临时文件，释放空间',
  usage_intro: '功能说明、常用操作与首次使用须知',
  manju_generate: '漫剧生产：去重/剧本/资产/分镜编排，生图/音色/生视频内置浏览器工具',
}

// 从注册表生成首页卡片，自动与侧边栏名字/图标保持一致
const allCards = computed(() => {
  return Object.entries(registry.features)
    .filter(([key, f]) =>
      !f.core &&
      f.parent === null &&
      f.emoji &&
      isEnabled(key) &&
      !EXCLUDED_KEYS.has(key)
    )
    .map(([key, f]) => ({
      key,
      label: f.label,
      route: f.route,
      emoji: f.emoji,
    }))
})

// 拖拽顺序持久化
const ORDER_KEY = 'sxm_home_card_order'
const savedOrder = ref([])
onMounted(() => {
  try {
    const raw = localStorage.getItem(ORDER_KEY)
    if (raw) savedOrder.value = JSON.parse(raw)
  } catch (_) { /* 忽略损坏的本地存储 */ }
})

const orderedCards = computed(() => {
  const items = allCards.value
  if (!savedOrder.value.length) return items

  const orderMap = new Map(savedOrder.value.map((k, i) => [k, i]))
  const defaultIndex = savedOrder.value.length
  return [...items].sort((a, b) => {
    const ia = orderMap.get(a.key)
    const ib = orderMap.get(b.key)
    if (ia === undefined && ib === undefined) return 0
    if (ia === undefined) return 1
    if (ib === undefined) return -1
    return ia - ib
  })
})

// 拖拽交互
const dragKey = ref(null)
const dragOverKey = ref(null)

function onDragStart(e, key) {
  dragKey.value = key
  e.dataTransfer.effectAllowed = 'move'
  // 让拖拽预览保持原有样式，不触发浏览器默认重影异常
  try { e.dataTransfer.setData('text/plain', key) } catch (_) {}
}

function onDragEnd() {
  dragKey.value = null
  dragOverKey.value = null
}

function onDragOver(e, key) {
  e.preventDefault()
  if (dragKey.value && dragKey.value !== key) {
    dragOverKey.value = key
  }
}

function onDragLeave() {
  dragOverKey.value = null
}

function onDrop(e, targetKey) {
  e.preventDefault()
  const fromKey = dragKey.value
  dragKey.value = null
  dragOverKey.value = null
  if (!fromKey || fromKey === targetKey) return

  const currentOrder = orderedCards.value.map(c => c.key)
  const fromIdx = currentOrder.indexOf(fromKey)
  const toIdx = currentOrder.indexOf(targetKey)
  if (fromIdx < 0 || toIdx < 0) return

  currentOrder.splice(fromIdx, 1)
  currentOrder.splice(toIdx, 0, fromKey)
  savedOrder.value = currentOrder
  try { localStorage.setItem(ORDER_KEY, JSON.stringify(currentOrder)) } catch (_) {}
}
</script>

<style scoped>
.home { width: 100%; max-width: none; margin: 0; color: var(--sx-text-strong); min-height: calc(100vh - 44px); }
.tip { color: var(--sx-text); margin-bottom: 16px; }
.cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 16px; grid-auto-rows: 1fr; }

.card {
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 18px;
  border: 1px solid var(--sx-border);
  border-radius: 10px;
  text-decoration: none;
  color: inherit;
  background: var(--sx-bg-surface);
  box-shadow: var(--sx-shadow-card);
  transition: .15s;
  cursor: grab;
  user-select: none;
}
.card:hover {
  border-color: var(--sx-accent);
  box-shadow: 0 2px 12px rgba(79, 124, 255, .15);
}
.card:active { cursor: grabbing; }
.card.dragging {
  opacity: .45;
  transform: scale(.98);
}
.card.drag-over {
  border-color: var(--sx-accent);
  box-shadow: 0 0 0 2px rgba(79, 124, 255, .18);
}
.card-title { font-weight: 600; font-size: 16px; margin-bottom: 6px; color: var(--sx-text-strong); }
.card-desc { color: var(--sx-text); font-size: 13px; }
</style>
