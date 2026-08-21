<template>
  <div class="pl-page">
    <!-- 顶部标题栏 -->
    <header class="pl-head">
      <div class="pl-title">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
          <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
        </svg>
        <div>
          <h1>提示词库</h1>
          <p class="pl-sub">漫剧创作 prompt 库：按类型 / 分类 / 风格 / 工具整理，随时预览、编辑、一键复制</p>
        </div>
      </div>
      <div class="pl-actions">
        <button class="btn ghost" @click="toggleManage">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="M4 6h16M4 12h16M4 18h16"/></svg>
          {{ manageMode ? '退出管理' : '管理' }}
        </button>
        <button class="btn ghost" @click="triggerImportText" title="从 .txt/.md/.json/.docx 等外部文件提取提示词，作为【新增】提示词收藏进来（不会覆盖现有数据）">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="M12 3v12M7 8l5 5 5-5M5 21h14"/></svg>
          收藏外部提示词
        </button>
        <button class="btn primary" @click="openCreate">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="M12 5v14M5 12h14" /></svg>
          新建提示词
        </button>
        <input ref="importTextInput" type="file" accept=".txt,.md,.json,.doc,.docx" style="display:none" @change="onImportTextPicked" />
      </div>
    </header>

    <!-- 筛选栏 -->
    <section class="pl-filters">
      <div class="search-wrap">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/></svg>
        <input v-model="filters.keyword" class="search" type="text" placeholder="搜索标题 / 正文 / 分类 / 风格 / 工具…" @input="debouncedLoad" />
      </div>

      <div class="filter-row">
        <span class="filter-label">分类</span>
        <div class="chips">
          <button
            v-for="c in categoryOptions"
            :key="c"
            :class="['chip', { on: filters.category === c }]"
            @click="setCategory(c)"
          >{{ c }}</button>
        </div>
      </div>

      <div class="filter-row inline">
        <label class="filter-label">类型</label>
        <select v-model="filters.outputType" class="mini-select" @change="loadList">
          <option v-for="o in outputOptions" :key="o" :value="o">{{ o }}</option>
        </select>
        <label class="filter-label">风格</label>
        <select v-model="filters.style" class="mini-select" @change="loadList">
          <option value="">全部风格</option>
          <option v-for="s in styleFilterOptions" :key="s" :value="s">{{ s }}</option>
        </select>
        <label class="filter-label">工具</label>
        <select v-model="filters.tool" class="mini-select" @change="loadList">
          <option value="">全部工具</option>
          <option v-for="t in toolFilterOptions" :key="t" :value="t">{{ t }}</option>
        </select>
        <label class="filter-label">作者</label>
        <select v-model="filters.owner" class="mini-select" @change="loadList">
          <option v-for="o in authorFilterOptions" :key="o" :value="o === '全部作者' ? '' : o">{{ o }}</option>
        </select>
        <span class="count">共 {{ list.length }} 条</span>
      </div>
    </section>

    <!-- 管理工具条（管理态显示） -->
    <section v-if="manageMode" class="pl-manage-bar">
      <span class="mb-info">已选 {{ selectedIds().length }} / {{ list.length }} 条</span>
      <button class="btn ghost sm" @click="selectAll">全选</button>
      <button class="btn ghost sm" @click="clearSelect">取消全选</button>
      <input ref="importInput" id="pl-import-input" type="file" accept=".zip" hidden @change="onImportPicked" />
      <label for="pl-import-input" class="btn ghost sm" title="导入本系统导出的 .zip 备份包，用于【恢复/合并】提示词与其图片（需先通过「导出选中」导出过）">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="M12 3v12M7 8l5 5 5-5M5 21h14"/></svg>
        恢复备份
      </label>
      <button class="btn ghost sm" @click="exportSelected" :disabled="!selectedIds().length || exporting">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="M12 3v12M7 8l5 5 5-5M5 21h14"/></svg>
        导出选中
      </button>
      <button class="btn danger sm" @click="batchDelete" :disabled="!selectedIds().length">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
        批量删除
      </button>
    </section>

    <!-- 卡片列表 -->
    <div class="pl-scroll">
      <section v-if="list.length" class="pl-grid">
        <article
          v-for="(item, idx) in list"
          :key="item.id"
          class="pl-card"
          :class="{ dragging: dragIndex === idx, 'drag-over': dragOverIndex === idx }"
          @dragenter.prevent="onDragEnter(idx)"
          @dragover.prevent="onDragOver($event)"
          @drop.prevent="onDrop(idx)"
          @dragend="onDragEnd"
          @click="manageMode ? toggleSelect(item.id) : openDetail(item)"
        >
          <div class="card-top">
            <label v-if="manageMode" class="pl-check" @click.stop="toggleSelect(item.id)">
              <input type="checkbox" :checked="isSelected(item.id)" @click.stop />
            </label>
            <span v-if="!manageMode" class="pl-handle" title="拖拽排序" draggable="true" @click.stop @dragstart="onDragStart(idx, $event)">⠿</span>
            <h3 class="card-title" :title="item.title">{{ item.title }}</h3>
            <span class="badge ot" :class="otClass(item.output_type)">{{ otShort(item.output_type) }}</span>
            <div v-if="!manageMode" class="card-more-wrap" @click.stop>
              <button class="card-more-btn" :class="{ open: cardMoreOpen === item.id }" title="更多操作" @click="toggleCardMore(item)">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><circle cx="5" cy="12" r="2"/><circle cx="12" cy="12" r="2"/><circle cx="19" cy="12" r="2"/></svg>
              </button>
              <div v-if="cardMoreOpen === item.id" class="card-more" @click.stop>
                <button class="card-more-item" @click="onCardMore(item, 'test')">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 3v4M3 5h4M6 17v4M4 19h4M13 3l2.5 6.5L22 12l-6.5 2.5L13 21l-2.5-6.5L4 12l6.5-2.5z"/></svg> 测试
                </button>
                <button class="card-more-item" @click="onCardMore(item, 'optimize')">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9z"/></svg> 优化
                </button>
                <button class="card-more-item goto" @click="onCardMore(item, 'gen')">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14M13 6l6 6-6 6"/></svg> {{ genActionLabel(item.output_type) }}
                </button>
              </div>
            </div>
          </div>
          <div class="card-meta">
            <span class="badge src">{{ item.owner_name || '我' }}</span>
            <span class="badge c1">{{ item.category }}</span>
            <span v-for="t in splitTags(item.tags)" :key="t" :class="['tag', tagClass(t, item.tags)]">#{{ t }}</span>
          </div>
          <p class="card-preview">{{ previewText(item.content) }}</p>
          <div v-if="!manageMode" class="card-ops" @click.stop>
            <button class="op" title="一键复制" @click="copy(item)">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
              复制
            </button>
            <button class="op" title="编辑" @click="openEdit(item)">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.12 2.12 0 0 1 3 3L12 15l-4 1 1-4z"/></svg>
              编辑
            </button>
            <button class="op danger" title="删除" @click="remove(item)">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
              删除
            </button>
          </div>
        </article>
      </section>

      <div v-else class="empty">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>
        <p>还没有提示词，点右上角「新建提示词」开始收藏。</p>
      </div>
    </div>

    <!-- 编辑/新建弹窗 -->
    <div v-if="showEditor" class="modal-mask" @click.self="closeEditor">
      <div class="modal">
        <div class="modal-head">
          <h2>{{ editing.id ? '编辑提示词' : '新建提示词' }}</h2>
          <button class="x" @click="closeEditor">✕</button>
        </div>
        <div class="modal-body">
          <div class="ai-gen-block">
            <div class="ai-gen-title">🤖 AI 帮我写一条</div>
            <div class="ai-gen-row">
              <textarea v-model="aiIntent" class="ai-gen-input" rows="2" placeholder="描述你想生成的提示词意图，例如：古风少女特写镜头，3D国风，用于即梦"></textarea>
              <button class="btn primary sm" :disabled="aiGenerating" @click="aiGenerate">
                <span v-if="aiGenerating" class="mini-spin"></span>
                {{ aiGenerating ? '生成中…' : '生成' }}
              </button>
            </div>
            <div class="ai-gen-hint">AI 会按提示词库规则补全标题/正文/分类/类型/风格/工具，生成后自动填入下方，你再微调后保存。</div>
          </div>
          <label class="fld">
            <span>标题 *</span>
            <input v-model="editing.title" type="text" placeholder="如：小说转剧本-复杂版" />
          </label>

          <label class="fld">
            <span>作者 *</span>
            <input v-model="editing.owner_name" type="text" placeholder="如：苏小沫" />
          </label>

          <label class="fld">
            <span>分类</span>
            <select v-model="editing.category" class="category-select">
              <option v-for="c in formCategoryOptions" :key="c" :value="c">{{ c }}</option>
              <option value="__custom__">+ 新建分类</option>
            </select>
            <input v-if="editing.category === '__custom__'" v-model="customCategory" type="text" placeholder="输入新分类名称" />
          </label>

          <div class="fld-row">
            <label class="fld">
              <span>类型</span>
              <select v-model="editing.output_type">
              <option>文本</option>
              <option>图片</option>
              <option>音频</option>
              <option>视频</option>
              <option>其他</option>
              </select>
            </label>
          </div>

          <div class="fld-row">
            <label class="fld">
              <span>风格</span>
              <select v-model="editing.style" class="category-select">
                <option v-for="s in STYLE_OPTIONS" :key="s" :value="s">{{ s }}</option>
                <option value="__custom__">+ 新建风格</option>
              </select>
              <input v-if="editing.style === '__custom__'" v-model="customStyle" type="text" placeholder="输入新风格名称" />
            </label>
            <label class="fld">
              <span>工具</span>
              <select v-model="editing.tool" class="category-select">
                <option v-for="t in TOOL_OPTIONS" :key="t" :value="t">{{ t }}</option>
                <option value="__custom__">+ 新建工具</option>
              </select>
              <input v-if="editing.tool === '__custom__'" v-model="customTool" type="text" placeholder="输入新工具名称" />
            </label>
          </div>

          <label class="fld">
            <span>prompt 正文</span>
            <textarea v-model="editing.content" rows="10" placeholder="粘贴或编写你的 prompt 内容…"></textarea>
          </label>

          <div class="fld">
            <span>模版图（生图参考，可多张）</span>
            <div class="img-grid">
              <div v-for="(img, i) in editing.images" :key="i" class="img-cell">
                <img :src="imgUrl(img)" alt="" @error="onImgError" />
                <span v-if="i === 0" class="cover-badge" title="当前首图">首图</span>
                <button v-else class="set-cover-edit" type="button" @click="setCoverEdit(img)" title="设为首图">设为首图</button>
                <button class="img-del" type="button" @click="removeImage(img)" title="删除图片">✕</button>
              </div>
            </div>
            <div class="img-upload">
              <input ref="imgInput" type="file" accept="image/*" multiple hidden @change="onImgPicked" />
              <button class="btn ghost sm" type="button" @click="imgInput?.click()">+ 选择图片</button>
              <button v-if="editing.id" class="btn primary sm" type="button" :disabled="!pendingImgs.length" @click="uploadImages">上传 {{ pendingImgs.length || '' }}</button>
            </div>
            <div v-if="pendingImgs.length" class="img-pending">
              <img v-for="(p, i) in pendingImgs" :key="i" :src="p.preview" class="pending-thumb" alt="" />
            </div>
            <p v-if="!editing.id" class="img-hint">保存时将自动上传所选图片。</p>
            <p v-else class="img-hint">选择图片后点「上传」即时保存，或保存后继续管理。</p>
          </div>

          <div v-if="editing.category === 'skills'" class="fld">
            <span>附加文件（skills）</span>
            <div v-if="editing.id && attachments.length" class="att-list">
              <div v-for="a in attachments" :key="a.id" class="att-item">
                <span class="att-name" :title="a.filename">{{ a.filename }}</span>
                <span class="att-size">{{ fmtSize(a.filesize) }}</span>
                <a class="att-dl" :href="`/api/prompt-library/${editing.id}/attachments/${a.id}/download`" target="_blank">下载</a>
                <button class="att-del" type="button" @click="removeAttachment(a)">删除</button>
              </div>
            </div>
            <div class="att-upload">
              <input ref="attInput" type="file" multiple hidden @change="onAttPicked" />
              <button class="btn ghost sm" type="button" @click="attInput?.click()">+ 选择文件</button>
              <span class="att-tip">md / txt / docx 读取后填入正文；压缩包（zip / 7z / rar / tar）保存为附件。</span>
            </div>
            <div v-if="attPending.length" class="att-pending">
              <div v-for="(p, i) in attPending" :key="i" class="att-pending-item">
                <span>{{ p.filename }}</span>
                <span class="att-pending-type">{{ p.mode === 'text' ? '已填入正文' : '压缩包（保存后上传）' }}</span>
              </div>
            </div>
          </div>
        </div>
        <div class="modal-foot">
          <button class="btn ghost" @click="closeEditor">取消</button>
          <button class="btn primary" :disabled="saving" @click="save">{{ saving ? '保存中…' : '保存' }}</button>
        </div>
      </div>
    </div>

    <!-- 详情预览弹窗 -->
    <div v-if="showDetail" class="modal-mask" @click.self="closeDetail" @mousedown="onMaskMouseDown">
      <div class="modal">
        <div class="modal-head">
          <h2>{{ detail.title }}</h2>
          <div class="head-tools">
            <button class="op" @click="editDetail">编辑</button>
            <button class="op danger" @click="removeDetail">删除</button>
            <button class="op" @click="runTest(detail)">测试</button>
            <button class="x" @click="closeDetail">✕</button>
          </div>
        </div>
        <div class="modal-body">
          <div class="detail-meta">创建时间 {{ detail.created_at }} · 更新时间 {{ detail.updated_at }}</div>
          <div v-if="detail.category === 'skills' && detail.source_file" class="detail-locpath">
            <span class="loc-label">本地目录</span>
            <code>{{ detail.source_file }}</code>
            <span class="loc-note">（固定存于 workspace 数据根下，可手动打开查看文件）</span>
          </div>
          <div class="detail-head-row">
            <span class="badge c1">{{ detail.category }}</span>
            <span class="badge ot" :class="otClass(detail.output_type)">{{ otShort(detail.output_type) }}</span>
            <template v-if="detail.tags">
              <span v-for="t in splitTags(detail.tags)" :key="t" :class="['tag', tagClass(t, detail.tags)]">#{{ t }}</span>
            </template>
          </div>
          <template v-if="detail.images && detail.images.length">
            <div class="detail-divider"></div>
            <div class="detail-section-title">参考图</div>
            <img :src="imgUrl(detail.images[0])" class="detail-img img-first" @click="openLightbox(detail.images[0], detail.images)" alt="" @error="onImgError" />
            <div v-if="detail.images.length > 1" class="detail-thumbs">
              <div v-for="(img, i) in detail.images.slice(1)" :key="i" class="thumb-wrap">
                <img :src="imgUrl(img)" class="detail-thumb" @click="openLightbox(img, detail.images)" alt="" @error="onImgError" />
                <button class="set-first" @click="setFirst(img)" title="点击设为首图">设为首图</button>
              </div>
            </div>
          </template>
          <div class="detail-divider"></div>
          <div class="detail-section-row">
            <div class="detail-section-title">Prompt 正文</div>
            <div class="row-actions">
              <button v-if="selMenu.visible" class="btn sm sel-copy" @click="copySelection">复制选中</button>
              <button class="btn primary sm" @click="copyDetail">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
                <span v-if="detailCopied">已复制 ✓</span><span v-else>一键复制prompt文本</span>
              </button>
            </div>
          </div>
          <pre class="detail-content" @mouseup="onDetailSelect">{{ detail.content }}</pre>
          <div v-if="testing || testResult || testError" class="detail-test">
            <div class="detail-test-head">
              <span>测试结果{{ detail.output_type === '文本' ? '' : '（当前为文本预览，配置即梦 / 可灵后可真实生成图 / 视频）' }}</span>
              <button v-if="testResult || testError" class="link-btn" @click="clearTest">清除</button>
            </div>
            <pre v-if="testResult" class="detail-content test-out">{{ testResult }}</pre>
            <p v-if="testError" class="test-err">{{ testError }}</p>
            <p v-if="testing" class="test-loading">生成中…</p>
          </div>
        </div>
      </div>
    </div>

    <!-- 图片灯箱（统一使用默认灯箱组件，含关闭/前后切换/键盘操作） -->
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

    <!-- 导出中遮罩：导出较慢，提示用户耐心等待、勿重复点击 -->
    <transition name="fade">
      <div v-if="exporting" class="export-mask">
        <div class="export-box">
          <div class="spinner"></div>
          <div class="export-text">{{ exportMsg }}</div>
          <div class="export-sub">导出需读取并打包每条提示词的正文、图片等较多文件，耗时随图片数量增加，请勿重复点击，请耐心等待…</div>
        </div>
      </div>
    </transition>

    <!-- 导入中遮罩：导入需解包并写入提示词正文与图片，耗时随图片数量增加，提示用户耐心等待、勿重复点击 -->
    <transition name="fade">
      <div v-if="importingZip" class="export-mask">
        <div class="export-box">
          <div class="spinner"></div>
          <div class="export-text">正在导入备份，请耐心等待…</div>
          <div class="export-sub">导入需解包并写入每条提示词的正文、图片等文件，耗时随图片数量增加，请勿重复点击，请耐心等待…</div>
        </div>
      </div>
    </transition>

    <!-- 导入外部提示词：预览 + 拆分策略 + 草稿 + 批量新建 -->
    <transition name="fade">
      <div v-if="importTextOpen" class="modal-mask" @click.self="closeImportText">
        <div class="modal import-modal">
          <header class="modal-head">
            <div>
              <h3>导入外部提示词</h3>
              <p class="modal-sub">{{ importFileName || '' }}</p>
            </div>
            <button class="icon-btn" @click="closeImportText">✕</button>
          </header>

          <!-- 步骤一：预览 + 拆分策略 -->
          <div v-if="importStep === 'preview'" class="modal-body">
            <label class="filter-label">原文预览（可手动编辑后再拆分）</label>
            <textarea v-model="importRaw" class="import-raw" spellcheck="false"></textarea>
            <div class="import-row">
              <span class="filter-label">拆分方式</span>
              <select v-model="importStrategy" class="mini-select">
                <optgroup label="单条">
                  <option v-for="s in importStrategiesSingle" :key="s.value" :value="s.value">{{ s.label }}</option>
                </optgroup>
                <optgroup label="多条">
                  <option v-for="s in importStrategiesMulti" :key="s.value" :value="s.value">{{ s.label }}</option>
                </optgroup>
              </select>
              <span class="import-count">预计拆分 {{ importPreviewCount }} 条</span>
            </div>
            <div class="import-example">{{ currentStrategyExample }}</div>
            <div class="section-divider"><span>AI 整理</span></div>
            <div class="import-ai-config">
              <!-- 第 1 行：名称选 -->
              <div class="ai-rule-line">
                <span class="filter-label">名称</span>
                <select ref="aiRuleSelectRef" v-model="aiRuleId" class="mini-select" @change="onAiRuleChange">
                  <option v-for="r in aiRules" :key="r.id" :value="r.id">{{ r.name }}</option>
                </select>
              </div>
              <!-- 第 2 行：角色和功能 -->
              <div v-if="selectedAiRule" class="ai-rule-line">
                <span class="filter-label">角色 / 功能</span>
                <div class="ai-tags">
                  <span class="ai-tag role"><em>角色</em>{{ roleLabel(selectedAiRule.role) }}</span>
                  <span class="ai-tag func"><em>功能</em>{{ selectedAiRule.function_key || '全部功能' }}</span>
                </div>
              </div>
              <!-- 第 3 行：记住状态 -->
              <div v-if="selectedAiRule" class="ai-rule-line ai-rule-foot">
                <span class="remembered-text">✓ 已记住：<b>{{ selectedAiRule.name }}</b></span>
              </div>
            </div>
            <div v-if="!selectedAiRule" class="import-ai-remembered muted">
              提示词库下还没有规则，请到「AI 调用规则」页新建
            </div>
            <div class="import-ai">
              <button class="btn ghost sm" :disabled="aiAnalyzing || !importRaw.trim()" @click="aiAnalyze">
                <span v-if="aiAnalyzing" class="mini-spin dark"></span>
                🤖 AI 分析整理
              </button>
              <span class="import-ai-tip">AI 按所选规则把原文拆成多条、自动归类（运镜/角色）并配工具，结果进入草稿表可再微调。</span>
            </div>
          </div>

          <!-- 步骤二：草稿表 -->
          <div v-else class="modal-body">
            <div class="import-draft-head">
              <span>草稿预览（共 {{ importDrafts.length }} 条，可逐项修改）</span>
              <div class="draft-head-actions author-row">
                <span class="author-inline">
                  作者 <input v-model="importOwner" class="owner-input" placeholder="作者" />
                </span>
                <button class="btn ghost sm" @click="openBatchSet('owner')">批量设作者</button>
              </div>
            </div>
            <div class="draft-batch-bar">
              <span class="batch-label">批量设置：</span>
              <button class="btn ghost sm" @click="openBatchSet('category')">分类</button>
              <button class="btn ghost sm" @click="openBatchSet('output_type')">类型</button>
              <button class="btn ghost sm" @click="openBatchSet('style')">风格</button>
              <button class="btn ghost sm" @click="openBatchSet('tool')">工具</button>
              <button class="btn ghost sm" @click="addDraftRow">+ 新增一行</button>
            </div>

            <!-- 批量设置弹窗（替代桌面端无效的 window.prompt） -->
            <div v-if="batchOpen" class="modal-mask batch-mask" @click.self="closeBatchSet">
              <div class="modal batch-modal">
                <header class="modal-head">
                  <div>
                    <h3>批量设置{{ batchLabel }}</h3>
                  </div>
                  <button class="icon-btn" @click="closeBatchSet">✕</button>
                </header>
                <div class="modal-body">
                  <select v-if="batchMode === 'field'" v-model="batchValue" class="mini-select batch-select">
                    <option value="">请选择{{ batchLabel }}</option>
                    <option v-for="o in batchOptions" :key="o" :value="o">{{ o }}</option>
                  </select>
                  <input v-else v-model="batchValue" class="owner-input batch-input" :placeholder="`请输入${batchLabel}`" />
                </div>
                <footer class="modal-foot">
                  <button class="btn ghost" @click="closeBatchSet">取消</button>
                  <button class="btn primary" @click="applyBatchSet">确定</button>
                </footer>
              </div>
            </div>
            <div class="import-drafts">
              <div v-for="(d, i) in importDrafts" :key="i" class="draft-row" :class="{ 'draft-anchor': draftAnchor === i, 'draft-dup': d._dup }">
                <div class="draft-idx">{{ i + 1 }}</div>
                <div class="draft-fields">
                  <div class="draft-line title-line">
                    <input v-model="d.title" class="draft-title" placeholder="标题" @input="d._dup = false" />
                    <span v-if="d._dup" class="dup-tag">⚠ 与库中重名，改名后重试</span>
                  </div>
                  <div class="draft-line meta-line">
                    <select v-model="d.category" class="mini-select">
                      <option v-for="c in formCategoryOptions" :key="c" :value="c">{{ c }}</option>
                    </select>
                    <select v-model="d.output_type" class="mini-select">
                      <option v-for="o in outputOptions.filter(x => x !== '全部')" :key="o" :value="o">{{ o }}</option>
                    </select>
                    <select v-model="d.style" class="mini-select">
                      <option v-for="s in STYLE_OPTIONS" :key="s" :value="s">{{ s }}</option>
                    </select>
                    <select v-model="d.tool" class="mini-select">
                      <option v-for="t in TOOL_OPTIONS" :key="t" :value="t">{{ t }}</option>
                    </select>
                    <button class="icon-btn" @click="insertDraftRow(i)" title="在当前行下方插入">＋</button>
                    <button class="del-btn" type="button" @click="removeDraftRow(i)">🗑 删除</button>
                  </div>
                  <textarea v-model="d.content" class="draft-content" placeholder="提示词正文（默认放到 prompt）" spellcheck="false"></textarea>
                  <div class="draft-img">
                    <input :ref="el => draftImgInputs[i] = el" type="file" accept="image/*" multiple hidden @change="onDraftImgPicked(d, i, $event)" />
                    <button class="btn ghost xs" type="button" @click="draftImgInputs[i] && draftImgInputs[i].click()">+ 图片</button>
                    <span v-for="(p, j) in d.images" :key="j" class="draft-img-thumb">
                      <img :src="p.preview" alt="" />
                      <button class="x" type="button" @click="d.images.splice(j, 1)">✕</button>
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <footer class="modal-foot">
            <button class="btn ghost" @click="closeImportText">取消</button>
            <button v-if="importStep === 'preview'" class="btn primary" @click="buildDrafts">预览草稿并新建</button>
            <template v-else>
              <button class="btn ghost" @click="importStep = 'preview'">返回</button>
              <button class="btn primary" :disabled="!importDrafts.length || importing" @click="submitImportDrafts">批量新建（{{ importDrafts.length }} 条）</button>
            </template>
          </footer>
        </div>
      </div>
    </transition>

    <!-- 卡片测试/优化/生成：外部平台提示弹窗（用户手动关闭，含一键复制） -->
    <transition name="fade">
      <div v-if="genHintOpen" class="modal-mask" @click.self="genHintOpen = false">
        <div class="modal gen-hint-modal">
          <header class="modal-head">
            <h3>{{ genHintItem ? genHintItem.title : '' }} · {{ genHintAction }}</h3>
            <button class="icon-btn" @click="genHintOpen = false">✕</button>
          </header>
          <div class="modal-body">
            <p class="gen-hint-text">{{ genHintText }}</p>
          </div>
          <footer class="modal-foot">
            <button class="btn primary" @click="copyGenHint">复制提示词</button>
            <button class="btn ghost" @click="genHintOpen = false">关闭</button>
          </footer>
        </div>
      </div>
    </transition>

  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { api, apiUpload } from '../common/http.js'
