<template>
  <div class="wn-page">
    <!-- 顶部标题栏 -->
    <header class="wn-head">
      <div class="wn-title">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="10" />
          <line x1="2" y1="12" x2="22" y2="12" />
          <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
        </svg>
        <div>
          <h1>网址导航</h1>
          <p class="wn-sub">常用网站快捷链接，分类收藏，一键直达</p>
        </div>
      </div>
      <div class="wn-actions">
        <button class="btn primary" @click="openCreate">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="M12 5v14M5 12h14" /></svg>
          新建链接
        </button>
      </div>
    </header>

    <!-- 筛选栏 -->
    <section class="wn-filters">
      <div class="search-wrap">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/></svg>
        <input v-model="filters.keyword" class="search" type="text" placeholder="搜索标题 / 网址 / 备注 / 标签…" @input="debouncedLoad" />
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

    <!-- 卡片列表 -->
    <section v-if="list.length" class="wn-grid">
      <article
        v-for="(item, idx) in list"
        :key="item.id"
        class="wn-card"
        :class="{ dragging: dragIndex === idx, dragover: overIndex === idx }"
        draggable="true"
        @dragstart="onDragStart(idx, $event)"
        @dragover.prevent="onDragOver(idx)"
        @dragleave="onDragLeave(idx)"
        @drop.prevent="onDrop(idx)"
        @dragend="onDragEnd"
        @click="openDetail(item)"
      >
        <div class="card-cover" :class="{ placeholder: !coverOf(item) }" @click.stop="coverOf(item) && openLightbox(coverOf(item), list.map(coverOf).filter(Boolean))">
          <img v-if="coverOf(item)" :src="imgUrl(coverOf(item))" alt="" />
          <div v-else class="cover-placeholder" :style="placeholderStyle(item.title)">
            <span>{{ titleInitial(item.title) }}</span>
          </div>
        </div>
        <div class="card-top">
          <h3 class="card-title">{{ item.title }}</h3>
        </div>
        <div class="card-badges">
          <span class="badge cat">{{ item.category }}</span>
        </div>

        <div v-if="item.tags" class="card-tags">
          <span v-for="t in splitTags(item.tags)" :key="t" class="tag">#{{ t }}</span>
        </div>
        <div class="card-ops" @click.stop>
          <button class="op" v-if="item.url" title="打开" @click="openUrl(item.url)">打开</button>
          <button class="op" title="编辑" @click="openEdit(item)">编辑</button>
          <button class="op danger" title="删除" @click="remove(item)">删除</button>
        </div>
      </article>
    </section>

    <div v-else class="empty">
      <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10" /><line x1="2" y1="12" x2="22" y2="12" /><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" /></svg>
      <p>还没有收藏的网站，点右上角「新建链接」开始搭建你的导航。</p>
    </div>

    <!-- 编辑/新建弹窗 -->
    <div v-if="showEditor" class="modal-mask" @click.self="closeEditor">
      <div class="modal">
        <div class="modal-head">
          <h2>{{ editing.id ? '编辑链接' : '新建链接' }}</h2>
          <button class="x" @click="closeEditor">✕</button>
        </div>
        <div class="modal-body">
          <label class="fld">
            <span>标题 *</span>
            <input v-model="editing.title" type="text" placeholder="如：即梦 AI 官网 / 豆瓣" />
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
              <span>标签（逗号分隔）</span>
              <input v-model="editing.tags" type="text" placeholder="生图, 生视频, 每日领积分" />
            </label>
          </div>

          <label class="fld">
            <span>备注</span>
            <textarea v-model="editing.note" rows="3" placeholder="补充说明…"></textarea>
          </label>

          <div class="fld" v-if="editing.id">
            <span>图标 / 截图（可选）</span>
            <div class="img-grid">
              <div v-for="(img, i) in editing.images" :key="i" class="img-cell" :class="{ cover: img === editing.cover_image }">
                <img :src="imgUrl(img)" alt="" @click.stop="openLightbox(img, editing.images)" />
                <div class="img-tools" @click.stop>
                  <button class="img-tool cover" type="button" title="裁剪为封面" @click="cropCoverFrom(img)">
                    <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
                    <span>封面</span>
                  </button>
                  <button class="img-tool del" type="button" title="删除" @click="removeImage(img)">×</button>
                </div>
              </div>
            </div>
            <div class="img-upload">
              <input ref="imgInput" type="file" accept="image/*" multiple hidden @change="onImgPicked" />
              <button class="btn ghost sm" type="button" @click="imgInput?.click()">+ 选择图片</button>
              <span class="img-hint-inline">点击缩略图可预览；点击“封面”可把该图裁剪为 16:9 封面</span>
            </div>
          </div>
          <p v-else class="img-hint">保存后即可上传图标/截图。</p>
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
          </div>
          <div v-if="detail.url" class="detail-url">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>
            <a :href="detail.url" target="_blank" rel="noopener">{{ detail.url }}</a>
            <button class="url-copy" type="button" title="复制链接" @click="copyUrl(detail.url)">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
            </button>
          </div>

          <div v-if="detail.note" class="detail-note">
            <span class="note-label">备注</span>
            <p>{{ detail.note }}</p>
          </div>

          <div v-if="orderedDetailImages.length" class="detail-imgs">
            <div v-for="(img, i) in orderedDetailImages" :key="i" class="detail-img-wrap" :class="{ cover: img === detail.cover_image }" @click="openLightbox(img, orderedDetailImages)">
              <img :src="imgUrl(img)" class="detail-img" alt="" />
              <span v-if="img === detail.cover_image" class="cover-badge">封面</span>
            </div>
          </div>

          <div v-if="detail.tags" class="detail-tags">
            <span v-for="t in splitTags(detail.tags)" :key="t" class="tag">#{{ t }}</span>
          </div>
        </div>
        <div class="modal-foot">
          <button class="btn ghost" @click="closeDetail">关闭</button>
          <button class="btn primary" v-if="detail.url" @click="openUrl(detail.url)">打开网站</button>
        </div>
      </div>
    </div>

    <!-- 图片裁剪弹窗 -->
    <div v-if="cropper.visible" class="modal-mask" @click.self="cancelCrop">
      <div class="modal">
        <div class="modal-head">
          <h2>{{ cropper.mode === 'cover' ? '裁剪为封面（16:9）' : '裁剪图片（16:9）' }}</h2>
          <button class="x" @click="cancelCrop">✕</button>
        </div>
        <div class="modal-body">
          <p class="crop-hint">拖动白色方框调整裁剪区域，拖拽四角调整大小，确认后按 16:9 保存。</p>
          <div class="crop-wrap" ref="cropWrapEl" @mousedown.prevent="cropStartDrag">
            <img :src="cropper.src" class="crop-img" ref="cropImgEl" @load="cropInitBox" alt="" />
            <div class="crop-box" :style="cropBoxStyle">
              <div class="crop-grid"></div>
              <span class="crop-handle tl" data-dir="tl"></span>
              <span class="crop-handle tr" data-dir="tr"></span>
              <span class="crop-handle bl" data-dir="bl"></span>
              <span class="crop-handle br" data-dir="br"></span>
            </div>
          </div>
          <div class="crop-preview-row">
            <span>预览：</span>
            <canvas ref="cropCanvasEl" width="160" height="90" style="width:160px;height:90px;"></canvas>
          </div>
        </div>
        <div class="modal-foot">
          <button class="btn ghost" @click="cancelCrop">取消</button>
          <button class="btn primary" :disabled="cropper.uploading" @click="confirmCrop">{{ cropper.uploading ? '上传中…' : '确认上传' }}</button>
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
import { ref, reactive, computed, onMounted } from 'vue'
import { api, apiUpload } from '../common/http.js'
import { confirm } from '../common/useConfirm.js'
import MediaLightbox from '../filespace/MediaLightbox.vue'

