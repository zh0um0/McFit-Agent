/**
 * Demo 模式贴纸 SVG —— 与后端 sticker_engine.py + icon_library.py 1:1 对齐的移植版。
 * 320×340 固定画布：标题/日期 + 图标区（最多 4 个自绘食物图标）+ 热量条 + 右下角状态印章。
 *
 * 【合规声明】全部为项目内自绘线条简笔图标，严禁使用麦当劳官方 Logo、餐品实拍图或官方物料。
 */

// ── 类别基础骨架（4 类，viewBox 100×100）────────────────────
const CATEGORY_BASE = {
  汉堡: [
    'M20 44 q30-26 60 0',
    'M16 48 h68 v9 h-68 z',
    'M18 62 h64 a4 4 0 0 1 4 4 v5 a4 4 0 0 1 -4 4 h-64 a4 4 0 0 1 -4-4 v-5 a4 4 0 0 1 4-4 z',
    'M20 44 q4-10 12-10 M50 34 q10 0 14 10',
  ],
  小食: [
    'M30 28 h40 l-4 50 a5 5 0 0 1 -5 4 h-22 a5 5 0 0 1 -5-4 z',
    'M28 28 h44',
    'M46 28 l6-12',
  ],
  甜点: [
    'M28 48 h44 l-5 30 a5 5 0 0 1 -5 4 h-24 a5 5 0 0 1 -5-4 z',
    'M28 48 q22-28 44 0',
    'M26 48 h48',
  ],
  饮品: [
    'M26 34 h38 v44 a6 6 0 0 1 -6 6 h-26 a6 6 0 0 1 -6-6 z',
    'M24 34 l6-14 h32 l6 14',
    'M32 20 v-10',
    'M64 42 h7 a9 9 0 0 1 0 18 h-7',
  ],
}

// ── 单品特征细节（叠加在骨架之上）──────────────────────────
const ITEM_DETAIL = {
  // 汉堡类：靠「夹心层数 + 顶部配料」区分
  板烧鸡腿堡: ['M24 52 h52'],
  麦辣鸡腿汉堡: ['M24 51 h14 M40 51 h14 M56 51 h12'],
  巨无霸: ['M24 50 h52', 'M24 56 h52'],
  双层吉士汉堡: ['M24 49 h52', 'M24 58 h52'],
  麦香鸡: ['M36 42 q14-6 28 0', 'M40 38 q10-4 20 0'],
  // 小食类：靠杯内物品形状区分
  麦乐鸡5块: ['M36 46 h28 v14 h-28 z', 'M50 46 v14'],
  '麦辣鸡翅-2块': ['M34 50 l16-8 12 14-16 8 z'],
  大杯玉米杯: ['M36 48 h28 l-3 12 h-22 z', 'M42 50 v8 M52 50 v8'],
  中薯条: ['M36 40 v32 M46 40 v32 M56 40 v32'],
  脆薯饼: ['M34 50 q16-8 32 0 v12 q-16 8 -32 0 z'],
  // 甜点类：靠顶部装饰区分
  菠萝派: ['M38 40 l4-8 4 8', 'M50 40 l4-8 4 8'],
  香芋派: ['M40 38 q10-6 20 0 v6 q-10 6 -20 0 z'],
  草莓新地: ['M44 24 l4-10 4 10'],
  奥利奥麦旋风: ['M40 36 h8 v6 h-8 z', 'M52 36 h8 v6 h-8 z'],
  圆筒冰淇淋: ['M38 18 h24 l-4 16 h-16 z', 'M46 18 v-8'],
  // 饮品类：靠杯身内图案区分
  无糖可口可乐中杯: ['M34 50 h26 M34 62 h26'],
  可乐中杯: ['M38 52 q6 6 0 12 q6-6 0-12', 'M48 52 q6 6 0 12'],
  '100%苹果汁': ['M44 54 q8-10 12 0 q4 10-4 10z', 'M48 44 v-8'],
  '纯牛奶（盒装）': ['M36 52 h24 v18 h-24 z', 'M44 52 l8-8'],
  冰美式中杯: ['M38 56 h8 v12 h-8 z', 'M52 56 h6 v12 h-6 z'],
}

