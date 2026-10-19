"""认证相关 Pydantic 模型。"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

USERNAME_RE = r"^[a-zA-Z0-9_一-龥]{3,30}$"


class UserRegisterIn(BaseModel):
    username: str = Field(..., min_length=3, max_length=30, pattern=USERNAME_RE,
                           description="3-30位字母/数字/下划线/中文")
    password: str = Field(..., min_length=8, max_length=72,
                          description="8-72位，至少含字母和数字")
    email: EmailStr | None = None

    @field_validator("password")
    @classmethod
    def _pwd_strength(cls, v: str) -> str:
        if not any(c.isalpha() for c in v) or not any(c.isdigit() for c in v):
            raise ValueError("密码必须同时包含字母和数字")
        return v


class UserLoginIn(BaseModel):
    username: str
    password: str


class RefreshIn(BaseModel):
    refresh_token: str


class ChangePasswordIn(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=8, max_length=72)


class UserOut(BaseModel):
    id: int
    username: str
    email: str | None
    role: str
    provider: str
    created_at: datetime
    last_login_at: datetime | None

    model_config = {"from_attributes": True}


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut