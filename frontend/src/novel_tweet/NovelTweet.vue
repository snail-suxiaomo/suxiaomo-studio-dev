<template>
  <div class="nt-page">
    <div class="nt-home-header">
      <!-- 顶部标题栏 -->
      <header class="nt-head">
        <div class="nt-title">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
            <line x1="8" y1="9" x2="16" y2="9" />
            <line x1="8" y1="13" x2="13" y2="13" />
          </svg>
          <div>
            <h1>推文助手</h1>
            <p class="nt-sub">以推文关键词为基准，管理推广与第三方平台回填</p>
          </div>
        </div>
        <div class="nt-actions">
          <button class="btn primary" @click="openCreate">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="M12 5v14M5 12h14" /></svg>
            新建推广
          </button>
        </div>
      </header>

      <!-- 筛选栏 -->
      <section class="nt-filters">
        <div class="search-wrap">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/></svg>
          <input v-model="filters.keyword" class="search" type="text" placeholder="搜索推文名称 / 原小说 / 链接 / 文案…" @input="debouncedLoad" />
        </div>

        <div class="filter-row">
          <span class="filter-label">小说平台</span>
          <div class="chips">
            <button v-for="c in catOptions" :key="c" :class="['chip', { on: filters.category === c }]" @click="setCat(c)">{{ c }}</button>
          </div>
        </div>

        <div class="filter-row inline">
          <span class="count">共 {{ list.length }} 条推广</span>
        </div>
      </section>
    </div>

    <div class="nt-home-body">
      <!-- 卡片列表 -->
      <section v-if="list.length" class="nt-grid">
      <article
        v-for="(item, idx) in list"
        :key="item.id"
        class="nt-card"
        :class="{ dragging: dragIndex === idx, dragover: overIndex === idx }"
        draggable="true"
        @dragstart="onDragStart(idx, $event)"
        @dragover.prevent="onDragOver(idx)"
        @dragleave="onDragLeave(idx)"
        @drop.prevent="onDrop(idx)"
        @dragend="onDragEnd"
        @click="openDetail(item)"
      >
        <div class="card-top">
          <h3 class="card-title">{{ item.name }}</h3>
        </div>
        <div class="card-badges">
          <span class="badge cat">{{ item.novel_platform }}</span>
          <span class="badge type" :class="item.platform_type">{{ platformTypeLabel(item.platform_type) }}</span>
          <span :class="['badge', item.platform_names ? 'cnt' : 'no']" :title="formatPlatformNames(item)">{{ item.platform_names ? formatPlatformNames(item) : '未选择平台' }}</span>
          <span :class="['tag', backfillTag(item).cls]">{{ backfillTag(item).text }}</span>
        </div>
        <div class="card-info">
          <div class="info-row novel-row" v-if="item.original_novel_name">
            <span class="info-label">📖 原小说</span>
            <span class="novel-name-val">{{ item.original_novel_name }}</span>
          </div>
          <div class="info-row account-row" :class="{ muted: !formatPublishAccounts(item) }">
            <span class="info-label">发布账号</span>
            <span class="info-value account-chips" v-if="selectedAccounts(item).length">
              <span v-for="a in selectedAccounts(item)" :key="a" :class="['acc-chip', 'acc-' + ACCOUNT_META[a].key]">{{ a }}</span>
            </span>
            <span class="info-value" v-else>未选择账号</span>
          </div>
        </div>
        <div class="card-ops" @click.stop>
          <button class="op copy" title="复制为模板" @click="copyCard(item)">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
            复制模板
          </button>
          <button class="op edit" title="编辑" @click="openEdit(item)">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
            编辑
          </button>
          <button class="op delete" title="删除" @click="remove(item)">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
            删除
          </button>
        </div>
      </article>
    </section>

    <div v-else class="empty">
      <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" /><line x1="8" y1="9" x2="16" y2="9" /><line x1="8" y1="13" x2="13" y2="13" /></svg>
      <p>还没有推广记录，点右上角「新建推广」开始搭建你的推文矩阵。</p>
    </div>
    </div>

    <!-- 编辑/新建弹窗 -->
    <div v-if="showEditor" class="modal-mask" @click.self="closeEditor">
      <div class="modal">
        <div class="modal-head">
          <h2>{{ editing.id ? '编辑推广' : '新建推广' }}</h2>
          <button class="x" @click="closeEditor">✕</button>
        </div>
        <div class="modal-body">
          <!-- 推文信息 -->
          <div class="section-label">推文信息</div>
          <div class="fld">
            <span>推文名称（关键词）*</span>
            <input v-model="editing.name" type="text" placeholder="如：错嫁的小萤" />
          </div>
          <div class="fld-row">
            <div class="fld">
              <span>小说平台</span>
              <select v-model="editing.novel_platform" class="category-select">
                <option v-for="c in formCatOptions" :key="c" :value="c">{{ c }}</option>
                <option value="__custom__">+ 自建平台</option>
              </select>
              <input v-if="editing.novel_platform === '__custom__'" v-model="customCategory" type="text" placeholder="输入平台名" />
            </div>
            <div class="fld">
              <span>版本类型</span>
              <div class="seg">
                <button type="button" :class="['seg-btn', { on: editing.platform_type === 'web' }]" @click="editing.platform_type = 'web'">网页</button>
                <button type="button" :class="['seg-btn', { on: editing.platform_type === 'app' }]" @click="editing.platform_type = 'app'">APP</button>
                <button type="button" :class="['seg-btn', { on: editing.platform_type === 'mini_program' }]" @click="editing.platform_type = 'mini_program'">小程序</button>
              </div>
            </div>
          </div>
          <div class="fld">
            <span>原小说名称</span>
            <input v-model="editing.original_novel_name" type="text" placeholder="如：剑来" />
          </div>
          <div class="fld">
            <span>原小说推广链接</span>
            <input v-model="editing.original_promotion_link" type="text" placeholder="https://…" />
          </div>
          <div class="fld">
            <span>原小说推广文案</span>
            <textarea v-model="editing.original_promotion_copy" rows="6" placeholder="粘贴原小说推广文案…"></textarea>
          </div>
          <div class="fld">
            <span>推广文案优化</span>
            <textarea v-model="editing.optimized_copy" rows="6" placeholder="优化后的文案 / 其他补充…"></textarea>
          </div>

          <!-- 分隔线：第三方平台 -->
          <div class="divider"><span>第三方推广平台</span></div>

          <div v-for="(p, pi) in editing.platforms" :key="pi" class="pf-card" :class="{ 'pf-open': p._open !== false }">
            <div class="pf-head" @click="p._open = !(p._open !== false)">
              <span class="pf-idx">{{ pi + 1 }}</span>
              <span class="pf-name">{{ p.platform_name || '未命名平台' }}</span>
              <span class="pf-toggle">{{ p._open !== false ? '收起' : '展开' }}</span>
            </div>
            <div v-if="p._open !== false" class="pf-body">
              <div class="fld">
                <span>平台名称</span>
                <input v-model="p.platform_name" type="text" placeholder="如：清风助手" />
              </div>
              <div class="fld">
                <span>申请日期</span>
                <input v-model="p.application_date" type="date" />
              </div>
              <div class="fld">
                <span>发布账号 <small class="hint">可多选</small></span>
                <div class="chips sm">
                  <button type="button" v-for="a in ACCOUNTS" :key="a" :class="['chip', { on: hasAccount(p, a) }]" @click="toggleAccount(p, a)">{{ a }}</button>
                </div>
              </div>
              <div v-for="(a, aIdx) in selectedAccounts(p)" :key="a" class="account-card">
                <div class="account-head">
                  <span class="acc-title"><b class="acc-idx">{{ aIdx + 1 }}</b>{{ a }}账号</span>
                  <label class="backfill-check">
                    <input type="checkbox" v-model="p[accountFields(ACCOUNT_META[a].key).backfill]" />
                    <span>已发布回填</span>
                  </label>
                </div>
                <div class="fld-row">
                  <div class="fld"><span>名称</span><input v-model="p[accountFields(ACCOUNT_META[a].key).name]" type="text" placeholder="账号名称" /></div>
                  <div class="fld"><span>作品发布日期</span><input v-model="p[accountFields(ACCOUNT_META[a].key).publish_date]" type="date" /></div>
                </div>
                <div class="fld-row">
                  <div class="fld"><span>ID</span><input v-model="p[accountFields(ACCOUNT_META[a].key).id]" type="text" placeholder="账号ID" /></div>
                  <div class="fld"><span>作品链接</span><input v-model="p[accountFields(ACCOUNT_META[a].key).link]" type="text" placeholder="https://…" /></div>
                </div>
                <div class="fld-row">
                  <div class="fld"><span>收益</span><input v-model="p[accountFields(ACCOUNT_META[a].key).earnings]" type="text" placeholder="如：¥1234.5" /></div>
                  <div class="fld"><span>备注</span><input v-model="p[accountFields(ACCOUNT_META[a].key).remark]" type="text" placeholder="备注" /></div>
                </div>
              </div>
              <button class="btn ghost danger sm mt" type="button" @click="removePlatform(pi)">删除该平台</button>
            </div>
          </div>

          <button class="btn ghost block" type="button" @click="addPlatform">+ 添加第三方平台</button>
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
          <h2>{{ detail.name }}</h2>
          <button class="x" @click="closeDetail" title="关闭">✕</button>
        </div>
        <div class="modal-body">
          <div class="detail-badges">
            <span class="badge cat">{{ detail.novel_platform }}</span>
            <span class="badge type" :class="detail.platform_type">{{ platformTypeLabel(detail.platform_type) }}</span>
          </div>

          <div class="section-label">推文信息</div>
          <dl class="kv">
            <dt>原小说名称</dt><dd>{{ detail.original_novel_name || '—' }}</dd>
            <template v-if="detail.original_promotion_link">
              <dt>原小说推广链接</dt>
              <dd>
                <div class="link-row">
                  <a class="link-url" :href="detail.original_promotion_link" target="_blank" rel="noopener">{{ detail.original_promotion_link }}</a>
                </div>
                <button class="text-copy" type="button" @click="copyUrl(detail.original_promotion_link)">复制链接</button>
              </dd>
            </template>
            <template v-if="detail.original_promotion_copy">
              <dt>原小说推广文案</dt>
              <dd>
                <div class="copy-block">
                  <div class="pre collapsed">{{ detail.original_promotion_copy }}</div>
                  <button class="text-copy" type="button" @click="copyText(detail.original_promotion_copy, '文案已复制')">复制全文</button>
                </div>
              </dd>
            </template>
            <template v-if="detail.optimized_copy">
              <dt>推广文案优化</dt>
              <dd>
                <div class="copy-block">
                  <div class="pre collapsed">{{ detail.optimized_copy }}</div>
                  <button class="text-copy" type="button" @click="copyText(detail.optimized_copy, '文案已复制')">复制全文</button>
                </div>
              </dd>
            </template>
          </dl>

          <div class="divider"><span>第三方推广平台（{{ (detail.platforms || []).length }}）</span></div>

          <div v-if="detail.platforms && detail.platforms.length" class="pf-list">
            <div v-for="(p, pi) in detail.platforms" :key="pi" class="pf-detail">
              <div class="pf-detail-head">
                <span class="pf-idx">{{ pi + 1 }}</span>
                <strong>{{ p.platform_name || '未命名平台' }}</strong>
              </div>
              <dl class="kv sm">
                <template v-if="p.application_date"><dt>申请日期</dt><dd>{{ p.application_date }}</dd></template>
                <template v-if="p.deadline_earnings"><dt>截止收益</dt><dd>{{ p.deadline_earnings }}</dd></template>
              </dl>
              <div v-if="p.publish_accounts && selectedAccounts(p).length" class="account-sections">
                <div v-for="(a, aIdx) in selectedAccounts(p)" :key="a" class="account-section">
                  <div class="account-section-head">
                    <strong><b class="acc-idx">{{ aIdx + 1 }}</b>{{ a }}账号</strong>
                    <span :class="['tag', accountBackfill(p, a) ? 'ok' : 'no']">{{ accountBackfill(p, a) ? '已回填' : '未回填' }}</span>
                  </div>
                  <dl class="kv sm">
                    <template v-for="row in accountDetailRows(p, a)" :key="row.label">
                      <dt>{{ row.label }}</dt>
                      <dd v-if="row.isLink" class="link">
                        <a :href="row.value" target="_blank" rel="noopener">{{ row.value }}</a>
                        <button class="url-copy" type="button" title="复制" @click="copyUrl(row.value)">
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
                        </button>
                      </dd>
                      <dd v-else>{{ row.value }}</dd>
                    </template>
                  </dl>
                </div>
              </div>
              <!-- 兼容旧数据 -->
              <dl v-if="p.publish_work_link" class="kv sm">
                <dt>发布作品</dt>
                <dd class="link">
                  <a :href="p.publish_work_link" target="_blank" rel="noopener">{{ p.publish_work_link }}</a>
                  <button class="url-copy" type="button" title="复制" @click="copyUrl(p.publish_work_link)">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
                  </button>
                </dd>
              </dl>
            </div>
          </div>
          <p v-else class="muted">暂无第三方平台。</p>
        </div>
      </div>
    </div>

    <!-- 轻提示 -->
    <transition name="fade">
      <div v-if="toast" class="toast">{{ toast }}</div>
    </transition>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { api } from '../common/http.js'
