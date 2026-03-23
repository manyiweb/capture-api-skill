# API Capture Skill 安装指南

## 方式 1: 作为独立工具使用（推荐）

### 安装步骤

1. 克隆或下载项目到本地：
```bash
git clone <repository-url> capture-api-skill
cd capture-api-skill
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

3. 使用 CLI 命令：
```bash
python main.py capture  # 启动代理捕获
python main.py review   # 启动 Web UI
python main.py clear    # 清空数据
```

## 方式 2: 作为 Agent Skill 使用

### 前提条件
- 项目已安装到本地（如 `D:/capture-api-skill`）
- 已安装 Python 依赖

### 在 Agent 中使用

1. **将 skill 定义文件添加到 agent 的 skills 目录**：
```bash
# 复制 skill 定义文件到 agent skills 目录
cp api-capture-to-test.md ~/.claude/skills/
# 或者
cp api-capture-to-test.md $CODEX_HOME/skills/
```

2. **在对话中调用 skill**：
```
用户: "帮我捕获 API 流量并生成测试用例"
Agent: 使用 api-capture-to-test skill 来执行任务
```

### 配置说明

skill 定义文件中的路径需要根据实际安装位置调整：
- 默认路径：`D:/capture-api-skill`
- 如果安装到其他位置，需要修改 skill 文件中的路径

## 方式 3: 打包为可安装的 Skill

### 创建 skill 包结构

```
api-capture-skill/
├── skill.md              # skill 定义文件
├── install.sh            # 安装脚本
├── requirements.txt      # Python 依赖
└── src/                  # 源代码
    ├── capture/
    ├── storage/
    ├── analyzer/
    ├── generator/
    ├── web/
    └── main.py
```

### 安装脚本示例

```bash
#!/bin/bash
# install.sh

INSTALL_DIR="$HOME/.local/share/api-capture-skill"

# 创建安装目录
mkdir -p "$INSTALL_DIR"

# 复制文件
cp -r src/* "$INSTALL_DIR/"
cp requirements.txt "$INSTALL_DIR/"

# 安装依赖
cd "$INSTALL_DIR"
pip install -r requirements.txt

# 创建命令别名
echo "alias api-capture='python $INSTALL_DIR/main.py'" >> ~/.bashrc

echo "安装完成！请运行 'source ~/.bashrc' 或重启终端"
```

## 使用建议

### 对于个人使用
- **推荐方式 1**：作为独立工具使用，简单直接

### 对于团队共享
- **推荐方式 3**：打包为可安装的 skill，便于分发和管理

### 对于 Agent 集成
- **推荐方式 2**：将 skill 定义文件添加到 agent，通过对话调用

## 注意事项

1. **路径配置**：确保 skill 文件中的路径与实际安装位置一致
2. **依赖管理**：首次使用前必须安装 Python 依赖
3. **权限要求**：需要能够启动 HTTP 服务（端口 8080, 8888）
4. **环境隔离**：建议使用虚拟环境避免依赖冲突

## 故障排查

### Skill 无法找到
- 检查 skill 文件是否在正确的目录
- 确认 agent 已重新加载 skills

### 命令执行失败
- 检查 Python 环境是否正确
- 确认依赖已安装
- 验证路径配置是否正确
