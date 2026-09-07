---
name: api-capture-to-test
description: 捕获浏览器 HTTP 流量并生成接口自动化测试用例
---

# API Capture to Test Skill

## 何时使用此 Skill

当用户需要：
- 捕获浏览器操作时的 API 流量
- 从捕获的流量生成自动化测试用例
- 快速为现有 Web 系统补充接口测试覆盖
- 学习目标测试框架的代码风格并生成符合风格的代码

## 使用流程

### 阶段 1: 捕获流量

1. 启动代理服务器：
```bash
cd D:/capture-api-skill
python main.py capture --port 18527 --include-host trackingmore.com
```

2. 告知用户：
   - 推荐运行 `python main.py browser --url <目标地址>`，启动独立临时 Chrome
   - 或手动配置浏览器代理为 `localhost:18527`
   - 正常操作 Web 系统
   - 完成后按 Ctrl+C 停止捕获

### 阶段 2: 筛选和生成

1. 启动 Web UI：
```bash
python main.py review --port 18528
```

2. 告知用户访问 `http://localhost:18528` 进行以下操作：
   - 查看捕获的接口列表
   - 按 HTTP 方法或关键字过滤
   - 勾选需要生成测试用例的接口
   - （可选）填入目标测试框架路径并点击"扫描框架"
   - 点击"生成用例"按钮

3. 生成的代码位于 `output/` 目录：
   - `output/api/` - API 封装函数
   - `output/data/` - 测试数据文件（YAML 格式）
   - `output/case/` - 测试用例
   - `output/lounger/` - Lounger 可执行的多步骤场景项目

### 阶段 3: 审查和迁移

1. 审查生成的代码：
```bash
ls -la output/api/
ls -la output/data/
ls -la output/case/
```

2. 将生成的代码迁移到目标测试框架：
```bash
# 示例：复制到目标框架
cp output/api/* /path/to/target/framework/api/
cp output/data/* /path/to/target/framework/data/
cp output/case/* /path/to/target/framework/case/
```

3. Lounger 产物：
   - 登录响应 token 与后续请求会自动生成 `extract` 依赖
   - 密码、Cookie、未关联 token 使用运行时配置变量，不写入捕获值
   - tracking number、时间戳使用 `conftest.py` 中注册的动态模板函数
   - 自动生成状态码、常见业务 code 和资源 ID 非空断言

## 其他命令

### 清空捕获数据
```bash
python main.py clear
```

### 启动独立测试 Chrome

```bash
python main.py browser --url <TM后台地址> --proxy-port 18527
```

独立 Chrome 使用临时 Profile 和进程级代理，不读取日常 Chrome 数据；关闭后自动清理临时 Profile。

### 运行测试验证工具本身
```bash
cd D:/capture-api-skill
pytest tests/ -v
```

## 工作原理

1. **代理捕获**：使用 mitmproxy 拦截浏览器 HTTP 流量
2. **智能过滤**：自动排除静态资源、健康检查等无关请求
3. **去重存储**：相同接口（path + body）只保留最新记录
4. **动态字段识别**：自动识别 token、tracking number、timestamp 等运行时字段
5. **框架扫描**：通过 AST 分析目标框架代码风格
6. **代码生成**：生成通用三层骨架和 Lounger 多步骤 YAML 场景

## 注意事项

- 仅支持 HTTP/HTTPS 流量（不支持 WebSocket）
- 需要手动配置浏览器代理
- 生成的代码需要人工审查和调整
- 生成断言来源于捕获响应，仍需人工确认业务语义和负向场景
- 建议在测试环境使用，避免捕获生产环境敏感数据

## 依赖要求

项目依赖已在 `requirements.txt` 中定义：
- mitmproxy >= 10.0.0
- fastapi >= 0.104.0
- uvicorn >= 0.24.0
- pytest >= 7.4.0
- lounger >= 1.5.0
- 其他依赖见 requirements.txt

首次使用前需要安装依赖：
```bash
cd D:/capture-api-skill
pip install -r requirements.txt
```

## 示例对话

**用户**："帮我捕获订单支付接口的流量并生成测试用例"

**Agent 响应**：
1. 我会启动代理服务器捕获流量
2. 请配置浏览器代理为 localhost:18527
3. 然后操作订单支付功能
4. 完成后我会启动 Web UI 让你筛选接口
5. 最后生成测试用例代码

## 故障排查

### 代理无法启动
- 检查端口 18527 是否被占用
- 尝试使用其他端口：`python main.py capture --port 18529`

### Web UI 无法访问
- 检查端口 18528 是否被占用
- 确认 FastAPI 服务已正常启动

### 生成的代码不符合预期
- 确保已正确扫描目标框架
- 手动调整生成的代码以符合实际需求
