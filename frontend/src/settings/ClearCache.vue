<template>
  <div class="cc-page">
    <header class="cc-head">
      <h1 class="cc-title">清除缓存</h1>
      <p class="cc-desc">管理浏览器本地缓存数据。参考浏览器的「删除浏览数据」，按数据类型分类清理。</p>
    </header>

    <!-- 醒目提示：业务数据不在浏览器缓存里，绝不会被清除 -->
    <div class="cc-safe">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
        <path d="M9 12l2 2 4-4" />
      </svg>
      <span><b>不会清除你的作品</b>：所有提示词 / 项目等数据都存放在后端的 <code>workspace</code> 目录与数据库（<code>app.db</code> 等）里，<b>不在浏览器缓存中</b>，这里的清除操作碰不到它们。</span>
    </div>

    <section class="cc-card">
      <div class="cc-item">
        <div class="cc-item-icon">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
            <circle cx="12" cy="7" r="4" />
          </svg>
        </div>
        <div class="cc-item-body">
          <div class="cc-item-title">登录信息</div>
          <div class="cc-item-desc">退出当前账号，并忘记记住的账号密码（下次需重新登录 / 重填）。不影响作品与界面设置。</div>
        </div>
        <button class="cc-btn" @click="clearLogin">清除</button>
      </div>

      <div class="cc-item">
        <div class="cc-item-icon">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
            <path d="M3 9h18M9 21V9" />
          </svg>
        </div>
        <div class="cc-item-body">
          <div class="cc-item-title">缓存的图片和文件（界面缓存）</div>
          <div class="cc-item-desc">清除 HTTP 磁盘缓存并重启，专治「改了样式 / 资源不更新」。保留账号与界面设置。</div>
        </div>
        <button class="cc-btn" @click="clearHttp">清除并重启</button>
      </div>

      <div class="cc-item danger">
        <div class="cc-item-icon">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
            <line x1="10" y1="11" x2="10" y2="17" />
            <line x1="14" y1="11" x2="14" y2="17" />
          </svg>
        </div>
        <div class="cc-item-body">
          <div class="cc-item-title">全部本地缓存</div>
          <div class="cc-item-desc">账号 + HTTP 缓存 + 界面设置 + 浏览器存储（localStorage / Cookie 等）全部清空，重启后回到初次启动。<b>仍不影响 workspace 目录与数据库。</b></div>
        </div>
        <button class="cc-btn danger" @click="clearAll">彻底清除</button>
      </div>
    </section>

    <p v-if="result" class="cc-result" :class="resultType">{{ result }}</p>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../login/auth-store.js'

const auth = useAuthStore()
const router = useRouter()
const result = ref('')
const resultType = ref('')

function showResult(msg, type = 'ok') {
  result.value = msg
  resultType.value = type
}

// 1. 清除登录信息：纯前端，退出账号（不影响作品 / 设置）
function clearLogin() {
  if (!window.confirm('确定退出当前账号，并忘记记住的账号密码吗？')) return
  auth.logout()
  showResult('已清除登录信息，正在跳转到登录页…')
  setTimeout(() => router.push('/login'), 600)
}

// 2. 刷新界面缓存：清 HTTP 磁盘缓存并重启（保留账号与设置）
async function clearHttp() {
  if (!window.confirm('确定清除界面缓存并重启应用吗？（账号与设置会保留）')) return
  if (!window.electronAPI || !window.electronAPI.clearCache) {
    showResult('当前环境不支持该操作', 'err')
    return
  }
  try {
    await window.electronAPI.clearCache('http')
    showResult('界面缓存已清除，正在重启…')
    if (window.electronAPI.restartApp) window.electronAPI.restartApp()
    else location.reload()
  } catch (e) {
    showResult('清除失败：' + (e && e.message ? e.message : e), 'err')
  }
}

// 3. 全部本地缓存：清账号 + HTTP 缓存 + 设置 + 浏览器存储，重启回初次（不影响 workspace/DB）
async function clearAll() {
  if (!window.confirm('将清除全部本地缓存（账号 / 界面缓存 / 设置 / 浏览器存储），重启后回到初次启动。确定继续？\n\n注意：此操作不影响你的作品与数据库（workspace / app.db 等）。')) return
  if (!window.electronAPI || !window.electronAPI.clearCache) {
    showResult('当前环境不支持该操作', 'err')
    return
  }
  try {
    // 先退出登录态，避免在重启过程中仍带旧 token
    auth.logout()
    await window.electronAPI.clearCache('all')
    showResult('全部本地缓存已清除，正在重启…')
    if (window.electronAPI.restartApp) window.electronAPI.restartApp()
    else location.reload()
  } catch (e) {
    showResult('清除失败：' + (e && e.message ? e.message : e), 'err')
  }
}
</script>

