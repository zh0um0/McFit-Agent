<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { api } from '../api/client'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const opts = ref({ activity_levels: [], goals: [], genders: [], meals: [] })
const msg = ref('')
const err = ref('')
const saving = ref(false)

// 新手引导：路由守卫把无档案用户送到这里，带from 记录原目标页
const onboarding = computed(() => !!route.query.from || !auth.hasProfile)
const redirectTo = computed(() => route.query.from || '/')

const form = reactive({
  gender: 'male', age: 30, height_cm: 175, weight_kg: 70,
  activity_level: 'sedentary', goal: 'cut',
})

async function loadOptions() {
  try {
    // 必须走 api 客户端：demo 模式下请求被导流到本地拦截器；
    // 此前用裸 fetch 在 GitHub Pages 上 404，导致下拉框无选项
    opts.value = await api.get('/api/v1/profile/options')
  } catch { /* 保留空默认值 */ }
}
loadOptions()

watch(() => auth.profile, (p) => {
  if (!p) return
  form.gender = p.gender
  form.age = p.age
  form.height_cm = p.height_cm
  if (p.weight_kg) form.weight_kg = p.weight_kg
  form.activity_level = p.activity_level
  form.goal = p.goal
}, { immediate: true })

async function save() {
  saving.value = true; msg.value = ''; err.value = ''
  try {
    await auth.saveProfile({ ...form, age: Number(form.age),
                            height_cm: Number(form.height_cm),
                            weight_kg: Number(form.weight_kg) })
    msg.value = '档案已保存，热量目标已重新计算'
    // 新手引导：保存后回到用户原本想去的页面
    if (onboarding.value) {
      setTimeout(() => router.replace(redirectTo.value), 700)
    }
  } catch (e) {
    err.value = e.message
  } finally {
    saving.value = false
  }
}

const m = computed(() => auth.metrics)
const ratio = computed(() => {
  if (!m.value?.daily_target) return 0
  return Math.min((m.value.tdee / m.value.daily_target) * 100, 100)
})

/** 四张指标卡：数值 + 一句话白话说明，降低专业术语门槛 */
const metricsCards = computed(() => {
  const v = m.value
  if (!v) return []
  return [
    {
      label: '基础代谢 BMR', value: v.bmr, unit: 'kcal', cls: 'info',
      note: '躺着不动，身体维持心跳呼吸的最低消耗',
    },
    {
      label: '每日消耗 TDEE', value: v.tdee, unit: 'kcal', cls: '',
      note: 'BMR 加上日常活动和运动的总消耗',
    },
    {
      label: '今日目标摄入', value: v.daily_target, unit: 'kcal', cls: 'ok',
      note: v.goal_label === '减脂'
        ? '按减脂目标下调后的每日摄入上限'
        : v.goal_label === '维持' ? '维持体重所需的每日摄入' : '增肌目标的每日摄入量',
    },
    {
      label: '蛋白质目标', value: `${v.protein_min_g}–${v.protein_max_g}`, unit: 'g', cls: 'warn',
      note: '每公斤体重的摄入区间，减脂期高蛋白保肌',
    },
  ]
})
</script>

<template>
  <div>
    <div v-if="onboarding" class="card" style="border-color:var(--red);border-width:2px">
      <h2 class="card-title">👋 先完善身材档案</h2>
      <div class="muted">
        填入性别、年龄、身高、体重后，系统会用 <b>Mifflin-St Jeor 公式</b>算出你的
        每日热量目标与蛋白质区间 —— 这是后续控卡与运动换算的基础。
        <br />所有数据加密存储于本机，不参与分享导出。
      </div>
    </div>

    <div class="card">
      <h2 class="card-title">
        身材档案
        <span class="sub">{{ onboarding ? '' : '数据加密存储于本机，不参与分享导出' }}</span>
      </h2>

      <div v-if="err" class="alert alert-error">{{ err }}</div>
      <div v-if="msg" class="alert alert-ok">{{ msg }}</div>

      <div class="row">
        <div class="field">
          <label>性别</label>
          <select v-model="form.gender">
            <option v-for="g in opts.genders" :key="g.value" :value="g.value">{{ g.label }}</option>
          </select>
        </div>
        <div class="field">
          <label>年龄</label>
          <input v-model.number="form.age" type="number" min="1" max="120" />
        </div>
        <div class="field">
          <label>身高 (cm)</label>
          <input v-model.number="form.height_cm" type="number" min="50" max="250" step="0.5" />
        </div>
        <div class="field">
          <label>体重 (kg)</label>
          <input v-model.number="form.weight_kg" type="number" min="20" max="400" step="0.1" />
        </div>
      </div>

      <div class="row">
        <div class="field">
          <label>活动强度</label>
          <select v-model="form.activity_level">
            <option v-for="a in opts.activity_levels" :key="a.value" :value="a.value">
              {{ a.label }}（系数 {{ a.factor }}）
            </option>
          </select>
        </div>
        <div class="field">
          <label>目标</label>
          <select v-model="form.goal">
            <option v-for="g in opts.goals" :key="g.value" :value="g.value">{{ g.label }}</option>
          </select>
        </div>
      </div>

      <button class="btn btn-primary" :disabled="saving" @click="save">
        <span v-if="saving" class="spinner"></span>{{ saving ? '保存中' : '保存并计算目标' }}
      </button>
    </div>

    <div v-if="m" class="card">
      <h2 class="card-title">我的热量目标 <span class="sub">Mifflin-St Jeor · 权威公式</span></h2>
      <div class="grid cols-4">
        <div v-for="s in metricsCards" :key="s.label" class="stat" :class="s.cls">
          <div class="label">{{ s.label }}</div>
          <div class="value mono">{{ s.value }}<span class="unit">{{ s.unit }}</span></div>
          <div class="stat-note">{{ s.note }}</div>
        </div>
      </div>

      <div class="mt-16">
        <div class="muted">单餐热量上限分配（{{ m.activity_label }} · {{ m.goal_label }}）</div>
        <div class="grid cols-3 mt-8">
          <div v-for="(v, k) in m.meal_limit" :key="k" class="stat">
            <div class="label">{{ k }}</div>
            <div class="value mono">{{ v }}<span class="unit">kcal</span></div>
          </div>
        </div>
      </div>

      <div class="progress-bar" title="每日目标摄入占每日总消耗的比例">
        <div class="progress-fill s-keep" :style="{ width: ratio + '%' }"></div>
      </div>
      <div class="muted mt-8">
        每日目标摄入约为每日总消耗的 {{ m.daily_target / m.tdee * 100 | 0 }}%
        （减脂期通常为 80%~90%，低于 80% 属过度节食，不建议长期维持）
      </div>

      <div class="disclaimer">
        以上为公式估算值，仅供参考，不构成医疗或营养专业建议。如有健康问题请咨询专业人士。
      </div>
    </div>

    <div v-else class="card">
      <div class="empty">
        还没有档案数据。填写上方表单并保存，系统会用 Mifflin-St Jeor 公式算出你的每日热量目标。
      </div>
    </div>
  </div>
</template>