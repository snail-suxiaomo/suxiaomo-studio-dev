<template>
  <div class="um-page">
    <header class="um-head">
      <div class="um-head-left">
        <h1 class="um-title">用户管理</h1>
        <p class="um-desc">查看并管理当前数据库中的所有用户信息（授权与角色后续再细化）</p>
      </div>
      <button class="um-action primary" @click="openAdd">+ 添加账号</button>
    </header>

    <section class="um-card">
      <div class="um-table-wrap">
        <table class="um-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>账号</th>
              <th>昵称</th>
              <th>创建时间</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="u in users" :key="u.id">
              <td>{{ u.id }}</td>
              <td>{{ u.username }}</td>
              <td>{{ u.display_name || '-' }}</td>
              <td>{{ fmtDate(u.created_at) }}</td>
              <td class="um-ops">
                <button class="um-action edit" @click="openEdit(u)">编辑</button>
                <button class="um-action del" @click="onDelete(u)">删除</button>
              </td>
            </tr>
            <tr v-if="!users.length && !loading">
              <td colspan="5" class="um-empty">暂无用户</td>
            </tr>
          </tbody>
        </table>
      </div>
      <p v-if="msg" class="um-msg" :class="ok ? 'ok' : 'err'">{{ msg }}</p>
    </section>

    <!-- 编辑弹窗 -->
    <div v-if="showEdit" class="um-dialog-overlay" @click.self="showEdit = false">
      <div class="um-dialog">
        <h3 class="um-dialog-title">编辑用户</h3>
        <label class="um-field">
          <span class="um-field-label">账号</span>
          <input v-model="form.username" class="um-input" placeholder="英文或英文+数字，字母开头" @input="onAccInput" />
        </label>
        <label class="um-field">
          <span class="um-field-label">昵称</span>
          <input v-model="form.display_name" class="um-input" placeholder="展示用昵称（可空）" />
        </label>
        <label class="um-field">
          <span class="um-field-label">新密码 <span class="um-opt">（留空则不修改）</span></span>
          <div class="um-pw-row">
            <input v-model="form.password" :type="showPwd ? 'text' : 'password'" class="um-input" placeholder="留空则不修改密码" autocomplete="new-password" />
            <button
              type="button"
              class="um-pw-eye"
              :title="showPwd ? '隐藏密码' : '显示密码'"
              @click="showPwd = !showPwd"
            >
              <svg v-if="showPwd" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.24m-8.72-1.07A3 3 0 1 1 9.88 9.88M1 1l22 22"/></svg>
              <svg v-else viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
            </button>
          </div>
        </label>
        <p v-if="dialogMsg" class="um-dialog-msg" :class="dialogOk ? 'ok' : 'err'">{{ dialogMsg }}</p>
        <div class="um-dialog-actions">
          <button class="um-action secondary" @click="showEdit = false">取消</button>
          <button class="um-action primary" :disabled="saving" @click="saveEdit">保存</button>
        </div>
      </div>
    </div>

    <!-- 添加账号弹窗 -->
    <div v-if="showAdd" class="um-dialog-overlay" @click.self="showAdd = false">
      <div class="um-dialog">
        <h3 class="um-dialog-title">添加账号</h3>
        <label class="um-field">
          <span class="um-field-label">账号</span>
          <input
            v-model="addForm.username"
            class="um-input"
            placeholder="英文或英文+数字，字母开头"
            autocomplete="off"
            @input="onAddAccInput"
          />
        </label>
        <label class="um-field">
          <span class="um-field-label">昵称</span>
          <input v-model="addForm.display_name" class="um-input" placeholder="展示用昵称（可空）" autocomplete="off" />
        </label>
        <label class="um-field">
          <span class="um-field-label">密码</span>
          <div class="um-pw-row">
            <input
              v-model="addForm.password"
              :type="showAddPwd ? 'text' : 'password'"
              class="um-input"
              placeholder="请输入密码"
              autocomplete="new-password"
            />
            <button
              type="button"
              class="um-pw-eye"
              :title="showAddPwd ? '隐藏密码' : '显示密码'"
              @click="showAddPwd = !showAddPwd"
            >
              <svg v-if="showAddPwd" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.24m-8.72-1.07A3 3 0 1 1 9.88 9.88M1 1l22 22"/></svg>
              <svg v-else viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
            </button>
          </div>
        </label>
        <p v-if="addMsg" class="um-dialog-msg" :class="addOk ? 'ok' : 'err'">{{ addMsg }}</p>
        <div class="um-dialog-actions">
          <button class="um-action secondary" @click="showAdd = false">取消</button>
          <button class="um-action primary" :disabled="adding" @click="saveAdd">创建</button>
        </div>
      </div>
    </div>

    <!-- 删除确认弹窗 -->
    <div v-if="showDelete" class="um-dialog-overlay" @click.self="showDelete = false">
      <div class="um-dialog um-dialog-confirm">
        <h3 class="um-dialog-title">删除用户</h3>
        <p class="um-confirm-body">
          确定删除用户「{{ pendingDelete?.username }}」？<br/>
          <span class="um-confirm-tip">关联的记住账号记录也会一并清除，且不可恢复。</span>
        </p>
        <div class="um-dialog-actions">
          <button class="um-action secondary" @click="showDelete = false">取消</button>
          <button class="um-action del" :disabled="deleting" @click="doDelete">确定删除</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { listUsers, adminUpdateUser, deleteUser, registerApi } from '../login/auth-api.js'

