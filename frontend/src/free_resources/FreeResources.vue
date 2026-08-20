<template>
  <div class="fr-page">
    <div class="fr-home-header">
      <!-- 顶部标题栏 -->
      <header class="fr-head">
        <div class="fr-title">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>
          </svg>
          <div>
            <h1>羊毛管理</h1>
            <p class="fr-sub">羊毛站 / 免费生图生视频：网址、操作步骤、截图一键收藏</p>
          </div>
        </div>
        <div class="fr-actions">
          <button class="btn primary" @click="openCreate">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="M12 5v14M5 12h14" /></svg>
            新建条目
          </button>
        </div>
      </header>

      <!-- 统计条（点击切换状态筛选） -->
      <section class="fr-stats" v-if="meta.counts">
        <div class="stat" :class="{ on: filters.status === '全部' }" @click="setStatus('全部')">
          <span class="stat-num">{{ meta.counts.total }}</span><span class="stat-lbl">全部</span>
        </div>
        <div class="stat s-available" :class="{ on: filters.status === 'available' }" @click="setStatus('available')">
          <span class="stat-num">{{ meta.counts.available }}</span><span class="stat-lbl">可用</span>
        </div>
        <div class="stat s-expired" :class="{ on: filters.status === 'expired' }" @click="setStatus('expired')">
          <span class="stat-num">{{ meta.counts.expired }}</span><span class="stat-lbl">已失效</span>
        </div>
      </section>

      <!-- 筛选栏 -->
      <section class="fr-filters">
        <div class="search-wrap">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/></svg>
          <input v-model="filters.keyword" class="search" type="text" placeholder="搜索标题 / 网址 / 平台 / 步骤 / 提示词 / 标签…" @input="debouncedLoad" />
        </div>

        <div class="filter-row">
          <span class="filter-label">分类</span>
          <div class="chips">
            <button v-for="c in catOptions" :key="c" :class="['chip', { on: filters.category === c }]" @click="setCat(c)">{{ c }}</button>
          </div>
        </div>

        <div class="filter-row inline">
          <label class="filter-label">标签</label>
          <select v-model="filters.tag" class="mini-select" @change="loadList">
            <option value="">全部标签</option>
            <option v-for="t in meta.all_tags" :key="t" :value="t">{{ t }}</option>
          </select>
          <span class="count">共 {{ list.length }} 条</span>
        </div>
      </section>
    </div>

    <div class="fr-home-body">
      <!-- 卡片列表 -->
      <section v-if="list.length" class="fr-grid">
      <article
        v-for="item in list"
        :key="item.id"
        class="fr-card"
        :class="['st-'+statusOf(item), { dragging: draggingId===item.id, dragover: dragOverId===item.id }]"
        @dragover.prevent="onDragOver(item)"
        @dragleave="onDragLeave(item)"
        @drop.prevent="onDrop(item)"
      >
        <div class="card-main" @click="openDetail(item)">
          <div class="card-top">
            <span class="drag-handle" title="拖拽排序" draggable="true" @dragstart.stop="onDragStart(item, $event)" @click.stop>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="9" cy="5" r="1.5"/><circle cx="15" cy="5" r="1.5"/><circle cx="9" cy="12" r="1.5"/><circle cx="15" cy="12" r="1.5"/><circle cx="9" cy="19" r="1.5"/><circle cx="15" cy="19" r="1.5"/>
              </svg>
            </span>
            <h3 class="card-title">{{ item.title }}</h3>
            <span class="status-dot" :class="'s-'+statusOf(item)" :title="statusLabel(statusOf(item))"></span>
          </div>
          <div class="card-badges">
            <span class="badge cat">{{ item.category }}</span>
          </div>
          <div v-if="item.tags" class="card-tags">
            <span v-for="t in splitTags(item.tags)" :key="t" class="tag">#{{ t }}</span>
          </div>
        </div>
        <div class="card-ops" @click.stop>
          <button class="fr-op" v-if="item.url" title="打开网站" @click="openUrl(item.url)">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/>
            </svg>
            <span>打开</span>
          </button>
          <button class="fr-op" title="编辑" @click="openEdit(item)">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
            </svg>
            <span>编辑</span>
          </button>
          <button class="fr-op danger" title="删除" @click="remove(item)">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
            </svg>
            <span>删除</span>
          </button>
        </div>
      </article>
    </section>

    <div v-else class="empty">
      <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg>
      <p>还没有羊毛资源，点右上角「新建条目」开始收藏羊毛站。</p>
    </div>
    </div>

    <!-- 编辑/新建弹窗 -->
    <div v-if="showEditor" class="modal-mask" @click.self="closeEditor">
      <div class="modal">
        <div class="modal-head">
          <h2>{{ editing.id ? '编辑条目' : '新建条目' }}</h2>
          <button class="x" @click="closeEditor">✕</button>
        </div>
        <div class="modal-body">
          <label class="fld">
            <span>标题 *</span>
            <input ref="titleInput" v-model="editing.title" type="text" placeholder="如：即梦 AI / 可灵免费额度领取" />
          </label>

          <label class="fld">
            <span>网址</span>
            <input v-model="editing.url" type="text" placeholder="https://…（留空则只作为备忘）" />
          </label>

          <div class="fld-row">
            <label class="fld">
              <span>分类</span>
              <select v-model="editing.category" class="category-select">
                <option v-for="c in formCatOptions" :key="c" :value="c">{{ c }}</option>
                <option value="__custom__">+ 自建分类</option>
              </select>
              <input v-if="editing.category === '__custom__'" v-model="customCategory" type="text" placeholder="输入新分类名称" />
            </label>
            <label class="fld">
              <span>标签</span>
              <div class="tag-pick">
                <div v-if="editingTagsArr.length" class="tag-chips">
                  <span v-for="t in editingTagsArr" :key="t" class="tchip">#{{ t }}<button type="button" @click="removeTag(t)">×</button></span>
                </div>
                <div class="tag-add-row">
                  <select class="tag-select" @change="($event.target.value && addTag($event.target.value)); $event.target.value = ''">
                    <option value="">选择已有标签</option>
                    <option v-for="t in tagOptions" :key="t" :value="t">{{ t }}</option>
                  </select>
                  <input v-model="newTag" type="text" placeholder="输入新标签回车添加" @keydown.enter.prevent="addNewTag" />
                </div>
              </div>
            </label>
          </div>

          <label class="fld">
            <span>状态</span>
            <div class="status-switch">
              <button type="button" class="sw sw-available" :class="{ on: editing.status !== 'expired' }" @click="editing.status = 'available'">可用</button>
              <button type="button" class="sw sw-expired" :class="{ on: editing.status === 'expired' }" @click="editing.status = 'expired'">已失效</button>
            </div>
          </label>

          <div class="fld-row">
            <label class="fld">
              <span>国内外</span>
              <select v-model="editing.region">
                <option value="">未选择</option>
                <option value="国内">国内</option>
                <option value="国外">国外</option>
              </select>
            </label>
            <label class="fld">
              <span>注册方式</span>
              <input v-model="editing.register_way" type="text" placeholder="手机号 / 邮箱 / Google" />
            </label>
          </div>
          <div class="fld-row">
            <label class="fld">
              <span>需梯子</span>
              <select v-model="editing.need_vpn">
                <option value="">未选择</option>
                <option value="是">是</option>
                <option value="否">否</option>
              </select>
            </label>
            <label class="fld">
              <span>画质</span>
              <select v-model="editing.quality">
                <option value="">未选择</option>
                <option value="480P">480P</option>
                <option value="720P">720P</option>
                <option value="1080P">1080P</option>
              </select>
            </label>
          </div>
          <div class="fld-row">
            <label class="fld">
              <span>支持模型</span>
              <input v-model="editing.support_model" type="text" placeholder="如 2.0 / Fast / Standard" />
            </label>
            <label class="fld">
              <span>验证日期</span>
              <input v-model="editing.verified_at" type="date" />
            </label>
          </div>
          <div class="fld-row">
            <label class="fld">
              <span>评级（1-5）</span>
              <input v-model="editing.rating" type="number" min="1" max="5" placeholder="如 4" />
            </label>
            <label class="fld">
              <span>每15秒积分消耗</span>
              <input v-model="editing.cost_15s_points" type="text" placeholder="如 5 积分" />
            </label>
          </div>
          <div class="fld-row">
            <label class="fld">
              <span>每15秒金额消耗</span>
              <input v-model="editing.cost_15s_amount" type="text" placeholder="如 ¥0.02" />
            </label>
          </div>

          <label class="fld">
            <span>平台</span>
            <input v-model="editing.platform" type="text" placeholder="即梦 / 可灵 / Midjourney…" />
          </label>
          <label class="fld">
            <span>操作步骤（自由文本）</span>
            <textarea v-model="editing.steps" rows="8" placeholder="1. 打开网址&#10;2. 注册/登录&#10;3. 每日签到领额度…"></textarea>
          </label>
          <label class="fld">
            <span>免费额度 / 限制说明</span>
            <input v-model="editing.quota" type="text" placeholder="如：每日免费 66 积分，需签到" />
          </label>
          <label class="fld">
            <span>相关提示词（自由文本）</span>
            <textarea v-model="editing.prompt_ref" rows="3" placeholder="配合使用的 prompt 关键词…"></textarea>
          </label>

          <div class="fld" v-if="editing.id">
            <span>操作步骤图（可多张）</span>
            <div class="img-grid">
              <div v-for="(img, i) in editing.images" :key="i" class="img-cell">
                <img :src="imgUrl(img)" alt="" />
                <div class="img-tools" @click.stop>
                  <button class="img-tool del" type="button" title="删除" @click="removeImage(img)">×</button>
                </div>
              </div>
            </div>
            <div class="img-upload">
              <input ref="imgInput" type="file" accept="image/*" multiple hidden @change="onImgPicked" />
              <button class="btn ghost sm" type="button" @click="imgInput?.click()">+ 选择操作步骤图</button>
              <button class="btn primary sm" type="button" :disabled="!pendingImgs.length" @click="uploadImages">上传 {{ pendingImgs.length || '' }}</button>
            </div>
            <div v-if="pendingImgs.length" class="img-pending">
              <img v-for="(p, i) in pendingImgs" :key="i" :src="p.preview" class="pending-thumb" alt="" />
            </div>
          </div>
          <p v-else class="img-hint">保存后即可上传操作步骤图。</p>

          <label class="fld">
            <span>备注</span>
            <input v-model="editing.note" type="text" placeholder="补充说明…" />
          </label>
        </div>
        <div class="modal-foot">
          <button class="btn ghost" @click="closeEditor">取消</button>
          <button class="btn primary" :disabled="saving" @click="save">{{ saving ? '保存中…' : '保存' }}</button>
        </div>
      </div>
    </div>

    <!-- 详情预览弹窗 -->
    <div v-if="showDetail" class="modal-mask" @click.self="closeDetail">
      <div class="modal">
        <div class="modal-head">
          <h2>{{ detail.title }}</h2>
          <button class="x" @click="closeDetail">✕</button>
        </div>
        <div class="modal-body">
          <div class="detail-badges">
            <span class="badge cat">{{ detail.category }}</span>
            <span v-if="detail.platform" class="badge plat">{{ detail.platform }}</span>
            <span class="badge st" :class="'bs-'+statusOf(detail)">{{ statusLabel(statusOf(detail)) }}</span>
            <div v-if="detail.tags" class="detail-tags">
              <span v-for="t in splitTags(detail.tags)" :key="t" class="tag">#{{ t }}</span>
            </div>
          </div>
          <div v-if="detail.url" class="detail-url">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>
            <a :href="detail.url" target="_blank" rel="noopener">{{ detail.url }}</a>
            <button class="url-copy" type="button" title="复制链接" @click="copyUrl(detail.url)">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
            </button>
          </div>

          <div class="detail-grid" v-if="detail.region || detail.register_way || detail.need_vpn || detail.quality || detail.support_model || detail.verified_at || detail.rating || detail.cost_15s_points || detail.cost_15s_amount || detail.quota">
            <div class="db-label">资源信息</div>
            <div class="dg-cell" v-if="detail.region"><span>国内外</span><b>{{ detail.region }}</b></div>
            <div class="dg-cell" v-if="detail.register_way"><span>注册方式</span><b>{{ detail.register_way }}</b></div>
            <div class="dg-cell" v-if="detail.need_vpn"><span>需梯子</span><b>{{ detail.need_vpn }}</b></div>
            <div class="dg-cell" v-if="detail.quality"><span>画质</span><b>{{ detail.quality }}</b></div>
            <div class="dg-cell" v-if="detail.support_model"><span>支持模型</span><b>{{ detail.support_model }}</b></div>
            <div class="dg-cell" v-if="detail.verified_at"><span>验证日期</span><b>{{ detail.verified_at }}</b></div>
            <div class="dg-cell" v-if="detail.rating"><span>评级</span><b>★ {{ detail.rating }}</b></div>
            <div class="dg-cell" v-if="detail.cost_15s_points"><span>每15秒积分消耗</span><b>{{ detail.cost_15s_points }}</b></div>
            <div class="dg-cell" v-if="detail.cost_15s_amount"><span>每15秒金额消耗</span><b>{{ detail.cost_15s_amount }}</b></div>
            <div class="dg-cell" v-if="detail.quota"><span>免费额度 / 限制</span><b>{{ detail.quota }}</b></div>
          </div>

          <div v-if="detail.images && detail.images.length" class="detail-imgs">
            <img v-for="(img, i) in detail.images" :key="i" :src="imgUrl(img)" class="detail-img" @click="openLightbox(img, detail.images)" alt="" />
          </div>

          <div class="detail-block" v-if="detail.steps">
            <div class="db-label">操作步骤</div>
            <pre class="detail-content">{{ detail.steps }}</pre>
          </div>
          <div class="detail-block" v-if="detail.prompt_ref">
            <div class="db-label">相关提示词</div>
            <pre class="detail-content">{{ detail.prompt_ref }}</pre>
          </div>
          <div class="detail-block" v-if="detail.note">
            <div class="db-label">备注</div>
            <div class="detail-text">{{ detail.note }}</div>
          </div>

        </div>
        <div class="modal-foot">
          <button class="btn ghost" @click="closeDetail">关闭</button>
          <button class="btn primary" v-if="detail.url" @click="openUrl(detail.url)">打开网站</button>
        </div>
      </div>
    </div>

    <!-- 图片灯箱：统一复用默认 MediaLightbox（含上一张/下一张 + 键盘操作） -->
    <MediaLightbox
      :visible="lightboxVisible"
      :items="lightboxItems"
      :index="lightboxIndex"
      @close="closeLightbox"
      @update:index="lightboxIndex = $event"
    />

    <!-- 轻提示 -->
    <transition name="fade">
      <div v-if="toast" class="toast">{{ toast }}</div>
    </transition>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { api, apiUpload } from '../common/http.js'
