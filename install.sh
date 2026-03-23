#!/bin/bash
# 安装脚本 - 将 API Capture Skill 安装到系统

set -e

# 配置
INSTALL_DIR="${HOME}/.local/share/api-capture-skill"
BIN_DIR="${HOME}/.local/bin"

echo "=== API Capture Skill 安装程序 ==="
echo ""

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到 Python 3"
    echo "请先安装 Python 3.9 或更高版本"
    exit 1
fi

echo "✓ Python 版本: $(python3 --version)"

# 创建安装目录
echo "创建安装目录: $INSTALL_DIR"
mkdir -p "$INSTALL_DIR"
mkdir -p "$BIN_DIR"

# 复制文件
echo "复制项目文件..."
cp -r capture storage analyzer generator web utils tests "$INSTALL_DIR/"
cp main.py config.py requirements.txt README.md "$INSTALL_DIR/"

# 安装依赖
echo "安装 Python 依赖..."
cd "$INSTALL_DIR"
python3 -m pip install -r requirements.txt --quiet

# 创建启动脚本
echo "创建命令行工具..."
cat > "$BIN_DIR/api-capture" << 'SCRIPT'
#!/bin/bash
INSTALL_DIR="${HOME}/.local/share/api-capture-skill"
cd "$INSTALL_DIR"
python3 main.py "$@"
SCRIPT

chmod +x "$BIN_DIR/api-capture"

# 检查 PATH
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    echo ""
    echo "⚠️  请将以下行添加到你的 ~/.bashrc 或 ~/.zshrc:"
    echo "export PATH=\"\$HOME/.local/bin:\$PATH\""
    echo ""
fi

echo ""
echo "=== 安装完成 ==="
echo ""
echo "使用方法:"
echo "  api-capture capture    # 启动代理捕获"
echo "  api-capture review     # 启动 Web UI"
echo "  api-capture clear      # 清空数据"
echo ""
echo "安装位置: $INSTALL_DIR"
echo ""
