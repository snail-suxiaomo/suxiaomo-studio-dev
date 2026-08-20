<template>
  <div class="page">
    <div class="crumb">
      <router-link to="/novel_project">← 小说项目</router-link>
      <span class="sep">/</span>
      <span class="cur">{{ project ? project.name : '加载中…' }}</span>
    </div>

    <!-- 项目信息 -->
    <div class="card head">
      <div class="hrow">
        <div class="title">
          <h2>{{ project ? project.name : '加载中…' }}</h2>
          <span v-if="project" :class="['badge', project.status]">{{ project.status }}</span>
        </div>
        <div class="hactions">
          <button class="ghost" @click="goList">返回列表</button>
          <button v-if="project && project.status !== 'archived'" class="ghost" @click="archive">归档</button>
          <button class="danger" @click="remove">删除</button>
        </div>
      </div>
      <p class="desc">{{ project ? (project.description || '（无简介）') : '' }}</p>
      <p class="meta" v-if="project && project.updated_at">更新于 {{ project.updated_at }}</p>
    </div>

    <!-- 管线功能入口 -->
    <div class="card">
      <h3>管线功能</h3>
      <p class="hint">每个步骤拆分为「校验 / 生成 / 审核」三块，分别选择要使用的 AI 调用规则，点「AI 分析」进入执行页。</p>
      <div v-if="isArchived" class="archived-bar">
        ⚠️ 该项目已归档，所有管线功能已禁用。恢复激活后可继续使用。
        <button class="ghost" @click="activate">恢复激活</button>
      </div>
      <div class="pipeline-list" :class="{ disabled: isArchived }">
        <div
          v-for="f in features"
          :key="f.fid"
          class="pipeline-row"
          :class="{ disabled: isArchived }"
        >
          <div class="row-main">
            <div class="function-icon" v-html="f.icon"></div>
            <div class="function-title">{{ f.no }}-{{ f.name }}</div>
          </div>

          <div class="row-rules">
            <div
              v-for="rb in f.roles"
              :key="rb.role"
              class="role-block"
              :class="'rb-' + rb.role"
            >
              <span class="role-label">{{ rb.label }}</span>
              <select
                class="mini-select"
                :disabled="isArchived || stepStates[f.fid]?.byRole[rb.role]?.loading"
                :value="selectedValue(f.fid, rb.role)"
                @change="onRoleChange(f.fid, rb.role, $event)"
              >
                <option value="">未选择</option>
                <optgroup label="我的规则">
                  <option
                    v-for="r in stepStates[f.fid]?.byRole[rb.role]?.dbRules || []"
                    :key="r.id"
                    :value="'db:' + r.id"
                  >{{ r.name }}</option>
                </optgroup>
                <optgroup label="参考规则">
                  <option
                    v-for="r in stepStates[f.fid]?.byRole[rb.role]?.refRules || []"
                    :key="r.ref_path"
                    :value="'ref:' + r.ref_path"
                  >{{ r.name }}</option>
                </optgroup>
              </select>
              <span v-if="selectedRule(f.fid, rb.role)" class="remembered-text">✓ {{ selectedRule(f.fid, rb.role).name }}</span>
            </div>
          </div>

          <div class="row-action">
            <button
              class="btn primary"
              :disabled="isArchived || stepStates[f.fid]?.loading"
              @click="runStep(f)"
            >
              <span v-if="stepStates[f.fid]?.executing" class="mini-spin"></span>
              🤖 AI 分析
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, reactive } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../common/http.js'
import { confirm } from '../common/useConfirm.js'
import { useProjectStore } from '../common/project-store.js'

const route = useRoute()
const router = useRouter()
const proj = useProjectStore()

const project = ref(null)
const isArchived = computed(() => project.value && project.value.status === 'archived')
const stepStates = reactive({})

const MENU = '小说改写'

// 每个功能拆成三块，顺序：校验 / 生成 / 审核
const ROLE_ORDER = [
  { role: 'format', label: '校验' },
  { role: 'generate', label: '生成' },
  { role: 'review', label: '审核' },
]

const ICONS = {
  split: '<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/></svg>',
  synopsis: '<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>',
  graph: '<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="5" r="3"/><circle cx="5" cy="19" r="3"/><circle cx="19" cy="19" r="3"/><line x1="12" y1="8" x2="5" y2="16"/><line x1="12" y1="8" x2="19" y2="16"/></svg>',
  diagnose: '<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>',
  strategy: '<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>',
  table: '<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="3" y1="15" x2="21" y2="15"/><line x1="9" y1="3" x2="9" y2="21"/><line x1="15" y1="3" x2="15" y2="21"/></svg>',
  rewrite: '<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>',
}