import { confirm } from '../common/useConfirm.js'
import MediaLightbox from '../filespace/MediaLightbox.vue'

const list = ref([])
const meta = reactive({ categories: [], all_tags: [] })
const filters = reactive({ keyword: '', category: '全部', tag: '', status: '全部' })

const catOptions = computed(() => ['全部', ...meta.categories])
const formCatOptions = computed(() => meta.categories.length ? meta.categories : ['生图', '生视频', '去水印', '剪辑', '配音', '其他'])

const showEditor = ref(false)
const editing = reactive(blankForm())
const saving = ref(false)
const customCategory = ref('')
const newTag = ref('')

const showDetail = ref(false)
const detail = ref({})

const toast = ref('')
let toastTimer = null
const titleInput = ref(null)
const imgInput = ref(null)
const pendingImgs = ref([])
// 统一灯箱状态（复用默认 MediaLightbox 组件）
const lightboxVisible = ref(false)
const lightboxItems = ref([])
const lightboxIndex = ref(0)
const draggingId = ref(null)
const dragOverId = ref(null)

const DRAFT_KEY = 'fr_new_draft'
function saveDraft() {
  if (!showEditor.value || editing.id) return
  const draft = { ...editing, customCategory: customCategory.value }
  try { sessionStorage.setItem(DRAFT_KEY, JSON.stringify(draft)) } catch (e) { /* ignore */ }
}
function loadDraft() {
  try {
    const raw = sessionStorage.getItem(DRAFT_KEY)
    if (!raw) return false
    const draft = JSON.parse(raw)
    Object.assign(editing, blankForm(), draft)
    if (draft.customCategory !== undefined) customCategory.value = draft.customCategory
    return true
  } catch (e) {
    return false
  }
}
function clearDraft() {
  try { sessionStorage.removeItem(DRAFT_KEY) } catch (e) { /* ignore */ }
}

