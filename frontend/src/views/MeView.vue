<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api/client'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()
const health = ref(null)
const history = ref([])
const msg = ref('')
const err = ref('')
const newPwd = ref('')
const oldPwd = ref('')

async function load() {
  try {
    health.value = await api.health()
    const h = await api.get('/api/v1/orders')
    history.value = h.items || []
  } catch (e) {
    err.value = e.message
  }
}
onMounted(load)

async function changePwd() {
  err.value = ''; msg.value = ''
  try {
    const r = await api.post('/api/v1/auth/change-password',
      { old_password: oldPwd.value, new_password: newPwd.value })
    msg.value = r.message
    oldPwd.value = ''; newPwd.value = ''
  } catch (e) {
    err.value = e.message
  }
}

function logout() {
  auth.logout()
  router.push('/login')
}
</script>

<template>
  <div>
    <div v-if="err" class="alert alert-error">{{ err }}</div>
    <div v-if="msg" class="alert alert-ok">{{ msg }}</div>

    <div class="card">
      <h2 class="card-title">账号信息</h2>
      <div class="grid cols-4">
        <div class="stat info"><div class="label">用户名</div>
          <div class="value" style="font-size:18px">{{ auth.user?.username }}</div></div>
        <div class="stat"><div class="label">角色</div>
          <div class="value" style="font-size:18px">{{ auth.user?.role }}</div></div>
        <div class="stat"><div class="label">登录方式</div>
          <div class="value" style="font-size:18px">{{ auth.user?.provider }}</div></div>
        <div class="stat"><div class="label">加入时间</div>
          <div class="value" style="font-size:14px">
            {{ auth.user?.created_at?.slice(0, 10) }}
          </div></div>
      </div>
    </div>

    <div class="card">
      <h2 class="card-title">系统状态</h2>
      <div v-if="health" class="grid cols-4">
        <div class="stat" :class="health.status === 'ok' ? 'ok' : 'warn'">
          <div class="label">服务</div><div class="value" style="font-size:18px">
            {{ health.status === 'ok' ? '正常' : '降级' }}</div></div>
        <div class="stat info"><div class="label">数据库</div>
          <div class="value" style="font-size:18px">
            {{ health.database === 'sqlite' ? 'SQLite' : 'Postgres' }}</div></div>
        <div class="stat warn"><div class="label">MCP 数据源</div>
          <div class="value" style="font-size:18px">
            {{ health.mcp_configured ? '官方实时' : '内置种子' }}</div></div>
        <div class="stat ok"><div class="label">云端同步</div>
          <div class="value" style="font-size:18px">
            {{ health.cloud_sync_enabled ? '已开启' : '未开启' }}</div></div>
      </div>

      <div class="disclaimer">
        身体数据（体重、身高、TDEE）以加密形式存储于本机数据库，默认<b>不参与任何云端同步</b>，
        分享海报也默认脱敏。项目内所有贴纸图标均为自绘 SVG，不含任何官方素材。
      </div>
    </div>

    <div class="grid cols-2">
      <div class="card">
        <h2 class="card-title">修改密码</h2>
        <div class="field">
          <label>原密码</label>
          <input v-model="oldPwd" type="password" autocomplete="current-password" />
        </div>
        <div class="field">
          <label>新密码</label>
          <input v-model="newPwd" type="password" autocomplete="new-password"
                 placeholder="至少8位，含字母和数字" />
        </div>
        <button class="btn btn-primary" :disabled="!oldPwd || !newPwd" @click="changePwd">
          更新密码
        </button>
      </div>

      <div class="card">
        <h2 class="card-title">近期点餐 <span class="sub">最近 {{ history.length }} 条</span></h2>
        <div v-if="!history.length" class="empty">还没有点餐记录</div>
        <div v-for="o in history.slice(0, 8)" :key="o.id" class="list-item">
          <div>
            <div>{{ o.meals.map((m) => m.name).join(' + ') }}</div>
            <div class="muted" style="font-size:12px">{{ o.date }} · ¥{{ o.total_price }}</div>
          </div>
          <span class="badge" :class="o.status === '达标' ? 'badge-ok'
            : o.status === '维持' ? 'badge-info' : 'badge-warn'">{{ o.status }}</span>
        </div>
      </div>
    </div>

    <div class="card center">
      <button class="btn btn-ghost" @click="logout">退出登录</button>
    </div>
  </div>
</template>