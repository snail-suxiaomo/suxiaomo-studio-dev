<template>
  <div class="page">
    <h2>小说策略（04）</h2>

  <ActiveRuleBar function-key="04-策略" />
    <p class="hint">依据 03-诊断 报告，确定单集时长、视觉风格、取舍策略，并生成「项目配置.md」（下游 05+ 的 {config} 来源）。</p>

    <div class="bar">
      <select v-model="projectId">
        <option :value="null" disabled>选择项目</option>
        <option v-for="p in projects" :key="p.id" :value="p.id">{{ p.name }}</option>
      </select>
      <button :disabled="!projectId || running" @click="callStage('generate')">生成策略</button>
      <button :disabled="!projectId || running" @click="callStage('validate')">格式校验</button>
      <button :disabled="!projectId || running" @click="callStage('review')">AI 审核</button>
      <span v-if="running" class="running">处理中…</span>
      <button class="ghost" @click="goBack">← 返回项目</button>
    </div>

    <div v-if="result" class="result">
      <div class="status" :class="result.ok ? 'ok' : 'fail'">
        {{ result.ok ? '✅ ' + stageLabel(result.stage) + '完成' : '⚠️ ' + stageLabel(result.stage) + '：' + (result.error || '') }}
      </div>

      <template v-if="result.ok">
        <div class="checks">
          <div class="check" :class="result.validation.ok ? 'ok' : 'fail'">
            格式校验：{{ result.validation.ok ? '通过' : '未通过（' + result.validation.errors.join('；') + '）' }}
          </div>
          <div class="check" :class="result.review.passed === true ? 'ok' : (result.review.passed === false ? 'fail' : '')">
            AI 审核：{{ result.review.passed === true ? 'PASS' : (result.review.passed === false ? 'FAIL：' + result.review.raw : (result.review.note || '跳过')) }}
          </div>
          <div class="check" v-if="result.config_path">
            项目配置.md：已生成 → {{ result.config_path }}
          </div>
          <div class="check" v-else>项目配置.md：未抽取到 CONFIG 块</div>
        </div>

        <h3>策略报告</h3>
        <pre class="report">{{ result.result_text }}</pre>
      </template>
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
const running = ref(false)
const result = ref(null)

async function loadProjects() {
  const r = await api('/novel_project')
  projects.value = r
}
function stageLabel(stage) {
  const map = { generate: '生成', validate: '格式校验', review: 'AI 审核', unknown: '执行', done: '执行', error: '请求' }
  return map[stage] || stage
}

async function callStage(stage) {
  if (!projectId.value) return
  running.value = true
  result.value = null
  try {
    const d = await api('/novel_strategy/' + stage, 'POST', { project_id: projectId.value })
    result.value = d
  } catch (e) {
    result.value = { ok: false, stage: 'error', error: String(e) }
  } finally {
    running.value = false
  }
}
onMounted(async () => {
  await loadProjects()
  if (proj.current) projectId.value = proj.current.id
})
</script>

<style>
.page { max-width: 960px; }
.hint { color: #666; font-size: 13px; margin: 4px 0 16px; }
.bar { display: flex; gap: 10px; align-items: center; margin-bottom: 16px; }
.bar select { padding: 6px 10px; border: 1px solid #ccc; border-radius: 6px; min-width: 180px; }
.bar button { padding: 6px 16px; border: none; border-radius: 6px; background: #4f7cff; color: #fff; cursor: pointer; }
.bar button:disabled { background: #b9c6ee; cursor: not-allowed; }
.running { color: #888; font-size: 13px; }
.status { padding: 8px 12px; border-radius: 6px; margin-bottom: 12px; font-weight: 600; }
.status.ok { background: #e6f7ec; color: #1a7f37; }
.status.fail { background: #fdecea; color: #c0392b; }
.checks { margin-bottom: 14px; }
.check { padding: 6px 10px; border-radius: 6px; margin-bottom: 6px; font-size: 13px; background: #f5f6fa; }
.check.ok { color: #1a7f37; }
.check.fail { color: #c0392b; }
.report { white-space: pre-wrap; word-break: break-word; background: #fafbfc; border: 1px solid #ececec;
  border-radius: 8px; padding: 16px; font-family: ui-monospace, Menlo, Consolas, monospace; font-size: 13px; line-height: 1.6; }
</style>