let loadTimer = null
function debouncedLoad() {
  clearTimeout(loadTimer)
  loadTimer = setTimeout(loadList, 250)
}

async function loadMeta() {
  try {
    const m = await api('/free-resources/meta', 'GET')
    meta.categories = m.categories || []
    meta.all_tags = m.all_tags || []
    meta.counts = m.counts || { available: 0, expired: 0, total: 0 }
  } catch (e) { /* 忽略 */ }
}

async function loadList() {
  const q = new URLSearchParams({
    category: filters.category,
    keyword: filters.keyword,
    tag: filters.tag,
    status: filters.status === '全部' ? '' : filters.status,
  }).toString()
  try {
    const rows = await api(`/free-resources/list?${q}`, 'GET')
    list.value = rows.map(r => ({ ...r, images: parseImages(r.images) }))
  } catch (e) {
    showToast(e.message || '加载失败')
  }
}

function setCat(c) { filters.category = c; loadList() }
function setStatus(s) { filters.status = s; loadList() }

function blankForm() {
  return { id: null, title: '', url: '', category: '其他', platform: '', steps: '', quota: '', prompt_ref: '', note: '', tags: '', images: [],
    status: 'available', region: '', register_way: '', need_vpn: '', quality: '', support_model: '', verified_at: '', rating: '',
    cost_15s_points: '', cost_15s_amount: '' }
}

