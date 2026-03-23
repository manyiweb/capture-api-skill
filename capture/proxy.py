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
    """启动 mitmproxy"""
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
