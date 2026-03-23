@echo off
chcp 65001 >nul
REM API Capture 启动脚本 - Socket 代理模式（更稳定）

echo ========================================
echo   API Capture Skill - 启动代理
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

echo [信息] 使用 Socket 代理模式（更稳定）
echo.

REM 启动 Socket 代理
python "%~dp0socket_proxy.py" 18527

echo.
echo [信息] 代理已停止
pause
