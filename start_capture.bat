@echo off
REM API Capture 启动脚本 - Windows 版本
REM 使用 mitmdump 命令行工具启动代理

echo ========================================
echo   API Capture Skill - 代理启动
echo ========================================
echo.

REM 检查 mitmdump 是否可用
where mitmdump >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [错误] 未找到 mitmdump 命令
    echo.
    echo 请确保已安装 mitmproxy:
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

REM 启动 mitmdump
mitmdump -s "%~dp0mitm_script.py" --listen-port 18527 --set block_global=false

echo.
echo [信息] 代理已停止
pause
