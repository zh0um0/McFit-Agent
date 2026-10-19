"""应用主入口。"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.v1 import router as v1_router
from app.core.config import settings
from app.db.session import engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("mcfit")


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.db.init_db import init_db
    init_db()
    logger.info("%s v%s 启动完成 | DB=%s", settings.app_name, settings.app_version,
                "SQLite(本地)" if settings.is_sqlite else "Postgres")
    if not settings.mcp_token:
        logger.info("未配置 MCP_TOKEN —— 将使用内置种子菜单（离线演示模式）")
    yield


app = FastAPI(
    title=f"{settings.app_name} · 麦门控卡精明私教 API",
    version=settings.app_version,
    description=(
        "控卡 + 省钱 + 贴纸打卡。\n\n"
        "**所有营养与运动换算均为估算值，仅供参考，不构成医疗或营养专业建议。**\n\n"
        "隐私口径：身体数据默认仅本地存储（`CLOUD_SYNC_ENABLED=false`），不参与任何外发。"
    ),
    lifespan=lifespan,
    docs_url="/docs",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(v1_router, prefix=settings.api_prefix)


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    """统一校验错误格式，前端可直接提示第一条。

    注意：Pydantic 的 errors() 里 ctx/input 可能含 ValueError、bytes 等
    不可JSON 序列化的对象，必须逐项清洗，否则本处理器自身会抛 500。
    """
    errors = exc.errors()

    def _clean(obj: object) -> object:
        if isinstance(obj, (str, int, float, bool, type(None))):
            return obj
        if isinstance(obj, dict):
            return {str(k): _clean(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [_clean(x) for x in obj]
        return str(type(obj).__name__)

    first = errors[0] if errors else {}
    field = ".".join(str(x) for x in first.get("loc", [])[1:]) or "请求参数"
    msg = str(first.get("msg", "参数不合法")).removeprefix("Value error, ")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": f"{field}: {msg}",
            "errors": [{k: _clean(v) for k, v in e.items() if k != "ctx"} for e in errors[:5]],
        },
    )


@app.get("/health", tags=["系统"], summary="健康检查（免鉴权）")
def health() -> dict:
    db_ok = True
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:                                  # noqa: BLE001
        db_ok = False

    # 区分「配了 Token」与「库里真有官方数据」——
    # 配了但未同步时，菜单仍是种子数据，界面应如实展示。
    has_mcp_data = False
    if db_ok:
        try:
            from sqlalchemy import select
            from app.db.session import SessionLocal
            from app.models.entities import MealCache
            with SessionLocal() as s:
                has_mcp_data = bool(
                    s.scalar(select(MealCache).where(MealCache.source == "mcp").limit(1)))
        except Exception:                              # noqa: BLE001
            has_mcp_data = False

    return {
        "status": "ok" if db_ok else "degraded",
        "app": settings.app_name,
        "version": settings.app_version,
        "database": "sqlite" if settings.is_sqlite else "postgres",
        "database_ok": db_ok,
        "mcp_configured": bool(settings.mcp_token),
        "mcp_mode": "live" if has_mcp_data else "seed",
        "cloud_sync_enabled": settings.cloud_sync_enabled,
    }