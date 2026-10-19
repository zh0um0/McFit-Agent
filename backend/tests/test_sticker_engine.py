"""自绘贴纸引擎测试：固定尺寸 + 真实商品名 + 图标独立。"""
from __future__ import annotations

import re

import pytest

from app.services.icon_library import MCD_CATEGORY_HINT, get_icon_paths, render_icon
from app.services.mcd_official_data import MCD_OFFICIAL_PICKS
from app.services.sticker_engine import (
    STICKER_H, STICKER_W, build_sticker_svg, sticker_fingerprint,
)

M1 = {"name": "板烧鸡腿堡", "category": "汉堡"}
M2 = {"name": "大杯玉米杯", "category": "小食"}
M3 = {"name": "冰美式中杯", "category": "饮品"}
M4 = {"name": "菠萝派", "category": "甜点"}


def _vb(svg: str) -> str:
    m = re.search(r'viewBox="([^"]+)"', svg)
    return m.group(1) if m else ""


# ---------------- 固定尺寸（核心需求）----------------
@pytest.mark.parametrize("meals", [
    [],
    [M1],
    [M1, M2],
    [M1, M2, M3],
    [M1, M2, M3, M4],
    [{"name": "巨无霸", "category": "汉堡"}, {"name": "中薯条", "category": "小食"},
     {"name": "草莓新地", "category": "甜点"}, {"name": "可乐中杯", "category": "饮品"},
     {"name": "香芋派", "category": "甜点"}],
])
def test_sticker_viewbox_identical_regardless_of_meal_count(meals):
    """无论 0/1/2/3/4/5 个餐品，外部轮廓必须完全一致。"""
    svg = build_sticker_svg(meals, "达标", 626, "2026-10-19")
    assert _vb(svg) == f"0 0 {STICKER_W} {STICKER_H}"


def test_sticker_outer_rect_identical():
    """外框矩形坐标尺寸必须固定，不能随餐品数量伸缩。"""
    rects = set()
    for meals in ([M1], [M1, M2], [M1, M2, M3], [M1, M2, M3, M4]):
        svg = build_sticker_svg(meals, "达标", 626, "2026-10-19")
        m = re.search(r'<rect x="2" y="2" width="([\d.]+)" height="([\d.]+)"', svg)
        assert m, "未找到外框 rect"
        rects.add((m.group(1), m.group(2)))
    assert len(rects) == 1, f"外框尺寸不一致：{rects}"


def test_sticker_width_height_attrs_fixed():
    a = build_sticker_svg([M1], "达标", 500, "2026-10-19")
    b = build_sticker_svg([M1, M2, M3, M4], "达标", 900, "2026-10-19")
    ra = re.search(r'width="(\d+)" height="(\d+)"', a)
    rb = re.search(r'width="(\d+)" height="(\d+)"', b)
    assert ra.groups() == rb.groups()


# ---------------- 使用真实商品名 ----------------
def test_sticker_contains_real_meal_names():
    meals = [{"name": "板烧鸡腿堡", "category": "汉堡"},
             {"name": "大杯玉米杯", "category": "小食"}]
    svg = build_sticker_svg(meals, "达标", 478, "2026-10-19")
    assert "板烧鸡腿堡" in svg
    assert "大杯玉米杯" in svg
    # 不应出现类别概括代替商品名
    assert "鸡肉+小食" not in svg


def test_sticker_names_are_escaped():
    """商品名来自外部接口，必须做 XML 转义防注入。"""
    svg = build_sticker_svg(
        [{"name": '<script>&"\'', "category": "汉堡"}], "达标", 100, "2026-10-19")
    assert "<script>" not in svg
    assert "&lt;" in svg or "…" in svg      # 转义或被截断


def test_sticker_uses_category_for_icon_not_display():
    """类别只用于选图标，不作为展示文字。"""
    svg = build_sticker_svg(
        [{"name": "巨无霸", "category": "汉堡"}], "达标", 513, "2026-10-19")
    assert "巨无霸" in svg
    # 类别不应单独出现在文字里（图标是路径不是文字）
    assert ">汉堡<" not in svg


def test_sticker_dedup_same_name():
    meals = [M1, M1, M1]
    svg = build_sticker_svg(meals, "达标", 391, "2026-10-19")
    assert svg.count("板烧鸡腿堡") == 1     # 同款只贴一次


def test_sticker_shows_overflow_count():
    meals = [{"name": n, "category": "汉堡"} for n in
             ["巨无霸", "麦香鸡", "双层吉士汉堡", "板烧鸡腿堡", "麦辣鸡腿汉堡"]]
    svg = build_sticker_svg(meals, "达标", 2000, "2026-10-19")
    assert "+1" in svg                        # 超出 4 个的部分有提示


def test_sticker_empty_meals():
    svg = build_sticker_svg([], "达标", 0, "2026-10-19")
    assert "未记录餐品" in svg
    assert _vb(svg) == f"0 0 {STICKER_W} {STICKER_H}"


# ---------------- 图标库 ----------------
def test_every_picked_item_has_unique_icon():
    """20 个精选单品必须各有独立图标细节，否则贴纸无法区分。"""
    no_detail = [n for n in MCD_OFFICIAL_PICKS if n not in MCD_CATEGORY_HINT]
    assert not no_detail, f"以下单品缺少图标映射：{no_detail}"


def test_icons_differ_within_same_category():
    """同一类别内的不同单品，图标细节必须不同（否则视觉上分不出）。"""
    by_cat: dict[str, list] = {}
    for name, (cat, *_) in MCD_OFFICIAL_PICKS.items():
        by_cat.setdefault(cat, []).append(name)

    for cat, names in by_cat.items():
        sigs = [tuple(get_icon_paths(n, cat)) for n in names]
        assert len(set(sigs)) == len(sigs), f"{cat} 类存在图标完全相同的单品"


def test_render_icon_contains_svg_group():
    out = render_icon("板烧鸡腿堡", "汉堡", "#1f9d55", 60, 10, 20)
    assert "<g" in out and "<path" in out
    assert "translate(10.00,20.00)" in out


def test_resolve_category_by_fallback():
    """未显式映射的商品名应能按关键词推断类别。"""
    from app.services.icon_library import resolve_category
    assert resolve_category("巨无霸套餐") == "汉堡"
    assert resolve_category("巧克力新地") == "甜点"
    assert resolve_category("冰可乐大杯") == "饮品"
    assert resolve_category("完全陌生的东西", "汉堡") == "汉堡"


# ---------------- 指纹与状态 ----------------
def test_fingerprint_differs_by_meal():
    a = sticker_fingerprint([M1])
    b = sticker_fingerprint([M1, M2])
    assert a != b
    assert a == sticker_fingerprint([M1])


def test_status_changes_color():
    """三种状态应产出不同颜色的贴纸。"""
    colors = set()
    for st in ("达标", "维持", "超标"):
        svg = build_sticker_svg([M1], st, 500, "2026-10-19")
        colors.add(re.search(r'stroke="(#[0-9a-f]{6})"', svg).group(1))
    assert len(colors) == 3


def test_kcal_shown():
    svg = build_sticker_svg([M1], "达标", 391, "2026-10-19")
    assert "391 kcal" in svg


def test_date_shown():
    svg = build_sticker_svg([M1], "达标", 391, "2026-10-19")
    assert "2026-10-19" in svg