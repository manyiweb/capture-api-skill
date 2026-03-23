#!/usr/bin/env python3
"""
改进的 HTTP 代理服务器 - 修复连接问题
"""

import sys
import json
import select
import socket
from pathlib import Path
from urllib.parse import urlparse

# 添加项目路径
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from storage.db import Database
from capture.filters import should_capture


class SimpleProxy:
    """简单的 HTTP 代理"""

    def __init__(self, host='127.0.0.1', port=18527, db_path=None):
        self.host = host
        self.port = port
        self.db = Database(str(db_path or BASE_DIR / "capture.db"))

    def start(self):
        """启动代理服务器"""
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((self.host, self.port))
        server_socket.listen(5)

        print("=" * 50)
        print("  API Capture Skill - 简单代理模式")
        print("=" * 50)
        print()
        print(f"[信息] 启动代理服务器...")
        print(f"[信息] 监听地址: {self.host}:{self.port}")
        print(f"[信息] 数据库: {self.db.db_path}")
        print()
        print(f"[提示] 请配置浏览器代理为 localhost:{self.port}")
        print(f"[提示] 按 Ctrl+C 停止捕获")
        print()
        print("=" * 50)
        print()
        print(f"[INFO] 代理已启动，开始捕获流量...")
        print()

        try:
            while True:
                client_socket, addr = server_socket.accept()
                self.handle_client(client_socket)
        except KeyboardInterrupt:
            print()
            print("[INFO] 停止捕获...")
            self.db.close()
            server_socket.close()

    def handle_client(self, client_socket):
        """处理客户端请求"""
        try:
            # 接收请求
            request_data = b''
            client_socket.settimeout(5)

            while True:
                try:
                    chunk = client_socket.recv(4096)
                    if not chunk:
                        break
                    request_data += chunk
                    if b'\r\n\r\n' in request_data:
                        # 检查是否有 Content-Length
                        headers_end = request_data.find(b'\r\n\r\n')
                        headers = request_data[:headers_end].decode('utf-8', errors='ignore')

                        if 'Content-Length:' in headers:
                            content_length = 0
                            for line in headers.split('\r\n'):
                                if line.startswith('Content-Length:'):
                                    content_length = int(line.split(':')[1].strip())
                                    break

                            body_received = len(request_data) - headers_end - 4
                            if body_received >= content_length:
                                break
                        else:
                            break
                except socket.timeout:
                    break

            if not request_data:
                client_socket.close()
                return

            # 解析请求
            request_line = request_data.split(b'\r\n')[0].decode('utf-8', errors='ignore')
            parts = request_line.split(' ')

            if len(parts) < 3:
                client_socket.close()
                return

            method = parts[0]
            url = parts[1]

            # 解析 URL
            if url.startswith('http://') or url.startswith('https://'):
                parsed = urlparse(url)
                host = parsed.hostname
                port = parsed.port or (443 if parsed.scheme == 'https' else 80)
                path = parsed.path or '/'
                if parsed.query:
                    path += '?' + parsed.query
            else:
                # 从 Host 头获取
                headers = request_data.split(b'\r\n\r\n')[0].decode('utf-8', errors='ignore')
                host = None
                for line in headers.split('\r\n'):
                    if line.lower().startswith('host:'):
                        host = line.split(':', 1)[1].strip()
                        break

                if not host:
                    client_socket.close()
                    return

                port = 80
                path = url

            # 连接到目标服务器
            try:
                target_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                target_socket.settimeout(10)
                target_socket.connect((host, port))

                # 转发请求
                target_socket.sendall(request_data)

                # 接收响应
                response_data = b''
                while True:
                    try:
                        chunk = target_socket.recv(4096)
                        if not chunk:
                            break
                        response_data += chunk
                    except socket.timeout:
                        break

                # 发送响应给客户端
                client_socket.sendall(response_data)

                # 捕获数据
                self.capture_request(method, url, request_data, response_data)

                target_socket.close()

            except Exception as e:
                error_response = (
                    b'HTTP/1.1 502 Bad Gateway\r\n'
                    b'Content-Type: text/plain\r\n'
                    b'\r\n'
                    b'Proxy Error: ' + str(e).encode('utf-8')
                )
                client_socket.sendall(error_response)

        except Exception as e:
            print(f"[ERROR] {e}")
        finally:
            client_socket.close()

    def capture_request(self, method, url, request_data, response_data):
        """捕获请求数据"""
        try:
            # 创建模拟的 request 对象用于过滤
            class MockRequest:
                def __init__(self, url, path):
                    self.url = url
                    self.path = path

            parsed = urlparse(url)
            mock_req = MockRequest(url, parsed.path)

            if not should_capture(mock_req):
                return

            # 解析请求体
            req_body = ''
            if b'\r\n\r\n' in request_data:
                req_body = request_data.split(b'\r\n\r\n', 1)[1].decode('utf-8', errors='ignore')

            # 解析响应
            resp_code = 0
            resp_body = ''
            if response_data:
                try:
                    status_line = response_data.split(b'\r\n')[0].decode('utf-8', errors='ignore')
                    resp_code = int(status_line.split(' ')[1])

                    if b'\r\n\r\n' in response_data:
                        resp_body = response_data.split(b'\r\n\r\n', 1)[1].decode('utf-8', errors='ignore')
                except:
                    pass

            data = {
                'method': method,
                'url': url,
                'path': parsed.path,
                'query_params': json.dumps(dict(parsed.query)) if parsed.query else '{}',
                'request_body': req_body,
                'response_code': resp_code,
                'response_body': resp_body[:10000],  # 限制大小
            }

            self.db.save_or_update(data)
            print(f"[CAPTURED] {method} {parsed.path} -> {resp_code}")

        except Exception as e:
            print(f"[ERROR] Failed to capture: {e}")


if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 18527
    proxy = SimpleProxy(port=port)
    proxy.start()