import { confirm } from '../common/useConfirm.js'
import { useAuthStore } from '../login/auth-store.js'
import { askApi } from '../chat/ai-api.js'
import MediaLightbox from '../filespace/MediaLightbox.vue'
import JSZip from 'jszip'

const auth = useAuthStore()
const list = ref([])
const meta = reactive({ categories: [], output_types: [], all_tags: [], owners: [] })
const filters = reactive({ keyword: '', category: '全部', outputType: '全部', style: '', tool: '', owner: '' })

const defaultCategories = ['全部', 'skills', '去重', '改写', '剧本', '角色', '场景', '道具', '分镜', '打斗', '特效', '服装', '运镜', '法术', '发型', '萌宠', '情绪', '站位', '反推', '台词', '其他']
const outputOptions = ref(['全部', '文本', '图片', '音频', '视频', '其他'])
const STYLE_OPTIONS = ['通用风格', '3D国风', '3D仿真人', '2D防真人', '2D水墨', '二次元', 'Q版', '漫画', '科幻', '赛博朋克', '手绘', '彩绘']
const TOOL_OPTIONS = ['通用工具', 'DeepSeek', 'ChatGPT', 'GPT Image 2', 'Nano Banana', 'MidJourney', 'Kimi', 'GLM', '即梦', '可灵', '海螺', '千问', '豆包']

// ---------- 提示词库 AI 助手：专属规则词表 + 系统提示词 ----------
const AI_CATEGORY_TABLE = '角色、场景、运镜、光影、服饰、道具、情绪、其他'
const AI_STYLE_TABLE = STYLE_OPTIONS.join('、')
const AI_TOOL_TABLE = TOOL_OPTIONS.join('、')
const AI_OUTPUT_TABLE = '文本、图片、音频、视频、其他'

// 规则A：根据创作意图补全为一条完整提示词
const AI_SYS_RULE_A = `你是一个「漫剧创作提示词库」的 AI 助手。用户会给你一段创作意图（可能很短，例如"写一条古风少女特写镜头"），请补全为一条结构完整的提示词。
【输出格式】严格输出一个 JSON 对象，不要任何解释、不要使用 markdown 代码块包裹，字段如下：
{
  "title": "提示词标题（简洁，不超过 20 字）",
  "content": "提示词正文（完整、可直接使用，包含画面/镜头/风格等要素）",
  "category": "只能从[${AI_CATEGORY_TABLE}]选一个；运镜/镜头类必须选『运镜』",
  "output_type": "只能从[${AI_OUTPUT_TABLE}]选一个",
  "style": "只能从[${AI_STYLE_TABLE}]选一个",
  "tool": "只能从[${AI_TOOL_TABLE}]选一个；运镜/镜头类优先选『可灵』『即梦』『海螺』之一",
  "note": "可选的补充说明（默认空字符串）",
  "tags": "可选，其他自由标签，逗号分隔（默认空字符串）"
}
【硬约束】category / output_type / style / tool 必须严格使用上述词表里的字面值，不得自造不在词表中的值；运镜类必须 category=运镜 且 tool 为可灵/即梦/海螺。只输出 JSON。`

// 规则B：把零散多要点文本按语义拆成多条独立提示词
const AI_SYS_RULE_B = `你是一个「漫剧创作提示词库」的 AI 整理助手。用户会给你一段零散、可能包含多条提示词的原始文本（如多个运镜技巧、多个角色设定混在一起）。请按语义拆分成多条独立的提示词，每条都补全字段。
【输出格式】严格输出一个 JSON 数组，每一项是一个对象：
{
  "title": "提示词标题（简洁，不超过 20 字）",
  "content": "提示词正文（完整、可直接使用）",
  "category": "只能从[${AI_CATEGORY_TABLE}]选一个；运镜/镜头类必须选『运镜』",
  "output_type": "只能从[${AI_OUTPUT_TABLE}]选一个",
  "style": "只能从[${AI_STYLE_TABLE}]选一个",
  "tool": "只能从[${AI_TOOL_TABLE}]选一个；运镜/镜头类优先选『可灵』『即梦』『海螺』之一",
  "note": "可选补充说明（默认空字符串）",
  "tags": "可选自由标签（默认空字符串）"
}
【拆分原则】一条原始文本如果明显是多个独立要点（如"1.推镜头 2.拉镜头"或空行分隔的多段），就拆成多条；如果整段只是一个要点，就返回一条。每条 title 要有区分度。
【硬约束】category / output_type / style / tool 必须严格使用上述词表里的字面值；运镜类必须 category=运镜 且 tool 为可灵/即梦/海螺。只输出 JSON 数组，不要任何解释、不要使用 markdown 代码块包裹。`

