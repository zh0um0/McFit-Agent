"""自绘 SVG 食物贴纸引擎。

【合规声明】全部为项目内自绘线条简笔图标，**严禁使用麦当劳官方 Logo、
餐品实拍图或官方物料**——此为参赛声明的知识产权红线。

【固定尺寸原则】无论贴1 个还是 4 个餐品，贴纸的**外部轮廓（viewBox）
完全一致**，只有内部图标排布与文字内容变化。这样日历视图里每格贴纸
大小统一，不会因餐品数量不同而忽大忽小。
"""
from __future__ import annotations

from app.services.icon_library import render_icon, resolve_category

CHECKIN_DONE = "达标"
CHECKIN_KEEP = "维持"
CHECKIN_OVER = "超标"

_STATUS_COLOR = {
    CHECKIN_DONE: "#1f9d55",
    CHECKIN_KEEP: "#2f6fd0",
    CHECKIN_OVER: "#e8811f",
}
_STAMP_TEXT = {
    CHECKIN_DONE: "麦门减脂自律先锋印",
    CHECKIN_KEEP: "麦门日常平衡章",
    CHECKIN_OVER: "麦门弹性平衡章",
}

# ── 固定画布尺寸（贴纸无论几个餐品都保持此大小）────────────
STICKER_W = 320
STICKER_H = 340
_MARGIN = 18
_HEADER_H = 50          # 标题 + 日期区
_ICON_TOP = _HEADER_H + 6
_ICON_AREA_H = 172      # 图标区高度（不随餐品数量变化）
_KCAL_LINE_H = 34                        # 底部热量行
_MAX_ICONS = 4


def _layout(n: int) -> list[tuple[float, float, float]]:
    """按图标数量返回 (x, y, size) 列表——画布固定，仅内部排布变化。

    1 个：居中大图 | 2 个：并排 | 3 个：上二下一 | 4 个：2×2 网格
    """
    if n <= 1:
        s = min(_ICON_AREA_H, 130)
        return [((STICKER_W - s) / 2, _ICON_TOP + (_ICON_AREA_H - s) / 2, s)]
    if n == 2:
        s = 92
        gap = 26
        total = s * 2 + gap
        x0 = (STICKER_W - total) / 2
        return [(x0 + i * (s + gap), _ICON_TOP + (_ICON_AREA_H - s) / 2, s) for i in range(2)]
    if n == 3:
        s = 72
        y_top = _ICON_TOP + 4
        return [
            ((STICKER_W - (s * 2 + 8)) / 2, y_top, s),
            ((STICKER_W - (s * 2 + 8)) / 2 + s + 8, y_top, s),
            ((STICKER_W - s) / 2, y_top + s + 12, s),
        ]
    s = 78
    gap = 14
    s = 72
    x0 = (STICKER_W - (s * 2 + gap)) / 2
    y0 = _ICON_TOP + 4
    return [
        (x0, y0, s), (x0 + s + gap, y0, s),
        (x0, y0 + s + 14, s), (x0 + s + gap, y0 + s + 14, s),
    ]


