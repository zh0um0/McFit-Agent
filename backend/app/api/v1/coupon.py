"""卡券管理：本地示例券 + MCP live 拉取。"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.core.config import settings
from app.core.deps import CurrentUser, DbSession
from app.models.entities import CouponSnapshot

router = APIRouter(prefix="/coupons", tags=["优惠券"])


@router.get("", summary="我的可用卡券")
def my_coupons(db: DbSession, user: CurrentUser) -> dict:
    from app.services.seed_data import SEED_COUPONS
    from app.services import pricing

    today = datetime.now(UTC).date()
    rows = db.scalars(
        select(CouponSnapshot).where(
            CouponSnapshot.user_id == user.id,
            CouponSnapshot.used.is_(False),
            (CouponSnapshot.expires_at.is_(None)) | (CouponSnapshot.expires_at >= today),
        ).order_by(CouponSnapshot.threshold)
    ).all()

    if rows:
        items = [{
            "code": r.coupon_code, "title": r.title, "threshold": r.threshold,
            "discount": r.discount, "expires_at": r.expires_at, "source": "mcp",
        } for r in rows]
        mode = "user"
    else:
        # 未配置 MCP Token 或未领券：给示例券，保证凑单算法可演示
        items = [{
            "code": c["coupon_code"], "title": c["title"], "threshold": c["threshold"],
            "discount": c["discount"],
            "expires_at": today + timedelta(days=7), "source": "seed",
        } for c in SEED_COUPONS]
        mode = "seed"

    usable = pricing.coupons_from_rows(items)
    return {
        "items": items,
        "mode": mode,
        "disclaimer": "示例券仅用于演示凑单算法；真实卡券以麦当劳官方 App 卡包为准。",
    }


@router.post("/bind", summary="手动绑定/导入卡券（离线演示用）")
def bind_coupon(payload: dict, db: DbSession, user: CurrentUser) -> dict:
    code = (payload.get("code") or "").strip()
    title = (payload.get("title") or "").strip()
    if not code or not title:
        raise HTTPException(status_code=400, detail="code 与 title 必填")
    db.add(CouponSnapshot(
        user_id=user.id, coupon_code=code, title=title,
        threshold=float(payload.get("threshold") or 0),
        discount=float(payload.get("discount") or 0),
        rule=payload.get("rule") or {},
    ))
    db.commit()
    return {"ok": True, "message": f"已绑定卡券 {title}"}


@router.post("/auto-bind", summary="一键领券（配置 MCP Token 后为真实调用）")
def auto_bind(db: DbSession, user: CurrentUser) -> dict:
    if not settings.mcp_token:
        return {
            "ok": False, "mode": "seed",
            "message": "未配置 MCP_TOKEN，无法调用官方 auto-bind-coupons；当前使用示例卡券演示。",
            "hint": "在 backend/.env 写入 MCP_TOKEN=你的Token 后重启即可联动官方接口。",
        }
    from app.services.mcp_client import call_tool
    try:
        data = call_tool("auto-bind-coupons", {})
    except Exception as exc:                # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"官方 MCP 调用失败：{exc}") from exc
    return {"ok": True, "mode": "live", "data": data}


@router.post("/sync-nutrition", summary="从官方 MCP 同步营养数据（每类精选 5 个）")
def sync_nutrition(db: DbSession, user: CurrentUser) -> dict:
    """从官方 list-nutrition-foods 拉取 160 条全量，按精选集落库 25 条。

    需管理员权限，且需配置 MCP_TOKEN。
    """
    if not settings.mcp_token:
        raise HTTPException(
            status_code=400,
            detail="未配置 MCP_TOKEN。官方营养数据需真实 Token；未配置时继续使用内置种子数据。",
        )
    from app.services.mcp_client import McpError, sync_meals_to_cache

    try:
        return sync_meals_to_cache(db, picked_only=settings.mcd_picked_only)
    except McpError as exc:
        raise HTTPException(status_code=502, detail=f"官方 MCP 同步失败：{exc}") from exc
    except Exception as exc:                 # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"同步过程异常：{exc}") from exc