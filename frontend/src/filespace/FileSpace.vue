<template>
  <div class="filespace">
    <!-- ============ 首页：目录卡片网格（按分类分组） ============ -->
    <template v-if="view === 'home'">
      <div class="fs-home-head">
        <div class="head">
          <h2>📁 文件管理</h2>
          <button class="add-btn" @click="openAdd">＋ 添加目录</button>
        </div>
        <p class="sub">把散落在各盘的常用目录钉在这里，点卡片进去看子目录和文件，支持预览图片/视频/文本，也能一键用系统程序打开。不扫描全盘，纯链接 + 按需展开。</p>
      </div>

      <div class="fs-home-scroll">
        <div v-if="roots.length === 0" class="empty">
          还没有目录，点「添加目录」把一个常用文件夹或文件钉到这里。
        </div>

        <div v-for="(g, gi) in groups" :key="g.name" class="cat-block">
        <div class="cat-head">
          <span class="cat-dot" :style="{ background: g.color }"></span>
          <span class="cat-name">{{ g.name }}</span>
          <span class="cat-count">{{ g.items.length }}</span>
        </div>
        <div class="grid">
          <div
            v-for="(r, ii) in g.items"
            :key="r.id"
          class="tile"
          :class="{ 'drag-target': dragFrom && dragFrom.gi === gi && dragOverIndex === ii }"
            draggable="true"
            @dragstart="dragStart(gi, ii, $event)"
            @dragenter.prevent="dragEnter(gi, ii)"
            @dragleave="dragLeave(gi, ii)"
            @dragover.prevent
            @drop="drop(gi, ii)"
            @click="openRoot(r)"
          >
            <div class="tile-cover-wrap">
              <img v-if="covers[r.id]" :src="covers[r.id]" class="tile-cover-img" alt="">
              <div v-else class="tile-cover" :style="{ background: r.default_color || 'var(--sx-accent)' }"></div>
            </div>
            <div class="tile-bar">
              <span class="tile-name" :title="r.path">{{ r.name }}</span>
              <span class="tile-actions">
                <button class="act-open" @click.stop="openRoot(r)" title="打开">
                  <img src="/filespace/icons/icon-open@2x.png" alt="打开" />
                </button>
                <button class="act-edit" @click.stop="editRoot(r)" title="编辑目录">
                  <img src="/filespace/icons/icon-edit@2x.png" alt="编辑" />
                </button>
                <button class="act-set" @click.stop="openCover(r)" title="修改封面">
                  <img src="/filespace/icons/icon-set@2x.png" alt="设置" />
                </button>
                <button class="act-del" @click.stop="delRoot(r)" title="删除目录">
                  <img src="/filespace/icons/icon-del@2x.png" alt="删除" />
                </button>
              </span>
            </div>
          </div>
        </div>
      </div>
      </div>
    </template>

    <!-- ============ 目录内部：面包屑 + 文件列表 ============ -->
    <template v-else>
      <div class="fs-dir-head">
        <div class="head dir-head">
          <button class="ghost" @click="view = 'home'">← 首页</button>
          <button class="ghost" :disabled="!canGoUp" @click="goParent">↑ 上一级</button>
          <span class="crumbs-wrap">
            <span class="crumbs" :title="current">{{ current }}</span>
            <button v-if="current" class="ghost copy-path-btn" title="复制完整路径" @click="copyCurrentPath">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
            </button>
          </span>
        </div>

        <div class="dir-toolbar">
          <div class="view-toggle">
            <button
              type="button"
              :class="{ on: dirViewMode === 'list' }"
              @click="dirViewMode = 'list'"
              title="列表视图"
            >
              <svg viewBox="0 0 20 20" class="view-ico"><path d="M3 5h14M3 10h14M3 15h14" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
            </button>
            <button
              type="button"
              :class="{ on: dirViewMode === 'thumb' }"
              @click="dirViewMode = 'thumb'"
              title="缩略图视图"
            >
              <svg viewBox="0 0 20 20" class="view-ico"><rect x="3" y="3" width="6" height="6" rx="1.5" fill="currentColor"/><rect x="11" y="3" width="6" height="6" rx="1.5" fill="currentColor"/><rect x="3" y="11" width="6" height="6" rx="1.5" fill="currentColor"/><rect x="11" y="11" width="6" height="6" rx="1.5" fill="currentColor"/></svg>
            </button>
          </div>
          <input
            v-model="searchText"
            class="search-box"
            placeholder="搜索文件名…"
          />
          <div class="filter-chips">
            <button
              v-for="f in filters"
              :key="f.v"
              type="button"
              class="fchip"
              :class="{ on: typeFilter === f.v }"
              @click="typeFilter = f.v"
            >{{ f.label }}</button>
          </div>
          <div class="sort-box">
            <span class="sort-label">排序</span>
            <select v-model="sortKey" class="sort-select">
              <option value="name">名称</option>
              <option value="date">修改日期</option>
              <option value="size">大小</option>
              <option value="type">类型</option>
            </select>
            <button type="button" class="sort-dir" @click="sortDesc = !sortDesc" :title="sortDesc ? '当前降序，点切换升序' : '当前升序，点切换降序'">
              {{ sortDesc ? '↓ 降' : '↑ 升' }}
            </button>
            <label class="sort-folders">
              <input type="checkbox" v-model="foldersFirst" /> 文件夹置顶
            </label>
          </div>
          <div class="pin-tags" v-if="rootPath">
            <div class="pin-row">
              <span class="pin-label">文件夹快捷入口</span>
              <button
                type="button"
                class="pin-text-btn"
                :title="'扫描 ' + (basenameOf(current) || '当前文件夹') + ' 的直接子文件夹'"
                @click="generateTags"
              >{{ currentHasTags ? '重新扫描' : '＋ 生成子文件夹入口' }}</button>
              <button
                type="button"
                class="pin-text-btn danger"
                v-if="hasAnyTags"
                @click="clearTags"
                title="清空该书签根的所有快捷入口"
              >清空</button>
            </div>
            <div class="pin-chips" v-if="hasAnyTags">
              <button
                v-for="chip in allTagChips"
                :key="chip.key"
                type="button"
                class="pin-tag"
                :class="{ active: chip.active }"
                :title="'进入：' + chip.path"
                @click="enter(chip.path)"
              >
                <svg class="pin-folder" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7z"/></svg>
                <span class="pin-tag-name">{{ chip.displayName }}</span>
                <span class="pin-x" title="移除该入口及其子级" @click.stop="removeTag(chip)">✕</span>
              </button>
            </div>
          </div>
        </div>
      </div>

      <div class="fs-dir-scroll">
        <div class="dir-main" :class="{ 'thumb-mode': dirViewMode === 'thumb' }">
        <template v-if="dirViewMode === 'list'">
          <div v-if="loading" class="card"><p>加载中…</p></div>
          <div v-else class="card list">
            <table>
              <thead>
                <tr><th>名称</th><th>类型</th><th>大小</th><th>修改时间</th><th>操作</th></tr>
              </thead>
              <tbody>
                <tr
                  v-for="it in pagedItems"
                  :key="it.path"
                  :class="{ clickable: true, sel: selected && selected.path === it.path, folder: it.is_dir }"
                  @click="it.is_dir ? enter(it.path) : (['image','video'].includes(it.type) ? openLightbox(it) : select(it))"
                >
                  <td class="name-cell">
                    <span class="type-ico">{{ it.is_dir ? '📂' : iconOf(it.type) }}</span>
                    <span class="fname" :title="it.name">{{ it.name }}</span>
                  </td>
                  <td>{{ it.is_dir ? '文件夹' : it.type }}</td>
                  <td>{{ it.size == null ? '-' : fmtSize(it.size) }}</td>
                  <td>{{ fmtTime(it.mtime) }}</td>
                  <td class="ops">
                    <button v-if="!it.is_dir" @click.stop="openFile(it.path)">打开</button>
                    <button v-if="!it.is_dir && canPreview(it.type)" class="ghost" @click.stop="previewInList(it)">预览</button>
                    <button @click.stop="startRename(it)">重命名</button>
                    <button class="ghost danger" @click.stop="deleteItem(it)">删除</button>
                  </td>
                </tr>
                <tr v-if="filteredItems.length === 0">
                  <td colspan="5" class="empty-row">没有匹配的文件</td>
                </tr>
              </tbody>
            </table>
          </div>
        </template>

        <template v-else>
          <div v-if="loading" class="card"><p>加载中…</p></div>
          <div v-else class="thumb-grid" tabindex="0" @keydown="onGridKey">
            <div
              v-for="it in pagedItems"
              :key="it.path"
              class="thumb-tile"
              :class="{ folder: it.is_dir, sel: !it.is_dir && focusedIndex >= 0 && lightboxItemsIndex(it) === focusedIndex }"
              :draggable="!it.is_dir"
              @dragstart="onNativeDragStart($event, it)"
              @click="openLightbox(it)"
              @mouseenter="onThumbEnter(it)"
              @mouseleave="onThumbLeave"
            >
              <div class="thumb-cover">
                <img v-if="it.type === 'image'" :src="streamUrl(it.path)" class="thumb-img" loading="lazy" alt="" />
                <video v-else-if="it.type === 'video'" :src="streamUrl(it.path)" class="thumb-video" preload="metadata" muted playsinline @loadeddata="onVideoMeta"></video>
                <div v-else-if="it.is_dir" class="thumb-folder">📂</div>
                <div v-else class="thumb-type">{{ iconOf(it.type) }}</div>
                <span v-if="it.type === 'video'" class="play-badge">▶</span>
              </div>
              <div class="thumb-bar">
                <div class="thumb-name" :title="it.name">{{ it.name }}</div>
                <div class="thumb-actions" @click.stop>
                  <button v-if="!it.is_dir" class="ta-btn" title="打开位置" draggable="false" @click.stop="openParent(it.path)">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><path d="M15 3h6v6"/><path d="M10 14 21 3"/></svg>
                  </button>
                  <button class="ta-btn" title="重命名" draggable="false" @click.stop="startRename(it)">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 3a2.828 2.828 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3z"/></svg>
                  </button>
                  <button class="ta-btn danger" title="删除" draggable="false" @click.stop="deleteItem(it)">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"/><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
                  </button>
                </div>
              </div>
            </div>
            <div v-if="filteredItems.length === 0" class="empty-row" style="grid-column: 1/-1;">没有匹配的文件</div>
          </div>
        </template>

      <!-- 分页器：目录深/文件多时分页浏览，避免一次渲染过多 -->
      <div v-if="total > 0" class="pager">
        <div class="pager-info">共 {{ total }} 条 · 第 {{ pageNo }}/{{ totalPages }} 页</div>
        <div class="pager-ctrl">
          <button class="pg-btn" :disabled="pageNo <= 1" @click="goPage(1)">« 首页</button>
          <button class="pg-btn" :disabled="pageNo <= 1" @click="goPage(pageNo - 1)">‹ 上一页</button>
          <button
            v-for="b in pageButtons"
            :key="String(b)"
            class="pg-num"
            :class="{ on: b === pageNo, ellipsis: b === '...' }"
            :disabled="b === '...'"
            @click="b !== '...' && goPage(b)"
          >{{ b }}</button>
          <button class="pg-btn" :disabled="pageNo >= totalPages" @click="goPage(pageNo + 1)">下一页 ›</button>
          <button class="pg-btn" :disabled="pageNo >= totalPages" @click="goPage(totalPages)">尾页 »</button>
        </div>
        <div class="pager-size">
          每页
          <div class="size-btns">
            <button
              v-for="sz in [8, 10, 16, 24, 32, 64, 128]"
              :key="sz"
              :class="['size-btn', { on: pageSize === sz }]"
              @click="pageSize = sz"
            >{{ sz }}</button>
          </div>
          条
        </div>
      </div>

    <!-- 预览/编辑弹窗：列表与缩略图视图共用 -->
    <div v-if="preview" class="mask preview-mask" @click.self="preview = null">
      <div class="preview-modal">
        <div class="pv-head">
          <span class="pv-name">{{ preview.name }}</span>
          <div class="pv-actions">
            <template v-if="preview.kind === 'text'">
              <button class="ghost" @click="copyText">复制</button>
              <button v-if="!preview.editing" class="ghost" @click="startEdit">编辑</button>
              <button v-else :disabled="saving" @click="saveEdit">{{ saving ? '保存中…' : '保存' }}</button>
              <button v-if="preview.editing" class="ghost" @click="cancelEdit">取消</button>
            </template>
            <button class="ghost" @click="preview = null">关闭</button>
          </div>
        </div>
        <div class="pv-body">
          <img v-if="preview.kind === 'image'" :src="preview.src" class="pv-img" />
          <div v-else-if="preview.kind === 'text'" class="pv-text-wrap">
            <textarea v-if="preview.editing" v-model="preview.draft" class="pv-edit" spellcheck="false"></textarea>
            <textarea v-else :value="preview.text || '（文件内容为空）'" class="pv-edit" readonly spellcheck="false" style="resize: none;"></textarea>
          </div>
          <video v-else-if="preview.kind === 'video'" :src="preview.stream" controls class="pv-media"></video>
          <audio v-else-if="preview.kind === 'audio'" :src="preview.stream" controls class="pv-media"></audio>
          <iframe v-else-if="preview.kind === 'pdf'" :src="preview.stream" class="pv-pdf"></iframe>
          <div v-else class="pv-hint">
            <p>该类型（{{ preview.type }}）暂不支持内联预览。</p>
            <button @click="openFile(preview.path)">用系统程序打开</button>
          </div>
        </div>
      </div>
    </div>
      </div>
      </div>
    </template>

    <!-- ============ 添加/编辑目录弹窗 ============ -->
    <div v-if="showForm" class="mask" @click.self="closeForm">
      <div class="modal">
        <h3>{{ editingRoot ? '编辑目录' : '添加目录' }}</h3>
        <div class="form-row">
          <label>目录名</label>
          <input v-model="newName" placeholder="如 F盘·小说项目" />
        </div>
        <div class="form-row">
          <label>绝对路径（文件夹或文件）</label>
          <input v-model="newPath" placeholder="如 F:\suxiaomo-studio 或 C:\Users\xxx\file.xlsx" />
        </div>
        <div class="form-row">
          <label>分类</label>
          <div class="cat-chips">
            <button
              v-for="c in ['下载','文件','文件夹','其它']"
              :key="c"
              type="button"
              class="cat-chip"
              :class="{ on: newCategory === c }"
              @click="newCategory = c"
            >{{ c }}</button>
            <button
              type="button"
              class="cat-chip add"
              :class="{ on: isCustomCategory }"
              @click="focusCustomCategory"
            >＋ 自定义</button>
          </div>
          <input
            ref="catInput"
            v-model="newCategory"
            placeholder="输入自定义分类名，回车确认"
            class="cat-custom-input"
            @focus="customFocused = true"
            @blur="customFocused = false"
            @keyup.enter="blurCustomCategory"
          />
          <p v-if="isCustomCategory" class="cat-hint">已启用自定义分类：{{ newCategory || '（未填写）' }}</p>
        </div>
        <div class="form-row">
          <label>备注（可选）</label>
          <input v-model="newNote" placeholder="写点备注…" />
        </div>
        <div class="modal-actions">
          <button :disabled="!newName || !newPath" @click="saveRoot">保存</button>
          <button class="ghost" @click="closeForm">取消</button>
        </div>
      </div>
    </div>

    <!-- 封面上传弹窗 -->
    <div v-if="coverModal" class="mask" @click.self="closeCover">
      <div class="modal" style="max-width: 520px">

        <!-- 步骤1：选择 / 裁剪 -->
        <template v-if="!cropSrc">
          <h3 style="margin: 0 0 8px">修改封面</h3>
          <p style="color: var(--sx-text); font-size: 13px; margin: 0 0 16px">
            为「{{ coverTarget && coverTarget.name }}」上传一张本地图片作为封面，支持 1:1 裁剪。
          </p>
          <div style="display:flex; gap:12px; align-items:center; margin-bottom:16px">
            <div style="width:80px;height:80px;border-radius:10px;overflow:hidden;background:var(--sx-bg-surface-2);display:flex;align-items:center;justify-content:center;border:1px solid var(--sx-border)">
              <img v-if="coverTarget && covers[coverTarget.id]" :src="covers[coverTarget.id]" style="width:100%;height:100%;object-fit:cover" alt="">
              <div v-else :style="{ width:'100%',height:'100%', background: coverTarget && (coverTarget.default_color || 'var(--sx-accent)') }"></div>
            </div>
            <div style="flex:1">
              <input type="file" accept="image/*" @change="onCoverFilePick" :disabled="coverUploading" style="font-size:12px;width:100%">
              <button v-if="coverTarget && coverTarget.cover_path" class="ghost" style="margin-top:8px" @click="clearCover" :disabled="coverUploading">恢复默认色块</button>
            </div>
          </div>
        </template>

        <!-- 步骤2：裁剪预览 -->
        <template v-else>
          <h3 style="margin: 0 0 8px">裁剪封面（1:1）</h3>
          <p style="color: var(--sx-text); font-size: 13px; margin: 0 0 12px">拖动白色方框调整裁剪区域，松开后点击「确定」。</p>

          <!-- 裁剪区域 -->
          <div class="crop-wrap" ref="cropWrapEl"
            @mousedown.prevent="cropStartDrag"
          >
            <img :src="cropSrc" class="crop-img" ref="cropImgEl" @load="cropInitBox" />
            <!-- 1:1 选框 -->
            <div class="crop-box" :style="cropBoxStyle">
              <div class="crop-grid"></div>
              <!-- 四角拖拽手柄 -->
              <span class="crop-handle tl" data-dir="tl"></span>
              <span class="crop-handle tr" data-dir="tr"></span>
              <span class="crop-handle bl" data-dir="bl"></span>
              <span class="crop-handle br" data-dir="br"></span>
            </div>
          </div>

          <!-- 预览 -->
          <div style="display:flex; gap:12px; align-items:center; margin-top:14px">
            <span style="font-size:12px;color:var(--sx-text);font-weight:600">预览：</span>
            <canvas ref="cropCanvasEl" width="80" height="80" style="width:80px;height:80px;border-radius:10px;border:1px solid var(--sx-border);display:block"></canvas>
          </div>
        </template>

        <div class="modal-actions" style="margin-top:16px">
          <button v-if="cropSrc" @click="cropConfirm" :disabled="coverUploading">{{ coverUploading ? '上传中…' : '确定' }}</button>
          <button v-if="cropSrc" class="ghost" @click="cropCancel">取消裁剪</button>
          <button class="ghost" @click="closeCover" :disabled="coverUploading">关闭</button>
        </div>
      </div>
    </div>
  </div>

  <!-- 重命名弹窗：名称放长一些，方便修改长文件名 -->
  <div v-if="renameModal" class="mask" @click.self="cancelRename">
    <div class="modal" style="max-width: 540px">
      <h3 style="margin: 0 0 6px">重命名</h3>
      <p style="color: var(--sx-text); font-size: 13px; margin: 0 0 14px">
        正在重命名：<code style="background:var(--sx-bg-surface-2);padding:1px 5px;border-radius:4px">{{ renameTarget && renameTarget.name }}</code>
      </p>
      <input
        ref="renameInputEl"
        v-model="draftName"
        v-select-base-name
        class="rename-input"
        :class="{ 'ext-danger': renameTarget && extChanged(renameTarget) }"
        style="width: 100%; font-size: 14px; padding: 9px 11px"
        @keyup.enter="saveRename()"
        @keyup.esc="cancelRename"
      />
      <p v-if="renameTarget && extChanged(renameTarget)" style="color:var(--sx-btn-danger-text);font-size:12px;margin:6px 0 0">
        ⚠ 扩展名将改变（{{ extOf(renameTarget.name) || '无' }} → {{ extOf(draftName.trim()) || '无' }}），可能导致文件无法打开。
      </p>
      <div class="modal-actions" style="margin-top:16px">
        <button @click="saveRename()">保存</button>
        <button class="ghost" @click="cancelRename">取消</button>
      </div>
    </div>
  </div>

  <!-- 媒体灯箱：缩略图视图下点击/空格放大，Esc 关闭，← → 切换 -->
  <MediaLightbox
    :visible="lightboxVisible"
    :items="lightboxItems"
    :index="lightboxIndex"
    @close="closeLightbox"
    @update:index="lightboxIndex = $event"
  />
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { api } from '../common/http.js'
import { confirm, alert } from '../common/useConfirm.js'
import { useErrorStore } from '../common/error-store.js'
import MediaLightbox from './MediaLightbox.vue'

