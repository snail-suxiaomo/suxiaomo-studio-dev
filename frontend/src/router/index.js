import { createRouter, createWebHistory } from 'vue-router'
import { isEnabled, registry } from '../common/features.js'
import { ENABLED_IMPORTS } from '../common/enabled-imports.js'
import { useAuthStore } from '../login/auth-store.js'
import { useProjectStore } from '../common/project-store.js'

// 开发态全量静态映射：dev 下直接使用；prod 下处于死分支被 Rollup 整体摇掉
const ALL_IMPORTS = {
  prompt_library: () => import('../prompt_library/PromptLibrary.vue'),
  novel_create: () => import('../common/DevPlaceholder.vue'),
  script_create: () => import('../common/DevPlaceholder.vue'),
  viral_collection: () => import('../viral_collection/ViralCollection.vue'),
  novel_project: () => import('../novel_project/ProjectList.vue'),
  novel_project_detail: () => import('../novel_project/ProjectDetail.vue'),
  free_resources: () => import('../free_resources/FreeResources.vue'),
  novel_tweet: () => import('../novel_tweet/NovelTweet.vue'),
  daily_tasks: () => import('../daily_tasks/DailyTasks.vue'),
  filespace: () => import('../filespace/FileSpace.vue'),
  apps_launcher: () => import('../apps-launcher/AppLauncher.vue'),
  web_nav: () => import('../web_nav/WebNav.vue'),
  social_accounts: () => import('../social_account/SocialAccount.vue'),
  chat: () => import('../chat/Chat.vue'),
  key_vault: () => import('../key_vault/KeyVault.vue'),
  model_config: () => import('../model_config/ModelConfig.vue'),
  ai_call_rule: () => import('../ai_rule/AiRuleManage.vue'),
  settings: () => import('../settings/Settings.vue'),
  user_management: () => import('../settings/UserManagement.vue'),
  clear_cache: () => import('../settings/ClearCache.vue'),
  usage_intro: () => import('../usage_intro/UsageIntro.vue'),
  manju_generate: () => import('../manju_generate/ManJuGenerate.vue'),
  novel_split: () => import('../novel_split/SplitUpload.vue'),
  novel_synopsis: () => import('../novel_synopsis/Synopsis.vue'),
  novel_graph: () => import('../novel_graph/Graph.vue'),
  novel_diagnose: () => import('../novel_diagnose/Diagnose.vue'),
  novel_strategy: () => import('../novel_strategy/Strategy.vue'),
  novel_summary_table: () => import('../novel_summary_table/SummaryTable.vue'),
  novel_rewrite: () => import('../novel_rewrite/Rewrite.vue'),
  novel_memory: () => import('../novel_memory/MemoryView.vue'),
  login: () => import('../login/Login.vue'),
  register: () => import('../login/Register.vue'),
  home: () => import('../common/Home.vue'),
}

// prod 构建用 build.js 生成的 ENABLED_IMPORTS（仅启用功能的 import()）；
// dev 用全量 ALL_IMPORTS。prod 下 ALL_IMPORTS 处于 `import.meta.env.DEV` 死分支被摇掉，
// 未勾选功能的 import() 表达式不进产物 → 其 chunk 不被生成（真正剔除前端代码）。
const IMPORTS = import.meta.env.DEV ? ALL_IMPORTS : ENABLED_IMPORTS

function buildRoute(key, f) {
  const r = { path: f.route }
  if (IMPORTS[key]) r.component = IMPORTS[key]
  if (f.props) r.props = f.props
  // login/register 必须公开（否则无法进入登录流程）；home 需登录后才可见，
  // 否则无 session 时会被守卫放行停在 /home，导致 Login.vue 的自动登录永不触发、侧边栏消失。
  if (f.core && key !== 'home') r.meta = { public: true }
  return r
}

const routes = [
  { path: '/', redirect: '/home' },
]

// 按注册表 + 启用状态注册路由：未启用的功能不进入 routes（页面打不开、组件不被主包引用）
for (const [key, f] of Object.entries(registry.features)) {
  if (!f.route || !IMPORTS[key]) continue
  if (!isEnabled(key)) continue
  routes.push(buildRoute(key, f))
  // 小说改写详情页（带 :id）随父功能一起启用（统一走 IMPORTS，便于打包态一起剔除）
  if (key === 'novel_project' && IMPORTS['novel_project_detail']) {
    routes.push({ path: '/novel_project/:id', component: IMPORTS['novel_project_detail'] })
  }
}

// 日志查看 / 发布版本：仅开发版注册路由（打包版不暴露入口）
if (import.meta.env.DEV) {
  routes.push({ path: '/log-viewer', component: () => import('../log_viewer/LogViewer.vue') })
  routes.push({ path: '/packaging', component: () => import('../packaging/PackagingView.vue') })
}

// 爆款收集：独立浏览器窗口路由（方案 C）。与主窗口共享登录态（默认 partition），
// 该路由不依赖功能注册表，直接在打包产物中常驻。
routes.push({ path: '/viral-browser', component: () => import('../viral_collection/ViralBrowserWindow.vue') })

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 管线功能页路径（用于归档拦截）：从注册表动态派生（novel_project 的子功能）
const FUNC_ROUTES = Object.entries(registry.features)
  .filter(([, f]) => f.parent === 'novel_project')
  .map(([, f]) => f.route)

// 路由守卫：未登录跳 /login；已登录还访问登录页则去 /home
router.beforeEach((to) => {
  const auth = useAuthStore()
  if (!to.meta.public && !auth.token) {
    return '/login'
  }
  if (to.meta.public && auth.token) {
    return '/home'
  }
  // 归档拦截：进入管线功能页时，若当前项目已归档则弹回详情页并带 archived 提示
  if (FUNC_ROUTES.includes(to.path)) {
    const proj = useProjectStore()
    if (proj.current && proj.current.status === 'archived') {
      return { path: `/novel_project/${proj.current.id}`, query: { archived: '1' } }
    }
  }
})

export default router
