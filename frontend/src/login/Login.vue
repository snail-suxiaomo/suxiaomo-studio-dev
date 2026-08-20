<template>
  <div class="auth-stage">
    <div class="auth-card">
      <div class="brand">
        <div class="brand-mark">苏</div>
        <div class="brand-text">
          <div class="brand-title">苏小沫工作台</div>
          <div class="brand-sub">智能创作工作台</div>
        </div>
      </div>

      <h2 class="auth-h2">欢迎回来</h2>
      <p class="auth-desc">登录以继续创作</p>

      <!-- 账号：下拉选择已记住的账号 / 或输入新账号 -->
      <label class="field">
        <span class="field-label">账号</span>
        <div class="acct-row">
          <select
            v-if="!addingNew"
            v-model="selectedUser"
            class="acct-select"
            @change="onSelectChange"
          >
            <option v-for="a in accounts" :key="a.username" :value="a.username">
              {{ a.username }}
            </option>
            <option value="__add__">+ 添加账号</option>
          </select>
          <input
            v-else
            v-model="username"
            class="acct-input"
            placeholder="英文或英文+数字"
            autocomplete="username"
            @input="onAcctInput"
          />
          <button
            v-if="!addingNew && accounts.length"
            type="button"
            class="acct-x"
            title="删除此账号（仅清除本机记住的记录，不影响真实账号）"
            @click="removeSelected"
          >
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">
              <line x1="6" y1="6" x2="18" y2="18"/>
              <line x1="6" y1="18" x2="18" y2="6"/>
            </svg>
          </button>
        </div>
      </label>

      <label class="field">
        <span class="field-label">密码</span>
        <div class="pw-row">
          <input
            v-model="password"
            :type="showPwd ? 'text' : 'password'"
            placeholder="请输入密码"
            autocomplete="current-password"
            @keyup.enter="onLogin"
          />
          <button
            type="button"
            class="pw-eye"
            :title="showPwd ? '隐藏密码' : '显示密码'"
            @click="showPwd = !showPwd"
          >
            <svg v-if="showPwd" viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/>
              <line x1="1" y1="1" x2="23" y2="23"/>
            </svg>
            <svg v-else viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
              <circle cx="12" cy="12" r="3"/>
            </svg>
          </button>
        </div>
      </label>

      <div class="auto-row-group">
        <label class="auto-row">
          <input type="checkbox" v-model="rememberPassword" />
          <span>记住密码</span>
        </label>
        <label class="auto-row">
          <input type="checkbox" v-model="autoLogin" />
          <span>自动登录</span>
        </label>
      </div>

      <button type="button" class="btn-primary" :disabled="loading" @click="onLogin">
        <span v-if="loading" class="spinner"></span>
        {{ loading ? '登录中…' : '登 录' }}
      </button>

      <p v-if="error" class="err">{{ error }}</p>
      <p v-if="warn && !error" class="warn">{{ warn }}</p>

      <div class="auth-footer">
        <span>还没有账号？<router-link to="/register">去注册</router-link></span>
      </div>
      <p class="hint">默认管理员：admin / admin</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { loginApi } from './auth-api.js'
import {
  listRemembered,
  getRemembered,
  saveRemembered,
  deleteRemembered,
} from './auth-api.js'
import { useAuthStore } from './auth-store.js'

const auth = useAuthStore()
const router = useRouter()

const accounts = ref([])          // 记住的账号列表（来自数据库）
const selectedUser = ref('')      // 下拉当前选中的用户名
const addingNew = ref(false)      // true=手动输入新账号
const username = ref('')          // 添加模式下的用户名输入
const password = ref('')
const error = ref('')
const loading = ref(false)
const rememberPassword = ref(false)
const autoLogin = ref(false)
const warn = ref('')           // 非阻断性警告（如加密失败仍允许登录）
const showPwd = ref(false)     // 密码明文显示开关（小眼睛）

// 自动登录必须依赖记住密码：用户勾自动登录时自动连带勾选记住密码
watch(autoLogin, (val) => {
  if (val && !rememberPassword.value) rememberPassword.value = true
})

async function loadAccounts() {
  try {
    accounts.value = await listRemembered()
  } catch (e) {
    accounts.value = []
  }
}

// 把某个记住的账号填进表单（含解密密码）
async function loadAccountIntoForm(uname) {
  const acc = accounts.value.find((a) => a.username === uname)
  if (!acc) return
  selectedUser.value = uname
  addingNew.value = false
  rememberPassword.value = !!acc.remember_password
  autoLogin.value = !!acc.auto_login
  password.value = ''
  if (acc.remember_password) {
    try {
      const detail = await getRemembered(uname)
      password.value = detail.password || ''
      console.log('[login] 密码已回填')
    } catch (e) {
      console.warn('[login] 加载账号详情失败:', e)
    }
  }
}

function onAcctInput(e) {
  // 账号仅允许英文与数字：实时过滤非法字符（添加新账号模式）
  const v = (e.target.value || '').replace(/[^a-zA-Z0-9]/g, '')
  username.value = v
  if (e.target.value !== v) e.target.value = v
}

