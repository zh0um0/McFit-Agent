"""FastAPI 依赖：当前用户鉴权。"""
from __future__ import annotations

from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.db.session import get_db
from app.models.entities import User

bearer_scheme = HTTPBearer(auto_error=False, description="Bearer <access_token>")

_UNAUTH = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="登录状态无效或已过期，请重新登录",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    if creds is None:
        raise _UNAUTH
    try:
        payload = decode_token(creds.credentials, "access")
    except jwt.PyJWTError:
        raise _UNAUTH from None

    user = db.get(User, int(payload["sub"]))
    if user is None or not user.is_active:
        raise _UNAUTH
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
DbSession = Annotated[Session, Depends(get_db)]


def require_admin(user: CurrentUser) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return user