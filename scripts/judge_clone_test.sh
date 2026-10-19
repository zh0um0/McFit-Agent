#!/usr/bin/env bash
# ============================================================
#  评委视角验证：模拟「全新克隆 → 零配置启动」完整流程
#  用法：bash scripts/judge_clone_test.sh
#  本脚本会在 _clone_test/ 下建一个干净的副本（排除所有 gitignore 项），
#  然后按 README 的步骤从零跑一遍，检验评委能否顺利启动。
# ============================================================
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TEST_DIR="$ROOT/_clone_test"

echo "============================================================"
echo "评委视角验证：全新克隆 → 零配置启动"
echo "============================================================"

# ---- 1. 模拟 git clone：只复制会被提交的文件 ----
echo ""
echo "[1/6] 模拟 git clone（排除 .gitignore 中的内容）..."
rm -rf "$TEST_DIR"
mkdir -p "$TEST_DIR"
cd "$ROOT"
# 用 git 的忽略规则导出（若已 init），否则手工排除
if [ -d .git ]; then
  git ls-files -z | while IFS= read -r -d '' f; do
    mkdir -p "$TEST_DIR/$(dirname "$f")"
    cp "$f" "$TEST_DIR/$f" 2>/dev/null
  done
  echo "      已按 git 跟踪文件导出"
else
  tar --exclude='.venv' --exclude='node_modules' --exclude='__pycache__' \
      --exclude='*.db' --exclude='.env' --exclude='.local_key' \
      --exclude='dist' --exclude='.pytest_cache' --exclude='.git' \
      -cf - . 2>/dev/null | (cd "$TEST_DIR" && tar -xf -)
  echo "      已按忽略规则导出（未 init git，使用等价规则）"
fi

# ---- 2. 检查是否有不该提交的文件混进去 ----
echo ""
echo "[2/6] 检查敏感文件是否泄漏..."
LEAK=""
[ -f "$TEST_DIR/backend/mcfit.db" ] && LEAK="$LEAK mcfit.db"
[ -f "$TEST_DIR/backend/.env" ] && LEAK="$LEAK .env"
[ -f "$TEST_DIR/backend/.local_key" ] && LEAK="$LEAK .local_key"
[ -d "$TEST_DIR/backend/.venv" ] && LEAK="$LEAK .venv"
[ -d "$TEST_DIR/frontend/node_modules" ] && LEAK="$LEAK node_modules"
if [ -n "$LEAK" ]; then
  echo "      [FAIL] 以下敏感内容被提交了：$LEAK"
  exit 1
fi
echo "      [OK] 无 Token / 数据库 / 虚拟环境泄漏"

# ---- 3. 检查 Token 是否出现在任何文件里 ----
echo ""
echo "[3/6] 扫描 Token 泄漏..."
if grep -rlE '[A-Za-z0-9]{32}' "$TEST_DIR" \
     --include='*.py' --include='*.json' --include='*.md' \
     --include='*.vue' --include='*.js' --include='*.txt' 2>/dev/null \
     | grep -v node_modules | head -5 | grep -q .; then
  echo "      [WARN] 存在疑似 32 位字符串，请人工确认是否为 Token："
  grep -rlE '[A-Za-z0-9]{32}' "$TEST_DIR" \
    --include='*.py' --include='*.json' --include='*.md' 2>/dev/null | head -5
else
  echo "      [OK] 未发现疑似 Token"
fi

# ---- 4. 后端能否零配置启动 ----
echo ""
echo "[4/6] 测试后端零配置启动..."
PY="$ROOT/backend/.venv/Scripts/python.exe"
[ -x "$PY" ] || PY="$ROOT/backend/.venv/bin/python"
if [ ! -x "$PY" ]; then
  echo "      [SKIP] 本机无 venv（评委需自行 pip install）"
else
  cd "$TEST_DIR/backend"
  # 借用主仓库的虚拟环境（依赖等价），但数据库与目录完全是干净的副本
  PYTHONPATH="$TEST_DIR/backend" "$PY" - <<'PYEOF' 2>&1 | tail -8
import os, sys
sys.path.insert(0, os.getcwd())
os.environ['DATABASE_URL'] = 'sqlite:///./_fresh.db'
os.environ.pop('MCP_TOKEN', None)
try:
    from app.db.init_db import init_db
    init_db()
    from app.db.session import SessionLocal
    from app.models.entities import MealCache, User
    from sqlalchemy import select, func
    with SessionLocal() as db:
        n = db.scalar(select(func.count()).select_from(MealCache))
        src = dict(db.execute(select(MealCache.source, func.count())
                             .group_by(MealCache.source)).fetchall())
        users = [x[0] for x in db.execute(select(User.username)).fetchall()]
    print(f"      建表 OK | 菜单 {n} 条 {src} | 账号 {users}")
    ok = n > 0 and 'demo' in users
    print("      [OK] 后端可零配置启动" if ok else "      [FAIL] 初始化异常")
except Exception as exc:
    print(f"      [FAIL] 启动异常：{exc}")
PYEOF
  rm -f "$TEST_DIR/backend/_fresh.db"
fi

# ---- 5. 前端依赖是否已声明 ----
echo ""
echo "[5/6] 检查前端依赖声明..."
PKG="$TEST_DIR/frontend/package.json"
if [ -f "$PKG" ]; then
  grep -q '"vite"' "$PKG" && grep -q '"vue"' "$PKG" \
    && echo "      [OK] package.json 已声明 vue + vite" \
    || echo "      [FAIL] package.json 缺关键依赖"
else
  echo "      [FAIL] 缺 frontend/package.json"
fi

# ---- 6. 启动脚本是否齐全 ----
echo ""
echo "[6/6] 检查一键启动脚本..."
for f in start.bat start.sh check.bat check.sh README.md; do
  [ -f "$TEST_DIR/$f" ] && echo "      [OK] $f" || echo "      [FAIL] 缺 $f"
done

echo ""
echo "============================================================"
echo "评委在 README 中需执行的前置步骤："
echo "  1. 安装 Python 3.10+ 与 Node.js 18+"
echo "  2. 双击 start.bat（Windows）或 ./start.sh（macOS/Linux）"
echo "  3. 浏览器打开 http://localhost:5173"
echo "  4. 用demo / demo123456 登录"
echo "============================================================"

if [ "${KEEP:-0}" = "1" ]; then
  echo "副本保留在：$TEST_DIR"
else
  rm -rf "$TEST_DIR"
  echo ""
  echo "（验证副本已清理，设 KEEP=1 可保留）"
fi