const features = [
  { no: '00', name: '小说拆分', route: '/novel_split',       fid: '00-拆分', icon: ICONS.split,  roles: [{ role: 'review', label: '审核' }] },
  { no: '01', name: '小说梗概', route: '/novel_synopsis',    fid: '01-梗概', icon: ICONS.synopsis, roles: ROLE_ORDER },
  { no: '02', name: '小说图谱', route: '/novel_graph',       fid: '02-图谱', icon: ICONS.graph,    roles: ROLE_ORDER },
  { no: '03', name: '小说诊断', route: '/novel_diagnose',    fid: '03-诊断', icon: ICONS.diagnose, roles: ROLE_ORDER },
  { no: '04', name: '小说策略', route: '/novel_strategy',    fid: '04-策略', icon: ICONS.strategy, roles: ROLE_ORDER },
  { no: '05', name: '小说总表', route: '/novel_summary_table', fid: '05-总表', icon: ICONS.table,   roles: ROLE_ORDER },
  { no: '06', name: '小说改写', route: '/novel_rewrite',     fid: '06-改写', icon: ICONS.rewrite,  roles: ROLE_ORDER },
]

function getState(fid) {
  if (!stepStates[fid]) {
    const byRole = {}
    for (const rb of ROLE_ORDER) byRole[rb.role] = { loading: false, dbRules: [], refRules: [], active: null }
    stepStates[fid] = { loading: false, executing: false, byRole }
  }
  return stepStates[fid]
}

function selectedValue(fid, role) {
  const b = getState(fid).byRole[role]
  if (!b.active) return ''
  // 一旦复制进 DB 就按 id 匹配，避免参考规则选项被过滤后 select 显示「未选择」
  if (b.active.id) return 'db:' + b.active.id
  if (b.active.ref_path) return 'ref:' + b.active.ref_path
  return ''
}

function selectedRule(fid, role) {
  return getState(fid).byRole[role].active
}

async function load() {
  const list = await api('/novel_project')
  const id = Number(route.params.id)
  project.value = list.find((p) => p.id === id) || null
  if (project.value) proj.setCurrent({ id: project.value.id, name: project.value.name, status: project.value.status })
  await loadAllRules()
}

async function loadAllRules() {
  for (const f of features) {
    const s = getState(f.fid)
    s.loading = true
    try {
      const [dbRows, refRows] = await Promise.all([
        api('/ai-rules?menu=' + encodeURIComponent(MENU) + '&function_key=' + encodeURIComponent(f.fid)),
        api('/ai-rules/references'),
      ])
      const copiedPaths = new Set((dbRows || []).map((r) => r.ref_path).filter(Boolean))
      for (const rb of f.roles) {
        const blk = s.byRole[rb.role]
        blk.dbRules = (dbRows || []).filter((r) => r.function_key === f.fid && r.role === rb.role)
        blk.refRules = (refRows || []).filter(
          (r) => r.menu === MENU && r.function_key === f.fid && r.role === rb.role && !copiedPaths.has(r.ref_path)
        )
        // 默认仅显示用户已启用(即曾选中)的规则；未选过时保持「未选择」，绝不替用户默认挑一条
        blk.active = blk.dbRules.find((r) => r.enabled) || null
      }
    } finally {
      s.loading = false
    }
  }
}

async function onRoleChange(fid, role, e) {
  const val = e.target.value
  const f = features.find((x) => x.fid === fid)
  if (!f) return
  const b = getState(fid).byRole[role]
  if (!val) {
    b.active = null
    return
  }
  b.loading = true
  try {
    let chosen = null
    if (val.startsWith('db:')) {
      chosen = b.dbRules.find((r) => String(r.id) === val.slice(3))
    } else {
      chosen = b.refRules.find((r) => r.ref_path === val.slice(4))
    }
    let payload
    if (val.startsWith('db:')) {
      payload = { menu: MENU, function_key: fid, role, rid: Number(val.slice(3)) }
    } else {
      payload = { menu: MENU, function_key: fid, role, ref_path: val.slice(4) }
    }
    await api('/ai-rules/set-active', 'POST', payload)
    // 刷新该角色规则列表，避免参考/自建状态不同步
    const [dbRows, refRows] = await Promise.all([
      api('/ai-rules?menu=' + encodeURIComponent(MENU) + '&function_key=' + encodeURIComponent(fid)),
      api('/ai-rules/references'),
    ])
    const copiedPaths = new Set((dbRows || []).map((r) => r.ref_path).filter(Boolean))
    b.dbRules = (dbRows || []).filter((r) => r.function_key === fid && r.role === role)
    b.refRules = (refRows || []).filter(
      (r) => r.menu === MENU && r.function_key === fid && r.role === role && !copiedPaths.has(r.ref_path)
    )
    // 重新从「已启用的自建规则」里取当前激活项，保证 selectedValue 能匹配到 option
    b.active = b.dbRules.find((r) => r.enabled) || null
  } finally {
    b.loading = false
  }
}

async function runStep(f) {
  if (!project.value) return
  if (isArchived.value) {
    await alert('该项目已归档，功能已禁用，请先恢复激活。')
    return
  }
  const s = getState(f.fid)
  s.executing = true
  try {
    proj.setCurrent({ id: project.value.id, name: project.value.name })
    router.push(f.route)
  } finally {
    s.executing = false
  }
}

