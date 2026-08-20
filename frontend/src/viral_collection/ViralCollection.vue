<template>
  <div class="vc-page">
    <!-- 顶部标题栏（固定，不随列表滚动） -->
    <header class="vc-head">
      <div class="vc-title">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z"/>
        </svg>
        <div>
          <h1>爆款收集</h1>
          <p class="vc-sub">右侧浏览器刷抖音 → 截图 → AI 识别填表 → 一键去小说平台找原著</p>
        </div>
      </div>
      <div class="vc-actions">
        <button class="btn ghost" @click="toggleBrowser()">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M2 12h20M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1 4-10 15.3 15.3 0 0 1 4-10z"/></svg>
          {{ browserOpen ? '收起收集' : '去收集' }}
        </button>
        <button class="btn ghost" @click="openSites">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.6 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.6a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9c.14.36.4.66.73.86.3.18.65.28 1 .28H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
          搜索站点
        </button>
        <button class="btn primary" @click="openCreate">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="M12 5v14M5 12h14" /></svg>
          新建爆款
        </button>
      </div>
    </header>

    <!-- 主体：列表模式（红色框 + 卡片列表） / 收集模式（内嵌浏览器占满）。切换由按钮控制。 -->
    <div class="vc-body">

      <!-- 红色框区：统计 + 搜索 + 筛选 + 截图暂存。打开浏览器时收起让位 -->
      <div v-show="!browserOpen" class="vc-toolbar">
        <!-- 统计条 -->
        <section class="vc-stats">
          <div class="stat" :class="{ on: filters.on_hongguo === '' }" @click="setHongguo('')">
            <span class="stat-num">{{ stats.total }}</span><span class="stat-lbl">全部</span>
          </div>
          <div class="stat s-yes" :class="{ on: filters.on_hongguo === '1' }" @click="setHongguo('1')">
            <span class="stat-num">{{ stats.hongguo }}</span><span class="stat-lbl">已上架红果</span>
          </div>
          <div class="stat s-todo" :class="{ on: filters.on_hongguo === '0' }" @click="setHongguo('0')">
            <span class="stat-num">{{ stats.total - stats.hongguo }}</span><span class="stat-lbl">未上架</span>
          </div>
          <div class="stat s-warn">
            <span class="stat-num">{{ stats.noNovel }}</span><span class="stat-lbl">原著待补</span>
          </div>
        </section>

        <!-- 筛选栏 -->
        <section class="vc-filters">
          <div class="search-wrap">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/></svg>
            <input v-model="filters.keyword" class="search" type="text" placeholder="搜索标题 / 作者 / 抖音号 / 剧名 / 原著 / 标签 / 备注…" @input="debouncedLoad" />
          </div>
          <div class="filter-row">
            <span class="filter-label">平台</span>
            <div class="chips">
              <button v-for="p in platformOptions" :key="p" :class="['chip', { on: filters.platform === p }]" @click="setPlatform(p)">{{ p }}</button>
            </div>
          </div>
          <div class="filter-row">
            <span class="filter-label">分类</span>
            <div class="chips">
              <button v-for="c in categoryOptions" :key="c" :class="['chip', { on: filters.category === c }]" @click="setCategory(c)">{{ c }}</button>
            </div>
            <span class="count">共 {{ list.length }} 条</span>
          </div>
        </section>

        <!-- 截图暂存区：浏览器截的图直接进这里；也可 Ctrl+V 粘贴、或截整屏/框选 -->
        <div v-if="tray.length" class="bw-tray">
          <div class="tray-head">
            <b>暂存截图（{{ tray.length }}）</b>
            <button class="tray-clear" type="button" @click="tray = []">清空</button>
          </div>
          <div class="tray-imgs">
            <div v-for="(t, i) in tray" :key="i" class="tray-cell">
              <img :src="t.dataUrl" alt="" @click="openTrayLightbox(i)" />
              <button class="tray-del" type="button" @click.stop="tray.splice(i, 1)">✕</button>
            </div>
          </div>
        </div>

        <!-- AI 识别区：参考提示词库「AI 整理」样式 -->
        <div v-if="tray.length" class="ai-parse-card">
          <div class="section-divider"><span>AI 识别</span></div>
          <div class="ai-parse-config">
            <!-- 第 1 行：名称 -->
            <div class="ai-rule-line">
              <span class="filter-label">名称</span>
              <select v-model="aiRuleId" class="mini-select" @change="onAiRuleChange">
                <option v-if="!aiRules.length" :value="null">暂无可用规则</option>
                <option v-for="r in aiRules" :key="r.id" :value="r.id">{{ r.name }}</option>
              </select>
            </div>
            <!-- 第 2 行：角色和功能 -->
            <div v-if="selectedAiRule" class="ai-rule-line">
              <span class="filter-label">角色 / 功能</span>
              <div class="ai-tags">
                <span class="ai-tag role"><em>角色</em>{{ roleLabel(selectedAiRule.role) }}</span>
                <span class="ai-tag func"><em>功能</em>{{ selectedAiRule.function_key || '截图识别填表' }}</span>
              </div>
            </div>
            <!-- 第 3 行：记住状态 -->
            <div v-if="selectedAiRule" class="ai-rule-line ai-rule-foot">
              <span class="remembered-text">✓ 已记住：<b>{{ selectedAiRule.name }}</b></span>
            </div>
          </div>
          <div v-if="!selectedAiRule" class="ai-parse-hint muted">
            爆款收集下还没有规则，请到「AI 调用规则」页新建
          </div>
          <div class="ai-parse-action">
            <button class="btn primary sm" :disabled="parsing || !selectedAiRule" @click="aiParseTray">
              <span v-if="parsing" class="mini-spin"></span>
              <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><path d="M21 15l-5-5L5 21"/></svg>
              {{ parsing ? 'AI 识别中…' : 'AI 识别并新建' }}
            </button>
            <span class="ai-parse-tip">AI 按所选规则识别截图中的爆款信息，自动填入新建表单，可再手动改。</span>
          </div>
          <div v-if="parseError" class="parse-error">识别失败：{{ parseError }}</div>
        </div>
      </div>

      <!-- 内嵌浏览器（点「去收集」后展开，占满主区高度） -->
      <div v-show="browserOpen" class="vc-browser">
        <div class="bw-bar">
          <div class="bw-bar-row">
            <button class="bw-ico" title="后退" @click="wvGoBack">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 18l-6-6 6-6"/></svg>
            </button>
            <button class="bw-ico" title="前进" @click="wvGoForward">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 18l6-6-6-6"/></svg>
            </button>
            <button class="bw-ico" title="刷新" @click="wvReload">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12a9 9 0 0 1 15.5-6.3L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-15.5 6.3L3 16"/><path d="M3 21v-5h5"/></svg>
            </button>
            <input class="bw-url" v-model="urlInput" @keydown.enter="goUrl" placeholder="输入网址…" />
            <button class="bw-go" @click="goUrl">前往</button>
          </div>
          <div class="bw-bar-row bw-quick">
            <button v-for="s in QUICK_SITES" :key="s.name" class="bw-chip" @click="goSite(s.url)">{{ s.name }}</button>
          </div>
        </div>
        <div ref="wvWrap" class="bw-view">
          <webview
            ref="wv"
            :src="wvSrc"
            class="bw-webview"
            partition="persist:viral"
            :useragent="UA"
            @dom-ready="onWvReady"
            @will-navigate="onWvNavigate"
            @will-redirect="onWvNavigate"
            @did-navigate-in-page="onWvNavigateInPage"
            @new-window="onWvNewWindow"
          ></webview>
          <div v-if="!wvSrc" class="bw-placeholder">
            <p>输入网址或点上方快捷站点开始浏览。</p>
            <p class="tip">登录状态会保存，下次打开不用重新扫码。</p>
          </div>
        </div>
        <div class="bw-foot">
          <div class="bw-shot-tip">
            <b>截图建议：</b>
            <span>① 爆款视频页（必截）</span>
            <span>② 评论区（至少 2 张，找小说线索）</span>
            <span>③ 作者主页（视情况）</span>
            <span>④ 播放量页面（视情况）</span>
          </div>
          <div class="bw-shot-ops">
            <span class="bw-hint">截图直接进暂存区</span>
            <button class="btn ghost sm" :disabled="!wvSrc" @click="captureView">截取浏览器</button>
            <button class="btn ghost sm" @click="captureScreen">截整屏</button>
            <button class="btn ghost sm" @click="captureRegion">框选截图</button>
          </div>
        </div>
      </div>

      <!-- 卡片列表（打开浏览器时收起；与浏览器互斥显示） -->
      <div v-show="!browserOpen" class="vc-list">
        <div v-if="list.length" class="vc-grid">
          <article v-for="item in list" :key="item.id" class="vc-card">
            <div class="card-main" @click="openDetail(item)">
              <div class="card-cover" v-if="item.screenshots.length">
                <img :src="imgUrl(item.screenshots[0])" alt="" />
                <span v-if="item.screenshots.length > 1" class="cover-count">{{ item.screenshots.length }} 图</span>
              </div>
              <div class="card-top">
                <h3 class="card-title">{{ item.title || '（无标题）' }}</h3>
                <span v-if="item.on_hongguo" class="badge hg">红果</span>
              </div>
              <div class="card-badges">
                <span v-if="item.platform" class="badge plat">{{ item.platform }}</span>
                <span v-if="item.category" class="badge cat">{{ item.category }}</span>
                <span v-if="item.username" class="badge user">@{{ item.username }}</span>
              </div>
              <div class="card-nums">
                <span v-if="item.likes" title="点赞">♥ {{ item.likes }}</span>
                <span v-if="item.comment_count" title="评论">💬 {{ item.comment_count }}</span>
                <span v-if="item.favorites" title="收藏">★ {{ item.favorites }}</span>
                <span v-if="item.share_count" title="分享">↗ {{ item.share_count }}</span>
                <span v-if="item.play_count" title="播放">▶ {{ item.play_count }}</span>
              </div>
              <div class="card-novel" :class="{ missing: !item.original_novel }">
                <span>原著</span><b>{{ item.original_novel || '待补' }}</b>
              </div>
              <div v-if="item.tags" class="card-tags">
                <span v-for="t in splitTags(item.tags)" :key="t" class="tag">#{{ t }}</span>
              </div>
            </div>
            <div class="card-ops" @click.stop>
              <button v-if="item.link" class="vc-op" title="打开原视频" @click="openExternal(item.link)">打开</button>
              <button class="vc-op" title="去小说平台搜" @click="openSearchFor(item)">找原著</button>
              <button class="vc-op" title="编辑" @click="openEdit(item)">编辑</button>
              <button class="vc-op danger" title="删除" @click="remove(item)">删除</button>
            </div>
          </article>
        </div>

        <div v-else class="empty">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="room"><path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z"/></svg>
          <p>还没有收集爆款。点右上角「去收集」打开浏览器刷抖音，看到好片就截图，它会进暂存区，让 AI 帮你填表。</p>
        </div>
      </div>

    </div>

    <!-- 框选截图遮罩：先截整屏，用户拖选区域，松开即裁剪该区域入暂存区 -->
    <teleport to="body">
      <div
        v-if="showRegion"
        class="region-mask"
        @mousedown="regionStart"
        @mousemove="regionMove"
        @mouseup="regionEnd"
      >
        <img class="region-bg" :src="regionBg" alt="" draggable="false" />
        <div v-if="regionRect.w > 0 && regionRect.h > 0" class="region-box" :style="regionBoxStyle"></div>
        <div class="region-tip">按住鼠标拖选区域，松开即截图（按 Esc 取消）</div>
      </div>
    </teleport>

    <!-- 新建 / 编辑弹窗 -->
    <div v-if="showEditor" class="modal-mask" @click.self="closeEditor">
      <div class="modal">
        <div class="modal-head">
          <h2>{{ editing.id ? '编辑爆款' : '新建爆款' }}</h2>
          <button class="x" @click="closeEditor">✕</button>
        </div>
        <div class="modal-body">
          <!-- AI 识别补充区：暂存区识别不全时补传图片，结果只补缺失字段 -->
          <div class="ai-box">
            <div class="ai-row">
              <b>识别补充</b>
              <span class="ai-rule-name" v-if="selectedAiRule">{{ selectedAiRule.name }}</span>
              <input ref="aiInput" type="file" accept="image/*" multiple hidden @change="onAiFilesPicked" />
              <button class="btn ghost sm" type="button" @click="aiInput?.click()">选图片</button>
              <button class="btn primary sm" type="button" :disabled="parsing || !aiFiles.length" @click="aiParseFiles">
                {{ parsing ? '识别中…' : `识别 ${aiFiles.length || ''}` }}
              </button>
            </div>
            <div v-if="aiFiles.length" class="ai-thumbs">
              <img v-for="(f, i) in aiFiles" :key="i" :src="f.preview" alt="" />
            </div>
            <p class="ai-tip">暂存区截图识别不全时，可在此补传图片补充识别；支持 Ctrl+V 粘贴，结果只补空缺字段，不会覆盖已填内容。</p>
          </div>

          <div class="fld-row">
            <label class="fld">
              <span>标题 *</span>
              <input ref="titleInput" v-model="editing.title" type="text" placeholder="视频标题 / 作品名" />
            </label>
            <label class="fld sm-fld">
              <span>平台</span>
              <input v-model="editing.platform" type="text" placeholder="抖音 / 快手 / 红果" list="vc-platforms" />
              <datalist id="vc-platforms">
                <option v-for="p in meta.platforms" :key="p" :value="p" />
              </datalist>
            </label>
            <label class="fld sm-fld">
              <span>分类（视频归属）</span>
              <input v-model="editing.category" type="text" placeholder="AI动画 / 真人短剧" list="vc-categories" />
              <datalist id="vc-categories">
                <option v-for="c in categoryPresets" :key="c" :value="c" />
              </datalist>
            </label>
          </div>

          <label class="fld">
            <span>视频链接</span>
            <div class="novel-line">
              <input v-model="editing.link" type="text" placeholder="https://v.douyin.com/…" />
              <button class="btn ghost sm" type="button" @click="fetchBrowserLink('link')">从浏览器取</button>
              <button class="btn ghost sm" type="button" @click="openLinkInBrowser('link')">打开浏览器 ↗</button>
              <button class="btn ghost sm" type="button" :disabled="!editing.link" @click="copyText(editing.link)">复制</button>
            </div>
          </label>

          <div class="fld-row">
            <label class="fld"><span>剧名</span><input v-model="editing.drama_name" type="text" placeholder="短剧正式名称" /></label>
            <label class="fld"><span>别名 / 又名</span><input v-model="editing.aliases" type="text" placeholder="多个用逗号分隔" /></label>
          </div>

          <div class="fld-row">
            <label class="fld">
              <span>原著小说</span>
              <div class="novel-line">
                <input v-model="editing.original_novel" type="text" placeholder="改编自哪本小说（查到再填）" />
                <button class="btn ghost sm" type="button" :disabled="!searchKeyOf(editing)" @click="searchNovelNow">去搜</button>
              </div>
            </label>
            <label class="fld sm-fld">
              <span>已上架红果</span>
              <div class="hg-switch">
                <button type="button" class="sw" :class="{ on: !editing.on_hongguo }" @click="editing.on_hongguo = 0">否</button>
                <button type="button" class="sw sw-yes" :class="{ on: !!editing.on_hongguo }" @click="editing.on_hongguo = 1">是</button>
              </div>
            </label>
          </div>

          <div v-if="aiKeywords.length" class="kw-box">
            <span class="kw-label">AI 提取的疑似原著 / 关键词：</span>
            <button v-for="k in aiKeywords" :key="k" class="kw" type="button" @click="searchKeyword(k)">{{ k }} ↗</button>
          </div>

          <div class="fld-row">
            <label class="fld"><span>作者 / 账号</span><input v-model="editing.username" type="text" placeholder="账号名" /></label>
            <label class="fld"><span>抖音号</span><input v-model="editing.douyin_id" type="text" placeholder="抖音号 / 主页 ID" /></label>
          </div>

          <label class="fld"><span>可借鉴 / 亮点</span><textarea v-model="editing.learn_from" rows="3" placeholder="从截图能看到的：画面风格、封面文案、字幕、配音、评论区互动…"></textarea></label>
          <label class="fld"><span>小说线索</span><textarea v-model="editing.novel_clue" rows="3" placeholder="评论区提到的书名、主角名、梗概…"></textarea></label>

          <div class="fld">
            <div class="fld-head">
              <span>视频标签</span>
              <span class="fld-hint">原视频 # 号标签，多个用逗号分隔</span>
              <button type="button" class="tag-toggle" @click="showVideoTags = !showVideoTags">{{ showVideoTags ? '收起清单' : '+ 从清单选' }}</button>
            </div>
            <input v-model="editing.tags" type="text" placeholder="如 #古风, #萌娃" />
            <div v-if="showVideoTags" class="tag-cloud">
              <template v-for="grp in videoTagOptions" :key="grp.label">
                <div class="tc-label">{{ grp.label }}</div>
                <button v-for="t in grp.options" :key="t" type="button" class="tag-chip"
                        :class="{ on: hasTag('tags', t) }" @click="toggleTag('tags', t)">{{ t }}</button>
              </template>
            </div>
          </div>

          <div class="fld">
            <div class="fld-head">
              <span>小说标签</span>
              <span class="fld-hint">AI 按题材推断，多个用逗号分隔</span>
              <button type="button" class="tag-toggle" @click="showNovelTags = !showNovelTags">{{ showNovelTags ? '收起清单' : '+ 从清单选' }}</button>
            </div>
            <input v-model="editing.novel_tags" type="text" placeholder="如 玄幻, 重生, 甜宠" />
            <div v-if="showNovelTags" class="tag-cloud">
              <template v-for="grp in novelTagOptions" :key="grp.label">
                <div class="tc-label">{{ grp.label }}</div>
                <button v-for="t in grp.options" :key="t" type="button" class="tag-chip"
                        :class="{ on: hasTag('novel_tags', t) }" @click="toggleTag('novel_tags', t)">{{ t }}</button>
              </template>
            </div>
          </div>

          <!-- 选填数据区：对收集意义不大，放最底部并标注选填 -->
          <div class="opt-block">
            <div class="opt-title">选填数据（识别到就填，没有可留空）</div>
            <div class="fld-row">
              <label class="fld"><span>点赞</span><input v-model="editing.likes" type="text" placeholder="如 12.3w" /></label>
              <label class="fld"><span>评论数</span><input v-model="editing.comment_count" type="text" placeholder="如 182" /></label>
              <label class="fld"><span>收藏</span><input v-model="editing.favorites" type="text" placeholder="如 8.9w" /></label>
            </div>
            <div class="fld-row">
              <label class="fld"><span>分享 / 转发</span><input v-model="editing.share_count" type="text" placeholder="如 487" /></label>
              <label class="fld"><span>播放量</span><input v-model="editing.play_count" type="text" placeholder="如 500w" /></label>
            </div>
            <div class="fld-row">
              <label class="fld"><span>关注数</span><input v-model="editing.following" type="text" placeholder="如 233" /></label>
              <label class="fld"><span>粉丝数</span><input v-model="editing.followers" type="text" placeholder="如 2.1w" /></label>
              <label class="fld"><span>上架集数</span><input v-model="editing.works_count" type="text" placeholder="如 24" /></label>
            </div>
            <label class="fld">
              <span>主页链接</span>
              <div class="novel-line">
                <input v-model="editing.homepage_link" type="text" placeholder="作者主页 URL（在浏览器登录后可完整查看）" />
                <button class="btn ghost sm" type="button" @click="fetchBrowserLink('homepage_link')">从浏览器取</button>
                <button class="btn ghost sm" type="button" @click="openLinkInBrowser('homepage_link')">打开浏览器 ↗</button>
                <button class="btn ghost sm" type="button" :disabled="!editing.homepage_link" @click="copyText(editing.homepage_link)">复制</button>
              </div>
            </label>
            <label class="fld"><span>作者简介 / 签名</span><textarea v-model="editing.bio" rows="2" placeholder="主页简介 / 签名文字"></textarea></label>
          </div>

          <label class="fld"><span>备注</span><input v-model="editing.note" type="text" placeholder="补充说明…" /></label>

          <!-- 截图管理 -->
          <div class="fld" v-if="editing.id">
            <span>截图（可多张）</span>
            <div class="img-grid">
              <div v-for="(img, i) in editing.screenshots" :key="i" class="img-cell">
                <img :src="imgUrl(img)" alt="" @click="openLightbox(img, editing.screenshots)" />
                <div class="img-tools" @click.stop>
                  <button class="img-tool del" type="button" title="删除" @click="removeScreenshot(img)">×</button>
                </div>
              </div>
            </div>
            <div class="img-upload">
              <input ref="shotInput" type="file" accept="image/*" multiple hidden @change="onShotsPicked" />
              <button class="btn ghost sm" type="button" @click="shotInput?.click()">+ 选择截图</button>
              <button class="btn primary sm" type="button" :disabled="!pendingShots.length" @click="uploadShots">上传 {{ pendingShots.length || '' }}</button>
            </div>
            <div v-if="pendingShots.length" class="img-pending">
              <img v-for="(p, i) in pendingShots" :key="i" :src="p.preview" class="pending-thumb" alt="" />
            </div>
          </div>
          <p v-else class="img-hint">
            {{ tray.length ? `保存后会自动把暂存区的 ${tray.length} 张截图挂到这条记录上。` : '保存后即可上传截图。' }}
          </p>
        </div>
        <div class="modal-foot">
          <button class="btn ghost" @click="closeEditor">取消</button>
          <button class="btn primary" :disabled="saving" @click="save">{{ saving ? '保存中…' : '保存' }}</button>
        </div>
      </div>
    </div>

    <!-- 详情弹窗 -->
    <div v-if="showDetail" class="modal-mask" @click.self="showDetail = false">
      <div class="modal">
        <div class="modal-head">
          <h2>{{ detail.title }}</h2>
          <button class="x" @click="showDetail = false">✕</button>
        </div>
        <div class="modal-body">
          <div class="detail-badges">
            <span v-if="detail.platform" class="badge plat">{{ detail.platform }}</span>
            <span v-if="detail.category" class="badge cat">{{ detail.category }}</span>
            <span v-if="detail.on_hongguo" class="badge hg">已上架红果</span>
            <div v-if="detail.tags" class="detail-tags">
              <span v-for="t in splitTags(detail.tags)" :key="t" class="tag">#{{ t }}</span>
            </div>
          </div>

          <div v-if="detail.link" class="detail-url">
            <a href="javascript:void(0)" @click="openExternal(detail.link)">{{ detail.link }}</a>
          </div>

          <div class="detail-grid">
            <div class="db-label">爆款信息</div>
            <div class="dg-cell" v-if="detail.drama_name"><span>剧名</span><b>{{ detail.drama_name }}</b></div>
            <div class="dg-cell" v-if="detail.aliases"><span>别名</span><b>{{ detail.aliases }}</b></div>
            <div class="dg-cell"><span>原著小说</span><b :class="{ miss: !detail.original_novel }">{{ detail.original_novel || '待补' }}</b></div>
            <div class="dg-cell" v-if="detail.username"><span>作者</span><b>{{ detail.username }}</b></div>
            <div class="dg-cell" v-if="detail.douyin_id"><span>抖音号</span><b>{{ detail.douyin_id }}</b></div>
            <div class="dg-cell" v-if="detail.followers"><span>粉丝</span><b>{{ detail.followers }}</b></div>
            <div class="dg-cell" v-if="detail.following"><span>关注</span><b>{{ detail.following }}</b></div>
            <div class="dg-cell" v-if="detail.works_count"><span>上架集数</span><b>{{ detail.works_count }}</b></div>
            <div class="dg-cell" v-if="detail.likes"><span>点赞</span><b>{{ detail.likes }}</b></div>
            <div class="dg-cell" v-if="detail.comment_count"><span>评论</span><b>{{ detail.comment_count }}</b></div>
            <div class="dg-cell" v-if="detail.favorites"><span>收藏</span><b>{{ detail.favorites }}</b></div>
            <div class="dg-cell" v-if="detail.share_count"><span>分享</span><b>{{ detail.share_count }}</b></div>
            <div class="dg-cell" v-if="detail.play_count"><span>播放量</span><b>{{ detail.play_count }}</b></div>
            <div class="dg-cell" v-if="detail.homepage_link">
              <span>主页</span>
              <b class="home-link" @click="copyText(detail.homepage_link)">复制链接 ↗</b>
            </div>
            <div class="dg-cell" v-if="detail.bio" style="grid-column: 1 / -1"><span>简介</span><b>{{ detail.bio }}</b></div>
          </div>

          <div class="detail-block" v-if="detail.novel_tags">
            <div class="db-label">小说标签</div>
            <div class="detail-tags">
              <span v-for="t in splitTags(detail.novel_tags)" :key="t" class="tag">#{{ t }}</span>
            </div>
          </div>

          <div v-if="detail.screenshots && detail.screenshots.length" class="detail-imgs">
            <img v-for="(img, i) in detail.screenshots" :key="i" :src="imgUrl(img)" class="detail-img" @click="openLightbox(img, detail.screenshots)" alt="" />
          </div>

          <div class="detail-block" v-if="detail.learn_from">
            <div class="db-label">可借鉴 / 亮点</div>
            <pre class="detail-content">{{ detail.learn_from }}</pre>
          </div>
          <div class="detail-block" v-if="detail.novel_clue">
            <div class="db-label">小说线索</div>
            <pre class="detail-content">{{ detail.novel_clue }}</pre>
          </div>
          <div class="detail-block" v-if="detail.note">
            <div class="db-label">备注</div>
            <div class="detail-text">{{ detail.note }}</div>
          </div>

          <div class="detail-block">
            <div class="db-label">去小说平台找原著</div>
            <div class="site-btns">
              <button v-for="s in sites" :key="s.name" class="chip sm" :disabled="!searchKeyOf(detail)" @click="copySite(s, searchKeyOf(detail))">{{ s.name }} ↗</button>
            </div>
            <p class="ai-tip" v-if="!searchKeyOf(detail)">先填「剧名」或「标题」才能搜。</p>
            <p class="ai-tip app-hint">在上方浏览器里先登录一次抖音，登录态会自动保存（关掉重开也在）。登录后作者主页（关注/粉丝/上架集数/简介）就能完整显示；若有的页面仍要过一次中间页，点一下确认即可，之后一直能开。需要把主页链接带出来时，用这里「复制链接 ↗」或点「打开浏览器 ↗」即可。</p>
          </div>
        </div>
        <div class="modal-foot">
          <button class="btn ghost" @click="showDetail = false">关闭</button>
          <button class="btn primary" @click="openEdit(detail); showDetail = false">编辑</button>
        </div>
      </div>
    </div>

    <!-- 搜索站点配置弹窗 -->
    <div v-if="showSites" class="modal-mask" @click.self="showSites = false">
      <div class="modal narrow">
        <div class="modal-head">
          <h2>小说平台搜索站点</h2>
          <button class="x" @click="showSites = false">✕</button>
        </div>
        <div class="modal-body">
          <p class="ai-tip">URL 里用 <code>{q}</code> 代表关键词。点「去搜」时用系统浏览器打开，结果自己看，工具不做自动抓取。</p>
          <div v-for="(s, i) in sitesDraft" :key="i" class="site-row">
            <input v-model="s.name" class="site-name" type="text" placeholder="站点名" />
            <input v-model="s.url" class="site-url" type="text" placeholder="https://xxx.com/search?q={q}" />
            <button class="vc-op danger" type="button" @click="sitesDraft.splice(i, 1)">删</button>
          </div>
          <button class="btn ghost sm" type="button" @click="sitesDraft.push({ name: '', url: '' })">+ 添加站点</button>
        </div>
        <div class="modal-foot">
          <button class="btn ghost" @click="showSites = false">取消</button>
          <button class="btn primary" @click="saveSites">保存</button>
        </div>
      </div>
    </div>

    <MediaLightbox
      :visible="lightboxVisible"
      :items="lightboxItems"
      :index="lightboxIndex"
      @close="lightboxVisible = false"
      @update:index="lightboxIndex = $event"
    />

    <transition name="fade">
      <div v-if="toast" class="toast">{{ toast }}</div>
    </transition>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
