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

      <h2 class="auth-h2">创建账号</h2>
      <p class="auth-desc">注册后即可开始创作</p>

      <form @submit.prevent="onRegister" class="auth-form">
      <label class="field">
        <span class="field-label">账号</span>
        <input v-model="username" placeholder="英文或英文+数字，字母开头" autocomplete="username" @input="onAcctInput" />
      </label>
        <label class="field">
          <span class="field-label">密码</span>
          <input v-model="password" type="password" placeholder="请输入密码" autocomplete="new-password" />
        </label>
        <label class="field">
          <span class="field-label">昵称<span class="opt">（可空）</span></span>
          <input v-model="displayName" placeholder="展示用昵称" @keyup.enter="onRegister" />
        </label>
        <button type="submit" class="btn-primary" :disabled="loading">
          <span v-if="loading" class="spinner"></span>
          {{ loading ? '注册中…' : '注 册' }}
        </button>
      </form>

      <p v-if="error" class="err">{{ error }}</p>

      <div class="auth-footer">
        <span>已有账号？<router-link to="/login">去登录</router-link></span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { registerApi } from './auth-api.js'
import { useAuthStore } from './auth-store.js'

const username = ref('')
const password = ref('')
const displayName = ref('')
const error = ref('')
const loading = ref(false)
const auth = useAuthStore()
const router = useRouter()

function onAcctInput(e) {
  const v = (e.target.value || '').replace(/[^a-zA-Z0-9]/g, '')
  username.value = v
  if (e.target.value !== v) e.target.value = v
}

async function onRegister() {
  error.value = ''
  if (!/^[a-zA-Z][a-zA-Z0-9]{1,19}$/.test(username.value.trim())) {
    error.value = '账号须为字母开头、仅含英文与数字，长度 2-20'
    return
  }
  loading.value = true
  try {
    const data = await registerApi(username.value.trim(), password.value, displayName.value || null)
    auth.setSession(data.access_token, data.user)
    router.push('/home')
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}
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
.field-label { font-size: 12.5px; color: #5a6072; font-weight: 600; }
.field-label .opt { color: #b3b8c9; font-weight: 400; }
.field input {
  width: 100%; box-sizing: border-box;
  padding: 11px 13px; font-size: 14px;
  border: 1.5px solid #e3e6ef; border-radius: 10px;
  background: #f8f9fc; color: #1f2330;
  transition: border-color .15s, background .15s, box-shadow .15s;
}
.field input::placeholder { color: #b3b8c9; }
.field input:focus {
  outline: none; border-color: #4f7cff; background: #fff;
  box-shadow: 0 0 0 3px rgba(79, 124, 255, 0.15);
}

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
.auth-footer { margin-top: 20px; font-size: 13px; color: #5a6072; text-align: center; }
.auth-footer a { color: #4f7cff; text-decoration: none; font-weight: 600; }
.auth-footer a:hover { text-decoration: underline; }
</style>