const view = ref('home') // 'home' | 'dir'
const roots = ref([])
const showForm = ref(false)
const editingRoot = ref(null)
const newName = ref('')
const newPath = ref('')
const newCategory = ref('下载')
const newNote = ref('')

const current = ref('')
const parent = ref('')
const items = ref([])
const loading = ref(false)
const searchText = ref('')
const typeFilter = ref('all')
const filters = [
  { v: 'all', label: '全部' },
  { v: 'folder', label: '文件夹' },
  { v: 'video', label: '视频' },
  { v: 'image', label: '图片' },
  { v: 'audio', label: '音频' },
  { v: 'text', label: '文本' },
  { v: 'other', label: '其他' },
]

// ===== 文件夹快捷入口（任意层级，持久化在 filespace_roots.pinned_tags）=====
// 存储结构：{ 文件夹绝对路径: [该文件夹下的直接子文件夹名, ...] }
// 任意层级都能生成：在哪儿点「扫描本文件夹子目录」，就扫描那个文件夹的直接子文件夹写入。
// 不判断层级深度、不设上限；文件夹原名原样保留（含 NN- 前缀与括号）。
// 点节点 = 进该文件夹；✕ = 删除该入口及其下整条分支。
const currentRoot = computed(() => {
  return roots.value.find(r => normPath(r.path) === normPath(rootPath.value)) || null
})
// 读取「路径 → 直接子文件夹列表」字典（后端已归一化为新格式；这里兜底容错）
const tagMap = computed(() => {
  const r = currentRoot.value
  const raw = r && r.pinned_tags
  if (raw && typeof raw === 'object' && !Array.isArray(raw)) return raw
  return {}
})
const tagCount = computed(() => Object.keys(tagMap.value).length)
// 路径匹配键：统一正斜杠、小写、去尾分隔符，避免 Windows 反斜杠/大小写不一致导致 key 对不上
function normKey(p) {
  return (p || '').replace(/[\\/]+$/, '').replace(/\\/g, '/').toLowerCase()
}
// 给定目标路径在 tagMap 中的精确 key（通过 normKey 查找，兼容大小写/斜杠差异）
function findTagKey(target) {
  if (!target) return null
  const t = normKey(target)
  for (const k of Object.keys(tagMap.value)) {
    if (normKey(k) === t) return k
  }
  return null
}
// 书签根下所有已生成入口，摊平为药丸列表
// 重名时 displayName = 上级目录名_原名；唯一时保持原名
const allTagChips = computed(() => {
  const root = rootPath.value
  if (!root) return []
  const rootNorm = normKey(root)
  // 收集所有入口
  const entries = []
  for (const [folderPath, names] of Object.entries(tagMap.value)) {
    if (!folderPath || !Array.isArray(names)) continue
    const folderNorm = normKey(folderPath)
    if (!folderNorm.startsWith(rootNorm)) continue
    for (const name of names) {
      const path = joinPath(folderPath, name)
      entries.push({ key: normKey(path), name, parent: folderPath, path })
    }
  }
  // 统计名称冲突
  const nameCount = {}
  for (const e of entries) {
    nameCount[e.name] = (nameCount[e.name] || 0) + 1
  }
  // 构造展示项
  const chips = entries.map(e => {
    const parentBase = basenameOf(e.parent)
    const displayName = nameCount[e.name] > 1 ? parentBase + '_' + e.name : e.name
    return {
      ...e,
      displayName,
      active: normKey(current.value) === normKey(e.path),
    }
  })
  // 按路径自然排序
  return chips.sort((a, b) => naturalCompare(a.path, b.path))
})
const hasAnyTags = computed(() => allTagChips.value.length > 0)
// 当前文件夹是否已生成过入口（用于决定按钮显示「重新扫描」还是「＋扫描」）
const currentHasTags = computed(() => {
  const k = findTagKey(current.value)
  return k ? (Array.isArray(tagMap.value[k]) ? tagMap.value[k].length > 0 : false) : false
})

