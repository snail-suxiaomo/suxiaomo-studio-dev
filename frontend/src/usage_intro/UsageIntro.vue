<template>
  <div class="usage-page">
    <header class="usage-head">
      <h1 class="usage-title">📖 使用介绍</h1>
      <p class="usage-desc">快速上手 suxiaomo-studio，了解每个功能最常用的操作方法</p>
    </header>

    <!-- 重要声明 -->
    <section class="usage-card notice-card">
      <div class="usage-card-head">
        <span class="head-icon">⚠️</span>
        <div>
          <h2 class="head-title">重要声明 · 使用前必读</h2>
          <p class="head-sub">花 30 秒读完，避免踩坑</p>
        </div>
      </div>
      <div class="notice-table-wrap">
        <table class="notice-table">
          <tbody>
            <tr>
              <td class="nc"><span class="nc-tag">版权</span></td>
              <td>当前软件完全免费，版权归属苏小沫</td>
            </tr>
            <tr class="row-danger">
              <td class="nc"><span class="nc-tag danger">商用</span></td>
              <td>商用请联系苏小沫，所有开发数据都有记录，<strong>侵权起诉！！！</strong></td>
            </tr>
            <tr class="row-danger">
              <td class="nc"><span class="nc-tag danger">免责</span></td>
              <td>所有数据记得保存和备份，操作不当或软件 bug 引起的数据丢失，<strong>概不负责！！！</strong></td>
            </tr>
            <tr>
              <td class="nc"><span class="nc-tag">路径</span></td>
              <td>数据与产物都保存在本地，默认都在 workspace 或您自定义的路径下，后续更新版本复制或链接直接可用</td>
            </tr>
            <tr>
              <td class="nc"><span class="nc-tag">拖拽</span></td>
              <td>所有功能卡片都支持拖拽，开发中和重构中的还在思考中，不建议使用</td>
            </tr>
            <tr>
              <td class="nc"><span class="nc-tag">需求</span></td>
              <td>想新增或优化某些功能可以联系苏小沫，需求要写详细，重大功能请提供积分支持，加急请提供💰</td>
            </tr>
            <tr>
              <td class="nc"><span class="nc-tag hot">关注</span></td>
              <td>新功能正在构思开发中，关注抖音号：<strong class="hl">苏小沫（73832469150）</strong>，粉丝或加群可获取最新版</td>
            </tr>
            <tr>
              <td class="nc"><span class="nc-tag">联系</span></td>
              <td>联系方式 wx：<strong class="hl">suxiaomo9527888</strong></td>
            </tr>
            <tr>
              <td class="nc"><span class="nc-tag hot">提示词</span></td>
              <td>提示词库和指令库想要作者版的可以联系作者导入即可使用</td>
            </tr>
            <tr class="row-version">
              <td class="nc"><span class="nc-tag ver">版本</span></td>
              <td>当前版本：<span class="ver-badge">v{{ appVersion }}</span></td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- 首次启动须知 -->
    <section class="usage-card">
      <div class="usage-card-head">
        <span class="head-icon">👋</span>
        <div>
          <h2 class="head-title">首次启动须知</h2>
          <p class="head-sub">新用户第一次打开或升级新版本时建议先看这里</p>
        </div>
      </div>
      <ul class="firsttip-list">
        <li>
          <span class="ft-ico">⏳</span>
          <div><b>首次启动会装运行环境</b><br>约几十秒到两分钟，有进度条，请耐心等待、<b>不要关闭窗口</b>。</div>
        </li>
        <li>
          <span class="ft-ico">📁</span>
          <div><b>别放系统保护目录</b><br>程序放普通位置（D 盘 / 桌面 / U 盘），勿放 <code>C:\Program Files</code>，否则无法写入数据。</div>
        </li>
        <li>
          <span class="ft-ico">🪟</span>
          <div><b>已打开不会再开新窗口</b><br>重复双击 exe 只会唤起已有窗口，这是正常的，不是没反应。</div>
        </li>
        <li>
          <span class="ft-ico">💾</span>
          <div><b>数据在 workspace 文件夹</b><br>升级新版时把旧 <code>workspace</code> 复制进新版即可沿用，建议先备份。</div>
        </li>
        <li>
          <span class="ft-ico">🗂️</span>
          <div><b>也可以选择自定义路径</b><br>首次启动或后续在「设置」里选择自定义数据目录，升级新版时直接沿用该目录即可，无需再复制 workspace。</div>
        </li>
      </ul>
    </section>

    <!-- 功能常用操作 -->
    <section class="usage-card">
      <div class="usage-card-head">
        <span class="head-icon">🧭</span>
        <div>
          <h2 class="head-title">各功能常用操作</h2>
          <p class="head-sub">每个功能挑选 3 条以上最重要、最常用、最容易踩坑的操作</p>
        </div>
      </div>

      <div class="feature-groups">
        <div v-for="g in featureGroups" :key="g.name" class="feature-group">
          <h3 class="group-title">{{ g.emoji }} {{ g.name }}</h3>
          <div class="group-items">
            <div v-for="f in g.items" :key="f.label" class="feature-item">
              <div class="feature-name">{{ f.label }}</div>
              <ul class="feature-ops">
                <li v-for="(op, idx) in f.ops" :key="idx">{{ op }}</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
