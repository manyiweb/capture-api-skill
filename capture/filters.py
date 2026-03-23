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