import { confirm } from '../common/useConfirm.js'

const ACCOUNTS = ['抖音', '快手', 'B站', '视频号', '其他平台']
const PLATFORM_TYPE_LABEL = { web: '网页', app: 'APP', mini_program: '小程序' }
function platformTypeLabel(t) { return PLATFORM_TYPE_LABEL[t] || '网页' }

// 草稿缓存已移除（用卡片「复制」功能替代）

const list = ref([])
const meta = reactive({ categories: [] })
const filters = reactive({ keyword: '', category: '全部' })

// 兜底分类：仅 onMounted 拉取 /meta 之前或失败时使用。
// 正式分类一律以后端 /novel-tweet/meta 返回为准（service.py DEFAULT_PLATFORMS + 用户自建），
// 改默认分类请在后端 service.py 的 DEFAULT_PLATFORMS 增删，保持此处兜底同步即可。
const FALLBACK_CATEGORIES = ['番茄', '知乎', '七猫', '盐言', '书旗', 'QQ阅读', '起点', '其他']
const catOptions = computed(() => ['全部', ...(meta.categories.length ? meta.categories : FALLBACK_CATEGORIES)])
const formCatOptions = computed(() => meta.categories.length ? meta.categories : FALLBACK_CATEGORIES)
const customCategory = ref('')

