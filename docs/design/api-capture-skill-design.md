# API 捕获与测试生成 Skill 设计文档

## 1. 概述

### 1.1 目标
创建一个独立的 Skill，用于捕获浏览器操作 Web 系统时的 API 接口调用，记录请求/响应数据，并基于这些数据快速生成接口自动化测试用例，加速接口自动化框架的完善和覆盖率提升。

### 1.2 核心能力
- 代理捕获浏览器 HTTP 流量
- Web UI 可视化筛选接口
- 自动学习目标框架代码风格
- 生成符合框架风格的测试代码（api/data/case 三层）

### 1.3 技术栈
- 捕获：mitmproxy（Python 代理工具）
- 存储：SQLite（轻量级本地数据库）
- Web UI：FastAPI + Jinja2 模板
- 代码生成：Python AST 分析 + 模板渲染

---

## 2. 架构设计

### 2.1 目录结构

```
api-capture-skill/
├── capture/           # 代理捕获模块
│   ├── proxy.py       # mitmproxy addon，流量捕获逻辑
│   └── filters.py     # 过滤规则（排除静态资源等）
├── storage/           # 数据持久化
│   └── db.py          # SQLite 操作封装
├── web/               # Web UI 模块
│   ├── server.py      # FastAPI 服务
│   └── templates/     # HTML 模板
│       ├── index.html # 主界面
│       └── detail.html # 接口详情弹窗
├── analyzer/          # 框架风格分析
│   └── scanner.py     # AST 扫描目标框架
├── generator/         # 代码生成
│   ├── api_gen.py     # 生成 api/ 层封装函数
│   ├── case_gen.py    # 生成 case/ 层测试用例
│   └── data_gen.py    # 生成 data/ 层 YAML 数据
├── output/            # 生成产物输出目录
│   ├── api/
│   ├── data/
│   └── case/
├── utils/             # 工具函数
│   └── common.py
├── main.py            # CLI 统一入口
└── config.py          # Skill 配置
```

### 2.2 核心流程

```
阶段1: 捕获 (Capture)
    ↓
用户运行: python main.py capture
    ↓
启动 mitmproxy 监听 localhost:8080
    ↓
用户配置浏览器代理 → 操作 Web 系统
    ↓
所有请求经过 proxy.py → 过滤 → 存入 capture.db
    ↓
Ctrl+C 停止捕获

阶段2: 筛选 (Review)
    ↓
用户运行: python main.py review
    ↓
启动 FastAPI 服务 localhost:8888
    ↓
浏览器打开 Web UI
    ↓
查看接口列表 → 按方法/关键字过滤 → 勾选需要生成的接口
    ↓
填入目标框架路径 → 点击"扫描框架"
    ↓
框架扫描器分析现有代码风格
    ↓
点击"生成用例"

阶段3: 生成 (Generate)
    ↓
读取已选接口数据
    ↓
按扫描到的框架风格生成代码
    ↓
api_gen.py → output/api/generated_*.py
data_gen.py → output/data/generated_*.yaml
case_gen.py → output/case/generated_*.py
    ↓
提示生成完成，用户审查后迁入目标框架
```

---

## 3. 模块详细设计

### 3.1 捕获模块 (capture/)

#### 3.1.1 过滤规则 (filters.py)

**自动排除：**
- 静态资源：`.js`, `.css`, `.png`, `.jpg`, `.gif`, `.ico`, `.woff`, `.svg`
- 健康检查：`/health`, `/ping`, `/actuator`, `/ready`
- 常见第三方：`/analytics`, `/sentry`, `/track`, `/log`

**用户自定义：**
- 配置文件中可添加额外排除前缀
- 支持排除特定域名

#### 3.1.2 数据存储结构

SQLite 表 `captured_requests`：

| 字段 | 类型 | 说明 |
|------|------|------|
| timestamp | DATETIME | 捕获时间 |
| method | TEXT | HTTP 方法 |
| url | TEXT | 完整 URL |
| path | TEXT | 接口路径（不含域名和 query）|
| query_params | TEXT | URL 查询参数（JSON）|
| request_body | TEXT | 请求体（JSON 或原始文本）|
| response_code | INTEGER | HTTP 状态码 |
| response_body | TEXT | 响应体（JSON 或原始文本）|
| selected | INTEGER | 是否选中生成（0/1）|

