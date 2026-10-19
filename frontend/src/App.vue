<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from './stores/auth'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

const links = [
  { to: '/', label: '今日概览' },
  { to: '/order', label: '点餐控卡' },
  { to: '/checkin', label: '打卡日历' },
  { to: '/profile', label: '身材档案' },
  { to: '/me', label: '我的' },
]
const showNav = computed(() => auth.isLoggedIn)

function logout() {
  auth.logout()
  router.push('/login')
}
</script>

<template>
  <div class="app-shell">
    <header v-if="showNav" class="topbar">
      <div class="brand">
        🍔 麦门控卡
        <small>McFit-Agent</small>
      </div>
      <nav>
        <RouterLink v-for="l in links" :key="l.to" :to="l.to" class="nav-link"
                    :class="{ active: route.path === l.to }">
          {{ l.label }}
        </RouterLink>
      </nav>
      <div class="user-box">
        <span>{{ auth.user?.username }}</span>
        <button class="btn btn-sm btn-ghost" style="margin-left:10px;color:#fff;border-color:rgba(255,255,255,.5)"
                @click="logout">登出</button>
      </div>
    </header>

    <main class="main">
      <RouterView />
    </main>
  </div>
</template>