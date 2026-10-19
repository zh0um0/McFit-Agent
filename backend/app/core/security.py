"""密码哈希与 JWT 签发校验。"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.core.config import settings

_hasher = PasswordHasher(time_cost=settings.pwd_hash_time_cost)
TokenType = Literal["access", "refresh"]


def hash_password(raw: str) -> str:
    return _hasher.hash(raw)


def verify_password(raw: str, hashed: str) -> bool:
    try:
        _hasher.verify(hashed, raw)
        return True
    except (VerifyMismatchError, ValueError):
        return False


def _create_token(subject: str, token_type: TokenType, expires: timedelta,
                  extra: dict[str, Any] | None = None) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "typ": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + expires).timestamp()),
        "jti": uuid.uuid4().hex,
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_access_token(user_id: int, username: str, role: str) -> str:
    return _create_token(
        str(user_id), "access", timedelta(minutes=settings.access_token_expire_minutes),
        {"username": username, "role": role},
    )


def create_refresh_token(user_id: int) -> str:
    return _create_token(
        str(user_id), "refresh", timedelta(days=settings.refresh_token_expire_days)
    )


def decode_token(token: str, expected: TokenType) -> dict[str, Any]:
    """校验签名与有效期；失败抛 jwt.PyJWTError（由上层转 401）。"""
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    if payload.get("typ") != expected:
        raise jwt.InvalidTokenError("令牌类型不匹配")
    return payload