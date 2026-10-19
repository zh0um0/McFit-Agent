"""打卡日历 + 自绘 SVG 贴纸。

合规：贴纸为项目内自绘线条简笔图标，严禁官方 Logo / 实拍图 / 官方物料
（PRD v1.1 硬性要求）。引擎实现见 `app/services/sticker_engine.py`。
"""
from __future__ import annotations

from datetime import UTC, date, datetime

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.core.deps import CurrentUser, DbSession
from app.models.entities import CHECKIN_DONE, CHECKIN_KEEP, CHECKIN_OVER, DailyCheckin
from app.services.sticker_engine import build_sticker_svg, sticker_fingerprint

router = APIRouter(prefix="/checkin", tags=["打卡与贴纸"])


class CheckinIn(BaseModel):
    status: str = Field(..., pattern="^(达标|维持|超标)$")
    total_kcal: float = 0
    protein_g: float = 0
    meals: list[dict] = Field(default_factory=list)
    note: str | None = Field(None, max_length=200)


@router.post("", status_code=201, summary="打卡（当日覆盖）")
def checkin(payload: CheckinIn, db: DbSession, user: CurrentUser) -> dict:
    today = datetime.now(UTC).date()

    # 只保留商品名与类别 —— 贴纸与日历展示以此为准，
    # 必须是本次真实点单的餐品，不能用类别概括
    meals = []
    for m in payload.meals or []:
        nm = str((m or {}).get("name") or "").strip()
        if not nm:
            continue
        meals.append({"name": nm, "category": str((m or {}).get("category") or "")})

    sticker = build_sticker_svg(meals, payload.status,
                               round(payload.total_kcal), today.isoformat())

    # 落库的meals 与贴纸展示保持一致（同款只留一个），
    # 否则日历格会出现两个同名条目，与贴纸对不上
    seen: set[str] = set()
    shown = []
    for m in meals:
        if m["name"] in seen:
            continue
        seen.add(m["name"])
        shown.append(m)

    rec = db.scalar(select(DailyCheckin).where(
        DailyCheckin.user_id == user.id, DailyCheckin.checkin_date == today))
    if rec is None:
        rec = DailyCheckin(user_id=user.id, checkin_date=today)
        db.add(rec)
    rec.status = payload.status
    rec.total_kcal = payload.total_kcal
    rec.protein_g = payload.protein_g
    rec.meals = shown
    rec.sticker_svg = sticker
    rec.note = payload.note
    db.commit()
    db.refresh(rec)
    return {
        "id": rec.id, "date": today.isoformat(), "status": rec.status,
        "stamp": {"达标": "麦门减脂自律先锋印", "维持": "麦门日常平衡章",
                  "超标": "麦门弹性平衡章"}.get(rec.status, ""),
        "sticker_length": len(sticker),
        "items": [m["name"] for m in shown],
        # 超出贴纸最多 4 个图标的部分
        "overflow": max(len(shown) - 4, 0),
    }


@router.get("/calendar", summary="月度打卡日历")
def calendar(db: DbSession, user: CurrentUser,
             month: str = Query(..., pattern=r"^\d{4}-\d{2}$", description="YYYY-MM")) -> dict:
    year, mon = (int(x) for x in month.split("-"))
    first = date(year, mon, 1)
    last = date(year + (mon == 12), mon % 12 + 1, 1)

    recs = db.scalars(select(DailyCheckin).where(
        DailyCheckin.user_id == user.id,
        DailyCheckin.checkin_date >= first,
        DailyCheckin.checkin_date < last,
    )).all()
    by_day = {r.checkin_date.day: r for r in recs}

    import calendar as cal
    n_days = cal.monthrange(year, mon)[1]
    cells = []
    for d in range(1, n_days + 1):
        r = by_day.get(d)
        items = (r.meals if r and r.meals else []) or []
        cells.append({
            "day": d, "date": f"{year:04d}-{mon:02d}-{d:02d}",
            "status": r.status if r else None,
            "kcal": round(r.total_kcal) if r else None,
            "has_sticker": bool(r and r.sticker_svg),
            # 真实点单餐品名，供日历格展示——必须是商品名而非类别
            "items": [str(i.get("name")) for i in items if isinstance(i, dict) and i.get("name")],
        })

    checked = len(recs)
    return {
        "month": month, "days": n_days,
        "first_weekday": cal.monthrange(year, mon)[0],   # 0=周一
        "cells": cells,
        "summary": {
            "checked_days": checked,
            "done": sum(1 for r in recs if r.status == CHECKIN_DONE),
            "keep": sum(1 for r in recs if r.status == CHECKIN_KEEP),
            "over": sum(1 for r in recs if r.status == CHECKIN_OVER),
            "avg_kcal": round(sum(r.total_kcal for r in recs) / checked) if checked else 0,
        },
    }


@router.get("/{checkin_id}/sticker", summary="取贴纸 SVG（脱敏，不含体重/TDEE）")
def sticker_svg(checkin_id: int, db: DbSession, user: CurrentUser) -> dict:
    rec = db.scalar(select(DailyCheckin).where(
        DailyCheckin.id == checkin_id, DailyCheckin.user_id == user.id))
    if rec is None:
        raise HTTPException(status_code=404, detail="打卡记录不存在")
    return {
        "date": rec.checkin_date.isoformat(), "status": rec.status,
        "svg": rec.sticker_svg or "",
        "privacy": "海报默认脱敏：不含体重、TDEE 等身体原始数据",
    }