import { api, apiUpload } from '../common/http.js'
import { confirm } from '../common/useConfirm.js'
import MediaLightbox from '../filespace/MediaLightbox.vue'
import {
  VIDEO_CATEGORIES, VIDEO_TAG_GROUPS, NOVEL_TAG_GROUPS, mergeOptions,
} from './taxonomy.js'

// 内嵌浏览器（方案 C：独立窗口）已由桌面壳单独承载，主窗口只负责收集列表与暂存区
const el = () => window.electronAPI || null

const list = ref([])
const meta = reactive({ platforms: [], categories: [] })
const filters = reactive({ keyword: '', platform: '全部', category: '全部', on_hongguo: '' })
const toast = ref('')
let toastTimer = null

// 截图状态（截图来自独立浏览器窗口经 IPC 发回，也可在主窗口直接截整屏/框选、或 Ctrl+V 粘贴）
const capturing = ref(false)
const tray = ref([])          // [{ dataUrl }]
// 暂存区持久化：刷新/重进页面后未识别的截图不会丢
function saveTray() {
  try {
    localStorage.setItem(TRAY_STORAGE_KEY, JSON.stringify(tray.value.slice(-20)))
  } catch (e) { /* localStorage 满则静默失败 */ }
}
function restoreTray() {
  try {
    const raw = localStorage.getItem(TRAY_STORAGE_KEY)
    const arr = raw ? JSON.parse(raw) : []
    tray.value = Array.isArray(arr) ? arr.filter(t => t && t.dataUrl) : []
  } catch (e) { tray.value = [] }
}
watch(tray, saveTray, { deep: true })

