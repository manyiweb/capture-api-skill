#!/usr/bin/env python3
"""测试代理服务器 - 带详细日志"""

import sys
import socket

# 这是需要人工连接和 Ctrl+C 结束的诊断服务器，不应被 pytest 自动收集。
__test__ = False

def test_proxy(port=18527):
    """测试代理服务器启动"""
    print(f"[1] 创建 socket...")
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    print(f"[2] 设置 SO_REUSEADDR...")
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    print(f"[3] 绑定到 127.0.0.1:{port}...")
    server_socket.bind(('127.0.0.1', port))

    print(f"[4] 开始监听...")
    server_socket.listen(5)

    print(f"[5] 代理服务器已启动！")
    print(f"[INFO] 监听地址: 127.0.0.1:{port}")
    print(f"[INFO] 等待连接...")
    print()

    try:
        while True:
            print("[DEBUG] 等待客户端连接...")
            client_socket, addr = server_socket.accept()
            print(f"[DEBUG] 收到连接: {addr}")

            # 读取请求
            data = client_socket.recv(4096)
            print(f"[DEBUG] 收到数据: {len(data)} 字节")

            if data:
                request_line = data.split(b'\r\n')[0].decode('utf-8', errors='ignore')
                print(f"[DEBUG] 请求: {request_line}")

            # 返回简单响应
            response = b'HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n\r\nProxy is working!'
            client_socket.sendall(response)
            client_socket.close()
            print(f"[DEBUG] 响应已发送")

    except KeyboardInterrupt:
        print("\n[INFO] 停止服务器...")
        server_socket.close()

if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 18527
    test_proxy(port)
