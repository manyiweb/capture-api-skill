# API Capture Skill

用于捕获浏览器 HTTP 流量并生成接口自动化测试用例的工具。

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动代理捕获

```bash
python main.py capture
```

配置浏览器代理为 `localhost:8080`，然后操作 Web 系统。

### 3. 启动 Web UI 筛选

```bash
python main.py review
```

访问 http://localhost:8888，勾选需要的接口，点击生成。

### 4. 查看生成产物

生成的代码位于 `output/` 目录：
- `api/` - API 封装函数
- `data/` - 测试数据文件
- `case/` - 测试用例

## 命令参考

```bash
python main.py capture [--port 8080] [--db capture.db]    # 启动代理
python main.py review [--port 8888] [--db capture.db]     # 启动 Web UI
python main.py clear [--db capture.db]                    # 清空数据
```

## 运行测试

```bash
pytest tests/ -v
```