function openCreate() {
  newTag.value = ''
  const hasDraft = loadDraft()
  if (!hasDraft) {
    customCategory.value = ''
    Object.assign(editing, blankForm())
  }
  showEditor.value = true
}
function openEdit(item) {
  const known = formCatOptions.value.includes(item.category)
  customCategory.value = known ? '' : (item.category || '')
  Object.assign(editing, {
    id: item.id, title: item.title, url: item.url || '', category: known ? item.category : '__custom__',
    platform: item.platform || '', steps: item.steps || '', quota: item.quota || '',
    prompt_ref: item.prompt_ref || '', note: item.note || '', tags: item.tags || '',
    images: parseImages(item.images), status: item.status || 'available',
    region: item.region || '', register_way: item.register_way || '', need_vpn: item.need_vpn || '', quality: item.quality || '',
    support_model: item.support_model || '', verified_at: item.verified_at || '',
    rating: item.rating || '', cost_15s_points: item.cost_15s_points || '', cost_15s_amount: item.cost_15s_amount || ''
  })
  showEditor.value = true
}
function closeEditor() { showEditor.value = false }

async function save() {
  if (!editing.title.trim()) {
    showToast('标题不能为空')
    titleInput.value?.focus()
    return
  }
  const cat = editing.category === '__custom__' ? (customCategory.value.trim() || '其他') : editing.category
  saving.value = true
  try {
    const payload = {
      title: editing.title, url: editing.url || '', category: cat,
      platform: editing.platform, steps: editing.steps, quota: editing.quota,
      prompt_ref: editing.prompt_ref, note: editing.note, tags: editing.tags,
      status: editing.status || 'available', region: editing.region || '', register_way: editing.register_way || '',
      need_vpn: editing.need_vpn || '', quality: editing.quality || '', support_model: editing.support_model || '',
      // rating 用的是 <input type="number">，v-model 会自动转成数字，后端字段是字符串，这里统一转回来
      verified_at: editing.verified_at || '', rating: editing.rating === 0 || editing.rating ? String(editing.rating) : '',
      cost_15s_points: editing.cost_15s_points || '', cost_15s_amount: editing.cost_15s_amount || ''
    }
    console.log('[FreeResources] save payload', payload)
    if (editing.id) {
      await api(`/free-resources/${editing.id}`, 'PUT', payload)
    } else {
      await api('/free-resources/', 'POST', payload)
      clearDraft()
    }
    showEditor.value = false
    // 乐观同步标签
    const tagSet = new Set(meta.all_tags)
    splitTags(editing.tags).forEach(t => tagSet.add(t))
    meta.all_tags = Array.from(tagSet).sort()
    await loadMeta()
    await loadList()
    showToast('已保存')
  } catch (e) {
    console.error('[FreeResources] 保存失败', e)
    window.lastSaveError = e
    showToast(e.message || '保存失败')
  } finally {
    saving.value = false
  }
}

async function remove(item) {
  if (!(await confirm(`确定删除「${item.title}」？此操作不可撤销。`, { title: '删除确认' }))) return
  try {
    await api(`/free-resources/${item.id}`, 'DELETE')
    await loadMeta()
    await loadList()
    showToast('已删除')
  } catch (e) {
    showToast(e.message || '删除失败')
  }
}

function openUrl(url) {
  if (url) window.open(url, '_blank', 'noopener')
}

function copyUrl(url) {
  if (!url) return
  const done = () => showToast('链接已复制')
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(url).then(done).catch(() => legacyCopy(url, done))
  } else {
    legacyCopy(url, done)
  }
}
function legacyCopy(text, done) {
  const ta = document.createElement('textarea')
  ta.value = text
  ta.style.position = 'fixed'
  ta.style.opacity = '0'
  document.body.appendChild(ta)
  ta.select()
  try { document.execCommand('copy'); done() } catch (e) { showToast('复制失败，请手动复制') }
  document.body.removeChild(ta)
}

