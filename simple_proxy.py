#!/usr/bin/env python3
"""
简单的 HTTP 代理服务器 - Windows 兼容版本
不依赖 mitmproxy，使用标准库实现
"""

import sys
import json
import socket
import threading
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
import requests

# 添加项目路径
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from storage.db import Database
from capture.filters import should_capture


class ProxyHandler(BaseHTTPRequestHandler):
    """简单的 HTTP 代理处理器"""

    def do_GET(self):
        self._handle_request('GET')

    def do_POST(self):
        self._handle_request('POST')

    def do_PUT(self):
        self._handle_request('PUT')

    def do_DELETE(self):
        self._handle_request('DELETE')

    def _handle_request(self, method):
        """处理请求"""
        try:
            # 读取请求体
            content_length = int(self.headers.get('Content-Length', 0))
            request_body = self.rfile.read(content_length) if content_length > 0 else b''

            # 构造目标 URL
            url = self.path
            if not url.startswith('http'):
                url = f"http://{self.headers.get('Host', '')}{url}"

            # 创建模拟的 request 对象用于过滤
            class MockRequest:
                def __init__(self, url, path, method, headers):
                    self.url = url
                    self.path = path
                    self.method = method
                    self.headers = headers

            mock_req = MockRequest(url, urlparse(url).path, method, self.headers)

            # 转发请求
            headers = {k: v for k, v in self.headers.items()
                      if k.lower() not in ['host', 'connection']}

            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                data=request_body,
                allow_redirects=False,
                timeout=30
            )

            # 发送响应
            self.send_response(response.status_code)
            for key, value in response.headers.items():
                if key.lower() not in ['connection', 'transfer-encoding']:
                    self.send_header(key, value)
            self.end_headers()
            self.wfile.write(response.content)

            # 捕获数据
            if should_capture(mock_req):
                self._capture_data(method, url, request_body, response)
                print(f"[CAPTURED] {method} {urlparse(url).path} -> {response.status_code}")

        except Exception as e:
            print(f"[ERROR] {e}")
            self.send_error(500, str(e))

    def _capture_data(self, method, url, request_body, response):
        """保存捕获的数据"""
        try:
            parsed = urlparse(url)

            # 解析请求体
            req_body_str = ''
            if request_body:
                try:
                    req_body_str = request_body.decode('utf-8')
                except:
                    req_body_str = '<binary>'

            # 解析响应体
            resp_body_str = ''
            try:
                resp_body_str = response.text
            except:
                resp_body_str = '<binary>'

            data = {
                'method': method,
                'url': url,
                'path': parsed.path,
                'query_params': json.dumps(
                    {
                        key: values[0] if len(values) == 1 else values
                        for key, values in parse_qs(parsed.query, keep_blank_values=True).items()
                    },
                    ensure_ascii=False,
                ),
                'request_body': req_body_str,
                'request_headers': json.dumps(dict(self.headers.items()), ensure_ascii=False),
                'response_code': response.status_code,
                'response_body': resp_body_str,
                'response_headers': json.dumps(dict(response.headers), ensure_ascii=False),
            }

            self.server.db.save_or_update(data)
        except Exception as e:
            print(f"[ERROR] Failed to capture: {e}")

    def log_message(self, format, *args):
        """禁用默认日志"""
        pass


def start_simple_proxy(port=18527):
    """启动简单代理服务器"""
    db_path = BASE_DIR / "capture.db"
    db = Database(str(db_path))

    print("=" * 50)
    print("  API Capture Skill - 简单代理模式")
    print("=" * 50)
    print()
    print(f"[信息] 启动代理服务器...")
    print(f"[信息] 监听地址: localhost:{port}")
    print(f"[信息] 数据库: {db_path}")
    print()
    print(f"[提示] 请配置浏览器代理为 localhost:{port}")
    print(f"[提示] 按 Ctrl+C 停止捕获")
    print()
    print("=" * 50)
    print()
    print(f"[INFO] 数据库已连接: {db_path}")
    print(f"[INFO] 代理已启动，开始捕获流量...")
    print()

    server = HTTPServer(('localhost', port), ProxyHandler)
    server.db = db

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print()
        print("[INFO] 停止捕获...")
        db.close()
        server.shutdown()


if __name__ == '__main__':
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 18527
    start_simple_proxy(port)