const users = ref([])
const loading = ref(false)
const msg = ref('')
const ok = ref(false)

const showEdit = ref(false)
const editingId = ref(null)
const form = ref({ username: '', display_name: '', password: '' })
const showPwd = ref(false)
const dialogMsg = ref('')
const dialogOk = ref(false)
const saving = ref(false)

const showDelete = ref(false)
const pendingDelete = ref(null)
const deleting = ref(false)

const showAdd = ref(false)
const addForm = ref({ username: '', display_name: '', password: '' })
const showAddPwd = ref(false)
const adding = ref(false)
const addMsg = ref('')
const addOk = ref(false)

function onAccInput(e) {
  const v = (e.target.value || '').replace(/[^a-zA-Z0-9]/g, '')
  form.value.username = v
  if (e.target.value !== v) e.target.value = v
}

function onAddAccInput(e) {
  const v = (e.target.value || '').replace(/[^a-zA-Z0-9]/g, '')
  addForm.value.username = v
  if (e.target.value !== v) e.target.value = v
}

function fmtDate(v) {
  if (!v) return '-'
  const d = new Date(v)
  if (isNaN(d.getTime())) return v
  return d.toLocaleString('zh-CN', { hour12: false })
}

async function load() {
  loading.value = true
  try {
    users.value = await listUsers()
  } catch (e) {
    msg.value = e.message || '加载失败'
    ok.value = false
  } finally {
    loading.value = false
  }
}

function openEdit(u) {
  editingId.value = u.id
  form.value = { username: u.username, display_name: u.display_name || '', password: '' }
  showPwd.value = false
  dialogMsg.value = ''
  showEdit.value = true
}

async function saveEdit() {
  dialogMsg.value = ''
  const data = {}
  const cur = users.value.find((u) => u.id === editingId.value)
  if (!cur) return
  if (form.value.username.trim() !== cur.username) data.username = form.value.username.trim()
  if (form.value.display_name !== (cur.display_name || '')) data.display_name = form.value.display_name
  if (form.value.password) data.password = form.value.password
  if (!Object.keys(data).length) {
    dialogMsg.value = '没有需要修改的内容'
    dialogOk.value = false
    return
  }
  saving.value = true
  try {
    await adminUpdateUser(editingId.value, data)
    dialogMsg.value = '已保存'
    dialogOk.value = true
    await load()
    setTimeout(() => { showEdit.value = false }, 400)
  } catch (e) {
    dialogMsg.value = e.message || '保存失败'
    dialogOk.value = false
  } finally {
    saving.value = false
  }
}

function openAdd() {
  addForm.value = { username: '', display_name: '', password: '' }
  showAddPwd.value = false
  addMsg.value = ''
  showAdd.value = true
}

async function saveAdd() {
  addMsg.value = ''
  const uname = addForm.value.username.trim()
  const pwd = addForm.value.password
  if (!uname) { addMsg.value = '请输入账号'; addOk.value = false; return }
  if (!/^[a-zA-Z][a-zA-Z0-9]{1,19}$/.test(uname)) { addMsg.value = '账号须为字母开头、仅含英文与数字，长度 2-20'; addOk.value = false; return }
  if (!pwd) { addMsg.value = '请输入密码'; addOk.value = false; return }
  adding.value = true
  try {
    await registerApi(uname, pwd, addForm.value.display_name || null)
    addMsg.value = '账号创建成功'
    addOk.value = true
    await load()
    setTimeout(() => { showAdd.value = false }, 400)
  } catch (e) {
    addMsg.value = e.message || '创建失败'
    addOk.value = false
  } finally {
    adding.value = false
  }
}

function onDelete(u) {
  pendingDelete.value = u
  showDelete.value = true
}

