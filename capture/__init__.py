from .filters import extract_dynamic_fields, is_dynamic_field, should_capture

__all__ = ['should_capture', 'is_dynamic_field', 'extract_dynamic_fields', 'CaptureAddon', 'start_proxy']


def __getattr__(name):
    """仅在真正启动代理时导入 mitmproxy，生成器和单测无需依赖它。"""
    if name in {'CaptureAddon', 'start_proxy'}:
        from .proxy import CaptureAddon, start_proxy

        return {'CaptureAddon': CaptureAddon, 'start_proxy': start_proxy}[name]
    raise AttributeError(name)
