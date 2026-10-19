"""贴纸与分享海报接口。

合规：贴纸为项目内自绘 SVG 简笔图标，严禁官方 Logo / 实拍图；
海报默认脱敏（不含体重、TDEE 等身体原始数据）。
"""
from __future__ import annotations

import hashlib

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.core.deps import CurrentUser, DbSession
from app.models.entities import DailyCheckin, OrderRecord

router = APIRouter(prefix="/sticker", tags=["贴纸海报"])


class PreviewIn(BaseModel):
    meals: list[dict] = Field(default_factory=list, description="[{category,name}] 即可")
    status: str = Field("达标", pattern="^(达标|维持|超标)$")
    kcal: int = 0
    date_str: str | None = None


def sticker_fingerprint(meals: list[dict]) -> str:
    payload = "|".join(sorted(f"{m.get('code') or m.get('name')}{m.get('category')}"
                              for m in meals))
    return hashlib.sha256(payload.encode()).hexdigest()[:12]


@router.post("/preview", summary="贴纸实时预览（不落库）")
def preview(payload: PreviewIn) -> dict:
    from datetime import UTC, datetime
    from app.api.v1.checkin import build_sticker_svg

    svg = build_sticker_svg(payload.meals, payload.status, payload.kcal,
                            payload.date_str or datetime.now(UTC).date().isoformat())
    return {"svg": svg, "fingerprint": sticker_fingerprint(payload.meals)}


@router.get("/latest", summary="最近一次打卡贴纸")
def latest(db: DbSession, user: CurrentUser) -> dict:
    rec = db.scalar(
        select(DailyCheckin).where(DailyCheckin.user_id == user.id)
        .order_by(DailyCheckin.checkin_date.desc())
    )
    if rec is None:
        raise HTTPException(status_code=404, detail="还没有打卡记录，先去完成今天的一餐吧")
    return {"id": rec.id, "date": rec.checkin_date.isoformat(), "status": rec.status,
            "svg": rec.sticker_svg or "", "note": rec.note}


@router.get("/poster", summary="今日分享海报数据（脱敏）")
def poster(db: DbSession, user: CurrentUser) -> dict:
    """返回可直接喂给前端 canvas/海报组件的结构化数据。

    脱敏口径：仅暴露餐品名称、热量、运动换算；不返回体重、身高、TDEE。
    """
    from datetime import UTC, datetime
    from app.services import exercise as exercise_svc

    today = datetime.now(UTC).date()
    rec = db.scalar(select(DailyCheckin).where(
        DailyCheckin.user_id == user.id, DailyCheckin.checkin_date == today))
    if rec is None:
        raise HTTPException(status_code=404, detail="今日尚未打卡")

    orders = db.scalars(select(OrderRecord).where(
        OrderRecord.user_id == user.id,
        OrderRecord.created_at >= datetime.combine(today, datetime.min.time()).replace(tzinfo=UTC),
    )).all()

    # 餐品优先取打卡时保存的快照（与贴纸展示完全一致），
    # 打卡记录缺失时才回退到当日订单快照
    meals: list[dict] = list(rec.meals or [])
    if not meals:
        for o in orders:
            meals.extend(o.meal_snapshot or [])

    # 运动换算文案来自已存记录，避免海报接口需要读身体数据
    eq = None
    for o in orders:
        if o.exercise_equivalent:
            eq = o.exercise_equivalent
            break
    if eq is None and rec.exercise_equivalent:
        eq = rec.exercise_equivalent

    return {
        "date": today.isoformat(),
        "status": rec.status,
        "stamp": {"达标": "麦门减脂自律先锋印", "维持": "麦门日常平衡章",
                  "超标": "麦门弹性平衡章"}.get(rec.status, ""),
        "total_kcal": round(rec.total_kcal),
        "protein_g": round(rec.protein_g, 1),
        "items": [{"name": m.get("name"), "category": m.get("category"),
                   "kcal": round(m.get("kcal", 0))} for m in meals],
        "exercise_equivalent": eq,
        "slogan": ("今天也是自律的一天，麦当劳也能吃出掌控感 🍔"
                   if rec.status == "达标"
                   else "小波动不影响大局，继续保持节奏 💪"),
        "watermark": "本图不含身体原始数据 · 数据仅供参考，非医疗建议",
        "svg": rec.sticker_svg or "",
    }


@router.get("/stats", summary="打卡统计（连续天数/累计）")
def stats(db: DbSession, user: CurrentUser) -> dict:
    from datetime import timedelta
    recs = db.scalars(select(DailyCheckin).where(
        DailyCheckin.user_id == user.id).order_by(DailyCheckin.checkin_date.desc())).all()
    if not recs:
        return {"total_days": 0, "streak": 0, "best_streak": 0,
                "done_ratio": 0, "latest_date": None}

    dates = [r.checkin_date for r in recs]
    today = dates[0]

    streak = 1
    for prev, cur in zip(dates, dates[1:]):
        if prev - cur == timedelta(days=1):
            streak += 1
        else:
            break

    best, run = 1, 1
    for prev, cur in zip(dates, dates[1:]):
        run = run + 1 if prev - cur == timedelta(days=1) else 1
        best = max(best, run)

    return {
        "total_days": len(recs),
        "streak": streak,
        "best_streak": best,
        "done_ratio": round(sum(1 for r in recs if r.status == "达标") / len(recs) * 100),
        "latest_date": today.isoformat(),
    }