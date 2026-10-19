"""建表 + 种子数据填充（幂等，可重复执行）。

本期用 create_all 保证「克隆即跑」零配置；Alembic 迁移脚本在
backend/alembic/ 已就绪，需要正式版本化时执行 `alembic revision --autogenerate`。
"""
from __future__ import annotations

import logging

from sqlalchemy import select

from app.db.session import Base, SessionLocal, engine
from app.models import entities  # noqa: F401  确保模型被注册
from app.models.entities import CouponSnapshot, ExercisePreset, MealCache, User
from app.services.exercise import SEED_PRESETS
from app.services.seed_data import SEED_MEALS

logger = logging.getLogger("mcfit.init")

DEMO_USER = {
    "username": "demo",
    "password": "demo123456",
    "email": "demo@mcfit.dev",
}


def _ensure_seed_meals(db) -> int:
    """种子菜单仅在无任何菜单数据时写入，作为无 Token 时的降级兜底。

    一旦官方 MCP 数据已同步（source='mcp'），种子数据必须让位——
    否则界面会同时出现 25 条官方 + 27 条种子，演示时口径混乱。
    """
    has_mcp = db.scalar(select(MealCache).where(MealCache.source == "mcp").limit(1))
    if has_mcp:
        stale = db.query(MealCache).filter(MealCache.source == "seed").delete()
        if stale:
            logger.info("检测到官方 MCP 数据，已清理 %s 条种子菜单", stale)
        return 0

    exists = db.scalar(select(MealCache).limit(1))
    if exists:
        return 0
    for row in SEED_MEALS:
        db.add(MealCache(source="seed", **row))
    return len(SEED_MEALS)


def _ensure_exercise_presets(db) -> int:
    exists = db.scalar(select(ExercisePreset).limit(1))
    if exists:
        return 0
    for code, name, unit, factor, order in SEED_PRESETS:
        db.add(ExercisePreset(code=code, name=name, unit=unit, factor=factor,
                              sort_order=order))
    return len(SEED_PRESETS)


def _ensure_demo_user(db) -> str:
    from app.core.security import hash_password
    if db.scalar(select(User).where(User.username == DEMO_USER["username"])):
        return ""
    db.add(User(
        username=DEMO_USER["username"], email=DEMO_USER["email"],
        password_hash=hash_password(DEMO_USER["password"]),
        role="admin", provider="local",
    ))
    return DEMO_USER["username"]


def _ensure_columns(db) -> list[str]:
    """为已存在的表补齐新增列。

    create_all() 只会建新表，不会给已有表加列——新增字段后本地库会报
    "no such column"，故这里显式做一次轻量迁移。
    """
    import sqlalchemy as sa
    from app.models import entities as ent

    added: list[str] = []
    insp = sa.inspect(engine)
    existing_tables = set(insp.get_table_names())
    checks = [
        ("daily_checkins", "meals", sa.JSON),
    ]
    for table, col, coltype in checks:
        if table not in existing_tables:
            continue
        cols = {c["name"] for c in insp.get_columns(table)}
        if col in cols:
            continue
        with engine.begin() as conn:
            conn.execute(sa.text(
                f"ALTER TABLE {table} ADD COLUMN {col} JSON"
            ))
        added.append(f"{table}.{col}")
    if added:
        logger.info("已补齐新增列：%s", added)
    return added


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    _ensure_columns(SessionLocal())
    with SessionLocal() as db:
        meals = _ensure_seed_meals(db)
        presets = _ensure_exercise_presets(db)
        demo = _ensure_demo_user(db)
        db.commit()
    logger.info("建表完成 | 种子菜单 %s 条 | 运动预设 %s 条%s",
                meals, presets, f" | 演示账号 {demo}" if demo else "")