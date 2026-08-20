<template>
  <div class="page">
    <h2>小说图谱（02）</h2>

  <ActiveRuleBar function-key="02-图谱" />

    <div class="card">
      <div class="row">
        <label>项目：</label>
        <select v-model="projectId" @change="onChange">
          <option :value="null" disabled>选择项目</option>
          <option v-for="p in projects" :key="p.id" :value="p.id">{{ p.name }}</option>
        </select>
        <button @click="runGenerate" :disabled="!projectId || busy">生成图谱</button>
        <button @click="runValidate" :disabled="!projectId || busy">格式校验</button>
        <button @click="runReview" :disabled="!projectId || busy">AI 审核</button>
      <button class="ghost" @click="goBack">← 返回项目</button>
      </div>
      <p class="tip">基于「小说梗概」全部章节，产出单一图谱报告（人物/场景/伏笔）。若已存在旧报告，将自动增量更新。</p>
      <p v-if="msg" class="msg">{{ msg }}</p>
    </div>

    <div class="card" v-if="result">
      <h3>{{ resultTitle }}</h3>
      <template v-if="result.ok">
        <p class="status" v-if="result.stage === 'generate'">
          模式：<span :class="result.incremental?'warn':'ok'">{{ result.incremental ? '增量更新' : '首次构建' }}</span>
          ｜ 已落盘 {{ OUTPUT_DIR }}/{{ REPORT_NAME }}
        </p>
        <p class="status" v-if="result.stage === 'validate'">
          格式校验：<span :class="result.format_ok?'ok':'warn'">{{ result.format_ok ? '通过' : '未通过' }}</span>
        </p>
        <div v-if="result.stage === 'validate' && !result.format_ok" class="errs">
          <div v-for="e in result.format_errors" :key="e">⚠ {{ e }}</div>
        </div>
        <p class="status" v-if="result.stage === 'review'">
          AI 审核：<span :class="result.review_passed?'ok':'warn'">{{ result.review_passed ? '通过' : '未通过' }}</span>
        </p>
        <pre v-if="result.output" class="output">{{ result.output }}</pre>
        <pre v-if="result.review_detail" class="output">{{ result.review_detail }}</pre>
      </template>
      <p v-else class="err">{{ stageLabel(result.stage) }}失败：{{ result.error }}</p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
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
const busy = ref(false)
const msg = ref('')
const result = ref(null)

const resultTitle = computed(() => {
  if (!result.value) return ''
  return stageLabel(result.value.stage) + '结果'
})

function stageLabel(stage) {
  const map = { generate: '生成', validate: '格式校验', review: 'AI 审核', unknown: '执行' }
  return map[stage] || stage
}

async function loadProjects() {
  projects.value = await api('/novel_project')
}
async function onChange() {
  result.value = null
  msg.value = ''
}
async function callStage(stage) {
  if (!projectId.value) return
  busy.value = true; msg.value = ''; result.value = null
  try {
    result.value = await api('/novel_graph/' + stage, 'POST', { project_id: projectId.value })
  } catch (e) { msg.value = e.message }
  busy.value = false
}
async function runGenerate() { return callStage('generate') }
async function runValidate() { return callStage('validate') }
async function runReview() { return callStage('review') }
onMounted(async () => {
  await loadProjects()
  if (proj.current) projectId.value = proj.current.id
})
</script>

<style scoped>
.page { max-width: 960px; }
.card { background: #fff; border: 1px solid #ececec; border-radius: 10px; padding: 16px 18px; margin-bottom: 16px; }
.row { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
label { font-size: 14px; }
select { padding: 7px 10px; border: 1px solid #ccc; border-radius: 6px; min-width: 200px; }
button { padding: 7px 14px; border: none; border-radius: 6px; background: #4f7cff; color: #fff; cursor: pointer; }
button:disabled { opacity: .5; cursor: not-allowed; }
.tip { color: #888; font-size: 13px; margin: 8px 0 0; }
.msg { color: #2a7; margin-top: 8px; }
.status { font-size: 14px; }
.status .ok { color: #2a7; font-weight: 600; }
.status .warn { color: #e8a000; font-weight: 600; }
.errs { color: #e25b5b; font-size: 13px; margin: 8px 0; }
.err { color: #e25b5b; }
.output { white-space: pre-wrap; background: #f7f8fa; border: 1px solid #ececec; border-radius: 8px; padding: 14px; font-size: 13px; line-height: 1.6; max-height: 540px; overflow: auto; }
</style>
