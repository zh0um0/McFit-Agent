<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useOrderStore } from '../stores/order'
import { api } from '../api/client'

const auth = useAuthStore()
const order = useOrderStore()
const router = useRouter()

const msg = ref('')
const err = ref('')
const saving = ref(false)

onMounted(async () => {
  if (!auth.hasProfile) {
    err.value = '请先完善身材档案，才能计算单餐热量上限'
  }
  await order.loadMeals()
  await order.loadCoupons()
})

const metrics = computed(() => auth.metrics)
const lunchLimit = computed(() => metrics.value?.meal_limit?.['午餐'] || 0)
const kcalPct = computed(() =>
  lunchLimit.value ? Math.min((order.totalKcal / lunchLimit.value) * 100, 100) : 0)

const status = computed(() => {
  if (!lunchLimit.value || !order.totalKcal) return null
  const r = order.totalKcal / lunchLimit.value
  if (r <= 0.95) return { text: '达标', cls: 'badge-ok', fill: 's-ok' }
  if (r <= 1.10) return { text: '维持', cls: 'badge-info', fill: 's-keep' }
  return { text: '超标', cls: 'badge-warn', fill: 's-over' }
})

const fillCls = computed(() => status.value?.fill || 's-ok')

async function saveOrder() {
  if (!order.selected.length) return
  saving.value = true; msg.value = ''; err.value = ''
  try {
    const r = await api.post('/api/v1/orders', { codes: order.selected, meal_name: '午餐' })
    msg.value = `已记录本餐 ${r.total_kcal} kcal · 蛋白 ${r.total_protein_g}g · 状态「${r.status}」`
    if (r.exercise_equivalent) {
      msg.value += '\n' + r.exercise_equivalent.message
    }
    setTimeout(() => router.push('/checkin'), 1600)
  } catch (e) {
    err.value = e.message
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div>
    <div v-if="err" class="alert alert-error">{{ err }}</div>
    <div v-if="msg" class="alert alert-ok">{{ msg }}</div>

    <div class="card">
      <h2 class="card-title">
        本餐热量仪表盘
        <span class="sub" v-if="lunchLimit">单餐上限 {{ lunchLimit }} kcal</span>
        <span class="badge badge-muted" v-else>未设档案</span>
      </h2>

      <div class="grid cols-4">
        <div class="stat" :class="status ? '' : 'info'">
          <div class="label">总热量</div>
          <div class="value mono">{{ order.totalKcal }}<span class="unit">kcal</span></div>
        </div>
        <div class="stat info">
          <div class="label">蛋白质</div>
          <div class="value mono">{{ order.totalProtein.toFixed(1) }}<span class="unit">g</span></div>
        </div>
        <div class="stat warn">
          <div class="label">原价合计</div>
          <div class="value mono">¥{{ order.totalPrice.toFixed(2) }}</div>
        </div>
        <div class="stat ok">
          <div class="label">最优实付</div>
          <div class="value mono">
            ¥{{ (order.calc?.final_price ?? order.totalPrice).toFixed(2) }}
            <span v-if="order.calc?.extra_saving > 0" class="unit" style="color:var(--ok)">
              省¥{{ order.calc.extra_saving.toFixed(2) }}
            </span>
          </div>
        </div>
      </div>

      <div class="progress-bar">
        <div class="progress-fill" :class="fillCls" :style="{ width: kcalPct + '%' }"></div>
      </div>
      <div class="muted mt-8">
        <span v-if="status">当前状态：<b :class="status.cls" style="padding:2px 8px;border-radius:99px"
          >{{ status.text }}</b> · 已用 {{ kcalPct | 0 }}% 单餐预算</span>
        <span v-else>勾选单品后实时累加热量与差额</span>
      </div>
    </div>

    <div class="grid cols-2">
      <div class="card">
        <h2 class="card-title">
          菜单勾选
          <span class="sub">
            数据源
            <span class="badge" :class="order.source === 'mcp' ? 'badge-ok' : 'badge-muted'">
              {{ order.source === 'mcp' ? '官方MCP实时' : '内置种子' }}
            </span>
          </span>
        </h2>

        <div class="actions mb-8">
          <select v-model="order.category" style="max-width:130px">
            <option value="">全部分类</option>
            <option v-for="c in order.categories" :key="c" :value="c">{{ c }}</option>
          </select>
          <input v-model.trim="order.keyword" type="text" placeholder="搜单品名" style="max-width:150px" />
          <button class="btn btn-sm btn-ghost" :class="{ active: order.highProteinOnly }"
                  @click="order.highProteinOnly = !order.highProteinOnly">
            高蛋白
          </button>
          <button class="btn btn-sm btn-ghost" @click="order.excludeFried = !order.excludeFried">
            {{ order.excludeFried ? '✓ ' : '' }}排除油炸
          </button>
        </div>

        <div v-if="order.loading" class="empty"><span class="spinner dark"></span></div>
        <div v-else-if="!order.filtered.length" class="empty">没有符合条件的单品</div>

        <div v-for="(items, cat) in order.byCategory" :key="cat" class="mb-8">
          <div class="muted mb-8" style="font-weight:700">{{ cat }}</div>
          <div class="meal-grid">
            <div v-for="m in items" :key="m.code" class="meal-card"
                 :class="{ active: order.selected.includes(m.code) }"
                 @click="order.toggle(m.code)">
              <div class="tick">✓</div>
              <div class="name">{{ m.name }}</div>
              <div class="tags">
                <span v-if="m.is_high_protein" class="badge badge-ok">高蛋白</span>
                <span v-if="m.is_fried" class="badge badge-warn">油炸</span>
              </div>
              <div class="nums">
                <span>{{ m.kcal }} kcal</span>
                <span>¥{{ m.price }}</span>
              </div>
              <div class="nums"><span>蛋白 {{ m.protein_g }}g</span></div>
            </div>
          </div>
        </div>

        <div class="disclaimer">{{ order.disclaimer }}</div>
      </div>

      <div>
        <div class="card">
          <h2 class="card-title">已选方案 <span class="sub">{{ order.selected.length }} 件</span></h2>
          <div v-if="!order.selectedMeals.length" class="empty">
            还没有选择。左侧点击餐品卡片即可加入本餐。
          </div>
          <div v-for="m in order.selectedMeals" :key="m.code" class="list-item">
            <span>{{ m.name }}</span>
            <span class="mono muted">{{ m.kcal }} kcal · ¥{{ m.price }}</span>
          </div>
          <div class="actions mt-16">
            <button class="btn btn-primary" :disabled="!order.selected.length || saving"
                    @click="order.calculate()">
              <span v-if="saving" class="spinner"></span>试算凑单最优
            </button>
            <button class="btn btn-ghost" :disabled="!order.selected.length"
                    @click="order.clear()">清空</button>
            <button class="btn btn-yellow" :disabled="!order.selected.length || saving"
                    @click="saveOrder">保存这一餐</button>
          </div>
        </div>

        <div v-if="order.calc" class="card">
          <h2 class="card-title">省钱凑单方案</h2>

          <div class="list-item">
            <span>当前方案原价</span>
            <span class="mono">¥{{ order.calc.baseline.final_price.toFixed(2) }}</span>
          </div>
          <div class="list-item">
            <span>推荐方案实付</span>
            <span class="mono" style="color:var(--ok);font-weight:700">
              ¥{{ order.calc.final_price.toFixed(2) }}
            </span>
          </div>
          <div class="list-item">
            <span>合计热量</span>
            <span class="mono">{{ order.calc.total_kcal }} kcal</span>
          </div>

          <div class="alert alert-ok mt-16">{{ order.calc.recommend_text }}</div>

          <div class="mt-8">
            <div class="muted mb-8" style="font-weight:700">推荐组合</div>
            <div v-for="m in order.calc.meals" :key="m.code" class="list-item">
              <span>{{ m.name }}</span>
              <span class="mono muted">{{ m.kcal }} kcal</span>
            </div>
          </div>

          <div v-if="order.calc.coupon_code" class="mt-8 muted">
            已用卡券：{{ order.calc.coupon_title }}（{{ order.calc.coupon_code }}）
          </div>

          <button class="btn btn-primary btn-block mt-16"
                  @click="order.applyRecommendation()">采用推荐组合</button>
        </div>

        <div class="card">
          <h2 class="card-title">我的卡券
            <span class="sub">
              <span class="badge" :class="order.coupons[0]?.source === 'mcp' ? 'badge-ok' : 'badge-muted'">
                {{ order.coupons[0]?.source === 'mcp' ? '官方卡包' : '示例券' }}
              </span>
            </span>
          </h2>
          <div v-if="!order.coupons.length" class="empty">暂无卡券</div>
          <div v-for="c in order.coupons" :key="c.code" class="list-item">
            <span>{{ c.title }}</span>
            <span class="mono muted">满{{ c.threshold }}减{{ c.discount }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>