function basenameOf(p) {
  return (p || '').replace(/[\\/]+$/, '').split(/[\\/]/).pop() || p || ''
}
function joinPath(a, b) {
  const sep = a.includes('\\') ? '\\' : '/'
  return a.replace(/[\\/]+$/, '') + sep + b
}
function syncRoot(updated) {
  const idx = roots.value.findIndex(x => x.id === updated.id)
  if (idx >= 0) roots.value[idx] = { ...roots.value[idx], ...updated }
}
async function generateTags() {
  const r = currentRoot.value
  if (!r) { await alert('请先进入一个书签目录，再生成快捷入口。'); return }
  try {
    const updated = await api('/filespace/roots/' + r.id + '/generate-tags', 'POST', { folder_path: current.value })
    syncRoot(updated)
  } catch (e) {
    await alert('生成快捷入口失败：' + (e.message || e))
  }
}
async function removeTag(chip) {
  const r = currentRoot.value
  if (!r || !chip) return
  const folderPath = findTagKey(chip.parent)
  const name = chip.name
  if (!folderPath) return
  const newMap = JSON.parse(JSON.stringify(tagMap.value))
  if (Array.isArray(newMap[folderPath])) {
    newMap[folderPath] = newMap[folderPath].filter(x => x !== name)
  }
  // 级联删除该入口下的整条分支（子路径键）
  const sep = folderPath.includes('\\') ? '\\' : '/'
  const childPath = folderPath + sep + name
  const prefix = childPath + sep
  for (const k of Object.keys(newMap)) {
    if (k === childPath || k.startsWith(prefix)) delete newMap[k]
  }
  try {
    const updated = await api('/filespace/roots/' + r.id + '/tags', 'PUT', { tags: newMap })
    syncRoot(updated)
  } catch (e) {
    await alert('移除入口失败：' + (e.message || e))
  }
}
async function clearTags() {
  const r = currentRoot.value
  if (!r || tagCount.value === 0) return
  if (!confirm('确定清空「' + r.name + '」的所有文件夹快捷入口？')) return
  try {
    const updated = await api('/filespace/roots/' + r.id + '/tags', 'PUT', { tags: {} })
    syncRoot(updated)
  } catch (e) {
    await alert('清空失败：' + (e.message || e))
  }
}
// 路径归一化：去掉尾部路径分隔符，避免根目录比较时因分隔符差异误判
function normPath(p) {
  return (p || '').replace(/[\\/]+$/, '')
}
// 是否允许"上一级"：存在父目录且当前不是书签根目录（书签目录即最顶层，不做向上溯源）
const canGoUp = computed(() => {
  return !!parent.value && normPath(current.value) !== normPath(rootPath.value)
})
// 排序：名称 / 修改日期 / 大小 / 类型，升/降序，文件夹可选置顶
const sortKey = ref('name')       // 'name' | 'date' | 'size' | 'type'
const sortDesc = ref(false)        // true=降序, false=升序
const foldersFirst = ref(true)     // 文件夹置顶

// 列表数据源：搜索模式下展示业务标签搜索结果，否则展示当前目录一层内容
const displaySource = computed(() => items.value)
const filteredItems = computed(() => {
  const q = searchText.value.trim().toLowerCase()
  let list = displaySource.value
  if (q) list = list.filter(it => it.name.toLowerCase().includes(q))
  if (typeFilter.value !== 'all') {
    if (typeFilter.value === 'folder') list = list.filter(it => it.is_dir)
    else if (typeFilter.value === 'other') list = list.filter(it => !it.is_dir && !['video', 'image', 'audio', 'text'].includes(it.type))
    else list = list.filter(it => it.type === typeFilter.value)
  }
  list = list.slice().sort((a, b) => {
    if (foldersFirst.value && a.is_dir !== b.is_dir) return a.is_dir ? -1 : 1
    let cmp = 0
    switch (sortKey.value) {
      case 'date': cmp = (a.mtime || 0) - (b.mtime || 0); break
      case 'size': cmp = (a.size == null ? -1 : a.size) - (b.size == null ? -1 : b.size); break
      case 'type':
        cmp = naturalCompare(a.type || '', b.type || '')
        if (cmp === 0) cmp = naturalCompare(a.name, b.name)
        break
      case 'name':
      default: cmp = naturalCompare(a.name, b.name)
    }
    return sortDesc.value ? -cmp : cmp
  })
  return list
})

// ===== 分页：先全局筛选/排序，再对结果切片，避免一次渲染过多 DOM 卡顿 =====
const pageNo = ref(1)
const pageSize = ref(24)
// 筛选/搜索/排序/目录内容变化时回到第一页
watch(filteredItems, () => { pageNo.value = 1 })

const total = computed(() => filteredItems.value.length)
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)))
const pagedItems = computed(() => {
  const start = (pageNo.value - 1) * pageSize.value
  return filteredItems.value.slice(start, start + pageSize.value)
})
// 页码按钮：页数少全显示；页数多显示首/尾 + 当前页附近，中间用省略号
const pageButtons = computed(() => {
  const tp = totalPages.value
  if (tp <= 7) return Array.from({ length: tp }, (_, i) => i + 1)
  const cur = pageNo.value
  const set = new Set([1, 2, tp - 1, tp, cur - 1, cur, cur + 1])
  const arr = [...set].filter(n => n >= 1 && n <= tp).sort((a, b) => a - b)
  const out = []
  let prev = 0
  for (const n of arr) {
    if (n - prev > 1) out.push('...')
    out.push(n)
    prev = n
  }
  return out
})
function goPage(n) {
  const t = totalPages.value
  if (n < 1) n = 1
  if (n > t) n = t
  pageNo.value = n
}

// 自然排序：数字按数值比较（10.mp4 排在 2.mp4 之后），中文按拼音
function naturalCompare(a, b) {
  return String(a).localeCompare(String(b), 'zh-CN', { numeric: true, sensitivity: 'base' })
}
const selected = ref(null)
const preview = ref(null)
const rootPath = ref('')  // 书签根目录：目录导航最顶层，不可向上越出
const saving = ref(false)
const dragFrom = ref(null)
const dragOverIndex = ref(null)
const renameModal = ref(false)
const renameTarget = ref(null)
const renameInputEl = ref(null)

// ===== 缩略图视图 + 灯箱 =====
const dirViewMode = ref('thumb')    // 'list' | 'thumb'
const lightboxVisible = ref(false)
const lightboxIndex = ref(0)
const focusedIndex = ref(0)
const hoveredItem = ref(null)        // 当前鼠标悬停的缩略图项
// 灯箱可浏览项：仅媒体文件（图片/视频/音频/PDF），文本走预览抽屉
const lightboxItems = computed(() => filteredItems.value.filter(it => !it.is_dir && ['image', 'video', 'audio', 'pdf'].includes(it.type)))

