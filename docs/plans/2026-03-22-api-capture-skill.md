# API Capture Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 创建一个独立的 Skill，用于捕获浏览器 HTTP 流量并生成符合目标框架风格的 pytest 测试用例

**Architecture:** 使用 mitmproxy 作为代理捕获流量 → SQLite 存储 → FastAPI Web UI 筛选 → AST 扫描目标框架学习代码风格 → 生成 api/data/case 三层代码

**Tech Stack:** Python 3.9+, mitmproxy, FastAPI, SQLite, Jinja2, click

---

## File Structure

```
api-capture-skill/
├── capture/
│   ├── __init__.py
│   ├── proxy.py           # mitmproxy addon 实现
│   └── filters.py         # 流量过滤规则
├── storage/
│   ├── __init__.py
│   └── db.py              # SQLite 操作封装
├── web/
│   ├── __init__.py
│   ├── server.py          # FastAPI 服务
│   └── templates/
│       ├── index.html     # 主界面
│       └── detail.html    # 详情弹窗
├── analyzer/
│   ├── __init__.py
│   └── scanner.py         # AST 框架扫描器
├── generator/
│   ├── __init__.py
│   ├── base.py            # 生成器基类
│   ├── api_gen.py         # API 层生成器
│   ├── data_gen.py        # 数据层生成器
│   └── case_gen.py        # 用例层生成器
├── output/                # 生成产物目录（gitignore）
├── utils/
│   ├── __init__.py
│   └── common.py          # 通用工具函数
├── tests/                 # 单元测试
│   ├── __init__.py
│   ├── test_capture.py
│   ├── test_storage.py
│   ├── test_analyzer.py
│   └── test_generator.py
├── requirements.txt
├── config.py              # Skill 配置
├── main.py                # CLI 入口
└── capture.db             # SQLite 数据库（gitignore）
```

---

## Task 1: 项目初始化与依赖配置

**Files:**
- Create: `requirements.txt`
- Create: `config.py`
- Create: `.gitignore`
- Create: `output/.gitkeep`

- [ ] **Step 1: 创建 requirements.txt**

```txt
# Core
mitmproxy>=10.0.0
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
jinja2>=3.1.0
click>=8.1.0
pydantic>=2.0.0

# Utils
pyyaml>=6.0

# Testing
pytest>=7.4.0
pytest-asyncio>=0.21.0
httpx>=0.25.0
```

- [ ] **Step 2: 创建 config.py**

```python
"""Skill 配置"""
from pathlib import Path

# 路径配置
BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"
DEFAULT_DB_PATH = BASE_DIR / "capture.db"
DEFAULT_PROXY_PORT = 8080
DEFAULT_WEB_PORT = 8888

# 输出子目录
API_OUTPUT_DIR = OUTPUT_DIR / "api"
DATA_OUTPUT_DIR = OUTPUT_DIR / "data"
CASE_OUTPUT_DIR = OUTPUT_DIR / "case"

# 过滤配置
EXCLUDED_EXTENSIONS = {'.js', '.css', '.png', '.jpg', '.gif', '.ico', '.woff', '.svg', '.woff2'}
EXCLUDED_PATHS = {'/health', '/ping', '/actuator', '/ready'}
EXCLUDED_KEYWORDS = {'analytics', 'sentry', 'track', 'log', 'metrics'}

# 动态值识别
DYNAMIC_FIELD_PATTERNS = [
    r'[a-z]*[iI]d$',           # id, Id, tokenId
    r'[a-z]*[tT]ime$',         # time, timestamp
    r'[a-z]*[nN]o$',           # no, orderNo
    r'[a-z]*[sS]ign$',         # sign, signature
    r'^\d{13}$',               # 13位时间戳
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',  # UUID
]

# 框架扫描配置
TARGET_FILES = [
    "conftest.py",
    "api/base.py",
    "config.py",
]
```

- [ ] **Step 3: 创建 .gitignore**

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python

# Virtual environments
venv/
env/
ENV/

# IDE
.vscode/
.idea/
*.swp
*.swo

# Database
capture.db
*.db

