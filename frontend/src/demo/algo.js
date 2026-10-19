/**
 * Demo 模式算法层 —— 从 backend/app/services/{tdee,exercise,pricing}.py 移植。
 * 与后端保持同一公式口径，保证线上演示与本地完整版行为一致。
 */

// ---------- TDEE（Mifflin-St Jeor） ----------
export const ACTIVITY_FACTORS = {
  sedentary: { label: '久坐（几乎不运动）', factor: 1.2 },
  light: { label: '轻度（每周1-3次）', factor: 1.375 },
  moderate: { label: '中度（每周3-5次）', factor: 1.55 },
  active: { label: '高强（每周6-7次）', factor: 1.725 },
}
export const GOALS = {
  cut: { label: '减脂', factor: 0.82 },
  keep: { label: '维持', factor: 1.0 },
  lean_bulk: { label: '增肌（lean bulk）', factor: 1.1 },
}
export const MEAL_RATIO = { 早餐: 0.2, 午餐: 0.4, 晚餐: 0.4 }
export const PROTEIN_PER_KG = { cut: [1.6, 2.0], keep: [1.2, 1.6], lean_bulk: [1.6, 2.2] }

export function computeMetrics(p) {
  const base = 10 * p.weight_kg + 6.25 * p.height_cm - 5 * p.age
  const bmr = p.gender === 'male' ? base + 5 : base - 161
  const act = ACTIVITY_FACTORS[p.activity_level] || ACTIVITY_FACTORS.light
  const goal = GOALS[p.goal] || GOALS.cut
  const tdee = bmr * act.factor
  const dailyTarget = tdee * goal.factor
  const [pMin, pMax] = PROTEIN_PER_KG[p.goal] || PROTEIN_PER_KG.cut
  const mealLimit = {}
  for (const [meal, ratio] of Object.entries(MEAL_RATIO)) {
    mealLimit[meal] = round1(dailyTarget * ratio)
  }
  return {
    bmr: round1(bmr),
    tdee: round1(tdee),
    daily_target: round1(dailyTarget),
    protein_min_g: round1(pMin * p.weight_kg),
    protein_max_g: round1(pMax * p.weight_kg),
    meal_limit: mealLimit,
    activity_label: act.label,
    goal_label: goal.label,
  }
}

const round1 = (n) => Math.round(n * 10) / 10

// ---------- 运动代偿换算（正向激励口径） ----------
const SEED_PRESETS = [
  { code: 'jog', name: '慢跑(8km/h)', unit: 'km', factor: 1.036, byWeight: true },
  { code: 'walk', name: '快走(5km/h)', unit: '步', factor: 5 / 130, byWeight: false },
  { code: 'rope', name: '跳绳(中速)', unit: '分钟', factor: 11, byWeight: false },
  { code: 'pushup', name: '俯卧撑', unit: '个', factor: 0.55, byWeight: false },
]

export function convert(kcal, weightKg) {
  if (kcal <= 0 || weightKg <= 0) return []
  return SEED_PRESETS.map((p) => {
    const amount = p.byWeight ? kcal / (weightKg * p.factor) : kcal / p.factor
    return { ...p, amount: round1(amount), kcal: Math.round(kcal), text: `${p.name} ${round1(amount)} ${p.unit}` }
  })
}

export function narrate(totalKcal, limitKcal, weightKg) {
  const gap = Math.abs(totalKcal - limitKcal)
  const plans = gap > 0 ? convert(gap, weightKg) : []
  let status, headline, message
  if (totalKcal <= limitKcal * 0.95) {
    status = '达标'
    headline = '控卡成功'
    const best = plans[0]?.text || '散步放松'
    message = `本餐摄入 ${Math.round(totalKcal)} kcal，处于健康减脂区间！还余 ${Math.round(gap)} kcal 预算，约 ${best} 就能消耗掉，今天也是自律的一天 🎉`
  } else if (totalKcal <= limitKcal * 1.1) {
    status = '维持'
    headline = '稳稳达标'
    message = `本餐摄入 ${Math.round(totalKcal)} kcal，接近单餐上限 ${Math.round(limitKcal)} kcal。保持这个节奏就很好，明天继续加油！`
  } else {
    status = '超标'
    headline = '轻微超出'
    const top2 = plans.slice(0, 2).map((p) => p.text).join('、') || '快走一会儿'
    message = `本餐超出预算 ${Math.round(gap)} kcal —— ${top2} 即可回归平衡。一次小调整不影响整体进度，明天继续！`
  }
  return {
    status, headline,
    gap_kcal: Math.round(gap),
    message,
    plans: plans.slice(0, status === '超标' ? 2 : 3).map(({ code, name, amount, unit, kcal: k, text }) => ({ code, name, amount, unit, kcal: k, text })),
  }
}