// ===== 封面 =====
// covers: { [root_id]: base64DataUrl }  有封面图时显示，否则用 r.default_color 纯色块
const covers = ref({})
const coverModal = ref(false)       // 封面上传弹窗
const coverTarget = ref(null)       // 当前编辑封面的书签对象
const coverUploading = ref(false)
const draftName = ref('')
const vFocus = { mounted: (el) => el.focus() }
const vSelectBaseName = {
  mounted(el) {
    el.focus()
    const val = el.value || ''
    const dot = val.lastIndexOf('.')
    const end = dot > 0 ? dot : val.length
    el.setSelectionRange(0, end)
  },
  updated(el) {
    // 指令更新时如果已经选过就保持原状，避免反复重置光标
  }
}

// 弹窗分类：快捷按钮 + 自定义输入
const catInput = ref(null)
const customFocused = ref(false)
const PRESET_CATS = ['下载', '文件', '文件夹', '其它']
const isCustomCategory = computed(() => !PRESET_CATS.includes(newCategory.value))
function focusCustomCategory() {
  catInput.value?.focus()
}
function blurCustomCategory() {
  catInput.value?.blur()
}

// ===== 裁剪（1:1 正方形） =====
const cropSrc = ref('')              // 原图 data URL（进入裁剪模式时赋值）
const cropRawFile = ref(null)        // 原始 File 对象，确认后上传用
const cropBox = ref({ x: 0, y: 0, size: 120 })  // 选框：左上角坐标 + 边长（显示像素）
const cropImgNatural = ref({ w: 0, h: 0 })       // 原图实际尺寸
const cropDrag = ref(null)           // 拖拽状态 { type:'move'|'resize', dir?, startX, startY, startBox }
const cropWrapEl = ref(null)
const cropImgEl = ref(null)
const cropCanvasEl = ref(null)

// 选框样式（响应式）
const cropBoxStyle = computed(() => {
  const b = cropBox.value
  return {
    left: b.x + 'px',
    top: b.y + 'px',
    width: b.size + 'px',
    height: b.size + 'px',
  }
})

async function onCoverFilePick(e) {
  const file = e.target.files && e.target.files[0]
  if (!file || !coverTarget.value) return
  if (!file.type.startsWith('image/')) {
    await alert('请选择图片文件')
    return
  }
  const reader = new FileReader()
  reader.onload = () => {
    cropSrc.value = reader.result
    cropRawFile.value = file
    // 重置选框为居中，等图片 load 后再精确初始化
    cropBox.value = { x: 60, y: 40, size: 120 }
  }
  reader.readAsDataURL(file)
}

function cropInitBox() {
  const img = cropImgEl.value
  if (!img) return
  // 图片加载完成后，根据显示尺寸初始化 1:1 选框（居中，取短边）
  const dw = img.clientWidth
  const dh = img.clientHeight
  const minSide = Math.min(dw, dh)
  const size = minSide * 0.8  // 占短边 80%
  cropBox.value = {
    x: (dw - size) / 2,
    y: (dh - size) / 2,
    size: size,
  }
  cropImgNatural.value = { w: img.naturalWidth, h: img.naturalHeight }
  cropDrawPreview()
}

function cropGetScale() {
  const img = cropImgEl.value
  if (!img) return 1
  return img.naturalWidth / img.clientWidth
}

function cropStartDrag(ev) {
  const boxEl = ev.target.closest('.crop-box')
  const handleEl = ev.target.closest('.crop-handle')
  if (!boxEl && !handleEl) return

  const dir = handleEl ? handleEl.dataset.dir : null
  cropDrag.value = {
    type: handleEl ? 'resize' : 'move',
    dir,
    startX: ev.clientX,
    startY: ev.clientY,
    startBox: { ...cropBox.value },
  }
  // 用 document 级别监听，防止鼠标移出裁剪区域丢失事件
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
  const minSize = 40
  let b = { ...d.startBox }

  if (d.type === 'move') {
    b.x = clamp(d.startBox.x + dx, 0, iw - b.size)
    b.y = clamp(d.startBox.y + dy, 0, ih - b.size)
  } else {
    // resize：四角拖拽，保持 1:1
    let newSize = d.startBox.size
    if (d.dir?.includes('r')) newSize = Math.max(minSize, d.startBox.size + dx)
    else if (d.dir?.includes('l')) newSize = Math.max(minSize, d.startBox.size - dx)

    newSize = clamp(newSize, minSize, Math.min(iw, ih))

    let nx = d.startBox.x, ny = d.startBox.y
    if (d.dir?.includes('l')) nx = d.startBox.x + d.startBox.size - newSize
    if (d.dir?.includes('t')) ny = d.startBox.y + d.startBox.size - newSize

    b.x = clamp(nx, 0, iw - newSize)
    b.y = clamp(ny, 0, ih - newSize)
    b.size = newSize
  }

  cropBox.value = b
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
  const b = cropBox.value
  const ctx = canvas.getContext('2d')
  canvas.width = 80
  canvas.height = 80
  ctx.drawImage(
    img,
    b.x * scale, b.y * scale, b.size * scale, b.size * scale,
    0, 0, 80, 80
  )
}

async function cropConfirm() {
  if (!cropRawFile.value || !coverTarget.value) return
  coverUploading.value = true
  try {
    // 用 Canvas 截取选区 → 转 Blob → 上传
    const canvas = document.createElement('canvas')
    const img = cropImgEl.value
    if (!img) throw new Error('图片未就绪')
    const scale = cropGetScale()
    const b = cropBox.value
    const outSize = 200  // 输出 200x200 封面图
    canvas.width = outSize
    canvas.height = outSize
    const ctx = canvas.getContext('2d')
    ctx.drawImage(
      img,
      b.x * scale, b.y * scale, b.size * scale, b.size * scale,
      0, 0, outSize, outSize
    )
    const blob = await new Promise(r => canvas.toBlob(r, 'image/png'))
    const fd = new FormData()
    fd.append('root_id', coverTarget.value.id)
    fd.append('file', blob, 'cover.png')

    const resp = await fetch('/api/filespace/cover', { method: 'POST', body: fd })
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}))
      throw new Error(err.detail || `上传失败 (${resp.status})`)
    }
    const updated = await resp.json()
    const cres = await api(`/filespace/cover/${coverTarget.value.id}`)
    if (cres && cres.data) covers.value[coverTarget.value.id] = cres.data
    else delete covers.value[coverTarget.value.id]
    const idx = roots.value.findIndex(x => x.id === coverTarget.value.id)
    if (idx >= 0) roots.value[idx] = { ...roots.value[idx], ...updated }
    cropCancel()
    closeCover()
  } catch (e) {
    await alert('封面上传失败：' + e.message)
  } finally {
    coverUploading.value = false
  }
}

function cropCancel() {
  cropSrc.value = ''
  cropRawFile.value = null
  cropBox.value = { x: 0, y: 0, size: 120 }
}

function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)) }

// 调色板已移到后端 DEFAULT_PALETTE，前端直接用 r.default_color

// ===== 分类分组 =====
const CAT_ORDER = ['下载', '文件', '文件夹', '其它', '未分类']
const catPalette = [
  'linear-gradient(135deg,#ff7a59,#ffb259)', // 下载-橙
  'linear-gradient(135deg,#2bb6ff,#36e0c8)', // 文件-青蓝
  'linear-gradient(135deg,#6a5cff,#9b7bff)', // 文件夹-紫
  'linear-gradient(135deg,#34c759,#7be38a)', // 其它-绿
  'linear-gradient(135deg,#8b5cf6,#c084fc)', // 未分类-紫粉
]
function catColor(name, idx) {
  const i = CAT_ORDER.indexOf(name)
  return i >= 0 ? catPalette[i] : catPalette[(CAT_ORDER.length + idx) % catPalette.length]
}
const groups = computed(() => {
  const map = new Map()
  for (const r of roots.value) {
    if (!map.has(r.category)) map.set(r.category, [])
    map.get(r.category).push(r)
  }
  const names = []
  for (const c of CAT_ORDER) if (map.has(c)) names.push(c)
  for (const c of map.keys()) if (!CAT_ORDER.includes(c)) names.push(c)
  return names.map((name, idx) => ({
    name,
    color: catColor(name, idx),
    items: map.get(name),
  }))
})

async function loadRoots() {
  try {
    roots.value = await api('/filespace/roots')
    // 加载每个书签的封面（有 cover_path 的才请求 base64）
    await loadAllCovers()
  } catch (e) {
    console.error('加载目录失败：', e)
  }
}

// ===== 封面相关 =====
async function loadAllCovers() {
  const tasks = roots.value
    .filter(r => r.cover_path)
    .map(async r => {
      try {
        const res = await api(`/filespace/cover/${r.id}`)
        if (res && res.data) covers.value[r.id] = res.data
      } catch (e) { /* 忽略单个封面加载失败 */ }
    })
  await Promise.all(tasks)
}

function openCover(r) {
  coverTarget.value = r
  coverModal.value = true
}

function closeCover() {
  coverModal.value = false
  coverTarget.value = null
}

async function clearCover() {
  if (!coverTarget.value) return
  if (!(await confirm('确定清除封面，恢复默认色块吗？', { title: '清除确认' }))) return
  coverUploading.value = true
  try {
    const updated = await api(`/filespace/cover/${coverTarget.value.id}`, { method: 'DELETE' })
    delete covers.value[coverTarget.value.id]
    const idx = roots.value.findIndex(x => x.id === coverTarget.value.id)
    if (idx >= 0) roots.value[idx] = { ...roots.value[idx], ...updated }
    closeCover()
  } catch (e) {
    await alert('清除封面失败：' + e.message)
  } finally {
    coverUploading.value = false
  }
}

function openAdd() {
  editingRoot.value = null
  newName.value = ''
  newPath.value = ''
  newCategory.value = '下载'
  newNote.value = ''
  showForm.value = true
}

function editRoot(r) {
  editingRoot.value = r
  newName.value = r.name
  newPath.value = r.path
  newCategory.value = r.category || '未分类'
  newNote.value = r.note || ''
  showForm.value = true
}

function closeForm() {
  showForm.value = false
  editingRoot.value = null
  newName.value = ''
  newPath.value = ''
  newCategory.value = '下载'
  newNote.value = ''
}

