"""认证路由：注册 / 登录 / 刷新 / 当前用户 / 改密 / 登出。

预留第三方登录：User.provider / provider_id 字段已就位，
接入 OAuth 时只需新增 /auth/oauth/{provider} 回调分支，无需改表。
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import or_, select

from app.core.config import settings
from app.core.deps import CurrentUser, DbSession
from app.core.security import (
    create_access_token, create_refresh_token, decode_token, hash_password, verify_password,
)
from app.models.entities import User
from app.schemas.auth import (
    ChangePasswordIn, RefreshIn, TokenPair, UserLoginIn, UserOut, UserRegisterIn,
)

router = APIRouter(prefix="/auth", tags=["认证"])

MAX_FAILED = 5
LOCK_MINUTES = 15


def _issue(user: User) -> TokenPair:
    return TokenPair(
        access_token=create_access_token(user.id, user.username, user.role),
        refresh_token=create_refresh_token(user.id),
        expires_in=settings.access_token_expire_minutes * 60,
        user=UserOut.model_validate(user),
    )


@router.post("/register", response_model=TokenPair, status_code=201, summary="注册并直接登录")
def register(payload: UserRegisterIn, db: DbSession) -> TokenPair:
    # 逐字段独立查重：不可写成 or_(username==X, email==Y) 的单条查询——
    # 当 Y 为 None 时 SQLAlchemy 会生成 `email IS NULL`，从而匹配到任意一个
    # 未填邮箱的存量用户，导致「从没填过邮箱」的新用户被误判「邮箱已注册」。
    if db.scalar(select(User).where(User.username == payload.username)):
        raise HTTPException(status_code=409, detail="该用户名已被注册")
    if payload.email and db.scalar(select(User).where(User.email == payload.email)):
        raise HTTPException(status_code=409, detail="该邮箱已被注册")

    user = User(
        username=payload.username,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role="user",
        provider="local",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _issue(user)


@router.post("/login", response_model=TokenPair, summary="登录")
def login(payload: UserLoginIn, db: DbSession) -> TokenPair:
    # 支持用「用户名或邮箱」登录。用户名本身不为空，故两侧都可安全比较
    #（不会出现 IS NULL 误匹配）。
    user = db.scalar(
        select(User).where(
            or_(User.username == payload.username, User.email == payload.username)
        )
    )
    # 统一文案，不暴露「用户名是否存在」
    bad = HTTPException(status_code=401, detail="用户名或密码错误")
    if user is None:
        raise bad

    if user.locked_until and user.locked_until.replace(tzinfo=UTC) > datetime.now(UTC):
        raise HTTPException(status_code=423, detail=f"账号已锁定，请 {LOCK_MINUTES} 分钟后再试")

    if not verify_password(payload.password, user.password_hash):
        user.failed_attempts += 1
        if user.failed_attempts >= MAX_FAILED:
            user.locked_until = datetime.now(UTC) + timedelta(minutes=LOCK_MINUTES)
            user.failed_attempts = 0
        db.commit()
        raise bad

    if not user.is_active:
        raise HTTPException(status_code=403, detail="账号已被停用")

    user.failed_attempts = 0
    user.locked_until = None
    user.last_login_at = datetime.now(UTC)
    db.commit()
    db.refresh(user)
    return _issue(user)


@router.post("/refresh", response_model=TokenPair, summary="用refresh 换新 access")
def refresh(payload: RefreshIn, db: DbSession) -> TokenPair:
    try:
        data = decode_token(payload.refresh_token, "refresh")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="refresh token 无效或已过期") from None

    user = db.get(User, int(data["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="用户不存在")
    return _issue(user)


@router.get("/me", response_model=UserOut, summary="当前登录用户")
def me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)


@router.post("/change-password", summary="修改密码")
def change_password(payload: ChangePasswordIn, user: CurrentUser, db: DbSession) -> dict:
    if not verify_password(payload.old_password, user.password_hash):
        raise HTTPException(status_code=400, detail="原密码不正确")
    if verify_password(payload.new_password, user.password_hash):
        raise HTTPException(status_code=400, detail="新密码不能与原密码相同")
    user.password_hash = hash_password(payload.new_password)
    db.commit()
    return {"ok": True, "message": "密码已更新，请重新登录"}


@router.post("/logout", status_code=status.HTTP_200_OK, summary="登出")
def logout(user: CurrentUser) -> dict:
    """JWT 无状态，服务端不存 token；客户端删除即可。
    此端点用于前端统一调用链与埋点。"""
    return {"ok": True, "message": "已登出"}


@router.get("/oauth-providers", summary="已启用的第三方登录方式（预留）")
def oauth_providers() -> dict:
    return {"providers": [], "note": "本期仅本地密码登录，OAuth 接口位已预留"}