const list = ref([])
const meta = reactive({ categories: [], all_tags: [] })
const filters = reactive({ keyword: '', category: '全部', tag: '' })

const DEFAULT_CATEGORIES = ['AI', '漫剧', '工具', '文档', '素材', '其他']
const catOptions = computed(() => ['全部', ...(meta.categories.length ? meta.categories : DEFAULT_CATEGORIES)])
const formCatOptions = computed(() => meta.categories.length ? meta.categories : DEFAULT_CATEGORIES)
const customCategory = ref('')

const showEditor = ref(false)
const editing = reactive(blankForm())
const saving = ref(false)

const showDetail = ref(false)
const detail = ref({})

const toast = ref('')
let toastTimer = null
const imgInput = ref(null)
// 统一灯箱状态（复用默认 MediaLightbox 组件）
const lightboxVisible = ref(false)
const lightboxItems = ref([])
const lightboxIndex = ref(0)

const dragIndex = ref(-1)
const overIndex = ref(-1)

let loadTimer = null
function debouncedLoad() {
  clearTimeout(loadTimer)
  loadTimer = setTimeout(loadList, 250)
}

async function loadMeta(silent = false) {
  try {
    const m = await api('/web-nav/meta', 'GET')
    meta.categories = m.categories || []
    meta.all_tags = m.all_tags || []
  } catch (e) {
    if (!silent) showToast(e.message || '加载筛选维度失败')
  }
}

