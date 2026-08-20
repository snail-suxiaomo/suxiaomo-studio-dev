<template>
  <div class="page">
    <h2>小说改写（06）</h2>

  <ActiveRuleBar function-key="06-改写" />
    <p class="hint">逐集影视化改写：读 00-拆分 本章，结合项目配置.md、05-总表、前情记忆，按 6 条铁律（心理描写清零/冲突具象化/黄金3秒/钩子对位/字数均匀/C级注入）改写。</p>

    <div class="bar">
      <select v-model="projectId">
        <option :value="null" disabled>选择项目</option>
        <option v-for="p in projects" :key="p.id" :value="p.id">{{ p.name }}</option>
      </select>
      <button :disabled="!projectId || loading" @click="loadChapters">加载章节</button>
      <button :disabled="!projectId || loading" @click="runAll">全部改写</button>
      <span v-if="loading" class="running">处理中…</span>
      <button class="ghost" @click="goBack">← 返回项目</button>
    </div>

    <div v-if="chapters.length" class="chapters">
      <div v-for="c in chapters" :key="c.idx" class="chapter-row">
        <span class="c-title">第{{ c.idx }}章 · {{ c.title }}</span>
        <span class="c-flag" :class="c.rewritten ? 'done' : ''">{{ c.rewritten ? '已改写' : '未改写' }}</span>
        <div class="ops">
          <button :disabled="loading" @click="runStage('generate', c.idx)">改写本章</button>
          <button :disabled="loading" @click="runStage('validate', c.idx)">格式校验</button>
          <button :disabled="loading" @click="runStage('review', c.idx)">AI 审核</button>
        </div>
      </div>
    </div>

    <div v-if="result" class="result">
      <div class="status" :class="result.ok ? 'ok' : 'fail'">
        {{ result.ok ? '✅ ' + stageLabel(result.stage) + '完成（第' + result.chapter_idx + '章）' : '⚠️ ' + stageLabel(result.stage) + '：' + (result.error || '') }}
      </div>

      <template v-if="result.ok">
        <div class="checks">
          <div class="check" :class="result.validation.ok ? 'ok' : 'fail'">
            格式校验：{{ result.validation.ok ? '通过' : '未通过（' + result.validation.errors.join('；') + '）' }}
          </div>
          <div class="check" :class="result.review.passed === true ? 'ok' : (result.review.passed === false ? 'fail' : '')">
            AI 审核：{{ result.review.passed === true ? 'PASS' : (result.review.passed === false ? 'FAIL：' + result.review.raw : (result.review.note || '跳过')) }}
          </div>
        </div>

        <h3>改写正文</h3>
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
const chapters = ref([])
const loading = ref(false)
const result = ref(null)

async function loadProjects() {
  const r = await api('/novel_project')
  projects.value = r
}
async function loadChapters() {
  if (!projectId.value) return
  result.value = null
  chapters.value = await api(`/novel_rewrite/chapters?project_id=${projectId.value}`)
}
function stageLabel(stage) {
  const map = { generate: '改写', validate: '格式校验', review: 'AI 审核', unknown: '执行', done: '执行', error: '请求' }
  return map[stage] || stage
}

async function runStage(stage, idx) {
  if (!projectId.value) return
  loading.value = true
  result.value = null
  try {
    const d = await api('/novel_rewrite/' + stage, 'POST', { project_id: projectId.value, chapter_idx: idx })
    result.value = d
    await loadChapters()
  } catch (e) {
    result.value = { ok: false, stage: 'error', error: String(e) }
  } finally {
    loading.value = false
  }
}
async function runAll() {
  if (!projectId.value) return
  loading.value = true
  result.value = null
  try {
    const d = await api('/novel_rewrite/run_all', 'POST', { project_id: projectId.value })
    result.value = { ok: d.ok, stage: 'done', chapter_idx: '全部', error: d.error || '' }
    await loadChapters()
  } catch (e) {
    result.value = { ok: false, stage: 'error', error: String(e) }
  } finally {
    loading.value = false
  }
}
onMounted(async () => {
  await loadProjects()
  if (proj.current) {
    projectId.value = proj.current.id
    await loadChapters()
  }
})
</script>

<style>
.page { max-width: 960px; }
.hint { color: #666; font-size: 13px; margin: 4px 0 16px; }
.bar { display: flex; gap: 10px; align-items: center; margin-bottom: 16px; flex-wrap: wrap; }
.bar select { padding: 6px 10px; border: 1px solid #ccc; border-radius: 6px; min-width: 180px; }
.bar button { padding: 6px 16px; border: none; border-radius: 6px; background: #4f7cff; color: #fff; cursor: pointer; }
.bar button:disabled { background: #b9c6ee; cursor: not-allowed; }
.running { color: #888; font-size: 13px; }
.chapters { margin-bottom: 16px; }
.chapter-row { display: flex; gap: 12px; align-items: center; padding: 8px 10px; border-bottom: 1px solid #eee; }
.chapter-row .c-title { flex: 1; font-size: 14px; }
.chapter-row .c-flag { font-size: 12px; color: #999; }
.chapter-row .c-flag.done { color: #1a7f37; }
.chapter-row .ops { display: flex; gap: 8px; }
.chapter-row button { padding: 4px 12px; border: none; border-radius: 6px; background: #4f7cff; color: #fff; cursor: pointer; font-size: 12px; }
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