def _esc(text: str) -> str:
    """XML 转义——商品名称来自外部接口，必须防注入。"""
    return (str(text).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def _shorten(name: str, n: int = 7) -> str:
    name = str(name or "")
    return name if len(name) <= n else name[:n] + "…"


def build_sticker_svg(meals: list[dict], status: str, kcal: int, date_str: str) -> str:
    """生成自绘SVG 贴纸。

    meals: [{name, category}] —— **必须是真实点单的商品名称**，
    这样贴纸展示内容与本次点单完全吻合。
    外部轮廓固定为 STICKER_W × STICKER_H，与餐品数量无关。
    """
    color = _STATUS_COLOR.get(status, _STATUS_COLOR[CHECKIN_KEEP])

    # 名称去重但保留顺序（同款只贴一次，避免重复图标占位）
    items: list[tuple[str, str]] = []
    for m in (meals or []):
        nm = str((m or {}).get("name") or "").strip()
        if not nm:
            continue
        cat = str((m or {}).get("category") or "") or resolve_category(nm)
        if any(nm == x[0] for x in items):
            continue
        items.append((nm, cat))
    items = items[:_MAX_ICONS]

    p: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {STICKER_W} {STICKER_H}" '
        f'width="{STICKER_W}" height="{STICKER_H}" role="img" '
        f'aria-label="{_esc(date_str)} 控卡打卡贴纸">',
        f'<rect x="2" y="2" width="{STICKER_W - 4}" height="{STICKER_H - 4}" rx="26" '
        f'fill="#fffdf7" stroke="{color}" stroke-width="4"/>',
        f'<text x="{STICKER_W / 2}" y="30" text-anchor="middle" font-size="19" '
        f'fill="#3b2a1a" font-family="sans-serif" font-weight="bold">麦门控卡打卡</text>',
        f'<text x="{STICKER_W / 2}" y="47" text-anchor="middle" font-size="12" '
        f'fill="#8a7561" font-family="sans-serif">{_esc(date_str)}</text>',
    ]

    if not items:
        p.append(f'<text x="{STICKER_W / 2}" y="{_ICON_TOP + _ICON_AREA_H / 2}" '
                 f'text-anchor="middle" font-size="13" fill="#b9a894" '
                 f'font-family="sans-serif">未记录餐品</text>')
    else:
        slots = _layout(len(items))
        # 标签跟随各自图标底部，而非统一固定行——
        # 2×2 网格时下排图标贴近底部，固定行会让文字压在图标上
        for (nm, _cat), (x, y, s) in zip(items, slots):
            fs = 9.5 if len(items) >= 2 else 10.5
            p.append(f'<text x="{x + s / 2:.1f}" y="{y + s + 12:.1f}" text-anchor="middle" '
                     f'font-size="{fs}" fill="#6b5847" font-family="sans-serif">'
                     f'{_esc(_shorten(nm, 6))}</text>')
        for (nm, cat), (x, y, s) in zip(items, slots):
            p.append(render_icon(nm, cat, color, s, x, y))

        # 超出 4 个时的提示
        extra = len([m for m in (meals or []) if (m or {}).get("name")]) - len(items)
        if extra > 0:
            p.append(f'<text x="{STICKER_W - 22}" y="24" text-anchor="middle" '
                     f'font-size="11" fill="{color}" font-family="sans-serif">'
                     f'+{extra}</text>')

    # 底部热量条：独立分隔线 + 数值，不与标签重叠
    bar_y = STICKER_H - _KCAL_LINE_H
    p.append(f'<line x1="{_MARGIN}" y1="{bar_y}" x2="{STICKER_W - _MARGIN}" '
             f'y2="{bar_y}" stroke="#ece0d2" stroke-width="1.5"/>')
    p.append(f'<text x="{STICKER_W / 2}" y="{bar_y + 24}" text-anchor="middle" '
             f'font-size="17" fill="#3b2a1a" font-family="sans-serif" '
             f'font-weight="bold">{int(kcal)} kcal</text>')

    # 状态印章（固定右下角，不随图标数量移动）
    sx, sy, sr = STICKER_W - 48, STICKER_H - 42, 34
    p.append(f'<g transform="translate({sx},{sy}) rotate(-12)">')
    p.append(f'<circle r="{sr}" fill="#fffdf7" stroke="{color}" stroke-width="3.5"/>')
    p.append(f'<circle r="{sr - 6}" fill="none" stroke="{color}" stroke-width="1.2" '
             f'opacity="0.65"/>')
    p.append(f'<text y="-1" text-anchor="middle" font-size="11" fill="{color}" '
             f'font-family="sans-serif" font-weight="bold">麦门</text>')
    p.append(f'<text y="13" text-anchor="middle" font-size="11" fill="{color}" '
             f'font-family="sans-serif" font-weight="bold">{_esc(status)}</text>')
    p.append('</g>')
    p.append('</svg>')
    return "".join(p)


def sticker_fingerprint(meals: list[dict]) -> str:
    """贴纸内容指纹，用于前端判断是否需要重新生成。"""
    import hashlib
    payload = "|".join(sorted(str((m or {}).get("name") or "") for m in meals))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]