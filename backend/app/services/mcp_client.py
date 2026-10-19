"""麦当劳官方 MCP Streamable HTTP 客户端（JSON-RPC 2.0）。

要点：
  - initialize → notifications/initialized → tools/call 三步握手
  - Session 复用（Streamable HTTP 通过 Mcp-Session-Id 保持会话）
  - Token 只从环境变量读取，绝不落库/入日志
  - 任何异常均向上抛出，由调用方降级到种子数据
"""
from __future__ import annotations

import hashlib
import logging
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger("mcfit.mcp")

_jsonrpc_id = 0

# PRD 模块2 锁定的 6 个工具（不扩展）
ALLOWED_TOOLS = {
    "list-nutrition-foods",
    "auto-bind-coupons",
    "query-my-coupons",
    "query-meals",
    "calculate-price",
    "campaign-calendar",
}


def _next_id() -> int:
    global _jsonrpc_id
    _jsonrpc_id += 1
    return _jsonrpc_id


class McpError(RuntimeError):
    pass


class McpClient:
    def __init__(self, token: str | None = None) -> None:
        self.token = token if token is not None else settings.mcp_token
        if not self.token:
            raise McpError("未配置 MCP_TOKEN")
        self._session_id: str | None = None
        self._inited = False

    def _headers(self) -> dict[str, str]:
        h = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if self._session_id:
            h["Mcp-Session-Id"] = self._session_id
        return h

    def _post(self, client: httpx.Client, payload: dict[str, Any]) -> dict:
        resp = client.post(settings.mcp_url, json=payload, headers=self._headers())
        if resp.status_code >= 400:
            # 绝不把 Authorization 头写进异常信息
            raise McpError(f"HTTP {resp.status_code}: {resp.text[:200]}")
        sid = resp.headers.get("Mcp-Session-Id")
        if sid:
            self._session_id = sid

        ctype = resp.headers.get("content-type", "")
        if "text/event-stream" in ctype:
            for line in resp.text.splitlines():
                if line.startswith("data:"):
                    import json
                    return json.loads(line[5:].strip())
            raise McpError("SSE 响应中无 data 帧")
        return resp.json() if resp.text.strip() else {}

    def _rpc(self, client: httpx.Client, method: str, params: dict | None = None) -> dict:
        body = {"jsonrpc": "2.0", "id": _next_id(), "method": method,
                "params": params or {}}
        res = self._post(client, body)
        if isinstance(res, dict) and res.get("error"):
            raise McpError(f"{method} 返回错误：{res['error']}")
        return res.get("result", {}) if isinstance(res, dict) else {}

    def _notify(self, client: httpx.Client, method: str, params: dict | None = None) -> None:
        self._post(client, {"jsonrpc": "2.0", "method": method, "params": params or {}})

    def initialize(self) -> dict:
        with httpx.Client(timeout=settings.mcp_timeout_seconds) as c:
            result = self._rpc(c, "initialize", {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": settings.app_name, "version": settings.app_version},
            })
            self._notify(c, "notifications/initialized")
            self._inited = True
            logger.info("MCP 初始化成功，session=%s", bool(self._session_id))
            return result

    def list_tools(self) -> list[dict]:
        with httpx.Client(timeout=settings.mcp_timeout_seconds) as c:
            if not self._inited:
                self.initialize()
            return self._rpc(c, "tools/list").get("tools", [])

    def call_tool(self, name: str, arguments: dict | None = None) -> Any:
        if name not in ALLOWED_TOOLS:
            raise McpError(f"工具 {name} 不在 PRD 约定的 6 个工具白名单内")
        with httpx.Client(timeout=settings.mcp_timeout_seconds) as c:
            if not self._inited:
                self.initialize()
            res = self._rpc(c, "tools/call", {"name": name, "arguments": arguments or {}})
            return _extract_text(res)


def _extract_text(res: dict) -> Any:
    """MCP 工具返回 content 数组，取 text 并解析为结构化数据。

    实测官方返回并非纯 JSON，而是带markdown 说明的文本：
        # API Response Information
        ...字段说明...
        ## Original Response
        {"success":true,...,"data":"[160]{...}:\\n  麦辣鸡腿汉堡,..."}

    故需先剥离 `## Original Response` 之后的包装，再做JSON 解析。
    """
    content = res.get("content") or []
    chunks = [c.get("text", "") for c in content if c.get("type") == "text"]
    if not chunks:
        return res

    joined = "".join(chunks)

    # 剥离 markdown 说明段，只留原始响应体
    import re
    m = re.search(r"##\s*Original Response\s*\n+(.*)", joined, re.S)
    if m:
        joined = m.group(1).strip()

    # 若已是JSON 对象则解析；否则按原样返回字符串（如 data 为专有文本格式）
    import json
    try:
        return json.loads(joined)
    except (json.JSONDecodeError, ValueError):
        return joined


