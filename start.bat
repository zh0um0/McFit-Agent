@echo off
REM ============================================================
REM  麦门控卡精明私教 · 一键启动
REM  用法：双击本文件，或在命令行执行 start.bat
REM  前置条件：已安装 Python 3.10+ 与 Node.js 18+
REM ============================================================
setlocal enabledelayedexpansion
cd /d "%~dp0"
title McFit-Agent Launcher

echo.
echo   ==== 麦门控卡精明私教 McFit-Agent ====
echo.

REM ---------- 1. 后端 ----------
where python >nul 2>nul
if errorlevel 1 (
    echo [x] 未找到 Python，请先安装 Python 3.10+
    pause & exit /b 1
)

if not exist "backend\.venv" (
    echo [1/4] 创建 Python 虚拟环境...
    python -m venv backend\.venv
)
call "backend\.venv\Scripts\activate.bat"

echo [2/4] 安装后端依赖...
python -m pip install -q --upgrade pip
python -m pip install -q -r backend\requirements.txt

if not exist "backend\.env" (
    copy "backend\.env.example" "backend\.env" >nul
    echo       已生成 backend\.env（按需填写 MCP_TOKEN）
)

echo [3/4] 启动后端 API (http://127.0.0.1:8000)...
start "McFit Backend" cmd /k "cd backend && .venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"

REM 轮询等待后端真正就绪，而不是死等固定 4 秒
echo       等待后端就绪...
set /a WAITED=0
:WAIT_LOOP
curl -s -o nul -m 1 http://127.0.0.1:8000/health >nul 2>nul
if not errorlevel 1 goto WAIT_OK
set /a WAITED+=1
if !WAITED! lss 20 (
    timeout /t 1 >nul
    goto WAIT_LOOP
)
echo       [!] 后端启动超时，可双击 check.bat 排查
:WAIT_OK
echo       后端已就绪

REM ---------- 2. 前端 ----------
where node >nul 2>nul
if errorlevel 1 (
    echo [!] 未找到 Node.js，将只启动后端
    echo     浏览器访问 http://127.0.0.1:8000/docs 查看 API 文档
    pause & exit /b 0
)

echo [4/4] 启动前端界面 (http://localhost:5173)...
if not exist "frontend\node_modules" (
    echo       首次运行，安装前端依赖...
    pushd frontend
    call npm install --no-fund --no-audit
    popd
)
echo.
echo   --------------------------------------------
echo   前端界面：http://localhost:5173
echo   接口文档：http://127.0.0.1:8000/docs
echo   演示账号：demo / demo123456
echo   关闭本窗口即停止前端服务
echo.
pushd frontend
call npm run dev
popd

endlocal