<template>
  <div class="page">
    <h2>小说诊断（七维质量评估）</h2>

  <ActiveRuleBar function-key="03-诊断" />
    <p class="hint">基于 01-梗概 + 02-图谱，对整本书做七维质量评估，产出单一诊断报告。</p>

    <div class="bar">
      <select v-model="projectId">
        <option :value="null" disabled>选择项目</option>
        <option v-for="p in projects" :key="p.id" :value="p.id">{{ p.name }}</option>
      </select>
        <button :disabled="!projectId || loading" @click="callStage('generate')">生成诊断</button>
        <button :disabled="!projectId || loading" @click="callStage('validate')">格式校验</button>
        <button :disabled="!projectId || loading" @click="callStage('review')">AI 审核</button>
      <button class="ghost" @click="goBack">← 返回项目</button>
      </div>

    <div v-if="error" class="err">⚠️ {{ error }}</div>

    <div v-if="result" class="result">
      <div class="status">
        <span :class="['badge', result.ok ? 'ok' : 'bad']">{{ result.ok ? stageLabel(result.stage) + '完成' : stageLabel(result.stage) + '失败' }}</span>
        <span v-if="result.missing_upstream" class="warn">⚠ 未找到 02-图谱，已按无图谱上下文评估</span>
      </div>

      <div v-if="result.validation" class="block">
        <h3>格式校验</h3>
        <span :class="['badge', result.validation.ok ? 'ok' : 'bad']">{{ result.validation.ok ? '通过' : '未通过' }}</span>
        <ul v-if="result.validation.problems && result.validation.problems.length">
          <li v-for="(p, i) in result.validation.problems" :key="i">{{ p }}</li>
        </ul>
      </div>

      <div v-if="result.review" class="block">
        <h3>AI 审核</h3>
        <span v-if="result.review.passed === true" class="badge ok">PASS</span>
        <span v-else-if="result.review.passed === false" class="badge bad">FAIL</span>
        <span v-else class="badge warn">跳过 / 未运行</span>
        <pre v-if="result.review.raw" class="review">{{ result.review.raw }}</pre>
      </div>

      <div class="block">
        <h3>诊断报告</h3>
        <pre class="report">{{ result.result_text }}</pre>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../common/http.js'
import ActiveRuleBar from '../common/ActiveRuleBar.vue'
import { useProjectStore } from '../common/project-store.js'

const proj = useProjectStore()
const router = useRouter()
function goBack() {
  router.push(proj.current ? '/novel_project/' + proj.current.id : '/novel_project')
}

const projects = ref([])
const projectId = ref(null)
const loading = ref(false)
const result = ref(null)
const error = ref('')

async function loadProjects() {
  const r = await api('/novel_project')
  projects.value = r
}

function stageLabel(stage) {
  const map = { generate: '生成', validate: '格式校验', review: 'AI 审核', unknown: '执行', done: '执行' }
  return map[stage] || stage
}

async function callStage(stage) {
  error.value = ''
  result.value = null
  loading.value = true
  try {
    const r = await api('/novel_diagnose/' + stage, 'POST', { project_id: projectId.value })
    result.value = r
    if (!r.ok) error.value = r.error || (stageLabel(r.stage || stage) + '失败')
  } catch (e) {
    error.value = '请求失败：' + (e.message || e)
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await loadProjects()
  if (proj.current) projectId.value = proj.current.id
})
</script>

<style scoped>
.page { max-width: 960px; }
.hint { color: #666; font-size: 13px; margin-bottom: 12px; }
.bar { display: flex; gap: 10px; margin-bottom: 14px; }
.bar select { padding: 6px 10px; min-width: 200px; }
.bar button { padding: 6px 16px; background: #4f7cff; color: #fff; border: none; border-radius: 6px; cursor: pointer; }
.bar button:disabled { background: #b9c6f5; cursor: not-allowed; }
.err { color: #c0392b; background: #fdecea; padding: 8px 12px; border-radius: 6px; margin-bottom: 12px; }
.status { display: flex; gap: 12px; align-items: center; margin-bottom: 12px; }
.block { margin-bottom: 16px; }
.block h3 { margin: 0 0 8px; font-size: 15px; }
.badge { padding: 2px 10px; border-radius: 12px; font-size: 12px; font-weight: 600; }
.badge.ok { background: #e6f7ee; color: #1a9c54; }
.badge.bad { background: #fdecea; color: #c0392b; }
.badge.warn { background: #fff5e6; color: #c8801a; }
.warn { color: #c8801a; font-size: 13px; }
ul { margin: 6px 0 0; padding-left: 20px; color: #c0392b; font-size: 13px; }
.report, .review { background: #f7f8fb; border: 1px solid #ececec; border-radius: 8px; padding: 12px; white-space: pre-wrap; word-break: break-word; font-family: ui-monospace, Menlo, Consolas, monospace; font-size: 13px; line-height: 1.6; max-height: 480px; overflow: auto; }
.review { background: #fbfaff; }
</style>
