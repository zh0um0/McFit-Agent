#!/usr/bin/env bash
# ============================================================
#  环境自检 —— 排查「服务起不来 / 页面打不开」
#  用法：./check.sh
# ============================================================
set -u
cd "$(dirname "$0")"

BACKEND=http://127.0.0.1:8000
FRONTEND=http://localhost:5173
OK=0
FAIL=0

c_ok()   { echo -e "  \033[32m✓\033[0m $1"; OK=$((OK+1)); }
c_bad()  { echo -e "  \033[31m✗\033[0m $1"; FAIL=$((FAIL+1)); }
c_warn() { echo -e "  \033[33m!\033[0m $1"; }

echo ""
echo "  麦门控卡精明私教 · 环境自检"
echo "  ────────────────────────────────────────────"

# ---- 1. 运行环境 ----
echo ""
echo "运行环境"
command -v python >/dev/null && c_ok "Python: $(python --version 2>&1)" \
  || c_bad "未找到 Python（需 3.10+）"
if command -v node >/dev/null; then
  c_ok "Node.js: $(node --version)"
else
  c_warn "未找到 Node.js —— 仍可启动后端并查看 /docs 接口文档"
fi

# ---- 2. 依赖 ----
echo ""
echo "依赖"
[ -d "backend/.venv" ] && c_ok "后端虚拟环境已创建" \
  || c_bad "后端虚拟环境缺失 → 执行 python -m venv backend/.venv"
[ -d "frontend/node_modules" ] && c_ok "前端依赖已安装" \
  || c_warn "前端依赖未安装 → 进入 frontend 执行 npm install"

# ---- 3. 配置 ----
echo ""
echo "配置"
[ -f "backend/.env" ] && c_ok "backend/.env 已配置" \
  || c_warn "backend/.env 不存在 → 从 .env.example 复制一份（可选，不影响本地运行）"
if grep -qE '^\s*MCP_TOKEN=..+' "backend/.env" 2>/dev/null; then
  c_ok "MCP_TOKEN 已填写 → 将使用官方实时菜单"
elif [ -f "backend/.env" ]; then
  c_warn "未配置 MCP_TOKEN → 使用内置种子菜单（功能不降级）"
else
  c_warn "无 .env → 使用内置默认配置"
fi

# ---- 4. 服务状态 ----
echo ""
echo "服务状态"
code=$(curl -s -o /dev/null -w "%{http_code}" -m 3 "$BACKEND/health" 2>/dev/null)
if [ "$code" = "200" ]; then
  c_ok "后端运行中 → $BACKEND"
  curl -s -m 3 "$BACKEND/health" 2>/dev/null | tr ',' '\n' \
    | sed 's/[{}"]//g; s/^ *//' | grep -E 'status|mcp_mode|database' \
    | while read -r line; do echo "      $line"; done
else
  c_bad "后端未运行（HTTP $code）"
  echo "      → cd backend && .venv/Scripts/python -m uvicorn app.main:app --port 8000"
fi

code=$(curl -s -o /dev/null -w "%{http_code}" -m 3 "$FRONTEND/" 2>/dev/null)
if [ "$code" = "200" ]; then
  c_ok "前端运行中 → $FRONTEND"
else
  c_bad "前端未运行（HTTP $code）"
  echo "      → cd frontend && npm run dev"
fi

# ---- 5. 端口占用提示 ----
echo ""
echo "端口占用排查"
for p in 8000 5173; do
  if netstat -ano 2>/dev/null | grep -q ":$p .*LISTENING"; then
    if [ "$p" = "8000" ] && [ "$code" != "200" ]; then
      c_warn "端口 $p 已被占用但服务无响应 → 可能是残留进程，任务管理器结束该进程"
    fi
  fi
done

# ---- 汇总 ----
echo ""
echo "  ────────────────────────────────────────────"
if [ "$FAIL" -eq 0 ]; then
  echo -e "  \033[32m全部就绪\033[0m（$OK 项通过）"
else
  echo -e "  \033[31m$FAIL 项需处理\033[0m（$OK 项通过）"
fi
echo ""
echo "  启动方式：双击 start.bat（Windows）或 ./start.sh（macOS/Linux）"
echo "  接口文档：http://127.0.0.1:8000/docs"
echo "  演示账号：demo / demo123456"
echo ""

exit $([ "$FAIL" -eq 0 ] && echo 0 || echo 1)