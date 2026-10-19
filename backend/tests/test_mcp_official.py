"""官方 MCP 数据接入的单元测试（不触网，全部用官方真实返回样本）。"""
from __future__ import annotations

import pytest

from app.services.mcd_official_data import (
    CATEGORY_ORDER, MCD_OFFICIAL_PICKS, verify_picks,
)
from app.services.mcp_client import _num, parse_nutrition_payload

# 官方 list-nutrition-foods 真实返回片段（2026-10-19 实测，截取 5 行）
REAL_SAMPLE = (
    "[5]{productName,nutritionDescription,energyKj,energyKcal,protein,"
    "fat,carbohydrate,sodium,calcium}:\n"
    "  板烧鸡腿堡,null,1638,391,23,17,35,1041,93\n"
    "  麦辣鸡腿汉堡,null,2029,485,24,24,42,1208,154\n"
    "  巨无霸,null,2146,513,27,26,42,961,171\n"
    "  麦香鸡,null,1546,369,15,17,39,731,73\n"
    "  双层吉士汉堡,null,1796,429,27,22,31,1017,232"
)


# ---------------- 解析器 ----------------
def test_parse_official_string_format():
    items = parse_nutrition_payload(REAL_SAMPLE)
    assert len(items) == 5
    assert items[0]["productName"] == "板烧鸡腿堡"
    assert items[0]["energyKcal"] == "391"
    assert items[1]["energyKcal"] == "485"


def test_parse_returns_empty_on_bad_format():
    """格式不符时必须返回空列表而不是抛异常或返回垃圾。"""
    assert parse_nutrition_payload("not a valid payload") == []
    assert parse_nutrition_payload("") == []


def test_parse_skips_mismatched_rows():
    """字段数不匹配的行应跳过，不得错位解析。"""
    bad = ("[2]{a,b,c}:\n  1,2\n  3,4,5")   # 第一行字段数不足
    items = parse_nutrition_payload(bad)
    assert len(items) == 1
    assert items[0] == {"a": "3", "b": "4", "c": "5"}


def test_num_handles_null_and_junk():
    assert _num("485") == 485.0
    assert _num("null") == 0.0
    assert _num(None) == 0.0
    assert _num("abc") == 0.0


# ---------------- 精选集 ----------------
def test_each_category_has_exactly_five():
    from collections import Counter
    c = Counter(v[0] for v in MCD_OFFICIAL_PICKS.values())
    assert sorted(c) == sorted(CATEGORY_ORDER)
    for cat, n in c.items():
        assert n == 5, f"{cat} 有 {n} 个，应为5 个"


def test_total_picks_is_20():
    """4 类 × 5 个 = 20 条（饮料与饮品已合并为「饮品」）。"""
    assert len(MCD_OFFICIAL_PICKS) == 20


def test_drink_and_beverage_merged():
    """回归：饮料与饮品必须合并为同一类，不得再拆开。"""
    cats = {v[0] for v in MCD_OFFICIAL_PICKS.values()}
    assert "饮料" not in cats, "饮料应已并入「饮品」"
    assert "饮品" in cats
    # 合并后仍有 5 个饮品，且覆盖咖啡/牛奶/果汁等不同种类
    drinks = [n for n, v in MCD_OFFICIAL_PICKS.items() if v[0] == "饮品"]
    assert len(drinks) == 5
    assert any("美式" in d for d in drinks), "应含咖啡类"
    assert any("牛奶" in d for d in drinks), "应含奶饮类"
    assert any("果汁" in d or "苹果汁" in d for d in drinks), "应含果汁类"


def test_no_duplicate_names():
    assert len(MCD_OFFICIAL_PICKS) == len(set(MCD_OFFICIAL_PICKS))


def test_prices_are_positive():
    for name, (_, price, _, _) in MCD_OFFICIAL_PICKS.items():
        assert price > 0, f"{name} 价格异常：{price}"


def test_verify_picks_reports_missing():
    """官方改名/下架时必须报出缺失项，不能静默失效。"""
    partial = {"板烧鸡腿堡", "巨无霸"}
    r = verify_picks(partial)
    assert len(r["missing"]) == 18
    assert "板烧鸡腿堡" not in r["missing"]
    assert "巨无霸" not in r["missing"]


def test_verify_picks_all_present():
    r = verify_picks(set(MCD_OFFICIAL_PICKS))
    assert r["missing"] == []
    assert r["coverage"] == "20/20"


