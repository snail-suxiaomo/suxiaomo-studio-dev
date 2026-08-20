<template>
  <div class="sa-page">
    <div class="sa-head">
      <div class="sa-title">
        <h1>账号矩阵</h1>
        <p class="sa-sub">统一管理各平台账号信息，支持手动增删改、Excel 一键导入与选择性导出。导入时按表头自动识别列名，建议先<a href="#" @click.prevent="downloadTemplate">下载模板</a>。</p>
      </div>
      <div class="sa-actions">
        <template v-if="managing">
          <button class="btn ghost" @click="exportAll">导出全部</button>
          <button class="btn ghost" :disabled="!selectedIds.length" @click="exportSelected">
            导出选中（{{ selectedIds.length }}）
          </button>
          <button class="btn ghost" @click="openImport">导入</button>
        </template>
        <button class="btn" :class="managing ? 'primary' : 'ghost'" @click="toggleManaging">
          {{ managing ? '返回列表' : '管理' }}
        </button>
        <button class="btn primary" @click="openCreate">+ 新增账号</button>
      </div>
    </div>

    <div v-if="loading" class="sa-loading">加载中…</div>
    <div v-else-if="!accounts.length" class="sa-empty">
      还没有账号，点「+ 新增账号」或「导入 Excel」开始汇总
    </div>

    <div v-else class="sa-table-wrap">
      <table class="sa-table">
        <thead>
          <tr>
            <th v-if="managing" class="col-sel">
              <input type="checkbox" :checked="allSelected" @change="toggleAll" />
            </th>
            <th class="col-idx">序号</th>
            <th class="col-platform">平台</th>
            <th class="col-name">账号名称</th>
            <th class="col-id">账号ID</th>
            <th class="col-userid">
              UserId
              <button class="icon-btn eye" :title="showUserId ? '隐藏' : '显示'" @click.stop="showUserId = !showUserId">
                {{ showUserId ? '🙈' : '👁' }}
              </button>
            </th>
            <th class="col-gender">性别</th>
            <th class="col-birth">生日</th>
            <th class="col-loc">所在地</th>
            <th class="col-link">主页链接</th>
            <th class="num">获赞</th>
            <th class="num">互关</th>
            <th class="num">关注</th>
            <th class="num">粉丝</th>
            <th class="col-op">操作</th>
          </tr>
        </thead>
        <tbody>
          <template v-for="(a, i) in accounts" :key="a.id">
            <tr class="row-main" :class="{ 'row-open': expandedId === a.id }" @click="toggleExpand(a.id)">
              <td v-if="managing" class="col-sel" @click.stop>
                <input type="checkbox" :checked="isSelected(a.id)" @change="toggleSelect(a.id)" />
              </td>
              <td class="col-idx">{{ i + 1 }}</td>
              <td class="col-platform"><span class="pill">{{ a.platform || '-' }}</span></td>
              <td class="cell-name col-name">{{ a.account_name || '-' }}</td>
              <td class="col-id">
                <div class="cell-flex">
                  <span class="id-text cell-dim">{{ a.account_id || '-' }}</span>
                  <button v-if="a.account_id" class="copy" title="复制账号ID" @click.stop="copyText(a.account_id)">📋</button>
                </div>
              </td>
              <td class="col-userid">
                <div class="cell-flex">
                  <template v-if="a.user_id">
                    <span v-if="showUserId" class="id-text">{{ a.user_id }}</span>
                    <span v-else class="mask">************</span>
                    <button class="copy" title="复制UserId" @click.stop="copyText(a.user_id)">📋</button>
                  </template>
                  <span v-else class="cell-dim">-</span>
                </div>
              </td>
              <td class="col-gender">{{ a.gender || '-' }}</td>
              <td class="col-birth">{{ a.birthday || '-' }}</td>
              <td class="col-loc">{{ a.location || '-' }}</td>
              <td class="col-link" :title="a.homepage_url">
                <div class="cell-flex">
                  <template v-if="a.homepage_url">
                    <a :href="a.homepage_url" target="_blank" rel="noopener" class="link-text" @click.stop>{{ a.homepage_url }}</a>
                    <button class="copy" title="复制链接" @click.stop="copyText(a.homepage_url)">📋</button>
                  </template>
                  <span v-else>-</span>
                </div>
              </td>
              <td class="num">{{ fmtNum(a.likes_count) }}</td>
              <td class="num">{{ fmtNum(a.mutual_count) }}</td>
              <td class="num">{{ fmtNum(a.following_count) }}</td>
              <td class="num">{{ fmtNum(a.followers_count) }}</td>
              <td class="col-op" @click.stop>
                <button class="op" @click="openEdit(a)">编辑</button>
                <button class="op danger" @click="remove(a)">删除</button>
              </td>
            </tr>
            <tr v-if="expandedId === a.id" class="row-detail">
              <td :colspan="managing ? 15 : 14">
                <div class="detail">
                  <div class="detail-rows">
                    <div class="d-row d-bio"><span class="d-k">简介</span><span class="d-v">{{ a.bio || '-' }}</span></div>
                    <div class="d-row d-imgs">
                      <div class="img-block">
                        <span class="d-k">二维码</span>
                        <img v-if="a.qr_image" :src="imgUrl(a.qr_image)" class="img-prev" @click.stop="preview(a.qr_image)" />
                        <span v-else class="img-placeholder">未上传</span>
                      </div>
                      <div class="img-block">
                        <span class="d-k">封面</span>
                        <img v-if="a.cover_image" :src="imgUrl(a.cover_image)" class="img-prev" @click.stop="preview(a.cover_image)" />
                        <span v-else class="img-placeholder">未上传</span>
                      </div>
                    </div>
                  </div>
                </div>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>

    <!-- 新增 / 编辑 弹窗 -->
    <div v-if="showForm" class="modal-mask" @click.self="closeForm">
      <div class="modal">
        <div class="modal-head">
          <h2>{{ editing ? '编辑账号' : '新增账号' }}</h2>
          <button class="x" @click="closeForm">✕</button>
        </div>
        <div class="modal-body">
          <div class="grid2">
            <label class="fld"><span>平台 *</span>
              <input v-model="form.platform" placeholder="如：抖音" />
            </label>
            <label class="fld"><span>账号名称 *</span>
              <input v-model="form.account_name" placeholder="如：苏小沫" />
            </label>
            <label class="fld"><span>账号ID *</span>
              <input v-model="form.account_id" />
            </label>
            <label class="fld"><span>UserId</span>
              <input v-model="form.user_id" />
            </label>
            <label class="fld"><span>主页链接</span>
              <input v-model="form.homepage_url" placeholder="https://" />
            </label>
            <label class="fld"><span>性别</span>
              <input v-model="form.gender" />
            </label>
            <label class="fld"><span>生日</span>
              <input v-model="form.birthday" placeholder="如：1998-05-20" />
            </label>
            <label class="fld"><span>所在地</span>
              <input v-model="form.location" />
            </label>
            <label class="fld"><span>获赞</span>
              <input v-model.number="form.likes_count" type="number" min="0" />
            </label>
            <label class="fld"><span>互关</span>
              <input v-model.number="form.mutual_count" type="number" min="0" />
            </label>
            <label class="fld"><span>关注</span>
              <input v-model.number="form.following_count" type="number" min="0" />
            </label>
            <label class="fld"><span>粉丝</span>
              <input v-model.number="form.followers_count" type="number" min="0" />
            </label>
          </div>
          <label class="fld"><span>简介</span>
            <textarea v-model="form.bio" rows="2" placeholder="账号简介 / 签名"></textarea>
          </label>
          <div class="grid2">
            <div class="fld">
              <span>二维码图片</span>
              <div class="img-row">
                <img v-if="form.qr_image" :src="imgUrl(form.qr_image)" class="img-prev" @click="preview(form.qr_image)" />
                <span v-else class="img-placeholder">未上传</span>
                <label for="qrInput" class="btn ghost sm">上传</label>
                <button v-if="form.qr_image" class="btn ghost sm" type="button" @click="form.qr_image=''">移除</button>
                <input id="qrInput" ref="qrInput" type="file" accept="image/*" class="file-input-hidden" @change="onImgPicked($event, 'qr_image')" />
              </div>
            </div>
            <div class="fld">
              <span>封面图片</span>
              <div class="img-row">
                <img v-if="form.cover_image" :src="imgUrl(form.cover_image)" class="img-prev" @click="preview(form.cover_image)" />
                <span v-else class="img-placeholder">未上传</span>
                <label for="coverInput" class="btn ghost sm">上传</label>
                <button v-if="form.cover_image" class="btn ghost sm" type="button" @click="form.cover_image=''">移除</button>
                <input id="coverInput" ref="coverInput" type="file" accept="image/*" class="file-input-hidden" @change="onImgPicked($event, 'cover_image')" />
              </div>
            </div>
          </div>
        </div>
        <div class="modal-foot">
          <button class="btn ghost" @click="closeForm">取消</button>
          <button class="btn primary" :disabled="saving || !form.platform.trim() || !form.account_name.trim()" @click="submitForm">
            {{ saving ? '保存中…' : '保存' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 图片预览 -->
    <!-- 导入 Excel 弹窗 -->
    <div v-if="showImport" class="modal-mask" @click.self="closeImport">
      <div class="modal" style="width:560px">
        <div class="modal-head">
          <h2>导入</h2>
          <button class="x" @click="closeImport">✕</button>
        </div>
        <div class="modal-body">
          <div class="imp-section">
            <div class="imp-sec-title">① 文件类型</div>
            <p class="imp-tip">可导入 <b>.xlsx</b>（纯账号文本）或 <b>.zip</b>（「导出全部 / 导出选中」得到的带图包）。</p>
          </div>

          <div class="imp-section">
            <div class="imp-sec-title">② 选择导入方式</div>
            <label class="imp-opt">
              <input type="radio" value="skip" v-model="importMode" />
              <span><b>仅新增（跳过已有）</b><small>已有账号 ID 保持不变，只把表格里的新账号加到后面。<br/>适合：在现有账号基础上补充新账号。</small></span>
            </label>
            <label class="imp-opt">
              <input type="radio" value="overwrite" v-model="importMode" />
              <span><b>新增或更新（按 ID 覆盖）</b><small>账号 ID 重复的行，用表格内容更新已有账号；不存在的则新增。<br/>适合：批量修改已有账号的信息。</small></span>
            </label>
          </div>

          <div class="imp-section imp-note">
            <div class="imp-sec-title">③ 图片怎么匹配</div>
            <p class="imp-tip">zip 内的图片按「平台_账号ID」命名自动关联，重新导入或换库都能正确回显，无需手动选图。</p>
          </div>
          <div class="imp-file">
            <input id="importInput" ref="importInput" type="file" accept=".xlsx,.xls,.zip" class="file-input-hidden" @change="onImportPicked" />
            <label for="importInput" class="btn ghost">选择文件</label>
            <span class="imp-fname">{{ importFile ? importFile.name : '未选择文件' }}</span>
          </div>
        </div>
        <div class="modal-foot">
          <button class="btn" @click="closeImport">取消</button>
          <button class="btn primary" :disabled="!importFile" @click="startImport">开始导入</button>
        </div>
      </div>
    </div>

    <div v-if="previewUrl" class="modal-mask" @click.self="previewUrl=''" style="background:rgba(0,0,0,.8)">
      <img :src="imgUrl(previewUrl)" class="preview-big" />
      <button class="x preview-x" @click="previewUrl=''">✕</button>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { api, apiUpload } from '../common/http.js'
import { confirm } from '../common/useConfirm.js'
import { useAuthStore } from '../login/auth-store.js'

const auth = useAuthStore()
const loading = ref(true)
const accounts = ref([])
const selectedIds = ref([])
const importMode = ref('skip')
const importInput = ref(null)
const importFile = ref(null)
const showImport = ref(false)
const qrInput = ref(null)
const coverInput = ref(null)
const previewUrl = ref('')
const managing = ref(false)
const showUserId = ref(false)

function toggleManaging() {
  managing.value = !managing.value
  if (!managing.value) clearSelection()
}

async function copyText(text) {
  if (!text) return
  try {
    await navigator.clipboard.writeText(text)
    showToast('已复制')
  } catch {
    const ta = document.createElement('textarea')
    ta.value = text
    document.body.appendChild(ta)
    ta.select()
    document.execCommand('copy')
    document.body.removeChild(ta)
    showToast('已复制')
  }
}

const showForm = ref(false)
const editing = ref(false)
const saving = ref(false)
const formId = ref(null)
const form = reactive({
  platform: '', account_name: '', account_id: '', user_id: '',
  homepage_url: '', bio: '', gender: '', birthday: '', location: '',
  likes_count: 0, mutual_count: 0, following_count: 0, followers_count: 0,
  qr_image: '', cover_image: '',
})

const allSelected = computed(() =>
  accounts.value.length > 0 && selectedIds.value.length === accounts.value.length)
const isSelected = (id) => selectedIds.value.includes(id)
const expandedId = ref(null)

function toggleExpand(id) {
  expandedId.value = expandedId.value === id ? null : id
}
function fmtNum(n) {
  const v = Number(n) || 0
  if (v >= 10000) return (v / 10000).toFixed(1).replace(/\.0$/, '') + 'w'
  return String(v)
}

function imgUrl(rel) {
  return `/api/social-accounts/asset/${rel}`
}
function preview(rel) { previewUrl.value = rel }
function toggleSelect(id) {
  const i = selectedIds.value.indexOf(id)
  if (i >= 0) selectedIds.value.splice(i, 1)
  else selectedIds.value.push(id)
}
function toggleAll(e) {
  if (e.target.checked) selectedIds.value = accounts.value.map((a) => a.id)
  else selectedIds.value = []
}
function clearSelection() { selectedIds.value = [] }

async function load() {
  loading.value = true
  try {
    accounts.value = await api('/social-accounts', 'GET')
    clearSelection()
  } catch (e) {
    showToast(e.message || '加载失败')
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editing.value = false
  formId.value = null
  Object.assign(form, {
    platform: '', account_name: '', account_id: '', user_id: '',
    homepage_url: '', bio: '', gender: '', birthday: '', location: '',
    likes_count: 0, mutual_count: 0, following_count: 0, followers_count: 0,
    qr_image: '', cover_image: '',
  })
  showForm.value = true
}
function openEdit(a) {
  editing.value = true
  formId.value = a.id
  Object.assign(form, {
    platform: a.platform || '', account_name: a.account_name || '', account_id: a.account_id || '',
    user_id: a.user_id || '', homepage_url: a.homepage_url || '', bio: a.bio || '',
    gender: a.gender || '', birthday: a.birthday || '', location: a.location || '',
    likes_count: a.likes_count ?? 0, mutual_count: a.mutual_count ?? 0,
    following_count: a.following_count ?? 0, followers_count: a.followers_count ?? 0,
    qr_image: a.qr_image || '', cover_image: a.cover_image || '',
  })
  showForm.value = true
}
function closeForm() { showForm.value = false }

async function onImgPicked(e, field) {
  const f = e.target.files && e.target.files[0]
  if (!f) return
  try {
    const fd = new FormData()
    fd.append('file', f)
    const r = await apiUpload('/social-accounts/upload-image', fd)
    form[field] = r.path
  } catch (err) {
    showToast(err.message || '上传失败')
  } finally {
    e.target.value = ''
  }
}

async function submitForm() {
  if (!form.platform.trim() || !form.account_name.trim() || !form.account_id.trim()) {
    showToast('平台、账号名称、账号ID 均为必填项'); return
  }
  saving.value = true
  const payload = {
    platform: form.platform.trim(), account_name: form.account_name.trim(),
    account_id: form.account_id.trim(), user_id: form.user_id.trim(),
    homepage_url: form.homepage_url.trim(), bio: form.bio.trim(),
    gender: form.gender.trim(), birthday: form.birthday.trim(), location: form.location.trim(),
    likes_count: Number(form.likes_count) || 0, mutual_count: Number(form.mutual_count) || 0,
    following_count: Number(form.following_count) || 0, followers_count: Number(form.followers_count) || 0,
    qr_image: form.qr_image, cover_image: form.cover_image,
  }
  try {
    if (editing.value) await api(`/social-accounts/${formId.value}`, 'PUT', payload)
    else await api('/social-accounts', 'POST', payload)
    showForm.value = false
    await load()
    showToast('已保存')
  } catch (e) {
    showToast(e.message || '保存失败')
  } finally {
    saving.value = false
  }
}

async function remove(a) {
  if (!(await confirm(`确定删除「${a.account_name}」？此操作不可撤销。`, { title: '删除确认' }))) return
  try {
    await api(`/social-accounts/${a.id}`, 'DELETE')
    selectedIds.value = selectedIds.value.filter((id) => id !== a.id)
    await load()
    showToast('已删除')
  } catch (e) {
    showToast(e.message || '删除失败')
  }
}

// 导入
function openImport() {
  importFile.value = null
  importMode.value = 'skip'
  showImport.value = true
}
function closeImport() {
  showImport.value = false
}
function onImportPicked(e) {
  const f = e.target.files && e.target.files[0]
  importFile.value = f || null
}
async function startImport() {
  const f = importFile.value
  if (!f) return
  try {
    const fd = new FormData()
    fd.append('file', f)
    fd.append('mode', importMode.value)
    const url = /\.zip$/i.test(f.name) ? '/social-accounts/import-bundle' : '/social-accounts/import'
    const r = await apiUpload(url, fd)
    const parts = []
    if (r.imported) parts.push(`新增 ${r.imported}`)
    if (r.updated) parts.push(`更新 ${r.updated}`)
    if (r.skipped) parts.push(`跳过 ${r.skipped}`)
    const errs = r.errors && r.errors.length ? r.errors : []
    if (errs.length) {
      const head = parts.length ? '导入完成（' + parts.join('，') + '），' : ''
      const detail = errs.slice(0, 3).join('；') + (errs.length > 3 ? ` 等共 ${errs.length} 行` : '')
      showToast(head + `有 ${errs.length} 行因缺少必填项未导入：` + detail)
    } else if (parts.length) {
      showToast('导入完成：' + parts.join('，'))
    } else {
      showToast('未导入任何数据，请检查 Excel：表头下方是否填写了账号行（至少填「平台」「账号名称」「账号ID」）')
    }
    closeImport()
    await load()
  } catch (err) {
    showToast(err.message || '导入失败')
  } finally {
    if (importInput.value) importInput.value.value = ''
    importFile.value = null
  }
}

// 导出（全部/选中 均为带图 zip 包）
async function downloadBundle(ids) {
  const body = JSON.stringify(ids && ids.length ? { ids } : {})
  try {
    const res = await fetch('/api/social-accounts/export-bundle', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(auth.token ? { Authorization: `Bearer ${auth.token}` } : {}),
      },
      body,
    })
    if (!res.ok) throw new Error('导出失败')
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = (ids && ids.length) ? `账号矩阵_选中${ids.length}.zip` : '账号矩阵_全部.zip'
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
  } catch (e) {
    showToast(e.message || '导出失败')
  }
}
function exportAll() { downloadBundle(null) }
function exportSelected() { if (selectedIds.value.length) downloadBundle(selectedIds.value) }

// 下载模板
async function downloadTemplate() {
  try {
    const auth = useAuthStore()
    const res = await fetch('/api/social-accounts/template', {
      headers: auth.token ? { Authorization: `Bearer ${auth.token}` } : {},
    })
    if (!res.ok) throw new Error('模板下载失败')
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = '账号矩阵导入模板.xlsx'
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
  } catch (e) {
    showToast(e.message || '模板下载失败')
  }
}

// 轻量 toast
let toastTimer = null
const toastMsg = ref('')
function showToast(msg) {
  toastMsg.value = msg
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => { toastMsg.value = '' }, 2600)
}

