# -*- coding: utf-8 -*-
"""把 docs/gif-frames 的录帧合成为演示 GIF（docs/demo.gif）。

帧命名：001H.png（H=结果帧，停留久）/ 002.png（过程帧）。
输出：~800px 宽、自适应调色板、永久循环。
"""
import sys
from pathlib import Path

from PIL import Image

FRAME_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("docs/gif-frames")
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("docs/demo.gif")

HOLD_MS = 1400   # 结果帧停留
STEP_MS = 650    # 过程帧
TARGET_W = 800
MAX_COLORS = 160

files = sorted(FRAME_DIR.glob("*.png"))
if not files:
    sys.exit(f"no frames in {FRAME_DIR}")

frames = []
durations = []
for f in files:
    im = Image.open(f).convert("RGB")
    if im.width > TARGET_W:
        h = round(im.height * TARGET_W / im.width)
        im = im.resize((TARGET_W, h), Image.LANCZOS)
    frames.append(im)
    durations.append(HOLD_MS if f.stem.endswith("H") else STEP_MS)

# 全局自适应调色板：以第一帧质量为基准量化，避免逐帧调色板闪烁
pal = frames[0].quantize(colors=MAX_COLORS, method=Image.MEDIANCUT, dither=Image.FLOYDSTEINBERG)
quantized = [im.quantize(palette=pal, dither=Image.FLOYDSTEINBERG) for im in frames]

OUT.parent.mkdir(parents=True, exist_ok=True)
quantized[0].save(
    OUT,
    save_all=True,
    append_images=quantized[1:],
    duration=durations,
    loop=0,
    optimize=True,
)
size_mb = OUT.stat().st_size / 1048576
print(f"OK: {OUT} -> {len(quantized)} frames, {size_mb:.2f} MB")
