"""API v1 路由聚合。"""
from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import auth, checkin, coupon, meals, orders, profile, sticker

router = APIRouter()

router.include_router(auth.router)
router.include_router(profile.router)
router.include_router(meals.router)
router.include_router(coupon.router)
router.include_router(orders.router)
router.include_router(checkin.router)
router.include_router(sticker.router)