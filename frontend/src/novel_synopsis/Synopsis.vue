<template>
  <div class="page">
    <h2>小说梗概（01）</h2>

    <ActiveRuleBar function-key="01-梗概" />

    <div class="card">
      <div class="row">
        <label>项目：</label>
        <select v-model="projectId" @change="onProjectChange">
          <option :value="null" disabled>选择项目</option>
          <option v-for="p in projects" :key="p.id" :value="p.id">{{ p.name }}</option>
        </select>
        <button @click="runAll" :disabled="!projectId || busy">生成全部</button>
        <button class="ghost" @click="goBack">← 返回项目</button>
      </div>
      <p v-if="msg" class="msg">{{ msg }}</p>
    </div>

    <div class="card" v-if="projectId && chapters.length">
      <h3>待处理章节（来自 00-拆分）</h3>
      <table>
        <colgroup>
          <col style="width: 14%" />
          <col style="width: 46%" />
          <col style="width: 40%" />
        </colgroup>
        <thead>
          <tr><th>章号</th><th>标题</th><th>操作</th></tr>
        </thead>
        <tbody>
          <tr v-for="c in chapters" :key="c.idx">
            <td>第{{ c.idx }}章</td>
            <td>{{ c.title }}</td>
            <td class="ops">
              <button @click="runGenerate(c.idx)" :disabled="busy">生成梗概</button>
              <button @click="runValidate(c.idx)" :disabled="busy">格式校验</button>
              <button @click="runReview(c.idx)" :disabled="busy">AI 审核</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <div class="card empty" v-else-if="projectId">该项目在 00-拆分 下没有可处理的章节。</div>

    <div class="card" v-if="result">
      <h3>{{ resultTitle }}</h3>
      <template v-if="result.ok">
        <p class="status" v-if="result.stage === 'generate'">
          已生成并落盘 01-梗概/第{{ result.chapter_idx }}章.md
        </p>
        <p class="status" v-if="result.stage === 'validate'">
          格式校验：<span :class="result.format_ok ? 'ok' : 'warn'">{{ result.format_ok ? '通过' : '未通过' }}</span>
        </p>
        <div v-if="result.stage === 'validate' && !result.format_ok" class="errs">
          <div v-for="e in result.format_errors" :key="e">⚠ {{ e }}</div>
        </div>
        <p class="status" v-if="result.stage === 'review'">
          AI 审核：<span :class="result.review_passed ? 'ok' : 'warn'">{{ result.review_passed ? '通过' : '未通过' }}</span>
        </p>
        <pre v-if="result.output" class="output">{{ result.output }}</pre>
        <pre v-if="result.review_detail" class="output">{{ result.review_detail }}</pre>
      </template>
      <p v-else class="err">{{ stageLabel(result.stage) }}失败：{{ result.error }}</p>
    </div>

    <div class="card" v-if="batch">
      <h3>批量结果</h3>
      <table>
        <colgroup>
          <col style="width: 14%" />
          <col style="width: 14%" />
          <col style="width: 14%" />
          <col style="width: 58%" />
        </colgroup>
        <thead><tr><th>章号</th><th>格式校验</th><th>AI 审核</th><th>备注</th></tr></thead>
        <tbody>
          <tr v-for="r in batch.results" :key="r.chapter_idx">
            <td>第{{ r.chapter_idx }}章</td>
            <td><span :class="r.ok && r.format_ok ? 'ok' : 'warn'">{{ r.ok ? (r.format_ok ? '通过' : '未通过') : '失败' }}</span></td>
            <td><span :class="r.ok && r.review_passed ? 'ok' : 'warn'">{{ r.ok ? (r.review_passed ? '通过' : '未通过') : '—' }}</span></td>
            <td class="note">{{ !r.ok ? r.error : (r.format_ok ? '' : r.format_errors.join('；')) }}</td>
          </tr>
        </tbody>
      </table>
      <p class="msg">报告已写入 01-梗概/01-小说梗概报告.md</p>
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
const chapters = ref([])
const msg = ref('')
const busy = ref(false)
const result = ref(null)
const batch = ref(null)

const resultTitle = computed(() => {
  if (!result.value) return ''
  const base = result.value.chapter_idx != null ? `第${result.value.chapter_idx}章 · ` : ''
  return base + stageLabel(result.value.stage) + '结果'
})

function stageLabel(stage) {
  const map = { generate: '生成', validate: '格式校验', review: 'AI 审核', unknown: '执行' }
  return map[stage] || stage
}

async function loadProjects() {
  projects.value = await api('/novel_project')
}

async function onProjectChange() {
  result.value = null
  batch.value = null
  msg.value = ''
  if (!projectId.value) return
  chapters.value = await api(`/novel_synopsis/chapters?project_id=${projectId.value}`)
}

async function callStage(stage, idx) {
  busy.value = true
  msg.value = ''
  result.value = null
  try {
    result.value = await api(`/novel_synopsis/${stage}`, 'POST',
      { project_id: projectId.value, chapter_idx: idx })
  } catch (e) {
    msg.value = e.message
  }
  busy.value = false
}

function runGenerate(idx) { return callStage('generate', idx) }
function runValidate(idx) { return callStage('validate', idx) }
function runReview(idx) { return callStage('review', idx) }

async function runAll() {
  if (!projectId.value) return
  busy.value = true
  msg.value = ''
  result.value = null
  batch.value = null
  try {
    batch.value = await api('/novel_synopsis/run_all', 'POST',
      { project_id: projectId.value })
  } catch (e) {
    msg.value = e.message
  }
  busy.value = false
}

onMounted(async () => {
  await loadProjects()
  if (proj.current) {
    projectId.value = proj.current.id
    await onProjectChange()
  }
})
</script>

<style scoped>
.page { max-width: 960px; }
.card { background: #fff; border: 1px solid #ececec; border-radius: 10px; padding: 16px 18px; margin-bottom: 16px; }
.card.empty { color: #999; }
.row { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.ops { display: flex; gap: 8px; flex-wrap: wrap; }
.ops button { padding: 5px 10px; font-size: 13px; }
label { font-size: 14px; color: #444; }
select { padding: 7px 10px; border: 1px solid #ccc; border-radius: 6px; min-width: 200px; }
.msg { color: #2a7; margin-top: 8px; }
.status { font-size: 14px; }
.ok { color: #2a7; font-weight: 600; }
.warn { color: #e2952b; font-weight: 600; }
.errs { color: #e2952b; font-size: 13px; margin: 6px 0; }
.output { white-space: pre-wrap; background: #f8f9fc; border: 1px solid #eee; border-radius: 8px; padding: 12px; font-size: 13px; line-height: 1.7; max-height: 420px; overflow: auto; }
.err { color: #e25b5b; }
.note { color: #888; font-size: 13px; }
</style>