#### 3.1.3 去重策略

相同 `path` + 相同 `request_body` 结构（忽略动态值）只保留最新一条。

**动态值识别规则：**
- 字段名包含：`id`, `Id`, `token`, `Token`, `time`, `Time`, `no`, `No`, `sign`, `Sign`
- 值为时间戳格式（13位数字）
- 值为 UUID 格式

#### 3.1.4 代码实现 (proxy.py)

```python
from mitmproxy import http
from storage.db import Database
from capture.filters import should_capture

class CaptureAddon:
    def __init__(self, db_path: str):
        self.db = Database(db_path)

    def response(self, flow: http.HTTPFlow):
        # 检查是否应该捕获
        if not should_capture(flow.request):
            return

        # 提取数据
        data = {
            'timestamp': datetime.now(),
            'method': flow.request.method,
            'url': flow.request.url,
            'path': flow.request.path.split('?')[0],
            'query_params': self._parse_query(flow.request),
            'request_body': self._parse_body(flow.request),
            'response_code': flow.response.status_code,
            'response_body': self._parse_body(flow.response),
            'selected': 0
        }

        # 去重检查，保存或更新
        self.db.save_or_update(data)
```

### 3.2 存储模块 (storage/)

#### 3.2.1 Database 类 (db.py)

```python
class Database:
    def __init__(self, db_path: str):
        self.conn = sqlite3.connect(db_path)
        self._init_table()

    def save_or_update(self, data: dict):
        """保存或更新（去重）"""
        pass

    def get_all(self, filters: dict = None) -> list:
        """获取所有记录，支持过滤"""
        pass

    def update_selected(self, ids: list, selected: bool):
        """更新选中状态"""
        pass

    def get_selected(self) -> list:
        """获取所有选中的记录"""
        pass

    def clear(self):
        """清空所有数据"""
        pass
```

### 3.3 Web UI 模块 (web/)

#### 3.3.1 页面布局

```
┌─────────────────────────────────────────────────────────────┐
│  API Capture Review                    [全选] [清空] [生成用例]│
├──────────────┬──────────────────────────────────────────────┤
│ 搜索/过滤栏   │  接口列表                                     │
│              │  ☐ POST /api/order/list          200  23:41  │
│ 按方法过滤：  │  ☑ POST /api/order/pay           200  23:42  │
│ [ALL][POST]  │  ☑ POST /api/invoice/apply       200  23:43  │
│ [GET][PUT]   │  ☐ GET  /api/user/info           200  23:40  │
│              │  ☐ POST /api/static/resource     200  23:41  │
│ 关键字搜索：  ├──────────────────────────────────────────────┤
│ [_______]    │  请求详情（点击某条接口展开）                   │
│              │  Path:    /api/invoice/apply                 │
│ 批量操作：    │  Method:  POST                               │
│ [排除含字样]  │  Body:    {"tokenId":"xxx","orderId":"yyy"}  │
│              │  Response:{"code":"200","success":true}      │
│ 生成选项：    │                                              │
│ 框架路径:     │  动态字段标记：                                │
│ [_______]    │  ⚠️ tokenId - 运行时注入                     │
│ [扫描框架]   │  ⚠️ orderId - 运行时注入                     │
└──────────────┴──────────────────────────────────────────────┘
```

#### 3.3.2 功能说明

**左侧过滤栏：**
- 按 HTTP 方法过滤（ALL/GET/POST/PUT/DELETE）
- 关键字搜索（接口路径模糊匹配）
- 批量排除（输入关键字，排除所有包含该关键字的接口）

**中间列表：**
- 显示捕获的接口（方法、路径、状态码、时间）
- 复选框勾选/取消
- 点击某条展开右侧详情
- 支持全选/清空

**右侧详情：**
- 展示完整请求/响应内容
- 高亮标记动态字段（需要运行时注入的值）

**底部框架配置：**
- 输入目标框架路径
- 扫描框架按钮（触发 analyzer/scanner.py）
- 显示扫描结果摘要（识别的框架风格）

**生成按钮：**
- 点击后对选中接口生成代码
- 显示生成进度和结果
- 提示输出目录位置

#### 3.3.3 API 端点 (server.py)

```python
@app.get("/")  # 主页面
@app.get("/api/requests")  # 获取接口列表
@app.post("/api/select")  # 更新选中状态
@app.post("/api/filter")  # 应用过滤器
@app.post("/api/scan")  # 扫描目标框架
@app.post("/api/generate")  # 生成代码
```

