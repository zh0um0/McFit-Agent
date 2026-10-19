/**
 * Demo 模式路由器 —— 无后端时的本地内存实现。
 * request() 在 VITE_DEMO=1 构建下把所有请求导流到这里；
 * 数据存 localStorage，刷新页面不丢（每个浏览器独立，不构成账号体系）。
 */
import mealsData from './demo_meals.json'
import couponsData from './demo_coupons.json'
import optionsData from './demo_options.json'
import { computeMetrics, narrate, suggestionForGap, recommend } from './algo'
import { buildStickerSvg } from './sticker'

const K = {
  user: 'mcfit_demo_user',
  profile: 'mcfit_demo_profile',
  orders: 'mcfit_demo_orders',
  checkins: 'mcfit_demo_checkins',
}

const load = (k, fallback) => {
  try { return JSON.parse(localStorage.getItem(k)) ?? fallback } catch { return fallback }
}
const save = (k, v) => localStorage.setItem(k, JSON.stringify(v))
const today = () => new Date().toISOString().slice(0, 10)

const COUPONS = couponsData.items.map((c) => ({
  ...c,
  applies_to: c.code === 'SEED-BEVERAGE' ? ['饮料', '咖啡'] : [],
}))

const MEALS = mealsData.items
const DISCLAIMER = mealsData.disclaimer || '演示数据（种子菜单），实时数据以麦当劳官方渠道为准。'

function getUser() {
  let u = load(K.user, null)
  if (!u) {
    u = { id: 1, username: 'demo_guest', email: null, role: 'user', provider: 'local', created_at: new Date().toISOString(), last_login_at: null }
    save(K.user, u)
  }
  return u
}

const tokens = () => ({ access_token: 'demo-token', refresh_token: 'demo-token' })

function mealLimitsOf(profile) {
  return profile?.metrics?.meal_limit || null
}

function weightOf(profile) {
  return profile?.weight_kg || 70
}