onMounted(load)
</script>

<style scoped>
.sa-page { padding: 18px 22px 40px; }
.sa-head { display: flex; justify-content: space-between; align-items: flex-end; gap: 16px; flex-wrap: wrap; margin-bottom: 16px; }
.sa-title h1 { font-size: 22px; margin: 0; }
.sa-sub { margin: 4px 0 0; font-size: 13px; color: var(--sx-text-muted); line-height: 1.7; }
.sa-sub a { display: inline-block; background: var(--sx-tag-info-bg); color: var(--sx-link); padding: 1px 8px; border-radius: 6px; font-weight: 600; text-decoration: none; transition: .15s; margin: 0 2px; }
.sa-sub a:hover { background: var(--sx-accent-soft); color: var(--sx-accent-strong); text-decoration: none; }
.sa-actions { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.btn { display: inline-flex; align-items: center; justify-content: center; padding: 8px 14px; border-radius: 9px; border: 1px solid var(--sx-border); background: var(--sx-bg-surface); cursor: pointer; font-size: 14px; }
.btn.primary { background: var(--sx-btn-primary-solid-bg); border-color: var(--sx-btn-primary-solid-bg); color: #fff; }
.btn.primary:hover { background: var(--sx-btn-primary-solid-hover); border-color: var(--sx-btn-primary-solid-hover); }
.btn.ghost { background: var(--sx-bg-surface-2); color: var(--sx-text-strong); }
.btn.sm { padding: 5px 10px; font-size: 13px; }
.btn:disabled { opacity: .5; cursor: not-allowed; }
.sel.sm { padding: 7px 8px; border-radius: 9px; border: 1px solid var(--sx-border); background: var(--sx-bg-surface-2); font-size: 13px; }
.import-wrap { display: flex; align-items: center; gap: 6px; }

.sa-loading, .sa-empty { padding: 60px; text-align: center; color: var(--sx-text-muted); }
.sa-table-wrap { overflow: auto; border: 1px solid var(--sx-border); border-radius: 12px; background: var(--sx-bg-surface); }
.sa-table { border-collapse: collapse; width: 100%; font-size: 13px; min-width: 1380px; }
.sa-table th, .sa-table td { border-bottom: 1px solid var(--sx-border-faint); padding: 9px 10px; text-align: left; white-space: nowrap; }
.sa-table thead th { background: var(--sx-bg-surface-2); position: sticky; top: 0; z-index: 1; color: var(--sx-text-emphasis); }
.sa-table .num { text-align: right; font-variant-numeric: tabular-nums; }
.col-sel { width: 38px; text-align: center; }
.col-idx { width: 42px; text-align: center; color: var(--sx-text-muted); }
.col-platform { width: 72px; text-align: center; }
.col-name { max-width: 100px; overflow: hidden; text-overflow: ellipsis; }
.col-id { max-width: 190px; }
.col-userid { width: 220px; }
.col-gender { width: 52px; text-align: center; }
.col-birth { width: 92px; }
.col-loc { width: 104px; }
.col-link { max-width: 220px; }
.col-link a { color: var(--sx-link); text-decoration: none; }
.col-op { width: 120px; }
.cell-flex { display: flex; align-items: center; gap: 4px; }
.cell-flex .id-text, .cell-flex .link-text, .cell-flex .mask { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; vertical-align: middle; }
.cell-flex .copy { margin-left: auto; }
.sa-table .num { width: 48px; }
.copy { padding: 2px 5px; font-size: 11px; line-height: 1; border: 1px solid var(--sx-border); background: var(--sx-bg-surface); border-radius: 5px; cursor: pointer; color: var(--sx-text-muted); vertical-align: middle; flex-shrink: 0; }
.copy:hover { border-color: var(--sx-accent); color: var(--sx-accent); }
.icon-btn.eye { margin-left: 4px; padding: 1px 4px; font-size: 12px; line-height: 1; border: 1px solid var(--sx-border); background: var(--sx-bg-surface); border-radius: 5px; cursor: pointer; color: var(--sx-text-muted); vertical-align: middle; }
.mask { color: var(--sx-text-faint); letter-spacing: 1px; }
.row-main { cursor: pointer; }
.row-main:hover { background: var(--sx-row-hover); }
.row-open { background: var(--sx-row-selected-bg) !important; }
.pill { display: inline-block; padding: 2px 10px; background: var(--sx-tag-info-bg); color: var(--sx-tag-info-text); border-radius: 999px; font-size: 12px; }
.cell-name { font-weight: 600; color: var(--sx-text-strong); }
.cell-dim { color: var(--sx-text-muted); }
.op { padding: 4px 10px; border: 1px solid var(--sx-border); background: var(--sx-bg-surface); border-radius: 7px; cursor: pointer; font-size: 12px; margin-right: 4px; }
.op.danger { color: var(--sx-btn-danger-text); border-color: var(--sx-btn-danger-border); }

/* 展开详情 */
.row-detail td { background: var(--sx-row-hover); padding: 0; }
.detail { padding: 14px 18px; }
.detail-rows { display: flex; flex-direction: column; gap: 10px; }
.d-row { display: flex; gap: 12px; font-size: 13px; line-height: 1.6; }
.d-row.d-bio { flex-direction: column; gap: 6px; }
.d-row.d-bio .d-k { min-width: 0; }
.d-bio .d-v { white-space: pre-wrap; line-height: 1.7; color: var(--sx-text-strong); }
.d-row.d-imgs { flex-direction: row; gap: 24px; margin-top: 2px; }
.d-k { color: var(--sx-text-muted); min-width: 56px; flex-shrink: 0; }
.d-v { color: var(--sx-text-strong); word-break: break-all; }
.d-v a { color: var(--sx-link); text-decoration: none; }
.img-block { display: flex; flex-direction: column; gap: 6px; }
.img-block .img-prev { width: 56px; height: 56px; border-radius: 8px; object-fit: cover; cursor: pointer; border: 1px solid var(--sx-border-faint); }
.img-placeholder { font-size: 12px; color: var(--sx-text-faint); }

.modal-mask { position: fixed; inset: 0; background: var(--sx-overlay); display: flex; align-items: center; justify-content: center; z-index: 200; }
.modal { width: 720px; max-width: 94vw; max-height: 90vh; overflow: auto; background: var(--sx-bg-surface); border-radius: 14px; box-shadow: var(--sx-shadow-pop); }
.modal-head { display: flex; justify-content: space-between; align-items: center; padding: 16px 20px; border-bottom: 1px solid var(--sx-border-faint); }
.modal-head h2 { margin: 0; font-size: 18px; }
.modal-body { padding: 18px 20px; }
.modal-foot { display: flex; justify-content: flex-end; gap: 10px; padding: 14px 20px; border-top: 1px solid var(--sx-border-faint); }
.x { border: none; background: none; font-size: 18px; cursor: pointer; color: var(--sx-text-muted); }
.grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 12px 16px; }
.fld { display: flex; flex-direction: column; gap: 5px; font-size: 13px; color: var(--sx-text); }
.fld input, .fld textarea, .fld select { padding: 8px 10px; border: 1px solid var(--sx-border); border-radius: 8px; font-size: 14px; font-family: inherit; }
.img-row { display: flex; align-items: center; gap: 8px; }
.img-prev { width: 46px; height: 46px; border-radius: 6px; object-fit: cover; cursor: pointer; border: 1px solid var(--sx-border-faint); }
.img-placeholder { font-size: 12px; color: var(--sx-text-faint); }
.preview-big { max-width: 80vw; max-height: 80vh; border-radius: 10px; }

/* 导入 Excel 弹窗 */
.imp-section { border: 1px solid var(--sx-border-faint); border-radius: 12px; padding: 12px 14px; margin-bottom: 12px; background: var(--sx-row-hover); }
.imp-section.imp-note { background: var(--sx-tag-success-bg); border-color: var(--sx-tag-success-border); }
.imp-sec-title { font-size: 13px; font-weight: 700; color: var(--sx-text-strong); margin-bottom: 6px; }
.imp-tip { margin: 0; color: var(--sx-text); font-size: 13px; line-height: 1.6; }
.imp-tip b { color: var(--sx-text-strong); }
.imp-opt { display: flex; gap: 10px; align-items: flex-start; padding: 11px 12px; border: 1px solid var(--sx-border); border-radius: 10px; margin-bottom: 8px; cursor: pointer; }
.imp-opt:hover { border-color: var(--sx-accent); background: var(--sx-row-hover); }
.imp-opt input { margin-top: 3px; }
.imp-opt b { display: block; font-size: 14px; color: var(--sx-text-strong); font-weight: 600; }
.imp-opt small { color: var(--sx-text-muted); font-size: 12px; }
.imp-opt .warn { color: var(--sx-btn-danger-text); }
.imp-file { display: flex; align-items: center; gap: 10px; margin-top: 14px; }
.file-input-hidden { position: absolute; opacity: 0; width: 0; height: 0; pointer-events: none; }
.imp-fname { color: var(--sx-text); font-size: 13px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 280px; }
.preview-x { position: fixed; top: 24px; right: 28px; color: #fff; font-size: 26px; z-index: 210; }

/* toast */
:global(.sa-toast) { position: fixed; bottom: 30px; left: 50%; transform: translateX(-50%); background: var(--sx-toast-bg); color: var(--sx-toast-text); padding: 10px 18px; border-radius: 10px; font-size: 14px; z-index: 500; }
</style>