async function loadList() {
  const q = new URLSearchParams({
    category: filters.category,
    keyword: filters.keyword,
    tag: filters.tag,
  }).toString()
  try {
    const rows = await api(`/web-nav/list?${q}`, 'GET')
    list.value = rows.map(r => ({ ...r, images: parseImages(r.images) }))
  } catch (e) {
    showToast(e.message || '加载失败')
  }
}

function setCat(c) { filters.category = c; loadList() }

function blankForm() {
  customCategory.value = ''
  return { id: null, title: '', url: '', category: '漫剧', note: '', tags: '生图, 生视频, 每日领积分', images: [], cover_image: '' }
}

function openCreate() {
  Object.assign(editing, blankForm())
  showEditor.value = true
}
function openEdit(item) {
  const known = formCatOptions.value.includes(item.category)
  customCategory.value = known ? '' : (item.category || '')
  Object.assign(editing, {
    id: item.id, title: item.title, url: item.url || '',
    category: known ? item.category : '__custom__',
    note: item.note || '', tags: item.tags || '',
    images: parseImages(item.images), cover_image: item.cover_image || '',
  })
  showEditor.value = true
}
function closeEditor() { showEditor.value = false }

async function save() {
  if (!editing.title.trim()) { showToast('标题不能为空'); return }
  let cat = editing.category
  if (cat === '__custom__') {
    cat = customCategory.value.trim()
    if (!cat) { showToast('请输入自建分类名称'); return }
  }
  saving.value = true
  try {
    const payload = {
      title: editing.title, url: editing.url || '', category: cat,
      note: editing.note, tags: editing.tags,
    }
    if (editing.id) {
      await api(`/web-nav/${editing.id}`, 'PUT', payload)
    } else {
      await api('/web-nav/', 'POST', payload)
    }
    showEditor.value = false
    // 乐观同步标签，确保新建/编辑后立即出现在筛选下拉
    const tagSet = new Set(meta.all_tags)
    splitTags(editing.tags).forEach(t => tagSet.add(t))
    meta.all_tags = Array.from(tagSet).sort()
    await loadMeta()
    await loadList()
    showToast('已保存')
  } catch (e) {
    showToast(e.message || '保存失败')
  } finally {
    saving.value = false
  }
}

async function remove(item) {
  if (!(await confirm(`确定删除「${item.title}」？此操作不可撤销。`, { title: '删除确认' }))) return
  try {
    await api(`/web-nav/${item.id}`, 'DELETE')
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

async function copyUrl(url) {
  if (!url) return
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(url)
    } else {
      const ta = document.createElement('textarea')
      ta.value = url
      ta.style.position = 'fixed'
      ta.style.opacity = '0'
      document.body.appendChild(ta)
      ta.select()
      document.execCommand('copy')
      document.body.removeChild(ta)
    }
    showToast('链接已复制')
  } catch (e) {
    showToast('复制失败，请手动复制')
  }
}

function openDetail(item) {
  detail.value = item
  showDetail.value = true
}
function closeDetail() { showDetail.value = false }

function splitTags(s) {
  return (s || '').split(',').map(x => x.trim()).filter(Boolean)
}

const orderedDetailImages = computed(() => {
  const arr = detail.value?.images || []
  const cover = detail.value?.cover_image
  if (!cover || !arr.includes(cover)) return arr
  return [cover, ...arr.filter(x => x !== cover)]
})

function parseImages(v) {
  if (Array.isArray(v)) return v
  if (!v) return []
  try { const a = JSON.parse(v); return Array.isArray(a) ? a : [] } catch { return [] }
}
function coverOf(item) {
  return item?.cover_image || (item?.images && item.images[0]) || null
}
function titleInitial(title) {
  const s = (title || '').trim()
  if (!s) return '站'
  const c = s[0]
  // 取第一个能看的字符；如果标题是纯 URL/特殊符号，显示通用图标
  if (/[\u4e00-\u9fa5a-zA-Z0-9]/.test(c)) return c.toUpperCase()
  return '站'
}
const PLACEHOLDER_GRADIENTS = [
  ['#4f7cff', '#7b5cff'],
  ['#00c6a0', '#00a8e8'],
  ['#ff6b6b', '#ff8e53'],
  ['#7b5cff', '#e040fb'],
  ['#00b09b', '#96c93d'],
  ['#4f7cff', '#00c6a0'],
]
function placeholderStyle(title) {
  const hash = (title || '').split('').reduce((a, c) => a + c.charCodeAt(0), 0)
  const [a, b] = PLACEHOLDER_GRADIENTS[hash % PLACEHOLDER_GRADIENTS.length]
  return { background: `linear-gradient(135deg, ${a} 0%, ${b} 100%)` }
}
function imgUrl(rel) {
  return '/api/web-nav/asset/' + rel
}
function openLightbox(rel, all) {
  const arr = Array.isArray(all) ? all : [rel]
  lightboxItems.value = arr.map(x => ({ url: imgUrl(x) }))
  lightboxIndex.value = Math.max(0, arr.indexOf(rel))
  lightboxVisible.value = true
}
function closeLightbox() { lightboxVisible.value = false }