<style scoped>
.cc-page {
  padding: 28px 24px 40px;
}
.cc-head { margin-bottom: 18px; }
.cc-title { margin: 0 0 6px; font-size: 22px; color: var(--text-primary, #1f2330); }
.cc-desc { margin: 0; font-size: 13px; color: var(--text-secondary, #6e7391); line-height: 1.6; }

/* 安全提示条 */
.cc-safe {
  display: flex; align-items: flex-start; gap: 10px;
  padding: 12px 14px; margin-bottom: 18px;
  background: #eef7ef; border: 1px solid #cfe9d4; border-radius: 12px;
  font-size: 12.5px; color: #2f6b43; line-height: 1.6;
}
.cc-safe svg { flex-shrink: 0; margin-top: 1px; color: #2f9e4f; }
.cc-safe code {
  font-family: ui-monospace, Menlo, Consolas, monospace;
  background: rgba(0,0,0,.05); padding: 1px 5px; border-radius: 4px; font-size: 12px;
}

.cc-card {
  background: var(--bg-card, #fff);
  border: 1px solid var(--border-card, #e7e9f2);
  border-radius: 16px;
  box-shadow: var(--shadow-card, 0 3px 14px rgba(30,34,56,.04));
  overflow: hidden;
}
.cc-item {
  display: flex; align-items: center; gap: 14px;
  padding: 16px 18px;
  border-bottom: 1px solid var(--border-soft, #eef0f6);
}
.cc-item:last-child { border-bottom: none; }
.cc-item.danger { background: #fff8f8; }
.cc-item-icon {
  width: 40px; height: 40px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  border-radius: 11px; background: #eef1fa; color: #4f7cff;
}
.cc-item.danger .cc-item-icon { background: #fdeaea; color: #e25757; }
.cc-item-body { flex: 1; min-width: 0; }
.cc-item-title { font-size: 14.5px; font-weight: 600; color: var(--text-primary, #1f2330); }
.cc-item.danger .cc-item-title { color: #c0392b; }
.cc-item-desc { margin-top: 3px; font-size: 12.5px; color: var(--text-secondary, #6e7391); line-height: 1.55; }
.cc-item-desc b { color: var(--text-primary, #1f2330); }

.cc-btn {
  flex-shrink: 0;
  padding: 8px 16px; border-radius: 9px; cursor: pointer;
  border: 1px solid #d7dbed; background: #fff; color: #4f7cff;
  font-size: 13px; font-weight: 600; transition: .15s;
}
.cc-btn:hover { background: #f0f4ff; border-color: #b9cdff; }
.cc-btn.danger { border-color: #f0caca; background: #fff; color: #e25757; }
.cc-btn.danger:hover { background: #fdeaea; border-color: #ecb6b6; }

.cc-result {
  margin-top: 16px; padding: 10px 14px; border-radius: 10px;
  font-size: 13px;
}
.cc-result.ok { background: #eef7ef; color: #2f6b43; border: 1px solid #cfe9d4; }
.cc-result.err { background: #fdf0f0; color: #c0392b; border: 1px solid #f3d2d2; }

:global([data-theme="dark"]) .cc-safe { background: #18301f; border-color: #2c4a36; color: #8fd6a6; }
:global([data-theme="dark"]) .cc-safe code { background: rgba(255,255,255,.08); }
:global([data-theme="dark"]) .cc-item-icon { background: #232740; color: #8fa8ff; }
:global([data-theme="dark"]) .cc-item.danger .cc-item-icon { background: #3a2326; color: #ff8a8a; }
:global([data-theme="dark"]) .cc-btn { background: #232740; border-color: #353c5e; color: #8fa8ff; }
:global([data-theme="dark"]) .cc-btn:hover { background: #2a3050; border-color: #4f7cff; }
:global([data-theme="dark"]) .cc-btn.danger { background: #3a2326; border-color: #5c2f33; color: #ff8a8a; }
:global([data-theme="dark"]) .cc-btn.danger:hover { background: #4a2a2e; border-color: #b33838; }
</style>