function openDetail(item) {
  detail.value = item
  showDetail.value = true
}
function closeDetail() { showDetail.value = false }

const STATUS_OPTS = [
  { val: 'available', label: '可用' },
  { val: 'expired', label: '已失效' },
]
function statusOf(item) {
  const st = item && item.status
  return st === 'expired' ? 'expired' : 'available'
}
function statusLabel(s) {
  const m = { available: '可用', expired: '已失效' }
  return m[s] || '可用'
}
function previewText(t) {
  if (!t) return ''
  const plain = t.replace(/\s+/g, ' ').trim()
  return plain.length > 120 ? plain.slice(0, 120) + '…' : plain
}
function splitTags(s) {
  return (s || '').split(',').map(x => x.trim()).filter(Boolean)
}
const editingTagsArr = computed(() => splitTags(editing.tags))
const tagOptions = computed(() => (meta.all_tags || []).filter(t => !editingTagsArr.value.includes(t)))
function addTag(t) {
  const arr = editingTagsArr.value
  if (!arr.includes(t)) arr.push(t)
  editing.tags = arr.join(', ')
}
function removeTag(t) {
  const arr = editingTagsArr.value.filter(x => x !== t)
  editing.tags = arr.join(', ')
}
function addNewTag() {
  const t = newTag.value.trim()
  if (!t) return
  addTag(t)
  newTag.value = ''
}

function parseImages(v) {
  if (Array.isArray(v)) return v
  if (!v) return []
  try { const a = JSON.parse(v); return Array.isArray(a) ? a : [] } catch { return [] }
}
function imgUrl(rel) {
  return '/api/free-resources/asset/' + rel
}
function openLightbox(rel, all) {
  const arr = Array.isArray(all) ? all : [rel]
  lightboxItems.value = arr.map(x => ({ url: imgUrl(x) }))
  lightboxIndex.value = Math.max(0, arr.indexOf(rel))
  lightboxVisible.value = true
}
function closeLightbox() { lightboxVisible.value = false }

function onDragStart(item, e) {
  draggingId.value = item.id
  if (e && e.dataTransfer) {
    e.dataTransfer.effectAllowed = 'move'
    e.dataTransfer.setData('text/plain', String(item.id))
  }
}
function onDragOver(item) {
  if (draggingId.value && draggingId.value !== item.id) dragOverId.value = item.id
}
function onDragLeave(item) {
  if (dragOverId.value === item.id) dragOverId.value = null
}
async function onDrop(item) {
  const from = draggingId.value
  const to = item.id
  draggingId.value = null
  dragOverId.value = null
  if (!from || from === to) return
  const ids = list.value.map(x => x.id)
  const fi = ids.indexOf(from)
  const ti = ids.indexOf(to)
  if (fi < 0 || ti < 0) return
  ids.splice(ti, 0, ids.splice(fi, 1)[0])
  const map = {}
  list.value.forEach(x => { map[x.id] = x })
  list.value = ids.map(id => map[id])
  try {
    await api('/free-resources/reorder', 'POST', { ids })
  } catch (e) {
    showToast('排序保存失败，已恢复')
    await loadList()
  }
}

function onImgPicked(e) {
  const files = Array.from(e.target.files || [])
  pendingImgs.value = files.map(f => ({ file: f, preview: URL.createObjectURL(f) }))
  e.target.value = ''
}
async function uploadImages() {
  if (!editing.id || !pendingImgs.value.length) return
  const fd = new FormData()
  for (const p of pendingImgs.value) fd.append('files', p.file)
  try {
    const updated = await apiUpload(`/free-resources/${editing.id}/images`, fd)
    editing.images = parseImages(updated.images)
    pendingImgs.value = []
    await loadList()
    showToast('操作步骤图已上传')
  } catch (err) {
    showToast(err.message || '上传失败')
  }
}
async function removeImage(rel) {
  if (!editing.id) return
  const fn = rel.split('/').pop()
  try {
    const updated = await api(`/free-resources/${editing.id}/images/${encodeURIComponent(fn)}`, 'DELETE')
    editing.images = parseImages(updated.images)
    await loadList()
    showToast('已删除操作步骤图')
  } catch (err) {
    showToast(err.message || '删除失败')
  }
}

function showToast(msg) {
  toast.value = msg
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => { toast.value = '' }, 2000)
}

watch(editing, saveDraft, { deep: true })
watch(customCategory, saveDraft)

onMounted(async () => {
  await loadMeta()
  await loadList()
})
</script>

<style scoped>
.fr-page {
  width: 100%;
  height: calc(100vh - 44px);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  font-family: system-ui, -apple-system, "Segoe UI", Roboto, "PingFang SC", "Microsoft YaHei", sans-serif;
  color: var(--sx-text-strong);
}
.fr-home-header { flex-shrink: 0; position: sticky; top: 0; z-index: 3; background: var(--sx-bg-page); }
.fr-home-body { flex: 1; overflow-y: auto; min-height: 0; }
.fr-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 18px;
}
.fr-title { display: flex; align-items: center; gap: 12px; color: var(--sx-accent-orange); }
.fr-title h1 { font-size: 22px; margin: 0; color: var(--sx-text-strong); }
.fr-sub { margin: 2px 0 0; font-size: 12.5px; color: var(--sx-text-muted); }
.fr-actions { display: flex; gap: 10px; }