function onDragStart(idx, ev) {
  dragIndex.value = idx
  if (ev.dataTransfer) {
    ev.dataTransfer.effectAllowed = 'move'
    ev.dataTransfer.setData('text/plain', String(idx))
  }
}
function onDragOver(idx) {
  if (dragIndex.value !== -1 && dragIndex.value !== idx) overIndex.value = idx
}
function onDragLeave(idx) {
  if (overIndex.value === idx) overIndex.value = -1
}
function onDragEnd() {
  dragIndex.value = -1
  overIndex.value = -1
}
async function onDrop(idx) {
  const from = dragIndex.value
  dragIndex.value = -1
  overIndex.value = -1
  if (from < 0 || from === idx) return
  const arr = list.value
  if (from >= arr.length || idx >= arr.length) return
  const moved = arr.splice(from, 1)[0]
  arr.splice(idx, 0, moved)
  await reorder()
}
async function reorder() {
  try {
    const ids = list.value.map(i => i.id)
    await api('/web-nav/reorder', 'POST', { ids })
    showToast('排序已保存')
  } catch (e) {
    showToast(e.message || '排序保存失败')
    await loadList()
  }
}

async function onImgPicked(e) {
  const files = Array.from(e.target.files || []).filter(f => f.type.startsWith('image/'))
  if (!files.length) {
    showToast('请选择图片文件')
    e.target.value = ''
    return
  }
  if (!editing.id) return
  const fd = new FormData()
  for (const f of files) fd.append('files', f)
  try {
    const updated = await apiUpload(`/web-nav/${editing.id}/images`, fd)
    editing.images = parseImages(updated.images)
    editing.cover_image = updated.cover_image || ''
    await loadList()
    showToast(`已上传 ${files.length} 张图片`)
  } catch (err) {
    showToast(err.message || '上传失败')
  }
  e.target.value = ''
}

async function cropCoverFrom(rel) {
  // 从已有图片裁剪封面
  if (!editing.id) return
  cropper.mode = 'cover'
  cropper.targetRel = rel
  cropper.src = imgUrl(rel) + '?t=' + Date.now()
  cropper.file = null
  cropper.visible = true
}

async function removeImage(rel) {
  if (!editing.id) return
  const fn = rel.split('/').pop()
  try {
    const updated = await api(`/web-nav/${editing.id}/images/${encodeURIComponent(fn)}`, 'DELETE')
    editing.images = parseImages(updated.images)
    editing.cover_image = updated.cover_image || ''
    await loadList()
    showToast('已删除图片')
  } catch (err) {
    showToast(err.message || '删除失败')
  }
}

async function setCover(rel) {
  if (!editing.id) return
  try {
    const updated = await api(`/web-nav/${editing.id}/cover`, 'PUT', { cover_image: rel })
    editing.cover_image = updated.cover_image || ''
    await loadList()
    showToast('已设为封面')
  } catch (err) {
    showToast(err.message || '设置封面失败')
  }
}

// ===== 图片裁剪（16:9）=====
const cropper = reactive({
  visible: false,
  src: '',
  file: null,
  mode: 'upload',   // 'upload' | 'cover'
  targetRel: '',    // cover 模式时对应的原图 rel
  uploading: false,
})
const cropBox = reactive({ x: 0, y: 0, w: 240, h: 135 })
const cropImgNatural = reactive({ w: 0, h: 0 })
const cropDrag = ref(null)
const cropWrapEl = ref(null)
const cropImgEl = ref(null)
const cropCanvasEl = ref(null)
const CROP_RATIO = 16 / 9

const cropBoxStyle = computed(() => ({
  left: cropBox.x + 'px',
  top: cropBox.y + 'px',
  width: cropBox.w + 'px',
  height: cropBox.h + 'px',
}))