const parsing = ref(false)
const parseError = ref('')

// AI 规则（识别截图填表走 ai_rule 机制，规则内容可在 AI 规则管理页调整）
const AI_RULE_MENU = '爆款收集'
const AI_RULE_PREF_KEY = 'ai_rule.爆款收集'
const TRAY_STORAGE_KEY = 'viral.tray'
const aiRules = ref([])
const aiRuleId = ref(null)
const selectedAiRule = computed(() => aiRules.value.find(r => r.id === aiRuleId.value) || null)
const ROLE_LABELS = { organize: '整理', review: '审核', generate: '生成', parser: '解析', assistant: '助手' }

async function loadAiRules() {
  try {
    const list = await api('/ai-rules?menu=' + encodeURIComponent(AI_RULE_MENU) + '&enabled=1', 'GET')
    aiRules.value = Array.isArray(list) ? list : []
    if (!aiRuleId.value && aiRules.value.length) aiRuleId.value = aiRules.value[0].id
    await restoreAiRuleSelection()
  } catch (e) { /* 规则加载失败不阻断识别 */ }
}
// 记住选择：localStorage（快）→ 后端 prefs（永久）→ 默认第一条
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
  let hit = aiRules.value.find(r => r.id === snap.rule_id)
  if (!hit && snap.name) hit = aiRules.value.find(r => r.name === snap.name)
  aiRuleId.value = hit ? hit.id : aiRules.value[0].id
}
function onAiRuleChange() {
  const r = selectedAiRule.value
  if (!r) return
  const snap = { rule_id: r.id, name: r.name, menu: r.menu, function_key: r.function_key, role: r.role }
  try { localStorage.setItem(AI_RULE_PREF_KEY, JSON.stringify(snap)) } catch (e) { /* ignore */ }
  api('/prefs/' + encodeURIComponent(AI_RULE_PREF_KEY), 'PUT', { value: snap }).catch(() => {})
}
function roleLabel(role) {
  return ROLE_LABELS[role] || role || '整理'
}

// 弹窗
const showEditor = ref(false)
const showDetail = ref(false)
const showSites = ref(false)
const editing = reactive(blankForm())
const detail = ref({})
const saving = ref(false)
const aiKeywords = ref([])

const titleInput = ref(null)
const aiInput = ref(null)
const shotInput = ref(null)
const aiFiles = ref([])       // [{ file, preview }]
const pendingShots = ref([])  // [{ file, preview }]
const showVideoTags = ref(false)   // 标签清单默认折叠
const showNovelTags = ref(false)

// 站点
const sites = ref([])
const sitesDraft = ref([])

// 灯箱
const lightboxVisible = ref(false)
const lightboxItems = ref([])
const lightboxIndex = ref(0)

