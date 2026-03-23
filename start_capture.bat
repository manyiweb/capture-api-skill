@echo off
chcp 65001 >nul
REM API Capture 启动脚本 - Windows 版本
REM 使用 Python 模块方式运行 mitmdump

echo ========================================
echo   API Capture Skill - 代理启动
echo ========================================
echo.

REM 检查 Python 是否可用
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [错误] 未找到 Python
    echo.
    echo 请确保已安装 Python 3.9+
    echo.
    pause
    exit /b 1
)

REM 检查 mitmproxy 是否已安装
python -c "import mitmproxy" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [错误] 未找到 mitmproxy 模块
    echo.
    echo 请安装 mitmproxy:
    echo   pip install mitmproxy
    echo.
    pause
    exit /b 1
)

echo [信息] 启动代理服务器...
echo [信息] 监听地址: localhost:18527
echo [信息] 数据库: %~dp0capture.db
echo.
echo [提示] 请配置浏览器代理为 localhost:18527
echo [提示] 按 Ctrl+C 停止捕获
echo.
echo ========================================
echo.

REM 使用 Python 模块方式启动 mitmdump
python -m mitmproxy.tools.dump -s "%~dp0mitm_script.py" --listen-port 18527 --set block_global=false

echo.
echo [信息] 代理已停止
pause
