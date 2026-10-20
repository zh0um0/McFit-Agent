<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { api, IS_DEMO } from '../api/client'

const auth = useAuthStore()
const router = useRouter()

const mode = ref('login')          // login | register
// 演示模式预填演示账号，访客点一下「登录」即可进入
const form = reactive({ username: IS_DEMO ? 'demo' : '', password: IS_DEMO ? 'demo123456' : '', email: '' })
const health = ref(null)

api.health().then((h) => (health.value = h)).catch(() => (health.value = null))

async function submit() {
  try {
    if (mode.value === 'register') {
      await auth.register({ username: form.username, password: form.password,
                            email: form.email || undefined })
    } else {
      await auth.login({ username: form.username, password: form.password })
    }
    router.push('/')
  } catch { /* 错误已在 auth.error */ }
}
</script>

<template>
  <div class="login-wrap">
    <div class="login-card card">
      <div class="login-logo">🍔</div>
      <div class="login-title">
        <h1>麦门控卡精明私教</h1>
        <p>控卡 · 省钱 · 贴纸打卡，一顿麦当劳也能吃出掌控感</p>
      </div>

      <div class="tabs">
        <button :class="{ active: mode === 'login' }" @click="mode = 'login'">登录</button>
        <button :class="{ active: mode === 'register' }" @click="mode = 'register'">注册</button>
      </div>

      <div v-if="auth.error" class="alert alert-error">{{ auth.error }}</div>

      <form @submit.prevent="submit">
        <div class="field">
          <label>用户名</label>
          <input v-model.trim="form.username" type="text" required
                 placeholder="3-30位字母/数字/中文" autocomplete="username" />
        </div>

        <div v-if="mode === 'register'" class="field">
          <label>邮箱（选填）</label>
          <input v-model.trim="form.email" type="email" placeholder="用于找回账号" />
        </div>

        <div class="field">
          <label>密码</label>
          <input v-model="form.password" type="password" required
                 :placeholder="mode === 'register' ? '至少8位，含字母和数字' : ''"
                 :autocomplete="mode === 'register' ? 'new-password' : 'current-password'" />
        </div>

        <button class="btn btn-primary btn-block" type="submit" :disabled="auth.loading">
          <span v-if="auth.loading" class="spinner"></span>
          {{ mode === 'login' ? '登录' : '注册并开始' }}
        </button>
      </form>

      <div v-if="health" class="alert alert-info mt-16" style="font-size:12px">
        后端状态：{{ health.status === 'ok' ? '正常' : '降级' }} ·
        数据库 {{ health.database === 'sqlite' ? '本地SQLite' : 'Postgres' }} ·
        MCP 模式
        <span class="badge" :class="health.mcp_configured ? 'badge-ok' : 'badge-muted'">
          {{ health.mcp_configured ? '官方实时' : '内置种子' }}
        </span>
      </div>
      <div v-else class="alert alert-error mt-16" style="font-size:12px">
        未检测到后端服务。请在 backend 目录执行
        <code>uvicorn app.main:app --reload --port 8000</code>
      </div>

      <div v-if="IS_DEMO" class="disclaimer">
        已为你填好演示账号（<b>demo</b> / <b>demo123456</b>），直接点「登录」即可体验。<br />
        本产品输出的营养与运动数据均为<b>估算值</b>，仅供参考，不构成医疗或营养专业建议。
      </div>
    </div>
  </div>
</template>