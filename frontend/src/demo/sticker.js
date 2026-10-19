/**
 * Demo 模式贴纸 SVG —— 按 sticker_engine.py 的版式做一个轻量模板版：
 * 320×340 卡片 + 标题/日期 + 餐品行 + 合计热量 + 右下角状态印章。
 * 线条与配色对齐后端输出（#fffdf7 底 / #e8811f 边），全部为项目自绘元素。
 */

const STAMP_BY_STATUS = {
  达标: ['麦门', '达标', '#3b6d11'],
  维持: ['麦门', '维持', '#185fa5'],
  超标: ['麦门', '超标', '#e8811f'],
}

export function buildStickerSvg(date, status, meals, totalKcal) {
  const rows = (meals || []).slice(0, 7)
  const startY = 78
  const rowH = 26
  const mealText = rows.length
    ? rows
        .map((m, i) => {
          const y = startY + i * rowH
          return (
            `<text x="24" y="${y}" font-size="13" fill="#3b2a1a" font-family="sans-serif">${esc(m.name)}` +
            `<tspan dx="6" font-size="11" fill="#8a7561">${Math.round(m.kcal)} kcal · ¥${m.price}</tspan></text>`
          )
        })
        .join('')
    : `<text x="160" y="142" text-anchor="middle" font-size="13" fill="#b9a894" font-family="sans-serif">未记录餐品</text>`

  const [t1, t2, color] = STAMP_BY_STATUS[status] || STAMP_BY_STATUS.维持
  const bottomY = 306
  const kcalY = rows.length ? Math.max(startY + rows.length * rowH + 14, 268) : 268

  return (
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 340" width="320" height="340" role="img" aria-label="${date} 控卡打卡贴纸">` +
    `<rect x="2" y="2" width="316" height="336" rx="26" fill="#fffdf7" stroke="${color}" stroke-width="4"/>` +
    `<text x="160" y="30" text-anchor="middle" font-size="19" fill="#3b2a1a" font-family="sans-serif" font-weight="bold">麦门控卡打卡</text>` +
    `<text x="160" y="47" text-anchor="middle" font-size="12" fill="#8a7561" font-family="sans-serif">${date}</text>` +
    mealText +
    `<line x1="18" y1="${bottomY}" x2="302" y2="${bottomY}" stroke="#ece0d2" stroke-width="1.5"/>` +
    `<text x="160" y="330" text-anchor="middle" font-size="17" fill="#3b2a1a" font-family="sans-serif" font-weight="bold">${Math.round(totalKcal)} kcal</text>` +
    `<g transform="translate(272,298) rotate(-12)">` +
    `<circle r="34" fill="#fffdf7" stroke="${color}" stroke-width="3.5"/>` +
    `<circle r="28" fill="none" stroke="${color}" stroke-width="1.2" opacity="0.65"/>` +
    `<text y="-1" text-anchor="middle" font-size="11" fill="${color}" font-family="sans-serif" font-weight="bold">${t1}</text>` +
    `<text y="13" text-anchor="middle" font-size="11" fill="${color}" font-family="sans-serif" font-weight="bold">${t2}</text>` +
    `</g></svg>`
  )
}

function esc(s) {
  return String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}