async function doDelete() {
  if (!pendingDelete.value) return
  deleting.value = true
  try {
    await deleteUser(pendingDelete.value.id)
    msg.value = `用户「${pendingDelete.value.username}」已删除`
    ok.value = true
    showDelete.value = false
    pendingDelete.value = null
    await load()
  } catch (e) {
    msg.value = e.message || '删除失败'
    ok.value = false
  } finally {
    deleting.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.um-page { width: 100%; padding-bottom: 40px; background: var(--sx-bg-page); }
.um-head {
  display: flex; align-items: flex-start; justify-content: space-between; gap: 16px;
  margin-bottom: 24px;
}
.um-head-left { flex: 1; min-width: 0; }
.um-title { font-size: 26px; font-weight: 700; color: var(--sx-text-strong); margin: 0 0 6px; }
.um-desc { margin: 0; color: var(--sx-text); font-size: 14px; }

.um-card {
  background: var(--sx-bg-surface);
  border: 1px solid var(--sx-border);
  border-radius: 16px;
  padding: 22px;
  box-shadow: var(--sx-shadow-card);
}
.um-table-wrap { overflow-x: auto; }
.um-table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  font-size: 14px;
  text-align: left;
}
.um-table th {
  padding: 12px 14px;
  font-weight: 600;
  color: var(--sx-text-emphasis);
  background: var(--sx-bg-surface-2);
  border-bottom: 1px solid var(--sx-border);
  white-space: nowrap;
}
.um-table td {
  padding: 12px 14px;
  color: var(--sx-text-strong);
  border-bottom: 1px solid var(--sx-border-faint);
  vertical-align: middle;
}
.um-table tbody tr:hover { background: var(--sx-row-hover); }
.um-ops { display: flex; gap: 8px; white-space: nowrap; }
.um-empty {
  text-align: center;
  color: var(--sx-text-muted);
  padding: 28px;
}
.um-msg { margin: 14px 0 0; font-size: 13px; }
.um-msg.ok { color: #2e7d32; }
.um-msg.err { color: #c0392b; }

/* 弹窗 */
.um-dialog-overlay {
  position: fixed; inset: 0; z-index: 1000;
  background: var(--sx-overlay);
  display: flex; align-items: center; justify-content: center;
}
.um-dialog {
  width: 90%; max-width: 420px;
  background: var(--sx-bg-elevated);
  border-radius: 16px;
  padding: 24px;
  box-shadow: var(--sx-shadow-pop);
}
.um-dialog-title { margin: 0 0 18px; font-size: 18px; font-weight: 700; color: var(--sx-text-strong); }
.um-field { display: flex; flex-direction: column; gap: 6px; margin-bottom: 14px; }
.um-field-label { font-size: 12.5px; color: var(--sx-text-emphasis); font-weight: 600; }
.um-field-label .um-opt { color: var(--sx-text-faint); font-weight: 400; }
.um-input {
  width: 100%; box-sizing: border-box;
  padding: 11px 13px; font-size: 14px;
  border: 1.5px solid var(--sx-border-input); border-radius: 10px;
  background: var(--sx-bg-surface-2); color: var(--sx-text-strong);
}
.um-input:focus { outline: none; border-color: var(--sx-accent); background: var(--sx-bg-surface); box-shadow: 0 0 0 3px var(--sx-accent-soft); }
.um-pw-row { position: relative; display: flex; align-items: center; }
.um-pw-row .um-input { padding-right: 40px; }
.um-pw-eye {
  position: absolute; right: 8px; top: 50%; transform: translateY(-50%);
  width: 26px !important; height: 26px !important;
  border: none; border-radius: 6px; background: transparent; cursor: pointer;
  display: flex !important; align-items: center; justify-content: center;
  padding: 0 !important; color: var(--sx-text-muted);
}
.um-pw-eye svg { display: block; }
.um-pw-eye:hover { color: #4f7cff; }
.um-dialog-actions {
  display: flex; justify-content: flex-end; gap: 10px;
  margin-top: 20px;
}
.um-dialog-msg { margin: -6px 0 6px; font-size: 13px; }
.um-dialog-msg.ok { color: #2e7d32; }
.um-dialog-msg.err { color: #c0392b; }

.um-dialog-confirm { max-width: 360px; }
.um-confirm-body {
  margin: 0 0 20px; font-size: 14px; color: var(--sx-text-strong); line-height: 1.7;
}
.um-confirm-tip { color: #c0392b; font-size: 13px; }

/* 按钮样式由 global.css 统一处理（.um-action / .um-action.edit / .del / .secondary / .primary） */
</style>