def parse_nutrition_payload(s: str) -> list[dict]:
    """解析官方 list-nutrition-foods 的专有字符串格式。

    实测格式（非标准 JSON，必须专用解析器）：
        [160]{productName,nutritionDescription,energyKj,energyKcal,protein,
               fat,carbohydrate,sodium,calcium}:
          麦辣鸡腿汉堡,null,2029,485,24,24,42,1208,154

    注意：官方仅按名称区分，**无商品编码、无价格**——价格为项目估算值，
    分类由mcd_official_data.MCD_OFFICIAL_PICKS 人工指定。
    """
    import re

    m = re.match(r"\[(\d+)\]\{([^}]*)\}:", s)
    if not m:
        return []
    fields = m.group(2).split(",")
    rows = [ln.strip() for ln in s.split("\n")[1:] if ln.strip()]

    out: list[dict] = []
    for ln in rows:
        parts = ln.split(",")
        if len(parts) != len(fields):
            continue                      # 字段数不匹配的行直接跳过，不猜测
        out.append(dict(zip(fields, parts)))
    return out


def _num(v: object) -> float:
    """安全转float：官方用字符串 'null' 表示缺失。"""
    try:
        return float(v)                  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0.0


def call_tool(name: str, arguments: dict | None = None) -> Any:
    return McpClient().call_tool(name, arguments)


def sync_meals_to_cache(db, *, picked_only: bool = True) -> dict:
    """从 list-nutrition-foods 拉取官方营养数据写入 meals_cache。

    picked_only=True时只落库精选集（每类 5 个，共 25 条），
    避免演示界面出现 160 条单品淹没核心卖点。
    返回 {synced, matched, official_total, missing}。
    """
    from datetime import UTC, datetime

    from app.models.entities import MealCache
    from app.services.mcd_official_data import MCD_OFFICIAL_PICKS, OFFICIAL_SOURCE_NOTE
    from sqlalchemy import select

    payload = call_tool("list-nutrition-foods", {})
    if isinstance(payload, dict):
        raw = payload.get("data", payload)
    else:
        raw = payload

    items = parse_nutrition_payload(raw) if isinstance(raw, str) else []
    if not items:
        raise McpError(
            "未能解析官方营养数据（返回格式与预期不符）。"
            f"data 类型={type(raw).__name__}，长度={len(str(raw))}"
        )

    by_name = {i.get("productName", "").strip(): i for i in items}
    now = datetime.now(UTC)
    synced = 0
    missing: list[str] = []

    targets = MCD_OFFICIAL_PICKS if picked_only else {}
    for name, (category, price, high_protein, fried) in targets.items():
        row = by_name.get(name)
        if row is None:
            missing.append(name)          # 官方改名/下架时不静默，留痕
            continue

        # 稳定伪编码（仅作主键）：用 md5 而非内置 hash，
        # 因Python 内置 hash 对 str 逐进程加盐，重启后会漂移导致重复记录
        code = "MCD-" + hashlib.md5(name.encode("utf-8")).hexdigest()[:8].upper()
        m = db.scalar(select(MealCache).where(MealCache.mcp_code == code))
        if m is None:
            m = MealCache(mcp_code=code)
            db.add(m)
        m.name = name
        m.category = category
        m.kcal = _num(row.get("energyKcal"))
        m.protein_g = _num(row.get("protein"))
        m.fat_g = _num(row.get("fat"))
        m.carb_g = _num(row.get("carbohydrate"))
        m.sodium_mg = _num(row.get("sodium"))
        m.price = price
        m.is_high_protein = high_protein
        m.is_fried = fried
        m.source = "mcp"
        m.synced_at = now
        synced += 1

    db.commit()
    result = {
        "synced": synced,
        "official_total": len(items),
        "matched": len(MCD_OFFICIAL_PICKS) - len(missing),
        "missing": missing,
        "note": OFFICIAL_SOURCE_NOTE,
    }
    logger.info("MCP 营养同步完成：%s/%s 条（官方全量 %s），缺失 %s",
                result["synced"], len(MCD_OFFICIAL_PICKS), result["official_total"], missing)
    return result