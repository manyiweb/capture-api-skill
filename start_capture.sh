#!/bin/bash
# API Capture 启动脚本 - Linux/Mac 版本
# 使用 mitmdump 命令行工具启动代理

echo "========================================"
echo "  API Capture Skill - 代理启动"
echo "========================================"
echo ""

# 检查 mitmdump 是否可用
if ! command -v mitmdump &> /dev/null; then
    echo "[错误] 未找到 mitmdump 命令"
    echo ""
    echo "请确保已安装 mitmproxy:"
    echo "  pip install mitmproxy"
    echo ""
    exit 1
fi

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "[信息] 启动代理服务器..."
echo "[信息] 监听地址: localhost:8080"
echo "[信息] 数据库: $SCRIPT_DIR/capture.db"
echo ""
echo "[提示] 请配置浏览器代理为 localhost:8080"
echo "[提示] 按 Ctrl+C 停止捕获"
echo ""
echo "========================================"
echo ""

# 启动 mitmdump
mitmdump -s "$SCRIPT_DIR/mitm_script.py" --listen-port 8080 --set block_global=false

echo ""
echo "[信息] 代理已停止"
