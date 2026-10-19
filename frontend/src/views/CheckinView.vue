<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api/client'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()

const summary = ref(null)
const sticker = ref(null)
const poster = ref(null)
const stats = ref(null)
const note = ref('')
const msg = ref('')
const err = ref('')
const svg = ref('')

const now = new Date()
const month = ref(`${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`)
const cal = ref(null)

async function loadAll() {
  try {
    const [s, st, c] = await Promise.all([
      api.get('/api/v1/orders/today-summary'),
      api.get('/api/v1/sticker/stats'),
      api.get(`/api/v1/checkin/calendar?month=${month.value}`),
    ])
    summary.value = s
    stats.value = st
    cal.value = c
    if (s.order_count > 0) {
      poster.value = await api.get('/api/v1/sticker/poster')
      svg.value = poster.value.svg
    }
  } catch (e) {
    err.value = e.message
  }
}
onMounted(loadAll)
watch(month, loadAll)

const statusText = computed(() => ({ 达标: '达标', 维持: '维持', 超标: '超出' }[summary.value?.status] || '—'))

async function doCheckin() {
  if (!summary.value?.order_count) {
    err.value = '今天还没有点餐记录，先去点餐控卡页记录一餐'
    return
  }
  err.value = ''; msg.value = ''
  try {
    // 贴纸必须使用「本次真实点单的餐品」，故直接取当日订单记录，
    // 而非打卡快照（首次打卡时快照还不存在）
    const { items: todayOrders } = await api.get('/api/v1/orders')
    const meals = (todayOrders || [])
      .filter((o) => o.is_today)
      .flatMap((o) => o.meals || [])
      .map((m) => ({ name: m.name, category: m.category }))

    if (!meals.length) {
      err.value = '未找到今天的点餐明细，请先去点餐控卡页记录'
      return
    }

    const r = await api.post('/api/v1/checkin', {
      status: summary.value.status,
      total_kcal: summary.value.total_kcal,
      protein_g: summary.value.total_protein_g,
      meals,
      note: note.value || null,
    })
    msg.value = `打卡成功！印章「${r.stamp}」已加盖`
    if (r.items?.length) msg.value += ` · 贴纸已记录：${r.items.join(' + ')}`
    await loadAll()
  } catch (e) {
    err.value = e.message
  }
}

const WEEK = ['一', '二', '三', '四', '五', '六', '日']

/**
 * 日历格里的商品名摘要。
 * 直接拼「板烧鸡腿堡+大杯玉米杯」会断成「...玉米/杯」，观感差。
 * 改为「首字+尾字」压缩：板烧鸡腿堡→板烧堡，大杯玉米杯→大杯杯。
 */
function shortNames(items) {
  const brief = (n) => (n.length <= 4 ? n : n.slice(0, 2) + n.slice(-1))
  const shown = items.slice(0, 2).map(brief).join('+')
  return items.length > 2 ? `${shown}…` : shown
}
const cells = computed(() => {
  if (!cal.value) return []
  const out = []
  for (let i = 0; i < cal.value.first_weekday; i++) out.push(null)
  out.push(...cal.value.cells)
  return out
})

function cellClass(c) {
  if (!c) return 'blank'
  const cls = c.status === '达标' ? 'done' : c.status === '维持' ? 'keep'
    : c.status === '超标' ? 'over' : ''
  const today = new Date().toISOString().slice(0, 10) === c.date
  return [cls, today ? 'today' : ''].join(' ').trim()
}