.btn {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 9px 16px; border-radius: 10px; font-size: 14px; font-weight: 600;
  cursor: pointer; border: 1px solid transparent; transition: .15s;
}
.btn.primary { background: var(--sx-fr-btn-orange-bg); color: #fff; box-shadow: var(--sx-btn-orange-shadow); }
.btn.primary:hover { filter: brightness(1.05); }
.btn.primary:disabled { opacity: .6; cursor: default; }
.btn.ghost { background: var(--sx-bg-surface); border-color: var(--sx-border-strong); color: var(--sx-text); }
.btn.ghost:hover { background: var(--sx-bg-surface-2); }
.btn.sm { padding: 7px 12px; font-size: 13px; }

.fr-filters {
  background: var(--sx-bg-surface); border: 1px solid var(--sx-border); border-radius: 14px;
  padding: 16px; margin-bottom: 18px; box-shadow: var(--sx-shadow-card);
}
.search-wrap { display: flex; align-items: center; gap: 8px; background: var(--sx-bg-surface-2); border: 1px solid var(--sx-border); border-radius: 10px; padding: 0 12px; color: var(--sx-text-muted); }
.search-wrap .search { flex: 1; border: 0; background: transparent; padding: 11px 0; font-size: 14px; color: var(--sx-text-strong); outline: none; }
.filter-row { display: flex; align-items: center; gap: 10px; margin-top: 12px; flex-wrap: wrap; }
.filter-row.inline { gap: 14px; }
.filter-label { font-size: 12.5px; color: var(--sx-text-muted); font-weight: 600; flex-shrink: 0; }
.chips { display: flex; gap: 8px; flex-wrap: wrap; }
.chip {
  padding: 6px 13px; border-radius: 999px; border: 1px solid var(--sx-border); background: var(--sx-bg-surface);
  color: var(--sx-text); font-size: 13px; cursor: pointer; transition: .15s;
}
.chip:hover { border-color: var(--sx-accent-orange-soft-border); color: var(--sx-accent-orange); }
.chip.on { background: var(--sx-accent-orange); border-color: var(--sx-accent-orange); color: #fff; }
.mini-select { padding: 7px 10px; border-radius: 9px; border: 1px solid var(--sx-border); background: var(--sx-bg-surface); font-size: 13px; color: var(--sx-text); cursor: pointer; }
.count { margin-left: auto; font-size: 12.5px; color: var(--sx-text-muted); }

.fr-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 18px; }
.fr-card {
  background: var(--sx-bg-surface); border: 1px solid var(--sx-border); border-radius: 14px; padding: 18px;
  transition: .2s; display: flex; flex-direction: column; gap: 12px;
  box-shadow: var(--sx-shadow-card);
}
.fr-card:hover { border-color: var(--sx-accent-orange-soft-border); box-shadow: var(--sx-fr-card-orange-shadow); transform: translateY(-2px); }
.fr-card.st-expired { opacity: .55; }
.fr-card.st-expired .card-title { text-decoration: line-through; color: var(--sx-text-muted); }
.card-main { cursor: pointer; display: flex; flex-direction: column; gap: 8px; flex: 1; }
.card-top { display: flex; align-items: flex-start; gap: 8px; }
.drag-handle {
  display: inline-flex; align-items: center; justify-content: center;
  width: 22px; height: 22px; border-radius: 6px; margin: -2px 0 0 -4px;
  color: var(--sx-text-faint); cursor: grab; flex-shrink: 0; transition: .15s;
}
.drag-handle:hover { background: var(--sx-bg-surface-2); color: var(--sx-accent-orange); }
.drag-handle:active { cursor: grabbing; }
.card-title { font-size: 16px; margin: 0; color: var(--sx-text-strong); font-weight: 700; line-height: 1.35; flex: 1; word-break: break-word; }
.status-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; margin-top: 5px; }
.status-dot.s-available { background: var(--sx-tag-success-text); box-shadow: 0 0 0 3px var(--sx-tag-success-soft); }
.status-dot.s-expired { background: var(--sx-text-faint); }
.card-badges { display: flex; gap: 6px; flex-wrap: wrap; }
.badge { font-size: 11px; padding: 3px 9px; border-radius: 999px; font-weight: 600; }
.badge.cat { background: var(--sx-fr-accent-orange-soft-bg) !important; color: var(--sx-fr-accent-orange-muted-text) !important; }
.badge.plat { background: var(--sx-tag-purple-bg) !important; color: var(--sx-tag-purple-text) !important; }
.badge.note { background: var(--sx-tag-warn-bg) !important; color: var(--sx-tag-warn-text) !important; }
.card-tags { display: flex; gap: 5px; flex-wrap: wrap; }
.tag { font-size: 11px; color: var(--sx-text-muted); background: var(--sx-bg-surface-2); padding: 2px 7px; border-radius: 6px; }
.card-ops {
  display: flex; gap: 6px; margin-top: auto; padding-top: 10px;
  border-top: 1px solid var(--sx-border-faint); justify-content: flex-end; align-items: center;
}
.fr-op {
  display: inline-flex; align-items: center; justify-content: center; gap: 4px;
  flex: 0 0 auto; padding: 6px 10px; border-radius: 6px; border: 1px solid var(--sx-border);
  background: var(--sx-bg-surface); color: var(--sx-text); font-size: 12.5px; cursor: pointer; transition: .15s;
  white-space: nowrap; line-height: 1;
}
.fr-op:hover { background: var(--sx-bg-surface-2); color: var(--sx-link); border-color: var(--sx-border-hover); }
.fr-op.danger:hover { background: var(--sx-btn-danger-bg); color: var(--sx-btn-danger-text); border-color: var(--sx-btn-danger-border); }
.fr-op svg { flex-shrink: 0; width: 14px; height: 14px; }

