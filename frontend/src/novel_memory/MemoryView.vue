<template>
  <div class="page">
    <div class="head">
      <h2>🧠 记忆库</h2>
      <p class="sub">每章处理完成后自动保存草稿（由管线功能写入），可在此逐条查看、修改、删除，或手动补充。确认后的记忆会注入后续章节生成上下文。</p>
    </div>

    <!-- 筛选 -->
    <div class="card filter">
      <div class="row">
        <label>项目：</label>
        <select v-model="selectedProjectId" @change="onProjectChange">
          <option :value="null">请选择项目</option>
          <option v-for="p in projects" :key="p.id" :value="p.id">{{ p.name }}</option>
        </select>

        <label>功能：</label>
        <select v-model="selectedFunctionId" @change="loadMemories">
          <option value="">全部</option>
          <option v-for="f in functions" :key="f.id" :value="f.id">{{ f.name }}</option>
        </select>

        <button class="ghost" v-if="selectedProjectId" @click="goProject">打开项目</button>
        <button :disabled="!selectedProjectId" @click="openCreate">＋ 新增记忆</button>
      </div>
    </div>

    <div v-if="loading" class="card"><p>加载中…</p></div>

    <div v-else-if="!selectedProjectId" class="card empty">
      <p>请先选择一个项目，查看或编辑它的记忆库。</p>
    </div>

    <div v-else-if="memories.length === 0" class="card empty">
      <p>该条件下暂无可记忆内容。运行对应功能后，AI 会自动把每章摘要存为草稿。</p>
    </div>

    <!-- 记忆列表 -->
    <div v-else class="card list">
      <table>
        <colgroup>
          <col style="width:64px" />
          <col style="width:128px" />
          <col />
          <col style="width:84px" />
          <col style="width:120px" />
        </colgroup>
        <thead>
          <tr>
            <th>章节</th>
            <th>功能</th>
            <th>摘要</th>
            <th>状态</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="m in memories" :key="m.id">
            <td>{{ m.chapter_idx === 0 ? '整本' : ('第' + m.chapter_idx + '章') }}</td>
            <td>{{ m.function_id }}</td>
            <td class="summary">{{ m.summary || '（空）' }}</td>
            <td>
              <span class="badge" :class="m.status === 'confirmed' ? 'ok' : 'warn'">
                {{ m.status === 'confirmed' ? '已确认' : '草稿' }}
              </span>
            </td>
            <td class="ops">
              <button @click="openEdit(m)">编辑</button>
              <button class="danger" @click="remove(m)">删除</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 编辑/新增 弹窗 -->
    <div v-if="showModal" class="mask" @click.self="closeModal">
      <div class="modal">
        <h3>{{ isCreate ? '新增记忆' : '编辑记忆' }}</h3>

        <div class="form-row" v-if="isCreate">
          <label>章节序号：</label>
          <input type="number" v-model.number="form.chapter_idx" min="1" />
        </div>
        <div class="form-row" v-if="isCreate">
          <label>功能：</label>
          <select v-model="form.function_id">
            <option v-for="f in functions" :key="f.id" :value="f.id">{{ f.name }}</option>
          </select>
        </div>

        <div class="form-row">
          <label>摘要（中文）：</label>
          <textarea v-model="form.summary" rows="8" placeholder="输入记忆摘要…"></textarea>
        </div>

        <div class="form-row">
          <label>状态：</label>
          <select v-model="form.status">
            <option value="draft">草稿（待确认）</option>
            <option value="confirmed">已确认（注入后续章节）</option>
          </select>
        </div>

        <div class="modal-actions">
          <button :disabled="saving" @click="save">{{ saving ? '保存中…' : '保存' }}</button>
          <button class="ghost" @click="closeModal">取消</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../common/http.js'
import { confirm, alert } from '../common/useConfirm.js'
import { useProjectStore } from '../common/project-store.js'

const router = useRouter()
const proj = useProjectStore()

const projects = ref([])
// 13 个管线功能（与产物目录 / novel_function.function_id 对应）
const functions = [
  { id: '00-拆分', name: '00-小说拆分' },
  { id: '01-梗概', name: '01-小说梗概' },
  { id: '02-图谱', name: '02-小说图谱' },
  { id: '03-诊断', name: '03-小说诊断' },
  { id: '04-策略', name: '04-小说策略' },
  { id: '05-总表', name: '05-小说总表' },
  { id: '06-改写', name: '06-小说改写' },
  { id: '07-去重', name: '07-小说去重' },
  { id: '08-精要', name: '08-小说精要' },
  { id: '09-剧本', name: '09-小说剧本' },
  { id: '10-资产', name: '10-小说资产' },
  { id: '11-分卷', name: '11-分镜分卷' },
  { id: '12-分镜', name: '12-分镜脚本' },
]