const showEditor = ref(false)
const editing = reactive(blankForm())
const saving = ref(false)

const showDetail = ref(false)
const detail = ref({})

const toast = ref('')
let toastTimer = null

const dragIndex = ref(-1)
const overIndex = ref(-1)

let loadTimer = null
function debouncedLoad() {
  clearTimeout(loadTimer)
  loadTimer = setTimeout(loadList, 250)
}

async function loadMeta() {
  try {
    const m = await api('/novel-tweet/meta', 'GET')
    meta.categories = m.categories || []
  } catch (e) {
    showToast(e.message || '加载筛选维度失败')
  }
}

async function loadList() {
  const q = new URLSearchParams({
    category: filters.category,
    keyword: filters.keyword,
  }).toString()
  try {
    const rows = await api(`/novel-tweet/list?${q}`, 'GET')
    list.value = rows
  } catch (e) {
    showToast(e.message || '加载失败')
  }
}

function setCat(c) { filters.category = c; loadList() }

function blankPlatform() {
  return {
    id: null, platform_name: '', application_date: '', publish_date: '', is_published_backfill: false,
    publish_accounts: '',
    // 抖音账号 5 项
    douyin_name: '', douyin_account_id: '', douyin_publish_date: '', douyin_link: '', douyin_earnings: '', douyin_remark: '', douyin_is_published_backfill: false,
    // B站账号 6 项
    bilibili_name: '', bilibili_id: '', bilibili_publish_date: '', bilibili_link: '', bilibili_earnings: '', bilibili_remark: '', bilibili_is_published_backfill: false,
    // 快手账号 6 项
    kuaishou_name: '', kuaishou_id: '', kuaishou_publish_date: '', kuaishou_link: '', kuaishou_earnings: '', kuaishou_remark: '', kuaishou_is_published_backfill: false,
    // 视频号账号 6 项
    shipinhao_name: '', shipinhao_id: '', shipinhao_publish_date: '', shipinhao_link: '', shipinhao_earnings: '', shipinhao_remark: '', shipinhao_is_published_backfill: false,
    // 其他平台账号 6 项
    other_name: '', other_id: '', other_publish_date: '', other_link: '', other_earnings: '', other_remark: '', other_is_published_backfill: false,
    // 旧字段保留兼容
    publish_work_link: '', deadline_earnings: '',
    _open: true,
  }
}
const ACCOUNT_META = {
  '抖音': { key: 'douyin', label: '抖音' },
  '快手': { key: 'kuaishou', label: '快手' },
  'B站': { key: 'bilibili', label: 'B站' },
  '视频号': { key: 'shipinhao', label: '视频号' },
  '其他平台': { key: 'other', label: '其他平台' },
}
function accountFields(key) {
  return {
    name: `${key}_name`,
    id: key === 'douyin' ? 'douyin_account_id' : `${key}_id`,
    publish_date: `${key}_publish_date`,
    link: `${key}_link`,
    earnings: `${key}_earnings`,
    remark: `${key}_remark`,
    backfill: `${key}_is_published_backfill`,
  }
}
const ACCOUNT_DETAIL_LABELS = [
  { label: '名称', field: 'name' },
  { label: '作品发布日期', field: 'publish_date' },
  { label: 'ID', field: 'id' },
  { label: '作品链接', field: 'link' },
  { label: '收益', field: 'earnings' },
  { label: '备注', field: 'remark' },
]
function accountDetailRows(p, a) {
  const fields = accountFields(ACCOUNT_META[a].key)
  return ACCOUNT_DETAIL_LABELS.map(({ label, field }) => {
    let value = p[fields[field]]
    // 旧数据兼容：账号级作品发布日期为空时，回退到平台级 publish_date
    if (field === 'publish_date' && !value && p.publish_date) value = p.publish_date
    return { label: a + label, value, isLink: field === 'link' }
  }).filter(r => r.value)
}
function accountBackfill(p, a) {
  const key = ACCOUNT_META[a].key
  const field = `${key}_is_published_backfill`
  // 账号级字段只要存在（即使是 0）就以它为准；不存在才回退到平台级旧字段
  if (field in p && p[field] !== null && p[field] !== undefined && p[field] !== '') {
    return !!p[field]
  }
  return !!p.is_published_backfill
}
function formatPublishAccounts(item) {
  const set = new Set((item.publish_accounts || '').split(',').map(s => s.trim()).filter(Boolean))
  const labels = Array.from(set).filter(a => ACCOUNTS.includes(a))
  return labels.join('，')
}
function formatPlatformNames(item) {
  return (item.platform_names || '').split(',').map(s => s.trim()).filter(Boolean).join('，')
}
function backfillTag(item) {
  const total = Number(item.backfill_total || 0)
  const done = Number(item.backfill_done || 0)
  if (total === 0) return { text: '未回填', cls: 'no' }
  if (done >= total) return { text: '已全部回填', cls: 'ok' }
  if (done === 0) return { text: '未回填', cls: 'no' }
  return { text: `回填 ${done}/${total}`, cls: 'part' }
}
function blankForm() {
  customCategory.value = ''
  return {
    id: null, name: '', novel_platform: '番茄', platform_type: 'web',
    original_novel_name: '', original_promotion_link: '', original_promotion_copy: '',
    optimized_copy: '', platforms: [blankPlatform()],
  }
}

