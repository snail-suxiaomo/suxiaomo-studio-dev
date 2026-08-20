<template>
  <div class="page">
    <h2>小说改写项目</h2>

    <!-- 新建项目 -->
    <div class="card">
      <h3>新建项目</h3>
      <div class="row">
        <input v-model="newName" placeholder="项目名，如《错嫁的小萤》" />
        <input v-model="newDesc" placeholder="简介（可选）" />
        <button @click="create">创建</button>
      </div>
      <p v-if="msg" class="msg">{{ msg }}</p>
    </div>

    <!-- 项目列表 -->
    <div class="card">
      <h3>全部项目</h3>
      <table v-if="projects.length">
        <colgroup>
          <col style="width: 8%" />
          <col style="width: 17%" />
          <col style="width: 12%" />
          <col style="width: 45%" />
          <col style="width: 200px" />
        </colgroup>
        <thead>
          <tr><th>ID</th><th>名称</th><th>状态</th><th>简介</th><th>操作</th></tr>
        </thead>
        <tbody>
          <tr v-for="p in projects" :key="p.id">
            <td>{{ p.id }}</td>
            <td><router-link :to="`/novel_project/${p.id}`" class="pname">{{ p.name }}</router-link></td>
            <td>
              <span :class="['badge', p.status]">{{ p.status }}</span>
            </td>
            <td class="desc">{{ p.description || '—' }}</td>
            <td class="ops">
              <button class="danger" @click="remove(p)">删除</button>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-else class="empty">还没有项目，先在上面创建一个。</p>
    </div>

    <section class="rule-tip">
      <div class="rule-tip-text">规则不完善，暂不支持使用</div>
    </section>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { api } from '../common/http.js'
import { confirm } from '../common/useConfirm.js'
import { useProjectStore } from '../common/project-store.js'

const projects = ref([])
const newName = ref('')
const newDesc = ref('')
const msg = ref('')
const proj = useProjectStore()
const current = computed(() => proj.current)

async function load() {
  projects.value = await api('/novel_project')
}

async function create() {
  msg.value = ''
  if (!newName.value.trim()) { msg.value = '请填项目名'; return }
  try {
    const row = await api('/novel_project', 'POST', { name: newName.value.trim(), description: newDesc.value.trim() || null })
    msg.value = `已创建：${row.name}`
    newName.value = ''
    newDesc.value = ''
    await load()
    proj.setCurrent({ id: row.id, name: row.name })
  } catch (e) {
    msg.value = e.message
  }
}

async function remove(p) {
  if (!(await confirm(`确定删除项目「${p.name}」？\n（仅删数据库记录，projects/${p.name}/ 下的文件需你手动清理）`, { title: '删除确认' }))) return
  await api(`/novel_project/${p.id}`, 'DELETE')
  if (current.value && current.value.id === p.id) proj.clear()
  await load()
}

onMounted(load)
</script>

<style scoped>
.page { max-width: 100%; }
.rule-tip {
  margin-bottom: 16px;
  padding: 22px;
  border-radius: 12px;
  background: linear-gradient(135deg, #fff4ec, #f3efff);
  border: 1px solid #f0d9c8;
  text-align: center;
}
.rule-tip-text {
  font-size: 32px;
  font-weight: 800;
  letter-spacing: 2px;
  background: linear-gradient(135deg, #ff7a3a, #7b5cff);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
}
.card { background: #fff; border: 1px solid #ececec; border-radius: 10px; padding: 16px 18px; margin-bottom: 16px; }
.row { display: flex; gap: 8px; flex-wrap: wrap; }
input { padding: 7px 10px; border: 1px solid #ccc; border-radius: 6px; flex: 1; min-width: 160px; }
button { padding: 7px 14px; border: none; border-radius: 6px; background: #4f7cff; color: #fff; cursor: pointer; }
button.danger { background: #e25b5b; }
.msg { color: #2a7; margin-top: 8px; }
.desc { color: #666; }
.ops button { margin-right: 6px; }
.pname { color: #4f7cff; text-decoration: none; font-weight: 600; }
.pname:hover { text-decoration: underline; }
.badge { padding: 2px 8px; border-radius: 10px; font-size: 12px; }
.badge.active { background: #e6f7ec; color: #2a7; }
.badge.archived { background: #f0f0f0; color: #888; }
.empty { color: #999; }
.rule-tip {
  margin-bottom: 16px;
  padding: 22px 24px;
  border-radius: 12px;
  background: linear-gradient(135deg, #fff4ec, #f3efff);
  border: 1px solid #f0d9c8;
  text-align: center;
}
.rule-tip-text {
  font-size: 30px;
  font-weight: 800;
  letter-spacing: 2px;
  background: linear-gradient(135deg, #ff7a3a, #7b5cff);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
}
</style>