const appVersion = __APP_VERSION__

const featureGroups = [
  {
    name: '漫剧创作',
    emoji: '🎬',
    items: [
      {
        label: '提示词库',
        ops: [
          '新建提示词时务必填写「类型 / 分类 / 标签」，方便后续按维度筛选复用',
          '支持导入外部 .txt 文件，导入前用「AI 分析整理」自动拆条、归类并匹配工具',
          '每条提示词正文修改后点击保存，系统会自动记录 updated_at 时间戳',
        ],
      },
      {
        label: '爆款收集',
        ops: [
          '收集前先选择平台（番茄 / 书旗 / 起点 / QQ阅读）和作品分类',
          '题材标签可直接点选常用项，也支持自由输入，避免生造未约定标签',
          '定期把爆款链接、截图、关键数据回填完整，方便后续复盘和拆解',
        ],
      },
      {
        label: '小说改写',
        ops: [
          '先在「小说改写项目」中新建或打开项目，确认项目路径和集数后再进入管线',
          '00-拆分只负责把原文拆成章节文件，不生产后续内容；拆分后建议人工检查章节边界',
          '每个步骤都需要先在「AI调用规则」里配置对应规则，再点击「AI 分析」执行',
          '05-总表是 06-改写 的强依赖，执行改写前确保总表已生成且内容完整',
        ],
      },
      {
        label: '羊毛管理',
        ops: [
          '新增站点时记录免费额度、领取步骤和截止日期，防止错过最佳薅羊毛窗口',
          '截图或上传凭证方便后续核对，避免同一账号重复注册导致被封',
          '按 fastVIP / VIP 层级标注使用优先级，优先消耗快到期额度',
        ],
      },
      {
        label: '推文助手',
        ops: [
          '推文记录只用于第三方平台发布后的回填登记，不会自动发布内容',
          '一条推文可关联多个账号和平台，登记时把链接、发布时间、数据一并填全',
          '定期导出推文数据做汇总分析，找到效果最好的发布时段和平台',
        ],
      },
    ],
  },
  {
    name: '工具箱',
    emoji: '🧰',
    items: [
      {
        label: '每日任务',
        ops: [
          '登录日期当天完成的任务会自动标记完成，跨天不会补签',
          '设置「必做」任务后可在列表顶部快速查看，避免漏掉高收益签到',
          '积分累计规则支持累计与每日两种模式，创建时按平台活动要求选择',
        ],
      },
      {
        label: '文件管理',
        ops: [
          '文件空间只保存目录书签，不会自动扫描整盘，需手动「添加目录」',
          '给常用目录加上分类和备注，后续可通过关键词快速检索',
          '双击书签即可在系统文件管理器中打开对应目录',
        ],
      },
      {
        label: '应用中心',
        ops: [
          '把常用工具或脚本路径添加进来，设置好启动参数和图标',
          '支持为同一份工具创建多个启动配置，方便切换不同项目环境',
          '启动失败时检查路径是否包含空格、参数是否正确分割',
        ],
      },
      {
        label: '网址导航',
        ops: [
          '按使用场景分组收藏网址，避免浏览器书签与工作台书签混在一起',
          '链接支持拖拽排序，最常用的放在分组最上方',
          '失效链接及时清理或替换，保持导航页整洁可用',
        ],
      },
      {
        label: '账号矩阵',
        ops: [
          '一个账号记录一个平台身份，手机号、邮箱、密码等敏感信息请自行保管',
          '通过「平台 + 用途」标签区分同一平台下的不同账号角色',
          '导入导出时确认 CSV 表头与模板一致，避免覆盖已有账号数据',
        ],
      },
    ],
  },
  {
    name: 'AI 工具',
    emoji: '🤖',
    items: [
      {
        label: 'AI 模型配置',
        ops: [
          '先新增厂商，再在该厂商下添加模型；API Key 保存在 AI 密钥库中，不在模型配置里直接填写',
          '温度（temperature）只在模型配置层设置，调用规则层不再暴露该参数',
          '测试通过后再启用模型，避免调用时因地址或 Key 错误导致任务失败',
        ],
      },
      {
        label: 'AI 调用规则',
        ops: [
          '规则按「菜单 + 功能 + 角色」三维度匹配，调用方只查表、不硬编码提示词',
          '修改规则后所有下游功能立即生效，无需重启后端',
          '参考规则来自默认文件，点击「复制使用」才会进入 DB 生效',
        ],
      },
      {
        label: 'AI 密钥库',
        ops: [
          '一个密钥对应一个厂商账号，支持为同一厂商保存多条备用 Key',
          '密钥只在后端使用，前端仅展示脱敏后的末尾几位',
          'Key 失效时可在密钥库直接切换启用其他 Key，无需修改模型配置',
        ],
      },
      {
        label: 'AI 助手',
        ops: [
          '对话前先在右上角选择模型，未选择时可能走不到预期的厂商',
          '常用提示词可从提示词库一键插入，减少重复打字',
          '长会话注意上下文 token 消耗，必要时点击「新会话」清空历史',
        ],
      },
    ],
  },
  {
    name: '设置与帮助',
    emoji: '🛠️',
    items: [
      {
        label: '设置',
        ops: [
          '数据路径修改后必须重启应用才会生效，保存时会弹出重启确认',
          '自定义路径推荐放在非系统盘，并定期复制整个目录做备份',
          '「打开当前工作空间」可直接在文件管理器中定位到数据根目录',
        ],
      },
      {
        label: '用户管理',
        ops: [
          '仅管理员可新增/删除用户，普通账号只能修改自己的密码',
          '新建用户后把默认密码告知对方并提醒首次登录修改',
          '删除用户前确认该用户名下没有未完成的重要任务或项目',
        ],
      },
      {
        label: '清除缓存',
        ops: [
          '清除缓存只会删除前端本地缓存，不会删除 workspace 中的项目和数据库',
          '遇到页面数据不同步、下拉选项不更新时可先尝试清除缓存',
          '清除后需重新登录或重新加载当前页面',
        ],
      },
      {
        label: '使用介绍',
        ops: [
          '使用介绍集中展示重要声明、首次启动须知和各功能常用操作',
          '新增功能或规则调整后，使用介绍会同步更新',
          '遇到不熟悉的功能可先来本页查找常见操作和注意事项',
        ],
      },
    ],
  },
]
</script>