function cropInitBox() {
  const img = cropImgEl.value
  if (!img) return
  const dw = img.clientWidth
  const dh = img.clientHeight
  let h = dh * 0.8
  let w = h * CROP_RATIO
  if (w > dw) {
    w = dw * 0.8
    h = w / CROP_RATIO
  }
  cropBox.x = (dw - w) / 2
  cropBox.y = (dh - h) / 2
  cropBox.w = w
  cropBox.h = h
  cropImgNatural.w = img.naturalWidth
  cropImgNatural.h = img.naturalHeight
  cropDrawPreview()
}

function cropGetScale() {
  const img = cropImgEl.value
  if (!img || !img.clientWidth) return 1
  return img.naturalWidth / img.clientWidth
}

function cropStartDrag(ev) {
  const boxEl = ev.target.closest('.crop-box')
  const handleEl = ev.target.closest('.crop-handle')
  if (!boxEl && !handleEl) return
  cropDrag.value = {
    type: handleEl ? 'resize' : 'move',
    dir: handleEl ? handleEl.dataset.dir : null,
    startX: ev.clientX,
    startY: ev.clientY,
    startBox: { x: cropBox.x, y: cropBox.y, w: cropBox.w, h: cropBox.h },
  }
  document.addEventListener('mousemove', cropOnMove)
  document.addEventListener('mouseup', cropEndDrag)
}

function cropOnMove(ev) {
  const d = cropDrag.value
  if (!d) return
  const dx = ev.clientX - d.startX
  const dy = ev.clientY - d.startY
  const img = cropImgEl.value
  if (!img) return
  const iw = img.clientWidth
  const ih = img.clientHeight
  const minSize = 60
  let b = { ...d.startBox }

  if (d.type === 'move') {
    b.x = clamp(d.startBox.x + dx, 0, iw - b.w)
    b.y = clamp(d.startBox.y + dy, 0, ih - b.h)
  } else {
    let nw = d.startBox.w
    if (d.dir.includes('r')) nw = Math.max(minSize, d.startBox.w + dx)
    else if (d.dir.includes('l')) nw = Math.max(minSize, d.startBox.w - dx)

    nw = clamp(nw, minSize, iw)
    let nh = nw / CROP_RATIO
    if (nh > ih) {
      nh = ih
      nw = nh * CROP_RATIO
    }

    let nx = d.startBox.x
    let ny = d.startBox.y
    if (d.dir.includes('l')) nx = d.startBox.x + d.startBox.w - nw
    if (d.dir.includes('t')) ny = d.startBox.y + d.startBox.h - nh

    b.x = clamp(nx, 0, iw - nw)
    b.y = clamp(ny, 0, ih - nh)
    b.w = nw
    b.h = nh
  }
  cropBox.x = b.x
  cropBox.y = b.y
  cropBox.w = b.w
  cropBox.h = b.h
  cropDrawPreview()
}

function cropEndDrag() {
  cropDrag.value = null
  document.removeEventListener('mousemove', cropOnMove)
  document.removeEventListener('mouseup', cropEndDrag)
}

function cropDrawPreview() {
  const canvas = cropCanvasEl.value
  const img = cropImgEl.value
  if (!canvas || !img || !img.naturalWidth) return
  const scale = cropGetScale()
  const b = cropBox
  const ctx = canvas.getContext('2d')
  canvas.width = 320
  canvas.height = 180
  ctx.drawImage(
    img,
    b.x * scale, b.y * scale, b.w * scale, b.h * scale,
    0, 0, 320, 180
  )
}

function clamp(v, lo, hi) {
  return Math.max(lo, Math.min(hi, v))
}

function cancelCrop() {
  cropper.visible = false
  cropper.src = ''
  cropper.file = null
  cropper.mode = 'upload'
  cropper.targetRel = ''
  cropDrag.value = null
}