.empty { text-align: center; color: var(--sx-text-muted); padding: 60px 20px; }
.empty svg { color: var(--sx-text-faint); margin-bottom: 12px; }
.empty p { font-size: 14px; max-width: 420px; margin: 0 auto; line-height: 1.6; }

.modal-mask { position: fixed; inset: 0; background: var(--sx-overlay); display: flex; align-items: center; justify-content: center; z-index: 50; padding: 20px; }
.modal { background: var(--sx-bg-elevated); border-radius: 16px; width: 100%; max-width: 900px; max-height: 90vh; display: flex; flex-direction: column; box-shadow: var(--sx-shadow-pop); }
.modal-head { display: flex; align-items: center; justify-content: space-between; padding: 18px 22px; border-bottom: 1px solid var(--sx-border-faint); }
.modal-head h2 { margin: 0; font-size: 17px; color: var(--sx-text-strong); }
.x { border: 0; background: transparent; font-size: 18px; color: var(--sx-text-muted); cursor: pointer; line-height: 1; }
.x:hover { color: var(--sx-btn-danger-text); }
.modal-body { padding: 20px 22px; overflow-y: auto; }
.modal-foot { display: flex; justify-content: flex-end; gap: 10px; padding: 14px 22px; border-top: 1px solid var(--sx-border-faint); }

.fld { display: flex; flex-direction: column; gap: 6px; margin-bottom: 14px; }
.fld > span { font-size: 12.5px; color: var(--sx-text); font-weight: 600; }
.fld input, .fld select, .fld textarea {
  border: 1px solid var(--sx-border-input); border-radius: 9px; padding: 10px 12px; font-size: 14px;
  color: var(--sx-text-strong); font-family: inherit; outline: none; transition: .15s; background: var(--sx-bg-surface);
}
.fld input, .fld textarea { cursor: text; }
.fld select { cursor: pointer; }
.fld input:hover, .fld select:hover, .fld textarea:hover { border-color: var(--sx-border-strong); box-shadow: var(--sx-shadow-card); }
.fld input:focus, .fld select:focus, .fld textarea:focus { border-color: var(--sx-accent-orange); box-shadow: 0 0 0 3px var(--sx-accent-orange-soft); }
.fld textarea { resize: vertical; line-height: 1.6; }
.fld-row { display: flex; gap: 14px; }
.fld-row .fld { flex: 1; }

.detail-badges { display: flex; gap: 7px; flex-wrap: wrap; align-items: center; margin-bottom: 12px; }
.detail-badges .detail-tags { display: flex; gap: 6px; flex-wrap: wrap; align-items: center; margin-left: 4px; }
.detail-url { display: flex; align-items: center; gap: 6px; font-size: 13px; color: var(--sx-accent-orange); margin-bottom: 14px; word-break: break-all; }
.detail-url a { color: var(--sx-accent-orange); text-decoration: none; }
.detail-url a:hover { text-decoration: underline; }
.detail-block { margin-bottom: 14px; }
.db-label { font-size: 12.5px; color: var(--sx-text); font-weight: 600; margin-bottom: 6px; }
.detail-content {
  background: var(--sx-bg-surface-2); border: 1px solid var(--sx-border); border-radius: 10px; padding: 14px;
  font-size: 13.5px; line-height: 1.7; color: var(--sx-text-strong); white-space: pre-wrap; word-break: break-word;
  max-height: 42vh; overflow-y: auto; margin: 0; font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
}
.detail-text { font-size: 13.5px; color: var(--sx-text-strong); line-height: 1.6; }