async function saveRoot() {
  if (!newName.value) return
  try {
    if (editingRoot.value) {
      await api('/filespace/roots/' + editingRoot.value.id, 'PUT', {
        name: newName.value,
        path: newPath.value,
        category: newCategory.value || '未分类',
        note: newNote.value,
      })
    } else {
      if (!newPath.value) return
      await api('/filespace/roots', 'POST', {
        name: newName.value,
        path: newPath.value,
        category: newCategory.value || '未分类',
        note: newNote.value,
      })
    }
    closeForm()
    await loadRoots()
  } catch (e) {
    await alert('保存失败：' + (e.message || e))
  }
}

async function delRoot(r) {
  if (!(await confirm('删除目录「' + r.name + '」？', { title: '删除确认' }))) return
  try {
    await api('/filespace/roots/' + r.id, 'DELETE')
    await loadRoots()
  } catch (e) {
    await alert('删除失败：' + (e.message || e))
  }
}

function dragStart(gi, ii, ev) {
  dragFrom.value = { gi, ii }
  ev.dataTransfer.effectAllowed = 'move'
  ev.dataTransfer.setData('text/plain', String(ii))
}

function dragEnter(gi, ii) {
  if (dragFrom.value && dragFrom.value.gi === gi) dragOverIndex.value = ii
}

function dragLeave(gi, ii) {
  if (dragOverIndex.value === ii) dragOverIndex.value = null
}

async function drop(gi, ii) {
  dragOverIndex.value = null
  const from = dragFrom.value
  dragFrom.value = null
  if (!from || from.gi !== gi) return // 仅支持同分类内拖拽排序
  const gs = groups.value.map(g => ({ ...g, items: g.items.slice() }))
  const [moved] = gs[gi].items.splice(from.ii, 1)
  gs[gi].items.splice(ii, 0, moved)
  const flat = gs.flatMap(g => g.items)
  roots.value = flat
  try {
    await api('/filespace/roots/reorder', 'POST', { ids: flat.map(r => r.id) })
  } catch (e) {
    await alert('保存排序失败：' + (e.message || e))
    await loadRoots()
  }
}

async function enter(path) {
  view.value = 'dir'
  loading.value = true
  preview.value = null
  selected.value = null
  searchText.value = ''
  typeFilter.value = 'all'
  // 切换目录前，释放上一页所有视频缩略图持有的句柄，避免后端流长期不释放
  releaseAllVideoHandles()
  try {
    const d = await api('/filespace/list?path=' + encodeURIComponent(path))
    current.value = d.path
    parent.value = d.parent
    // 按扩展名兜底校正文件类型（兼容后端 classify 未把 md 等识别为 text 的旧版本）
    items.value = d.items.map(it => ({ ...it, type: itemTypeOf(it) }))
  } catch (e) {
    await alert('打开失败：' + (e.message || e))
  } finally {
    loading.value = false
  }
}

function goParent() {
  if (canGoUp.value) enter(parent.value)
}

function iconOf(t) {
  return {
    image: '🖼️', video: '🎬', audio: '🔊', text: '📄',
    pdf: '📕', office: '📊', other: '📦',
  }[t] || '📄'
}

function canPreview(t) {
  return ['image', 'text', 'video', 'audio', 'pdf'].includes(t)
}

const TEXT_EXTS = new Set([
  // 文档
  'md', 'txt', 'rtf',
  // 代码/脚本
  'json', 'js', 'ts', 'jsx', 'tsx', 'vue', 'py', 'rb', 'php', 'go', 'java',
  'c', 'cpp', 'h', 'hpp', 'cs', 'swift', 'kt', 'rs', 'sh', 'bash', 'zsh',
  'ps1', 'bat', 'cmd', 'vbs', 'lua', 'perl', 'pl', 'pm',
  // 样式/标记
  'css', 'scss', 'sass', 'less', 'html', 'htm', 'xml', 'xhtml', 'yaml', 'yml',
  'toml', 'ini', 'conf', 'cfg', 'config', 'properties',
  // 数据/日志
  'csv', 'tsv', 'log', 'sql',
])
function itemTypeOf(it) {
  if (it.is_dir) return 'dir'
  if (it.type && it.type !== 'other') return it.type
  const ext = it.name.split('.').pop().toLowerCase()
  if (TEXT_EXTS.has(ext)) return 'text'
  return it.type || 'other'
}

function extOf(n) {
  const i = n.lastIndexOf('.')
  return i > 0 ? n.slice(i) : ''
}
function extChanged(it) {
  if (!renameModal.value || !renameTarget.value || renameTarget.value.path !== it.path) return false
  return extOf(it.name).toLowerCase() !== extOf(draftName.value.trim()).toLowerCase()
}
function startRename(it) {
  // 重命名视频前，先释放所有 <video> 持有的文件句柄（preload=metadata 会持锁），
  // 同时关闭可能打开的预览抽屉/灯箱，避免 Chromium 占着文件导致后端 os.rename 失败。
  if (it.type === 'video') {
    releaseAllVideoHandles()
    if (preview.value && preview.value.path === it.path) preview.value = null
    // 如果当前正在灯箱里预览这个视频，也关掉灯箱以释放句柄
    if (lightboxVisible.value && lightboxItems.value.some(x => x.path === it.path)) {
      lightboxVisible.value = false
    }
  }
  renameTarget.value = it
  draftName.value = it.name
  renameModal.value = true
}
function cancelRename() {
  renameModal.value = false
  renameTarget.value = null
  draftName.value = ''
}
async function saveRename() {
  const it = renameTarget.value
  if (!it) return
  const newName = draftName.value.trim()
  if (!newName || newName === it.name) { cancelRename(); return }
  if (extChanged(it)) {
    if (!(await confirm(`新名称「${newName}」将改变文件扩展名（${extOf(it.name) || '无'} → ${extOf(newName) || '无'}），\n可能导致文件无法打开。确定要修改吗？`, { title: '重命名确认' }))) {
      return
    }
  }
  try {
    // 重命名前再兜底释放一次所有 video 句柄（缩略图重渲染或预览可能重新持锁）
    if (it.type === 'video') {
      releaseAllVideoHandles()
      if (lightboxVisible.value && lightboxItems.value.some(x => x.path === it.path)) {
        lightboxVisible.value = false
      }
    }
    const r = await api('/filespace/rename', 'POST', { old_path: it.path, new_name: newName })
    const idx = items.value.findIndex(x => x.path === it.path)
    if (idx >= 0) {
      items.value[idx] = { ...items.value[idx], name: r.name, path: r.new_path, type: r.type }
    }
    if (preview.value && preview.value.path === it.path) {
      preview.value.path = r.new_path
      preview.value.name = r.name
    }
    cancelRename()
  } catch (e) {
    await alert('重命名失败：' + (e.message || e))
  }
}

async function select(it) {
  selected.value = it
  preview.value = null
  try {
    if (it.type === 'image') {
      const r = await api('/filespace/image?path=' + encodeURIComponent(it.path))
      preview.value = { kind: 'image', name: it.name, src: r.data }
    } else if (it.type === 'text') {
      const r = await api('/filespace/text?path=' + encodeURIComponent(it.path))
      preview.value = { kind: 'text', name: it.name, path: it.path, text: r.text, editing: false, draft: '' }
    } else if (['video', 'audio', 'pdf'].includes(it.type)) {
      preview.value = {
        kind: it.type, name: it.name, type: it.type,
        stream: '/api/filespace/stream?path=' + encodeURIComponent(it.path),
      }
    } else {
      preview.value = { kind: 'other', name: it.name, type: it.type, path: it.path }
    }
  } catch (e) {
    await alert('预览失败：' + (e.message || e))
  }
}

// 列表视图点「预览」：图片/视频走灯箱；其余走弹窗预览
function previewInList(it) {
  if (['image', 'video'].includes(it.type)) {
    openLightbox(it)
  } else {
    select(it)
  }
}

async function openFile(path) {
  try {
    await api('/filespace/open?path=' + encodeURIComponent(path))
  } catch (e) {
    await alert('打开失败：' + (e.message || e))
  }
}

async function openParent(path) {
  try {
    await api('/filespace/open_parent?path=' + encodeURIComponent(path))
  } catch (e) {
    await alert('打开所在位置失败：' + (e.message || e))
  }
}

async function deleteItem(it) {
  if (it.is_dir) {
    if (!(await confirm(`删除文件夹「${it.name}」？\n该文件夹下的所有内容都会被删除，且不可恢复。`, { title: '删除确认' }))) return
  } else {
    if (!(await confirm(`删除文件「${it.name}」？`, { title: '删除确认' }))) return
  }
  try {
    await api('/filespace/delete?path=' + encodeURIComponent(it.path), 'DELETE')
    const idx = items.value.findIndex(x => x.path === it.path)
    if (idx >= 0) items.value.splice(idx, 1)
    if (preview.value && preview.value.path === it.path) preview.value = null
  } catch (e) {
    await alert('删除失败：' + (e.message || e))
  }
}

// ===== 缩略图视图 + 灯箱 =====
function streamUrl(path) {
  return '/api/filespace/stream?path=' + encodeURIComponent(path)
}
function lightboxItemsIndex(it) {
  return lightboxItems.value.findIndex(x => x.path === it.path)
}
function openLightbox(it) {
  if (it.is_dir) { enter(it.path); return }   // 文件夹直接进目录
  if (it.type === 'text') { select(it); return } // 文本文件走预览/编辑抽屉
  if (['image', 'video', 'audio', 'pdf'].includes(it.type)) {
    // 媒体/PDF 走灯箱
    const i = lightboxItemsIndex(it)
    lightboxIndex.value = i >= 0 ? i : 0
    focusedIndex.value = i >= 0 ? i : 0
    lightboxVisible.value = true
    return
  }
  // 其他类型（Excel/Office/压缩包/可执行文件等）直接用系统默认程序打开
  openFile(it.path)
}
function closeLightbox() { lightboxVisible.value = false }

function onThumbEnter(it) {
  hoveredItem.value = it
  if (!it.is_dir && lightboxItemsIndex(it) >= 0) {
    focusedIndex.value = lightboxItemsIndex(it)
  }
}
function onThumbLeave() {
  hoveredItem.value = null
}