function goList() {
  router.push('/novel_project')
}

async function archive() {
  if (!project.value) return
  if (!(await confirm('归档后该项目所有功能将不可用，需恢复激活才能继续。确定归档？', { title: '归档确认' }))) return
  await api(`/novel_project/${project.value.id}/archive`, 'PUT')
  await load()
}

async function activate() {
  if (!project.value) return
  await api(`/novel_project/${project.value.id}/activate`, 'PUT')
  await load()
}

async function remove() {
  if (!project.value) return
  if (!(await confirm(`确定删除项目「${project.value.name}」？\n（仅删数据库记录，projects/${project.value.name}/ 下的文件需你手动清理）`, { title: '删除确认' }))) return
  await api(`/novel_project/${project.value.id}`, 'DELETE')
  if (proj.current && proj.current.id === project.value.id) proj.clear()
  router.push('/novel_project')
}

onMounted(load)
</script>

<style scoped>
.page { max-width: 100%; }
.crumb { font-size: 13px; color: #888; margin-bottom: 14px; }
.crumb a { color: #4f7cff; text-decoration: none; }
.crumb a:hover { text-decoration: underline; }
.crumb .sep { margin: 0 8px; }
.crumb .cur { color: #333; }
.card { background: #fff; border: 1px solid #ececec; border-radius: 12px; padding: 18px 20px; margin-bottom: 16px; }
.head h2 { margin: 0 0 8px; font-size: 20px; }
.title { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.hrow { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; }
.hactions { display: flex; gap: 8px; flex-shrink: 0; }
.desc { color: #555; margin: 12px 0 4px; line-height: 1.6; }
.meta { color: #999; font-size: 13px; margin: 0; }
.badge { padding: 2px 10px; border-radius: 10px; font-size: 12px; }
.badge.active { background: #e6f7ec; color: #2a7; }
.badge.archived { background: #f0f0f0; color: #888; }
button { padding: 7px 14px; border: none; border-radius: 8px; background: #4f7cff; color: #fff; cursor: pointer; font-size: 14px; }
button.ghost { background: #eef1f8; color: #445; }
button.danger { background: #e25b5b; }
button:disabled { opacity: .6; cursor: not-allowed; }
.hint { color: #999; font-size: 13px; margin: 0 0 14px; }

.archived-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  background: #fff7e6;
  border: 1px solid #ffe08a;
  color: #9a6b00;
  border-radius: 10px;
  padding: 12px 16px;
  margin-bottom: 14px;
  font-size: 13px;
}
.archived-bar .ghost {
  background: #4f7cff;
  color: #fff;
  border: none;
}

.pipeline-list.disabled { opacity: .5; pointer-events: none; }

.pipeline-row {
  display: flex;
  align-items: center;
  gap: 18px;
  padding: 14px 16px;
  border: 1px solid #e8eaf0;
  border-radius: 12px;
  background: #fff;
  margin-bottom: 12px;
  transition: all .2s;
}
.pipeline-row:hover {
  border-color: #b9c4ff;
  background: rgba(79, 124, 255, .03);
}
.pipeline-row.disabled {
  cursor: not-allowed;
  opacity: .6;
}

.row-main {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 150px;
  flex-shrink: 0;
}
.function-icon { color: #4f7cff; }
.function-title {
  font-size: 14px;
  font-weight: 600;
  color: #2b2f44;
}

.row-rules {
  flex: 1;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px 20px;
  min-width: 0;
}

.role-block {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  padding: 6px 10px;
  border: 1px solid #eef0f4;
  border-radius: 10px;
  background: #fafbfd;
}
.role-label {
  font-size: 12px;
  font-weight: 700;
  padding: 2px 9px;
  border-radius: 8px;
  white-space: nowrap;
  flex-shrink: 0;
}
.rb-format .role-label { background: #E6F1FB; color: #0C447C; }
.rb-generate .role-label { background: #E7F6EC; color: #1C7A3E; }
.rb-review .role-label { background: #F0ECFD; color: #4A3C9E; }

.mini-select {
  min-width: 160px;
  max-width: 240px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  padding: 5px 9px;
  font-size: 13px;
  background: #fff;
  color: #374151;
  font-family: inherit;
  outline: none;
}
.mini-select:focus {
  border-color: #4f7cff;
  box-shadow: 0 0 0 3px rgba(79, 124, 255, .15);
}
.remembered-text {
  font-size: 12px;
  color: #185fa5;
  font-weight: 600;
  white-space: nowrap;
}

.row-action {
  flex-shrink: 0;
}

.mini-spin {
  display: inline-block;
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255,255,255,.4);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin .8s linear infinite;
  vertical-align: middle;
  margin-right: 4px;
}
@keyframes spin { to { transform: rotate(360deg); } }
</style>