// 从 AI 返回文本中稳健提取 JSON（兼容 ```json 代码块、前后多余文字、正文内含花括号）
function extractAiJson(text) {
  if (!text || !text.trim()) throw new Error('AI 返回内容为空')
  let s = text.trim()
  const fence = s.match(/```(?:json)?\s*([\s\S]*?)```/i)
  if (fence) s = fence[1].trim()
  const start = s.search(/[[{]/)
  if (start < 0) throw new Error('AI 返回中找不到 JSON')
  const open = s[start]
  const close = open === '[' ? ']' : '}'
  let depth = 0, inStr = false, esc = false
  for (let i = start; i < s.length; i++) {
    const c = s[i]
    if (inStr) {
      if (esc) esc = false
      else if (c === '\\') esc = true
      else if (c === '"') inStr = false
    } else {
      if (c === '"') inStr = true
      else if (c === open) depth++
      else if (c === close) { depth--; if (depth === 0) { s = s.slice(start, i + 1); break } }
    }
  }
  return JSON.parse(s)
}

const showEditor = ref(false)
const editing = reactive(blankForm())
const saving = ref(false)
const customCategory = ref('')
const customStyle = ref('')
const customTool = ref('')

const dragIndex = ref(-1)
const dragOverIndex = ref(-1)

// 管理 / 多选 / 导入导出
const manageMode = ref(false)
const selected = ref(new Set())
function selectedIds() { return Array.from(selected.value) }
function isSelected(id) { return selected.value.has(id) }
function toggleSelect(id) {
  const next = new Set(selected.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  selected.value = next
}
function selectAll() { selected.value = new Set(list.value.map(i => i.id)) }
function clearSelect() { selected.value = new Set() }
function toggleManage() { manageMode.value = !manageMode.value; if (!manageMode.value) selected.value = new Set() }
const importInput = ref(null)
const importMsg = ref('')
const importingZip = ref(false)

// ===== 导入外部提示词（txt/md/json/docx → 预览 → 拆分 → 草稿 → 批量新建）=====
const IMPORT_STRATEGIES = [
  { value: 'one', group: 'single', label: '整段作为一条', example: '不切分，整段原文作为一条提示词。适用于：原文本身就是一个完整提示词。' },
  { value: 'blank', group: 'multi', label: '按空行拆分', example: '原文中两个换行（空行）分隔的每段作为一条。例：\n段落一\n\n段落二\n→ 拆成 2 条' },
  { value: 'dash', group: 'multi', label: '按 --- 拆分', example: '原文中以单独一行的 --- 作为分隔符。例：\n内容A\n---\n内容B\n→ 拆成 2 条' },
  { value: 'num', group: 'multi', label: '按序号拆分', example: '原文中以「1. 2. 3.」「1、2、3、」或「## 1. ## 2.」开头的行作为每条起点，标题前的 ## 与序号会被去掉。例：\n## 1. 推镜头\n## 2. 拉镜头\n→ 拆成 2 条，标题分别为「推镜头」「拉镜头」' },
  { value: 'bracket', group: 'multi', label: '按【标题】拆分', example: '原文中以单独一行的【xxx】作为每条起点。例：\n【运镜技巧】内容…\n【景别】内容…\n→ 拆成 2 条' },
  { value: 'md', group: 'multi', label: '按 Markdown 标题拆分', example: '原文中以单独一行的 # / ## / ### 等 Markdown 标题作为每条分界：标题行作为该条标题，下方内容作为正文（不含标题行）。例：\n## 1. 御兽术\n召唤神龙咒语…\n## 2. 炼丹术\n九转金丹配方…\n→ 拆成 2 条' },
]
const importStrategiesSingle = computed(() => IMPORT_STRATEGIES.filter(s => s.group === 'single'))
const importStrategiesMulti = computed(() => IMPORT_STRATEGIES.filter(s => s.group === 'multi'))
const currentStrategyExample = computed(() => {
  const s = IMPORT_STRATEGIES.find(x => x.value === importStrategy.value)
  return s ? s.example : ''
})
const importTextInput = ref(null)
const importTextOpen = ref(false)
const importStep = ref('preview')
const importFileName = ref('')
const importRaw = ref('')
const importStrategy = ref('blank')
const importDrafts = ref([])
const importing = ref(false)
const importOwner = ref((auth.user && (auth.user.display_name || auth.user.username)) || '苏小沫')
const draftAnchor = ref(-1)

const importPreviewCount = computed(() => splitText(importRaw.value, importStrategy.value).length)

function triggerImportText() {
  importTextInput.value && importTextInput.value.click()
  loadAiRules()
  loadModelConfigs()
}
function closeImportText() {
  importTextOpen.value = false
  importStep.value = 'preview'
  importFileName.value = ''
  importRaw.value = ''
  importDrafts.value = []
}
async function onImportTextPicked(e) {
  const file = e.target.files && e.target.files[0]
  e.target.value = ''
  if (!file) return
  importFileName.value = file.name
  const ext = (file.name.split('.').pop() || '').toLowerCase()
  try {
    let text = ''
    if (ext === 'docx') {
      const buf = await file.arrayBuffer()
      text = await docxToText(buf)
    } else if (ext === 'doc') {
      showToast('仅支持 .docx（Word 2007+），旧版 .doc 请另存为 .docx 或 .txt 后导入')
      return
    } else {
      text = await file.text()
      if (ext === 'json') {
        try {
          const j = JSON.parse(text)
          if (Array.isArray(j) && j.length && j.every(x => x && (x.content || x.title))) {
            importDrafts.value = j.map((x, i) => ({
              title: (x.title || '').toString().trim() || `提示词${i + 1}`,
              content: x.content || '',
              category: x.category || '其他',
              output_type: x.output_type || '文本',
              style: x.style || '通用风格',
              tool: x.tool || '通用工具',
            }))
            importStep.value = 'draft'
            importTextOpen.value = true
            return
          }
        } catch (_) { /* 非结构化 JSON，当纯文本预览 */ }
      }
    }
    importRaw.value = text
    importStrategy.value = 'blank'
    importStep.value = 'preview'
    importTextOpen.value = true
  } catch (err) {
    showToast('读取文件失败：' + (err && err.message ? err.message : err))
  }
}
// 统一返回 [{ title, content }]：title 为空时由 buildDrafts 用首行兜底
function splitText(text, strategy) {
  const t = (text || '').replace(/\r\n/g, '\n').trim()
  if (!t) return []
  let raw = []
  if (strategy === 'one') {
    raw = [{ title: '', content: t }]
  } else if (strategy === 'blank') {
    raw = t.split(/\n\s*\n/).map(s => s.trim()).filter(Boolean).map(s => ({ title: '', content: s }))
  } else if (strategy === 'dash') {
    raw = t.split(/^\s*-{2,}\s*$/m).map(s => s.trim()).filter(Boolean).map(s => ({ title: '', content: s }))
  } else if (strategy === 'num') {
    // 支持「1. 」「1、」以及「## 1. 」这类 Markdown 标题 + 序号组合；序号前缀作为标题
    const lines = t.split('\n')
    let cur = { title: '', content: '' }
    for (const ln of lines) {
      if (/^\s*(?:#{1,6}\s+)?\d+[\.、]\s/.test(ln)) {
        if (cur.content.trim()) raw.push(cur)
        cur = { title: ln.replace(/^\s*(?:#{1,6}\s+)?\d+[\.、]\s/, '').trim(), content: '' }
      } else {
        cur.content += ln + '\n'
      }
    }
    if (cur.content.trim()) raw.push(cur)
  } else if (strategy === 'bracket') {
    // 单独一行的【xxx】作为分界，整行（含【】）保留进正文，标题由首行兜底
    const lines = t.split('\n')
    let cur = ''
    const segs = []
    for (const ln of lines) {
      if (/^\s*【[^】]+】\s*$/.test(ln) && cur.trim()) { segs.push(cur.trim()); cur = '' }
      cur += ln + '\n'
    }
    if (cur.trim()) segs.push(cur.trim())
    raw = segs.filter(Boolean).map(s => ({ title: '', content: s }))
  } else if (strategy === 'md') {
    // Markdown 标题（# ~ ###### 单独成行）作为分界：标题行当 title，下方内容当正文
    const lines = t.split('\n')
    let cur = { title: '', content: '' }
    for (const ln of lines) {
      const m = ln.match(/^\s*(#{1,6})\s+(.+?)\s*$/)
      if (m) {
        if (cur.title || cur.content.trim()) raw.push(cur)
        cur = { title: m[2].trim(), content: '' }
      } else {
        cur.content += ln + '\n'
      }
    }
    if (cur.title || cur.content.trim()) raw.push(cur)
  }
  return raw.map(r => ({ title: (r.title || '').trim(), content: (r.content || '').trim() }))
}
function firstLineTitle(seg) {
  const line = (seg.split('\n').find(l => l.trim()) || '').trim()
  return line ? line.slice(0, 40) : ''
}
// ---------- AI 内置助手：规则A 生成单条 / 规则B 分析整理文本 ----------
const aiIntent = ref('')
const aiGenerating = ref(false)
const aiAnalyzing = ref(false)

// ===== AI 规则模板（提示词库专属，持久化）=====
const aiRules = ref([])
const aiRuleId = ref(null)
const aiRuleSelectRef = ref(null)

const AI_RULE_MENU = '提示词库'
const AI_RULE_PREF_KEY = 'ai_rule.提示词库'

const selectedAiRule = computed(() => aiRules.value.find(r => r.id === aiRuleId.value) || null)

// 把 AI 返回统一成数组：单条对象也包成 [obj]（AI 自判断单/多，前端统一按数组处理）
function toAiArray(v) {
  if (Array.isArray(v)) return v
  if (v && typeof v === 'object') return [v]
  return null
}

function roleLabel(r) {
  return ({ system: '系统', generate: '生成', optimize: '优化', split: '拆分', organize: '整理', format: '格式', review: '审核' })[r] || r
}
// 规则 AI 配置 → askApi opts（空=跟随模型配置/默认模型）
function ruleOpts(rule) {
  if (!rule) return {}
  const opts = {}
  if (rule.model_config_id) opts.modelConfigId = rule.model_config_id
  if (rule.thinking === 'fast') opts.thinking = false
  else if (rule.thinking === 'expert') opts.thinking = true
  if (rule.strength && rule.strength !== 'follow') opts.reasoningEffort = rule.strength
  return opts
}

async function loadAiRules() {
  try {
    const list = await api('/ai-rules?menu=' + encodeURIComponent(AI_RULE_MENU) + '&enabled=1', 'GET')
    aiRules.value = Array.isArray(list) ? list : []
    if (!aiRuleId.value && aiRules.value.length) {
      aiRuleId.value = aiRules.value[0].id
    }
    await restoreAiRuleSelection()
  } catch (e) { /* 规则加载失败不阻断导入 */ }
}
// 记住选择：localStorage（快）→ 后端 prefs（永久，按用户存）→ 默认第一条
async function restoreAiRuleSelection() {
  if (!aiRules.value.length) { aiRuleId.value = null; return }
  let snap = null
  try {
    const ls = localStorage.getItem(AI_RULE_PREF_KEY)
    if (ls) snap = JSON.parse(ls)
  } catch (e) { /* ignore */ }
  if (!snap) {
    try {
      const res = await api('/prefs/' + encodeURIComponent(AI_RULE_PREF_KEY), 'GET')
      snap = res && res.value
    } catch (e) { /* ignore */ }
  }
  if (!snap) { aiRuleId.value = aiRules.value[0].id; return }
  // 三级容错：rule_id → name → name+menu+function_key+role
  let hit = aiRules.value.find(r => r.id === snap.rule_id)
  if (!hit && snap.name) hit = aiRules.value.find(r => r.name === snap.name)
  if (!hit && snap.name) {
    hit = aiRules.value.find(r =>
      r.name === snap.name && r.menu === snap.menu &&
      (r.function_key || '') === (snap.function_key || '') && r.role === snap.role
    )
  }
  aiRuleId.value = hit ? hit.id : aiRules.value[0].id
}
// 切换规则 → 记住（本地 + 后端永久）
function onAiRuleChange() {
  const r = selectedAiRule.value
  if (!r) return
  const snap = { rule_id: r.id, name: r.name, menu: r.menu, function_key: r.function_key, role: r.role }
  try { localStorage.setItem(AI_RULE_PREF_KEY, JSON.stringify(snap)) } catch (e) { /* ignore */ }
  api('/prefs/' + encodeURIComponent(AI_RULE_PREF_KEY), 'PUT', { value: snap }).catch(() => {})
}
async function aiAnalyze() {
  const raw = importRaw.value.trim()
  if (!raw) { showToast('没有可分析的文本'); return }
  const rule = selectedAiRule.value
  const sysPrompt = (rule && rule.content) ? rule.content : AI_SYS_RULE_B
  aiAnalyzing.value = true
  try {
    const opts = ruleOpts(rule)
    const r = await askApi(raw, sysPrompt, [], [], opts)
    const arr = toAiArray(extractAiJson(_aiReplyText(r)))
    if (!Array.isArray(arr)) throw new Error('AI 返回的不是数组')
    const drafts = arr.map(makeDraftFromAi).filter(d => (d.title || '').trim())
    if (!drafts.length) throw new Error('AI 未返回任何提示词')
    importDrafts.value = drafts
    importStep.value = 'draft'
    showToast(`AI 整理出 ${drafts.length} 条，请检查后批量新建`)
  } catch (e) {
    showToast('AI 分析失败：' + (e.message || e))
  } finally {
    aiAnalyzing.value = false
  }
}

function _aiReplyText(r) {
  if (typeof r === 'string') return r
  if (r && (r.reply || r.content)) return r.reply || r.content
  return ''
}

async function aiGenerate() {
  const intent = aiIntent.value.trim()
  if (!intent) { showToast('请先填写创作意图'); return }
  aiGenerating.value = true
  try {
    const r = await askApi(intent, AI_SYS_RULE_A, [], [], {})
    const obj = extractAiJson(_aiReplyText(r))
    applyAiToEditing(obj)
    showToast('AI 已生成，请检查后保存')
  } catch (e) {
    showToast('AI 生成失败：' + (e.message || e))
  } finally {
    aiGenerating.value = false
  }
}

function applyAiToEditing(o) {
  if (!o || typeof o !== 'object') return
  if (o.title) editing.title = String(o.title).trim().slice(0, 60)
  if (o.content) editing.content = String(o.content)
  if (o.note) editing.note = String(o.note)
  const cat = o.category ? String(o.category).trim() : ''
  if (cat) {
    if (formCategoryOptions.value.includes(cat)) editing.category = cat
    else { editing.category = '__custom__'; customCategory.value = cat }
  }
  if (o.output_type) editing.output_type = String(o.output_type).trim()
  const st = o.style ? String(o.style).trim() : ''
  if (st) {
    if (STYLE_OPTIONS.includes(st)) editing.style = st
    else { editing.style = '__custom__'; customStyle.value = st }
  }
  const tl = o.tool ? String(o.tool).trim() : ''
  if (tl) {
    if (TOOL_OPTIONS.includes(tl)) editing.tool = tl
    else { editing.tool = '__custom__'; customTool.value = tl }
  }
}

function makeDraftFromAi(o) {
  const cat = o.category ? String(o.category).trim() : '其他'
  const style = o.style ? String(o.style).trim() : '通用风格'
  const tool = o.tool ? String(o.tool).trim() : '通用工具'
  const out = o.output_type ? String(o.output_type).trim() : '文本'
  return {
    title: String(o.title || '').trim().slice(0, 60) || '未命名提示词',
    content: String(o.content || ''),
    category: cat,
    output_type: out,
    style,
    tool,
    note: String(o.note || ''),
    images: [],
  }
}

async function docxToText(arrayBuffer) {
  const zip = await JSZip.loadAsync(arrayBuffer)
  const xml = await zip.file('word/document.xml').async('string')
  let s = xml.replace(/<\/w:p>/g, '\n')            // 段落换行
  s = s.replace(/<w:tab\s*\/?>/g, '\t')            // 制表符
  s = s.replace(/<w:t[^>]*>([\s\S]*?)<\/w:t>/g, (_, t) => t)  // 取文本
  s = s.replace(/<[^>]+>/g, '')                    // 去其余标签
  s = s.replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>')
        .replace(/&quot;/g, '"').replace(/&apos;/g, "'").replace(/&nbsp;/g, ' ')
  return s
}
function buildDrafts() {
  const segs = splitText(importRaw.value, importStrategy.value)
  if (!segs.length) { showToast('没有可拆分的内容'); return }
  importDrafts.value = segs.map((seg, i) => ({
    title: seg.title || firstLineTitle(seg.content) || `提示词${i + 1}`,
    content: seg.content,
    category: '其他',
    output_type: '文本',
    style: '通用风格',
    tool: '通用工具',
    note: '',
    images: [],
  }))
  importStep.value = 'draft'
}
function blankDraft() {
  return { title: '', content: '', category: '其他', output_type: '文本', style: '通用风格', tool: '通用工具', note: '', images: [] }
}
function addDraftRow() {
  const next = [...importDrafts.value, blankDraft()]
  importDrafts.value = next
  draftAnchor.value = next.length - 1
  scrollToDraft(next.length - 1)
}
function insertDraftRow(i) {
  const next = [...importDrafts.value]
  next.splice(i + 1, 0, blankDraft())
  importDrafts.value = next
  draftAnchor.value = i + 1
  scrollToDraft(i + 1)
}
function scrollToDraft(i) {
  // 等待 DOM 渲染后滚动并高亮
  setTimeout(() => {
    const el = document.querySelectorAll('.draft-row')[i]
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'center' })
      el.classList.add('draft-flash')
      setTimeout(() => el.classList.remove('draft-flash'), 1200)
    }
  }, 60)
}
function removeDraftRow(i) {
  importDrafts.value = importDrafts.value.filter((_, idx) => idx !== i)
}
// 逐行图片上传（草稿态，保存在草稿对象里，submit 时随每条补传）
const draftImgInputs = reactive({})
function onDraftImgPicked(d, i, e) {
  const files = Array.from(e.target.files || [])
  const adds = files.map(f => ({ file: f, preview: URL.createObjectURL(f) }))
  d.images = [...(d.images || []), ...adds]
  e.target.value = ''
}
// 批量设置弹窗状态
const batchOpen = ref(false)
const batchMode = ref('field') // 'field' | 'owner'
const batchField = ref('')
const batchValue = ref('')
const batchLabel = computed(() => {
  if (batchMode.value === 'owner') return '作者'
  return { category: '分类', output_type: '类型', style: '风格', tool: '工具' }[batchField.value] || ''
})
const batchOptions = computed(() => {
  const map = {
    category: formCategoryOptions.value,
    output_type: outputOptions.value.filter(x => x !== '全部'),
    style: STYLE_OPTIONS,
    tool: TOOL_OPTIONS,
  }
  return map[batchField.value] || []
})
function openBatchSet(modeOrField) {
  if (modeOrField === 'owner') {
    batchMode.value = 'owner'
    batchField.value = ''
    batchValue.value = importOwner.value || ''
  } else {
    batchMode.value = 'field'
    batchField.value = modeOrField
    batchValue.value = importDrafts.value[0] ? importDrafts.value[0][modeOrField] : ''
  }
  batchOpen.value = true
}
function closeBatchSet() { batchOpen.value = false }
function applyBatchSet() {
  const v = (batchValue.value || '').toString().trim()
  if (!v) { showToast(`请输入${batchLabel.value}`); return }
  if (batchMode.value === 'owner') {
    importOwner.value = v
    showToast(`已将作者统一设为「${v}」`)
  } else {
    importDrafts.value = importDrafts.value.map(d => ({ ...d, [batchField.value]: v }))
    showToast(`已将 ${importDrafts.value.length} 条${batchLabel.value}设为「${v}」`)
  }
  batchOpen.value = false
}
async function submitImportDrafts() {
  const owner = (importOwner.value || '').trim() || ((auth.user && (auth.user.display_name || auth.user.username)) || '苏小沫')
  const items = importDrafts.value
    .filter(d => (d.title || '').trim())
    .map(d => ({
      title: (d.title || '').trim(),
      content: d.content || '',
      category: d.category || '其他',
      output_type: d.output_type || '文本',
      style: d.style || '通用风格',
      tool: d.tool || '通用工具',
      note: d.note || '',
      owner_name: owner,
    }))
  if (!items.length) { showToast('请至少填写一条标题'); return }

  // 冲突感知：先检测与库中已有提示词重名，不静默跳过（弹窗不关闭，可改名重试）
  const libTitles = new Set(list.value.map(x => (x.title || '').trim()))
  importDrafts.value.forEach(d => { d._dup = false })
  const dupTitles = new Set(items.filter(i => libTitles.has(i.title)).map(i => i.title))
  if (dupTitles.size) {
    importDrafts.value.forEach(d => {
      if ((d.title || '').trim() && dupTitles.has((d.title || '').trim())) d._dup = true
    })
    showToast(`${dupTitles.size} 条与库中已有提示词重名，请改名后重新提交（草稿不会丢）`)
    return
  }

  importing.value = true
  try {
    const stats = await api('/prompt-library/batch-create', 'POST', { items })
    // 逐条补图（每条草稿带有的图片）
    const created = stats.created_ids || []
    const draftsWithImg = importDrafts.value.filter(d => (d.title || '').trim() && d.images && d.images.length)
    for (let k = 0; k < created.length && k < draftsWithImg.length; k++) {
      const d = draftsWithImg[k]
      if (d.images && d.images.length) {
        const fd = new FormData()
        for (const p of d.images) fd.append('files', p.file)
        try { await apiUpload(`/prompt-library/${created[k]}/images`, fd) } catch (_) { /* 图片失败不阻断文本 */ }
      }
    }
    showToast(`已新建 ${stats.created} 条` + (stats.skipped ? `，跳过 ${stats.skipped} 条重复` : ''))
    closeImportText()
    await loadList()
    await loadMeta()
  } catch (e) {
    showToast(e.message || '批量新建失败')
  } finally {
    importing.value = false
  }
}
const categoryOptions = computed(() => {
  const set = new Set(defaultCategories)
  meta.categories.forEach(c => set.add(c))
  return Array.from(set)
})
const formCategoryOptions = computed(() => categoryOptions.value.filter(c => c !== '全部' && c !== '自定义'))

// 首页风格/工具筛选下拉：预定义项 + 已保存记录里实际出现的自定义值（用 splitStyleTool 还原位置，保证自定义风格归风格、自定义工具归工具）
const styleFilterOptions = computed(() => {
  const seen = new Set(STYLE_OPTIONS)
  list.value.forEach(item => {
    const { style } = splitStyleTool(item.tags)
    if (style) seen.add(style)
  })
  return Array.from(seen)
})
const toolFilterOptions = computed(() => {
  const seen = new Set(TOOL_OPTIONS)
  list.value.forEach(item => {
    const { tool } = splitStyleTool(item.tags)
    if (tool) seen.add(tool)
  })
  return Array.from(seen)
})
const authorFilterOptions = computed(() => ['全部作者', ...meta.owners])

const showDetail = ref(false)
const detail = ref({})
const testing = ref(false)
const testResult = ref('')
const testError = ref('')

const toast = ref('')
const detailCopied = ref(false)
let toastTimer = null
const imgInput = ref(null)
const pendingImgs = ref([])   // [{ file, preview }]

// 详情页 Prompt 正文「划词复制」浮动按钮
const selMenu = reactive({ visible: false, x: 0, y: 0, text: '' })

// 统一灯箱状态（复用默认 MediaLightbox 组件）
const lightboxVisible = ref(false)
const lightboxItems = ref([])
const lightboxIndex = ref(0)

let loadTimer = null
function debouncedLoad() {
  clearTimeout(loadTimer)
  loadTimer = setTimeout(loadList, 250)
}

async function loadMeta() {
  try {
    const m = await api('/prompt-library/meta?scope=prompt', 'GET')
    meta.categories = m.categories || []
    meta.output_types = m.output_types || []
    meta.all_tags = m.all_tags || []
    meta.owners = m.owners || []
  } catch (e) { /* 忽略 */ }
}

async function loadList() {
  const q = new URLSearchParams({
    category: filters.category,
    output_type: filters.outputType,
    keyword: filters.keyword,
    tag: [filters.style, filters.tool].filter(Boolean).join(','),
    owner: filters.owner,
    scope: 'prompt',
  }).toString()
  try {
    const rows = await api(`/prompt-library/list?${q}`, 'GET')
    list.value = rows.map(r => ({ ...r, images: parseImages(r.images) }))
  } catch (e) {
    showToast(e.message || '加载失败')
  }
}

function setCategory(c) { filters.category = c; loadList() }

function onDragStart(idx, e) {
  dragIndex.value = idx
  e.dataTransfer.effectAllowed = 'move'
  e.dataTransfer.setData('text/plain', String(idx))
}
function onDragEnter(idx) { dragOverIndex.value = idx }
function onDragOver(e) { e.dataTransfer.dropEffect = 'move' }
function onDrop(idx) {
  const from = dragIndex.value
  if (from === -1 || from === idx) { dragOverIndex.value = -1; dragIndex.value = -1; return }
  const moved = list.value[from]
  list.value.splice(from, 1)
  list.value.splice(idx, 0, moved)
  saveOrder()
  dragOverIndex.value = -1
  dragIndex.value = -1
}
function onDragEnd() { dragOverIndex.value = -1; dragIndex.value = -1 }
async function saveOrder() {
  try {
    await api('/prompt-library/reorder', 'POST', { order: list.value.map(i => i.id) })
  } catch (e) {
    showToast(e.message || '排序保存失败')
  }
}

function defaultOwnerName() {
  return auth.user?.display_name || auth.user?.username || '我'
}

// 模型配置（供 AI 分析/生成选模型）
const modelConfigs = ref([])
async function loadModelConfigs() {
  try {
    const list = await api('/model-configs', 'GET')
    modelConfigs.value = Array.isArray(list) ? list : []
  } catch (e) { /* 失败不阻断 */ }
}

// 卡片「更多」下拉（测试/优化/生成 收进这里；生X 标题按 output_type 动态，弹窗提示去外部平台）
const cardMoreOpen = ref(null)
const genHintOpen = ref(false)
const genHintItem = ref(null)
const genHintAction = ref('')
function toggleCardMore(item) {
  cardMoreOpen.value = cardMoreOpen.value === item.id ? null : item.id
}
function onCardMore(item, action) {
  cardMoreOpen.value = null
  genHintItem.value = item
  genHintAction.value = ({ test: '测试', optimize: '优化' })[action] || genActionLabel(item.output_type)
  genHintText.value = genActionHint(item, action)
  genHintOpen.value = true
}
function closeCardMore() { cardMoreOpen.value = null }
const genHintText = ref('')
async function copyGenHint() {
  const item = genHintItem.value
  if (!item) return
  try {
    await navigator.clipboard.writeText(item.content || '')
    showToast('提示词已复制')
  } catch (_) {
    showToast('复制失败，请手动复制')
  }
}

// 按 output_type 决定第三个按钮标题：文本/其他→生成、图片→生图、视频→生视频、音频→配音
function genActionLabel(ot) {
  return ({ 图片: '生图', 视频: '生视频', 音频: '配音' })[ot] || '生成'
}
// 统一弹窗提示（不复制、不调模型）：按 output_type 给对应外部平台建议
function genActionHint(item, action) {
  const name = item.title || ''
  const act = ({ test: '测试', optimize: '优化' })[action] || genActionLabel(item.output_type)
  const base = `「${name}」${act}：请复制提示词`
  const site = ({
    图片: '，并在椒图AI、Flux Art、ChatImage2 等生图网站使用',
    视频: '，并在即梦、可灵、小云雀 等视频网站使用',
    音频: '，并在 TTS、Mossland 等配音网站使用',
    其他: '，并在 Codex、WorkBuddy 等智能体平台使用',
  })[item.output_type] || '，在平台 AI 助手或免费 AI 网站使用'
  return base + site + '，积分有限，暂不做本地关联'
}

function blankForm() {
  return { id: null, title: '', owner_name: defaultOwnerName(), content: '', category: '角色', output_type: '文本', note: '', style: '通用风格', tool: '通用工具', tags: '', images: [] }
}

function openCreate() {
  customCategory.value = ''
  customStyle.value = ''
  customTool.value = ''
  attachments.value = []
  attPending.value = []
  Object.assign(editing, blankForm())
  showEditor.value = true
}
function openEdit(item) {
  const known = formCategoryOptions.value.includes(item.category)
  customCategory.value = known ? '' : (item.category || '')
  const st = splitStyleTool(item.tags)
  const styleVal = st.style || '通用风格'
  const toolVal = st.tool || '通用工具'
  const styleKnown = STYLE_OPTIONS.includes(styleVal)
  const toolKnown = TOOL_OPTIONS.includes(toolVal)
  customStyle.value = styleKnown ? '' : styleVal
  customTool.value = toolKnown ? '' : toolVal
  Object.assign(editing, {
    id: item.id, title: item.title, owner_name: item.owner_name || defaultOwnerName(), content: item.content,
    category: known ? item.category : '__custom__',
    output_type: ({ '文': '文本', '图': '图片' }[item.output_type] || item.output_type), note: item.note || '',
    style: styleKnown ? styleVal : '__custom__',
    tool: toolKnown ? toolVal : '__custom__',
    tags: item.tags || '',
    images: parseImages(item.images),
  })
  attachments.value = []
  attPending.value = []
  if (item.id) loadAttachments(item.id)
  showEditor.value = true
}
function closeEditor() { showEditor.value = false }

// ---------- skills 附件：md/txt/docx 读取填正文，压缩包存附件 ----------
const attachments = ref([])       // 已存附件（编辑态）
const attPending = ref([])        // 待处理文件：{file, filename, mode:'text'|'archive'}
const attInput = ref(null)
const ATT_TEXT_EXT = ['md', 'markdown', 'txt']
const ATT_ARCHIVE_EXT = ['zip', '7z', 'rar', 'tar', 'tgz', 'gz']

function fmtSize(n) {
  if (n == null) return ''
  if (n < 1024) return n + ' B'
  if (n < 1024 * 1024) return (n / 1024).toFixed(1) + ' KB'
  return (n / 1024 / 1024).toFixed(1) + ' MB'
}
async function loadAttachments(pid) {
  try {
    const list = await api(`/prompt-library/${pid}/attachments`, 'GET')
    attachments.value = Array.isArray(list) ? list : []
  } catch (e) { /* 附件加载失败不阻断 */ }
}
async function removeAttachment(a) {
  if (!(await confirm(`确定删除附件「${a.filename}」？`))) return
  try {
    await api(`/prompt-library/${editing.id}/attachments/${a.id}`, 'DELETE')
    attachments.value = attachments.value.filter(x => x.id !== a.id)
    showToast('已删除')
  } catch (e) {
    showToast(e.message || '删除失败')
  }
}
async function onAttPicked(e) {
  const files = Array.from(e.target.files || [])
  if (!files.length) return
  const textParts = []
  const archs = []
  for (const f of files) {
    const ext = (f.name.split('.').pop() || '').toLowerCase()
    if (ATT_TEXT_EXT.includes(ext)) {
      textParts.push(f)
    } else if (ext === 'docx') {
      try {
        const fd = new FormData()
        fd.append('file', f)
        const r = await apiUpload('/prompt-library/read-docx', fd)
        const t = (r && r.text) ? r.text.trim() : ''
        if (t) {
          editing.content = editing.content ? editing.content + '\n\n' + t : t
          attPending.value.push({ file: f, filename: f.name, mode: 'text' })
        }
      } catch (err) {
        showToast(`「${f.name}」解析失败：` + ((err && err.message) || err))
      }
    } else if (ATT_ARCHIVE_EXT.includes(ext)) {
      archs.push(f)
    } else {
      showToast(`「${f.name}」不支持的类型（md/txt/docx/压缩包）`)
    }
  }
  // md/txt：前端读取纯文本填入正文
  for (const f of textParts) {
    try {
      const t = await f.text()
      const text = (t || '').trim()
      if (text) {
        editing.content = editing.content ? editing.content + '\n\n' + text : text
        attPending.value.push({ file: f, filename: f.name, mode: 'text' })
      }
    } catch (_) { /* 读取失败跳过 */ }
  }
  for (const f of archs) {
    attPending.value.push({ file: f, filename: f.name, mode: 'archive' })
  }
  if (attPending.value.length) showToast(`已处理 ${attPending.value.length} 个文件：文本已填入正文，压缩包保存后上传`)
  e.target.value = ''
}

async function save() {
  if (!editing.title.trim()) { showToast('标题不能为空'); return }
  if (!editing.owner_name.trim()) { showToast('作者不能为空'); return }
  const category = editing.category === '__custom__' ? (customCategory.value.trim() || '其他') : editing.category
  const style = editing.style === '__custom__' ? (customStyle.value.trim() || '通用风格') : editing.style
  const tool = editing.tool === '__custom__' ? (customTool.value.trim() || '通用工具') : editing.tool
  saving.value = true
  try {
    const mergedTags = [style, tool].map(s => (s || '').trim()).filter(Boolean).join(', ')
    const payload = {
      title: editing.title, owner_name: editing.owner_name.trim(), content: editing.content,
      category,
      output_type: editing.output_type, note: editing.note, tags: mergedTags,
    }
    let newId = editing.id
    if (editing.id) {
      await api(`/prompt-library/${editing.id}`, 'PUT', payload)
    } else {
      const created = await api('/prompt-library/', 'POST', payload)
      newId = created && created.id
    }
    // 新建/编辑都支持：把待上传图片落到该条记录
    if (newId && pendingImgs.value.length) {
      const fd = new FormData()
      for (const p of pendingImgs.value) fd.append('files', p.file)
      try {
        await apiUpload(`/prompt-library/${newId}/images`, fd)
        pendingImgs.value = []
      } catch (err) {
        showToast('提示词已保存，但图片上传失败：' + (err.message || '未知错误'))
      }
    }
    // skills 附件：压缩包在保存后上传（md/txt/docx 已直接填入正文）
    if (newId && attPending.value.length) {
      const archs = attPending.value.filter(p => p.mode === 'archive')
      if (archs.length) {
        const fd = new FormData()
        for (const p of archs) fd.append('files', p.file)
        try {
          await apiUpload(`/prompt-library/${newId}/attachments`, fd)
        } catch (err) {
          showToast('提示词已保存，但附件上传失败：' + (err.message || '未知错误'))
        }
      }
      attPending.value = []
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
  if (!(await confirm(`确定删除「${item.title}」？此操作不可撤销。`, { title: '删除确认' }))) return
  try {
    await api(`/prompt-library/${item.id}`, 'DELETE')
    await loadMeta()
    await loadList()
    showToast('已删除')
  } catch (e) {
    showToast(e.message || '删除失败')
  }
}

// ---------- 管理：导出 / 导入 / 批量删除 ----------
const exporting = ref(false)
const exportMsg = ref('正在导出，请耐心等待…')
async function doExport(ids) {
  if (exporting.value) return
  exporting.value = true
  exportMsg.value = ids && ids.length
    ? `正在导出 ${ids.length} 条，请耐心等待…`
    : '正在导出全部提示词，请耐心等待…'
  try {
    const resp = await fetch('/api/prompt-library/export', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...(auth.token ? { Authorization: `Bearer ${auth.token}` } : {}) },
      body: JSON.stringify({ ids: ids && ids.length ? ids : null }),
    })
    if (!resp.ok) {
      let msg = '导出失败 ' + resp.status
      try { const j = await resp.json(); msg = j.detail || msg } catch (e) {}
      showToast(msg); return
    }
    const blob = await resp.blob()
    const d = new Date()
    const p = (n) => String(n).padStart(2, '0')
    const ts = `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}-${p(d.getHours())}${p(d.getMinutes())}${p(d.getSeconds())}`
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `提示词库_${ts}.zip`
    document.body.appendChild(a); a.click(); a.remove()
    setTimeout(() => URL.revokeObjectURL(a.href), 1000)
    showToast('已导出')
  } finally {
    exporting.value = false
  }
}
async function exportAll() {
  await doExport(null)
}
async function exportSelected() {
  const ids = selectedIds()
  if (!ids.length) { showToast('请先选择要导出的提示词'); return }
  await doExport(ids)
}
async function onImportPicked(e) {
  const f = e.target.files && e.target.files[0]
  if (!f) return
  if (importingZip.value) return
  importingZip.value = true
  const fd = new FormData()
  fd.append('file', f)
  try {
    const stats = await apiUpload('/prompt-library/import', fd)
    importMsg.value = `导入完成：新增 ${stats.imported} 条` + (stats.skipped ? `，跳过重复 ${stats.skipped} 条` : '') + (stats.failed ? `，失败 ${stats.failed} 条` : '')
    showToast(importMsg.value)
    await loadMeta(); await loadList()
  } catch (err) {
    showToast(err.message || '导入失败')
  } finally {
    importingZip.value = false
    e.target.value = ''
  }
}
async function batchDelete() {
  const ids = selectedIds()
  if (!ids.length) { showToast('请先选择要删除的提示词'); return }
  if (!(await confirm(`确定批量删除选中的 ${ids.length} 条提示词？其图片 / skill 文件也会一并移除，且不可撤销。`, { title: '批量删除确认' }))) return
  try {
    const r = await api('/prompt-library/batch-delete', 'POST', { ids })
    showToast(`已删除 ${r.deleted} 条`)
    manageMode.value = false
    selected.value = new Set()
    await loadMeta(); await loadList()
  } catch (e) { showToast(e.message || '删除失败') }
}

async function copy(item) {
  const text = item.content || ''
  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(text)
    } else {
      const ta = document.createElement('textarea')
      ta.value = text; document.body.appendChild(ta); ta.select()
      document.execCommand('copy'); document.body.removeChild(ta)
    }
    showToast('已复制到剪贴板')
  } catch (e) {
    showToast('复制失败，请手动选择')
  }
}

function openDetail(item) {
  detail.value = item
  clearTest()
  showDetail.value = true
}
async function setFirst(img) {
  const id = detail.value.id
  const updated = await api(`/prompt-library/${id}/set_cover`, 'POST', { image: img })
  detail.value = { ...updated, images: parseImages(updated.images) }
  await loadList()
  showToast('已设为首图')
}
function closeDetail() { showDetail.value = false }
function editDetail() {
  const item = detail.value
  closeDetail()
  openEdit(item)
}
async function removeDetail() {
  await remove(detail.value)
  closeDetail()
}
async function copyDetail() {
  await copy(detail.value)
  detailCopied.value = true
  setTimeout(() => { detailCopied.value = false }, 1500)
}
// 内嵌测试：把提示词发给已配置大模型看返回（图/视频型当前为文本预览）
async function runTest(item) {
  if (!item || !item.content) { showToast('该提示词没有正文，无法测试'); return }
  testing.value = true; testResult.value = ''; testError.value = ''
  try {
    const r = await askApi(item.content, '', [], [], {})
    testResult.value = typeof r === 'string' ? r : (r && (r.reply || r.content) ? (r.reply || r.content) : JSON.stringify(r))
  } catch (e) { testError.value = e.message || '测试失败' }
  finally { testing.value = false }
}
function clearTest() { testResult.value = ''; testError.value = '' }

// 在 Prompt 正文区域内选中文字后，在「Prompt 正文」标题行右侧显示「复制选中」按钮（固定位置，不跟随选区飘动）
function onDetailSelect() {
  const sel = window.getSelection && window.getSelection()
  const text = sel ? sel.toString() : ''
  if (!text || !text.trim()) { selMenu.visible = false; return }
  selMenu.text = text
  selMenu.visible = true
}
async function copySelection() {
  try {
    await navigator.clipboard.writeText(selMenu.text)
  } catch {
    const ta = document.createElement('textarea')
    ta.value = selMenu.text
    ta.style.position = 'fixed'
    ta.style.opacity = '0'
    document.body.appendChild(ta)
    ta.select()
    try { document.execCommand('copy') } catch (e) {}
    document.body.removeChild(ta)
  }
  selMenu.visible = false
  showToast('已复制选中文本')
  const s = window.getSelection && window.getSelection()
  if (s) s.removeAllRanges()
}
// 点击详情页其他区域时隐藏浮动按钮（点按钮本身除外）
function onMaskMouseDown(e) {
  if (e.target.closest && e.target.closest('.sel-copy')) return
  selMenu.visible = false
}

function previewText(t) {
  if (!t) return '（无正文）'
  const plain = t.replace(/\s+/g, ' ').trim()
  return plain.length > 120 ? plain.slice(0, 120) + '…' : plain
}
function splitTags(s) {
  return (s || '').split(',').map(x => x.trim()).filter(Boolean)
}
// 把存储的 tags 还原为 风格 / 工具（选型模式下通常各一个，按选项匹配）
function splitStyleTool(tags) {
  const arr = splitTags(tags)
  let s = '', t = ''
  for (const x of arr) {
    if (STYLE_OPTIONS.includes(x) && !s) s = x
    else if (TOOL_OPTIONS.includes(x) && !t) t = x
    else if (!s) s = x
    else if (!t) t = x
    else s = s ? s + ', ' + x : x
  }
  return { style: s, tool: t }
}
// 按存储位置判定标签角色：优先用 splitStyleTool 还原「风格/工具」位置，使自定义值也能正确染色；再回退到已知常量
function tagClass(t, tags) {
  const st = splitStyleTool(tags)
  if (t === st.style) return 'style-tag'
  if (t === st.tool) return 'tool-tag'
  if (STYLE_OPTIONS.includes(t)) return 'style-tag'
  if (TOOL_OPTIONS.includes(t)) return 'tool-tag'
  return ''
}
const OT_CLASS = {
  '文': 't-text', '图': 't-img', '音频': 't-audio', '视频': 't-video', '其他': 't-other', '自定义': 't-custom',
  '文本': 't-text', '图片': 't-img',
}
const OT_SHORT = {
  '文': '文本', '图': '图片', '音频': '音频', '视频': '视频', '其他': '其他', '自定义': '自定义',
  '文本': '文本', '图片': '图片', '视频': '视频', '音频': '音频', '其他': '其他',
}
function otClass(ot) {
  return OT_CLASS[ot] || 't-other'
}
function otShort(ot) {
  return OT_SHORT[ot] || (ot ? String(ot)[0] : '·')
}

function parseImages(v) {
  if (Array.isArray(v)) return v
  if (!v) return []
  try { const a = JSON.parse(v); return Array.isArray(a) ? a : [] } catch { return [] }
}
function imgUrl(rel) {
  return '/api/prompt-library/asset/' + rel
}
// 图片加载失败时显示占位图，避免绿色裂图
const BROKEN_IMG = 'data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxMDAiIGhlaWdodD0iMTAwIiB2aWV3Qm94PSIwIDAgMTAwIDEwMCI+PHJlY3Qgd2lkdGg9IjEwMCIgaGVpZ2h0PSIxMDAiIGZpbGw9IiNmMGYxZjgiLz48dGV4dCB4PSI1MCIgeT0iNTUiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGZpbGw9IiM5YWEwYzAiIGZvbnQtc2l6ZT0iMTIiPuWbvuagh+WknOaAgee8lueggTwvdGV4dD48L3N2Zz4='
function onImgError(e) {
  const img = e.target
  if (img && img.src !== BROKEN_IMG) img.src = BROKEN_IMG
}
function openLightbox(rel, all) {
  const arr = Array.isArray(all) ? all : [rel]
  lightboxItems.value = arr.map(x => ({ url: imgUrl(x) }))
  lightboxIndex.value = Math.max(0, arr.indexOf(rel))
  lightboxVisible.value = true
}
function closeLightbox() { lightboxVisible.value = false }

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
    const updated = await apiUpload(`/prompt-library/${editing.id}/images`, fd)
    editing.images = parseImages(updated.images)
    pendingImgs.value = []
    await loadList()
    showToast('模版图已上传')
  } catch (err) {
    showToast(err.message || '上传失败')
  }
}
async function removeImage(rel) {
  if (!editing.id) return
  if (!(await confirm('确定删除这张参考图？删除后不可恢复。', { title: '删除确认' }))) return
  const fn = rel.split('/').pop()
  try {
    const updated = await api(`/prompt-library/${editing.id}/images/${encodeURIComponent(fn)}`, 'DELETE')
    editing.images = parseImages(updated.images)
    await loadList()
    showToast('已删除图片')
  } catch (err) {
    showToast(err.message || '删除失败')
  }
}
async function setCoverEdit(img) {
  if (!editing.id) return
  try {
    const updated = await api(`/prompt-library/${editing.id}/set_cover`, 'POST', { image: img })
    editing.images = parseImages(updated.images)
    await loadList()
    if (detail.value && detail.value.id === editing.id) {
      detail.value = { ...updated, images: parseImages(updated.images) }
    }
    showToast('已设为首图')
  } catch (err) {
    showToast(err.message || '设置失败')
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
  await loadAiRules()
  await loadModelConfigs()
  document.addEventListener('click', closeCardMore)
})

</script>

<style scoped>
.pl-page {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  font-family: system-ui, -apple-system, "Segoe UI", Roboto, "PingFang SC", "Microsoft YaHei", sans-serif;
  color: var(--sx-pl-pl-page-color);
}
.pl-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 18px;
}
.pl-title { display: flex; align-items: center; gap: 12px; color: var(--sx-pl-pl-title-color) }
.pl-title h1 { font-size: 22px; margin: 0; color: var(--sx-pl-pl-title-h1-color) }
.pl-sub { margin: 2px 0 0; font-size: 12.5px; color: var(--sx-pl-pl-sub-color) }
.pl-actions { display: flex; gap: 10px }

.btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 9px 16px;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  border: 1px solid transparent;
  transition: .15s;
}
.btn.primary { background: linear-gradient(135deg, var(--sx-pl-btn-primary-background-color) 0%, var(--sx-pl-btn-primary-background-color-1) 100%); color: var(--sx-pl-btn-primary-color); box-shadow: 0 4px 14px var(--sx-pl-btn-primary-box-shadow) }
.btn.primary:hover { filter: brightness(1.05) }
.btn.primary:disabled { opacity: .6; cursor: default }
.btn.danger { background: var(--sx-pl-btn-danger-background-color) !important; color: var(--sx-pl-btn-danger-color) !important; box-shadow: 0 4px 14px var(--sx-pl-btn-danger-box-shadow) }
.btn.danger:hover { background: var(--sx-pl-btn-danger-hover-background-color) !important }
.btn.ghost { background: var(--sx-pl-btn-ghost-background-color); border-color: var(--sx-pl-btn-ghost-border-color); color: var(--sx-pl-btn-ghost-color) }
.btn.ghost:hover { background: var(--sx-pl-btn-ghost-hover-background-color) }