// 缩略图下的所有非文件夹文件：拖拽到外部（桌面/剪映/其他软件）
// Electron 桌面版走原生 webContents.startDrag；纯浏览器环境兜底放一个 URL
function onNativeDragStart(e, it) {
  if (it.is_dir) return
  if (window.electronAPI && window.electronAPI.startFileDrag) {
    e.preventDefault() // 阻止默认 HTML 拖拽，交给主进程发起系统级文件拖出
    window.electronAPI.startFileDrag(it.path)
  } else {
    e.dataTransfer.effectAllowed = 'copy'
    e.dataTransfer.setData('text/uri-list', streamUrl(it.path))
    e.dataTransfer.setData('text/plain', it.name)
  }
}

// 全局空格键预览：缩略图视图下，鼠标悬停某项时按空格即可打开预览/灯箱
function onDocKey(e) {
  if (e.key !== ' ') return
  if (view.value !== 'dir' || dirViewMode.value !== 'thumb') return
  if (lightboxVisible.value || showForm.value || coverModal.value || preview.value) return
  const active = document.activeElement
  if (active && (active.tagName === 'INPUT' || active.tagName === 'TEXTAREA' || active.isContentEditable)) return
  const it = hoveredItem.value || lightboxItems.value[focusedIndex.value]
  if (!it || it.is_dir) return
  e.preventDefault()
  openLightbox(it)
}

// 缩略图网格键盘导航：方向键移动焦点，空格/回车在焦点项上打开灯箱
function onGridKey(e) {
  if (lightboxVisible.value) return
  const list = lightboxItems.value
  if (!list.length) return
  if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
    e.preventDefault(); focusedIndex.value = (focusedIndex.value + 1) % list.length
  } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
    e.preventDefault(); focusedIndex.value = (focusedIndex.value - 1 + list.length) % list.length
  } else if (e.key === ' ' || e.key === 'Enter') {
    e.preventDefault()
    const it = list[focusedIndex.value]
    if (it) openLightbox(it)
  }
}
// 视频缩略图：元数据加载后跳到 0.1s 取首帧作为封面
function onVideoMeta(e) {
  try { e.target.currentTime = 0.1 } catch (_) {}
}

// 重命名视频前释放所有 <video> 元素对文件的句柄。Chromium 在 preload=metadata 时会一直
// 持有文件句柄，不释放则后端 os.rename 会抛 PermissionError（"文件正被其他程序占用"）。
// 做法是把页面上所有 <video> 清空 src、清空 <source>、load()，彻底断开底层文件读取。
function releaseAllVideoHandles() {
  document.querySelectorAll('video').forEach(v => {
    try {
      v.pause()
      v.removeAttribute('src')
      v.srcObject = null
      v.querySelectorAll('source').forEach(s => s.removeAttribute('src'))
      if (typeof v.load === 'function') v.load()
    } catch (_) { /* 忽略单个释放失败，继续释放其余 */ }
  })
}

async function openRoot(r) {
  // 文件书签直接调用系统默认程序打开
  if (r.is_dir) {
    rootPath.value = r.path  // 记录书签根目录为导航最顶层
    enter(r.path)
    return
  }
  await openFile(r.path)
}

async function copyCurrentPath() {
  const text = current.value
  const store = useErrorStore()
  if (!text) {
    store.push('没有可复制的内容', { kind: 'warning' })
    return
  }
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text)
    } else {
      const ta = document.createElement('textarea')
      ta.value = text
      ta.style.position = 'fixed'
      ta.style.left = '-9999px'
      document.body.appendChild(ta)
      ta.focus()
      ta.select()
      const ok = document.execCommand('copy')
      document.body.removeChild(ta)
      if (!ok) throw new Error('execCommand copy failed')
    }
    store.push('路径已复制', { kind: 'success' })
  } catch (e) {
    store.push('复制失败：' + (e.message || e), { kind: 'error' })
  }
}

async function copyText() {
  if (!preview.value || preview.value.kind !== 'text') return
  const text = preview.value.editing ? preview.value.draft : preview.value.text
  const store = useErrorStore()
  if (!text) {
    store.push('没有可复制的内容', { kind: 'warning' })
    return
  }
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text)
    } else {
      const ta = document.createElement('textarea')
      ta.value = text
      ta.style.position = 'fixed'
      ta.style.left = '-9999px'
      document.body.appendChild(ta)
      ta.focus()
      ta.select()
      const ok = document.execCommand('copy')
      document.body.removeChild(ta)
      if (!ok) throw new Error('execCommand copy failed')
    }
    store.push('已复制', { kind: 'success' })
  } catch (e) {
    store.push('复制失败：' + (e.message || e), { kind: 'error' })
  }
}

function startEdit() {
  if (!preview.value || preview.value.kind !== 'text') return
  preview.value.editing = true
  preview.value.draft = preview.value.text
}

function cancelEdit() {
  if (!preview.value) return
  preview.value.editing = false
  preview.value.draft = ''
}

async function saveEdit() {
  if (!preview.value || preview.value.kind !== 'text') return
  saving.value = true
  try {
    await api('/filespace/save_text', 'POST', {
      path: preview.value.path,
      content: preview.value.draft,
    })
    preview.value.text = preview.value.draft
    preview.value.editing = false
    preview.value.draft = ''
    await alert('已保存')
  } catch (e) {
    await alert('保存失败：' + (e.message || e))
  } finally {
    saving.value = false
  }
}

function fmtSize(b) {
  if (b < 1024) return b + ' B'
  if (b < 1024 * 1024) return (b / 1024).toFixed(1) + ' KB'
  return (b / 1024 / 1024).toFixed(1) + ' MB'
}

function fmtTime(ts) {
  if (!ts) return '-'
  return new Date(ts * 1000).toLocaleString('zh-CN')
}

onMounted(() => {
  loadRoots()
  document.addEventListener('keydown', onDocKey)
})
onUnmounted(() => {
  document.removeEventListener('keydown', onDocKey)
  // 离开文件空间页面时，释放所有视频缩略图/灯箱/预览持有的句柄，
  // 避免后端 StreamingResponse 在客户端断开后仍长期持锁。
  releaseAllVideoHandles()
})
</script>

