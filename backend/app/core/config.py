"""全局配置：全部走环境变量，零硬编码密钥。"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]  # backend/


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(BASE_DIR / ".env"), env_file_encoding="utf-8", extra="ignore"
    )

    # ---- 应用 ----
    app_name: str = "McFit-Agent"
    app_version: str = "0.1.0"
    api_prefix: str = "/api/v1"
    debug: bool = True

    # ---- 数据库 ----
    # 默认 SQLite 零配置，保证「克隆即跑」；改此值即可切 Postgres
    database_url: str = f"sqlite:///{(BASE_DIR / 'mcfit.db').as_posix()}"

    # ---- 认证 ----
    # 生产环境必须通过环境变量覆盖；仅本地演示时允许用默认值
    jwt_secret: str = "dev-only-change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 120      # 2 小时
    refresh_token_expire_days: int = 7           # 7 天
    pwd_hash_time_cost: int = 3

    # ---- 敏感字段落库加密（Fernet 对称密钥）----
    # 生成方式：python -c "from cryptography.fernet import Fernet;print(Fernet.generate_key().decode())"
    field_encryption_key: str = ""

    # ---- CORS ----
    cors_origins: list[str] = [
        "http://localhost:5173",   # vite dev
        "http://127.0.0.1:5173",
        "http://localhost:4173",   # vite preview
    ]

    # ---- 隐私开关（PRD 承诺项）----
    # True = 身体数据仅本地存储，不做任何云端同步（默认值，符合 PRD 隐私红线）
    cloud_sync_enabled: bool = False

    # ---- 麦当劳官方 MCP ----
    mcp_url: str = "https://mcp.mcd.cn"
    mcp_token: str = ""                 # 从环境变量读，绝不入库
    mcp_timeout_seconds: float = 20.0
    mcp_cache_ttl_hours: int = 12
    # 官方共160 条营养数据；演示场景只取每类 5 条，避免淹没核心卖点
    mcd_picked_only: bool = True

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()