.pl-filters {
  background: var(--sx-pl-pl-filters-background-color);
  border: 1px solid var(--sx-pl-pl-filters-border-color);
  border-radius: 14px;
  padding: 16px;
  margin-bottom: 18px;
  box-shadow: 0 2px 10px var(--sx-pl-pl-filters-box-shadow);
}
.search-wrap { display: flex; align-items: center; gap: 8px; background: var(--sx-pl-search-wrap-background-color); border: 1px solid var(--sx-pl-search-wrap-border-color); border-radius: 10px; padding: 0 12px; color: var(--sx-pl-search-wrap-color) }
.search-wrap .search { flex: 1; border: 0; background: transparent; padding: 11px 0; font-size: 14px; color: var(--sx-pl-search-wrap-search-color); outline: none }
.filter-row { display: flex; align-items: center; gap: 10px; margin-top: 12px; flex-wrap: wrap }
.filter-row.inline { gap: 14px }
.filter-label { font-size: 12.5px; color: var(--sx-pl-filter-label-color); font-weight: 600; flex-shrink: 0 }
.chips { display: flex; gap: 8px; flex-wrap: wrap }
.chip {
  padding: 6px 13px;
  border-radius: 999px;
  border: 1px solid var(--sx-pl-chip-border-color);
  background: var(--sx-pl-chip-background-color);
  color: var(--sx-pl-chip-color);
  font-size: 13px;
  cursor: pointer;
  transition: .15s;
}
.chip:hover { border-color: var(--sx-pl-chip-hover-border-color); color: var(--sx-pl-chip-hover-color) }
.chip.on { background: linear-gradient(135deg, var(--sx-pl-chip-on-background-color) 0%, var(--sx-pl-chip-on-background-color-1) 100%); border-color: transparent; color: var(--sx-pl-chip-on-color); box-shadow: 0 4px 12px var(--sx-pl-chip-on-box-shadow) }
.mini-select { padding: 7px 10px; border-radius: 9px; border: 1px solid var(--sx-pl-mini-select-border-color); background: var(--sx-pl-mini-select-background-color); font-size: 13px; color: var(--sx-pl-mini-select-color); cursor: pointer; transition: .15s }
.mini-select:hover { border-color: var(--sx-pl-mini-select-hover-border-color) }
.count { margin-left: auto; font-size: 12.5px; color: var(--sx-pl-count-color) }

