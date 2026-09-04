import json
from typing import Dict, Any, Iterable
from mitmproxy import http

from storage.db import Database
from capture.filters import should_capture


class CaptureAddon:
    """mitmproxy addon，用于捕获 HTTP 流量"""

    def __init__(
        self,
        db: Database,
        include_hosts: Iterable[str] = (),
        api_only: bool = True,
    ):
        self.db = db
        self.include_hosts = tuple(include_hosts)
        self.api_only = api_only

    def response(self, flow: http.HTTPFlow):
        """响应时捕获数据"""
        # 检查是否应该捕获
        if not should_capture(
            flow.request,
            include_hosts=self.include_hosts,
            api_only=self.api_only,
        ):
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
        query_params = self._parse_query(request.query.fields)

        return {
            'method': request.method,
            'url': request.url,
            'path': request.path.split('?')[0],
            'query_params': json.dumps(query_params, ensure_ascii=False),
            'request_body': json.dumps(request_body, ensure_ascii=False) if isinstance(request_body, (dict, list)) else str(request_body),
            'request_headers': json.dumps(dict(request.headers.items()), ensure_ascii=False),
            'response_code': response.status_code,
            'response_body': json.dumps(response_body, ensure_ascii=False) if isinstance(response_body, (dict, list)) else str(response_body),
            'response_headers': json.dumps(dict(response.headers.items()), ensure_ascii=False),
        }

    def _parse_body(self, content: bytes, content_type: str) -> Any:
        """解析请求/响应体"""
        if not content:
            return ''

        # 尝试 UTF-8 解码
        try:
            text = content.decode('utf-8')
        except UnicodeDecodeError:
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

    @staticmethod
    def _parse_query(fields) -> Dict[str, Any]:
        """保留重复 query key，避免浏览器请求信息在捕获时丢失。"""
        result: Dict[str, Any] = {}
        for key, value in fields:
            if key not in result:
                result[key] = value
            elif isinstance(result[key], list):
                result[key].append(value)
            else:
                result[key] = [result[key], value]
        return result


def start_proxy(
    db_path: str,
    port: int = 18527,
    include_hosts: Iterable[str] = (),
    api_only: bool = True,
):
    """启动 mitmproxy"""
    import asyncio
    import sys
    from mitmproxy.tools.dump import DumpMaster
    from mitmproxy import options

    # Windows 兼容性修复
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    db = Database(db_path)
    addon = CaptureAddon(db, include_hosts=include_hosts, api_only=api_only)

    opts = options.Options(
        listen_host='0.0.0.0',
        listen_port=port,
    )

    master = DumpMaster(opts)
    master.addons.add(addon)

    return master