# Output
tests/output/
output/*.py
output/*.yaml
!output/.gitkeep

# Logs
*.log
```

- [ ] **Step 4: 创建 output/.gitkeep**

```bash
# 空文件，用于保持目录结构
```

- [ ] **Step 5: 安装依赖并验证**

```bash
cd D:/picture_api_skill
pip install -r requirements.txt
python -c "import mitmproxy, fastapi, uvicorn, jinja2, click; print('All deps OK')"
```

Expected: `All deps OK`

- [ ] **Step 6: Commit**

```bash
git init
git add requirements.txt config.py .gitignore output/.gitkeep
git commit -m "chore: init project with dependencies and config"
```

---

## Task 2: 存储模块 (storage/db.py)

**Files:**
- Create: `storage/__init__.py`
- Create: `storage/db.py`
- Create: `tests/test_storage.py`

- [ ] **Step 1: 编写存储模块测试**

```python
# tests/test_storage.py
import pytest
import tempfile
import os
from storage.db import Database

@pytest.fixture
def temp_db():
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    db = Database(db_path)
    yield db
    db.close()
    os.unlink(db_path)

class TestDatabase:
    def test_init_creates_table(self, temp_db):
        """测试初始化创建表"""
        records = temp_db.get_all()
        assert records == []

    def test_save_record(self, temp_db):
        """测试保存记录"""
        data = {
            'method': 'POST',
            'url': 'http://example.com/api/test',
            'path': '/api/test',
            'query_params': '{}',
            'request_body': '{"key": "value"}',
            'response_code': 200,
            'response_body': '{"success": true}',
        }
        temp_db.save_or_update(data)

        records = temp_db.get_all()
        assert len(records) == 1
        assert records[0]['method'] == 'POST'
        assert records[0]['path'] == '/api/test'

    def test_deduplication(self, temp_db):
        """测试相同 path + body 去重"""
        data1 = {
            'method': 'POST',
            'url': 'http://example.com/api/test',
            'path': '/api/test',
            'query_params': '{}',
            'request_body': '{"key": "value"}',
            'response_code': 200,
            'response_body': '{"success": true}',
        }
        data2 = data1.copy()
        data2['response_code'] = 201  # 不同响应码

        temp_db.save_or_update(data1)
        temp_db.save_or_update(data2)

        records = temp_db.get_all()
        assert len(records) == 1  # 去重后只有一条
        assert records[0]['response_code'] == 201  # 保留最新

    def test_filter_by_method(self, temp_db):
        """测试按方法过滤"""
        temp_db.save_or_update({'method': 'GET', 'path': '/api/a', 'request_body': '{}'})
        temp_db.save_or_update({'method': 'POST', 'path': '/api/b', 'request_body': '{}'})

        records = temp_db.get_all(filters={'method': 'POST'})
        assert len(records) == 1
        assert records[0]['method'] == 'POST'

    def test_update_selected(self, temp_db):
        """测试更新选中状态"""
        data = {'method': 'POST', 'path': '/api/test', 'request_body': '{}'}
        temp_db.save_or_update(data)

        records = temp_db.get_all()
        record_id = records[0]['id']

        temp_db.update_selected([record_id], True)
        selected = temp_db.get_selected()
        assert len(selected) == 1
        assert selected[0]['selected'] == 1

    def test_clear(self, temp_db):
        """测试清空数据"""
        temp_db.save_or_update({'method': 'POST', 'path': '/api/test', 'request_body': '{}'})
        temp_db.clear()
        records = temp_db.get_all()
        assert records == []
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd D:/picture_api_skill
pytest tests/test_storage.py -v
```

Expected: `ImportError: No module named 'storage.db'`

- [ ] **Step 3: 实现 Database 类**

```python
# storage/__init__.py
from .db import Database

__all__ = ['Database']
```

```python
# storage/db.py
import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path


class Database:
    """SQLite 数据库操作封装"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_table()

    def _init_table(self):
        """初始化表结构"""
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS captured_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                method TEXT NOT NULL,
                url TEXT NOT NULL,
                path TEXT NOT NULL,
                query_params TEXT,
                request_body TEXT,
                response_code INTEGER,
                response_body TEXT,
                selected INTEGER DEFAULT 0
            )
        ''')
        self.conn.commit()

    def save_or_update(self, data: Dict):
        """保存或更新记录（去重）"""
        cursor = self.conn.cursor()

        # 检查是否存在相同 path + request_body 的记录
        cursor.execute('''
            SELECT id FROM captured_requests
            WHERE path = ? AND request_body = ?
        ''', (data.get('path', ''), data.get('request_body', '')))

        existing = cursor.fetchone()

        if existing:
            # 更新现有记录
            cursor.execute('''
                UPDATE captured_requests
                SET timestamp = CURRENT_TIMESTAMP,
                    method = ?,
                    url = ?,
                    query_params = ?,
                    response_code = ?,
                    response_body = ?,
                    selected = 0
                WHERE id = ?
            ''', (
                data.get('method'),
                data.get('url'),
                data.get('query_params', '{}'),
                data.get('response_code'),
                data.get('response_body'),
                existing['id']
            ))
        else:
            # 插入新记录
            cursor.execute('''
                INSERT INTO captured_requests
                (method, url, path, query_params, request_body, response_code, response_body)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                data.get('method'),
                data.get('url'),
                data.get('path'),
                data.get('query_params', '{}'),
                data.get('request_body', '{}'),
                data.get('response_code'),
                data.get('response_body')
            ))

        self.conn.commit()

    def get_all(self, filters: Optional[Dict] = None) -> List[Dict]:
        """获取所有记录，支持过滤"""
        cursor = self.conn.cursor()

        query = 'SELECT * FROM captured_requests WHERE 1=1'
        params = []

        if filters:
            if 'method' in filters:
                query += ' AND method = ?'
                params.append(filters['method'])
            if 'keyword' in filters:
                query += ' AND path LIKE ?'
                params.append(f'%{filters["keyword"]}%')

        query += ' ORDER BY timestamp DESC'

        cursor.execute(query, params)
        rows = cursor.fetchall()

        return [dict(row) for row in rows]

    def update_selected(self, ids: List[int], selected: bool):
        """更新选中状态"""
        cursor = self.conn.cursor()
        selected_val = 1 if selected else 0

        placeholders = ','.join('?' * len(ids))
        cursor.execute(f'''
            UPDATE captured_requests
            SET selected = ?
            WHERE id IN ({placeholders})
        ''', [selected_val] + ids)

        self.conn.commit()

    def get_selected(self) -> List[Dict]:
        """获取所有选中的记录"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM captured_requests WHERE selected = 1 ORDER BY timestamp')
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def clear(self):
        """清空所有数据"""
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM captured_requests')
        self.conn.commit()

    def close(self):
        """关闭数据库连接"""
        self.conn.close()
```

- [ ] **Step 4: 运行测试确认通过**

```bash
pytest tests/test_storage.py -v
```

Expected: 6 tests PASSED

- [ ] **Step 5: Commit**

```bash
git add storage/ tests/test_storage.py
git commit -m "feat: add storage module with SQLite operations"
```

---

## Task 3: 过滤模块 (capture/filters.py)

**Files:**
- Create: `capture/__init__.py`
- Create: `capture/filters.py`
- Create: `tests/test_capture.py`

- [ ] **Step 1: 编写过滤器测试**

```python
# tests/test_capture.py
import pytest
from capture.filters import should_capture, is_dynamic_field

class TestFilters:
    def test_should_capture_normal_api(self):
        """测试正常 API 请求应该被捕获"""
        class MockRequest:
            url = 'http://example.com/api/order/list'
            path = '/api/order/list'

        assert should_capture(MockRequest()) is True

    def test_should_exclude_js_file(self):
        """测试 JS 文件应该被排除"""
        class MockRequest:
            url = 'http://example.com/static/app.js'
            path = '/static/app.js'

        assert should_capture(MockRequest()) is False

    def test_should_exclude_health_endpoint(self):
        """测试健康检查端点应该被排除"""
        class MockRequest:
            url = 'http://example.com/health'
            path = '/health'

        assert should_capture(MockRequest()) is False

    def test_should_exclude_analytics(self):
        """测试埋点接口应该被排除"""
        class MockRequest:
            url = 'http://example.com/analytics/track'
            path = '/analytics/track'

        assert should_capture(MockRequest()) is False

class TestDynamicFieldDetection:
    def test_detect_id_field(self):
        """测试识别 ID 字段"""
        assert is_dynamic_field('orderId') is True
        assert is_dynamic_field('tokenId') is True
        assert is_dynamic_field('user_id') is True

    def test_detect_timestamp(self):
        """测试识别时间戳"""
        assert is_dynamic_field('timestamp') is True
        assert is_dynamic_field('createTime') is True

    def test_normal_field(self):
        """测试普通字段不被标记"""
        assert is_dynamic_field('name') is False
        assert is_dynamic_field('status') is False
        assert is_dynamic_field('amount') is False
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/test_capture.py -v
```

Expected: ImportError

- [ ] **Step 3: 实现过滤器**

```python
# capture/__init__.py
from .filters import should_capture
from .proxy import CaptureAddon

__all__ = ['should_capture', 'CaptureAddon']
```

```python
# capture/filters.py
import re
from typing import Any
from config import EXCLUDED_EXTENSIONS, EXCLUDED_PATHS, EXCLUDED_KEYWORDS, DYNAMIC_FIELD_PATTERNS


def should_capture(request) -> bool:
    """
    判断是否应该捕获该请求

    Args:
        request: mitmproxy HTTPFlow.request 对象

    Returns:
        bool: True 表示应该捕获
    """
    url = request.url
    path = request.path

    # 排除静态资源
    if any(url.endswith(ext) for ext in EXCLUDED_EXTENSIONS):
        return False

    # 排除特定路径
    if any(path.startswith(ep) for ep in EXCLUDED_PATHS):
        return False

    # 排除包含特定关键词的路径
    path_lower = path.lower()
    if any(kw in path_lower for kw in EXCLUDED_KEYWORDS):
        return False

    return True


def is_dynamic_field(field_name: str, value: Any = None) -> bool:
    """
    判断字段是否为动态值（需要运行时注入）

    Args:
        field_name: 字段名
        value: 字段值（可选，用于判断时间戳、UUID 等）

    Returns:
        bool: True 表示是动态字段
    """
    # 检查字段名模式
    for pattern in DYNAMIC_FIELD_PATTERNS:
        if re.match(pattern, field_name):
            return True

    # 检查值是否为时间戳
    if isinstance(value, (int, float)):
        val_str = str(int(value))
        if re.match(r'^\d{13}$', val_str):  # 13位时间戳
            return True

    # 检查值是否为 UUID
    if isinstance(value, str):
        if re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', value, re.I):
            return True

    return False


def extract_dynamic_fields(data: dict, prefix: str = '') -> list:
    """
    从嵌套字典中提取所有动态字段

    Args:
        data: 请求体字典
        prefix: 字段前缀（用于嵌套路径）

    Returns:
        list: 动态字段路径列表
    """
    dynamic_fields = []

    for key, value in data.items():
        field_path = f"{prefix}.{key}" if prefix else key

        if is_dynamic_field(key, value):
            dynamic_fields.append(field_path)
        elif isinstance(value, dict):
            dynamic_fields.extend(extract_dynamic_fields(value, field_path))
        elif isinstance(value, list) and value and isinstance(value[0], dict):
            dynamic_fields.extend(extract_dynamic_fields(value[0], field_path))

    return dynamic_fields
```

- [ ] **Step 4: 运行测试确认通过**

```bash
pytest tests/test_capture.py -v
```

Expected: 8 tests PASSED

- [ ] **Step 5: Commit**

```bash
git add capture/filters.py tests/test_capture.py
git commit -m "feat: add capture filter module"
```

---

## Task 4: 代理捕获模块 (capture/proxy.py)

**Files:**
- Create: `capture/proxy.py`
- Modify: `tests/test_capture.py` (添加测试)

- [ ] **Step 1: 编写代理模块测试**

```python
# 添加到 tests/test_capture.py
import json
from unittest.mock import Mock, MagicMock

class TestCaptureAddon:
    @pytest.fixture
    def mock_db(self):
        db = Mock()
        db.save_or_update = Mock()
        return db

    @pytest.fixture
    def mock_flow(self):
        """创建模拟的 HTTPFlow"""
        flow = Mock()
        flow.request = Mock()
        flow.request.method = 'POST'
        flow.request.url = 'http://example.com/api/test'
        flow.request.path = '/api/test'
        flow.request.query = {}
        flow.request.content = b'{"key": "value"}'
        flow.request.headers = {'Content-Type': 'application/json'}

        flow.response = Mock()
        flow.response.status_code = 200
        flow.response.content = b'{"success": true}'
        flow.response.headers = {'Content-Type': 'application/json'}

        return flow

    def test_response_captures_data(self, mock_db, mock_flow):
        """测试响应时捕获数据"""
        from capture.proxy import CaptureAddon

        addon = CaptureAddon(mock_db)
        addon.response(mock_flow)

        assert mock_db.save_or_update.called
        call_args = mock_db.save_or_update.call_args[0][0]
        assert call_args['method'] == 'POST'
        assert call_args['path'] == '/api/test'
        assert call_args['response_code'] == 200

    def test_response_skips_filtered(self, mock_db, mock_flow):
        """测试过滤的请求不捕获"""
        from capture.proxy import CaptureAddon

        mock_flow.request.url = 'http://example.com/static/app.js'

        addon = CaptureAddon(mock_db)
        addon.response(mock_flow)

        assert not mock_db.save_or_update.called
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/test_capture.py::TestCaptureAddon -v
```

Expected: ImportError

- [ ] **Step 3: 实现代理模块**

```python
# capture/proxy.py
import json
from typing import Dict, Any
from mitmproxy import http

from storage.db import Database
from capture.filters import should_capture


class CaptureAddon:
    """mitmproxy addon，用于捕获 HTTP 流量"""

    def __init__(self, db: Database):
        self.db = db

    def response(self, flow: http.HTTPFlow):
        """响应时捕获数据"""
        # 检查是否应该捕获
        if not should_capture(flow.request):
            return

        # 提取请求数据
        data = self._extract_request_data(flow)

        # 保存到数据库
        self.db.save_or_update(data)

    def _extract_request_data(self, flow: http.HTTPFlow) -> Dict[str, Any]:
        """从 HTTPFlow 中提取请求数据"""
        request = flow.request
        response = flow.response

        # 解析请求体
        request_body = self._parse_body(request.content, request.headers.get('Content-Type', ''))

        # 解析响应体
        response_body = self._parse_body(response.content, response.headers.get('Content-Type', ''))

        # 解析查询参数
        query_params = {k: v for k, v in request.query.fields}

        return {
            'method': request.method,
            'url': request.url,
            'path': request.path.split('?')[0],
            'query_params': json.dumps(query_params, ensure_ascii=False),
            'request_body': json.dumps(request_body, ensure_ascii=False) if isinstance(request_body, (dict, list)) else str(request_body),
            'response_code': response.status_code,
            'response_body': json.dumps(response_body, ensure_ascii=False) if isinstance(response_body, (dict, list)) else str(response_body),
        }

    def _parse_body(self, content: bytes, content_type: str) -> Any:
        """解析请求/响应体"""
        if not content:
            return ''

        # 尝试 UTF-8 解码
        try:
            text = content.decode('utf-8')
        except UnicodeDecodeError:
            # 尝试其他编码
            try:
                text = content.decode('gbk')
            except UnicodeDecodeError:
                return '<binary content>'

        # JSON 解析
        if 'application/json' in content_type:
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                pass

        return text


def start_proxy(db_path: str, port: int = 8080):
    """
    启动 mitmproxy

    Args:
        db_path: 数据库路径
        port: 代理端口
    """
    from mitmproxy.tools.dump import DumpMaster
    from mitmproxy import options

    db = Database(db_path)
    addon = CaptureAddon(db)

    opts = options.Options(
        listen_host='0.0.0.0',
        listen_port=port,
    )

    master = DumpMaster(opts)
    master.addons.add(addon)

    return master
```

- [ ] **Step 4: 运行测试确认通过**

```bash
pytest tests/test_capture.py::TestCaptureAddon -v
```

Expected: 2 tests PASSED

- [ ] **Step 5: Commit**

```bash
git add capture/proxy.py tests/test_capture.py
git commit -m "feat: add mitmproxy capture addon"
```

---

## Task 5: Web UI 模块 (web/)

**Files:**
- Create: `web/__init__.py`
- Create: `web/server.py`
- Create: `web/templates/index.html`

- [ ] **Step 1: 创建 HTML 模板**

```html
<!-- web/templates/index.html -->
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>API Capture Review</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f5f5;
            height: 100vh;
            display: flex;
            flex-direction: column;
        }
        .header {
            background: #2c3e50;
            color: white;
            padding: 15px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .header h1 { font-size: 18px; font-weight: 500; }
        .header-actions button {
            background: #3498db;
            color: white;
            border: none;
            padding: 8px 16px;
            margin-left: 10px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
        }
        .header-actions button:hover { background: #2980b9; }
        .header-actions button.generate {
            background: #27ae60;
        }
        .header-actions button.generate:hover { background: #229954; }
        .container {
            flex: 1;
            display: flex;
            overflow: hidden;
        }
        .sidebar {
            width: 280px;
            background: white;
            border-right: 1px solid #ddd;
            padding: 20px;
            overflow-y: auto;
        }
        .filter-section {
            margin-bottom: 20px;
        }
        .filter-section h3 {
            font-size: 14px;
            color: #666;
            margin-bottom: 10px;
            text-transform: uppercase;
        }
        .method-filters {
            display: flex;
            gap: 5px;
            flex-wrap: wrap;
        }
        .method-btn {
            padding: 5px 12px;
            border: 1px solid #ddd;
            background: white;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
        }
        .method-btn.active {
            background: #3498db;
            color: white;
            border-color: #3498db;
        }
        .search-box {
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
        }
        .exclude-box {
            width: 100%;
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 13px;
            margin-top: 5px;
        }
        .exclude-btn {
            margin-top: 8px;
            width: 100%;
            padding: 8px;
            background: #e74c3c;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }
        .framework-section {
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #eee;
        }
        .framework-path {
            width: 100%;
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 13px;
        }
        .scan-btn {
            margin-top: 8px;
            width: 100%;
            padding: 8px;
            background: #9b59b6;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }
        .scan-result {
            margin-top: 10px;
            padding: 10px;
            background: #f8f9fa;
            border-radius: 4px;
            font-size: 12px;
            color: #666;
        }
        .main-content {
            flex: 1;
            display: flex;
            flex-direction: column;
        }
        .request-list {
            flex: 1;
            overflow-y: auto;
            padding: 20px;
        }
        .request-item {
            background: white;
            border: 1px solid #ddd;
            border-radius: 4px;
            margin-bottom: 10px;
            padding: 12px 15px;
            display: flex;
            align-items: center;
            cursor: pointer;
            transition: all 0.2s;
        }
        .request-item:hover {
            border-color: #3498db;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .request-item.selected {
            border-color: #27ae60;
            background: #f0fff4;
        }
        .request-checkbox {
            margin-right: 12px;
            width: 18px;
            height: 18px;
            cursor: pointer;
        }
        .request-method {
            padding: 3px 8px;
            border-radius: 3px;
            font-size: 12px;
            font-weight: 600;
            margin-right: 12px;
            min-width: 50px;
            text-align: center;
        }
        .method-GET { background: #61affe; color: white; }
        .method-POST { background: #49cc90; color: white; }
        .method-PUT { background: #fca130; color: white; }
        .method-DELETE { background: #f93e3e; color: white; }
        .request-path {
            flex: 1;
            font-size: 14px;
            color: #333;
            font-family: 'Monaco', 'Menlo', monospace;
        }
        .request-status {
            padding: 3px 8px;
            border-radius: 3px;
            font-size: 12px;
            margin-right: 10px;
        }
        .status-2xx { background: #d4edda; color: #155724; }
        .status-4xx { background: #f8d7da; color: #721c24; }
        .status-5xx { background: #fff3cd; color: #856404; }
        .request-time {
            font-size: 12px;
            color: #999;
        }
        .detail-panel {
            height: 300px;
            background: white;
            border-top: 1px solid #ddd;
            padding: 20px;
            overflow-y: auto;
            display: none;
        }
        .detail-panel.active {
            display: block;
        }
        .detail-section {
            margin-bottom: 20px;
        }
        .detail-section h4 {
            font-size: 13px;
            color: #666;
            margin-bottom: 8px;
            text-transform: uppercase;
        }
        .detail-content {
            background: #f8f9fa;
            padding: 12px;
            border-radius: 4px;
            font-family: 'Monaco', 'Menlo', monospace;
            font-size: 13px;
            white-space: pre-wrap;
            word-break: break-all;
        }
        .dynamic-field {
            color: #e74c3c;
            font-weight: 600;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>API Capture Review</h1>
        <div class="header-actions">
            <button onclick="selectAll()">全选</button>
            <button onclick="clearAll()">清空</button>
            <button class="generate" onclick="generate()">生成用例</button>
        </div>
    </div>

    <div class="container">
        <div class="sidebar">
            <div class="filter-section">
                <h3>HTTP 方法</h3>
                <div class="method-filters">
                    <button class="method-btn active" data-method="ALL">ALL</button>
                    <button class="method-btn" data-method="GET">GET</button>
                    <button class="method-btn" data-method="POST">POST</button>
                    <button class="method-btn" data-method="PUT">PUT</button>
                    <button class="method-btn" data-method="DELETE">DELETE</button>
                </div>
            </div>

            <div class="filter-section">
                <h3>搜索</h3>
                <input type="text" class="search-box" id="searchBox" placeholder="搜索接口路径..." onkeyup="searchRequests()">
            </div>

            <div class="filter-section">
                <h3>批量排除</h3>
                <input type="text" class="exclude-box" id="excludeBox" placeholder="输入关键字排除...">
                <button class="exclude-btn" onclick="excludeByKeyword()">排除含此关键字的接口</button>
            </div>

            <div class="framework-section">
                <h3>目标框架路径</h3>
                <input type="text" class="framework-path" id="frameworkPath" placeholder="例如: D:/api_delivery">
                <button class="scan-btn" onclick="scanFramework()">扫描框架</button>
                <div class="scan-result" id="scanResult" style="display:none"></div>
            </div>
        </div>

        <div class="main-content">
            <div class="request-list" id="requestList">
                <!-- 动态加载 -->
            </div>
            <div class="detail-panel" id="detailPanel">
                <!-- 动态加载详情 -->
            </div>
        </div>
    </div>

    <script>
        let currentFilter = { method: 'ALL', keyword: '' };
        let frameworkPattern = null;

        // 加载接口列表
        function loadRequests() {
            fetch('/api/requests?' + new URLSearchParams(currentFilter))
                .then(r => r.json())
                .then(data => renderRequests(data));
        }

        function renderRequests(requests) {
            const container = document.getElementById('requestList');
            container.innerHTML = requests.map(r => `
                <div class="request-item ${r.selected ? 'selected' : ''}" data-id="${r.id}" onclick="toggleSelect(${r.id})">
                    <input type="checkbox" class="request-checkbox" ${r.selected ? 'checked' : ''} onclick="event.stopPropagation(); toggleSelect(${r.id})">
                    <span class="request-method method-${r.method}">${r.method}</span>
                    <span class="request-path">${r.path}</span>
                    <span class="request-status status-${Math.floor(r.response_code/100)}xx">${r.response_code}</span>
                    <span class="request-time">${new Date(r.timestamp).toLocaleTimeString()}</span>
                </div>
            `).join('');

            // 点击显示详情
            document.querySelectorAll('.request-item').forEach(item => {
                item.addEventListener('click', function(e) {
                    if (e.target.type !== 'checkbox') {
                        showDetail(this.dataset.id);
                    }
                });
            });
        }

        function toggleSelect(id) {
            fetch('/api/select', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ids: [id], selected: true })
            }).then(() => loadRequests());
        }

        function selectAll() {
            fetch('/api/select', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ids: 'all', selected: true })
            }).then(() => loadRequests());
        }

        function clearAll() {
            fetch('/api/select', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ids: 'all', selected: false })
            }).then(() => loadRequests());
        }

        function searchRequests() {
            currentFilter.keyword = document.getElementById('searchBox').value;
            loadRequests();
        }

        function excludeByKeyword() {
            const keyword = document.getElementById('excludeBox').value;
            if (!keyword) return;

            fetch('/api/exclude', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ keyword })
            }).then(() => loadRequests());
        }

        function scanFramework() {
            const path = document.getElementById('frameworkPath').value;
            if (!path) {
                alert('请输入框架路径');
                return;
            }

            fetch('/api/scan', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ path })
            })
            .then(r => r.json())
            .then(data => {
                frameworkPattern = data;
                document.getElementById('scanResult').style.display = 'block';
                document.getElementById('scanResult').innerHTML = `
                    <strong>扫描成功</strong><br>
                    HTTP库: ${data.library || 'unknown'}<br>
                    数据格式: ${data.data_format || 'unknown'}
                `;
            });
        }

        function generate() {
            fetch('/api/generate', { method: 'POST' })
                .then(r => r.json())
                .then(data => {
                    alert(`生成完成!\nAPI文件: ${data.api_count}\n数据文件: ${data.data_count}\n用例文件: ${data.case_count}\n\n输出目录: ${data.output_dir}`);
                });
        }

        // 方法过滤
        document.querySelectorAll('.method-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                document.querySelectorAll('.method-btn').forEach(b => b.classList.remove('active'));
                this.classList.add('active');
                currentFilter.method = this.dataset.method;
                loadRequests();
            });
        });

        // 初始化加载
        loadRequests();
    </script>
</body>
</html>
```

- [ ] **Step 2: 实现 FastAPI 服务**

```python
# web/__init__.py
from .server import create_app

__all__ = ['create_app']
```

```python
# web/server.py
import os
import sys
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

# 添加项目根目录到路径
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from storage.db import Database
from analyzer.scanner import FrameworkScanner
from generator.api_gen import APIGenerator
from generator.data_gen import DataGenerator
from generator.case_gen import CaseGenerator


class SelectRequest(BaseModel):
    ids: list
    selected: bool


class ExcludeRequest(BaseModel):
    keyword: str


class ScanRequest(BaseModel):
    path: str


def create_app(db_path: str) -> FastAPI:
    """创建 FastAPI 应用"""
    app = FastAPI(title="API Capture Review")

    db = Database(db_path)
    scanner = FrameworkScanner()

    # 模板目录
    templates_dir = Path(__file__).parent / "templates"
    templates = Jinja2Templates(directory=str(templates_dir))

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        """主页面"""
        return templates.TemplateResponse("index.html", {"request": request})

    @app.get("/api/requests")
    async def get_requests(method: Optional[str] = None, keyword: Optional[str] = None):
        """获取接口列表"""
        filters = {}
        if method and method != 'ALL':
            filters['method'] = method
        if keyword:
            filters['keyword'] = keyword

        records = db.get_all(filters)
        return records

    @app.post("/api/select")
    async def update_selected(req: SelectRequest):
        """更新选中状态"""
        if req.ids == 'all':
            # 全选/清空
            records = db.get_all()
            ids = [r['id'] for r in records]
        else:
            ids = req.ids

        db.update_selected(ids, req.selected)
        return {"success": True}

    @app.post("/api/exclude")
    async def exclude_by_keyword(req: ExcludeRequest):
        """按关键字排除"""
        records = db.get_all()
        ids_to_exclude = [
            r['id'] for r in records
            if req.keyword.lower() in r['path'].lower()
        ]
        if ids_to_exclude:
            db.update_selected(ids_to_exclude, False)
        return {"excluded": len(ids_to_exclude)}

    @app.post("/api/scan")
    async def scan_framework(req: ScanRequest):
        """扫描目标框架"""
        pattern = scanner.scan(req.path)
        return pattern.to_dict() if pattern else {}

    @app.post("/api/generate")
    async def generate_code():
        """生成代码"""
        selected = db.get_selected()
        if not selected:
            return {"error": "没有选中的接口"}

        # 获取框架模式
        pattern = scanner.last_pattern

        # 创建生成器
        api_gen = APIGenerator(pattern)
        data_gen = DataGenerator(pattern)
        case_gen = CaseGenerator(pattern)

        # 生成代码
        from config import API_OUTPUT_DIR, DATA_OUTPUT_DIR, CASE_OUTPUT_DIR

        api_files = api_gen.generate(selected, API_OUTPUT_DIR)
        data_files = data_gen.generate(selected, DATA_OUTPUT_DIR)
        case_files = case_gen.generate(selected, CASE_OUTPUT_DIR)

        return {
            "success": True,
            "api_count": len(api_files),
            "data_count": len(data_files),
            "case_count": len(case_files),
            "output_dir": str(Path(__file__).parent.parent / "output")
        }

    return app


def start_web_server(db_path: str, port: int = 8888):
    """启动 Web 服务器"""
    import uvicorn

    app = create_app(db_path)
    uvicorn.run(app, host="0.0.0.0", port=port)
```

- [ ] **Step 3: Commit**

```bash
git add web/
git commit -m "feat: add FastAPI web UI for request review"
```

---

## Task 6: 框架扫描器 (analyzer/scanner.py)

**Files:**
- Create: `analyzer/__init__.py`
- Create: `analyzer/scanner.py`
- Create: `tests/test_analyzer.py`

- [ ] **Step 1: 编写扫描器测试**

```python
# tests/test_analyzer.py
import pytest
import tempfile
import os
from pathlib import Path
from analyzer.scanner import FrameworkScanner

class TestFrameworkScanner:
    @pytest.fixture
    def sample_framework(self):
        """创建模拟框架结构"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建 conftest.py
            conftest = Path(tmpdir) / "conftest.py"
            conftest.write_text('''
import pytest
import httpx

@pytest.fixture
def client():
    return httpx.Client()
''')

            # 创建 api/base.py
            api_dir = Path(tmpdir) / "api"
            api_dir.mkdir()
            base_py = api_dir / "base.py"
            base_py.write_text('''
import httpx
from functools import wraps

def retry_on_failure(max_retries=3):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for i in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception:
                    if i == max_retries - 1:
                        raise
        return wrapper
    return decorator

def safe_post(client, endpoint, trace_id=None, **kwargs):
    """带重试的 POST 请求"""
    headers = kwargs.pop('headers', {})
    if trace_id:
        headers['X-Trace-Id'] = trace_id
    return client.post(endpoint, headers=headers, **kwargs)
''')

            # 创建 config.py
            config_py = Path(tmpdir) / "config.py"
            config_py.write_text('''
import os

BASE_URL = os.getenv('BASE_URL', 'http://localhost:8080')
RETRY_TIMES = 3
RETRY_INTERVAL = 1
''')

            yield tmpdir

    def test_scan_detects_httpx(self, sample_framework):
        """测试检测 httpx 库"""
        scanner = FrameworkScanner()
        pattern = scanner.scan(sample_framework)

        assert pattern is not None
        assert pattern.library == "httpx"

    def test_scan_detects_wrapper(self, sample_framework):
        """测试检测封装函数"""
        scanner = FrameworkScanner()
        pattern = scanner.scan(sample_framework)

        assert pattern.wrapper_func == "safe_post"
        assert "client" in pattern.wrapper_params
        assert "endpoint" in pattern.wrapper_params
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/test_analyzer.py -v
```

Expected: ImportError

- [ ] **Step 3: 实现扫描器**

```python
# analyzer/__init__.py
from .scanner import FrameworkScanner, FrameworkPattern

__all__ = ['FrameworkScanner', 'FrameworkPattern']
```

```python
# analyzer/scanner.py
import ast
import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional, Dict


@dataclass
class FrameworkPattern:
    """框架模式定义"""
    # HTTP 客户端
    library: str = "httpx"  # httpx 或 requests

    # 封装函数
    wrapper_func: str = "safe_post"
    wrapper_params: List[str] = field(default_factory=list)

    # 数据管理
    data_format: str = "yaml"  # yaml 或 json
    data_loader: str = "load_yaml_data"

    # 测试模式
    use_fixtures: bool = True
    use_allure: bool = True
    assertion_style: str = "direct"  # direct 或 wrapped

    # 响应解析
    success_field: str = "code"
    success_value: str = "200"

    def to_dict(self) -> dict:
        return {
            'library': self.library,
            'wrapper_func': self.wrapper_func,
            'data_format': self.data_format,
            'use_allure': self.use_allure,
            'success_field': self.success_field,
        }


class FrameworkScanner:
    """AST 框架扫描器"""

    def __init__(self):
        self.last_pattern: Optional[FrameworkPattern] = None

    def scan(self, framework_path: str) -> Optional[FrameworkPattern]:
        """
        扫描目标框架，学习代码风格

        Args:
            framework_path: 框架根目录路径

        Returns:
            FrameworkPattern: 识别出的框架模式
        """
        path = Path(framework_path)
        if not path.exists():
            return None

        pattern = FrameworkPattern()

        # 扫描各个文件
        self._scan_conftest(path, pattern)
        self._scan_api_base(path, pattern)
        self._scan_config(path, pattern)

        self.last_pattern = pattern
        return pattern

    def _scan_conftest(self, path: Path, pattern: FrameworkPattern):
        """扫描 conftest.py"""
        conftest = path / "conftest.py"
        if not conftest.exists():
            return

        try:
            tree = ast.parse(conftest.read_text(encoding='utf-8'))

            for node in ast.walk(tree):
                # 检查导入
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name == 'httpx':
                            pattern.library = 'httpx'
                        elif alias.name == 'requests':
                            pattern.library = 'requests'

                # 检查 fixture
                if isinstance(node, ast.FunctionDef):
                    for decorator in node.decorator_list:
                        if isinstance(decorator, ast.Call):
                            if getattr(decorator.func, 'id', '') == 'pytest_fixture':
                                pattern.use_fixtures = True
        except SyntaxError:
            pass

    def _scan_api_base(self, path: Path, pattern: FrameworkPattern):
        """扫描 api/base.py"""
        base_py = path / "api" / "base.py"
        if not base_py.exists():
            base_py = path / "utils" / "http.py"

        if not base_py.exists():
            return

        try:
            tree = ast.parse(base_py.read_text(encoding='utf-8'))

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # 查找主要的请求封装函数
                    if any(kw in node.name.lower() for kw in ['post', 'request', 'safe', 'call']):
                        pattern.wrapper_func = node.name
                        pattern.wrapper_params = [arg.arg for arg in node.args.args]
                        break
        except SyntaxError:
            pass

    def _scan_config(self, path: Path, pattern: FrameworkPattern):
        """扫描 config.py"""
        config_py = path / "config.py"
        if not config_py.exists():
            return

        try:
            content = config_py.read_text(encoding='utf-8')

            # 检查是否使用 allure
            if 'allure' in content.lower():
                pattern.use_allure = True

            # 检查响应成功字段
            if 'success' in content.lower():
                pattern.success_field = 'success'
                pattern.success_value = 'True'
        except:
            pass

    def _scan_data_files(self, path: Path, pattern: FrameworkPattern):
        """扫描数据文件确定格式"""
        data_dir = path / "data"
        if not data_dir.exists():
            return

        # 检查是否有 yaml 文件
        yaml_files = list(data_dir.glob("*.yaml")) + list(data_dir.glob("*.yml"))
        if yaml_files:
            pattern.data_format = "yaml"
            return

        # 检查是否有 json 文件
        json_files = list(data_dir.glob("*.json"))
        if json_files:
            pattern.data_format = "json"
```

- [ ] **Step 4: 运行测试确认通过**

```bash
pytest tests/test_analyzer.py -v
```

Expected: 2 tests PASSED

- [ ] **Step 5: Commit**

```bash
git add analyzer/ tests/test_analyzer.py
git commit -m "feat: add AST framework scanner"
```

---

## Task 7: 代码生成器 (generator/)

**Files:**
- Create: `generator/__init__.py`
- Create: `generator/base.py`
- Create: `generator/api_gen.py`
- Create: `generator/data_gen.py`
- Create: `generator/case_gen.py`
- Create: `tests/test_generator.py`

- [ ] **Step 1: 编写生成器测试**

```python
# tests/test_generator.py
import pytest
import tempfile
from pathlib import Path
from analyzer.scanner import FrameworkPattern
from generator.api_gen import APIGenerator
from generator.data_gen import DataGenerator
from generator.case_gen import CaseGenerator

class TestAPIGenerator:
    def test_generate_api_function(self):
        """测试生成 API 函数"""
        pattern = FrameworkPattern(
            library="httpx",
            wrapper_func="safe_post",
            wrapper_params=["client", "endpoint"]
        )

        gen = APIGenerator(pattern)

        records = [{
            'method': 'POST',
            'path': '/api/order/pay',
            'request_body': '{"orderId": "123", "amount": 100}',
            'response_body': '{"code": "200", "success": true}'
        }]

        with tempfile.TemporaryDirectory() as tmpdir:
            files = gen.generate(records, Path(tmpdir))
            assert len(files) > 0

            content = files[0].read_text()
            assert 'def order_pay' in content
            assert 'safe_post' in content
            assert 'orderId' in content

class TestDataGenerator:
    def test_generate_yaml_data(self):
        """测试生成 YAML 数据"""
        pattern = FrameworkPattern(data_format="yaml")
        gen = DataGenerator(pattern)

        records = [{
            'path': '/api/order/pay',
            'request_body': '{"orderId": "123", "amount": 100}'
        }]

        with tempfile.TemporaryDirectory() as tmpdir:
            files = gen.generate(records, Path(tmpdir))
            assert len(files) > 0

            content = files[0].read_text()
            assert 'order_pay:' in content
            assert 'DYNAMIC' in content  # 动态字段标记

class TestCaseGenerator:
    def test_generate_test_case(self):
        """测试生成测试用例"""
        pattern = FrameworkPattern(use_allure=True)
        gen = CaseGenerator(pattern)

        records = [{
            'path': '/api/order/pay',
            'method': 'POST',
            'request_body': '{"orderId": "123"}'
        }]

        with tempfile.TemporaryDirectory() as tmpdir:
            files = gen.generate(records, Path(tmpdir))
            assert len(files) > 0

            content = files[0].read_text()
            assert 'def test_' in content
            assert '@allure.feature' in content
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/test_generator.py -v
```

Expected: ImportError

- [ ] **Step 3: 实现生成器基类**

```python
# generator/__init__.py
from .api_gen import APIGenerator
from .data_gen import DataGenerator
from .case_gen import CaseGenerator

__all__ = ['APIGenerator', 'DataGenerator', 'CaseGenerator']
```

```python
# generator/base.py
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Any

from analyzer.scanner import FrameworkPattern


class BaseGenerator(ABC):
    """生成器基类"""

    def __init__(self, pattern: FrameworkPattern):
        self.pattern = pattern

    @abstractmethod
    def generate(self, records: List[Dict], output_dir: Path) -> List[Path]:
        """生成代码文件"""
        pass

    def _path_to_func_name(self, path: str) -> str:
        """将 API 路径转换为函数名"""
        # 移除开头的 /api/
        path = re.sub(r'^/api/', '', path)
        # 替换 / 和 _ 为驼峰
        parts = re.split(r'[/_.-]', path)
        return '_'.join(p.lower() for p in parts if p)

    def _path_to_module_name(self, path: str) -> str:
        """将 API 路径转换为模块名"""
        path = re.sub(r'^/api/', '', path)
        parts = path.split('/')
        return parts[0] if parts else 'default'
```

- [ ] **Step 4: 实现 API 生成器**

```python
# generator/api_gen.py
import json
from pathlib import Path
from typing import List, Dict

from generator.base import BaseGenerator
from capture.filters import extract_dynamic_fields


class APIGenerator(BaseGenerator):
    """API 层代码生成器"""

    def generate(self, records: List[Dict], output_dir: Path) -> List[Path]:
        """生成 API 封装函数"""
        output_dir.mkdir(parents=True, exist_ok=True)

        # 按模块分组
        modules = {}
        for record in records:
            module = self._path_to_module_name(record['path'])
            if module not in modules:
                modules[module] = []
            modules[module].append(record)

        generated_files = []

        for module_name, module_records in modules.items():
            file_path = output_dir / f"generated_{module_name}.py"
            content = self._generate_module(module_name, module_records)
            file_path.write_text(content, encoding='utf-8')
            generated_files.append(file_path)

        return generated_files

    def _generate_module(self, module_name: str, records: List[Dict]) -> str:
        """生成单个模块的代码"""
        lines = [
            '"""自动生成的 API 接口封装"""',
            '',
            f'import {self.pattern.library}',
        ]

        if self.pattern.use_allure:
            lines.append('import allure')

        lines.extend([
            '',
            f'from api.base import {self.pattern.wrapper_func}',
            '',
        ])

        # API 常量定义
        for record in records:
            func_name = self._path_to_func_name(record['path'])
            const_name = func_name.upper() + '_API'
            lines.append(f'{const_name} = "{record["path"]}"')

        lines.append('')

        # 函数定义
        for record in records:
            func_lines = self._generate_function(record)
            lines.extend(func_lines)
            lines.append('')

        return '\n'.join(lines)

    def _generate_function(self, record: Dict) -> List[str]:
        """生成单个 API 函数"""
        func_name = self._path_to_func_name(record['path'])
        const_name = func_name.upper() + '_API'

        # 解析请求体
        try:
            body = json.loads(record.get('request_body', '{}') or '{}')
        except json.JSONDecodeError:
            body = {}

        # 提取参数
        params = []
        dynamic_fields = extract_dynamic_fields(body)

        for key in body.keys():
            if key in dynamic_fields or key in ['tokenId', 'token', 'userId', 'timestamp']:
                params.append(f'{key.replace("Id", "_id").replace("ID", "_id").lower()}: str')
            else:
                # 从示例值推断类型
                value = body[key]
                if isinstance(value, bool):
                    param_type = 'bool'
                elif isinstance(value, int):
                    param_type = 'int'
                elif isinstance(value, float):
                    param_type = 'float'
                else:
                    param_type = 'str'
                params.append(f'{key}: {param_type} = {repr(value)}')

        # 添加 client 参数
        client_param = f'client: {self.pattern.library}.Client'
        if self.pattern.wrapper_params and 'trace_id' in self.pattern.wrapper_params:
            params.insert(0, 'trace_id: str = None')
        params.insert(0, client_param)

        lines = [
            f'def {func_name}({", ".join(params)}):',
            f'    """{record["path"]}"""',
            '    payload = {',
        ]

        # payload 内容
        for key in body.keys():
            param_name = key.replace('Id', '_id').replace('ID', '_id').lower()
            lines.append(f'        "{key}": {param_name},')

        lines.extend([
            '    }',
            '',
            '    # 添加额外参数',
            '    if extra:',
            '        payload.update(extra)',
            '',
        ])

        # 调用封装函数
        if self.pattern.use_allure:
            lines.extend([
                f'    with allure.step("调用 {func_name}"):',
                '        ',
            ])

        wrapper_call = f'{self.pattern.wrapper_func}(client, {const_name}'
        if 'trace_id' in self.pattern.wrapper_params:
            wrapper_call += ', trace_id=trace_id'
        wrapper_call += ', json=payload)'

        lines.extend([
            f'        resp = {wrapper_call}',
            '        return resp.json()',
        ])

        return lines
```

- [ ] **Step 5: 实现数据生成器**

```python
# generator/data_gen.py
import json
from pathlib import Path
from typing import List, Dict, Any

from generator.base import BaseGenerator
from capture.filters import is_dynamic_field, extract_dynamic_fields


class DataGenerator(BaseGenerator):
    """数据层代码生成器"""

    def generate(self, records: List[Dict], output_dir: Path) -> List[Path]:
        """生成数据文件"""
        output_dir.mkdir(parents=True, exist_ok=True)

        if self.pattern.data_format == 'yaml':
            return self._generate_yaml(records, output_dir)
        else:
            return self._generate_json(records, output_dir)

    def _generate_yaml(self, records: List[Dict], output_dir: Path) -> List[Path]:
        """生成 YAML 数据文件"""
        file_path = output_dir / "generated_data.yaml"

        lines = [
            '# 自动生成的测试数据模板',
            '# 标记为 DYNAMIC 的字段需要在运行时注入',
            '',
        ]

        for record in records:
            func_name = self._path_to_func_name(record['path'])
            lines.append(f'{func_name}:')

            # 解析请求体
            try:
                body = json.loads(record.get('request_body', '{}') or '{}')
            except json.JSONDecodeError:
                body = {}

            # 识别动态字段
            dynamic_fields = extract_dynamic_fields(body)

            for key, value in body.items():
                field_path = key
                if field_path in dynamic_fields:
                    lines.append(f'  {key}: "DYNAMIC"  # 运行时注入 {key}')
                else:
                    formatted_value = self._format_yaml_value(value)
                    lines.append(f'  {key}: {formatted_value}')

            lines.append('')

        file_path.write_text('\n'.join(lines), encoding='utf-8')
        return [file_path]

    def _generate_json(self, records: List[Dict], output_dir: Path) -> List[Path]:
        """生成 JSON 数据文件"""
        file_path = output_dir / "generated_data.json"

        data = {}
        for record in records:
            func_name = self._path_to_func_name(record['path'])

            try:
                body = json.loads(record.get('request_body', '{}') or '{}')
            except json.JSONDecodeError:
                body = {}

            dynamic_fields = extract_dynamic_fields(body)

            # 处理动态字段
            processed_body = {}
            for key, value in body.items():
                if key in dynamic_fields:
                    processed_body[key] = "DYNAMIC"
                else:
                    processed_body[key] = value

            data[func_name] = processed_body

        file_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding='utf-8'
        )
        return [file_path]

    def _format_yaml_value(self, value: Any) -> str:
        """格式化 YAML 值"""
        if isinstance(value, str):
            if ':' in value or '\n' in value:
                return f'"{value}"'
            return value
        elif isinstance(value, bool):
            return str(value).lower()
        elif isinstance(value, (int, float)):
            return str(value)
        elif isinstance(value, list):
            return str(value)
        elif isinstance(value, dict):
            return str(value)
        return str(value)
```

- [ ] **Step 6: 实现用例生成器**

```python
# generator/case_gen.py
import json
from pathlib import Path
from typing import List, Dict

from generator.base import BaseGenerator
from capture.filters import extract_dynamic_fields


class CaseGenerator(BaseGenerator):
    """测试用例生成器"""

    def generate(self, records: List[Dict], output_dir: Path) -> List[Path]:
        """生成测试用例"""
        output_dir.mkdir(parents=True, exist_ok=True)

        file_path = output_dir / "generated_cases.py"
        content = self._generate_test_file(records)
        file_path.write_text(content, encoding='utf-8')

        return [file_path]

    def _generate_test_file(self, records: List[Dict]) -> str:
        """生成测试文件"""
        lines = [
            '"""自动生成的接口测试用例"""',
            '',
            'import pytest',
        ]

        if self.pattern.use_allure:
            lines.append('import allure')

        lines.extend([
            '',
            'from api.generated_order import *',
            'from utils.file_loader import load_yaml_data',
            '',
        ])

        # 按模块分组
        modules = {}
        for record in records:
            module = self._path_to_module_name(record['path'])
            if module not in modules:
                modules[module] = []
            modules[module].append(record)

        # 为每个模块生成测试类
        for module_name, module_records in modules.items():
            lines.extend(self._generate_test_class(module_name, module_records))
            lines.append('')

        return '\n'.join(lines)

    def _generate_test_class(self, module_name: str, records: List[Dict]) -> List[str]:
        """生成测试类"""
        class_name = 'Test' + ''.join(w.capitalize() for w in module_name.split('_'))

        lines = []

        if self.pattern.use_allure:
            lines.append(f'@allure.feature("{module_name}")')

        lines.append(f'class {class_name}:');
        lines.append(f'    """{module_name} 接口测试"""')
        lines.append('')

        for record in records:
            test_lines = self._generate_test_method(record)
            lines.extend(test_lines)
            lines.append('')

        return lines

    def _generate_test_method(self, record: Dict) -> List[str]:
        """生成单个测试方法"""
        func_name = self._path_to_func_name(record['path'])
        test_name = f'test_{func_name}_success'

        # 解析请求体
        try:
            body = json.loads(record.get('request_body', '{}') or '{}')
        except json.JSONDecodeError:
            body = {}

        dynamic_fields = extract_dynamic_fields(body)

        lines = []

        if self.pattern.use_allure:
            lines.extend([
                f'    @allure.story("{func_name}")',
                f'    @allure.severity(allure.severity_level.NORMAL)',
            ])

        lines.extend([
            f'    def {test_name}(self, client, access_token):',
            f'        """测试 {record["path"]} 接口"""',
            '',
        ])

        # 加载数据
        lines.append('        # 加载测试数据')
        if self.pattern.data_format == 'yaml':
            lines.append(f'        data = load_yaml_data("generated_data.yaml", "{func_name}")')
        else:
            lines.append(f'        data = load_json_data("generated_data.json")["{func_name}"]')
        lines.append('')

        # 动态字段处理
        for field in dynamic_fields:
            field_name = field.replace('Id', '_id').replace('ID', '_id').lower()
            lines.append(f'        # TODO: 设置实际的 {field}')
            lines.append(f'        {field_name} = "PLACEHOLDER"')

        if dynamic_fields:
            lines.append('')

        # 调用 API
        lines.append('        # 调用接口')

        call_args = ['client']
        if 'trace_id' in self.pattern.wrapper_params:
            call_args.append('trace_id=access_token')

        for key in body.keys():
            if key in dynamic_fields:
                call_args.append(f'{key.replace("Id", "_id").replace("ID", "_id").lower()}={key.replace("Id", "_id").replace("ID", "_id").lower()}')
            else:
                call_args.append(f'{key}=data["{key}"]')

        lines.append(f'        resp = {func_name}({", ".join(call_args)})')
        lines.append('')

        # 断言
        lines.append('        # 断言响应')
        if self.pattern.success_field == 'code':
            lines.append(f'        assert resp.get("code") == "{self.pattern.success_value}"')
        else:
            lines.append(f'        assert resp.get("{self.pattern.success_field}") == {self.pattern.success_value}')

        return lines
```

- [ ] **Step 7: 运行测试确认通过**

```bash
pytest tests/test_generator.py -v
```

Expected: 3 tests PASSED

- [ ] **Step 8: Commit**

```bash
git add generator/ tests/test_generator.py
git commit -m "feat: add code generators for api/data/case layers"
```

---

## Task 8: CLI 入口 (main.py)

**Files:**
- Create: `main.py`

- [ ] **Step 1: 实现 CLI 入口**

```python
#!/usr/bin/env python3
"""
API Capture Skill - CLI 入口

Usage:
    python main.py capture     # 启动代理捕获
    python main.py review      # 启动 Web UI 筛选
    python main.py clear       # 清空捕获数据
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

import click
from config import DEFAULT_DB_PATH, DEFAULT_PROXY_PORT, DEFAULT_WEB_PORT


@click.group()
@click.version_option(version='0.1.0')
def cli():
    """API 捕获与测试生成工具"""
    pass


@cli.command()
@click.option('--port', '-p', default=DEFAULT_PROXY_PORT, help='代理端口 (默认: 8080)')
@click.option('--db', '-d', default=str(DEFAULT_DB_PATH), help='数据库路径')
def capture(port, db):
    """启动代理捕获流量"""
    import signal
    from capture.proxy import start_proxy

    click.echo(f"启动代理服务器...")
    click.echo(f"监听地址: localhost:{port}")
    click.echo(f"数据库: {db}")
    click.echo("")
    click.echo("请配置浏览器代理后操作 Web 系统")
    click.echo("按 Ctrl+C 停止捕获")
    click.echo("")

    master = None

    def signal_handler(sig, frame):
        click.echo("\n停止捕获...")
        if master:
            master.shutdown()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    try:
        master = start_proxy(db, port)
        master.run()
    except Exception as e:
        click.echo(f"错误: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--port', '-p', default=DEFAULT_WEB_PORT, help='Web UI 端口 (默认: 8888)')
@click.option('--db', '-d', default=str(DEFAULT_DB_PATH), help='数据库路径')
def review(port, db):
    """启动 Web UI 筛选界面"""
    from web.server import start_web_server

    click.echo(f"启动 Web UI...")
    click.echo(f"请访问: http://localhost:{port}")
    click.echo("")

    try:
        start_web_server(db, port)
    except Exception as e:
        click.echo(f"错误: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.confirmation_option(prompt='确定要清空所有捕获数据吗？')
@click.option('--db', '-d', default=str(DEFAULT_DB_PATH), help='数据库路径')
def clear(db):
    """清空捕获数据"""
    from storage.db import Database

    database = Database(db)
    database.clear()
    database.close()

    click.echo("已清空所有捕获数据")


if __name__ == '__main__':
    cli()
```

- [ ] **Step 2: 添加执行权限测试**

```bash
cd D:/picture_api_skill
python main.py --help
```

Expected: 显示帮助信息，包含 capture、review、clear 三个命令

```bash
python main.py capture --help
```

Expected: 显示 capture 命令的帮助

- [ ] **Step 3: Commit**

```bash
git add main.py
git commit -m "feat: add CLI entry point with capture/review/clear commands"
```

---

## Task 9: 工具函数与完善 (utils/)

**Files:**
- Create: `utils/__init__.py`
- Create: `utils/common.py`

- [ ] **Step 1: 实现工具函数**

```python
# utils/__init__.py
from .common import generate_trace_id, parse_json_safe, format_code

__all__ = ['generate_trace_id', 'parse_json_safe', 'format_code']
```

```python
# utils/common.py
import json
import uuid
from typing import Any


def generate_trace_id() -> str:
    """生成请求追踪 ID"""
    return str(uuid.uuid4()).replace('-', '')


def parse_json_safe(content: str or bytes, default: Any = None) -> Any:
    """
    安全解析 JSON

    Args:
        content: JSON 字符串或字节
        default: 解析失败时的默认值

    Returns:
        解析后的对象，或默认值
    """
    if not content:
        return default

    if isinstance(content, bytes):
        try:
            content = content.decode('utf-8')
        except UnicodeDecodeError:
            try:
                content = content.decode('gbk')
            except UnicodeDecodeError:
                return default

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return default


def format_code(code: str, indent: int = 4) -> str:
    """
    格式化代码缩进

    Args:
        code: 代码字符串
        indent: 缩进空格数

    Returns:
        格式化后的代码
    """
    lines = code.split('\n')
    formatted = []
    current_indent = 0

    for line in lines:
        stripped = line.strip()
        if not stripped:
            formatted.append('')
            continue

        # 减少缩进的情况
        if stripped.startswith('}') or stripped.startswith(']') or stripped.startswith('else:') or stripped.startswith('elif '):
            current_indent -= 1

        formatted.append(' ' * (current_indent * indent) + stripped)

        # 增加缩进的情况
        if stripped.endswith('{') or stripped.endswith('[') or stripped.endswith(':'):
            current_indent += 1

    return '\n'.join(formatted)
```

- [ ] **Step 2: Commit**

```bash
git add utils/
git commit -m "feat: add utility functions"
```

---

## Task 10: 集成测试与最终验证

**Files:**
- Create: `tests/test_integration.py`

- [ ] **Step 1: 编写集成测试**

```python
# tests/test_integration.py
import pytest
import tempfile
import json
from pathlib import Path

from storage.db import Database
from capture.filters import should_capture, extract_dynamic_fields
from analyzer.scanner import FrameworkScanner
from generator.api_gen import APIGenerator
from generator.data_gen import DataGenerator
from generator.case_gen import CaseGenerator


class TestIntegration:
    """集成测试"""

    def test_full_workflow(self):
        """测试完整工作流程"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 1. 创建数据库
            db_path = Path(tmpdir) / "test.db"
            db = Database(str(db_path))

            # 2. 保存捕获记录
            records = [
                {
                    'method': 'POST',
                    'url': 'http://example.com/api/order/pay',
                    'path': '/api/order/pay',
                    'query_params': '{}',
                    'request_body': json.dumps({'orderId': '12345', 'amount': 100.0}),
                    'response_code': 200,
                    'response_body': json.dumps({'code': '200', 'success': True}),
                },
                {
                    'method': 'GET',
                    'url': 'http://example.com/api/order/list',
                    'path': '/api/order/list',
                    'query_params': json.dumps({'page': 1}),
                    'request_body': '{}',
                    'response_code': 200,
                    'response_body': json.dumps({'data': []}),
                }
            ]

            for r in records:
                db.save_or_update(r)

            # 3. 标记为选中
            all_records = db.get_all()
            db.update_selected([r['id'] for r in all_records], True)
            selected = db.get_selected()
            assert len(selected) == 2

            # 4. 创建框架模式
            from analyzer.scanner import FrameworkPattern
            pattern = FrameworkPattern(
                library='httpx',
                wrapper_func='safe_post',
                use_allure=True,
                data_format='yaml'
            )

            # 5. 生成代码
            output_dir = Path(tmpdir) / "output"
            api_gen = APIGenerator(pattern)
            data_gen = DataGenerator(pattern)
            case_gen = CaseGenerator(pattern)

            api_files = api_gen.generate(selected, output_dir / "api")
            data_files = data_gen.generate(selected, output_dir / "data")
            case_files = case_gen.generate(selected, output_dir / "case")

            # 6. 验证生成结果
            assert len(api_files) > 0
            assert len(data_files) > 0
            assert len(case_files) > 0

            # 检查 API 文件内容
            api_content = api_files[0].read_text()
            assert 'def order_pay' in api_content
            assert 'safe_post' in api_content

            # 检查数据文件内容
            data_content = data_files[0].read_text()
            assert 'DYNAMIC' in data_content

            # 检查用例文件内容
            case_content = case_files[0].read_text()
            assert 'def test_' in case_content

            db.close()

    def test_dynamic_field_detection(self):
        """测试动态字段识别"""
        data = {
            'tokenId': 'abc123',
            'orderId': 'ORD-001',
            'timestamp': 1234567890123,
            'name': '测试订单',
            'amount': 100.0,
            'nested': {
                'userId': 'USR-001',
                'status': 'pending'
            }
        }

        dynamic_fields = extract_dynamic_fields(data)

        assert 'tokenId' in dynamic_fields
        assert 'orderId' in dynamic_fields
        assert 'timestamp' in dynamic_fields
        assert 'nested.userId' in dynamic_fields
        assert 'name' not in dynamic_fields
        assert 'amount' not in dynamic_fields
```

- [ ] **Step 2: 运行集成测试**

```bash
pytest tests/test_integration.py -v
```

Expected: 2 tests PASSED

- [ ] **Step 3: 创建 README 文档**

```markdown
# API Capture Skill

用于捕获浏览器 HTTP 流量并生成接口自动化测试用例的 Skill。

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动代理捕获

```bash
python main.py capture
```

配置浏览器代理为 `localhost:8080`，然后正常操作 Web 系统。

### 3. 启动 Web UI 筛选

```bash
python main.py review
```

访问 http://localhost:8888，勾选需要的接口，填入目标框架路径，点击生成。

### 4. 查看生成产物

生成的代码位于 `output/` 目录：
- `api/` - API 封装函数
- `data/` - 测试数据文件
- `case/` - 测试用例

### 5. 迁入目标框架

将生成的文件复制到你的自动化框架中，按需调整。

## 命令参考

```bash
python main.py capture [--port 8080] [--db capture.db]    # 启动代理
python main.py review [--port 8888] [--db capture.db]     # 启动 Web UI
python main.py clear [--db capture.db]                    # 清空数据
```

## 目录结构

```
api-capture-skill/
├── capture/      # 代理捕获模块
├── storage/      # SQLite 存储
├── web/          # FastAPI Web UI
├── analyzer/     # 框架风格扫描器
├── generator/    # 代码生成器
├── output/       # 生成产物目录
└── main.py       # CLI 入口
```
```

- [ ] **Step 4: Commit**

```bash
git add tests/test_integration.py README.md
git commit -m "test: add integration tests and documentation"
```

---

## Task 11: 最终审查与完成

- [ ] **Step 1: 运行所有测试**

```bash
pytest tests/ -v --tb=short
```

Expected: 所有测试 PASSED

- [ ] **Step 2: 检查代码结构**

```bash
tree -I '__pycache__|*.pyc|.git' .
```

Expected: 显示完整的项目结构

- [ ] **Step 3: 最终 Commit**

```bash
git add .
git commit -m "feat: complete API capture skill implementation"
```

---

## 执行命令速查

```bash
# 完整测试套件
pytest tests/ -v

# 单个模块测试
pytest tests/test_storage.py -v
pytest tests/test_capture.py -v
pytest tests/test_analyzer.py -v
pytest tests/test_generator.py -v

# 启动代理
cd D:/picture_api_skill
python main.py capture

# 启动 Web UI
python main.py review

# 清空数据
python main.py clear
```

---

## 注意事项

1. **依赖安装**：首次使用前确保执行 `pip install -r requirements.txt`
2. **数据库文件**：`capture.db` 默认在项目根目录，不会被 git 跟踪
3. **输出目录**：`output/` 目录下的生成产物不会被 git 跟踪
4. **代理配置**：HTTP 环境无需证书，直接配置代理即可
5. **Web UI**：使用现代浏览器访问，支持 Chrome/Firefox/Edge
