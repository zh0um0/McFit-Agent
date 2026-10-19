#!/usr/bin/env bash
# ============================================================
#  麦门控卡精明私教 · 一键启动（macOS / Linux）
#  用法：./start.sh
# ============================================================
set -e
cd "$(dirname "$0")"

command -v python3 >/dev/null || { echo "[x] 未找到 python3，请先安装 3.10+"; exit 1; }
command -v node >/dev/null || { echo "[!] 未找到 node，将只启动后端"; }

# ---- 1. 后端 ----
[ -d backend/.venv ] || python3 -m venv backend/.venv
source backend/.venv/bin/activate
echo "[1/2] 安装后端依赖..."
pip install -q --upgrade pip
pip install -q -r backend/requirements.txt

[ -f backend/.env ] || { cp backend/.env.example backend/.env; echo "已生成 backend/.env"; }

echo "[2/2] 启动后端 http://127.0.0.1:8000 ..."
(cd backend && python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000) &
BACKEND_PID=$!
trap 'kill $BACKEND_PID 2>/dev/null' EXIT

# 等待后端就绪后再拉前端，避免前端首屏请求打到尚未监听的端口
echo "等待后端就绪..."
for i in $(seq 1 20); do
  if curl -s -m 1 -o /dev/null http://127.0.0.1:8000/health 2>/dev/null; then
    echo "后端已就绪"
    break
  fi
  sleep 1
done

# ---- 2. 前端 ----
if command -v node >/dev/null; then
  [ -d frontend/node_modules ] || (cd frontend && npm install --no-fund --no-audit)
  echo ""
  echo "  前端：http://localhost:5173"
  echo "  接口文档：http://127.0.0.1:8000/docs"
  echo "  演示账号：demo / demo123456"
  echo "  按 Ctrl+C 停止"
  echo ""
  (cd frontend && npm run dev) || echo "前端启动失败，请执行 ./check.sh 排查"
else
  echo ""
  echo "  未找到 Node.js，仅启动后端。"
  echo "  接口文档：http://127.0.0.1:8000/docs"
  echo "  按 Ctrl+C 停止"
  echo ""
  wait $BACKEND_PID
fi