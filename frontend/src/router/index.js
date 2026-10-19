import { createRouter, createWebHashHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const routes = [
  { path: '/login', component: () => import('../views/LoginView.vue'), meta: { public: true } },
  { path: '/', component: () => import('../views/DashboardView.vue') },
  { path: '/profile', component: () => import('../views/ProfileView.vue'), meta: { onboarding: true } },
  { path: '/order', component: () => import('../views/OrderView.vue') },
  { path: '/checkin', component: () => import('../views/CheckinView.vue') },
  { path: '/me', component: () => import('../views/MeView.vue') },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

export const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  await auth.bootstrap()

  // 未登录：除公开页外一律打回登录页
  if (!to.meta.public && !auth.isLoggedIn) return '/login'
  if (to.path === '/login' && auth.isLoggedIn) return '/'

  // 已登录但未建档：强制进入档案页（档案页自身豁免，避免死循环）
  // onBoarding 标记让档案页知道是新手引导，保存后可自动跳回原目标页
  if (auth.isLoggedIn && !auth.hasProfile && !to.meta.onboarding) {
    return { path: '/profile', query: { from: to.fullPath } }
  }
  return true
})