<style scoped>
.usage-page {
  width: 100%;
  min-height: calc(100vh - 44px);
  padding-bottom: 40px;
  color: var(--sx-text-strong);
}

.usage-head {
  margin-bottom: 22px;
}
.usage-title {
  font-size: 26px;
  font-weight: 700;
  margin: 0 0 6px;
  color: var(--sx-text-strong);
}
.usage-desc {
  margin: 0;
  font-size: 14px;
  color: var(--sx-text);
}

.usage-card {
  background: var(--sx-bg-surface);
  border: 1px solid var(--sx-border);
  border-radius: 16px;
  padding: 22px;
  margin-bottom: 18px;
  box-shadow: var(--sx-shadow-card);
}
.usage-card-head {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 18px;
}
.head-icon {
  width: 42px;
  height: 42px;
  border-radius: 12px;
  background: var(--sx-icon-bg);
  color: var(--sx-icon-fg);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
}
.head-title {
  font-size: 17px;
  font-weight: 700;
  margin: 0 0 2px;
  color: var(--sx-text-strong);
}
.head-sub {
  margin: 0;
  font-size: 13px;
  color: var(--sx-text);
}

/* 重要声明 */
.notice-card {
  background: var(--sx-notice-warn-bg);
  border-color: var(--sx-notice-warn-border);
}
.notice-table-wrap {
  overflow-x: auto;
}
.notice-table { width: 100%; border-collapse: collapse; font-size: 14px; }
.notice-table td { padding: 12px 10px; border-bottom: 1px solid var(--sx-notice-warn-border); vertical-align: top; line-height: 1.7; color: var(--sx-text); }
.notice-table tbody tr:last-child td { border-bottom: none; }
.notice-table tbody tr:hover { background: var(--sx-notice-warn-row-hover); }
.nc { width: 80px; white-space: nowrap; }
.nc-tag {
  display: inline-flex; align-items: center; padding: 4px 12px; border-radius: 999px;
  font-size: 12.5px; font-weight: 700; background: var(--sx-notice-warn-tag-bg); color: var(--sx-notice-warn-tag-text);
}
.nc-tag.danger { background: rgba(224, 57, 57, .18); color: #ff8585; }
.nc-tag.hot { background: rgba(217, 119, 6, .18); color: #ffb347; }
.nc-tag.ver { background: var(--sx-tag-success-bg); color: var(--sx-tag-success-text); }
.row-danger { background: var(--sx-notice-warn-row-danger-bg); }
.row-danger td { color: var(--sx-notice-warn-row-danger-text); font-weight: 600; }
.row-danger strong { color: #ff8585; }
.hl { color: #ffb347; font-weight: 700; }
.ver-badge {
  display: inline-block; background: linear-gradient(135deg, #1f9d55, #37c878);
  color: #fff; font-weight: 800; padding: 3px 12px; border-radius: 8px; font-size: 14px;
}
.row-version td { background: var(--sx-tag-success-bg); }

/* 首次启动 */
.firsttip-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.firsttip-list li {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  font-size: 13.5px;
  line-height: 1.6;
  color: var(--sx-text);
}
.ft-ico { flex-shrink: 0; font-size: 18px; line-height: 1.4; }
.firsttip-list b { color: var(--sx-text-strong); }
.firsttip-list code {
  font-family: ui-monospace, Menlo, Consolas, monospace;
  font-size: 12px;
  background: var(--sx-bg-surface-2);
  color: var(--sx-text-emphasis);
  padding: 1px 6px;
  border-radius: 5px;
}

/* 功能常用操作 */
.feature-groups {
  display: flex;
  flex-direction: column;
  gap: 22px;
}
.group-title {
  font-size: 16px;
  font-weight: 700;
  margin: 0 0 12px;
  color: var(--sx-text-strong);
  padding-bottom: 8px;
  border-bottom: 1px solid var(--sx-border);
}
.group-items {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 14px;
}
.feature-item {
  background: var(--sx-bg-surface-2);
  border: 1px solid var(--sx-border);
  border-radius: 12px;
  padding: 14px 16px;
}
.feature-name {
  font-weight: 700;
  font-size: 14px;
  margin-bottom: 10px;
  color: var(--sx-text-strong);
}
.feature-ops {
  margin: 0;
  padding-left: 18px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 13px;
  color: var(--sx-text);
  line-height: 1.55;
}
.feature-ops li::marker { color: var(--sx-accent); }

@media (max-width: 640px) {
  .group-items { grid-template-columns: 1fr; }
  .notice-table td { padding: 10px 7px; font-size: 13px; }
  .nc { width: 62px; }
}
</style>