function openCreate() {
  Object.assign(editing, blankForm())
  showEditor.value = true
}
async function openEdit(item) {
  try {
    const full = await api(`/novel-tweet/${item.id}`, 'GET')
    const known = formCatOptions.value.includes(full.novel_platform)
    customCategory.value = known ? '' : (full.novel_platform || '')
    const platforms = (full.platforms || []).map(p => ({ ...coercePlatformBools(p), _open: false }))
    Object.assign(editing, {
      id: full.id, name: full.name,
      novel_platform: known ? full.novel_platform : '__custom__',
      platform_type: ['web', 'app', 'mini_program'].includes(full.platform_type) ? full.platform_type : 'web',
      original_novel_name: full.original_novel_name || '',
      original_promotion_link: full.original_promotion_link || '',
      original_promotion_copy: full.original_promotion_copy || '',
      optimized_copy: full.optimized_copy || '',
      platforms: platforms.length ? platforms : [blankPlatform()],
    })
    showEditor.value = true
  } catch (e) {
    showToast(e.message || '加载详情失败')
  }
}
async function copyCard(item) {
  try {
    const full = await api(`/novel-tweet/${item.id}`, 'GET')
    const known = formCatOptions.value.includes(full.novel_platform)
    customCategory.value = known ? '' : (full.novel_platform || '')
    const platforms = (full.platforms || []).map(p => ({ ...coercePlatformBools(p), id: null, _open: true }))
    Object.assign(editing, {
      id: null,
      name: full.name || '',
      novel_platform: known ? full.novel_platform : '__custom__',
      platform_type: ['web', 'app', 'mini_program'].includes(full.platform_type) ? full.platform_type : 'web',
      original_novel_name: full.original_novel_name || '',
      original_promotion_link: full.original_promotion_link || '',
      original_promotion_copy: full.original_promotion_copy || '',
      optimized_copy: full.optimized_copy || '',
      platforms: platforms.length ? platforms : [blankPlatform()],
    })
    showEditor.value = true
    showToast('已复制为新建模板，改好名称后保存即可')
  } catch (e) {
    showToast(e.message || '复制失败')
  }
}
function closeEditor() { showEditor.value = false }

// SQLite 返回的布尔是 0/1，前端 checkbox v-model 需要真正的 boolean
function coercePlatformBools(p) {
  const out = { ...p }
  const boolFields = ['is_published_backfill', ...Object.keys(ACCOUNT_META).map(a => `${ACCOUNT_META[a].key}_is_published_backfill`)]
  for (const f of boolFields) {
    out[f] = !!out[f]
  }
  return out
}

function addPlatform() {
  editing.platforms.push(blankPlatform())
}
function removePlatform(pi) {
  editing.platforms.splice(pi, 1)
}