async function confirmCrop() {
  if (!editing.id) return
  const canvas = document.createElement('canvas')
  const img = cropImgEl.value
  if (!img) return
  const scale = cropGetScale()
  const b = cropBox
  const outW = Math.max(640, Math.round(b.w * scale))
  const outH = Math.round(outW / CROP_RATIO)
  canvas.width = outW
  canvas.height = outH
  const ctx = canvas.getContext('2d')
  ctx.drawImage(
    img,
    b.x * scale, b.y * scale, b.w * scale, b.h * scale,
    0, 0, outW, outH
  )
  cropper.uploading = true
  try {
    const blob = await new Promise(r => canvas.toBlob(r, 'image/jpeg', 0.9))
    if (cropper.mode === 'cover') {
      const fd = new FormData()
      fd.append('file', blob, 'cover.jpg')
      const updated = await apiUpload(`/web-nav/${editing.id}/cover-crop`, fd)
      editing.cover_image = updated.cover_image || ''
      await loadList()
      showToast('封面已更新')
    } else {
      const fd = new FormData()
      fd.append('files', blob, 'cropped.jpg')
      const updated = await apiUpload(`/web-nav/${editing.id}/images`, fd)
      editing.images = parseImages(updated.images)
      editing.cover_image = updated.cover_image || editing.cover_image
      await loadList()
      showToast('图片已上传')
    }
    cancelCrop()
  } catch (err) {
    showToast(err.message || (cropper.mode === 'cover' ? '封面更新失败' : '上传失败'))
  } finally {
    cropper.uploading = false
  }
}

function showToast(msg) {
  toast.value = msg
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => { toast.value = '' }, 2000)
}

onMounted(async () => {
  await loadMeta()
  await loadList()
})
</script>

<style scoped>
.wn-page {
  width: 100%;
  font-family: system-ui, -apple-system, "Segoe UI", Roboto, "PingFang SC", "Microsoft YaHei", sans-serif;
  color: var(--sx-text-strong);
}
.wn-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 18px;
}
.wn-title { display: flex; align-items: center; gap: 12px; color: var(--sx-accent); }
.wn-title h1 { font-size: 22px; margin: 0; color: var(--sx-text-strong); }
.wn-sub { margin: 2px 0 0; font-size: 12.5px; color: var(--sx-text-muted); }
.wn-actions { display: flex; gap: 10px; }