const selectedProjectId = ref(null)
const selectedFunctionId = ref('')
const memories = ref([])
const loading = ref(false)

const showModal = ref(false)
const isCreate = ref(false)
const saving = ref(false)
const editingId = ref(null)
const form = ref({ chapter_idx: 1, function_id: '01-梗概', summary: '', status: 'draft' })

async function loadProjects() {
  try {
    projects.value = await api('/novel_project')
  } catch (e) {
    console.error('加载项目失败：', e)
  }
}

async function loadMemories() {
  if (!selectedProjectId.value) return
  loading.value = true
  try {
    let q = `/novel_memory?project_id=${selectedProjectId.value}`
    if (selectedFunctionId.value) q += `&function_id=${encodeURIComponent(selectedFunctionId.value)}`
    memories.value = await api(q)
  } catch (e) {
    await alert('加载记忆失败：' + (e.message || e))
  } finally {
    loading.value = false
  }
}

function onProjectChange() {
  selectedFunctionId.value = ''
  loadMemories()
}

function goProject() {
  if (selectedProjectId.value) router.push(`/novel_project/${selectedProjectId.value}`)
}

function openCreate() {
  isCreate.value = true
  editingId.value = null
  form.value = {
    chapter_idx: 1,
    function_id: functions[0]?.id || '01-梗概',
    summary: '',
    status: 'draft',
  }
  showModal.value = true
}

function openEdit(m) {
  isCreate.value = false
  editingId.value = m.id
  form.value = {
    chapter_idx: m.chapter_idx,
    function_id: m.function_id,
    summary: m.summary || '',
    status: m.status,
  }
  showModal.value = true
}

function closeModal() {
  showModal.value = false
}

async function save() {
  saving.value = true
  try {
    if (isCreate.value) {
      await api('/novel_memory', 'POST', {
        project_id: selectedProjectId.value,
        function_id: form.value.function_id,
        chapter_idx: form.value.chapter_idx,
        summary: form.value.summary,
        status: form.value.status,
      })
    } else {
      await api(`/novel_memory/${editingId.value}`, 'PATCH', {
        summary: form.value.summary,
        status: form.value.status,
      })
    }
    showModal.value = false
    await loadMemories()
  } catch (e) {
    await alert('保存失败：' + (e.message || e))
  } finally {
    saving.value = false
  }
}

async function remove(m) {
  if (!(await confirm(`确定删除第${m.chapter_idx}章的记忆吗？此操作不可恢复。`, { title: '删除确认' }))) return
  try {
    await api(`/novel_memory/${m.id}`, 'DELETE')
    await loadMemories()
  } catch (e) {
    await alert('删除失败：' + (e.message || e))
  }
}

onMounted(async () => {
  await loadProjects()
  if (proj.current && proj.current.id) {
    selectedProjectId.value = proj.current.id
    await loadMemories()
  }
})
</script>

<style scoped>
.head { margin-bottom: 18px; }
.sub { color: var(--ink2); font-size: 13px; margin: 0; line-height: 1.6; }

.filter .row { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.filter .row label { font-weight: 600; white-space: nowrap; color: var(--ink2); }

.empty { color: var(--muted); text-align: center; padding: 40px 20px; }

.summary { white-space: pre-wrap; line-height: 1.55; }

/* 弹窗 */
.mask {
  position: fixed; inset: 0; background: rgba(20, 22, 40, .45);
  display: flex; align-items: center; justify-content: center; z-index: 1000;
}
.modal {
  background: #fff; border-radius: var(--radius-lg); padding: 24px 26px;
  width: 540px; max-width: 92vw; max-height: 88vh; overflow: auto;
  box-shadow: 0 20px 60px rgba(20, 22, 40, .25);
}
.modal h3 { font-size: 18px; margin: 0 0 16px; }
.form-row { margin-bottom: 14px; }
.form-row label { display: block; font-weight: 600; margin-bottom: 6px; color: var(--ink2); }
.form-row textarea { width: 100%; resize: vertical; min-height: 120px; }
.modal-actions { display: flex; gap: 10px; justify-content: flex-end; margin-top: 8px; }
</style>
