#!/usr/bin/env python3
"""
mitmproxy 独立脚本
使用方式: mitmdump -s mitm_script.py --set db_path=capture.db
"""

import json
import sys
from pathlib import Path

# 添加项目路径
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from storage.db import Database
from capture.filters import should_capture
from mitmproxy import http


class CaptureAddon:
    """mitmproxy addon，用于捕获 HTTP 流量"""

    def __init__(self):
        # 从命令行参数获取数据库路径
        db_path = BASE_DIR / "capture.db"
        self.db = Database(str(db_path))
        print(f"[INFO] 数据库已连接: {db_path}")
        print(f"[INFO] 代理已启动，开始捕获流量...")
        print(f"[INFO] 按 Ctrl+C 停止捕获")

    def response(self, flow: http.HTTPFlow):
        """响应时捕获数据"""
        # 检查是否应该捕获
        if not should_capture(flow.request):
            return

        # 提取请求数据
        data = self._extract_request_data(flow)

        # 保存到数据库
        self.db.save_or_update(data)

        # 打印捕获信息
        print(f"[CAPTURED] {data['method']} {data['path']} -> {data['response_code']}")

    def _extract_request_data(self, flow: http.HTTPFlow):
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

    def _parse_body(self, content: bytes, content_type: str):
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
    def _parse_query(fields):
        """保留重复 query key。"""
        result = {}
        for key, value in fields:
            if key not in result:
                result[key] = value
            elif isinstance(result[key], list):
                result[key].append(value)
            else:
                result[key] = [result[key], value]
        return result


# mitmproxy 会自动加载这个 addon
addons = [CaptureAddon()]
