<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api/client'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()
const s = ref(null)
const loading = ref(true)
const err = ref('')

onMounted(async () => {
  try {
    s.value = await api.get('/api/v1/orders/today-summary')
  } catch (e) {
    err.value = e.message
  } finally {
    loading.value = false
  }
})

const pct = computed(() => {
  if (!s.value?.daily_target) return 0
  return Math.min((s.value.total_kcal / s.value.daily_target) * 100, 100)
})
const left = computed(() => (s.value?.gap_kcal ?? 0) > 0)
const statusCls = computed(() => ({
  达标: 'badge-ok', 维持: 'badge-info', 超标: 'badge-warn',
}[s.value?.status] || 'badge-muted'))

/* 进度条三态配色，与徽章语义一致 */
const fillCls = computed(() => ({
  达标: 's-ok', 维持: 's-keep', 超标: 's-over',
}[s.value?.status] || 's-ok'))
</script>

<template>
  <div>
    <div v-if="loading" class="card"><span class="spinner dark"></span></div>
    <div v-else-if="err" class="alert alert-error">{{ err }}</div>

    <template v-else>
      <div class="card">
        <h2 class="card-title">今天吃得怎么样
          <span class="sub">{{ new Date().toLocaleDateString('zh-CN', { month: 'long', day: 'numeric', weekday: 'long' }) }}</span>
        </h2>

        <div v-if="!auth.hasProfile" class="alert alert-warn">
          还没有身材档案，暂无法计算热量目标。
          <RouterLink to="/profile" style="color:var(--red);font-weight:700">立即填写 →</RouterLink>
        </div>

        <div v-if="!s?.order_count" class="empty">
          今天还没有记录。<RouterLink to="/order" style="color:var(--red)">去点餐控卡 →</RouterLink>
        </div>

        <template v-else>
          <div class="grid cols-4">
            <div class="stat" :class="s.status === '超标' ? 'warn' : 'ok'">
              <div class="label">今日摄入</div>
              <div class="value mono">{{ s.total_kcal }}<span class="unit">kcal</span></div>
            </div>
            <div class="stat info">
              <div class="label">蛋白质</div>
              <div class="value mono">{{ s.total_protein_g }}<span class="unit">g</span></div>
            </div>
            <div class="stat">
              <div class="label">今日目标</div>
              <div class="value mono">{{ s.daily_target ?? '—' }}<span class="unit">kcal</span></div>
            </div>
            <div class="stat ok">
              <div class="label">累计省</div>
              <div class="value mono">¥{{ s.total_saving.toFixed(2) }}</div>
            </div>
          </div>

          <div class="progress-bar">
            <div class="progress-fill" :class="fillCls" :style="{ width: pct + '%' }"></div>
          </div>
          <div class="muted mt-8">
            状态 <span class="badge" :class="statusCls">{{ s.status }}</span>
            · {{ left ? `还可以吃 ${s.gap_kcal} kcal` : `超出 ${Math.abs(s.gap_kcal)} kcal` }}
          </div>

          <div v-if="s.exercise" class="alert mt-16"
               :class="s.exercise.state === 'over' ? 'alert-warn' : 'alert-info'">
            <b>{{ s.exercise.headline }}</b>：{{ s.exercise.message }}
            <!-- 仅在超出目标时才展示运动代偿（未吃满无需运动找补） -->
            <template v-if="s.exercise.plans?.length">
              <div v-for="p in s.exercise.plans" :key="p.code" class="muted mt-8" style="font-size:12px">
                {{ p.text }} ≈ {{ p.kcal }} kcal
              </div>
            </template>
          </div>
        </template>
      </div>

      <div class="card center">
        <RouterLink to="/order"><button class="btn btn-primary">开始点餐控卡</button></RouterLink>
        <RouterLink to="/checkin"><button class="btn btn-ghost">查看打卡日历</button></RouterLink>
      </div>
    </template>
  </div>
</template>