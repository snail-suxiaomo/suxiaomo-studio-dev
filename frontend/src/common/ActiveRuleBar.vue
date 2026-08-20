<template>
  <div class="active-rule-bar" v-if="ready">
    <span class="arb-title">当前生效 AI 规则</span>
    <span class="arb-role" v-for="rb in order" :key="rb.role" :class="'arb-' + rb.role">
      <i class="arb-tag">{{ rb.label }}</i>
      <span class="arb-name">{{ nameOf(rb.role) }}</span>
    </span>
    <span class="arb-tip">（更换请到「小说改写」项目详情页对应步骤选择）</span>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { api } from './http.js'

const props = defineProps({
  functionKey: { type: String, required: true },
  menu: { type: String, default: '小说改写' },
})

// 角色顺序与配色：校验 / 生成 / 审核（与详情页一致）
const order = [
  { role: 'format', label: '校验' },
  { role: 'generate', label: '生成' },
  { role: 'review', label: '审核' },
]

const byRole = ref({})
const ready = ref(false)

function nameOf(role) {
  const r = byRole.value[role]
  if (!r) return '默认参考规则'
  let tag = r.is_ref ? '（参考）' : ''
  return (r.name || r.ref_path || ('#' + r.id)) + tag
}

async function load() {
  try {
    const rows = await api(
      '/ai-rules?menu=' + encodeURIComponent(props.menu) +
      '&function_key=' + encodeURIComponent(props.functionKey) + '&enabled=1'
    )
    const m = {}
    for (const r of (rows || [])) m[r.role] = r
    byRole.value = m
  } catch {
    byRole.value = {}
  } finally {
    ready.value = true
  }
}

onMounted(load)
</script>

<style scoped>
.active-rule-bar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px 14px;
  margin: 0 0 14px;
  padding: 8px 14px;
  background: #f7f9fc;
  border: 1px solid #e6eaf2;
  border-radius: 10px;
  font-size: 13px;
  color: #444;
}
.arb-title {
  font-weight: 700;
  color: #2b2f44;
}
.arb-role {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.arb-tag {
  font-style: normal;
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 7px;
  color: #fff;
}
.arb-format .arb-tag { background: #2b8fe0; }
.arb-generate .arb-tag { background: #1c9d52; }
.arb-review .arb-tag { background: #7b61ff; }
.arb-name {
  color: #185fa5;
  font-weight: 600;
}
.arb-tip {
  color: #9aa2b1;
  font-size: 12px;
}
</style>