<style scoped>
.filespace { width: 100%; height: calc(100vh - 44px); display: flex; flex-direction: column; overflow: hidden; }
.fs-home-head { flex-shrink: 0; position: sticky; top: 0; z-index: 3; background: var(--sx-bg-page); }
.fs-home-scroll {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  padding-top: 16px;
  padding-bottom: 20px;
}
.fs-dir-head { flex-shrink: 0; }
.fs-dir-scroll {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  padding-top: 14px;
  padding-bottom: 20px;
}
.head { margin-bottom: 8px; display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.head h2 { font-size: 20px; margin: 0; }
.add-btn {
  background: var(--sx-btn-orange-bg); color: #fff; border: none; border-radius: 10px;
  padding: 9px 16px; font-size: 13px; font-weight: 600; cursor: pointer; flex-shrink: 0;
}
.add-btn:hover { background: var(--sx-btn-orange-hover); }
.sub { color: var(--sx-text-soft); font-size: 13px; margin: 0; line-height: 1.6; }
.dir-head { display: flex; align-items: center; gap: 12px; }
.crumbs-wrap { display: flex; align-items: center; gap: 6px; flex: 1; min-width: 0; }
.crumbs { font-size: 13px; color: var(--sx-text-emphasis); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; min-width: 0; }
.copy-path-btn {
  display: inline-flex; align-items: center; justify-content: center;
  width: 28px; height: 28px; padding: 0 !important; border-radius: 7px; flex-shrink: 0;
}
.copy-path-btn:hover { color: var(--sx-link); }
.copy-path-btn svg { width: 14px; height: 14px; display: block; }

/* 分类分组（首页） */
.cat-block { margin-bottom: 22px; }
.cat-head { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; }
.cat-dot { width: 12px; height: 12px; border-radius: 4px; flex-shrink: 0; }
.cat-name { font-weight: 700; font-size: 15px; color: var(--sx-text-strong); }
.cat-count {
  font-size: 12px; color: var(--sx-count-text); background: var(--sx-count-bg); border-radius: 10px;
  padding: 1px 9px; font-weight: 600;
}

/* 弹窗内分类 chips */
.cat-chips { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 8px; }
.cat-chip {
  background: var(--sx-chip-bg); color: var(--sx-chip-text); border: 1px solid var(--sx-border-strong); border-radius: 20px;
  padding: 5px 14px; font-size: 13px; cursor: pointer; transition: .15s;
}
.cat-chip:hover { background: var(--sx-accent-soft); border-color: var(--sx-border-hover); }
.cat-chip.on { background: var(--sx-accent); color: #fff; border-color: var(--sx-accent); }
.cat-chip.add { font-weight: 600; }
.cat-chip.add.on { background: var(--sx-tag-warn-text); border-color: var(--sx-tag-warn-text); color: #fff; }
.cat-custom-input { width: 100%; padding: 9px 11px; border: 1px solid var(--sx-border-strong); border-radius: 9px; font-size: 13px; }
.cat-custom-input:focus { border-color: var(--sx-tag-warn-text); outline: none; }
.cat-hint { margin: 6px 0 0; font-size: 12px; color: var(--sx-tag-warn-text); }

/* 卡片网格（首页）：自动填充，最少 116px，最大等分，填满可用宽度 */
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(116px, 1fr));
  gap: 14px;
}
.tile {
  position: relative;
  border-radius: 14px;
  width: 100%;
  background: #000;   /* 图片溢出兜底，保留 */
  cursor: grab;
  box-shadow: var(--sx-shadow-tile);
  transition: transform .15s, box-shadow .15s;
  overflow: hidden;
  user-select: none;
  display: flex;
  flex-direction: column;
}
.tile:active { cursor: grabbing; }
.tile:hover { transform: translateY(-3px); box-shadow: var(--sx-shadow-tile-hover); }

/* 色块/封面：在卡片上方，铺满宽度，1:1 正方形（与裁剪封面比例一致，零裁切显示） */
.tile-cover-wrap {
  width: 100%;
  aspect-ratio: 1 / 1;   /* 1:1，与裁剪封面比例一致 */
  flex: 1;
  overflow: hidden;
  background: var(--sx-bg-surface-2);
}
.tile-cover { width: 100%; height: 100%; }
.tile-cover-img { width: 100%; height: 100%; object-fit: cover; display: block; }

/* 底部信息条：黑色一行，平时只显示名称（居中）；
   hover 卡片时名称淡出、四个操作按钮同位浮入（参考应用启动器交互） */
.tile-bar {
  background: var(--sx-tile-bar-bg);
  position: relative;
  display: flex; align-items: center; justify-content: center;
  padding: 8px 10px;
  min-height: 34px;
  flex-shrink: 0;
}
.tile-name {
  width: 100%; min-width: 0;
  font-family: 'SimSun', '宋体', 'Songti SC', serif;
  font-weight: 700; font-size: 12px; line-height: 1.2;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  color: var(--sx-tile-bar-text); text-align: center;
  transition: opacity .15s ease;
}
.tile:hover .tile-name { opacity: 0; }
.tile-actions {
  position: absolute; inset: 0;
  display: flex; gap: 14px; align-items: center; justify-content: center;
  background: var(--sx-tile-bar-bg);  /* 与图标背景统一 */
  opacity: 0; transform: translateY(2px);
  transition: opacity .15s ease, transform .15s ease;
}
.tile:hover .tile-actions { opacity: 1; transform: translateY(0); }
.tile-actions button {
  width: auto; height: auto;
  border: none !important; background: transparent !important;
  border-radius: 0 !important;
  line-height: 1; cursor: pointer;
  padding: 0 !important; margin: 0;
  display: inline-flex; align-items: center; justify-content: center;
  opacity: .9; transition: opacity .12s, transform .12s;
}
.tile-actions button img { width: 18px; height: auto; object-fit: contain; }
.tile-actions button:hover { opacity: 1; transform: scale(1.15); }
.tile-actions .act-open { color: #3ddc84; }
.tile-actions .act-edit { color: var(--sx-text-muted); }
.tile-actions .act-set { color: #2bb6ff; }
.tile-actions .act-del { color: var(--sx-btn-danger-text); }

/* 添加卡片（虚线） */
.tile.drag-target {
  outline: 3px dashed var(--sx-accent);
  outline-offset: -4px;
  box-shadow: 0 0 0 4px var(--sx-accent-soft);
}

.empty { color: var(--sx-text-muted); text-align: center; padding: 36px 20px; }

/* 目录内部：工具栏（搜索 + 筛选） */
.dir-toolbar { display: flex; align-items: center; gap: 10px; margin-bottom: 0; flex-wrap: wrap; }
.search-box {
  width: 170px; min-width: 140px; flex-shrink: 0;
  padding: 7px 12px; border: 1px solid var(--sx-border-strong); border-radius: 20px;
  font-size: 12.5px; outline: none;
}
.search-box:focus { border-color: var(--sx-accent); }
.filter-chips { display: flex; gap: 7px; flex-wrap: wrap; }

/* 排序区：紧凑胶囊风格 */
.sort-box {
  display: flex; align-items: center; gap: 6px; flex-shrink: 0;
  margin-left: auto;
}
.sort-label { font-size: 12px; color: var(--sx-text-muted); font-weight: 600; }
.sort-select {
  padding: 6px 10px; font-size: 12.5px; border: 1px solid var(--sx-border-strong); border-radius: 20px;
  background: var(--sx-bg-surface); color: var(--sx-text-emphasis); outline: none; cursor: pointer;
}
.sort-select:focus { border-color: var(--sx-accent); }
.sort-dir {
  padding: 6px 11px !important; font-size: 12.5px; font-weight: 700;
  background: var(--sx-bg-surface) !important; color: var(--sx-accent) !important; border: 1px solid var(--sx-accent) !important;
  border-radius: 20px !important; min-width: 38px;
}
.sort-dir:hover { background: var(--sx-accent-soft) !important; }
.sort-folders {
  display: flex; align-items: center; gap: 5px; font-size: 12px; color: var(--sx-text-emphasis);
  cursor: pointer; white-space: nowrap; user-select: none;
  padding: 5px 10px; border-radius: 20px; border: 1px solid var(--sx-border-strong); background: none;
}
.sort-folders:has(input:checked) {
  background: var(--sx-accent-soft); border-color: var(--sx-accent); color: var(--sx-accent-strong);
}
.sort-folders input { cursor: pointer; margin: 0; }
.fchip {
  background: var(--sx-chip-bg); color: var(--sx-chip-text); border: 1px solid var(--sx-border-strong); border-radius: 20px;
  padding: 6px 14px; font-size: 12.5px; cursor: pointer; transition: .15s;
}
.fchip.on { background: var(--sx-accent); color: #fff; border-color: var(--sx-accent); }

/* 文件夹快捷入口：当前目录的子文件夹横向药丸，独立两行 */
.pin-tags { margin-bottom: 12px; width: 100%; flex-basis: 100%; }
.pin-row {
  display: flex; align-items: center; gap: 8px; flex-wrap: nowrap;
  width: 100%;
  min-height: 34px;
  padding: 6px 0;
  margin-bottom: 6px;
}
.pin-label {
  font-size: 12px; color: var(--sx-text-muted); font-weight: 600; flex-shrink: 0;
  letter-spacing: .3px;
  margin-right: auto;
}
.pin-text-btn {
  background: transparent; color: var(--sx-accent); border: none;
  font-size: 12px; cursor: pointer; padding: 4px 6px; border-radius: 6px;
  transition: .15s; white-space: nowrap;
}
.pin-text-btn:hover { background: var(--sx-accent-soft); }
.pin-text-btn.danger { color: var(--sx-text-muted); }
.pin-text-btn.danger:hover { background: var(--sx-btn-danger-bg); color: var(--sx-btn-danger-text); }
.pin-spacer { flex: 1 1 auto; }
.pin-chips {
  display: flex; align-items: center; flex-wrap: wrap;
  gap: 8px;
  padding: 6px 0 2px;
}
/* global.css 第 138 行给所有 button 加了渐变主色 !important；这里必须覆盖回来 */
.pin-tag {
  display: inline-flex; align-items: center; gap: 5px;
  background: var(--sx-bg-surface-2) !important; color: var(--sx-text-emphasis) !important; border: 1px solid var(--sx-border-soft) !important; border-radius: 8px !important;
  padding: 5px 8px 5px 10px !important; font-size: 12px !important; font-weight: 400 !important; cursor: pointer; transition: .15s;
  box-shadow: none !important; transform: none !important;
}
.pin-tag.active { background: var(--sx-accent) !important; color: #fff !important; border-color: var(--sx-accent) !important; }
.pin-tag.active .pin-folder { color: #fff !important; }
.pin-tag.active .pin-x { color: rgba(255, 255, 255, .75); }
.pin-tag.active .pin-x:hover { background: rgba(255, 255, 255, .18); color: #fff; }
.pin-tag:hover { background: var(--sx-accent-soft) !important; border-color: var(--sx-border-hover) !important; color: var(--sx-accent-strong) !important; }
.pin-tag:hover.active { background: var(--sx-accent-hover) !important; border-color: var(--sx-accent-hover) !important; }
.pin-folder {
  width: 14px; height: 14px; flex-shrink: 0; color: #ffb85c;
  display: block;
}
.pin-tag-name {
  max-width: 240px;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.pin-x {
  display: inline-flex; align-items: center; justify-content: center;
  width: 15px; height: 15px; border-radius: 4px;
  font-size: 10px; line-height: 1; color: var(--sx-text-muted); transition: .15s;
}
.pin-x:hover { background: var(--sx-btn-danger-bg); color: var(--sx-btn-danger-text); }
.pin-gen {
  background: transparent; color: var(--sx-accent); border: 1px dashed var(--sx-border-hover); border-radius: 8px;
  padding: 5px 12px; font-size: 12px; font-weight: 500; cursor: pointer; transition: .15s;
}
.pin-gen:hover { background: var(--sx-accent-soft); border-color: var(--sx-accent); }

/* 目录内部：列表视图 */
.dir-main { display: block; }
.dir-main .list { flex: 1; min-width: 480px; margin-bottom: 0; }
.empty-row { text-align: center; color: var(--sx-text-muted); padding: 24px 0; }

/* 分页器 */
.pager {
  display: flex; align-items: center; justify-content: space-between;
  gap: 12px; flex-wrap: wrap;
  margin-top: 14px; padding: 12px 14px;
  background: var(--sx-bg-surface); border: 1px solid var(--sx-border); border-radius: 14px;
  box-shadow: var(--sx-shadow-card);
}
.pager-info { font-size: 13px; color: var(--sx-text-soft); white-space: nowrap; }
.pager-ctrl { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.pg-btn, .pg-num {
  min-width: 36px; height: 36px; padding: 0 10px;
  border: 1px solid var(--sx-border-soft); background: var(--sx-bg-surface); color: var(--sx-text-strong);
  border-radius: 9px; font-size: 13px; cursor: pointer;
  transition: background .15s, border-color .15s, color .15s;
}
.pg-btn:hover:not(:disabled), .pg-num:hover:not(:disabled):not(.on) {
  background: var(--sx-row-hover); border-color: var(--sx-border-hover);
}
.pg-num.on { background: var(--sx-accent); border-color: var(--sx-accent); color: #fff; font-weight: 600; }
.pg-num.ellipsis { border: none; background: transparent; cursor: default; color: var(--sx-text-muted); min-width: 18px; padding: 0; }
.pg-btn:disabled, .pg-num:disabled { opacity: .45; cursor: not-allowed; }
.pager-size { font-size: 13px; color: var(--sx-text-soft); white-space: nowrap; display: flex; align-items: center; gap: 6px; }
.size-btns {
  display: inline-flex; align-items: center; gap: 4px;
}
.size-btn {
  min-width: 34px; height: 30px;
  padding: 0 8px; border-radius: 8px;
  border: 1px solid var(--sx-border-soft) !important;
  background: var(--sx-bg-surface) !important;
  color: var(--sx-text-emphasis) !important;
  font-size: 13px; cursor: pointer;
  display: inline-flex; align-items: center; justify-content: center;
  box-shadow: none !important;
  transition: .15s;
}
.size-btn:hover {
  border-color: var(--sx-border-hover) !important;
  background: var(--sx-row-hover) !important;
  transform: none !important;
}
.size-btn.on {
  border-color: var(--sx-accent) !important;
  background: var(--sx-accent) !important;
  color: #fff !important;
}
@media (max-width: 768px) {
  .pager { justify-content: center; }
  .pager-info { width: 100%; text-align: center; }
  .pg-btn { padding: 0 8px; }
}

/* 列表 / 预览（目录内部） */
.card {
  background: var(--sx-bg-surface); border: 1px solid var(--sx-border); border-radius: 14px;
  padding: 16px 18px; margin-bottom: 14px;
  box-shadow: var(--sx-shadow-card);
}
table { width: 100%; border-collapse: collapse; font-size: 13px; table-layout: auto; }
th, td { text-align: left; padding: 9px 10px; border-bottom: 1px solid var(--sx-border-faint); }
th { color: var(--sx-text-muted); font-weight: 600; }
.name-cell .fname { min-width: 0; }
tr.clickable { cursor: pointer; }
tr.clickable:hover { background: var(--sx-row-hover); }
tr.sel { background: var(--sx-row-selected-bg); }
tr.folder { font-weight: 600; color: var(--sx-text-emphasis); }
tr.folder .fname { color: var(--sx-accent); }
.name-cell {
  display: flex; align-items: center; gap: 8px;
}
.name-cell .type-ico { flex-shrink: 0; }
.name-cell .fname {
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.ops button { margin-right: 6px; }
.rename-input {
  width: 150px; padding: 4px 8px; font-size: 13px;
  border: 1px solid var(--sx-accent); border-radius: 7px; outline: none;
}
.rename-input.ext-danger { border-color: var(--sx-btn-danger-text); background: var(--sx-btn-danger-bg); }
.mini {
  padding: 4px 9px; font-size: 12px; border-radius: 7px; margin-left: 4px;
}

/* 预览/编辑弹窗 */
.preview-mask { z-index: 1100; }
.preview-modal {
  width: 50vw;
  max-width: none;
  min-width: 320px;
  max-height: 60vh;
  display: flex; flex-direction: column;
  padding: 0;
  overflow: hidden;
  background: var(--sx-bg-elevated);
  border-radius: var(--sx-radius-lg);
  box-shadow: var(--sx-shadow-pop);
}
.pv-head {
  display: flex; align-items: center; justify-content: space-between;
  gap: 12px;
  padding: 16px 20px;
  border-bottom: 1px solid var(--sx-border);
  flex-shrink: 0;
}
.pv-name { font-weight: 600; color: var(--sx-text-strong); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; flex: 1; }
.pv-actions { display: flex; gap: 8px; flex-shrink: 0; }
.pv-body {
  flex: 1; min-height: 0;
  padding: 16px 20px 20px;
  overflow: auto;
  background: var(--sx-bg-page);
}
.pv-img { display: block; max-width: 100%; max-height: 68vh; margin: 0 auto; border-radius: 10px; }
/* 文本编辑器：刻意深色底（亮/暗主题下都保持代码编辑器观感），不随主题翻转 */
.pv-text-wrap { min-height: 46vh; height: 100%; border-radius: 10px; border: 1px solid #3d4366; background: #1b1f3b; overflow: hidden; }
.pv-edit {
  width: 100%; min-height: 46vh; height: 100%;
  background: #1b1f3b; color: #e8eaf6;
  padding: 16px 18px; border: none; border-radius: 10px;
  font-size: 14px; line-height: 1.65;
  resize: vertical; outline: none; font-family: inherit;
}
.pv-media { width: 100%; max-height: 68vh; border-radius: 10px; }
.pv-pdf { width: 100%; height: 70vh; border: none; border-radius: 10px; }
.pv-hint { text-align: center; padding: 20px; color: var(--sx-text-soft); }
@media (max-width: 768px) {
  .preview-modal { width: 92vw; max-height: 60vh; }
  .pv-edit { min-height: 50vh; font-size: 13px; padding: 12px 14px; }
}

/* 弹窗 */
.mask {
  position: fixed; inset: 0; background: var(--sx-overlay);
  display: flex; align-items: center; justify-content: center; z-index: 1000;
}
.modal {
  background: var(--sx-bg-elevated); border-radius: var(--sx-radius-lg); padding: 24px 26px;
  width: 480px; max-width: 92vw; box-shadow: var(--sx-shadow-pop);
}
.modal h3 { font-size: 18px; margin: 0 0 16px; }
.form-row { margin-bottom: 14px; }
.form-row label { display: block; font-weight: 600; margin-bottom: 6px; color: var(--sx-text-emphasis); font-size: 13px; }
.form-row input { width: 100%; padding: 9px 11px; border: 1px solid var(--sx-border-strong); border-radius: 9px; font-size: 13px; }
.modal-actions { display: flex; gap: 10px; justify-content: flex-end; margin-top: 8px; }

/* 按钮 */
button {
  padding: 7px 14px; font-size: 13px; border-radius: 9px; cursor: pointer;
  background: var(--sx-accent); color: #fff; border: 1px solid var(--sx-accent); transition: .15s;
}
button:hover { background: var(--sx-accent-hover); }
button:disabled { opacity: .5; cursor: not-allowed; }
button.ghost { background: var(--sx-bg-surface); color: var(--sx-text-emphasis); border: 1px solid var(--sx-border-strong); }
button.ghost:hover { background: var(--sx-chip-bg); }

/* ===== 裁剪区域 ===== */
.crop-wrap {
  position: relative;
  width: 100%;
  max-height: 360px;
  overflow: hidden;
  background: var(--sx-crop-bg);
  border-radius: 10px;
  cursor: crosshair;
  user-select: none;
  touch-action: none;
}
.crop-img {
  display: block;
  max-width: 100%;
  max-height: 340px;
  margin: auto;
}
.crop-box {
  position: absolute;
  border: 2px solid #fff;
  box-shadow: 0 0 0 9999px rgba(0, 0, 0, .55);
  cursor: move;
  z-index: 2;
}
.crop-grid {
  position: absolute; inset: 0;
  background:
    linear-gradient(rgba(255,255,255,.15) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,.15) 1px, transparent 1px);
  background-size: 33.33% 33.33%;
  pointer-events: none;
}
.crop-handle {
  position: absolute;
  width: 12px; height: 12px;
  background: #fff;
  border: 2px solid var(--sx-accent);
  border-radius: 2px;
  z-index: 3;
}
.crop-handle.tl { top: -6px; left: -6px; cursor: nw-resize; }
.crop-handle.tr { top: -6px; right: -6px; cursor: ne-resize; }
.crop-handle.bl { bottom: -6px; left: -6px; cursor: sw-resize; }
.crop-handle.br { bottom: -6px; right: -6px; cursor: se-resize; }

/* ===== 视图切换（列表 / 缩略图） ===== */
.view-toggle {
  display: flex; flex-shrink: 0; align-items: center; gap: 6px;
}
.view-toggle button {
  display: inline-flex; align-items: center; justify-content: center;
  width: 34px; height: 34px;
  border-radius: 9px !important;
  border: 1px solid var(--sx-border-strong) !important;
  background: var(--sx-bg-surface); color: var(--sx-text-muted);
  padding: 0 !important; transition: .15s;
}
.view-toggle button .view-ico { width: 17px; height: 17px; }
.view-toggle button:hover { background: var(--sx-row-hover); color: var(--sx-text-emphasis); border-color: var(--sx-border-hover); }
.view-toggle button.on { background: var(--sx-text-strong); color: #fff; border-color: var(--sx-text-strong); }
.view-toggle button.on:hover { background: var(--sx-text-emphasis); }

/* 缩略图模式下目录主体恢复为整宽 */
.dir-main.thumb-mode { display: block; }

/* 缩略图网格 */
.thumb-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(186px, 1fr));
  gap: 14px;
  outline: none;
  padding: 2px;
}
.thumb-tile {
  position: relative;
  border: 1px solid var(--sx-border); border-radius: 12px; overflow: hidden;
  background: var(--sx-bg-surface); cursor: pointer; transition: .15s;
  display: flex; flex-direction: column;
}
.thumb-tile:hover { border-color: var(--sx-border-hover); box-shadow: var(--sx-shadow-tile-hover); transform: translateY(-2px); }
.thumb-tile.sel { border-color: var(--sx-accent); box-shadow: 0 0 0 3px var(--sx-accent-soft); }
.thumb-tile.folder { background: var(--sx-bg-surface-2); }
.thumb-cover {
  position: relative; width: 100%; aspect-ratio: 1 / 1;
  background: var(--sx-bg-page); overflow: hidden;
  display: flex; align-items: center; justify-content: center;
}
.thumb-img, .thumb-video { width: 100%; height: 100%; object-fit: cover; display: block; background: #000; }
.thumb-folder, .thumb-type { font-size: 44px; }
.play-badge {
  position: absolute; right: 8px; bottom: 8px;
  width: 30px; height: 30px; border-radius: 50%;
  background: rgba(0, 0, 0, .55); color: #fff;
  display: flex; align-items: center; justify-content: center; font-size: 12px;
}
.thumb-bar {
  display: flex; align-items: center; justify-content: space-between;
  gap: 2px;
  padding: 3px 4px;
  border-top: 1px solid var(--sx-border-faint);
  min-height: 26px;
}
.thumb-bar.editing {
  justify-content: flex-start;
}
.thumb-name {
  flex: 1; min-width: 0;
  font-size: 12px; color: var(--sx-text-emphasis);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.thumb-actions {
  display: none;
  flex-shrink: 0;
  align-items: center;
  gap: 1px;
}
.thumb-tile:hover .thumb-actions {
  display: flex;
}
.thumb-actions .ta-btn {
  border: none !important; background: transparent !important;
  color: var(--sx-text-strong) !important;
  width: 20px; height: 20px; padding: 0 !important;
  display: inline-flex; align-items: center; justify-content: center;
  border-radius: 4px;
  cursor: pointer;
  transition: .12s;
}
.thumb-actions .ta-btn svg { width: 13px; height: 13px; display: block; }
.thumb-actions .ta-btn:hover { background: var(--sx-accent-soft) !important; color: var(--sx-accent) !important; }
.thumb-actions .ta-btn.danger { color: var(--sx-btn-danger-text) !important; }
.thumb-actions .ta-btn.danger:hover { background: var(--sx-btn-danger-bg) !important; color: var(--sx-btn-danger-text) !important; }
.thumb-bar.editing .thumb-actions {
  display: flex;
}
.thumb-bar.editing .ta-btn {
  color: var(--sx-text-strong) !important;
}
.thumb-bar.editing .ta-btn.confirm:hover { color: var(--sx-tag-success-text) !important; background: var(--sx-tag-success-bg) !important; }
.thumb-bar.editing .ta-btn.danger:hover { color: var(--sx-btn-danger-text) !important; background: var(--sx-btn-danger-bg) !important; }
</style>