const platformOptions = computed(() => ['全部', ...meta.platforms])
const categoryOptions = computed(() => ['全部', ...meta.categories])

// 预设 + 历史记录合并后的标签来源（实现"可续加"）
const usedTags = computed(() => {
  const set = new Set()
  for (const r of list.value) {
    for (const t of splitTags(r.tags)) set.add(t)
    for (const t of splitTags(r.novel_tags)) set.add(t)
  }
  return [...set]
})
const videoTagOptions = computed(() => VIDEO_TAG_GROUPS.map(g => ({
  label: g.label, options: mergeOptions(g.options, usedTags.value),
})))
const novelTagOptions = computed(() => NOVEL_TAG_GROUPS.map(g => ({
  label: g.label, options: mergeOptions(g.options, usedTags.value),
})))
const categoryPresets = computed(() => mergeOptions(VIDEO_CATEGORIES, meta.categories))

function hasTag(field, t) {
  return splitTags(editing[field]).includes(t)
}
function toggleTag(field, t) {
  const cur = splitTags(editing[field])
  const i = cur.indexOf(t)
  if (i >= 0) cur.splice(i, 1)
  else cur.push(t)
  editing[field] = cur.join(', ')
}
const stats = computed(() => ({
  total: list.value.length,
  hongguo: list.value.filter(x => x.on_hongguo).length,
  noNovel: list.value.filter(x => !x.original_novel).length,
}))

function blankForm() {
  return {
    id: null, platform: '抖音', category: 'AI动画', title: '', link: '', drama_name: '', aliases: '',
    original_novel: '', username: '', douyin_id: '', following: '', followers: '',
    works_count: '', bio: '', homepage_link: '', likes: '', favorites: '', play_count: '',
    comment_count: '', share_count: '',
    on_hongguo: 0, learn_from: '', novel_clue: '', tags: '', novel_tags: '', note: '', screenshots: [],
  }
}

// ---------- 列表 ----------
let loadTimer = null
function debouncedLoad() {
  clearTimeout(loadTimer)
  loadTimer = setTimeout(loadList, 250)
}

async function loadList() {
  const q = new URLSearchParams()
  if (filters.platform !== '全部') q.set('platform', filters.platform)
  if (filters.category !== '全部') q.set('category', filters.category)
  if (filters.keyword) q.set('keyword', filters.keyword)
  if (filters.on_hongguo !== '') q.set('on_hongguo', filters.on_hongguo)
  try {
    const rows = await api(`/viral-collection/list?${q.toString()}`, 'GET')
    list.value = rows.map(r => ({ ...r, screenshots: parseArr(r.screenshots) }))
  } catch (e) {
    showToast(e.message || '加载失败')
  }
}

async function loadMeta() {
  try {
    const m = await api('/viral-collection/meta', 'GET')
    meta.platforms = m.platforms || []
    meta.categories = m.categories || []
  } catch (e) { /* 忽略 */ }
}

const DEFAULT_NOVEL_SITES = [
  { name: '番茄小说', url: 'https://fanqienovel.com/search?query={q}' },
  { name: '起点中文网', url: 'https://www.qidian.com/search?kw={q}' },
  { name: '红果小说', url: 'https://www.hongguo.com/search?q={q}' },
]
async function loadSites() {
  try {
    sites.value = await api('/viral-collection/search-sites', 'GET')
  } catch (e) { sites.value = [] }
  // 用户没配置搜索站点时，用内置默认（字节系爆款改编多来自番茄/红果），保证「搜原著」始终可用
  if (!sites.value || !sites.value.length) sites.value = DEFAULT_NOVEL_SITES
}

function setPlatform(p) { filters.platform = p; loadList() }
function setCategory(c) { filters.category = c; loadList() }
function setHongguo(v) { filters.on_hongguo = v; loadList() }

// ---------- 内嵌浏览器（插入式展开，点「去收集」打开） ----------
const UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'
const QUICK_SITES = [
  { name: '抖音', url: 'https://www.douyin.com/' },
  { name: '红果', url: 'https://www.hongguoduanju.com/' },
  { name: '快手', url: 'https://www.kuaishou.com/' },
  { name: '视频号', url: 'https://channels.weixin.qq.com/' },
  { name: 'B站', url: 'https://www.bilibili.com/' },
]
const HTTP_RE = /^https?:\/\//i

const browserOpen = ref(false)         // 默认收起（红色框 + 列表为主），点「去收集」打开
const urlInput = ref('')
const wvSrc = ref('https://www.douyin.com/')   // 第一次打开浏览器时的初始 URL
const wv = ref(null)
const wvWrap = ref(null)
const currentUrl = ref('')