export function suggestionForGap(gapKcal, weightKg) {
  const gap = Math.round(gapKcal)
  if (gap > 0) {
    return {
      gap_kcal: gap, state: 'under', headline: '今日还可吃',
      message: `距今日目标还有 ${gap} kcal 预算，优先安排高蛋白低脂的搭配（如麦香鸡 + 玉米杯）`, plans: [],
    }
  }
  const over = Math.abs(gap)
  const plans = over > 0 ? convert(over, weightKg) : []
  if (!plans.length) {
    return { gap_kcal: gap, state: 'on_target', headline: '今日正好达标', message: '今日摄入刚好等于目标，保持这个节奏就很好 🌟', plans: [] }
  }
  const top = plans.slice(0, 2).map((p) => p.text).join('、')
  return {
    gap_kcal: gap, state: 'over', headline: '今日已超出',
    message: `今日超出 ${over} kcal —— ${top} 即可回归平衡，明天继续！`,
    plans: plans.slice(0, 3).map(({ code, name, amount, unit, kcal: k, text }) => ({ code, name, amount, unit, kcal: k, text })),
  }
}

// ---------- 优惠券凑单比价 ----------
export function evaluate(meals, coupons) {
  if (!meals.length) throw new Error('meal组合不能为空')
  const subtotal = sum(meals, 'price')
  const totalKcal = sum(meals, 'kcal')
  const protein = sum(meals, 'protein_g')
  let bestCoupon = null
  let bestDiscount = 0
  for (const c of coupons || []) {
    const cats = new Set(meals.map((m) => m.category))
    if (c.applies_to?.length && ![...cats].some((cat) => c.applies_to.includes(cat))) continue
    const d = discountFor(c, subtotal)
    if (d > bestDiscount) { bestCoupon = c; bestDiscount = d }
  }
  const final = Math.max(subtotal - bestDiscount, 0)
  return {
    meals, subtotal: r2(subtotal),
    coupon_code: bestCoupon?.code ?? null, coupon_title: bestCoupon?.title ?? null,
    discount: r2(bestDiscount), final_price: r2(final),
    total_kcal: Math.round(totalKcal), total_protein_g: round1(protein),
    saving: r2(bestDiscount),
    label: bestCoupon ? `最省¥${final.toFixed(2)}` : `单点¥${final.toFixed(2)}`,
  }
}

function discountFor(c, subtotal) {
  if (subtotal < c.threshold) return 0
  return Math.min(c.discount, subtotal)
}

const sum = (arr, key) => arr.reduce((a, m) => a + (Number(m[key]) || 0), 0)
const r2 = (n) => Math.round(n * 100) / 100

function hasBeverage(meals) { return meals.some((m) => ['饮料', '咖啡'].includes(m.category)) }
function isMain(meals) { return meals.some((m) => ['汉堡', '鸡肉'].includes(m.category)) }

export function recommend(selection, pool, coupons) {
  const basePlan = evaluate(selection, coupons)
  let best = basePlan
  const picked = new Set(selection.map((m) => m.code))
  const addons = pool.filter((p) => !picked.has(p.code)).sort((a, b) => a.price - b.price)
  const combos = (arr, size) => {
    const out = []
    const walk = (start, cur) => {
      if (cur.length === size) { out.push([...cur]); return }
      for (let i = start; i < arr.length; i++) { cur.push(arr[i]); walk(i + 1, cur); cur.pop() }
    }
    walk(0, [])
    return out
  }
  for (let size = 1; size <= 2; size++) {
    for (const combo of combos(addons, size)) {
      const plan = evaluate([...selection, ...combo], coupons)
      const moreComplete = isMain([...selection, ...combo]) && hasBeverage([...selection, ...combo])
      if (plan.final_price < best.final_price - 0.01) best = plan
      else if (Math.abs(plan.final_price - best.final_price) < 0.01 && moreComplete) best = plan
    }
  }
  const saved = r2(basePlan.final_price - best.final_price)
  const result = { ...best }
  result.baseline = basePlan
  result.baseline_price = basePlan.final_price
  result.extra_saving = saved
  result.recommend_text = saved > 0.01
    ? `再凑一个${isMain(best.meals) ? '套餐' : '单品'}，实付从¥${basePlan.final_price.toFixed(2)}降到¥${best.final_price.toFixed(2)}，省¥${saved.toFixed(2)}`
    : `当前方案已是卡券最优（实付¥${best.final_price.toFixed(2)}）`
  return result
}