export async function demoRequest(path, { method = 'GET', body } = {}) {
  const user = getUser()
  const profile = load(K.profile, null)
  const orders = load(K.orders, [])
  const checkins = load(K.checkins, [])

  // ---------- health ----------
  if (path === '/health') {
    return { status: 'ok', app: 'McFit-Agent', version: '0.1.0-demo', database: 'demo-local', database_ok: true, mcp_configured: false, mcp_mode: 'seed', cloud_sync_enabled: false }
  }

  // ---------- auth ----------
  if (path === '/api/v1/auth/register' || path === '/api/v1/auth/login') {
    const name = body?.username ? String(body.username).slice(0, 20) : 'demo_guest'
    user.username = `${name}·演示`
    save(K.user, user)
    return { ...tokens(), user }
  }
  if (path === '/api/v1/auth/refresh') return tokens()
  if (path === '/api/v1/auth/change-password') return { ok: true, message: '演示模式：密码修改不会真正生效' }
  if (path === '/api/v1/auth/me') return user

  // ---------- profile ----------
  if (path === '/api/v1/profile/options') return optionsData
  if (path === '/api/v1/profile' && method === 'GET') {
    if (!profile) throw new Error('尚未建立身材档案')
    return profile
  }
  if (path === '/api/v1/profile' && method === 'PUT') {
    const metrics = computeMetrics(body)
    const out = { ...body, cloud_sync_enabled: false, metrics }
    save(K.profile, out)
    return out
  }
  if (path === '/api/v1/profile' && method === 'DELETE') {
    localStorage.removeItem(K.profile)
    return { ok: true, message: '档案已删除' }
  }

  // ---------- meals ----------
  if (path === '/api/v1/meals') {
    const categories = [...new Set(MEALS.map((m) => m.category))]
    return { items: MEALS, categories, source: 'seed', disclaimer: DISCLAIMER }
  }
  if (path === '/api/v1/meals/calculate') {
    const codes = body?.codes || []
    const selection = codes.map((c) => MEALS.find((m) => m.code === c)).filter(Boolean)
    if (!selection.length) throw new Error('所选编码不存在，请刷新菜单')
    return recommend(selection, MEALS, COUPONS)
  }

  // ---------- coupons ----------
  if (path === '/api/v1/coupons') {
    return { items: couponsData.items, mode: 'seed', disclaimer: couponsData.disclaimer }
  }

  // ---------- orders ----------
  const orderMealName = body?.meal_name || '午餐'
  if (path === '/api/v1/orders' && method === 'POST') {
    const codes = body?.codes || []
    const meals = codes.map((c) => MEALS.find((m) => m.code === c)).filter(Boolean)
    if (!meals.length) throw new Error('所选编码不存在，请刷新菜单')
    const limits = mealLimitsOf(profile)
    const limit = limits ? limits[orderMealName] || limits['午餐'] : 700
    const totalKcal = Math.round(meals.reduce((a, m) => a + m.kcal, 0))
    const totalProtein = Math.round(meals.reduce((a, m) => a + m.protein_g, 0) * 10) / 10
    const subtotal = meals.reduce((a, m) => a + m.price, 0)
    const eq = narrate(totalKcal, limit, weightOf(profile))
    const rec = {
      id: (orders[0]?.id || 0) + 1,
      date: today(),
      is_today: true,
      meal_name: orderMealName,
      meals,
      total_kcal: totalKcal,
      total_protein_g: totalProtein,
      total_price: Math.round(subtotal * 100) / 100,
      saving_amount: 0,
      coupon_code: null,
      status: eq.status,
      exercise_equivalent: eq,
    }
    orders.unshift(rec)
    save(K.orders, orders)
    return { id: rec.id, status: rec.status, total_kcal: totalKcal, total_protein_g: totalProtein, final_price: rec.total_price, exercise_equivalent: eq }
  }
  if (path === '/api/v1/orders/today-summary') {
    const t = today()
    const todays = orders.filter((o) => o.date === t)
    const totalKcal = todays.reduce((a, o) => a + o.total_kcal, 0)
    const dailyTarget = profile?.metrics?.daily_target || null
    let status = null
    let exercise = null
    if (dailyTarget && todays.length) {
      const gap = Math.round(dailyTarget - totalKcal)
      status = totalKcal <= dailyTarget * 0.95 ? '达标' : totalKcal <= dailyTarget * 1.1 ? '维持' : '超标'
      exercise = suggestionForGap(dailyTarget - totalKcal, weightOf(profile))
      exercise.gap_kcal = Math.abs(gap)
    }
    return {
      date: t, order_count: todays.length,
      total_kcal: totalKcal,
      total_protein_g: Math.round(todays.reduce((a, o) => a + o.total_protein_g, 0) * 10) / 10,
      total_price: Math.round(todays.reduce((a, o) => a + o.total_price, 0) * 100) / 100,
      total_saving: 0,
      has_profile: !!profile,
      daily_target: dailyTarget ? Math.round(dailyTarget) : null,
      protein_target: profile ? [Math.round(profile.metrics.protein_min_g), Math.round(profile.metrics.protein_max_g)] : null,
      status, gap_kcal: dailyTarget ? Math.round(dailyTarget - totalKcal) : null,
      exercise,
    }
  }
  if (path === '/api/v1/orders' && method === 'GET') {
    return { items: orders }
  }
  const delOrder = path.match(/^\/api\/v1\/orders\/(\d+)$/)
  if (delOrder) {
    save(K.orders, orders.filter((o) => o.id !== Number(delOrder[1])))
    return { ok: true }
  }

  // ---------- checkin ----------
  if (path === '/api/v1/checkin' && method === 'POST') {
    const t = today()
    const todaysOrders = orders.filter((o) => o.date === t)
    const totalKcal = todaysOrders.reduce((a, o) => a + o.total_kcal, 0)
    const status = body?.status || '维持'
    const stamp = status === '达标' ? '麦门减脂自律先锋印' : status === '超标' ? '麦门弹性平衡章' : '麦门稳稳节奏章'
    const rec = { id: (checkins[0]?.id || 0) + 1, date: t, status, stamp, kcal: totalKcal, note: body?.note || '' }
    const idx = checkins.findIndex((c) => c.date === t)
    if (idx >= 0) checkins[idx] = rec
    else checkins.unshift(rec)
    save(K.checkins, checkins)
    return { id: rec.id, date: t, status, stamp, sticker_length: 0, items: todaysOrders.flatMap((o) => o.meals.map((m) => m.name)), overflow: 0 }
  }
  if (path.startsWith('/api/v1/checkin/calendar')) {
    const month = new URLSearchParams(path.split('?')[1] || '').get('month') || today().slice(0, 7)
    const [y, m] = month.split('-').map(Number)
    const days = new Date(y, m, 0).getDate()
    const firstWeekday = new Date(y, m - 1, 1).getDay() === 0 ? 6 : new Date(y, m - 1, 1).getDay() - 1 // 周一=0 口径
    const cells = []
    for (let d = 1; d <= days; d++) {
      const date = `${month}-${String(d).padStart(2, '0')}`
      const c = checkins.find((x) => x.date === date)
      const dayOrders = orders.filter((o) => o.date === date)
      cells.push({
        day: d, date,
        status: c?.status || null,
        kcal: c?.kcal ?? (dayOrders.length ? dayOrders.reduce((a, o) => a + o.total_kcal, 0) : null),
        has_sticker: !!c,
        items: dayOrders.flatMap((o) => o.meals.map((mm) => mm.name)),
      })
    }
    const checked = cells.filter((c) => c.status).length
    const summary = {
      checked_days: checked,
      done: cells.filter((c) => c.status === '达标').length,
      keep: cells.filter((c) => c.status === '维持').length,
      over: cells.filter((c) => c.status === '超标').length,
      avg_kcal: checked ? Math.round(cells.reduce((a, c) => a + (c.kcal || 0), 0) / checked) : 0,
    }
    return { month, days, first_weekday: firstWeekday, cells, summary }
  }

  // ---------- sticker ----------
  if (path === '/api/v1/sticker/poster') {
    const t = today()
    const c = checkins.find((x) => x.date === t)
    if (!c) throw new Error('今日尚未打卡')
    const todaysOrders = orders.filter((o) => o.date === t)
    const meals = todaysOrders.flatMap((o) => o.meals)
    const totalKcal = meals.reduce((a, m) => a + m.kcal, 0)
    const limit = mealLimitsOf(profile)?.['午餐'] || 700
    const svg = buildStickerSvg(t, c.status, meals, totalKcal)
    return {
      date: t, status: c.status, stamp: c.stamp,
      total_kcal: Math.round(totalKcal), protein_g: Math.round(meals.reduce((a, m) => a + m.protein_g, 0) * 10) / 10,
      items: meals.map((m) => ({ name: m.name, category: m.category, kcal: m.kcal })),
      exercise_equivalent: narrate(totalKcal, limit, weightOf(profile)),
      slogan: c.status === '超标' ? '小波动不影响大局，继续保持节奏 💪' : c.status === '维持' ? '稳稳的一天，节奏还在你手里 🌟' : '自律达标，今天也是了不起的一天 🎉',
      watermark: '本图不含身体原始数据 · 数据仅供参考，非医疗建议',
      svg,
    }
  }
  if (path === '/api/v1/sticker/stats') {
    const dates = [...new Set(checkins.map((c) => c.date))].sort()
    if (!dates.length) {
      return { total_days: 0, streak: 0, best_streak: 0, done_ratio: 0, latest_date: null }
    }
    let streak = 0
    const dayMs = 86400000
    const t0 = new Date(today()).getTime()
    if (dates.includes(today())) {
      streak = 1
      for (let i = dates.length - 1; i > 0; i--) {
        if (new Date(dates[i]).getTime() - new Date(dates[i - 1]).getTime() === dayMs) streak++
        else break
      }
    }
    let best = 0, cur = 0
    for (let i = 0; i < dates.length; i++) {
      if (i === 0 || new Date(dates[i]).getTime() - new Date(dates[i - 1]).getTime() === dayMs) cur++
      else cur = 1
      best = Math.max(best, cur)
    }
    const doneDays = checkins.filter((c) => c.status === '达标').length
    return {
      total_days: dates.length, streak, best_streak: best,
      done_ratio: Math.round((doneDays / dates.length) * 100),
      latest_date: dates[dates.length - 1],
    }
  }

  throw new Error(`演示模式暂不支持该操作：${method} ${path}`)
}
