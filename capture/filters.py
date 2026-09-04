import re
from typing import Any, Iterable
from urllib.parse import urlsplit

from config import (
    DYNAMIC_FIELD_PATTERNS,
    EXCLUDED_EXTENSIONS,
    EXCLUDED_HOST_SUFFIXES,
    EXCLUDED_KEYWORDS,
    EXCLUDED_PATHS,
)


def _host_matches(hostname: str, rule: str) -> bool:
    normalized_rule = rule.strip().lower().lstrip('.')
    return bool(normalized_rule) and (
        hostname == normalized_rule or hostname.endswith(f'.{normalized_rule}')
    )


def should_capture(
    request,
    include_hosts: Iterable[str] = (),
    api_only: bool = True,
) -> bool:
    """
    判断是否应该捕获该请求

    Args:
        request: mitmproxy HTTPFlow.request 对象

    Returns:
        bool: True 表示应该捕获
    """
    url = request.url
    path = request.path
    method = str(getattr(request, 'method', '')).upper()
    hostname = (urlsplit(url).hostname or '').lower()

    # CORS 预检不是业务 API 用例的一部分。
    if method in {'OPTIONS', 'HEAD'}:
        return False

    include_hosts = tuple(include_hosts)
    if include_hosts:
        if not any(_host_matches(hostname, rule) for rule in include_hosts):
            return False
    elif any(_host_matches(hostname, suffix) for suffix in EXCLUDED_HOST_SUFFIXES):
        return False

    # 浏览器 XHR/fetch 的 Sec-Fetch-Dest 通常为 empty。排除 document、script、
    # image 等页面资源；缺少该请求头时保留，兼容非浏览器 HTTP 客户端。
    headers = getattr(request, 'headers', {})
    fetch_dest = ''
    if hasattr(headers, 'items'):
        fetch_dest = next(
            (value for key, value in headers.items() if str(key).lower() == 'sec-fetch-dest'),
            '',
        )
    if api_only and fetch_dest and fetch_dest.lower() != 'empty':
        return False

    # 排除静态资源
    url_path = urlsplit(url).path.lower()
    if any(url_path.endswith(ext) for ext in EXCLUDED_EXTENSIONS):
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