.pl-scroll { flex: 1 1 auto; min-height: 0; overflow-y: auto; padding-right: 4px; scrollbar-width: thin; scrollbar-color: var(--sx-pl-pl-scroll-scrollbar-color) var(--sx-pl-pl-scroll-scrollbar-color-1) }
.pl-scroll::-webkit-scrollbar { width: 8px }
.pl-scroll::-webkit-scrollbar-track { background: var(--sx-pl-pl-scroll-webkit-scrollbar-track-background-color); border-radius: 4px }
.pl-scroll::-webkit-scrollbar-thumb { background: var(--sx-pl-pl-scroll-webkit-scrollbar-thumb-background-color); border-radius: 4px; border: 2px solid transparent; background-clip: content-box }
.pl-scroll::-webkit-scrollbar-thumb:hover { background: var(--sx-pl-pl-scroll-webkit-scrollbar-thumb-hover-background-color) }
.pl-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(290px, 1fr)); gap: 14px }
.pl-card {
  background: var(--sx-pl-pl-card-background-color);
  border: 1px solid var(--sx-pl-pl-card-border-color);
  border-radius: 14px;
  padding: 15px 15px 44px;
  cursor: pointer;
  transition: .15s;
  display: flex;
  flex-direction: column;
  gap: 9px;
  position: relative;
  box-shadow: 0 2px 10px var(--sx-pl-pl-card-box-shadow);
}
.pl-card:hover { border-color: var(--sx-pl-pl-card-hover-border-color); box-shadow: 0 6px 20px var(--sx-pl-pl-card-hover-box-shadow); transform: translateY(-2px) }
.pl-card.dragging { opacity: .5; transform: scale(.98) }
.pl-card.drag-over { border-color: var(--sx-pl-pl-card-drag-over-border-color); box-shadow: 0 0 0 2px var(--sx-pl-pl-card-drag-over-box-shadow) }
.card-top { display: flex; align-items: center; justify-content: space-between; gap: 8px; position: relative }
.pl-handle {
  cursor: grab;
  color: var(--sx-pl-pl-handle-color);
  font-size: 18px;
  line-height: 1;
  flex-shrink: 0;
  padding: 2px 5px;
  border-radius: 7px;
  user-select: none;
  transition: .15s;
}
.pl-handle:hover { color: var(--sx-pl-pl-handle-hover-color); background: var(--sx-pl-pl-handle-hover-background-color) }
.pl-handle:active { cursor: grabbing }
/* 卡片悬停时把手浮现，提示此处可拖拽 */
.pl-card:hover .pl-handle { color: var(--sx-pl-pl-card-hover-pl-handle-color) }
.card-title {
  font-size: 15.5px;
  margin: 0;
  color: var(--sx-pl-card-title-color);
  font-weight: 700;
  line-height: 1.35;
  flex: 1;
  min-width: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.card-meta { display: flex; gap: 6px; flex-wrap: wrap; align-items: center; margin-bottom: 8px }
.badge { font-size: 11.5px; padding: 3px 9px; border-radius: 7px; font-weight: 600 }
.badge.c1 { background: var(--sx-pl-badge-c1-background-color); color: var(--sx-pl-badge-c1-color) }
.badge.src { background: linear-gradient(135deg, var(--sx-pl-badge-src-background-color), var(--sx-pl-badge-src-background-color-1)); color: var(--sx-pl-badge-src-color); border: 1px solid var(--sx-pl-badge-src-border-color); box-shadow: 0 2px 8px var(--sx-pl-badge-src-box-shadow) }
.badge.ot { color: var(--sx-pl-badge-ot-color); min-width: 24px; height: 24px; border-radius: 12px; padding: 0 6px; display: inline-flex; align-items: center; justify-content: center; font-size: 10.5px; flex-shrink: 0; border: 1px solid var(--sx-pl-badge-ot-border-color); background: var(--sx-pl-badge-ot-background-color) }
.badge.ot.t-text { color: var(--sx-pl-badge-ot-t-text-color) !important; background: var(--sx-pl-badge-ot-t-text-background-color) !important; border-color: var(--sx-pl-badge-ot-t-text-border-color) !important }
.badge.ot.t-img { color: var(--sx-pl-badge-ot-t-img-color) !important; background: var(--sx-pl-badge-ot-t-img-background-color) !important; border-color: var(--sx-pl-badge-ot-t-img-border-color) !important }
.badge.ot.t-video { color: var(--sx-pl-badge-ot-t-video-color) !important; background: var(--sx-pl-badge-ot-t-video-background-color) !important; border-color: var(--sx-pl-badge-ot-t-video-border-color) !important }
.badge.ot.t-audio { color: var(--sx-pl-badge-ot-t-audio-color) !important; background: var(--sx-pl-badge-ot-t-audio-background-color) !important; border-color: var(--sx-pl-badge-ot-t-audio-border-color) !important }
.badge.ot.t-other { color: var(--sx-pl-badge-ot-t-other-color) !important; background: var(--sx-pl-badge-ot-t-other-background-color) !important; border-color: var(--sx-pl-badge-ot-t-other-border-color) !important }
.badge.ot.t-custom { color: var(--sx-pl-badge-ot-t-custom-color) !important; background: var(--sx-pl-badge-ot-t-custom-background-color) !important; border-color: var(--sx-pl-badge-ot-t-custom-border-color) !important }
.card-preview { margin: 0; font-size: 13px; color: var(--sx-pl-card-preview-color); line-height: 1.5; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; white-space: pre-wrap }
.tag { font-size: 11.5px; padding: 2px 8px; border-radius: 6px }
.tag.style-tag { background: var(--sx-pl-tag-style-tag-background-color); color: var(--sx-pl-tag-style-tag-color) }
.tag.tool-tag { background: var(--sx-pl-tag-tool-tag-background-color); color: var(--sx-pl-tag-tool-tag-color) }
.card-ops {
  position: absolute;
  left: 15px;
  right: 15px;
  bottom: 12px;
  display: flex;
  gap: 6px;
  opacity: 0;
  pointer-events: none;
  transform: translateY(6px);
  transition: opacity .15s, transform .15s;
}
.pl-card:hover .card-ops { opacity: 1; pointer-events: auto; transform: translateY(0) }
.op {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  flex: 1;
  justify-content: center;
  padding: 7px 0;
  border-radius: 8px;
  border: none;
  background: linear-gradient(135deg, var(--sx-pl-op-background-color) 0%, var(--sx-pl-op-background-color-1) 100%);
  color: var(--sx-pl-op-color);
  font-size: 12.5px;
  cursor: pointer;
  transition: .15s;
  box-shadow: 0 2px 8px var(--sx-pl-op-box-shadow);
}
.op:hover { transform: translateY(-1px); box-shadow: 0 4px 12px var(--sx-pl-op-hover-box-shadow) }
.op.danger { background: linear-gradient(135deg, var(--sx-pl-op-danger-background-color) 0%, var(--sx-pl-op-danger-background-color-1) 100%); box-shadow: 0 2px 8px var(--sx-pl-op-danger-box-shadow) }
.op.danger:hover { box-shadow: 0 4px 12px var(--sx-pl-op-danger-hover-box-shadow) }
/* 卡片右上角「更多」：测试/优化/生图视频收在此处 */
.card-more-wrap { position: relative; flex-shrink: 0 }
.card-more-btn {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  border: 1px solid var(--sx-pl-card-more-btn-border-color);
  background: var(--sx-pl-card-more-btn-background-color);
  color: var(--sx-pl-card-more-btn-color);
  cursor: pointer;
  transition: .15s;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.card-more-btn:hover { background: var(--sx-pl-card-more-btn-hover-background-color); color: var(--sx-pl-card-more-btn-hover-color); border-color: var(--sx-pl-card-more-btn-hover-border-color) }
.card-more-btn.open { background: var(--sx-pl-card-more-btn-open-background-color); color: var(--sx-pl-card-more-btn-open-color); border-color: var(--sx-pl-card-more-btn-open-border-color) }
.card-more { position: absolute; top: calc(100% + 6px); right: 0; bottom: auto; background: var(--sx-pl-card-more-background-color); border: 1px solid var(--sx-pl-card-more-border-color); border-radius: 12px; box-shadow: 0 8px 24px var(--sx-pl-card-more-box-shadow); padding: 6px; display: flex; flex-direction: column; gap: 2px; z-index: 20; min-width: 132px }
.card-more-item { display: flex; align-items: center; gap: 8px; padding: 8px 10px; border: 0; background: transparent; border-radius: 8px; font-size: 13px; color: var(--sx-pl-card-more-item-color); cursor: pointer; text-align: left; white-space: nowrap }
.card-more-item svg { flex-shrink: 0; color: var(--sx-pl-card-more-item-svg-color) }
.card-more-item:hover { background: var(--sx-pl-card-more-item-hover-background-color); color: var(--sx-pl-card-more-item-hover-color) }
.card-more-item:hover svg { color: var(--sx-pl-card-more-item-hover-svg-color) }

.empty { text-align: center; color: var(--sx-pl-empty-color); padding: 60px 20px }
.empty svg { color: var(--sx-pl-empty-svg-color); margin-bottom: 12px }
.empty p { font-size: 14px; max-width: 420px; margin: 0 auto; line-height: 1.6 }

.modal-mask { position: fixed; inset: 0; background: var(--sx-pl-modal-mask-background-color); display: flex; align-items: center; justify-content: center; z-index: 50; padding: 20px }
.modal { background: var(--sx-pl-modal-background-color); border-radius: 16px; width: 100%; max-width: 820px; max-height: 90vh; display: flex; flex-direction: column; box-shadow: 0 24px 60px var(--sx-pl-modal-box-shadow) }
.modal-head { display: flex; align-items: center; justify-content: space-between; padding: 18px 22px; border-bottom: 1px solid var(--sx-pl-modal-head-border-bottom-color) }
.modal-head h2 { margin: 0; font-size: 17px; color: var(--sx-pl-modal-head-h2-color) }
.x { border: 0; background: transparent; font-size: 18px; color: var(--sx-pl-x-color); cursor: pointer; line-height: 1 }
.x:hover { color: var(--sx-pl-x-hover-color) }
.modal-body { padding: 20px 26px 20px 22px; overflow-y: auto; scrollbar-width: thin; scrollbar-color: var(--sx-pl-modal-body-scrollbar-color) transparent }
.modal-body::-webkit-scrollbar { width: 6px }
.modal-body::-webkit-scrollbar-track { background: transparent }
.modal-body::-webkit-scrollbar-thumb { background: var(--sx-pl-modal-body-webkit-scrollbar-thumb-background-color); border-radius: 3px }
.modal-body::-webkit-scrollbar-thumb:hover { background: var(--sx-pl-modal-body-webkit-scrollbar-thumb-hover-background-color) }
.modal-foot { display: flex; justify-content: flex-end; gap: 10px; padding: 14px 22px; border-top: 1px solid var(--sx-pl-modal-foot-border-top-color) }

.icon-btn { border: none; background: transparent; cursor: pointer; font-size: 16px; color: var(--sx-pl-icon-btn-color); padding: 4px 6px; border-radius: 8px; line-height: 1 }
.icon-btn:hover { background: var(--sx-pl-icon-btn-hover-background-color); color: var(--sx-pl-icon-btn-hover-color) }
.del-btn { border: 1px solid var(--sx-pl-del-border-color); background: var(--sx-pl-del-bg-color); color: var(--sx-pl-del-color); cursor: pointer; font-size: 13px; font-weight: 600; padding: 5px 12px; border-radius: 8px; line-height: 1; white-space: nowrap }
.del-btn:hover { background: var(--sx-pl-del-hover-bg-color); color: #fff; border-color: var(--sx-pl-del-hover-bg-color) }
.modal-head h3 { margin: 0; font-size: 17px; color: var(--sx-pl-modal-head-h3-color) }
.modal-sub { margin: 4px 0 0; font-size: 12.5px; color: var(--sx-pl-modal-sub-color) }
.import-modal { max-width: 880px }
.import-raw { width: 100%; min-height: 220px; max-height: 38vh; resize: vertical; border: 1px solid var(--sx-pl-import-raw-border-color); border-radius: 10px; padding: 12px 14px; font-size: 13.5px; line-height: 1.6; font-family: ui-monospace, Menlo, Consolas, monospace; color: var(--sx-pl-import-raw-color); box-sizing: border-box }
.import-row { display: flex; align-items: center; gap: 12px; margin-top: 14px; flex-wrap: wrap }
.import-count { font-size: 13px; color: var(--sx-pl-import-count-color); font-weight: 600 }
.import-ai { display: flex; align-items: flex-start; gap: 12px; margin-top: 16px; padding: 12px 14px; background: var(--sx-pl-import-ai-background-color); border-radius: 10px }
.import-ai-tip { font-size: 12.5px; color: var(--sx-pl-import-ai-tip-color); line-height: 1.5 }

/* 拆分示例 + AI 配置区（导入弹窗预览步） */
.import-example { margin-top: 8px; padding: 10px 12px; background: var(--sx-pl-import-example-background-color); border: 1px dashed var(--sx-pl-import-example-border-color); border-radius: 8px; font-family: ui-monospace, Menlo, Consolas, monospace; font-size: 12.5px; line-height: 1.6; color: var(--sx-pl-import-example-color); white-space: pre-wrap; word-break: break-word; max-height: 150px; overflow-y: auto }
.import-ai-config { display: flex; flex-wrap: wrap; gap: 14px 20px; margin-top: 8px; padding: 12px 14px; background: var(--sx-pl-import-ai-config-background-color); border: 1px solid var(--sx-pl-import-ai-config-border-color); border-radius: 10px }
.cfg-item { display: flex; flex-direction: column; gap: 6px }
.cfg-item > span { font-size: 12px; color: var(--sx-pl-cfg-item-span-color); font-weight: 600 }
.cfg-item select, .cfg-item input[type="range"] { border: 1px solid var(--sx-pl-cfg-item-select-border-color); border-radius: 8px; padding: 7px 10px; font-size: 13px; background: var(--sx-pl-cfg-item-select-background-color); color: var(--sx-pl-cfg-item-select-color); font-family: inherit; outline: none }
.cfg-item select:focus { border-color: var(--sx-pl-cfg-item-select-focus-border-color); box-shadow: 0 0 0 3px var(--sx-pl-cfg-item-select-focus-box-shadow) }
.cfg-item .range-val { font-size: 12px; color: var(--sx-pl-cfg-item-range-val-color); font-weight: 700 }

.import-ai-remembered { margin-top: 10px; padding: 9px 14px; font-size: 13px; background: var(--sx-bg-secondary, #f1f5f9); border: 1px solid var(--sx-border, #e2e8f0); border-radius: 8px; color: var(--sx-text-strong, #1f2937) }
.draft-row.draft-dup { background: #FCEBEB; border: 1px solid #F09595 }
.draft-row.draft-dup .draft-title { border-color: #E24B4A }
.dup-tag { font-size: 12px; color: #A32D2D; font-weight: 600; white-space: nowrap }
.gen-hint-modal { max-width: 460px }
.gen-hint-text { margin: 0; font-size: 14px; line-height: 1.7; color: var(--sx-text-strong, #1f2937); white-space: pre-line }
.att-list { display: flex; flex-direction: column; gap: 6px; margin-bottom: 10px }
.att-item { display: flex; align-items: center; gap: 10px; padding: 6px 10px; background: var(--sx-pl-import-ai-config-background-color, #f8fafc); border: 1px solid var(--sx-pl-import-ai-config-border-color, #e2e8f0); border-radius: 8px; font-size: 13px }
.att-name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap }
.att-size { color: var(--sx-text-tertiary, #94a3b8); font-size: 12px }
.att-dl { color: #185fa5; text-decoration: none; font-size: 13px }
.att-del { border: none; background: transparent; color: #A32D2D; cursor: pointer; font-size: 13px }
.att-upload { display: flex; align-items: center; gap: 10px; flex-wrap: wrap }
.att-tip { font-size: 12px; color: var(--sx-text-tertiary, #94a3b8) }
.att-pending { display: flex; flex-direction: column; gap: 4px; margin-top: 8px }
.att-pending-item { display: flex; align-items: center; gap: 8px; font-size: 12.5px; color: var(--sx-text, #4b5563) }
.att-pending-type { color: #185fa5; font-weight: 600 }
.import-ai-remembered b { color: var(--sx-accent-strong, #185fa5); font-weight: 600 }
.import-ai-remembered.muted { color: var(--sx-text, #4b5563); background: var(--sx-bg-tertiary, #f8fafc) }
.import-ai-remembered.muted a { color: var(--sx-accent-strong, #185fa5); margin: 0 4px; cursor: pointer }
.import-ai-remembered .dim { color: var(--sx-text-tertiary, #94a3b8); margin: 0 4px }
.ai-rule-line { display: flex; align-items: center; gap: 12px; padding: 4px 0; flex-wrap: wrap }
.ai-rule-line .filter-label { min-width: 72px; margin: 0; font-size: 12px; color: var(--sx-text, #4b5563); font-weight: 600 }
.ai-rule-line .mini-select { flex: 1; min-width: 200px; max-width: 320px }
.ai-rule-line.ai-rule-foot { padding-top: 10px; border-top: 1px dashed var(--sx-border, #e2e8f0); margin-top: 4px; justify-content: space-between }
.ai-rule-line .remembered-text { font-size: 13px; color: var(--sx-text-strong, #1f2937) }
.ai-rule-line .remembered-text b { color: #185fa5; font-weight: 600 }
.ai-tags { display: flex; gap: 8px; flex-wrap: wrap }
.ai-tag { display: inline-flex; align-items: center; gap: 6px; padding: 4px 12px; border-radius: 999px; font-size: 12.5px; font-weight: 600; line-height: 1.6 }
.ai-tag em { font-style: normal; font-size: 11px; font-weight: 700; letter-spacing: 0.5px; padding: 1px 6px; border-radius: 4px; background: rgba(255,255,255,0.7); color: inherit; opacity: 0.7 }
.ai-tag.role { background: #E6F1FB; color: #0C447C; border: 1px solid #85B7EB }
.ai-tag.func { background: #EEEDFE; color: #3C3489; border: 1px solid #AFA9EC }
.section-divider { display: flex; align-items: center; gap: 12px; margin: 16px 0 12px; color: #6b7280; font-size: 12px; font-weight: 600; letter-spacing: 0.5px }
.section-divider::before, .section-divider::after { content: ''; flex: 1; height: 1px; background: var(--sx-border, #e2e8f0) }

/* 草稿表头部：作者 + 批量操作 */
.draft-head-actions { display: flex; align-items: center; gap: 10px; flex-wrap: wrap }
.owner-input { width: 150px; border: 1px solid var(--sx-pl-owner-input-border-color); border-radius: 8px; padding: 7px 10px; font-size: 13px; color: var(--sx-pl-owner-input-color); font-family: inherit; outline: none }
.owner-input:focus { border-color: var(--sx-pl-owner-input-focus-border-color); box-shadow: 0 0 0 3px var(--sx-pl-owner-input-focus-box-shadow) }

/* 草稿行内图片 */
.draft-img { display: flex; align-items: center; gap: 8px; flex-wrap: wrap }
.draft-img-thumb { position: relative; width: 46px; height: 46px; border-radius: 8px; overflow: hidden; border: 1px solid var(--sx-pl-draft-img-thumb-border-color); background: var(--sx-pl-draft-img-thumb-background-color); display: inline-flex; align-items: center; justify-content: center }
.draft-img-thumb img { width: 100%; height: 100%; object-fit: cover }

/* 草稿锚点高亮 + 闪烁 */
.import-drafts .draft-row.draft-anchor { border-color: var(--sx-pl-import-drafts-draft-row-draft-anchor-border-color); box-shadow: 0 0 0 3px var(--sx-pl-import-drafts-draft-row-draft-anchor-box-shadow) }
.draft-row.draft-flash { animation: draftFlash 1.2s ease }
@keyframes draftFlash {
  0% { background: var(--sx-pl-keyframes-draftFlash-kf); }
  30% { background: var(--sx-pl-keyframes-draftFlash-kf-1); }
  100% { background: var(--sx-pl-keyframes-draftFlash-kf-2); }
}

/* 导入后 AI 持续跟进 */
.import-follow { margin-top: 16px; padding: 12px 14px; background: var(--sx-pl-import-follow-background-color); border: 1px solid var(--sx-pl-import-follow-border-color); border-radius: 10px }
.import-follow-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px }
.import-follow-head > span { font-size: 13px; font-weight: 700; color: var(--sx-pl-import-follow-head-span-color) }
.import-follow-input { width: 100%; min-height: 64px; resize: vertical; border: 1px solid var(--sx-pl-import-follow-input-border-color); border-radius: 8px; padding: 8px 10px; font-size: 13px; line-height: 1.5; font-family: inherit; color: var(--sx-pl-import-follow-input-color); box-sizing: border-box }
.import-follow-input:focus { outline: none; border-color: var(--sx-pl-import-follow-input-focus-border-color); box-shadow: 0 0 0 3px var(--sx-pl-import-follow-input-focus-box-shadow) }
.import-follow-config { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; margin-bottom: 8px }
.import-follow-config .cfg-item { display: flex; align-items: center; gap: 6px }
.import-follow-config .mini-select { min-width: 110px }
.import-follow-config .mini-range { width: 90px }
.import-follow-tip { display: block; font-size: 12px; color: var(--sx-pl-import-ai-tip-color); margin-bottom: 8px; line-height: 1.4 }

/* AI 规则编辑弹窗 */
.ai-rule-text { width: 100%; border: 1px solid var(--sx-pl-ai-rule-text-border-color); border-radius: 9px; padding: 10px 12px; font-size: 13px; line-height: 1.6; font-family: ui-monospace, Menlo, Consolas, monospace; color: var(--sx-pl-ai-rule-text-color); box-sizing: border-box; resize: vertical }
.ai-rule-text:focus { outline: none; border-color: var(--sx-pl-ai-rule-text-focus-border-color); box-shadow: 0 0 0 3px var(--sx-pl-ai-rule-text-focus-box-shadow) }
.ai-rule-hint { margin-top: 6px; font-size: 12px; color: var(--sx-pl-ai-rule-hint-color); line-height: 1.5 }

/* 卡片级 AI 结果弹窗 */
.ai-loading { display: flex; align-items: center; gap: 8px; padding: 14px; font-size: 13.5px; color: var(--sx-pl-ai-loading-color) }
.ai-loading .spinner { width: 16px; height: 16px; border: 2px solid var(--sx-pl-ai-loading-spinner-border-color); border-top-color: var(--sx-pl-ai-loading-spinner-border-top-color); border-radius: 50%; animation: spin .7s linear infinite }
.ai-result-toolbar { display: flex; align-items: center; justify-content: flex-end; gap: 8px; margin-top: 10px }
.ai-result { background: var(--sx-pl-ai-result-background-color); border: 1px solid var(--sx-pl-ai-result-border-color); border-radius: 10px; padding: 14px; font-size: 13px; line-height: 1.7; color: var(--sx-pl-ai-result-color); white-space: pre-wrap; word-break: break-word; max-height: 50vh; overflow-y: auto; margin: 0; font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace }

/* AI 帮我写一条（编辑弹窗顶部） */
.ai-gen-block { border: 1px dashed var(--sx-pl-ai-gen-block-border-color); background: var(--sx-pl-ai-gen-block-background-color); border-radius: 12px; padding: 12px 14px; margin-bottom: 14px }
.ai-gen-title { font-size: 13px; font-weight: 700; color: var(--sx-pl-ai-gen-title-color); margin-bottom: 8px }
.ai-gen-row { display: flex; gap: 10px; align-items: flex-start }
.ai-gen-input { flex: 1; border: 1px solid var(--sx-pl-ai-gen-input-border-color); border-radius: 8px; padding: 8px 10px; font-size: 13px; resize: vertical; font-family: inherit; line-height: 1.5 }
.ai-gen-input:focus { outline: none; border-color: var(--sx-pl-ai-gen-input-focus-border-color) }
.ai-gen-hint { font-size: 12px; color: var(--sx-pl-ai-gen-hint-color); margin-top: 6px; line-height: 1.5 }
.mini-spin { display: inline-block; width: 12px; height: 12px; border: 2px solid var(--sx-pl-mini-spin-border-color); border-top-color: var(--sx-pl-mini-spin-border-top-color); border-radius: 50%; animation: spin .7s linear infinite; vertical-align: -1px; margin-right: 5px }
.mini-spin.dark { border-color: var(--sx-pl-mini-spin-dark-border-color); border-top-color: var(--sx-pl-mini-spin-dark-border-top-color) }
.import-draft-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; font-size: 13px; color: var(--sx-pl-import-draft-head-color); font-weight: 600 }
.draft-batch-bar { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin-bottom: 14px }
.batch-label { font-size: 12.5px; color: var(--sx-pl-import-draft-head-color); font-weight: 600; white-space: nowrap }
.batch-mask { z-index: 60 }
.batch-modal { max-width: 420px; width: 100% }
.batch-select, .batch-input { width: 100%; box-sizing: border-box }
.import-drafts { display: flex; flex-direction: column; gap: 14px }
.draft-row { display: flex; gap: 10px; padding: 14px; border: 1px solid var(--sx-pl-draft-row-border-color); border-radius: 12px; background: var(--sx-pl-draft-row-background-color) }
.draft-idx { width: 22px; flex-shrink: 0; font-size: 13px; font-weight: 700; color: var(--sx-pl-draft-idx-color); text-align: center; padding-top: 6px }
.draft-fields { flex: 1; display: flex; flex-direction: column; gap: 8px }
.draft-line { display: flex; gap: 8px; align-items: center; flex-wrap: wrap }
.draft-title { width: 100%; border: 1px solid var(--sx-pl-draft-title-border-color); border-radius: 8px; padding: 8px 10px; font-size: 13.5px; box-sizing: border-box }
.draft-content { width: 100%; min-height: 160px; resize: vertical; border: 1px solid var(--sx-pl-draft-content-border-color); border-radius: 8px; padding: 8px 10px; font-size: 13px; line-height: 1.5; font-family: ui-monospace, Menlo, Consolas, monospace; color: var(--sx-pl-draft-content-color); box-sizing: border-box }
.title-line { width: 100% }
.meta-line { justify-content: flex-start }
.meta-line .mini-select { min-width: 100px; flex: 1; max-width: 180px }

.fld { display: flex; flex-direction: column; gap: 6px; margin-bottom: 14px }
.fld > span { font-size: 12.5px; color: var(--sx-pl-fld-span-color); font-weight: 600 }
.fld input, .fld select, .fld textarea {
  border: 1px solid var(--sx-pl-fld-input-border-color);
  border-radius: 9px;
  padding: 10px 12px;
  font-size: 14px;
  color: var(--sx-pl-fld-input-color);
  font-family: inherit;
  outline: none;
  transition: .15s;
  background: var(--sx-pl-fld-input-background-color);
}
.fld input:focus, .fld select:focus, .fld textarea:focus { border-color: var(--sx-pl-fld-input-focus-border-color); box-shadow: 0 0 0 3px var(--sx-pl-fld-input-focus-box-shadow) }
.fld textarea { resize: vertical; line-height: 1.6 }
.fld-row { display: flex; gap: 14px }
.fld-row .fld { flex: 1 }
.fld-sep { align-self: flex-end; padding: 0 4px 11px; color: var(--sx-pl-fld-sep-color); font-size: 15px; font-weight: 600 }

.detail-meta { font-size: 12px; color: var(--sx-pl-detail-meta-color); margin-bottom: 10px }
.detail-locpath {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  margin-bottom: 12px;
  padding: 8px 12px;
  background: var(--sx-pl-detail-locpath-background-color);
  border: 1px solid var(--sx-pl-detail-locpath-border-color);
  border-radius: 10px;
  font-size: 12.5px;
  color: var(--sx-pl-detail-locpath-color);
}
.detail-locpath .loc-label { font-weight: 600; color: var(--sx-pl-detail-locpath-loc-label-color); flex-shrink: 0 }
.detail-locpath code {
  background: var(--sx-pl-detail-locpath-code-background-color);
  color: var(--sx-pl-detail-locpath-code-color);
  padding: 2px 7px;
  border-radius: 6px;
  font-family: ui-monospace, Menlo, Consolas, monospace;
  font-size: 12px;
  word-break: break-all;
}
.detail-locpath .loc-note { color: var(--sx-pl-detail-locpath-loc-note-color); font-size: 11.5px }
.detail-head-row { display: flex; gap: 6px; flex-wrap: wrap; align-items: center }
.head-tools { display: flex; align-items: center; gap: 6px }
.head-tools .op {
  flex: 0 0 auto;
  padding: 5px 10px;
  font-size: 12px;
  min-width: 52px;
  background: var(--sx-pl-head-tools-op-background-color);
  border-color: var(--sx-pl-head-tools-op-border-color);
  color: var(--sx-pl-head-tools-op-color);
}
.head-tools .op:hover { background: var(--sx-pl-head-tools-op-hover-background-color); border-color: var(--sx-pl-head-tools-op-hover-border-color) }
.head-tools .op.danger {
  background: var(--sx-pl-head-tools-op-danger-background-color);
  border-color: var(--sx-pl-head-tools-op-danger-border-color);
  color: var(--sx-pl-head-tools-op-danger-color);
}
.head-tools .op.danger:hover { background: var(--sx-pl-head-tools-op-danger-hover-background-color); border-color: var(--sx-pl-head-tools-op-danger-hover-border-color) }
.detail-test { margin-top: 14px; border-top: 1px dashed var(--sx-pl-detail-test-border-top-color); padding-top: 12px }
.detail-test-head { display: flex; align-items: center; justify-content: space-between; font-size: 13px; color: var(--sx-pl-detail-test-head-color); margin-bottom: 8px }
.link-btn { border: none; background: transparent; color: var(--sx-pl-link-btn-color); cursor: pointer; font-size: 13px }
.test-out { background: var(--sx-pl-test-out-background-color); max-height: 40vh }
.test-err { color: var(--sx-pl-test-err-color); font-size: 13px }
.test-loading { color: var(--sx-pl-test-loading-color); font-size: 13px }
.detail-content {
  background: var(--sx-pl-detail-content-background-color);
  border: 1px solid var(--sx-pl-detail-content-border-color);
  border-radius: 10px;
  padding: 14px;
  font-size: 13.5px;
  line-height: 1.7;
  color: var(--sx-pl-detail-content-color);
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 50vh;
  overflow-y: auto;
  margin: 0;
  font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
  scrollbar-width: thin;
  scrollbar-color: var(--sx-pl-detail-content-scrollbar-color) transparent;
  user-select: text;
  cursor: text;
}
.detail-content::-webkit-scrollbar { width: 5px }
.detail-content::-webkit-scrollbar-track { background: transparent }
.detail-content::-webkit-scrollbar-thumb { background: var(--sx-pl-detail-content-webkit-scrollbar-thumb-background-color); border-radius: 3px }
.detail-content::-webkit-scrollbar-thumb:hover { background: var(--sx-pl-detail-content-webkit-scrollbar-thumb-hover-background-color) }
.row-actions { display: flex; align-items: center; gap: 8px }
.sel-copy {
  background: var(--sx-pl-sel-copy-background-color);
  border: 1px solid var(--sx-pl-sel-copy-border-color);
  color: var(--sx-pl-sel-copy-color);
}
.sel-copy:hover { background: var(--sx-pl-sel-copy-hover-background-color); border-color: var(--sx-pl-sel-copy-hover-border-color) }

.toast {
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  background: var(--sx-pl-toast-background-color);
  color: var(--sx-pl-toast-color);
  padding: 16px 32px;
  border-radius: 12px;
  font-size: 16px;
  font-weight: 600;
  max-width: 80vw;
  line-height: 1.5;
  text-align: center;
  box-shadow: 0 10px 30px var(--sx-pl-toast-box-shadow);
  z-index: 9001;
}
.fade-enter-active, .fade-leave-active { transition: opacity .25s }
.fade-enter-from, .fade-leave-to { opacity: 0 }

/* 导出中遮罩 */
.export-mask {
  position: fixed;
  inset: 0;
  z-index: 9000;
  background: var(--sx-pl-export-mask-background-color);
  display: flex;
  align-items: center;
  justify-content: center;
  backdrop-filter: blur(2px);
}
.export-box {
  background: var(--sx-pl-export-box-background-color);
  border-radius: 16px;
  padding: 28px 36px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  box-shadow: 0 24px 60px var(--sx-pl-export-box-box-shadow);
  max-width: 86vw;
  text-align: center;
}
.spinner {
  width: 38px;
  height: 38px;
  border-radius: 50%;
  border: 4px solid var(--sx-pl-spinner-border-color);
  border-top-color: var(--sx-pl-spinner-border-top-color);
  animation: pl-spin .8s linear infinite;
}
@keyframes pl-spin { to { transform: rotate(360deg); } }
.export-text { font-size: 16px; font-weight: 700; color: var(--sx-pl-export-text-color); line-height: 1.4 }
.export-sub { font-size: 13px; color: var(--sx-pl-export-sub-color); line-height: 1.5 }

.detail-section-title { font-size: 13px; font-weight: 700; color: var(--sx-pl-detail-section-title-color); margin: 0 }
.detail-section-row { display: flex; align-items: center; justify-content: space-between; margin: 10px 0 8px }
.detail-divider { height: 1px; background: var(--sx-pl-detail-divider-background-color); margin: 4px 0 10px }
.detail-imgs { display: flex; flex-direction: column; gap: 8px; margin-bottom: 12px }
.detail-img.img-first { width: 100%; aspect-ratio: 16 / 9; object-fit: cover; border-radius: 10px; cursor: zoom-in; border: 1px solid var(--sx-pl-detail-img-img-first-border-color) }
.detail-thumbs { display: flex; gap: 8px; flex-wrap: wrap }
.thumb-wrap { position: relative; border-radius: 10px; overflow: hidden }
.detail-thumb { width: 96px; height: 96px; object-fit: cover; border-radius: 10px; cursor: zoom-in; border: 1px solid var(--sx-pl-detail-thumb-border-color) }
.set-first {
  position: absolute !important;
  bottom: 0 !important;
  left: 0 !important;
  right: 0 !important;
  border: none !important;
  padding: 5px 0 !important;
  font-size: 10px !important;
  line-height: 1.2 !important;
  color: var(--sx-pl-set-first-color) !important;
  cursor: pointer !important;
  background: var(--sx-pl-set-first-background-color) !important;
  opacity: 0;
  transition: opacity .15s;
  text-align: center !important;
  letter-spacing: .2px;
  box-shadow: none !important;
}
.thumb-wrap:hover .set-first { opacity: 1 }

.img-grid { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 10px }
.img-cell { position: relative; width: 110px; height: 110px; border-radius: 10px; overflow: hidden; border: 1px solid var(--sx-pl-img-cell-border-color) }
.img-cell img { width: 100%; height: 100%; object-fit: cover }
.img-del {
  position: absolute !important;
  top: 6px !important;
  right: 6px !important;
  width: 20px !important;
  height: 20px !important;
  border-radius: 50% !important;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 !important;
  border: none !important;
  background: var(--sx-pl-img-del-background-color) !important;
  color: var(--sx-pl-img-del-color) !important;
  font-size: 12px !important;
  line-height: 1 !important;
  cursor: pointer !important;
  opacity: 0;
  transition: opacity .15s;
  box-shadow: none !important;
}
.img-cell:hover .img-del { opacity: 1 }
.img-del:hover { background: var(--sx-pl-img-del-hover-background-color) !important }
.img-cell .cover-badge { position: absolute; top: 4px; left: 4px; background: var(--sx-pl-img-cell-cover-badge-background-color); color: var(--sx-pl-img-cell-cover-badge-color); font-size: 12px; line-height: 1.2; padding: 3px 8px; border-radius: 6px }
.img-cell .set-cover-edit {
  position: absolute !important;
  bottom: 0 !important;
  left: 0 !important;
  right: 0 !important;
  border: none !important;
  padding: 4px 0 !important;
  font-size: 10px !important;
  line-height: 1.2 !important;
  color: var(--sx-pl-img-cell-set-cover-edit-color) !important;
  cursor: pointer !important;
  background: var(--sx-pl-img-cell-set-cover-edit-background-color) !important;
  opacity: 0;
  transition: opacity .15s;
  text-align: center !important;
  border-radius: 0 0 9px 9px !important;
  box-shadow: none !important;
}
.img-cell:hover .set-cover-edit { opacity: 1 }
.img-upload { display: flex; gap: 8px; align-items: center }
.btn.sm { padding: 7px 12px; font-size: 13px }
.img-pending { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 8px }
.pending-thumb { width: 64px; height: 64px; object-fit: cover; border-radius: 8px; border: 1px solid var(--sx-pl-pending-thumb-border-color) }
.img-hint { font-size: 12.5px; color: var(--sx-pl-img-hint-color); margin: -4px 0 14px }
.sk-hint {
  font-size: 12.5px;
  color: var(--sx-pl-sk-hint-color);
  background: var(--sx-pl-sk-hint-background-color);
  border: 1px solid var(--sx-pl-sk-hint-border-color);
  border-radius: 10px;
  padding: 9px 12px;
  margin: 0 0 14px;
  line-height: 1.6;
}
.sk-hint code {
  background: var(--sx-pl-sk-hint-code-background-color);
  color: var(--sx-pl-sk-hint-code-color);
  padding: 1px 6px;
  border-radius: 5px;
  font-family: ui-monospace, Menlo, Consolas, monospace;
  font-size: 12px;
  word-break: break-all;
}
.skill-file-row { display: flex; gap: 10px; align-items: center }
.skill-file-name { font-size: 13px; color: var(--sx-pl-skill-file-name-color); word-break: break-all }

.pl-manage-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  background: var(--sx-pl-pl-manage-bar-background-color);
  border: 1px solid var(--sx-pl-pl-manage-bar-border-color);
  border-radius: 14px;
  padding: 12px 16px;
  margin-bottom: 18px;
  box-shadow: 0 2px 10px var(--sx-pl-pl-manage-bar-box-shadow);
}
.mb-info { font-size: 13px; color: var(--sx-pl-mb-info-color); font-weight: 600 }
.pl-check {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  flex-shrink: 0;
}
.pl-check input { width: 18px; height: 18px; cursor: pointer; accent-color: var(--sx-pl-pl-check-input-accent-color) }

@media (max-width: 640px) {
  .pl-head { flex-direction: column; align-items: stretch; }
  .pl-actions { flex-direction: column; }
  .fld-row { flex-direction: column; gap: 0; }
  .pl-grid { grid-template-columns: 1fr; }
}

@keyframes draftFlashDark {
  0% { background: var(--sx-pl-keyframes-draftFlashDark-kf); }
  30% { background: var(--sx-pl-keyframes-draftFlashDark-kf-1); }
  100% { background: var(--sx-pl-keyframes-draftFlashDark-kf-2); }
}

/* prompt-library dark-only fallbacks (tokenized) */
.export-box { border: 1px solid var(--sx-pl-export-box-border-color); }
.search-wrap svg { color: var(--sx-pl-search-wrap-svg-color); }
.tag { color: var(--sx-pl-tag-color); }
.tag { background: var(--sx-pl-tag-background-color); }
.modal { border: 1px solid var(--sx-pl-modal-border-color); }
.detail-img { border-color: var(--sx-pl-detail-img-border-color); }
.import-raw { background: var(--sx-pl-import-raw-background-color); }
.ai-gen-input { background: var(--sx-pl-ai-gen-input-background-color); }
.ai-gen-input { color: var(--sx-pl-ai-gen-input-color); }
.draft-title { background: var(--sx-pl-draft-title-background-color); }
.draft-content { background: var(--sx-pl-draft-content-background-color); }
.draft-title { color: var(--sx-pl-draft-title-color); }
.card-more-item.goto:hover { background: var(--sx-pl-card-more-item-goto-hover-background-color); }
.card-more-item.goto:hover { color: var(--sx-pl-card-more-item-goto-hover-color); }
.owner-input { background: var(--sx-pl-owner-input-background-color); }
.import-follow-input { background: var(--sx-pl-import-follow-input-background-color); }
.ai-rule-text { background: var(--sx-pl-ai-rule-text-background-color); }
</style>