function normalizeUrl(u) {
  const s = String(u || '').trim()
  if (!s) return ''
  if (/^https?:\/\//i.test(s)) return s
  return 'https://' + s
}
function navTo(u) {
  const url = normalizeUrl(u)
  if (!url) return
  urlInput.value = url
  currentUrl.value = url
  if (wv.value && typeof wv.value.loadURL === 'function') {
    try { wv.value.loadURL(url); return } catch (e) { /* 落到重建 */ }
  }
  wvSrc.value = url
}
function goUrl() { navTo(urlInput.value) }
function goSite(url) { navTo(url) }
function toggleBrowser() {
  // 切换「列表模式 / 收集模式」。关闭时不清 wvSrc，保留登录态与滚动位置
  browserOpen.value = !browserOpen.value
}

function wvGoBack() { try { wv.value?.goBack() } catch (e) { /* ignore */ } }
function wvGoForward() { try { wv.value?.goForward() } catch (e) { /* ignore */ } }
function wvReload() { try { wv.value?.reload() } catch (e) { /* ignore */ } }

// 主进程把 window.open 的 http(s) URL 发回，让本页 webview 内打开（替代新窗口）
function onOpenInSameWebview(_event, url) {
  if (!url) return
  navTo(url)
}

function onWvReady() {
  try { currentUrl.value = wv.value?.getURL?.() || currentUrl.value } catch (_) {}
}
function onWvNavigate(e) {
  const url = e?.url || ''
  if (url) currentUrl.value = url
  if (!HTTP_RE.test(url)) {
    try { e.preventDefault?.() } catch (_) {}
    console.log('[viral] blocked non-http navigation:', url)
  }
}
function onWvNavigateInPage(e) {
  // 抖音/快手等 SPA 用 history.pushState 打开视频/作者 Modal，URL 变化不会触发 will-navigate
  const url = e?.url || ''
  if (url && HTTP_RE.test(url)) currentUrl.value = url
}
function onWvNewWindow(e) {
  const url = e?.url || ''
  if (!HTTP_RE.test(url)) {
    try { e.preventDefault?.() } catch (_) {}
    console.log('[viral] blocked non-http new-window:', url)
  }
}

// 截取浏览器区域（webview 那一块），直接进左侧暂存区
async function captureView() {
  if (!el()?.capturePage) { showToast('截图需要在桌面版里使用'); return }
  const box = wvWrap.value?.getBoundingClientRect()
  capturing.value = true
  try {
    const rect = box ? { x: box.left, y: box.top, width: box.width, height: box.height } : null
    const dataUrl = await el().capturePage(rect)
    if (!dataUrl) { showToast('截取失败'); return }
    tray.value.push({ dataUrl })
    showToast(`已截取浏览器，暂存 ${tray.value.length} 张`)
  } catch (e) {
    console.error('[viral] captureView failed', e)
    showToast('截取浏览器失败')
  } finally {
    capturing.value = false
  }
}

// 兼容旧的独立浏览器窗口截图回传（IPC），保留无副作用
function onTrayAdd(_e, dataUrl) {
  if (!dataUrl) return
  tray.value.push({ dataUrl })
  showToast(`已收到截图，暂存 ${tray.value.length} 张`)
}

async function captureScreen() {
  if (!el()?.captureScreen) { showToast('截图需要在桌面版里使用'); return }
  capturing.value = true
  try {
    const dataUrl = await el().captureScreen()
    if (!dataUrl) { showToast('截屏失败'); return }
    tray.value.push({ dataUrl })
    showToast(`已截整屏，暂存 ${tray.value.length} 张`)
  } finally {
    capturing.value = false
  }
}

// 框选截图：先截整屏，弹出遮罩让用户拖选区域，松开后裁剪该区域入暂存区。
// 说明：截图基于主显示器整屏，坐标按 window.devicePixelRatio 映射；
// 窗口最大化时框选最准，未最大化时可能略有偏移（v1 已知限制）。
const showRegion = ref(false)
const regionBg = ref('')
const regionRect = reactive({ x: 0, y: 0, w: 0, h: 0 })
let regionStartPt = null
const regionBoxStyle = computed(() => ({
  left: regionRect.x + 'px',
  top: regionRect.y + 'px',
  width: regionRect.w + 'px',
  height: regionRect.h + 'px',
}))

async function captureRegion() {
  if (!el()?.captureScreen) { showToast('截图需要在桌面版里使用'); return }
  capturing.value = true
  try {
    const full = await el().captureScreen()
    if (!full) { showToast('截屏失败'); return }
    regionBg.value = full
    regionRect.x = regionRect.y = regionRect.w = regionRect.h = 0
    regionStartPt = null
    showRegion.value = true
  } finally {
    capturing.value = false
  }
}
function regionStart(e) {
  regionStartPt = { x: e.clientX, y: e.clientY }
  regionRect.x = e.clientX
  regionRect.y = e.clientY
  regionRect.w = 0
  regionRect.h = 0
}
function regionMove(e) {
  if (!regionStartPt) return
  regionRect.x = Math.min(regionStartPt.x, e.clientX)
  regionRect.y = Math.min(regionStartPt.y, e.clientY)
  regionRect.w = Math.abs(e.clientX - regionStartPt.x)
  regionRect.h = Math.abs(e.clientY - regionStartPt.y)
}
function regionEnd() {
  if (!regionStartPt) return
  regionStartPt = null
  const scale = window.devicePixelRatio || 1
  const sx = Math.round(regionRect.x * scale)
  const sy = Math.round(regionRect.y * scale)
  const sw = Math.round(regionRect.w * scale)
  const sh = Math.round(regionRect.h * scale)
  const bg = regionBg.value
  const finish = () => { showRegion.value = false; regionBg.value = '' }
  if (sw < 4 || sh < 4) { finish(); return } // 拖得太小，视为取消
  cropImage(bg, sx, sy, sw, sh).then((cropped) => {
    if (cropped) {
      tray.value.push({ dataUrl: cropped })
      showToast(`已框选截图，暂存 ${tray.value.length} 张`)
    }
    finish()
  }).catch(() => finish())
}
function cropImage(dataUrl, sx, sy, sw, sh) {
  return new Promise((resolve) => {
    const img = new Image()
    img.onload = () => {
      try {
        const canvas = document.createElement('canvas')
        canvas.width = sw
        canvas.height = sh
        const ctx = canvas.getContext('2d')
        ctx.drawImage(img, sx, sy, sw, sh, 0, 0, sw, sh)
        resolve(canvas.toDataURL('image/png'))
      } catch (e) {
        resolve('')
      }
    }
    img.onerror = () => resolve('')
    img.src = dataUrl
  })
}
function cancelRegion() {
  if (!showRegion.value) return
  showRegion.value = false
  regionBg.value = ''
  regionStartPt = null
}
function onRegionKey(e) {
  if (e.key === 'Escape' && showRegion.value) cancelRegion()
}

// 剪贴板粘贴图片
function onPaste(e) {
  const items = Array.from(e.clipboardData?.items || [])
  const imgs = items.filter(i => i.type && i.type.startsWith('image/'))
  if (!imgs.length) return
  e.preventDefault()
  for (const it of imgs) {
    const f = it.getAsFile()
    if (!f) continue
    if (showEditor.value) {
      const wrapped = { file: f, preview: URL.createObjectURL(f) }
      if (editing.id) pendingShots.value.push(wrapped)
      else aiFiles.value.push(wrapped)
    } else {
      const reader = new FileReader()
      reader.onload = () => tray.value.push({ dataUrl: reader.result })
      reader.readAsDataURL(f)
    }
  }
  showToast('已粘贴截图')
}

// ---------- AI 识别 ----------
function dataUrlToFile(dataUrl, name) {
  const [head, b64] = dataUrl.split(',')
  const mime = (head.match(/data:(.*?);/) || [])[1] || 'image/png'
  const bin = atob(b64)
  const arr = new Uint8Array(bin.length)
  for (let i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i)
  return new File([arr], name, { type: mime })
}

async function aiParseTray() {
  if (!tray.value.length) return
  const files = tray.value.map((t, i) => dataUrlToFile(t.dataUrl, `shot_${i + 1}.png`))
  const data = await doParse(files)
  if (!data) return
  openCreate(false)
  applyParsed(data)
}

async function aiParseFiles() {
  if (!aiFiles.value.length) return
  const data = await doParse(aiFiles.value.map(f => f.file))
  if (data) applyParsed(data)
}

async function doParse(files) {
  parsing.value = true
  parseError.value = ''
  try {
    const fd = new FormData()
    files.forEach(f => fd.append('files', f))
    if (aiRuleId.value) fd.append('rule_id', String(aiRuleId.value))
    const data = await apiUpload('/viral-collection/parse', fd)
    showToast('识别完成，已填入表单')
    return data
  } catch (e) {
    const msg = e.message || 'AI 识别失败'
    parseError.value = msg
    showToast(msg)
    return null
  } finally {
    parsing.value = false
  }
}

function applyParsed(d) {
  // 补缺式合并：只填当前为空的字段，不覆盖已填内容（识别补充语义）
  const put = (k, v) => {
    if (v === undefined || v === null || String(v).trim() === '') return
    if (String(editing[k] || '').trim() !== '') return
    editing[k] = String(v).trim()
  }
  put('platform', d.platform)
  put('category', d.category)
  put('title', d.title)
  put('link', d.link)
  put('drama_name', d.dramaName)
  put('username', d.username)
  put('douyin_id', d.douyinId)
  put('following', d.following)
  put('followers', d.followers)
  put('works_count', d.worksCount)
  put('bio', d.bio)
  put('homepage_link', d.homepageLink)
  put('likes', d.likes)
  put('favorites', d.favorites)
  put('play_count', d.playCount)
  put('comment_count', d.commentCount)
  put('share_count', d.shareCount)
  put('learn_from', d.learnFrom)
  put('novel_clue', d.novelClue)
  if (Array.isArray(d.tags) && d.tags.length) {
    if (String(editing.tags || '').trim() === '') editing.tags = d.tags.join(', ')
  } else put('tags', d.tags)
  if (Array.isArray(d.novelTags) && d.novelTags.length) {
    if (String(editing.novel_tags || '').trim() === '') editing.novel_tags = d.novelTags.join(', ')
  } else put('novel_tags', d.novelTags)
  if (d.onHongguo === true && !editing.on_hongguo) editing.on_hongguo = 1
  const kws = Array.isArray(d.novelKeywords) ? d.novelKeywords.filter(Boolean) : []
  aiKeywords.value = kws
  if (kws.length && !editing.original_novel) {
    const extra = '疑似原著/关键词：' + kws.join('、')
    editing.novel_clue = editing.novel_clue ? `${editing.novel_clue}\n${extra}` : extra
  }
}

function onAiFilesPicked(e) {
  const files = Array.from(e.target.files || [])
  aiFiles.value = files.map(f => ({ file: f, preview: URL.createObjectURL(f) }))
  e.target.value = ''
}

// ---------- 增删改 ----------
function openCreate(resetKeywords = true) {
  Object.assign(editing, blankForm())
  aiFiles.value = []
  pendingShots.value = []
  showVideoTags.value = false
  showNovelTags.value = false
  if (resetKeywords) aiKeywords.value = []
  showEditor.value = true
}

function openEdit(item) {
  Object.assign(editing, blankForm(), { ...item, screenshots: parseArr(item.screenshots) })
  aiFiles.value = []
  pendingShots.value = []
  aiKeywords.value = []
  showVideoTags.value = false
  showNovelTags.value = false
  showEditor.value = true
}
function closeEditor() { showEditor.value = false }

// 从内嵌浏览器取当前 URL 填入字段（弹窗不关也能拿到链接）
async function fetchBrowserLink(field) {
  let url = ''
  try { url = wv.value?.getURL?.() || '' } catch (_) {}

  // 兜底：如果 webview 还停留在抖音/快手首页（SPA 弹 Modal 时 getURL 可能仍是外层页），
  // 直接读页面 JS 的 location.href，通常能拿到当前 Modal 的真实 URL。
  const isHomeLike = (u) => {
    if (!u) return true
    return /^(https?:\/\/)?(www\.)?douyin\.com\/?(\?.*)?$/i.test(u) ||
           /^(https?:\/\/)?(www\.)?kuaishou\.com\/?(\?.*)?$/i.test(u)
  }
  if (isHomeLike(url) && wv.value?.executeJavaScript) {
    try {
      const pageHref = await wv.value.executeJavaScript('window.location.href')
      if (pageHref && !isHomeLike(pageHref)) url = pageHref
    } catch (_) {}
  }

  if (!url) { showToast('浏览器未打开或暂无地址，先点「去收集」打开浏览器'); return }
  editing[field] = url
  showToast('已从浏览器取链接')
}

// 用系统默认浏览器打开当前 webview 页面或已填链接（抖音弹窗抓不到真实链接时，去外部浏览器复制最稳）
function openLinkInBrowser(field) {
  let url = ''
  try { url = wv.value?.getURL?.() || '' } catch (_) {}
  if (!url) url = String(currentUrl.value || '').trim()
  if (!url && String(editing[field] || '').trim()) url = String(editing[field]).trim()
  if (!url) { showToast('浏览器未打开或暂无地址，先点「去收集」打开浏览器'); return }
  openExternal(url)
}

// 保存前自动给标题补作者前缀（username - title），保证同名作品可区分
function ensureTitlePrefix() {
  const name = String(editing.username || '').trim()
  const title = String(editing.title || '').trim()
  if (!name || !title) return
  if (title.startsWith(name + ' - ') || title.startsWith(name + ' -') || title === name) return
  editing.title = `${name} - ${title}`
}

async function save() {
  ensureTitlePrefix()
  if (!String(editing.title || '').trim()) {
    showToast('标题不能为空')
    titleInput.value?.focus()
    return
  }
  saving.value = true
  try {
    const payload = {
      platform: editing.platform || '', category: editing.category || '', title: editing.title,
      link: editing.link || '', drama_name: editing.drama_name || '', aliases: editing.aliases || '',
      original_novel: editing.original_novel || '', username: editing.username || '',
      douyin_id: editing.douyin_id || '', following: editing.following || '', followers: editing.followers || '',
      works_count: editing.works_count || '', bio: editing.bio || '', homepage_link: editing.homepage_link || '',
      likes: editing.likes || '', favorites: editing.favorites || '',
      play_count: editing.play_count || '', comment_count: editing.comment_count || '',
      share_count: editing.share_count || '', on_hongguo: editing.on_hongguo ? 1 : 0,
      learn_from: editing.learn_from || '', novel_clue: editing.novel_clue || '',
      tags: editing.tags || '', novel_tags: editing.novel_tags || '', note: editing.note || '',
    }
    let saved
    if (editing.id) {
      saved = await api(`/viral-collection/${editing.id}`, 'PUT', payload)
    } else {
      saved = await api('/viral-collection/', 'POST', payload)
      // 新建时把暂存区截图自动挂上去
      if (tray.value.length) {
        await api(`/viral-collection/${saved.id}/screenshots-base64`, 'POST', {
          images: tray.value.map(t => t.dataUrl),
          filename_prefix: 'shot',
        })
        tray.value = []
      }
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
  if (!(await confirm(`确定删除「${item.title}」？截图也会一并删除，不可撤销。`, { title: '删除确认' }))) return
  try {
    await api(`/viral-collection/${item.id}`, 'DELETE')
    await loadMeta()
    await loadList()
    showToast('已删除')
  } catch (e) {
    showToast(e.message || '删除失败')
  }
}

function openDetail(item) {
  detail.value = item
  showDetail.value = true
}

// ---------- 截图管理 ----------
function onShotsPicked(e) {
  const files = Array.from(e.target.files || [])
  pendingShots.value = files.map(f => ({ file: f, preview: URL.createObjectURL(f) }))
  e.target.value = ''
}
async function uploadShots() {
  if (!editing.id || !pendingShots.value.length) return
  const fd = new FormData()
  pendingShots.value.forEach(p => fd.append('files', p.file))
  try {
    const updated = await apiUpload(`/viral-collection/${editing.id}/screenshots`, fd)
    editing.screenshots = parseArr(updated.screenshots)
    pendingShots.value = []
    await loadList()
    showToast('截图已上传')
  } catch (e) {
    showToast(e.message || '上传失败')
  }
}
async function removeScreenshot(rel) {
  const fn = rel.split('/').pop()
  try {
    const updated = await api(`/viral-collection/${editing.id}/screenshots/${encodeURIComponent(fn)}`, 'DELETE')
    editing.screenshots = parseArr(updated.screenshots)
    await loadList()
    showToast('已删除截图')
  } catch (e) {
    showToast(e.message || '删除失败')
  }
}

// ---------- 去平台搜 ----------
function searchKeyOf(item) {
  if (!item) return ''
  return (item.original_novel || item.drama_name || item.title || '').trim()
}
function copySite(site, q) {
  if (!q) return
  const url = (site.url || '').includes('{q}')
    ? site.url.replace('{q}', encodeURIComponent(q))
    : site.url + encodeURIComponent(q)
  openExternal(url)
}
function searchKeyword(k) {
  if (!sites.value.length) { showToast('先配置搜索站点'); return }
  copySite(sites.value[0], k)
}
function openSearchFor(item) {
  const q = searchKeyOf(item)
  if (!q) { showToast('先填标题或剧名'); return }
  if (!sites.value.length) { showToast('先配置搜索站点'); return }
  detail.value = item
  showDetail.value = true
}
// 新建/编辑弹窗内：直接用系统默认浏览器搜当前原著名/剧名（跳过详情弹窗）
function searchNovelNow() {
  const q = searchKeyOf(editing)
  if (!q) { showToast('请先填原著名 / 剧名，或让 AI 识别出书名'); return }
  copySite(sites.value[0], q)
}
function openExternal(url) {
  if (!url) return
  // 桌面版：直接调用系统默认浏览器（外部 Chrome/Edge）打开，最稳、不怕 SPA 跳转丢链接
  if (window.electronAPI && window.electronAPI.openExternal) {
    window.electronAPI.openExternal(url)
    showToast('已用系统默认浏览器打开搜索')
    return
  }
  // 非桌面环境兜底：复制到剪贴板
  copyToClipboard(url).then((ok) => {
    showToast(ok ? '链接已复制，请在浏览器中打开' : '打开失败，链接：' + url)
  })
}

// 复制文本到剪贴板：优先 navigator.clipboard，失败回退 execCommand，避免自动拉起外部进程
async function copyToClipboard(text) {
  if (!text) return false
  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(text)
      return true
    }
  } catch (e) { /* 落到回退方案 */ }
  try {
    const ta = document.createElement('textarea')
    ta.value = text
    ta.style.position = 'fixed'
    ta.style.top = '-1000px'
    ta.style.opacity = '0'
    document.body.appendChild(ta)
    ta.focus(); ta.select()
    const ok = document.execCommand('copy')
    document.body.removeChild(ta)
    return ok
  } catch (e) { return false }
}
function copyText(text) {
  copyToClipboard(text).then((ok) => showToast(ok ? '已复制' : '复制失败：' + text))
}

function openSites() {
  sitesDraft.value = sites.value.map(s => ({ ...s }))
  if (!sitesDraft.value.length) sitesDraft.value.push({ name: '', url: '' })
  showSites.value = true
}
async function saveSites() {
  try {
    sites.value = await api('/viral-collection/search-sites', 'PUT', { sites: sitesDraft.value })
    showSites.value = false
    showToast('站点已保存')
  } catch (e) {
    showToast(e.message || '保存失败')
  }
}

// ---------- 工具 ----------
function parseArr(v) {
  if (Array.isArray(v)) return v
  if (!v) return []
  try { const a = JSON.parse(v); return Array.isArray(a) ? a : [] } catch { return [] }
}
function imgUrl(rel) { return '/api/viral-collection/asset/' + rel }
function splitTags(s) { return (s || '').split(/[,，、]/).map(x => x.trim()).filter(Boolean) }
function openLightbox(rel, all) {
  const arr = Array.isArray(all) ? all : [rel]
  lightboxItems.value = arr.map(x => ({ url: imgUrl(x) }))
  lightboxIndex.value = Math.max(0, arr.indexOf(rel))
  lightboxVisible.value = true
}
function openTrayLightbox(i) {
  lightboxItems.value = tray.value.map(t => ({ url: t.dataUrl }))
  lightboxIndex.value = i
  lightboxVisible.value = true
}
function showToast(msg) {
  toast.value = msg
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => { toast.value = '' }, 2200)
}