function onSelectChange() {
  if (selectedUser.value === '__add__') {
    addingNew.value = true
    username.value = ''
    password.value = ''
    rememberPassword.value = false
    autoLogin.value = false
    return
  }
  addingNew.value = false
  loadAccountIntoForm(selectedUser.value)
}

async function removeSelected() {
  const uname = selectedUser.value
  if (!uname) return
  await deleteRemembered(uname).catch(() => {})
  accounts.value = accounts.value.filter((a) => a.username !== uname)
  if (accounts.value.length) {
    await loadAccountIntoForm(accounts.value[0].username)
  } else {
    addingNew.value = true
    selectedUser.value = ''
    username.value = ''
    password.value = ''
  }
}

async function onLogin() {
  error.value = ''
  warn.value = ''
  const uname = (addingNew.value ? username.value : selectedUser.value).trim()
  const pwd = password.value
  if (!uname || !pwd) {
    error.value = '请输入账号和密码'
    return
  }
  loading.value = true
  try {
    const data = await loginApi(uname, pwd)
    auth.setSession(data.access_token, data.user)

    // 保存「记住的账号」：明文密码交给后端加密存储（跨环境稳定，不依赖 Electron safeStorage）
    try {
      await saveRemembered({
        username: uname,
        password: pwd,
        remember_password: rememberPassword.value,
        auto_login: autoLogin.value,
      })
      console.log('[login] 账号记忆已保存（记住密码=' + rememberPassword.value + ', 自动登录=' + autoLogin.value + '）')
    } catch (e) {
      warn.value = '账号记忆保存失败：' + (e?.message || e)
      console.warn('[login] saveRemembered 失败:', e)
    }

    await loadAccounts()
    router.push('/home')
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

// 等后端就绪：冷启动 / 重启时后端端口虽开、应用可能还没完全起来，
// 直接拉账号会让接口瞬时失败，导致自动登录不触发。轮询 /api/health 直到可用（最多 ~12s）。
async function waitBackend(maxMs = 12000, intervalMs = 400) {
  const deadline = Date.now() + maxMs
  while (Date.now() < deadline) {
    try {
      const res = await fetch('/api/health')
      if (res.ok) return true
    } catch (e) {
      /* 后端还没就绪，继续等待 */
    }
    await new Promise((r) => setTimeout(r, intervalMs))
  }
  return false
}

onMounted(async () => {
  // 先等后端稳定，避免冷启动时接口瞬时失败把自动登录跳过
  await waitBackend()
  await loadAccounts()
  if (!accounts.value.length) {
    addingNew.value = true
    return
  }
  // 默认选中：最近一次登录的账号（列表已按 last_login_at 倒序，accounts[0] 即最近登录）。
  // 多账号下以「最近登录」为准，避免被历史勾过自动登录的其他账号抢走默认位。
  const def = accounts.value[0]
  await loadAccountIntoForm(def.username)
  // 自动登录：仅当「勾了自动登录 + 记住了密码 + 本次非主动退出」
  if (def.auto_login && def.remember_password && !auth.manualLogout) {
    // 重试几次，吸收后端刚就绪时密码回填接口的瞬时抖动
    for (let i = 0; i < 5; i++) {
      if (password.value) {
        await onLogin()
        if (auth.token) return // 登录成功（onLogin 内已跳转主页）
        return // 账号/密码错误等硬错误，停止重试
      }
      // 密码尚未回填好 → 稍后重新拉取再试
      await new Promise((r) => setTimeout(r, 500))
      await loadAccountIntoForm(def.username)
    }
  }
})
</script>

<style scoped>
.auth-stage {
  position: fixed; inset: 0; z-index: 999;
  display: flex; align-items: center; justify-content: center;
  padding: 20px; box-sizing: border-box;
  background: radial-gradient(1200px 600px at 15% 10%, #2a3358 0%, transparent 55%),
              radial-gradient(1000px 700px at 90% 90%, #3b2a63 0%, transparent 50%),
              linear-gradient(135deg, #171a2b 0%, #1f2540 55%, #14162a 100%);
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
}
.auth-card {
  width: 380px; max-width: 100%;
  padding: 36px 34px 28px;
  background: rgba(255, 255, 255, 0.98);
  border: 1px solid rgba(255, 255, 255, 0.6);
  border-radius: 18px;
  box-shadow: 0 24px 70px rgba(0, 0, 0, 0.45), 0 2px 8px rgba(0, 0, 0, 0.2);
  animation: rise .5s cubic-bezier(.2,.8,.2,1);
}
@keyframes rise { from { opacity: 0; transform: translateY(18px); } to { opacity: 1; transform: none; } }

.brand { display: flex; align-items: center; gap: 12px; margin-bottom: 26px; }
.brand-mark {
  width: 46px; height: 46px; flex: none;
  display: flex; align-items: center; justify-content: center;
  font-size: 24px; font-weight: 700; color: #fff;
  border-radius: 13px;
  background: linear-gradient(135deg, #4f7cff 0%, #7b5cff 100%);
  box-shadow: 0 6px 16px rgba(79, 124, 255, 0.45);
}
.brand-title { font-size: 17px; font-weight: 700; color: #1f2330; letter-spacing: .3px; }
.brand-sub { font-size: 12px; color: #8a90a6; margin-top: 3px; }

.auth-h2 { margin: 0 0 4px; font-size: 22px; color: #1f2330; }
.auth-desc { margin: 0 0 22px; font-size: 13px; color: #8a90a6; }

.auth-form { display: flex; flex-direction: column; gap: 15px; }
.field { display: flex; flex-direction: column; gap: 6px; }
.field + .field { margin-top: 18px; }
.field-label { font-size: 12.5px; color: #5a6072; font-weight: 600; }

.acct-row { position: relative; display: flex; align-items: center; }
.acct-select, .acct-input {
  flex: 1; width: 100%; box-sizing: border-box;
  padding: 11px 40px 11px 13px; font-size: 14px;
  border: 1.5px solid #e3e6ef; border-radius: 10px;
  background: #f8f9fc; color: #1f2330;
  transition: border-color .15s, background .15s, box-shadow .15s;
}
.acct-select:focus, .acct-input:focus {
  outline: none; border-color: #4f7cff; background: #fff;
  box-shadow: 0 0 0 3px rgba(79, 124, 255, 0.15);
}

.field input {
  width: 100%; box-sizing: border-box;
  padding: 11px 42px 11px 13px; font-size: 14px;
  border: 1.5px solid #e3e6ef; border-radius: 10px;
  background: #f8f9fc; color: #1f2330;
  transition: border-color .15s, background .15s, box-shadow .15s;
}
.field input::placeholder { color: #b3b8c9; }
.field input:focus {
  outline: none; border-color: #4f7cff; background: #fff;
  box-shadow: 0 0 0 3px rgba(79, 124, 255, 0.15);
}

.auto-row-group {
  display: flex; align-items: center; gap: 28px;
  margin-top: 14px;
}
.auto-row {
  display: flex; align-items: center; gap: 8px;
  font-size: 13px; color: #5a6072; cursor: pointer; user-select: none;
  margin-top: 0;
}
.auto-row input { width: 15px; height: 15px; accent-color: #4f7cff; cursor: pointer; }

.acct-x {
  position: absolute; right: 30px; top: 50%; transform: translateY(-50%);
  width: 26px !important; height: 26px !important;
  border: none; background: transparent; color: #a7adbf;
  font-size: 20px; line-height: 1; cursor: pointer; border-radius: 6px;
  display: flex !important; align-items: center; justify-content: center;
  padding: 0 !important;
}
.acct-x:hover { background: #fdecec; color: #c0392b; }

.pw-row { position: relative; display: flex; align-items: center; }
.pw-eye {
  position: absolute; right: 8px; top: 50%; transform: translateY(-50%);
  width: 26px !important; height: 26px !important;
  border: none; background: transparent; cursor: pointer;
  display: flex !important; align-items: center; justify-content: center;
  padding: 0 !important; border-radius: 6px;
  color: #8b90b0;
}
.pw-eye svg { display: block; }
.pw-eye:hover { color: #4f7cff; }

.link-btn {
  border: none; background: transparent; cursor: pointer;
  color: #4f7cff; font-size: 12.5px; font-weight: 600; padding: 0; white-space: nowrap;
}
.link-btn:hover { text-decoration: underline; }
.link-btn.del { color: #c0392b; }

.btn-primary {
  margin-top: 6px; width: 100%; padding: 12px;
  display: flex; align-items: center; justify-content: center; gap: 8px;
  font-size: 15px; font-weight: 600; letter-spacing: 2px; color: #fff;
  border: none; border-radius: 10px; cursor: pointer;
  background: linear-gradient(135deg, #4f7cff 0%, #7b5cff 100%);
  box-shadow: 0 8px 20px rgba(79, 124, 255, 0.35);
  transition: transform .1s, box-shadow .15s, opacity .15s;
}
.btn-primary:hover:not(:disabled) { transform: translateY(-1px); box-shadow: 0 12px 26px rgba(79, 124, 255, 0.45); }
.btn-primary:active:not(:disabled) { transform: translateY(0); }
.btn-primary:disabled { opacity: .7; cursor: default; }
.spinner {
  width: 15px; height: 15px; border-radius: 50%;
  border: 2px solid rgba(255,255,255,.4); border-top-color: #fff;
  animation: spin .7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.err {
  margin: 14px 0 0; padding: 9px 12px; font-size: 13px;
  color: #c0392b; background: #fdecec; border: 1px solid #f5c6c6; border-radius: 8px;
}
.warn {
  margin: 14px 0 0; padding: 9px 12px; font-size: 13px;
  color: #b7791f; background: #fff8e6; border: 1px solid #f5deb3; border-radius: 8px;
}
.auth-footer { margin-top: 20px; font-size: 13px; color: #5a6072; text-align: center; }
.auth-footer a { color: #4f7cff; text-decoration: none; font-weight: 600; }
.auth-footer a:hover { text-decoration: underline; }
.hint { margin: 14px 0 0; text-align: center; color: #b3b8c9; font-size: 12px; }
</style>
