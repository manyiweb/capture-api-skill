#!/usr/bin/env python3
"""API Capture Skill - CLI 入口"""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

import click
from config import DEFAULT_DB_PATH, DEFAULT_PROXY_PORT, DEFAULT_WEB_PORT


@click.group()
@click.version_option(version='0.1.0')
def cli():
    """API 捕获与测试生成工具"""
    pass


@cli.command()
@click.option('--port', '-p', default=DEFAULT_PROXY_PORT, help='代理端口')
@click.option('--db', '-d', default=str(DEFAULT_DB_PATH), help='数据库路径')
def capture(port, db):
    """启动代理捕获流量"""
    import signal
    import asyncio
    from capture.proxy import start_proxy

    # Windows 兼容性修复
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    click.echo(f"启动代理服务器...")
    click.echo(f"监听地址: localhost:{port}")
    click.echo(f"数据库: {db}")
    click.echo("")
    click.echo("请配置浏览器代理后操作 Web 系统")
    click.echo("按 Ctrl+C 停止捕获")
    click.echo("")

    master = None

    def signal_handler(sig, frame):
        click.echo("\n停止捕获...")
        if master:
            master.shutdown()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    try:
        master = start_proxy(db, port)
        master.run()
    except Exception as e:
        click.echo(f"错误: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--port', '-p', default=DEFAULT_WEB_PORT, help='Web UI 端口')
@click.option('--db', '-d', default=str(DEFAULT_DB_PATH), help='数据库路径')
def review(port, db):
    """启动 Web UI 筛选界面"""
    click.echo(f"启动 Web UI...")
    click.echo(f"请访问: http://localhost:{port}")
    click.echo("")

    try:
        import uvicorn
        from web.server import create_app
        app = create_app(db)
        uvicorn.run(app, host="0.0.0.0", port=port)
    except Exception as e:
        click.echo(f"错误: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.confirmation_option(prompt='确定要清空所有捕获数据吗？')
@click.option('--db', '-d', default=str(DEFAULT_DB_PATH), help='数据库路径')
def clear(db):
    """清空捕获数据"""
    from storage.db import Database

    database = Database(db)
    database.clear()
    database.close()

    click.echo("已清空所有捕获数据")


if __name__ == '__main__':
    cli()