.toast {
  position: fixed; left: 50%; bottom: 40px; transform: translateX(-50%);
  background: var(--sx-toast-bg); color: var(--sx-toast-text); padding: 11px 22px; border-radius: 10px; font-size: 14px;
  box-shadow: var(--sx-shadow-pop); z-index: 80;
}
.fade-enter-active, .fade-leave-active { transition: opacity .25s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

.detail-imgs { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 14px; }
.detail-img { width: 240px; height: 135px; object-fit: cover; border-radius: 8px; cursor: zoom-in; border: 1px solid var(--sx-border); }

.img-grid { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 8px; }
.img-cell { position: relative; width: 84px; height: 84px; border-radius: 8px; overflow: hidden; border: 1px solid var(--sx-border); }
.img-cell img { width: 100%; height: 100%; object-fit: cover; }
.img-tools { position: absolute; left: 0; right: 0; bottom: 0; height: 22px; display: flex; align-items: center; justify-content: center; padding: 0 6px; background: rgba(20,22,40,.68); backdrop-filter: blur(2px); }
.img-tool { appearance: none; -webkit-appearance: none; display: inline-flex; align-items: center; justify-content: center; border: 0; background: transparent; color: #fff; cursor: pointer; padding: 0; font-size: 12px; line-height: 22px; opacity: .95; transition: .15s; }
.img-tool:hover { opacity: 1; }
.img-tool.del { font-size: 15px; }
.img-tool.del:hover { color: #ff9a9a; }
.img-upload { display: flex; gap: 8px; align-items: center; }
.img-pending { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 8px; }
.pending-thumb { width: 56px; height: 56px; object-fit: cover; border-radius: 6px; border: 1px solid var(--sx-border); }
.img-hint { font-size: 12.5px; color: var(--sx-text-muted); margin: -4px 0 14px; }

/* 统计条（兼状态筛选，点击切换） */
.fr-stats { display: flex; gap: 10px; margin-bottom: 16px; flex-wrap: wrap; }
.stat { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 3px; padding: 11px 20px; border-radius: 12px; background: var(--sx-bg-surface); border: 1px solid var(--sx-border); cursor: pointer; transition: .15s; min-width: 88px; }
.stat:hover { border-color: var(--sx-accent-orange-soft-border); }
.stat.on { border-color: var(--sx-accent-orange); box-shadow: 0 0 0 2px var(--sx-accent-orange-soft); }
.stat-num { font-size: 21px; font-weight: 800; color: var(--sx-text-strong); line-height: 1; }
.stat-lbl { font-size: 12px; color: var(--sx-text-muted); }
.stat.on .stat-lbl { color: var(--sx-accent-orange); }
.stat.s-available .stat-num { color: var(--sx-tag-success-text); }
.stat.s-expired .stat-num { color: var(--sx-text-muted); }

/* 状态色标 */
.fr-card.dragging { opacity: .4; }
.fr-card.dragover { border-color: var(--sx-accent-orange) !important; box-shadow: 0 0 0 2px var(--sx-accent-orange-soft); }

.modal-body .detail-badges .badge.cat { background: var(--sx-fr-accent-orange-soft-bg) !important; color: var(--sx-fr-accent-orange-muted-text) !important; }
.modal-body .detail-badges .badge.plat { background: var(--sx-tag-info-bg) !important; color: var(--sx-tag-info-text) !important; }
.badge.st { color: #fff !important; }
.badge.st.bs-available { background: var(--sx-tag-success-fill) !important; }
.badge.st.bs-expired { background: var(--sx-tag-default-fill) !important; }

.status-switch { display: inline-flex; background: var(--sx-bg-surface-2); border-radius: 10px; padding: 4px; gap: 4px; }
.sw { padding: 8px 22px; border-radius: 8px; border: 1px solid transparent; background: transparent; color: var(--sx-text); font-size: 13px; font-weight: 600; cursor: pointer; transition: .15s; }
.sw:hover { color: var(--sx-accent-orange); }
.sw:not(.on) { opacity: .45; }
.sw:not(.on):hover { opacity: .8; color: var(--sx-text); }
.sw.on.sw-available { background: var(--sx-tag-success-fill); color: #fff; box-shadow: var(--sx-tag-success-shadow); }
.sw.on.sw-expired { background: var(--sx-tag-default-fill); color: #fff; box-shadow: var(--sx-shadow-card); }

.category-select { padding: 10px 12px; border-radius: 9px; border: 1px solid var(--sx-border-input); background: var(--sx-bg-surface); font-size: 14px; color: var(--sx-text-strong); outline: none; cursor: pointer; transition: .15s; }
.category-select:hover { border-color: var(--sx-border-strong); box-shadow: var(--sx-shadow-card); }
.category-select:focus { border-color: var(--sx-accent-orange); box-shadow: 0 0 0 3px var(--sx-accent-orange-soft); }

.tag-pick { display: flex; flex-direction: column; gap: 8px; }
.tag-chips { display: flex; gap: 6px; flex-wrap: wrap; }
.tchip { display: inline-flex; align-items: center; gap: 4px; font-size: 12.5px; color: var(--sx-text); background: var(--sx-bg-surface-2); padding: 4px 6px 4px 8px; border-radius: 7px; }
.tchip button { border: 0; background: transparent; color: var(--sx-text-muted); cursor: pointer; font-size: 11px; line-height: 1; width: 15px; height: 15px; display: inline-flex; align-items: center; justify-content: center; border-radius: 50%; padding: 0; margin-left: 2px; }
.tchip button:hover { color: var(--sx-btn-danger-text); background: var(--sx-btn-danger-bg); }
.tag-add-row { display: flex; gap: 8px; align-items: center; }
.tag-select { padding: 9px 10px; border-radius: 9px; border: 1px solid var(--sx-border); background: var(--sx-bg-surface); font-size: 13px; color: var(--sx-text); cursor: pointer; outline: none; }
.tag-select:focus { border-color: var(--sx-accent-orange); box-shadow: 0 0 0 3px var(--sx-accent-orange-soft); }

.detail-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px 20px;
  margin-bottom: 14px;
  background: var(--sx-bg-surface);
  border: 1px solid var(--sx-border-strong);
  border-radius: 10px;
  padding: 14px 16px;
  box-shadow: var(--sx-shadow-card);
}
.detail-grid .db-label {
  grid-column: 1 / -1;
  margin-bottom: 2px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--sx-border-faint);
  font-size: 13px;
  color: var(--sx-text);
  display: flex;
  align-items: center;
  gap: 6px;
}
.detail-grid .db-label::before {
  content: '';
  width: 3px;
  height: 12px;
  background: var(--sx-accent-orange);
  border-radius: 2px;
}
.dg-cell { display: flex; flex-direction: column; align-items: flex-start; gap: 3px; font-size: 13.5px; padding: 5px 0; }
.dg-cell span { color: var(--sx-text-muted); font-weight: 500; width: 100%; text-align: left; }
.dg-cell b { color: var(--sx-text-strong); font-weight: 600; width: 100%; text-align: left; }

.url-copy { margin-left: 6px; border: 0; background: transparent; color: var(--sx-accent-orange); cursor: pointer; display: inline-flex; align-items: center; padding: 2px; border-radius: 6px; }
.url-copy:hover { background: var(--sx-accent-orange-soft); }

@media (max-width: 640px) {
  .fr-head { flex-direction: column; align-items: stretch; }
  .fr-actions { flex-direction: column; }
  .fld-row { flex-direction: column; gap: 0; }
  .fr-grid { grid-template-columns: 1fr; }
}
</style>