// 类别提示表（单品 → 类别）
const CATEGORY_HINT = {
  板烧鸡腿堡: '汉堡', 麦辣鸡腿汉堡: '汉堡', 巨无霸: '汉堡',
  双层吉士汉堡: '汉堡', 麦香鸡: '汉堡',
  麦乐鸡5块: '小食', '麦辣鸡翅-2块': '小食', 大杯玉米杯: '小食',
  中薯条: '小食', 脆薯饼: '小食',
  菠萝派: '甜点', 香芋派: '甜点', 草莓新地: '甜点',
  奥利奥麦旋风: '甜点', 圆筒冰淇淋: '甜点',
  无糖可口可乐中杯: '饮品', 可乐中杯: '饮品', '100%苹果汁': '饮品',
  '纯牛奶（盒装）': '饮品', 冰美式中杯: '饮品',
}

// 兜底：名称未匹配时按关键词猜测，猜不到用汉堡骨架
const FALLBACK_RULES = [
  [['麦满分', '堡'], '汉堡'],
  [['鸡', '翅', '乐鸡', '脆鸡'], '小食'],
  [['薯', '玉米', '饼', '脆'], '小食'],
  [['派', '新地', '旋风', '冰淇淋', '雪冰'], '甜点'],
  [['可乐', '雪碧', '咖啡', '美式', '牛奶', '汁', '茶'], '饮品'],
]

const GENERIC_DETAIL = ['M44 20 q6-6 12 0', 'M70 46 q4 4 0 8']

export function resolveCategory(name, fallback = '') {
  if (CATEGORY_HINT[name]) return CATEGORY_HINT[name]
  for (const [keywords, cat] of FALLBACK_RULES) {
    if (keywords.some((k) => name.includes(k))) return cat
  }
  return fallback || '汉堡'
}

/** 渲染单个商品图标为 <g> 分组：骨架层 stroke 3 + 特征层 stroke 4.2（缩小后仍可辨）。 */
function renderIcon(name, category, color, size, x, y) {
  const cat = category || resolveCategory(name)
  const base = CATEGORY_BASE[cat] || CATEGORY_BASE.汉堡
  const detail = ITEM_DETAIL[name] || GENERIC_DETAIL
  const scale = size / 100.0
  const tf = `transform="translate(${x.toFixed(2)},${y.toFixed(2)}) scale(${scale.toFixed(4)})"`
  const layer = (paths, w) =>
    `<g ${tf} stroke="${color}" stroke-width="${w}" fill="none" stroke-linecap="round" stroke-linejoin="round">` +
    paths.map((d) => `<path d="${d}"/>`).join('') +
    `</g>`
  return layer(base, 3) + layer(detail, 4.2)
}

// ── 固定画布尺寸（与后端 STICKER_W/H 一致）──────────────────
const W = 320
const H = 340
const MARGIN = 18
const ICON_TOP = 56 // _HEADER_H(50) + 6
const ICON_AREA_H = 172
const KCAL_LINE_H = 34
const MAX_ICONS = 4

/** 按图标数量返回 (x, y, size)——画布固定，仅内部排布变化：1 居中 / 2 并排 / 3 上二下一 / 4 2×2。 */
function layout(n) {
  if (n <= 1) {
    const s = Math.min(ICON_AREA_H, 130)
    return [[(W - s) / 2, ICON_TOP + (ICON_AREA_H - s) / 2, s]]
  }
  if (n === 2) {
    const s = 92
    const gap = 26
    const x0 = (W - (s * 2 + gap)) / 2
    const y = ICON_TOP + (ICON_AREA_H - s) / 2
    return [
      [x0, y, s],
      [x0 + s + gap, y, s],
    ]
  }
  if (n === 3) {
    const s = 72
    const yTop = ICON_TOP + 4
    const x0 = (W - (s * 2 + 8)) / 2
    return [
      [x0, yTop, s],
      [x0 + s + 8, yTop, s],
      [(W - s) / 2, yTop + s + 12, s],
    ]
  }
  const s = 72
  const gap = 14
  const x0 = (W - (s * 2 + gap)) / 2
  const y0 = ICON_TOP + 4
  return [
    [x0, y0, s],
    [x0 + s + gap, y0, s],
    [x0, y0 + s + 14, s],
    [x0 + s + gap, y0 + s + 14, s],
  ]
}

