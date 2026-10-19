"""全部 ORM 模型（8 张表）。

敏感字段策略：weight_kg / daily_calorie_target / tdee 用 Fernet 加密后落库为
Text（EncryptedString 类型），满足「敏感字段加密」要求；密钥走环境变量。
"""
from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import (
    Boolean, Date, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

CHECKIN_DONE = "达标"
CHECKIN_KEEP = "维持"
CHECKIN_OVER = "超标"


def _now() -> datetime:
    return datetime.now(UTC)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    email: Mapped[str | None] = mapped_column(String(120), unique=True, index=True, nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="user")   # user | admin
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # 预留第三方登录：目前仅本地密码，OAuth 落地时写 provider + provider_id
    provider: Mapped[str | None] = mapped_column(String(30), default="local", nullable=True)
    provider_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    # 登录失败计数与锁定时间（防暴力破解）
    failed_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    profile: Mapped["UserProfile | None"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    orders: Mapped[list["OrderRecord"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    checkins: Mapped[list["DailyCheckin"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class UserProfile(Base):
    """身材档案 —— 减脂期敏感数据，weight/target/tdee 加密落库。"""
    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)

    gender: Mapped[str] = mapped_column(String(10))                   # male | female
    age: Mapped[int] = mapped_column(Integer)
    height_cm: Mapped[float] = mapped_column()
    weight_kg_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    activity_level: Mapped[str] = mapped_column(String(20), default="sedentary")
    goal: Mapped[str] = mapped_column(String(20), default="cut")       # cut | keep | lean_bulk
    target_weight_kg_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    tdee_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 若用户关闭云同步，此用户所有身体数据仅存本机，接口层据此拒绝跨设备读取
    cloud_sync_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    user: Mapped[User] = relationship(back_populates="profile")


class MealCache(Base):
    """官方 MCP 菜单/营养数据缓存。无 Token 时由种子数据填充。"""
    __tablename__ = "meals_cache"

    id: Mapped[int] = mapped_column(primary_key=True)
    mcp_code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    category: Mapped[str] = mapped_column(String(50), default="其他")
    kcal: Mapped[float] = mapped_column(default=0)
    protein_g: Mapped[float] = mapped_column(default=0)
    fat_g: Mapped[float] = mapped_column(default=0)
    carb_g: Mapped[float] = mapped_column(default=0)
    sodium_mg: Mapped[float] = mapped_column(default=0)
    price: Mapped[float] = mapped_column(default=0)
    is_high_protein: Mapped[bool] = mapped_column(Boolean, default=False)
    is_fried: Mapped[bool] = mapped_column(Boolean, default=False)
    source: Mapped[str] = mapped_column(String(20), default="seed")     # seed | mcp
    synced_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class OrderRecord(Base):
    """一次点餐记录（勾选组合的快照）。"""
    __tablename__ = "order_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    meal_snapshot: Mapped[list] = mapped_column(JSON)                  # [{code,name,kcal,...}]
    total_kcal: Mapped[float] = mapped_column(default=0)
    total_protein_g: Mapped[float] = mapped_column(default=0)
    total_fat_g: Mapped[float] = mapped_column(default=0)
    total_price: Mapped[float] = mapped_column(default=0)
    coupon_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    saving_amount: Mapped[float] = mapped_column(default=0)
    status: Mapped[str] = mapped_column(String(20), default="达标")
    exercise_equivalent: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now, index=True)

    user: Mapped[User] = relationship(back_populates="orders")


class DailyCheckin(Base):
    """每日打卡 —— 日历看板数据源，(user_id, date) 唯一。"""
    __tablename__ = "daily_checkins"
    __table_args__ = (UniqueConstraint("user_id", "checkin_date", name="uq_user_date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    checkin_date: Mapped[date] = mapped_column(Date, index=True)
    status: Mapped[str] = mapped_column(String(10), default=CHECKIN_KEEP)
    total_kcal: Mapped[float] = mapped_column(default=0)
    protein_g: Mapped[float] = mapped_column(default=0)
    # 当天实际点单的餐品快照 [{name,category}]——贴纸与日历都基于它，
    # 保证贴纸展示内容与本次点单完全吻合
    meals: Mapped[list | None] = mapped_column(JSON, nullable=True)
    sticker_svg: Mapped[str | None] = mapped_column(Text, nullable=True)   # 自绘 SVG 组合结果
    exercise_equivalent: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    note: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    user: Mapped[User] = relationship(back_populates="checkins")


class CouponSnapshot(Base):
    """从 MCP 拉取到的用户卡券快照（token 不落库）。"""
    __tablename__ = "coupon_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    coupon_code: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(120))
    rule: Mapped[dict] = mapped_column(JSON, default=dict)   # {type,threshold,amount,applies_to}
    threshold: Mapped[float] = mapped_column(default=0)
    discount: Mapped[float] = mapped_column(default=0)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    expires_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    used: Mapped[bool] = mapped_column(Boolean, default=False)


class UserCoupon(Base):
    """用户↔卡券绑定（预留多卡包/转赠，P1 起可用）。"""
    __tablename__ = "user_coupons"
    __table_args__ = (UniqueConstraint("user_id", "coupon_code", name="uq_user_coupon"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    coupon_code: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(20), default="unused")   # unused | used | expired
    used_order_id: Mapped[int | None] = mapped_column(
        ForeignKey("order_records.id", ondelete="SET NULL"), nullable=True
    )
    acquired_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class ExercisePreset(Base):
    """运动代偿换算参数（慢跑/跳绳/俯卧撑等），支持后台调整。"""
    __tablename__ = "exercise_presets"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True)
    name: Mapped[str] = mapped_column(String(60))
    unit: Mapped[str] = mapped_column(String(20))            # km | minute | rep | step
    factor: Mapped[float] = mapped_column()                 # 消耗系数
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)