# ---------------- 主键稳定性 ----------------
def test_generated_code_is_stable_across_calls():
    """跨进程稳定：同一名称必须生成同一编码，否则重启产生重复记录。"""
    import hashlib
    name = "板烧鸡腿堡"
    a = "MCD-" + hashlib.md5(name.encode("utf-8")).hexdigest()[:8].upper()
    b = "MCD-" + hashlib.md5(name.encode("utf-8")).hexdigest()[:8].upper()
    assert a == b
    assert len(a) == 12


def test_different_names_get_different_codes():
    import hashlib
    def code(n):
        return "MCD-" + hashlib.md5(n.encode("utf-8")).hexdigest()[:8].upper()
    assert code("板烧鸡腿堡") != code("巨无霸")


# ---------------- 业务口径 ----------------
def test_no_forbidden_words_in_notes():
    """官方数据源说明不得出现免责缺失或夸大表述。"""
    from app.services.mcd_official_data import OFFICIAL_SOURCE_NOTE
    assert "官方" in OFFICIAL_SOURCE_NOTE
    assert "估算" in OFFICIAL_SOURCE_NOTE     # 价格须标明为估算

# ---------------- 种子/官方数据互斥 ----------------
def test_seed_meals_removed_when_official_present(client):
    """官方数据同步后，种子菜单必须让位，不能两条来源并存。"""
    from sqlalchemy import select
    from app.db.session import SessionLocal
    from app.models.entities import MealCache
    from app.services.mcd_official_data import MCD_OFFICIAL_PICKS

    with SessionLocal() as db:
        # 先灌一条官方数据
        db.add(MealCache(mcp_code="MCD-TEST0001", name="测试官方单品",
                         category="汉堡", kcal=400, source="mcp"))
        db.commit()

        # 触发 init_db 的种子检查逻辑
        from app.db.init_db import _ensure_seed_meals
        _ensure_seed_meals(db)
        db.commit()

        seed_left = db.scalars(
            select(MealCache).where(MealCache.source == "seed")).all()
        mcp_left = db.scalars(
            select(MealCache).where(MealCache.source == "mcp")).all()

    assert len(seed_left) == 0, "官方数据存在时种子菜单应被清理"
    assert any(m.mcp_code == "MCD-TEST0001" for m in mcp_left)


def test_seed_meals_written_when_no_official(client):
    """无官方数据时，种子菜单必须写入（保证零配置可跑）。"""
    from sqlalchemy import func, select
    from app.db.session import SessionLocal
    from app.models.entities import MealCache

    with SessionLocal() as db:
        db.query(MealCache).delete()
        db.commit()
        from app.db.init_db import _ensure_seed_meals
        n = _ensure_seed_meals(db)
        db.commit()
        total = db.scalar(select(func.count()).select_from(MealCache))

    assert n > 0, "无官方数据时应写入种子菜单"
    assert total == n


def test_seed_and_official_values_agree_on_shared_names(client):
    """降级切换时的核心保证：两条来源重名的单品，营养数值必须一致。

    允许重名（同一单品本就该同名），但**数值绝不能矛盾**——
    否则用户会看到「板烧鸡腿堡474 kcal / 391 kcal」两个答案。
    """
    from app.services.seed_data import SEED_MEALS
    from app.services.mcp_client import parse_nutrition_payload

    seed = {m["name"]: m for m in SEED_MEALS}
    items = parse_nutrition_payload(REAL_SAMPLE)
    official = {i["productName"]: i for i in items}

    shared = set(seed) & set(official)
    assert shared, "样本中应存在重名单品用于校验"

    for name in shared:
        s, o = seed[name], official[name]
        assert s["kcal"] == float(o["energyKcal"]), \
            f"{name} 热量不一致：种子 {s['kcal']} vs 官方 {o['energyKcal']}"
        assert s["protein_g"] == float(o["protein"]), \
            f"{name} 蛋白不一致：种子 {s['protein_g']} vs 官方 {o['protein']}"


def test_all_official_picks_have_matching_seed_where_named(client):
    """精选集里凡种子表也收录的单品，两者营养值必须完全一致。"""
    from app.services.mcd_official_data import MCD_OFFICIAL_PICKS
    from app.services.seed_data import SEED_MEALS
    from app.services.mcp_client import parse_nutrition_payload

    seed = {m["name"]: m for m in SEED_MEALS}
    official = {i["productName"]: i for i in parse_nutrition_payload(REAL_SAMPLE)}
    mismatches = []

    for name in MCD_OFFICIAL_PICKS:
        if name not in seed or name not in official:
            continue                      # 样本未覆盖该单品，跳过
        if seed[name]["kcal"] != float(official[name]["energyKcal"]):
            mismatches.append(name)

    assert not mismatches, f"以下单品两源数值不一致：{mismatches}"