### 3.4 框架扫描器 (analyzer/)

#### 3.4.1 扫描目标文件

```python
TARGET_FILES = [
    "conftest.py",          # pytest fixtures、配置
    "api/base.py",          # HTTP 客户端封装
    "config.py",            # 配置管理
    "case/test_*.py",       # 示例测试用例
]
```

#### 3.4.2 学习维度

**1. HTTP 客户端模式：**
```python
class HTTPClientPattern:
    library: str  # "httpx" or "requests"
    wrapper_func: str  # "safe_post"
    wrapper_signature: list  # ["client", "endpoint", "trace_id", ...]
    retry_decorator: str  # "retry_on_failure"
    error_handling: str  # "exception" or "return_bool"
```

**2. 数据管理模式：**
```python
class DataPattern:
    format: str  # "yaml" or "json"
    loader_func: str  # "load_yaml_data"
    data_dir: str  # "data/"
    injection_pattern: str  # "runtime_inject" or "template_replace"
```

**3. 测试用例模式：**
```python
class TestCasePattern:
    class_based: bool  # 是否使用 unittest.TestCase
    fixture_pattern: str  # pytest fixtures 使用方式
    assertion_style: str  # "direct" or "wrapped"
    allure_decorators: bool  # 是否使用 allure
    marker_style: str  # "critical" or "normal"
```

**4. 响应解析模式：**
```python
class ResponsePattern:
    success_field: str  # "code" or "success"
    success_value: any  # "200" or True
    error_code_path: str  # 错误码字段路径
```

#### 3.4.3 扫描实现

使用 Python `ast` 模块解析源码，提取：
- 函数定义和签名
- 装饰器使用
- 导入语句（判断使用的库）
- 特定模式的调用方式

### 3.5 代码生成器 (generator/)

#### 3.5.1 API 层生成 (api_gen.py)

**输入：**
- 选中的接口列表
- 扫描到的 HTTPClientPattern

**输出：**
- `output/api/generated_{module}.py`

**生成内容示例（适配 httpx + safe_post 风格）：**
```python
import httpx
from api.base import safe_post
import allure

ORDER_PAY_API = "/api/order/pay"
INVOICE_APPLY_API = "/api/invoice/apply"

def order_pay(client: httpx.Client, token_id: str, order_id: str,
              amount: float, **extra):
    """订单支付接口"""
    payload = {
        "tokenId": token_id,
        "orderId": order_id,
        "amount": amount
    }
    if extra:
        payload.update(extra)

    with allure.step("订单支付"):
        resp = safe_post(client, ORDER_PAY_API, json=payload)
        return resp.json()

def invoice_apply(client: httpx.Client, token_id: str,
                  order_id: str, invoice_type: str, **extra):
    """发票申请接口"""
    payload = {
        "tokenId": token_id,
        "orderId": order_id,
        "invoiceType": invoice_type
    }
    if extra:
        payload.update(extra)

    with allure.step("发票申请"):
        resp = safe_post(client, INVOICE_APPLY_API, json=payload)
        return resp.json()
```

#### 3.5.2 数据层生成 (data_gen.py)

**输出：**
- `output/data/generated_data.yaml`

**生成内容示例：**
```yaml
# 自动生成的测试数据模板
# 标记为 DYNAMIC 的字段需要在运行时注入

order_pay:
  tokenId: "DYNAMIC"      # 运行时注入 token
  orderId: "DYNAMIC"      # 运行时注入订单ID
  amount: 100.0           # 示例值，可修改
  payType: "CashPay"

invoice_apply:
  tokenId: "DYNAMIC"
  orderId: "DYNAMIC"
  invoiceType: "NORMAL"
  title: "测试公司"
  taxNo: "123456789"
```

#### 3.5.3 用例层生成 (case_gen.py)

**单接口用例（回归测试）：**
```python
import pytest
import allure
from api.generated_order import order_pay, invoice_apply
from utils.file_loader import load_yaml_data

@allure.feature("订单支付")
@allure.story("单接口回归测试")
@allure.severity(allure.severity_level.CRITICAL)
class TestOrderPay:

    def test_order_pay_success(self, client, access_token):
        """订单支付成功场景"""
        # 加载数据
        data = load_yaml_data("generated_data.yaml", "order_pay")

        # TODO: 替换为实际的 order_id
        order_id = "PLACEHOLDER"

        resp = order_pay(
            client,
            token_id=access_token,
            order_id=order_id,
            amount=data["amount"]
        )

        assert resp.get("code") == "200"
        assert resp.get("success") is True
```