// 发布账号：抖音/快手/B站/视频号/其他平台 多选，按固定顺序返回
function selectedAccounts(p) {
  const set = new Set((p.publish_accounts || '').split(',').map(s => s.trim()).filter(s => ACCOUNTS.includes(s)))
  return ACCOUNTS.filter(a => set.has(a))
}
function hasAccount(p, a) { return selectedAccounts(p).includes(a) }
function toggleAccount(p, a) {
  const arr = selectedAccounts(p)
  const idx = arr.indexOf(a)
  if (idx >= 0) arr.splice(idx, 1)
  else arr.push(a)
  p.publish_accounts = arr.join(',')
}

async function save() {
  if (!editing.name.trim()) { showToast('推文名称不能为空'); return }
  let cat = editing.novel_platform
  if (cat === '__custom__') {
    cat = customCategory.value.trim()
    if (!cat) { showToast('请输入小说平台名称'); return }
  }
  saving.value = true
  try {
    const payload = {
      name: editing.name,
      novel_platform: cat,
      platform_type: editing.platform_type,
      original_novel_name: editing.original_novel_name,
      original_promotion_link: editing.original_promotion_link,
      original_promotion_copy: editing.original_promotion_copy,
      optimized_copy: editing.optimized_copy,
      // 去掉前端辅助字段后再提交
      platforms: editing.platforms.map(p => {
        const { _open, ...rest } = p
        return rest
      }),
    }
    if (editing.id) {
      await api(`/novel-tweet/${editing.id}`, 'PUT', payload)
    } else {
      await api('/novel-tweet/', 'POST', payload)
    }
    showEditor.value = false
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
  if (!(await confirm(`确定删除推广「${item.name}」？此操作不可撤销。`, { title: '删除确认' }))) return
  try {
    await api(`/novel-tweet/${item.id}`, 'DELETE')
    await loadMeta()
    await loadList()
    showToast('已删除')
  } catch (e) {
    showToast(e.message || '删除失败')
  }
}

async function openDetail(item) {
  try {
    detail.value = await api(`/novel-tweet/${item.id}`, 'GET')
    showDetail.value = true
  } catch (e) {
    showToast(e.message || '加载详情失败')
  }
}
function closeDetail() { showDetail.value = false }

async function copyText(text, tip = '已复制') {
  if (!text) return
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text)
    } else {
      const ta = document.createElement('textarea')
      ta.value = text
      ta.style.position = 'fixed'
      ta.style.opacity = '0'
      document.body.appendChild(ta)
      ta.select()
      document.execCommand('copy')
      document.body.removeChild(ta)
    }
    showToast(tip)
  } catch (e) {
    showToast('复制失败，请手动复制')
  }
}
async function copyUrl(url) { await copyText(url, '链接已复制') }