function downloadSvg() {
  if (!svg.value) return
  const blob = new Blob([svg.value], { type: 'image/svg+xml;charset=utf-8' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = `mcfit-checkin-${month.value}.svg`
  a.click()
  URL.revokeObjectURL(a.href)
}

/** 最近 6 个月（含本月）的 YYYY-MM 列表 */
const months = Array.from({ length: 6 }, (_, i) => {
  const d = new Date()
  d.setMonth(d.getMonth() - i)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
})
</script>

<template>
  <div>
    <div v-if="err" class="alert alert-error">{{ err }}</div>
    <div v-if="msg" class="alert alert-ok">{{ msg }}</div>

    <div class="card">
      <h2 class="card-title">今日概览
        <span class="sub">{{ new Date().toLocaleDateString('zh-CN') }}</span>
      </h2>

      <div v-if="!summary?.order_count" class="empty">
        今天还没有点餐记录。<RouterLink to="/order" style="color:var(--red)">去记录一餐 →</RouterLink>
      </div>

      <template v-else>
        <div class="grid cols-4">
          <div class="stat" :class="summary.status === '超标' ? 'warn' : 'ok'">
            <div class="label">今日摄入</div>
            <div class="value mono">{{ summary.total_kcal }}<span class="unit">kcal</span></div>
          </div>
          <div class="stat info">
            <div class="label">蛋白质</div>
            <div class="value mono">{{ summary.total_protein_g }}<span class="unit">g</span></div>
          </div>
          <div class="stat">
            <div class="label">目标摄入</div>
            <div class="value mono">{{ summary.daily_target ?? '—' }}<span class="unit">kcal</span></div>
          </div>
          <div class="stat ok">
            <div class="label">今日省</div>
            <div class="value mono">¥{{ summary.total_saving.toFixed(2) }}</div>
          </div>
        </div>

        <div v-if="summary.exercise" class="alert mt-16"
             :class="summary.exercise.state === 'over' ? 'alert-warn' : 'alert-info'">
          <b>{{ summary.exercise.headline }}</b>：{{ summary.exercise.message }}
          <!-- 仅在超出目标时才展示运动代偿 -->
          <template v-if="summary.exercise.plans?.length">
            <div v-for="p in summary.exercise.plans" :key="p.code" class="muted mt-8"
                 style="font-size:12px">{{ p.text }} ≈ {{ p.kcal }} kcal</div>
          </template>
        </div>

        <div class="actions mt-16">
          <input v-model="note" type="text" placeholder="今日心情备注（选填）" style="flex:1;min-width:180px" />
          <button class="btn btn-primary" @click="doCheckin">完成今日打卡</button>
          <button v-if="svg" class="btn btn-ghost" @click="downloadSvg">下载贴纸</button>
        </div>
      </template>
    </div>

    <div v-if="stats?.total_days" class="card">
      <h2 class="card-title">坚持记录</h2>
      <div class="grid cols-4">
        <div class="stat"><div class="label">累计打卡</div>
          <div class="value mono">{{ stats.total_days }}<span class="unit">天</span></div></div>
        <div class="stat ok"><div class="label">当前连续</div>
          <div class="value mono">{{ stats.streak }}<span class="unit">天</span></div></div>
        <div class="stat info"><div class="label">最长连续</div>
          <div class="value mono">{{ stats.best_streak }}<span class="unit">天</span></div></div>
        <div class="stat warn"><div class="label">达标率</div>
          <div class="value mono">{{ stats.done_ratio }}<span class="unit">%</span></div></div>
      </div>
    </div>

    <div class="card">
      <h2 class="card-title">打卡日历
        <span class="sub">
          <select v-model="month" style="padding:4px 8px;font-size:12px;width:auto">
            <option v-for="m in months" :key="m" :value="m">{{ m }}</option>
          </select>
        </span>
      </h2>

      <div class="calendar">
        <div v-for="w in WEEK" :key="w" class="cal-head">{{ w }}</div>
        <div v-for="(c, i) in cells" :key="i" class="cal-cell" :class="cellClass(c)"
             :title="c?.items?.length ? c.items.join(' + ') : ''">
          <template v-if="c">
            <span class="day">{{ c.day }}</span>
            <!-- 展示本次点单的真实商品名，而非类别 -->
            <span v-if="c.items?.length" class="items">
              {{ shortNames(c.items) }}
            </span>
            <span v-if="c.kcal" class="kcal">{{ c.kcal }}</span>
          </template>
        </div>
      </div>

      <div class="actions mt-16">
        <span class="badge badge-ok">达标 {{ cal?.summary.done ?? 0 }}</span>
        <span class="badge badge-info">维持 {{ cal?.summary.keep ?? 0 }}</span>
        <span class="badge badge-warn">超出 {{ cal?.summary.over ?? 0 }}</span>
        <span class="badge badge-muted">日均 {{ cal?.summary.avg_kcal ?? 0 }} kcal</span>
      </div>
    </div>

    <div v-if="svg" class="card">
      <h2 class="card-title">我的食物贴纸 <span class="sub">自绘 SVG · 项目原创素材</span></h2>
      <div class="grid cols-2">
        <div class="sticker-box" v-html="svg"></div>
        <div>
          <div v-if="poster" class="list-item"><span>印章</span><b>{{ poster.stamp }}</b></div>
          <div v-if="poster" class="list-item"><span>状态</span>
            <span class="badge" :class="poster.status === '达标' ? 'badge-ok'
              : poster.status === '维持' ? 'badge-info' : 'badge-warn'">{{ poster.status }}</span></div>
          <div class="list-item"><span>文案</span><span class="muted">{{ poster?.slogan }}</span></div>
          <div class="disclaimer">{{ poster?.watermark }}</div>
        </div>
      </div>
    </div>
  </div>
</template>