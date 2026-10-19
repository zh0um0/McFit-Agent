"""身材档案与 TDEE 指标。"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.crypto import decrypt_float, encrypt
from app.core.deps import CurrentUser, DbSession
from app.models.entities import UserProfile
from app.services import exercise as exercise_svc
from app.services import tdee as tdee_svc

router = APIRouter(prefix="/profile", tags=["身材档案"])


class ProfileIn(BaseModel):
    gender: str = Field(..., pattern="^(male|female)$")
    age: int = Field(..., ge=1, le=120)
    height_cm: float = Field(..., ge=50, le=250)
    weight_kg: float = Field(..., ge=20, le=400)
    activity_level: str = Field("sedentary",
                                pattern="^(sedentary|light|moderate|active)$")
    goal: str = Field("cut", pattern="^(cut|keep|lean_bulk)$")
    cloud_sync_enabled: bool | None = Field(
        None, description="是否开启云端同步；默认关闭=身体数据仅本地存储")


class ProfileOut(BaseModel):
    gender: str
    age: int
    height_cm: float
    weight_kg: float | None
    activity_level: str
    goal: str
    cloud_sync_enabled: bool
    metrics: dict | None = None


def _to_out(p: UserProfile, with_metrics: bool = True) -> ProfileOut:
    weight = decrypt_float(p.weight_kg_enc)
    metrics = None
    if with_metrics and weight:
        metrics = tdee_svc.compute_profile_metrics(
            weight, p.height_cm, p.age, p.gender, p.activity_level, p.goal
        ).as_dict()
    return ProfileOut(
        gender=p.gender, age=p.age, height_cm=p.height_cm, weight_kg=weight,
        activity_level=p.activity_level, goal=p.goal,
        cloud_sync_enabled=p.cloud_sync_enabled, metrics=metrics,
    )


@router.get("", response_model=ProfileOut, summary="获取我的档案")
def get_profile(user: CurrentUser, db: DbSession) -> ProfileOut:
    p = db.query(UserProfile).filter(UserProfile.user_id == user.id).one_or_none()
    if p is None:
        raise HTTPException(status_code=404, detail="尚未建立身材档案")
    return _to_out(p)


@router.put("", response_model=ProfileOut, summary="创建/更新档案")
def upsert_profile(payload: ProfileIn, user: CurrentUser, db: DbSession) -> ProfileOut:
    # 先算指标，参数非法直接报错（服务层已做边界校验）
    metrics = tdee_svc.compute_profile_metrics(
        payload.weight_kg, payload.height_cm, payload.age, payload.gender,
        payload.activity_level, payload.goal,
    )

    p = db.query(UserProfile).filter(UserProfile.user_id == user.id).one_or_none()
    if p is None:
        p = UserProfile(user_id=user.id)
        db.add(p)

    p.gender = payload.gender
    p.age = payload.age
    p.height_cm = payload.height_cm
    p.weight_kg_enc = encrypt(payload.weight_kg)
    p.activity_level = payload.activity_level
    p.goal = payload.goal
    p.tdee_enc = encrypt(metrics.tdee)
    if payload.cloud_sync_enabled is not None:
        if payload.cloud_sync_enabled and not settings.cloud_sync_enabled:
            raise HTTPException(
                status_code=400,
                detail="服务端未开启云同步能力，身体数据仍仅本地存储（符合隐私口径）",
            )
        p.cloud_sync_enabled = payload.cloud_sync_enabled

    db.commit()
    db.refresh(p)
    return _to_out(p)


@router.delete("", summary="删除档案")
def delete_profile(user: CurrentUser, db: DbSession) -> dict:
    p = db.query(UserProfile).filter(UserProfile.user_id == user.id).one_or_none()
    if p:
        db.delete(p)
        db.commit()
    return {"ok": True, "message": "档案已删除"}


@router.get("/options", summary="可选枚举（活动强度/目标/餐段）")
def options() -> dict:
    return {
        "activity_levels": [{"value": k, "label": v[0], "factor": v[1]}
                            for k, v in tdee_svc.ACTIVITY_FACTORS.items()],
        "goals": [{"value": k, "label": v[0], "factor": v[1]} for k, v in tdee_svc.GOALS.items()],
        "meals": list(tdee_svc.MEAL_RATIO.keys()),
        "genders": [{"value": "male", "label": "男"}, {"value": "female", "label": "女"}],
    }


@router.get("/exercise-equivalent", summary="热量→运动代偿换算（正向激励文案）")
def equivalent(kcal: float, weight_kg: float, limit_kcal: float | None = None) -> dict:
    if weight_kg <= 0:
        raise HTTPException(status_code=400, detail="请先在档案中填写体重")
    if limit_kcal:
        return exercise_svc.narrate(kcal, limit_kcal, weight_kg)
    return exercise_svc.suggestion_for_gap(kcal, weight_kg)