function esc(s) {
  return String(s ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

function shorten(name, n = 7) {
  name = String(name || '')
  return name.length <= n ? name : name.slice(0, n) + '…'
}

const STATUS_COLOR = { 达标: '#1f9d55', 维持: '#2f6fd0', 超标: '#e8811f' }

/**
 * 生成自绘 SVG 贴纸（版式与后端 build_sticker_svg 完全一致）。
 * meals: [{name, kcal, price}] —— 必须是真实点单的商品名称。
 */
export function buildStickerSvg(date, status, meals, totalKcal) {
  const color = STATUS_COLOR[status] || STATUS_COLOR.维持

  // 名称去重但保留顺序（同款只贴一次），最多 4 个图标
  const items = []
  for (const m of meals || []) {
    const nm = String((m || {}).name || '').trim()
    if (!nm || items.some((x) => x.name === nm)) continue
    items.push({ name: nm, cat: String((m || {}).category || '') || resolveCategory(nm) })
  }
  const shown = items.slice(0, MAX_ICONS)

  const p = []
  p.push(
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" role="img" aria-label="${esc(date)} 控卡打卡贴纸">`
  )
  p.push(`<rect x="2" y="2" width="${W - 4}" height="${H - 4}" rx="26" fill="#fffdf7" stroke="${color}" stroke-width="4"/>`)
  p.push(`<text x="${W / 2}" y="30" text-anchor="middle" font-size="19" fill="#3b2a1a" font-family="sans-serif" font-weight="bold">麦门控卡打卡</text>`)
  p.push(`<text x="${W / 2}" y="47" text-anchor="middle" font-size="12" fill="#8a7561" font-family="sans-serif">${esc(date)}</text>`)

  if (!shown.length) {
    p.push(`<text x="${W / 2}" y="${ICON_TOP + ICON_AREA_H / 2}" text-anchor="middle" font-size="13" fill="#b9a894" font-family="sans-serif">未记录餐品</text>`)
  } else {
    const slots = layout(shown.length)
    // 标签跟随各自图标底部（先画标签再画图标，标签不会被图标线条压住）
    shown.forEach(({ name }, i) => {
      const [x, y, s] = slots[i]
      const fs = shown.length >= 2 ? 9.5 : 10.5
      p.push(`<text x="${(x + s / 2).toFixed(1)}" y="${(y + s + 12).toFixed(1)}" text-anchor="middle" font-size="${fs}" fill="#6b5847" font-family="sans-serif">${esc(shorten(name, 6))}</text>`)
    })
    shown.forEach(({ name, cat }, i) => {
      const [x, y, s] = slots[i]
      p.push(renderIcon(name, cat, color, s, x, y))
    })
    // 超出 4 个时的提示
    const extra = (meals || []).filter((m) => (m || {}).name).length - shown.length
    if (extra > 0) {
      p.push(`<text x="${W - 22}" y="24" text-anchor="middle" font-size="11" fill="${color}" font-family="sans-serif">+${extra}</text>`)
    }
  }

  // 底部热量条
  const barY = H - KCAL_LINE_H
  p.push(`<line x1="${MARGIN}" y1="${barY}" x2="${W - MARGIN}" y2="${barY}" stroke="#ece0d2" stroke-width="1.5"/>`)
  p.push(`<text x="${W / 2}" y="${barY + 24}" text-anchor="middle" font-size="17" fill="#3b2a1a" font-family="sans-serif" font-weight="bold">${Math.round(totalKcal)} kcal</text>`)

  // 状态印章（固定右下角，纯文字圆章——与后端一致）
  const sx = W - 48
  const sy = H - 42
  p.push(`<g transform="translate(${sx},${sy}) rotate(-12)">`)
  p.push(`<circle r="34" fill="#fffdf7" stroke="${color}" stroke-width="3.5"/>`)
  p.push(`<circle r="28" fill="none" stroke="${color}" stroke-width="1.2" opacity="0.65"/>`)
  p.push(`<text y="-1" text-anchor="middle" font-size="11" fill="${color}" font-family="sans-serif" font-weight="bold">麦门</text>`)
  p.push(`<text y="13" text-anchor="middle" font-size="11" fill="${color}" font-family="sans-serif" font-weight="bold">${esc(status)}</text>`)
  p.push('</g></svg>')
  return p.join('')
}
