import json
import uuid
from typing import Any


def generate_trace_id() -> str:
    """生成请求追踪 ID"""
    return str(uuid.uuid4()).replace('-', '')


def parse_json_safe(content: str or bytes, default: Any = None) -> Any:
    """安全解析 JSON"""
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
