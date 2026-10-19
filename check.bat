@echo off
chcp 65001 >nul
REM ============================================================
REM  环境自检 —— 排查「服务起不来 / 页面打不开」
REM  用法：双击本文件
REM ============================================================
cd /d "%~dp0"
set OK=0
set FAIL=0

echo.
echo   麦门控卡精明私教 · 环境自检
echo   --------------------------------------------

echo.
echo 运行环境
where python >nul 2>nul
if errorlevel 1 (
    echo   [X] 未找到 Python ^(需 3.10+^)
    set /a FAIL+=1
) else (
    for /f "tokens=2" %%v in ('python --version 2^>^&1') do echo   [OK] Python %%v
    set /a OK+=1
)
where node >nul 2>nul
if errorlevel 1 (
    echo   [!] 未找到 Node.js —— 仍可启动后端并查看 /docs 接口文档
) else (
    for /f "tokens=1" %%v in ('node --version') do echo   [OK] Node.js %%v
)

echo.
echo 依赖
if exist "backend\.venv" (
    echo   [OK] 后端虚拟环境已创建
    set /a OK+=1
) else (
    echo   [X] 后端虚拟环境缺失 -^> python -m venv backend\.venv
    set /a FAIL+=1
)
if exist "frontend\node_modules" (
    echo   [OK] 前端依赖已安装
) else (
    echo   [!] 前端依赖未安装 -^> cd frontend ^&^& npm install
)

echo.
echo 配置
if exist "backend\.env" (
    echo   [OK] backend\.env 已配置
    set /a OK+=1
) else (
    echo   [!] backend\.env 不存在 -^> 从 .env.example 复制一份（可选，不影响本地运行）
)
findstr /R /C:"^MCP_TOKEN=..*" "backend\.env" >nul 2>nul
if errorlevel 1 (
    echo   [!] 未配置 MCP_TOKEN -^> 使用内置种子菜单（功能不降级）
) else (
    echo   [OK] MCP_TOKEN 已填写 -^> 使用官方实时菜单
)

echo.
echo 服务状态
curl -s -o nul -w "%%{http_code}" -m 3 http://127.0.0.1:8000/health > "%TEMP%\mcfit_be.txt" 2>nul
set /a BECODE=0
if exist "%TEMP%\mcfit_be.txt" set /a BECODE=<%TEMP%\mcfit_be.txt
if "%BECODE%"=="200" (
    echo   [OK] 后端运行中 -^> http://127.0.0.1:8000
    set /a OK+=1
) else (
    echo   [X] 后端未运行 ^(HTTP %BECODE%^)
    echo       -^> cd backend ^&^& .venv\Scripts\python -m uvicorn app.main:app --port 8000
    set /a FAIL+=1
)

curl -s -o nul -w "%%{http_code}" -m 3 http://localhost:5173/ > "%TEMP%\mcfit_fe.txt" 2>nul
set /a FECODE=0
if exist "%TEMP%\mcfit_fe.txt" set /a FECODE=<%TEMP%\mcfit_fe.txt
if "%FECODE%"=="200" (
    echo   [OK] 前端运行中 -^> http://localhost:5173
    set /a OK+=1
) else (
    echo   [X] 前端未运行 ^(HTTP %FECODE%^)
    echo       -^> cd frontend ^&^& npm run dev
    set /a FAIL+=1
)
del "%TEMP%\mcfit_be.txt" "%TEMP%\mcfit_fe.txt" >nul 2>nul

echo.
echo   --------------------------------------------
if %FAIL%==0 (
    echo   全部就绪（%OK% 项通过）
) else (
    echo   %FAIL% 项需处理（%OK% 项通过）
)
echo.
echo   启动方式：双击 start.bat
echo   接口文档：http://127.0.0.1:8000/docs
echo   演示账号：demo / demo123456
echo.
pause
exit /b %FAIL%