// ---------- 拖拽排序 ----------
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
function onDragEnd() { dragIndex.value = -1; overIndex.value = -1 }
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
    await api('/novel-tweet/reorder', 'POST', { ids })
    showToast('排序已保存')
  } catch (e) {
    showToast(e.message || '排序保存失败')
    await loadList()
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
.nt-page {
  width: 100%;
  height: calc(100vh - 44px);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  font-family: system-ui, -apple-system, "Segoe UI", Roboto, "PingFang SC", "Microsoft YaHei", sans-serif;
  color: var(--sx-text-strong);
}
.nt-home-header { flex-shrink: 0; position: sticky; top: 0; z-index: 3; background: var(--sx-bg-page); }
.nt-home-body { flex: 1; overflow-y: auto; min-height: 0; }
.nt-head {
  display: flex; align-items: center; justify-content: space-between; gap: 16px;
  flex-wrap: wrap; margin-bottom: 18px;
}
.nt-title { display: flex; align-items: center; gap: 12px; color: var(--sx-accent-orange); }
.nt-title h1 { font-size: 22px; margin: 0; color: var(--sx-text-strong); }
.nt-sub { margin: 2px 0 0; font-size: 12.5px; color: var(--sx-text-muted); }
.nt-actions { display: flex; gap: 10px; }

.btn {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 9px 16px; border-radius: 10px; font-size: 14px; font-weight: 600;
  cursor: pointer; border: 1px solid transparent; transition: .15s;
}
.btn.primary { background: var(--sx-btn-orange-bg) !important; color: #fff !important; box-shadow: var(--sx-btn-orange-shadow) !important; border: none !important; }
.btn.primary:hover { filter: brightness(1.05); transform: translateY(-1px) !important; }
.btn.primary:disabled { opacity: .6; cursor: default; transform: none !important; }
.btn.ghost { background: var(--sx-bg-surface) !important; border: 1px solid var(--sx-border) !important; color: var(--sx-text) !important; box-shadow: none !important; }
.btn.ghost:hover { background: var(--sx-bg-surface-2) !important; color: var(--sx-text) !important; transform: none !important; }
.btn.ghost.sm { padding: 7px 12px !important; font-size: 13px !important; }
.btn.block { width: 100%; justify-content: center; margin-top: 10px; }
.btn.danger { color: var(--sx-btn-danger-text) !important; border-color: var(--sx-btn-danger-border) !important; background: var(--sx-bg-surface) !important; }
.btn.danger:hover { background: var(--sx-btn-danger-bg) !important; transform: none !important; }

.nt-filters {
  background: var(--sx-bg-surface); border: 1px solid var(--sx-border); border-radius: 14px;
  padding: 16px; margin-bottom: 18px; box-shadow: var(--sx-shadow-card);
}
.search-wrap { display: flex; align-items: center; gap: 8px; background: var(--sx-bg-surface-2); border: 1px solid var(--sx-border); border-radius: 10px; padding: 0 12px; color: var(--sx-text-muted); }
.search-wrap .search { flex: 1; border: 0; background: transparent; padding: 11px 0; font-size: 14px; color: var(--sx-text-strong); outline: none; }
.filter-row { display: flex; align-items: center; gap: 10px; margin-top: 12px; flex-wrap: wrap; }
.filter-row.inline { gap: 14px; }
.filter-label { font-size: 12.5px; color: var(--sx-text-muted); font-weight: 600; flex-shrink: 0; }
.chips { display: flex; gap: 8px; flex-wrap: wrap; }
.chips.sm .chip { padding: 4px 10px !important; font-size: 12px !important; }
.chip {
  padding: 6px 13px !important; border-radius: 999px !important; border: 1px solid var(--sx-border) !important; background: var(--sx-bg-surface) !important;
  color: var(--sx-text) !important; font-size: 13px !important; cursor: pointer !important; transition: .15s; box-shadow: none !important;
}
.chip:hover { border-color: var(--sx-accent-orange-hover) !important; color: var(--sx-accent-orange) !important; transform: none !important; background: var(--sx-bg-surface) !important; }
.chip.on { background: var(--sx-accent-orange) !important; border-color: var(--sx-accent-orange) !important; color: #fff !important; font-weight: 600 !important; }
.chip.sm.on { background: var(--sx-accent-orange) !important; border-color: var(--sx-accent-orange) !important; }
.count { margin-left: auto; font-size: 12.5px; color: var(--sx-text-muted); }

.nt-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 14px; }
.nt-card {
  background: var(--sx-bg-surface); border: 1px solid var(--sx-border); border-radius: 14px; padding: 18px 18px 48px;
  position: relative;
  cursor: pointer; transition: .15s; display: flex; flex-direction: column; gap: 12px;
  box-shadow: var(--sx-shadow-card);
}
.nt-card:hover { border-color: var(--sx-accent-orange-soft-border); box-shadow: var(--sx-card-orange-shadow); transform: translateY(-2px); }
.nt-card[draggable="true"] { cursor: grab; }
.nt-card.dragging { opacity: .4; }
.nt-card.dragging:hover { transform: none; }
.nt-card.dragover { border-color: var(--sx-accent-orange); box-shadow: var(--sx-card-orange-shadow); }
.card-top { display: flex; align-items: center; gap: 6px; }
.card-title { font-size: 14.5px; margin: 0; color: var(--sx-text-strong); font-weight: 700; line-height: 1.3; flex: 1; }
.card-badges { display: flex; gap: 4px; flex-wrap: wrap; align-items: center; }
.badge { font-size: 10.5px !important; padding: 2px 7px !important; border-radius: 6px !important; font-weight: 600 !important; }
.card-badges .badge + .badge::before,
.card-badges .badge + .tag::before {
  content: '·';
  margin: 0 6px;
  color: var(--sx-text-faint);
  font-weight: 700;
}
.badge.cat { background: var(--sx-accent-orange-soft-bg) !important; color: var(--sx-accent-orange) !important; }
.badge.type { background: var(--sx-tag-info-bg) !important; color: var(--sx-tag-info-text) !important; }
.badge.type.app { background: var(--sx-tag-success-bg) !important; color: var(--sx-tag-success-text) !important; }
.badge.cnt { background: var(--sx-tag-default-bg) !important; color: var(--sx-tag-default-text) !important; max-width: 120px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.badge.no { background: var(--sx-tag-default-bg) !important; color: var(--sx-tag-default-text) !important; }
.card-info { display: flex; flex-direction: column; gap: 12px; }
.info-row { display: flex; align-items: baseline; gap: 12px; font-size: 13px; color: var(--sx-text); line-height: 1.65; }
.info-row.muted { color: var(--sx-text-muted); }
.info-label { flex-shrink: 0; font-size: 12px; color: var(--sx-text-muted); font-weight: 600; }
.info-value { flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.novel-row { align-items: baseline; }
.novel-name-val { flex: 1; font-size: 14px; font-weight: 700; color: var(--sx-text-strong); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.account-row { align-items: center; }
.account-chips { display: flex; flex-wrap: wrap; gap: 10px; white-space: normal; overflow: visible; }
.acc-chip {
  display: inline-flex; align-items: center; gap: 4px;
  font-size: 12.5px; font-weight: 700;
  padding: 1px 2px; border-radius: 4px;
  background: transparent; border: 0;
}
.acc-chip.acc-douyin { color: #d92b2b; }
.acc-chip.acc-kuaishou { color: #e0691a; }
.acc-chip.acc-bilibili { color: #1e6fdb; }
.acc-chip.acc-shipinhao { color: #148a4a; }
.acc-chip.acc-other { color: #7c3aed; }
.card-ops {
  position: absolute; left: 16px; right: 16px; bottom: 14px;
  display: flex; gap: 8px;
  opacity: 0; pointer-events: none;
  transform: translateY(6px);
  transition: opacity .15s, transform .15s;
}
.nt-card:hover .card-ops { opacity: 1; pointer-events: auto; transform: translateY(0); }
.op {
  display: inline-flex; align-items: center; justify-content: center; gap: 4px;
  flex: 1; padding: 7px 8px !important; border-radius: 8px !important; border: 1px solid transparent !important;
  font-size: 12px !important; font-weight: 600 !important; cursor: pointer !important; transition: .15s; min-width: 0;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis; box-shadow: none !important;
}
.op.edit { background: var(--sx-accent-orange-soft-bg) !important; color: var(--sx-accent-orange) !important; border-color: var(--sx-accent-orange-soft-border) !important; }
.op.edit:hover { background: var(--sx-accent-orange) !important; color: #fff !important; border-color: var(--sx-accent-orange) !important; transform: none !important; }
.op.delete { background: var(--sx-btn-danger-bg) !important; color: var(--sx-btn-danger-text) !important; border-color: var(--sx-btn-danger-border) !important; }
.op.delete:hover { background: var(--sx-btn-danger-text) !important; color: #fff !important; border-color: var(--sx-btn-danger-text) !important; transform: none !important; }
.op.copy { background: var(--sx-btn-secondary-bg) !important; color: var(--sx-btn-secondary-text) !important; border-color: var(--sx-btn-secondary-border) !important; }
.op.copy:hover { background: var(--sx-btn-secondary-text) !important; color: #fff !important; border-color: var(--sx-btn-secondary-text) !important; transform: none !important; }

.empty { text-align: center; color: var(--sx-text-muted); padding: 60px 20px; }
.empty svg { color: var(--sx-text-faint); margin-bottom: 12px; }
.empty p { font-size: 14px; max-width: 420px; margin: 0 auto; line-height: 1.6; }

.modal-mask { position: fixed; inset: 0; background: var(--sx-overlay); display: flex; align-items: center; justify-content: center; z-index: 50; padding: 20px; }
.modal { background: var(--sx-bg-elevated); border-radius: 16px; width: 100%; max-width: 900px; max-height: 90vh; display: flex; flex-direction: column; box-shadow: var(--sx-shadow-pop); }
.modal-head { display: flex; align-items: center; justify-content: space-between; padding: 18px 22px; border-bottom: 1px solid var(--sx-border-faint); }
.modal-head h2 { margin: 0; font-size: 17px; color: var(--sx-text-strong); }
.modal-head .x {
  width: 32px !important; height: 32px !important; border-radius: 50% !important;
  display: inline-flex !important; align-items: center !important; justify-content: center !important;
  border: 0 !important; background: var(--sx-bg-surface-2) !important;
  font-size: 18px !important; color: var(--sx-text-muted) !important;
  cursor: pointer !important; padding: 0 !important; box-shadow: none !important;
  transition: .15s; flex-shrink: 0;
}
.modal-head .x:hover { color: #fff !important; background: var(--sx-btn-danger-text) !important; transform: none !important; }
.modal-body { padding: 20px 22px; overflow-y: auto; }
:global(.modal-body::-webkit-scrollbar) { width: 6px; }
:global(.modal-body::-webkit-scrollbar-track) { background: transparent; }
:global(.modal-body::-webkit-scrollbar-thumb) { background: var(--sx-border-strong); border-radius: 3px; }
:global(.modal-body::-webkit-scrollbar-thumb:hover) { background: var(--sx-border-hover); }
.modal-foot { display: flex; justify-content: flex-end; gap: 10px; padding: 14px 22px; border-top: 1px solid var(--sx-border-faint); }

.section-label { font-size: 13px; font-weight: 700; color: var(--sx-accent-orange); margin: 0 0 12px; }
.divider { display: flex; align-items: center; gap: 12px; margin: 22px 0 16px; color: var(--sx-accent-orange); font-size: 13px; font-weight: 700; }
.divider::before, .divider::after { content: ''; flex: 1; height: 1px; background: linear-gradient(90deg, var(--sx-accent-orange-soft-border), transparent); }
.divider span { white-space: nowrap; }

.fld { display: flex; flex-direction: column; gap: 6px; margin-bottom: 14px; }
.fld > span { font-size: 12.5px; color: var(--sx-text); font-weight: 600; }
.fld input, .fld select, .fld textarea {
  border: 1px solid var(--sx-border-input); border-radius: 9px; padding: 10px 12px; font-size: 14px;
  color: var(--sx-text-strong); font-family: inherit; outline: none; transition: .15s; background: var(--sx-bg-surface);
}
.fld input:focus, .fld select:focus, .fld textarea:focus { border-color: var(--sx-accent-orange-hover); box-shadow: 0 0 0 3px var(--sx-accent-orange-soft); }
.fld textarea { resize: vertical; line-height: 1.6; }
.fld-row { display: flex; gap: 14px; }
.fld-row .fld { flex: 1; }
.check-fld { flex-direction: row; align-items: center; gap: 8px; }
.check-fld input { width: 16px; height: 16px; }
.check-fld span { font-size: 13px; color: var(--sx-text); }

.seg { display: inline-flex; border: 1px solid var(--sx-border-input); border-radius: 9px; overflow: hidden; }
.seg-btn {
  flex: 1; padding: 9px 14px !important; border: 0 !important; border-radius: 0 !important;
  background: var(--sx-bg-surface) !important; color: var(--sx-text) !important; font-size: 13px !important;
  cursor: pointer !important; transition: .15s; box-shadow: none !important;
}
.seg-btn:first-child { border-radius: 9px 0 0 9px !important; }
.seg-btn:last-child { border-radius: 0 9px 9px 0 !important; }
.seg-btn:hover { transform: none !important; color: var(--sx-accent-orange) !important; background: var(--sx-accent-orange-soft-bg) !important; }
.seg-btn.on { background: var(--sx-accent-orange) !important; color: #fff !important; font-weight: 600 !important; transform: none !important; }
.seg-btn.on:hover { background: var(--sx-accent-orange) !important; color: #fff !important; }

/* 第三方平台子卡片 */
.pf-card { border: 1px solid var(--sx-accent-orange-soft-border); border-radius: 12px; margin-bottom: 12px; background: var(--sx-accent-orange-soft-bg); overflow: hidden; }
.pf-head { display: flex; align-items: center; gap: 8px; padding: 11px 14px; cursor: pointer; user-select: none; }
.pf-idx { width: 20px; height: 20px; border-radius: 50%; background: var(--sx-accent-orange); color: #fff; font-size: 11px; font-weight: 700; display: inline-flex; align-items: center; justify-content: center; flex-shrink: 0; }
.pf-name { font-size: 13.5px; font-weight: 600; color: var(--sx-text-strong); flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.pf-toggle { font-size: 12px; color: var(--sx-accent-orange); flex-shrink: 0; }
.pf-body { padding: 0 14px 14px; border-top: 1px dashed var(--sx-accent-orange-soft-border); }
.sub-label { font-size: 12px; color: var(--sx-accent-orange-muted-text); font-weight: 700; margin: 12px 0 2px; }
.mt { margin-top: 10px; }
.account-card { border: 1px solid var(--sx-accent-orange-soft-border); border-radius: 10px; padding: 12px 14px; margin: 10px 0 14px; background: var(--sx-accent-orange-soft-bg); }
.account-head { font-size: 13px; font-weight: 700; color: var(--sx-accent-orange-muted-text); margin-bottom: 10px; display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.acc-title { display: inline-flex; align-items: center; gap: 8px; }
.acc-idx { display: inline-flex; align-items: center; justify-content: center; width: 20px; height: 20px; border-radius: 50%; background: var(--sx-accent-orange); color: #fff; font-size: 11.5px; font-weight: 700; margin-right: 7px; }
.backfill-check { display: inline-flex; align-items: center; gap: 4px; font-size: 12px; font-weight: 400; color: var(--sx-text-muted); white-space: nowrap; cursor: pointer; }
.backfill-check input { width: 14px; height: 14px; accent-color: var(--sx-tag-success-text); }
.account-section-head { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; }
.account-section-head strong { font-size: 14px; color: var(--sx-accent-orange-muted-text); font-weight: 700; }
.account-sections { display: flex; flex-direction: column; }
.account-section { padding: 18px 0; }
.account-section + .account-section { border-top: 1px dashed var(--sx-accent-orange-soft-border); }

.kv { margin: 0; display: grid; grid-template-columns: 110px 1fr; gap: 8px 12px; }
.kv dt { font-size: 12.5px; color: var(--sx-text-muted); font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.kv dd { margin: 0; font-size: 13.5px; color: var(--sx-text-strong); word-break: break-word; }
.kv.sm { grid-template-columns: 110px 1fr; gap: 7px 12px; }
.kv .pre { white-space: pre-wrap; line-height: 1.7; color: var(--sx-text-strong); font-size: 14px; }
.kv .pre.collapsed {
  display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical;
  overflow: hidden; max-height: 5.7em;
}
.kv .copy-text { margin-top: 8px; font-size: 12px; color: var(--sx-link) !important; }
.kv .link { display: flex; align-items: center; gap: 6px; }
.kv .link a { color: var(--sx-link); text-decoration: none; word-break: break-all; }
.kv .link a:hover { text-decoration: underline; }
.url-copy { border: 0 !important; background: transparent !important; color: var(--sx-link) !important; cursor: pointer !important; padding: 4px !important; border-radius: 6px !important; display: inline-flex; align-items: center; transition: .15s; flex-shrink: 0; box-shadow: none !important; }
.url-copy:hover { background: var(--sx-btn-secondary-bg) !important; transform: none !important; }
.link-row { word-break: break-all; line-height: 1.6; }
.link-url { color: var(--sx-link); text-decoration: none; font-size: 13.5px; }
.link-url:hover { text-decoration: underline; }
.copy-block {
  background: var(--sx-accent-orange-soft-bg); border: 1px solid var(--sx-accent-orange-soft-border); border-left: 3px solid var(--sx-accent-orange);
  border-radius: 10px; padding: 12px 14px;
}
.copy-block .pre { background: transparent !important; border: 0 !important; border-radius: 0 !important; padding: 0 !important; }
.text-copy {
  margin-top: 10px; font-size: 12.5px; color: var(--sx-link) !important;
  cursor: pointer; background: transparent !important; border: 0 !important; padding: 0 !important;
  transition: .15s; font-weight: 600; box-shadow: none !important; border-radius: 0 !important;
  text-decoration: none;
}
.text-copy:hover { color: var(--sx-accent-strong) !important; text-decoration: underline; }

.detail-badges { display: flex; gap: 7px; flex-wrap: wrap; align-items: center; padding-bottom: 14px; margin-bottom: 16px; border-bottom: 1px solid var(--sx-border-faint); }

.pf-list { display: flex; flex-direction: column; gap: 12px; }
.pf-detail { border: 1px solid var(--sx-accent-orange-soft-border); border-radius: 12px; padding: 12px 14px; background: var(--sx-accent-orange-soft-bg); }
.pf-detail-head { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.tag { font-size: 11px; padding: 2px 8px; border-radius: 999px; font-weight: 600; }
.tag.ok { background: var(--sx-tag-success-bg); color: var(--sx-tag-success-text); }
.tag.no { background: var(--sx-tag-no-bg); color: var(--sx-tag-no-text); }
.tag.part { background: var(--sx-tag-warn-bg) !important; color: var(--sx-tag-warn-text) !important; border-color: var(--sx-tag-warn-border) !important; }
.muted { color: var(--sx-text-muted); font-size: 13px; }

.toast {
  position: fixed; left: 50%; bottom: 40px; transform: translateX(-50%);
  background: var(--sx-toast-dark-bg); color: var(--sx-toast-text); padding: 11px 22px; border-radius: 10px; font-size: 14px;
  box-shadow: var(--sx-shadow-pop); z-index: 80;
}
.fade-enter-active, .fade-leave-active { transition: opacity .25s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

@media (max-width: 640px) {
  .nt-head { flex-direction: column; align-items: stretch; }
  .nt-actions { flex-direction: column; }
  .fld-row { flex-direction: column; gap: 0; }
  .nt-grid { grid-template-columns: 1fr; }
}

</style>