onMounted(async () => {
  restoreTray()
  window.addEventListener('paste', onPaste)
  window.addEventListener('keydown', onRegionKey)
  if (window.electronAPI && window.electronAPI.onTrayAdd) {
    window.electronAPI.onTrayAdd(onTrayAdd)
  }
  if (window.electronAPI && window.electronAPI.onOpenInSameWebview) {
    window.electronAPI.onOpenInSameWebview(onOpenInSameWebview)
  }
  await Promise.all([loadMeta(), loadSites(), loadAiRules()])
  await loadList()
})
onBeforeUnmount(() => {
  window.removeEventListener('paste', onPaste)
  window.removeEventListener('keydown', onRegionKey)
  if (window.electronAPI && window.electronAPI.offTrayAdd) {
    window.electronAPI.offTrayAdd(onTrayAdd)
  }
  if (window.electronAPI && window.electronAPI.offOpenInSameWebview) {
    window.electronAPI.offOpenInSameWebview(onOpenInSameWebview)
  }
  clearTimeout(loadTimer)
  clearTimeout(toastTimer)
})
</script>

<style scoped>
.vc-page {
  width: 100%;
  height: calc(100vh - 44px);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  font-family: system-ui, -apple-system, "Segoe UI", Roboto, "PingFang SC", "Microsoft YaHei", sans-serif;
  color: var(--sx-text-strong);
}
/* 顶部标题栏固定，不随列表滚动 */
.vc-head { display: flex; align-items: center; justify-content: space-between; gap: 16px; flex-wrap: wrap; margin-bottom: 14px; flex-shrink: 0; }
.vc-title { display: flex; align-items: center; gap: 12px; color: var(--sx-accent-pink); }
.vc-title h1 { font-size: 22px; margin: 0; color: var(--sx-text-strong); }
.vc-sub { margin: 2px 0 0; font-size: 12.5px; color: var(--sx-text-muted); }
.vc-actions { display: flex; gap: 10px; flex-wrap: wrap; }