**场景组合建议注释：**
```python
@allure.feature("业务流程")
@allure.story("支付开票场景")
class TestPayAndInvoiceScenario:
    """
    建议组合以下接口成场景用例：
    1. order_pay - 完成支付
    2. invoice_apply - 申请发票

    TODO: 根据需要组合成完整业务场景
    """
    pass
```

### 3.6 CLI 入口 (main.py)

```python
#!/usr/bin/env python3
"""
API Capture Skill CLI

Usage:
    python main.py capture     # 启动代理捕获
    python main.py review      # 启动 Web UI 筛选
    python main.py clear       # 清空捕获数据
"""

import click
import sys

@click.group()
def cli():
    """API 捕获与测试生成工具"""
    pass

@cli.command()
@click.option('--port', default=8080, help='代理端口')
@click.option('--db', default='capture.db', help='数据库路径')
def capture(port, db):
    """启动代理捕获流量"""
    pass

@cli.command()
@click.option('--port', default=8888, help='Web UI 端口')
@click.option('--db', default='capture.db', help='数据库路径')
def review(port, db):
    """启动 Web UI 筛选界面"""
    pass

@cli.command()
@click.confirmation_option(prompt='确定要清空所有捕获数据吗？')
@click.option('--db', default='capture.db', help='数据库路径')
def clear(db):
    """清空捕获数据"""
    pass

if __name__ == '__main__':
    cli()
```

---

## 4. 使用流程示例

### 4.1 完整使用示例

```bash
# 1. 安装依赖
pip install mitmproxy fastapi uvicorn jinja2 click

# 2. 启动代理捕获
cd api-capture-skill
python main.py capture
# 输出: 代理已启动，监听 localhost:8080
#       请配置浏览器代理后操作 Web 系统

# 3. 用户操作浏览器
#    - 配置浏览器代理: localhost:8080
#    - 正常操作 Web 系统
#    - 完成后 Ctrl+C 停止捕获

# 4. 启动 Web UI 筛选
python main.py review
# 输出: Web UI 已启动，请访问 http://localhost:8888

# 5. 在浏览器中操作 Web UI
#    - 查看捕获的接口列表
#    - 按方法/关键字过滤
#    - 勾选需要的接口
#    - 填入目标框架路径: D:/api_delivery
#    - 点击"扫描框架"
#    - 点击"生成用例"

# 6. 审查生成产物
ls output/
# api/generated_*.py
# data/generated_*.yaml
# case/generated_*.py

# 7. 手动迁入目标框架（可配合 git diff 审查）
cp output/api/* D:/api_delivery/api/
cp output/data/* D:/api_delivery/data/
cp output/case/* D:/api_delivery/case/
```

---

## 5. 扩展性设计

### 5.1 支持新框架风格

扫描器通过 AST 分析自动适配，无需修改代码即可支持新的封装模式。

### 5.2 支持自定义模板

可在 `config.py` 中配置自定义模板覆盖默认生成逻辑。

### 5.3 支持插件机制

预留 `plugins/` 目录，用户可编写自定义过滤器或生成器。

---

## 6. 边界情况处理

| 场景 | 处理方式 |
|------|----------|
| 请求/响应体过大 | 限制存储大小（如 1MB），超大内容存储摘要 |
| 非 JSON 内容 | 存储原始文本，生成代码时使用原始格式 |
| 编码问题 | 统一使用 UTF-8，失败时尝试其他编码 |
| 重复捕获 | 按 path + body 结构去重，保留最新 |
| 目标框架风格未知 | 使用默认模板（pytest + httpx） |

---

## 7. 待决策事项

1. **是否支持 WebSocket 捕获？** — 初期不考虑，HTTP 为主
2. **是否支持请求回放验证？** — 初期不考虑，专注于生成用例
3. **是否支持多用户/并发捕获？** — 初期不考虑，单机单用户使用

---

## 8. 设计批准

本设计文档已通过审查，可进入实现阶段。

- 设计日期：2026-03-22
- 批准人：用户确认
