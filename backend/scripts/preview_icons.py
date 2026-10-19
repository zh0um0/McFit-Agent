"""渲染全部商品图标为预览 SVG，用于人工检查视觉效果。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.icon_library import render_icon          # noqa: E402
from app.services.mcd_official_data import MCD_OFFICIAL_PICKS  # noqa: E402

COLS = 5
ICON = 84
PAD_X, PAD_Y = 18, 34
CELL_W = ICON + PAD_X * 2
CELL_H = ICON + PAD_Y + 18

items = list(MCD_OFFICIAL_PICKS.items())
rows = (len(items) + COLS - 1) // COLS
W = COLS * CELL_W + PAD_X
H = rows * CELL_H + PAD_Y + 30

parts = [
    f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
    f'width="{W}" height="{H}" font-family="sans-serif">',
    f'<rect width="{W}" height="{H}" fill="#faf6f0"/>',
    f'<text x="{W / 2}" y="22" text-anchor="middle" font-size="15" fill="#2b1d10">'
    f'全部 20 个商品的自绘图标（4类 × 5个）</text>',
]

for i, (name, (cat, *_)) in enumerate(items):
    r, c = divmod(i, COLS)
    x = PAD_X + c * CELL_W
    y = PAD_Y + 30 + r * CELL_H
    parts.append(f'<rect x="{x}" y="{y - 4}" width="{CELL_W - PAD_X}" '
                 f'height="{ICON + 8}" rx="10" fill="#fffdf7" stroke="#e5d9c9" '
                 f'stroke-width="1"/>')
    parts.append(render_icon(name, cat, "#2b1d10", ICON, x, y))
    label = name if len(name) <= 6 else name[:6] + "…"
    parts.append(f'<text x="{x + (CELL_W - PAD_X) / 2:.1f}" y="{y + ICON + 14}" '
                 f'text-anchor="middle" font-size="11" fill="#6b5847">{label}</text>')

parts.append('</svg>')

out = os.path.join(os.environ.get('TEMP', '/tmp'), 'icons_preview.svg')
with open(out, 'w', encoding='utf-8') as f:
    f.write(''.join(parts))
print(f'已生成 {out}  共 {len(items)} 个图标')