.btn {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 9px 16px; border-radius: 10px; font-size: 14px; font-weight: 600;
  cursor: pointer; border: 1px solid transparent; transition: .15s;
}
.btn.primary { background: var(--sx-btn-primary-bg); color: #fff; box-shadow: var(--sx-btn-primary-shadow); }
.btn.primary:hover { filter: brightness(1.05); }
.btn.primary:disabled { opacity: .6; cursor: default; }
.btn.ghost { background: var(--sx-bg-surface); border-color: var(--sx-border); color: var(--sx-text); }
.btn.ghost:hover { background: var(--sx-bg-surface-2); }
.btn.sm { padding: 7px 12px; font-size: 13px; }

.wn-filters {
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
.chip:hover { border-color: var(--sx-border-hover); color: var(--sx-accent); }
.chip.on { background: var(--sx-accent); border-color: var(--sx-accent); color: #fff; }
.mini-select { padding: 7px 10px; border-radius: 9px; border: 1px solid var(--sx-border); background: var(--sx-bg-surface); font-size: 13px; color: var(--sx-text); cursor: pointer; }
.count { margin-left: auto; font-size: 12.5px; color: var(--sx-text-muted); }

.wn-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(186px, 1fr)); gap: 12px; }
.wn-card {
  background: var(--sx-bg-surface); border: 1px solid var(--sx-border); border-radius: 12px; padding: 10px;
  cursor: pointer; transition: .15s; display: flex; flex-direction: column; gap: 6px;
  box-shadow: var(--sx-shadow-card);
}
.wn-card:hover { border-color: var(--sx-border-hover); box-shadow: var(--sx-card-hover-shadow); transform: translateY(-2px); }
.wn-card[draggable="true"] { cursor: grab; }
.wn-card.dragging { opacity: .4; }
.wn-card.dragging:hover { transform: none; }
.wn-card.dragover { border-color: var(--sx-accent); box-shadow: var(--sx-card-dragover-ring); }
.card-top { display: flex; align-items: center; gap: 6px; }
.card-title { font-size: 13.5px; margin: 0; color: var(--sx-text-strong); font-weight: 700; line-height: 1.3; flex: 1; }
.card-badges { display: flex; gap: 5px; flex-wrap: wrap; }
.badge { font-size: 10.5px; padding: 2px 7px; border-radius: 6px; font-weight: 600; }
.badge.cat { background: var(--sx-tag-info-bg); color: var(--sx-tag-info-text); }
.badge.note { background: var(--sx-tag-warn-bg); color: var(--sx-tag-warn-text); }
.card-tags { display: flex; gap: 5px; flex-wrap: wrap; }
.tag { font-size: 10.5px; color: var(--sx-text); background: var(--sx-bg-surface-2); padding: 2px 6px; border-radius: 5px; }
.card-ops { display: flex; gap: 4px; margin-top: auto; padding-top: 3px; }
.op {
  display: inline-flex; align-items: center; justify-content: center;
  flex: 1; padding: 4px 2px; border-radius: 6px; border: 1px solid var(--sx-border); background: var(--sx-bg-surface);
  color: var(--sx-text); font-size: 10.5px; cursor: pointer; transition: .15s; min-width: 0;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.op:hover { background: var(--sx-bg-surface-2); color: var(--sx-accent); border-color: var(--sx-border-hover); }
.op.danger:hover { background: var(--sx-btn-danger-bg); color: var(--sx-btn-danger-text); border-color: var(--sx-btn-danger-border); }

.empty { text-align: center; color: var(--sx-text-muted); padding: 60px 20px; }
.empty svg { color: var(--sx-text-faint); margin-bottom: 12px; }
.empty p { font-size: 14px; max-width: 420px; margin: 0 auto; line-height: 1.6; }

.modal-mask { position: fixed; inset: 0; background: var(--sx-overlay); display: flex; align-items: center; justify-content: center; z-index: 50; padding: 20px; }
.modal { background: var(--sx-bg-surface); border-radius: 16px; width: 100%; max-width: 900px; max-height: 90vh; display: flex; flex-direction: column; box-shadow: var(--sx-shadow-pop); }
.modal-head { display: flex; align-items: center; justify-content: space-between; padding: 18px 22px; border-bottom: 1px solid var(--sx-border); }
.modal-head h2 { margin: 0; font-size: 17px; color: var(--sx-text-strong); }
.x { border: 0; background: transparent; font-size: 18px; color: var(--sx-text-muted); cursor: pointer; line-height: 1; }
.x:hover { color: var(--sx-btn-danger-text); }
.modal-body { padding: 20px 22px; overflow-y: auto; }
.modal-foot { display: flex; justify-content: flex-end; gap: 10px; padding: 14px 22px; border-top: 1px solid var(--sx-border); }

.fld { display: flex; flex-direction: column; gap: 6px; margin-bottom: 14px; }
.fld > span { font-size: 12.5px; color: var(--sx-text); font-weight: 600; }
.fld input, .fld select, .fld textarea {
  border: 1px solid var(--sx-border-input); border-radius: 9px; padding: 10px 12px; font-size: 14px;
  color: var(--sx-text-strong); font-family: inherit; outline: none; transition: .15s; background: var(--sx-bg-surface);
}
.fld input:focus, .fld select:focus, .fld textarea:focus { border-color: var(--sx-accent-hover); box-shadow: 0 0 0 3px var(--sx-accent-soft); }
.fld textarea { resize: vertical; line-height: 1.6; }
.fld-row { display: flex; gap: 14px; }
.fld-row .fld { flex: 1; }

.detail-badges { display: flex; gap: 7px; flex-wrap: wrap; margin-bottom: 12px; }
.detail-url { display: flex; align-items: center; gap: 6px; font-size: 13px; color: var(--sx-link); margin-bottom: 14px; word-break: break-all; }
.url-copy { margin-left: auto; flex-shrink: 0; border: 0; background: transparent; color: var(--sx-link); cursor: pointer; padding: 5px; border-radius: 6px; display: inline-flex; align-items: center; transition: .15s; }
.url-copy:hover { background: var(--sx-tag-info-bg); }
.detail-url a { color: var(--sx-link); text-decoration: none; }
.detail-url a:hover { text-decoration: underline; }
.detail-note { margin: 12px 0 14px; }
.detail-note .note-label { display: inline-block; font-size: 11px; font-weight: 600; color: var(--sx-text-muted); margin-bottom: 6px; }
.detail-note p { margin: 0; font-size: 13.5px; color: var(--sx-text); line-height: 1.7; white-space: pre-wrap; word-break: break-word; background: var(--sx-bg-surface-2); border-radius: 10px; padding: 12px 14px; }
.detail-tags { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 12px; }

.toast {
  position: fixed; left: 50%; bottom: 40px; transform: translateX(-50%);
  background: var(--sx-toast-dark-bg); color: var(--sx-toast-text); padding: 11px 22px; border-radius: 10px; font-size: 14px;
  box-shadow: var(--sx-shadow-pop); z-index: 80;
}
.fade-enter-active, .fade-leave-active { transition: opacity .25s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

.card-cover { position: relative; margin-bottom: 6px; border-radius: 8px; overflow: hidden; aspect-ratio: 16 / 9; background: var(--sx-bg-surface-2); }
.card-cover img { width: 100%; height: 100%; object-fit: cover; cursor: zoom-in; }
.card-cover.placeholder { background: var(--sx-bg-surface-2); cursor: default; }
.cover-placeholder { width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; color: #fff; font-size: 34px; font-weight: 700; text-shadow: 0 2px 8px rgba(0,0,0,.15); user-select: none; }

.detail-imgs { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 14px; }
.detail-img-wrap { position: relative; width: 240px; height: 135px; border-radius: 10px; overflow: hidden; cursor: zoom-in; border: 1px solid var(--sx-border); background: var(--sx-bg-surface-2); }
.detail-img-wrap.cover { border-color: #ffb020; box-shadow: 0 0 0 2px rgba(255,176,32,.25); }
.detail-img { width: 100%; height: 100%; object-fit: cover; display: block; }
.cover-badge { position: absolute; top: 4px; left: 4px; background: rgba(255,176,32,.92); color: #fff; font-size: 11px; padding: 1px 6px; border-radius: 4px; font-weight: 600; }

.img-grid { display: flex; gap: 14px; flex-wrap: wrap; margin-bottom: 10px; }
.img-cell { position: relative; width: 100px; height: 100px; border-radius: 10px; overflow: hidden; border: 1px solid var(--sx-border); background: var(--sx-bg-surface-2); }
.img-cell img { width: 100%; height: 100%; object-fit: cover; cursor: zoom-in; }
.img-cell.cover { border-color: #ffb020; box-shadow: 0 0 0 2px rgba(255,176,32,.25); }
.img-tools { position: absolute; left: 0; right: 0; bottom: 0; height: 24px; display: flex; align-items: center; justify-content: space-between; padding: 0 6px; background: rgba(20,22,40,.68) !important; backdrop-filter: blur(2px); }
.img-tool { appearance: none; -webkit-appearance: none; display: inline-flex; align-items: center; justify-content: center; gap: 4px; border: 0; background: transparent !important; color: #fff; cursor: pointer; padding: 0; font-size: 12px; line-height: 24px; opacity: .95; transition: .15s; white-space: nowrap; flex-shrink: 0; overflow: visible; }
.img-tool:hover { opacity: 1; }
.img-tool.cover { flex: 1; min-width: 0; border-right: 1px solid rgba(255,255,255,.22); }
.img-tool.cover:hover { color: #ffd36e; }
.img-tool.del { flex: 1; min-width: 0; font-size: 16px; }
.img-tool.del:hover { color: #ff9a9a; }
.img-tool svg { width: 13px; height: 13px; flex-shrink: 0; }
.img-tool span { font-size: 12px; white-space: nowrap; }
.img-upload { display: flex; gap: 8px; align-items: center; }
.img-hint { font-size: 12.5px; color: var(--sx-text-muted); margin: -4px 0 14px; }

.img-hint-inline { font-size: 12px; color: var(--sx-text-muted); }

.crop-hint { font-size: 12.5px; color: var(--sx-text); margin: -4px 0 12px; }
.crop-wrap {
  position: relative; width: 100%; max-height: 420px;
  overflow: hidden; background: var(--sx-crop-bg); border-radius: 10px;
  cursor: crosshair; user-select: none; touch-action: none;
}
.crop-img { display: block; max-width: 100%; max-height: 400px; margin: auto; }
.crop-box {
  position: absolute; border: 2px solid #fff;
  box-shadow: 0 0 0 9999px rgba(0, 0, 0, .55);
  cursor: move; z-index: 2;
}
.crop-grid {
  position: absolute; inset: 0;
  background:
    linear-gradient(rgba(255,255,255,.15) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,.15) 1px, transparent 1px);
  background-size: 33.33% 33.33%; pointer-events: none;
}
.crop-handle {
  position: absolute; width: 12px; height: 12px;
  background: #fff; border: 2px solid var(--sx-accent); border-radius: 2px; z-index: 3;
}
.crop-handle.tl { top: -6px; left: -6px; cursor: nw-resize; }
.crop-handle.tr { top: -6px; right: -6px; cursor: ne-resize; }
.crop-handle.bl { bottom: -6px; left: -6px; cursor: sw-resize; }
.crop-handle.br { bottom: -6px; right: -6px; cursor: se-resize; }
.crop-preview-row { display: flex; gap: 12px; align-items: center; margin-top: 14px; }
.crop-preview-row span { font-size: 12px; color: var(--sx-text); font-weight: 600; }

@media (max-width: 640px) {
  .wn-head { flex-direction: column; align-items: stretch; }
  .wn-actions { flex-direction: column; }
  .fld-row { flex-direction: column; gap: 0; }
  .wn-grid { grid-template-columns: 1fr; }
}
</style>