.btn { display: inline-flex; align-items: center; gap: 6px; padding: 9px 16px; border-radius: 10px; font-size: 14px; font-weight: 600; cursor: pointer; border: 1px solid transparent; transition: .15s; }
.btn.primary { background: var(--sx-btn-pink-bg); color: #fff; box-shadow: var(--sx-btn-pink-shadow); }
.btn.primary:hover { filter: brightness(1.05); }
.btn.primary:disabled { opacity: .55; cursor: default; filter: none; }
.btn.ghost { background: var(--sx-bg-surface); border-color: var(--sx-border); color: var(--sx-text); }
.btn.ghost:hover { background: var(--sx-bg-surface-2); }
.btn.ghost:disabled { opacity: .5; cursor: default; }
.btn.sm { padding: 7px 12px; font-size: 13px; }

/* 主体：列表模式（红色框 + 卡片列表） / 收集模式（内嵌浏览器占满）。互斥显示 */
.vc-body { flex: 1; min-height: 0; display: flex; flex-direction: column; gap: 0; overflow: hidden; }
.vc-toolbar { flex: 0 0 auto; display: flex; flex-direction: column; gap: 10px; padding-bottom: 12px; }
.vc-browser { flex: 1 1 auto; min-height: 0; display: flex; flex-direction: column; border: 1px solid var(--sx-border); border-radius: 12px; overflow: hidden; background: var(--sx-bg-surface-2); }
.vc-list { flex: 1 1 auto; min-height: 0; overflow-y: auto; }

/* 浏览器面板内部 */
.bw-bar {
  display: flex; flex-direction: column; gap: 8px;
  padding: 10px 12px;
  background: var(--sx-bg-surface); border-bottom: 1px solid var(--sx-border);
}
.bw-bar-row { display: flex; align-items: center; gap: 8px; }
.bw-bar-row.bw-quick { flex-wrap: wrap; }
.bw-ico {
  display: inline-flex; align-items: center; justify-content: center;
  width: 32px; height: 32px; border: 1px solid var(--sx-border); background: var(--sx-bg-surface);
  border-radius: 9px; cursor: pointer; color: var(--sx-text); flex-shrink: 0;
  transition: background .15s, color .15s, border-color .15s;
}
.bw-ico svg { display: block; }
.bw-ico:hover { background: var(--sx-accent-pink-soft-bg); color: var(--sx-accent-pink); border-color: var(--sx-accent-pink-soft-border); }
.bw-url {
  flex: 1; min-width: 120px; height: 32px; padding: 0 12px; border: 1px solid var(--sx-border);
  border-radius: 9px; font-size: 13.5px; outline: none; background: var(--sx-bg-surface-2); color: var(--sx-text-strong);
  transition: border-color .15s, box-shadow .15s;
}
.bw-url:focus { border-color: var(--sx-accent-pink); box-shadow: 0 0 0 3px var(--sx-accent-pink-soft); background: var(--sx-bg-surface); }
.bw-go {
  display: inline-flex; align-items: center; justify-content: center;
  height: 32px; padding: 0 16px; border: 0; border-radius: 9px;
  background: var(--sx-accent-pink); color: #fff; cursor: pointer; font-size: 13px; font-weight: 500;
  flex-shrink: 0; transition: filter .15s, transform .1s;
}
.bw-go:hover { filter: brightness(1.06); }
.bw-go:active { transform: translateY(1px); }
.bw-quick { gap: 6px; }
.bw-chip {
  display: inline-flex; align-items: center; justify-content: center;
  height: 28px; padding: 0 12px; border: 1px solid var(--sx-border); background: var(--sx-bg-surface-2);
  border-radius: 999px; font-size: 12.5px; cursor: pointer; color: var(--sx-text);
  white-space: nowrap; transition: color .15s, border-color .15s, background .15s;
}
.bw-chip:hover { color: var(--sx-accent-pink); border-color: var(--sx-accent-pink-soft-border); background: var(--sx-accent-pink-soft-bg); }

.bw-view { position: relative; flex: 1; min-height: 0; background: #fff; }
.bw-webview { width: 100%; height: 100%; display: inline-flex; border: 0; }
.bw-placeholder {
  position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center;
  color: var(--sx-text-muted); font-size: 13px; gap: 6px; text-align: center; padding: 0 20px;
}
.bw-placeholder .tip { opacity: .7; font-size: 12px; }
.bw-foot {
  display: flex; align-items: center; gap: 8px; padding: 8px 10px; flex-wrap: wrap;
  background: var(--sx-bg-surface); border-top: 1px solid var(--sx-border);
}
.bw-foot { justify-content: space-between; }
.bw-shot-tip {
  display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
  font-size: 12px; color: var(--sx-text-muted); line-height: 1.5;
}
.bw-shot-tip b { color: var(--sx-accent-pink); font-weight: 600; }
.bw-shot-tip span { background: var(--sx-bg-tertiary); border-radius: 999px; padding: 2px 10px; }
.bw-shot-ops { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.bw-hint { font-size: 12px; color: var(--sx-text-muted); margin-right: auto; }

/* 框选截图遮罩：基于整屏截图，用户拖选区域，框外变暗（Snipaste 风格） */
.region-mask { position: fixed; inset: 0; z-index: 9999; cursor: crosshair; user-select: none; }
.region-bg { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: fill; pointer-events: none; -webkit-user-drag: none; }
.region-box { position: absolute; border: 2px dashed var(--sx-accent-pink); background: var(--sx-accent-pink-soft); box-shadow: 0 0 0 100vmax rgba(20, 22, 40, .42); pointer-events: none; }
.region-tip { position: fixed; top: 18px; left: 50%; transform: translateX(-50%); background: rgba(0, 0, 0, .72); color: #fff; font-size: 13px; padding: 7px 16px; border-radius: 9px; pointer-events: none; letter-spacing: .3px; }
.app-hint { color: var(--sx-tag-warn-text); background: var(--sx-tag-warn-bg); border: 1px solid var(--sx-tag-warn-border); border-radius: 8px; padding: 8px 10px; }

.bw-tray { flex-shrink: 0; margin-top: 10px; border-top: 1px solid var(--sx-border); padding-top: 10px; max-height: 260px; overflow-y: auto; }
.tray-head { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin-bottom: 10px; }
.tray-head b { font-size: 13px; color: var(--sx-text-strong); }
.tray-clear { margin-left: auto; font-size: 12.5px; color: var(--sx-text-muted); background: transparent; border: 0; cursor: pointer; padding: 4px 8px; border-radius: 6px; transition: .15s; }
.tray-clear:hover { color: var(--sx-btn-danger-text); background: var(--sx-btn-danger-bg); }
.parse-error { margin-top: 10px; padding: 8px 10px; border-radius: 8px; background: var(--sx-accent-pink-soft-bg); color: var(--sx-accent-pink-muted-text); border: 1px solid var(--sx-accent-pink-soft-border); font-size: 12.5px; word-break: break-all; }
.tray-imgs { display: flex; gap: 10px; flex-wrap: wrap; }
.tray-cell {
  position: relative; width: 152px; height: 100px;
  border-radius: 10px; overflow: hidden;
  border: 1px solid var(--sx-border); background: var(--sx-bg-surface-2);
  box-shadow: 0 1px 3px rgba(20,22,40,.06);
  transition: transform .15s, box-shadow .15s, border-color .15s;
}
.tray-cell:hover { transform: translateY(-1px); box-shadow: 0 4px 10px rgba(20,22,40,.12); border-color: var(--sx-accent-pink-soft-border); }
.tray-cell img { width: 100%; height: 100%; object-fit: cover; cursor: zoom-in; display: block; }
.tray-del {
  position: absolute; top: 6px; right: 6px;
  width: 22px; height: 22px; padding: 0; border: 0; border-radius: 50%;
  background: rgba(20,22,40,.62); color: #fff;
  display: flex; align-items: center; justify-content: center;
  font-size: 14px; line-height: 1; cursor: pointer;
  opacity: 0; transform: scale(.85); transition: opacity .15s, transform .15s, background .15s;
  backdrop-filter: blur(2px);
}
.tray-cell:hover .tray-del { opacity: 1; transform: scale(1); }
.tray-del:hover { background: #e0245e; }

/* AI 识别区（参考提示词库「AI 整理」） */
.ai-parse-card {
  flex-shrink: 0;
  margin-top: 10px;
  border-top: 1px solid var(--sx-border);
  padding-top: 10px;
}
.section-divider {
  display: flex; align-items: center; gap: 10px;
  font-size: 13px; color: var(--sx-text-strong); font-weight: 600;
  margin-bottom: 10px;
}
.section-divider::before, .section-divider::after {
  content: ''; flex: 1; height: 1px; background: var(--sx-border);
}
.ai-parse-config {
  background: var(--sx-bg-surface); border: 1px solid var(--sx-border);
  border-radius: 12px; padding: 12px 14px;
}
.ai-rule-line { display: flex; align-items: center; gap: 12px; padding: 4px 0; flex-wrap: wrap; }
.ai-rule-line .filter-label { min-width: 72px; margin: 0; font-size: 12px; color: var(--sx-text-muted); font-weight: 600; }
.ai-rule-line .mini-select { flex: 1; min-width: 180px; max-width: 420px; }
.ai-rule-line.ai-rule-foot {
  padding-top: 10px; border-top: 1px dashed var(--sx-border); margin-top: 4px;
  justify-content: space-between;
}
.ai-tags { display: flex; gap: 8px; flex-wrap: wrap; }
.ai-tag {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 4px 12px; border-radius: 999px;
  font-size: 12.5px; font-weight: 600; line-height: 1.6;
}
.ai-tag em {
  font-style: normal; font-size: 11px; font-weight: 700; letter-spacing: 0.5px;
  padding: 1px 6px; border-radius: 4px; background: rgba(255,255,255,0.7); color: inherit; opacity: 0.7;
}
.ai-tag.role { background: var(--sx-tag-purple-bg); color: var(--sx-tag-purple-text); }
.ai-tag.func { background: var(--sx-tag-pink-bg); color: var(--sx-tag-pink-text); }
.remembered-text { font-size: 13px; color: var(--sx-text-strong); }
.remembered-text b { color: var(--sx-accent-pink); font-weight: 600; }
.ai-parse-hint { font-size: 12.5px; color: var(--sx-text-muted); padding: 10px 14px; background: var(--sx-bg-surface-2); border-radius: 10px; }
.ai-parse-action {
  display: flex; align-items: center; gap: 12px; flex-wrap: wrap;
  margin-top: 12px;
}
.ai-parse-tip { font-size: 12px; color: var(--sx-text-muted); line-height: 1.5; }
.mini-spin {
  display: inline-block; width: 12px; height: 12px;
  border: 2px solid rgba(255,255,255,.5); border-top-color: #fff;
  border-radius: 50%; animation: spin .7s linear infinite;
  vertical-align: -1px; margin-right: 5px;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* 统计 */
.vc-stats { display: flex; gap: 10px; margin-bottom: 16px; flex-wrap: wrap; }
.stat { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 3px; padding: 11px 20px; border-radius: 12px; background: var(--sx-bg-surface); border: 1px solid var(--sx-border); cursor: pointer; transition: .15s; min-width: 92px; }
.stat:hover { border-color: var(--sx-accent-pink-soft-border); }
.stat.on { border-color: var(--sx-accent-pink); box-shadow: 0 0 0 2px var(--sx-accent-pink-soft); }
.stat-num { font-size: 21px; font-weight: 800; color: var(--sx-text-strong); line-height: 1; }
.stat-lbl { font-size: 12px; color: var(--sx-text-muted); }
.stat.on .stat-lbl { color: var(--sx-accent-pink); }
.stat.s-yes .stat-num { color: var(--sx-tag-red-text); }
.stat.s-todo .stat-num { color: var(--sx-text-muted); }
.stat.s-warn { cursor: default; }
.stat.s-warn .stat-num { color: var(--sx-tag-warn-text); }

/* 筛选 */
.vc-filters { background: var(--sx-bg-surface); border: 1px solid var(--sx-border); border-radius: 14px; padding: 16px; margin-bottom: 18px; box-shadow: var(--sx-shadow-card); }
.search-wrap { display: flex; align-items: center; gap: 8px; background: var(--sx-bg-surface-2); border: 1px solid var(--sx-border); border-radius: 10px; padding: 0 12px; color: var(--sx-text-muted); }
.search-wrap .search { flex: 1; border: 0; background: transparent; padding: 11px 0; font-size: 14px; color: var(--sx-text-strong); outline: none; }
.filter-row { display: flex; align-items: center; gap: 10px; margin-top: 12px; flex-wrap: wrap; }
.filter-label { font-size: 12.5px; color: var(--sx-text-muted); font-weight: 600; flex-shrink: 0; }
.chips { display: flex; gap: 8px; flex-wrap: wrap; }
.chip { padding: 6px 13px; border-radius: 999px; border: 1px solid var(--sx-border); background: var(--sx-bg-surface); color: var(--sx-text); font-size: 13px; cursor: pointer; transition: .15s; }
.chip:hover { border-color: var(--sx-accent-pink-soft-border); color: var(--sx-accent-pink); }
.chip.on { background: var(--sx-accent-pink); border-color: var(--sx-accent-pink); color: #fff; }
.chip.sm { padding: 5px 11px; font-size: 12.5px; }
.chip:disabled { opacity: .45; cursor: default; }
.mini-select { padding: 7px 10px; border-radius: 9px; border: 1px solid var(--sx-border); background: var(--sx-bg-surface); font-size: 13px; color: var(--sx-text); cursor: pointer; max-width: 230px; }
.count { margin-left: auto; font-size: 12.5px; color: var(--sx-text-muted); }

/* 卡片 */
.vc-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(290px, 1fr)); gap: 18px; }
.vc-card { background: var(--sx-bg-surface); border: 1px solid var(--sx-border); border-radius: 14px; padding: 16px; transition: .2s; display: flex; flex-direction: column; gap: 10px; box-shadow: var(--sx-shadow-card); }
.vc-card:hover { border-color: var(--sx-accent-pink-soft-border); box-shadow: var(--sx-card-pink-shadow); transform: translateY(-2px); }
.card-main { cursor: pointer; display: flex; flex-direction: column; gap: 8px; flex: 1; }
.card-cover { position: relative; width: 100%; height: 132px; border-radius: 10px; overflow: hidden; background: var(--sx-bg-surface-2); }
.card-cover img { width: 100%; height: 100%; object-fit: cover; }
.cover-count { position: absolute; right: 6px; bottom: 6px; background: rgba(20,22,40,.7); color: #fff; font-size: 11px; padding: 2px 7px; border-radius: 999px; }
.card-top { display: flex; align-items: flex-start; gap: 8px; }
.card-title { font-size: 15.5px; margin: 0; color: var(--sx-text-strong); font-weight: 700; line-height: 1.35; flex: 1; word-break: break-word; }
.card-badges { display: flex; gap: 6px; flex-wrap: wrap; }
.badge { font-size: 11px; padding: 3px 9px; border-radius: 999px; font-weight: 600; white-space: nowrap; }
.badge.plat { background: var(--sx-tag-purple-bg); color: var(--sx-tag-purple-text); }
.badge.cat { background: var(--sx-tag-pink-bg); color: var(--sx-tag-pink-text); }
.badge.user { background: var(--sx-tag-info-bg); color: var(--sx-tag-info-text); }
.badge.hg { background: var(--sx-tag-red-fill); color: #fff; }
.card-nums { display: flex; gap: 12px; font-size: 12.5px; color: var(--sx-text-muted); }
.card-novel { display: flex; gap: 6px; align-items: baseline; font-size: 12.5px; }
.card-novel span { color: var(--sx-text-muted); }
.card-novel b { color: var(--sx-text-strong); font-weight: 600; }
.card-novel.missing b { color: var(--sx-tag-warn-text); font-weight: 500; }
.card-tags { display: flex; gap: 5px; flex-wrap: wrap; }
.tag { font-size: 11px; color: var(--sx-text-muted); background: var(--sx-bg-surface-2); padding: 2px 7px; border-radius: 6px; }
.card-ops { display: flex; gap: 6px; margin-top: auto; padding-top: 10px; border-top: 1px solid var(--sx-border); justify-content: flex-end; }
.vc-op { padding: 6px 10px; border-radius: 6px; border: 1px solid var(--sx-border); background: var(--sx-bg-surface); color: var(--sx-text); font-size: 12.5px; cursor: pointer; transition: .15s; white-space: nowrap; }
.vc-op:hover { background: var(--sx-bg-surface-2); color: var(--sx-accent-pink); border-color: var(--sx-accent-pink-soft-border); }
.vc-op.danger:hover { background: var(--sx-btn-danger-bg); color: var(--sx-btn-danger-text); border-color: var(--sx-btn-danger-border); }

.empty { text-align: center; color: var(--sx-text-muted); padding: 60px 20px; }
.empty svg { color: var(--sx-text-faint); margin-bottom: 12px; }
.empty p { font-size: 14px; max-width: 460px; margin: 0 auto; line-height: 1.6; }

/* 弹窗 */
.modal-mask { position: fixed; inset: 0; background: var(--sx-overlay); display: flex; align-items: center; justify-content: center; z-index: 50; padding: 20px; }
.modal { background: var(--sx-bg-elevated); border-radius: 16px; width: 100%; max-width: 900px; max-height: 90vh; display: flex; flex-direction: column; box-shadow: var(--sx-shadow-pop); }
.modal.narrow { max-width: 620px; }
.modal-head { display: flex; align-items: center; justify-content: space-between; padding: 18px 22px; border-bottom: 1px solid var(--sx-border); }
.modal-head h2 { margin: 0; font-size: 17px; color: var(--sx-text-strong); }
.x { border: 0; background: transparent; font-size: 18px; color: var(--sx-text-muted); cursor: pointer; line-height: 1; }
.x:hover { color: var(--sx-btn-danger-text); }
.modal-body { padding: 20px 22px; overflow-y: auto; }
.modal-foot { display: flex; justify-content: flex-end; gap: 10px; padding: 14px 22px; border-top: 1px solid var(--sx-border); }

.ai-box { background: var(--sx-accent-pink-soft-bg); border: 1px solid var(--sx-accent-pink-soft-border); border-radius: 12px; padding: 12px 14px; margin-bottom: 16px; }
.ai-row { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.ai-row b { font-size: 13px; color: var(--sx-accent-pink-muted-text); margin-right: 4px; }
.ai-rule-name { font-size: 12px; color: var(--sx-accent-pink-muted-text); background: rgba(255,255,255,0.6); border-radius: 999px; padding: 2px 10px; }
.ai-thumbs { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 8px; }
.ai-thumbs img { width: 72px; height: 46px; object-fit: cover; border-radius: 6px; border: 1px solid var(--sx-accent-pink-soft-border); }
.ai-tip { font-size: 12px; color: var(--sx-text-muted); margin: 8px 0 0; }

/* 标签行头：标签名 + 提示 + 折叠开关 */
.fld-head { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.fld-head > span:first-child { font-size: 13px; font-weight: 600; color: var(--sx-text-strong); }
.fld-hint { font-size: 11px; color: var(--sx-text-muted); }
.tag-toggle { margin-left: auto; font-size: 12px; color: var(--sx-accent-pink); background: transparent; border: 1px dashed var(--sx-accent-pink-soft-border); border-radius: 999px; padding: 2px 10px; cursor: pointer; transition: .15s; }
.tag-toggle:hover { background: var(--sx-accent-pink-soft-bg); }

/* 选填数据区 */
.opt-block { border: 1px dashed var(--sx-border); border-radius: 12px; padding: 12px 14px; margin-bottom: 14px; background: var(--sx-bg-surface-2); }
.opt-title { font-size: 12px; font-weight: 600; color: var(--sx-text-muted); margin-bottom: 10px; letter-spacing: 0.5px; }

.fld { display: flex; flex-direction: column; gap: 6px; margin-bottom: 14px; }
.fld > span { font-size: 12.5px; color: var(--sx-text); font-weight: 600; }
.fld input, .fld select, .fld textarea { border: 1px solid var(--sx-border-strong); border-radius: 9px; padding: 10px 12px; font-size: 14px; color: var(--sx-text-strong); font-family: inherit; outline: none; transition: .15s; background: var(--sx-bg-surface); width: 100%; box-sizing: border-box; }
.fld input:hover, .fld textarea:hover { border-color: var(--sx-border-strong); }
.fld input:focus, .fld textarea:focus { border-color: var(--sx-accent-pink); box-shadow: 0 0 0 3px var(--sx-accent-pink-soft); }
.fld textarea { resize: vertical; line-height: 1.6; }
.fld-row { display: flex; gap: 14px; }
.fld-row .fld { flex: 1; min-width: 0; }
.fld-row .sm-fld { flex: 0 0 170px; }
.novel-line { display: flex; gap: 8px; align-items: center; }
.novel-line input { flex: 1; }

.hg-switch { display: inline-flex; background: var(--sx-bg-surface-2); border-radius: 10px; padding: 4px; gap: 4px; }
.sw { padding: 8px 20px; border-radius: 8px; border: 1px solid transparent; background: transparent; color: var(--sx-text); font-size: 13px; font-weight: 600; cursor: pointer; transition: .15s; }
.sw:not(.on) { opacity: .45; }
.sw.on { background: var(--sx-text-muted); color: #fff; }
.sw.on.sw-yes { background: var(--sx-tag-red-fill); box-shadow: var(--sx-tag-red-shadow); }

.kw-box { display: flex; gap: 6px; flex-wrap: wrap; align-items: center; background: var(--sx-tag-warn-bg); border: 1px solid var(--sx-tag-warn-border); border-radius: 10px; padding: 10px 12px; margin-bottom: 14px; }
.kw-label { font-size: 12.5px; color: var(--sx-tag-warn-text); font-weight: 600; }
.kw { border: 1px solid var(--sx-tag-warn-border); background: var(--sx-bg-surface); color: var(--sx-tag-warn-text); font-size: 12.5px; padding: 4px 10px; border-radius: 999px; cursor: pointer; }
.kw:hover { background: var(--sx-tag-warn-bg); }

.detail-badges { display: flex; gap: 7px; flex-wrap: wrap; align-items: center; margin-bottom: 12px; }
.detail-tags { display: flex; gap: 6px; flex-wrap: wrap; }
.detail-url { font-size: 13px; margin-bottom: 14px; word-break: break-all; }
.detail-url a { color: var(--sx-accent-pink); text-decoration: none; cursor: pointer; }
.detail-url a:hover { text-decoration: underline; }
.detail-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px 20px; margin-bottom: 14px; background: var(--sx-bg-surface); border: 1px solid var(--sx-border-strong); border-radius: 10px; padding: 14px 16px; }
.detail-grid .db-label { grid-column: 1 / -1; margin-bottom: 2px; padding-bottom: 8px; border-bottom: 1px solid var(--sx-border); font-size: 13px; color: var(--sx-text); display: flex; align-items: center; gap: 6px; }
.detail-grid .db-label::before { content: ''; width: 3px; height: 12px; background: var(--sx-accent-pink); border-radius: 2px; }
.dg-cell { display: flex; flex-direction: column; gap: 3px; font-size: 13.5px; padding: 5px 0; }
.home-link { color: var(--sx-accent-pink); cursor: pointer; }
.home-link:hover { text-decoration: underline; }

/* 标签云（分类/视频标签/小说标签） */
.tag-cloud { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; align-items: center; }
.tc-label { width: 100%; font-size: 12px; color: var(--sx-text-muted); margin-top: 4px; }
.tag-chip { border: 1px solid var(--sx-border); background: var(--sx-bg-surface); color: var(--sx-text); font-size: 12.5px; padding: 3px 10px; border-radius: 999px; cursor: pointer; transition: all .12s; }
.tag-chip:hover { border-color: var(--sx-accent-pink-soft-border); color: var(--sx-accent-pink); }
.tag-chip.on { background: var(--sx-accent-pink-soft-bg); border-color: var(--sx-accent-pink-soft-border); color: var(--sx-accent-pink-muted-text); font-weight: 600; }
.dg-cell span { color: var(--sx-text-muted); }
.dg-cell b { color: var(--sx-text-strong); font-weight: 600; }
.dg-cell b.miss { color: var(--sx-tag-warn-text); font-weight: 500; }
.detail-block { margin-bottom: 14px; }
.db-label { font-size: 12.5px; color: var(--sx-text); font-weight: 600; margin-bottom: 6px; }
.detail-content { background: var(--sx-bg-surface-2); border: 1px solid var(--sx-border); border-radius: 10px; padding: 14px; font-size: 13.5px; line-height: 1.7; color: var(--sx-text-strong); white-space: pre-wrap; word-break: break-word; max-height: 36vh; overflow-y: auto; margin: 0; }
.detail-text { font-size: 13.5px; color: var(--sx-text-strong); line-height: 1.6; }
.detail-imgs { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 14px; }
.detail-img { width: 220px; height: 124px; object-fit: cover; border-radius: 8px; cursor: zoom-in; border: 1px solid var(--sx-border); }
.site-btns { display: flex; gap: 8px; flex-wrap: wrap; }

.img-grid { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 8px; }
.img-cell { position: relative; width: 96px; height: 62px; border-radius: 8px; overflow: hidden; border: 1px solid var(--sx-border); }
.img-cell img { width: 100%; height: 100%; object-fit: cover; cursor: zoom-in; }
.img-tools { position: absolute; left: 0; right: 0; bottom: 0; height: 20px; display: flex; align-items: center; justify-content: center; background: rgba(20,22,40,.66); }
.img-tool { border: 0; background: transparent; color: #fff; cursor: pointer; padding: 0; font-size: 14px; line-height: 20px; }
.img-tool.del:hover { color: var(--sx-btn-danger-text); }
.img-upload { display: flex; gap: 8px; align-items: center; }
.img-pending { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 8px; }
.pending-thumb { width: 56px; height: 40px; object-fit: cover; border-radius: 6px; border: 1px solid var(--sx-border); }
.img-hint { font-size: 12.5px; color: var(--sx-text-muted); margin: -4px 0 14px; }

.site-row { display: flex; gap: 8px; align-items: center; margin-bottom: 8px; }
.site-name { flex: 0 0 140px; border: 1px solid var(--sx-border-strong); border-radius: 9px; padding: 9px 11px; font-size: 13.5px; outline: none; }
.site-url { flex: 1; border: 1px solid var(--sx-border-strong); border-radius: 9px; padding: 9px 11px; font-size: 13.5px; outline: none; }
.site-name:focus, .site-url:focus { border-color: var(--sx-accent-pink); box-shadow: 0 0 0 3px var(--sx-accent-pink-soft); }

.toast { position: fixed; left: 50%; bottom: 40px; transform: translateX(-50%); background: var(--sx-toast-bg); color: var(--sx-toast-text); padding: 11px 22px; border-radius: 10px; font-size: 14px; box-shadow: var(--sx-shadow-pop); z-index: 80; }
.fade-enter-active, .fade-leave-active { transition: opacity .25s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

@media (max-width: 720px) {
  .vc-head { flex-direction: column; align-items: stretch; }
  .fld-row { flex-direction: column; gap: 0; }
  .fld-row .sm-fld { flex: 1; }
  .vc-grid { grid-template-columns: 1fr; }
  .detail-grid { grid-template-columns: 1fr; }
}
</style>