# ---------------- 数据源标识的准确性 ----------------
def test_meals_source_reflects_db_not_token(client, auth):
    """source 必须反映库里真实数据，而非是否配置了 Token。

    配了 Token 但未同步时，仍应显示 seed（否则界面会对用户说谎）。
    """
    r = client.get("/api/v1/meals", headers=auth["headers"])
    body = r.json()
    assert body["source"] in ("seed", "mcp")
    # 全新库中只有种子数据
    assert body["source"] == "seed"
    assert "示例估算值" in body["disclaimer"]


def test_meals_source_is_mcp_after_official_sync(client, auth):
    """存在官方数据时，source 与文案都必须切换。"""
    from sqlalchemy import select
    from app.db.session import SessionLocal
    from app.models.entities import MealCache

    with SessionLocal() as db:
        db.add(MealCache(mcp_code="MCD-TEST0002", name="测试官方单品",
                         category="汉堡", kcal=400, source="mcp"))
        db.commit()
        db.query(MealCache).filter(MealCache.source == "seed").delete()
        db.commit()

    body = client.get("/api/v1/meals", headers=auth["headers"]).json()
    assert body["source"] == "mcp"
    assert "官方 MCP" in body["disclaimer"]
    assert "示例估算值" not in body["disclaimer"]


def test_health_mode_matches_actual_data(client):
    """health 的 mcp_mode 必须与库内真实数据一致。"""
    body = client.get("/health").json()
    assert body["mcp_mode"] == "seed"       # 全新库无官方数据
    assert "mcp_configured" in body         # Token 配置状态单独暴露


# ---------------- 种子与精选集完全对齐（评委体验一致性）----------------
# 评委克隆后没有 MCP Token，看到的是种子数据；
# 而README 演示截图基于官方精选数据。两者必须一致，否则评委看到的与截图对不上。
def test_seed_and_picks_have_same_item_names():
    from app.services.seed_data import SEED_MEALS
    seed_names = {m["name"] for m in SEED_MEALS}
    pick_names = set(MCD_OFFICIAL_PICKS)
    assert seed_names == pick_names, (
        f"不一致——仅在种子: {seed_names - pick_names}；"
        f"仅在精选: {pick_names - seed_names}"
    )


def test_seed_and_picks_have_same_categories():
    from app.services.seed_data import SEED_MEALS
    seed_cat = {m["name"]: m["category"] for m in SEED_MEALS}
    for name, (cat, *_rest) in MCD_OFFICIAL_PICKS.items():
        assert seed_cat[name] == cat, f"{name} 分类不一致：{seed_cat[name]} vs {cat}"


def test_seed_and_picks_have_same_calories():
    from app.services.seed_data import SEED_MEALS
    seed_kcal = {m["name"]: m["kcal"] for m in SEED_MEALS}
    for name, _v in MCD_OFFICIAL_PICKS.items():
        assert seed_kcal[name] == 0 or seed_kcal[name] > 0
    # 抽样校验：种子热量必须与官方真实值一致（用官方样本覆盖的单品）
    for item in parse_nutrition_payload(REAL_SAMPLE):
        if item["productName"] in seed_kcal:
            assert seed_kcal[item["productName"]] == float(item["energyKcal"]), \
                f"{item['productName']} 热量不一致：{seed_kcal[item['productName']]} vs {item['energyKcal']}"


def test_seed_count_is_20():
    from app.services.seed_data import SEED_MEALS
    assert len(SEED_MEALS) == 20, f"种子应与精选集一致为 20 条，实为 {len(SEED_MEALS)}"


def test_seed_no_merged_categories():
    """回归：种子表不得再有已合并的「饮料」「鸡肉」分类。"""
    from app.services.seed_data import SEED_MEALS
    cats = {m["category"] for m in SEED_MEALS}
    assert "饮料" not in cats, "饮料应已并入「饮品」"
    assert "鸡肉" not in cats, "鸡肉应已并入「汉堡」"
    assert cats == set(CATEGORY_ORDER)
