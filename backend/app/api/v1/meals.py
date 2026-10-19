"""菜单与营养数据（MCP 联动 + 种子降级）。"""
from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.core.config import settings
from app.core.deps import DbSession
from app.models.entities import MealCache
from app.services.mcd_official_data import OFFICIAL_SOURCE_NOTE

router = APIRouter(prefix="/meals", tags=["菜单与营养"])


class PlanRequest(BaseModel):
    codes: list[str] = Field(..., min_length=1, description="已勾选单品编码列表")
    kcal_budget: float | None = None


def _to_dict(m: MealCache) -> dict:
    return {
        "code": m.mcp_code, "name": m.name, "category": m.category,
        "kcal": m.kcal, "protein_g": m.protein_g, "fat_g": m.fat_g,
        "carb_g": m.carb_g, "sodium_mg": m.sodium_mg, "price": m.price,
        "is_high_protein": m.is_high_protein, "is_fried": m.is_fried,
        "source": m.source,
    }


@router.get("", summary="菜单列表（支持分类/高蛋白筛选）")
def list_meals(
    db: DbSession,
    category: str | None = Query(None, description="按分类筛选，如 汉堡/小食/饮料"),
    high_protein: bool | None = Query(None, description="只看高蛋白单品"),
    exclude_fried: bool | None = Query(None, description="排除油炸高脂"),
    keyword: str | None = Query(None, description="名称模糊搜索"),
) -> dict:
    q = select(MealCache)     # 排序在下方按业务分类顺序处理
    if category:
        q = q.where(MealCache.category == category)
    if high_protein:
        q = q.where(MealCache.is_high_protein.is_(True))
    if exclude_fried:
        q = q.where(MealCache.is_fried.is_(False))
    if keyword:
        q = q.where(MealCache.name.contains(keyword))

    items = [_to_dict(m) for m in db.scalars(q)]

    # 分类按业务逻辑排序（主食→小食→甜点→饮品），而非字母序——
    # 字母序会让「小食」排在「汉堡」前面，不符合用户点单的自然顺序
    from app.services.mcd_official_data import CATEGORY_ORDER
    rows = db.scalars(select(MealCache.category).distinct()).all()
    present = {r for r in rows}
    ordered = [c for c in CATEGORY_ORDER if c in present]
    ordered += sorted(r for r in present if r not in CATEGORY_ORDER)
    categories = ordered

    # 菜品按「分类业务顺序 + 类内热量升序」排列，便于从低卡到高卡做取舍
    items = sorted(items, key=lambda m: (
        categories.index(m["category"]) if m["category"] in categories else 99,
        m["kcal"],
    ))

    # 数据来源以「库内实际存的是什么」为准，而非「是否配了Token」——
    # 配了 Token 但还没执行同步时，仍是种子数据，反之亦然。
    has_mcp = db.scalar(select(MealCache).where(MealCache.source == "mcp").limit(1))
    source = "mcp" if has_mcp else "seed"
    disclaimer = (
        OFFICIAL_SOURCE_NOTE if has_mcp
        else "营养数据为示例估算值，仅供参考；实时以官方渠道为准。"
    )
    return {
        "items": items,
        "categories": categories,
        "source": source,
        "disclaimer": disclaimer,
        "synced": bool(settings.mcp_token) and bool(has_mcp),
    }


@router.get("/categories", summary="分类列表")
def categories(db: DbSession) -> dict:
    rows = db.execute(
        select(MealCache.category).distinct().order_by(MealCache.category)
    ).scalars().all()
    return {"categories": list(rows)}


@router.post("/calculate", summary="组合热量/价格试算 + 凑单推荐")
def calculate(payload: PlanRequest, db: DbSession) -> dict:
    from app.services import pricing

    pool = [_to_dict(m) for m in db.scalars(select(MealCache))]
    by_code = {m["code"]: m for m in pool}
    selection = [by_code[c] for c in payload.codes if c in by_code]
    if not selection:
        return {"error": "所选编码不存在，请刷新菜单", "valid": True}

    # 用户卡券：优先真实快照，无则用示例券演示算法
    from app.models.entities import CouponSnapshot
    from datetime import UTC, datetime
    today = datetime.now(UTC).date()
    rows = db.scalars(
        select(CouponSnapshot).where(
            CouponSnapshot.used.is_(False),
            (CouponSnapshot.expires_at.is_(None)) | (CouponSnapshot.expires_at >= today),
        )
    ).all()
    if rows:
        coupons = pricing.coupons_from_rows(rows)
        coupon_src = "user"
    else:
        from app.services.seed_data import SEED_COUPONS
        coupons = pricing.coupons_from_rows(SEED_COUPONS)
        coupon_src = "seed"

    result = pricing.recommend(selection, pool, coupons, payload.kcal_budget)
    result["coupon_source"] = coupon_src
    result["coupons"] = [{"code": c.code, "title": c.title} for c in coupons]
    return result