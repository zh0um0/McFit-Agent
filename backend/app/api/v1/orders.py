"""点餐记录（勾选组合存档）。"""
from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.core.crypto import decrypt_float
from app.core.deps import CurrentUser, DbSession
from app.models.entities import MealCache, OrderRecord, UserProfile
from app.services import exercise as exercise_svc
from app.services import tdee as tdee_svc

router = APIRouter(prefix="/orders", tags=["点餐记录"])


class OrderIn(BaseModel):
    codes: list[str] = Field(..., min_length=1)
    coupon_code: str | None = None
    final_price: float | None = None
    saving_amount: float = 0.0
    meal_name: str = "午餐"


def _weight_of(db, user_id: int) -> float:
    p = db.scalar(select(UserProfile).where(UserProfile.user_id == user_id))
    w = decrypt_float(p.weight_kg_enc) if p else None
    return w or 65.0     # 无档案时用默认体重，保证接口不 500


@router.post("", status_code=201, summary="保存一餐记录")
def create_order(payload: OrderIn, db: DbSession, user: CurrentUser) -> dict:
    by_code = {m.mcp_code: m for m in db.scalars(select(MealCache))}
    meals = []
    for c in payload.codes:
        m = by_code.get(c)
        if m:
            meals.append({"code": m.mcp_code, "name": m.name, "category": m.category,
                          "kcal": m.kcal, "protein_g": m.protein_g, "fat_g": m.fat_g,
                          "carb_g": m.carb_g, "price": m.price})
    if not meals:
        raise HTTPException(status_code=400, detail="所选单品不存在")

    total_kcal = sum(m["kcal"] for m in meals)
    total_protein = sum(m["protein_g"] for m in meals)
    total_fat = sum(m["fat_g"] for m in meals)
    subtotal = sum(m["price"] for m in meals)
    price = payload.final_price if payload.final_price is not None else subtotal

    # 档案缺失时只算热量不生成代偿文案，避免误导
    p = db.scalar(select(UserProfile).where(UserProfile.user_id == user.id))
    if p:
        weight = decrypt_float(p.weight_kg_enc) or 65.0
        metrics = tdee_svc.compute_profile_metrics(
            weight, p.height_cm, p.age, p.gender, p.activity_level, p.goal)
        limit = metrics.meal_limit.get(payload.meal_name) \
            or tdee_svc.meal_limit_of(metrics.daily_target, payload.meal_name)
        status = tdee_svc.evaluate_meal_status(total_kcal, limit)
        equivalent = exercise_svc.narrate(total_kcal, limit, weight)
    else:
        status = "维持"
        equivalent = None

    rec = OrderRecord(
        user_id=user.id, meal_snapshot=meals,
        total_kcal=total_kcal, total_protein_g=total_protein, total_fat_g=total_fat,
        total_price=price, coupon_code=payload.coupon_code,
        saving_amount=payload.saving_amount, status=status,
        exercise_equivalent=equivalent,
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)

    return {
        "id": rec.id, "status": status, "total_kcal": round(total_kcal),
        "total_protein_g": round(total_protein, 1), "final_price": round(price, 2),
        "exercise_equivalent": equivalent,
        "created_at": rec.created_at.isoformat(),
    }


@router.get("", summary="我的点餐历史")
def list_orders(
    db: DbSession, user: CurrentUser,
    limit: int = Query(30, ge=1, le=200),
) -> dict:
    # 只查自己的数据：user_id 由 token 决定，无法越权
    recs = db.scalars(
        select(OrderRecord).where(OrderRecord.user_id == user.id)
        .order_by(OrderRecord.created_at.desc()).limit(limit)
    ).all()
    today = datetime.now(UTC).date()
    return {
        "items": [{
            "id": r.id,
            "date": r.created_at.date().isoformat(),
            "is_today": r.created_at.date() == today,
            "meals": r.meal_snapshot,
            "total_kcal": round(r.total_kcal), "total_protein_g": round(r.total_protein_g, 1),
            "total_price": round(r.total_price, 2), "saving_amount": round(r.saving_amount, 2),
            "coupon_code": r.coupon_code, "status": r.status,
            "exercise_equivalent": r.exercise_equivalent,
        } for r in recs],
        "count": len(recs),
    }


@router.get("/today-summary", summary="今日摄入汇总（打卡页用）")
def today_summary(db: DbSession, user: CurrentUser) -> dict:
    today = datetime.now(UTC).date()
    recs = db.scalars(
        select(OrderRecord).where(
            OrderRecord.user_id == user.id,
            OrderRecord.created_at >= datetime.combine(today, datetime.min.time()).replace(tzinfo=UTC),
        )
    ).all()

    kcal = sum(r.total_kcal for r in recs)
    protein = sum(r.total_protein_g for r in recs)
    price = sum(r.total_price for r in recs)
    saving = sum(r.saving_amount for r in recs)

    p = db.scalar(select(UserProfile).where(UserProfile.user_id == user.id))
    payload: dict = {
        "date": today.isoformat(), "order_count": len(recs),
        "total_kcal": round(kcal), "total_protein_g": round(protein, 1),
        "total_price": round(price, 2), "total_saving": round(saving, 2),
        "has_profile": p is not None,
    }
    if p:
        weight = decrypt_float(p.weight_kg_enc) or 65.0
        metrics = tdee_svc.compute_profile_metrics(
            weight, p.height_cm, p.age, p.gender, p.activity_level, p.goal)
        # 传入真实差额（正=未吃满/ 负=超出），不可用 max(...,0) 截断，
        # 否则超出部分会被抹成 0，超标建议永远显示不出来
        gap = metrics.daily_target - kcal
        payload.update({
            "daily_target": round(metrics.daily_target),
            "protein_target": [round(metrics.protein_min_g), round(metrics.protein_max_g)],
            "status": tdee_svc.checkin_status(kcal, metrics.daily_target),
            "gap_kcal": round(gap),
            "exercise": exercise_svc.suggestion_for_gap(gap, weight),
        })
    return payload


@router.delete("/{order_id}", summary="删除记录")
def delete_order(order_id: int, db: DbSession, user: CurrentUser) -> dict:
    rec = db.scalar(
        select(OrderRecord).where(OrderRecord.id == order_id, OrderRecord.user_id == user.id)
    )
    if rec is None:
        raise HTTPException(status_code=404, detail="记录不存在")
    db.delete(rec)
    db.commit()
    return {"ok": True}