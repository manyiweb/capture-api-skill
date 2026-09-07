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
@click.option(
    '--include-host',
    'include_hosts',
    multiple=True,
    help='只捕获该域名及其子域名；可重复传入',
)
@click.option(
    '--all-http',
    is_flag=True,
    help='同时捕获页面、脚本和图片等非 API 请求',
)
@click.option(
    '--keep-existing',
    is_flag=True,
    help='保留数据库中的历史捕获；默认启动时清空',
)
def capture(port, db, include_hosts, all_http, keep_existing):
    """启动代理捕获流量"""
    import asyncio
    from capture.proxy import start_proxy

    # Windows 兼容性修复
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    click.echo(f"启动代理服务器...")
    click.echo(f"监听地址: localhost:{port}")
    click.echo(f"数据库: {db}")
    click.echo(
        f"域名范围: {', '.join(include_hosts)}"
        if include_hosts else
        "域名范围: 全部（已排除常见第三方遥测）"
    )
    click.echo(f"捕获类型: {'全部 HTTP' if all_http else 'API 请求'}")

    if not keep_existing:
        from storage.db import Database

        database = Database(db)
        previous_count = len(database.get_all())
        database.clear()
        database.close()
        click.echo(f"已清空旧捕获: {previous_count} 条")
    else:
        click.echo("历史数据: 保留")

    click.echo("")
    click.echo("请配置浏览器代理后操作 Web 系统")
    click.echo("按 Ctrl+C 停止捕获")
    click.echo("")

    try:
        async def run_proxy():
            # mitmproxy 12 要求在运行中的事件循环内创建 DumpMaster。
            master = start_proxy(
                db,
                port,
                include_hosts=include_hosts,
                api_only=not all_http,
            )
            await master.run()

        asyncio.run(run_proxy())
    except KeyboardInterrupt:
        click.echo("\n停止捕获...")
    except Exception as e:
        click.echo(f"错误: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--url', default='about:blank', show_default=True, help='测试浏览器打开的地址')
@click.option('--proxy-host', default='127.0.0.1', show_default=True, help='捕获代理地址')
@click.option('--proxy-port', default=DEFAULT_PROXY_PORT, show_default=True, type=int, help='捕获代理端口')
@click.option(
    '--chrome-path',
    type=click.Path(exists=True, file_okay=True, dir_okay=False, path_type=Path),
    help='Chrome/Chromium 可执行文件路径',
)
@click.option(
    '--profile-dir',
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    help='自定义隔离 Profile；默认使用关闭后自动删除的临时目录',
)
@click.option('--keep-profile', is_flag=True, help='保留自动创建的临时 Profile')
@click.option('--verify-certificates', is_flag=True, help='启用证书校验；需要已信任 mitmproxy CA')
def browser(url, proxy_host, proxy_port, chrome_path, profile_dir, keep_profile, verify_certificates):
    """启动独立 Chrome，仅该实例使用捕获代理。"""
    from capture.browser import ChromeLaunchError, launch_isolated_chrome

    try:
        session = launch_isolated_chrome(
            url=url,
            proxy_host=proxy_host,
            proxy_port=proxy_port,
            chrome_path=chrome_path,
            profile_dir=profile_dir,
            keep_profile=keep_profile,
            ignore_certificate_errors=not verify_certificates,
        )
    except ChromeLaunchError as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo("已启动独立 Chrome 测试实例")
    click.echo(f"代理: http://{proxy_host}:{proxy_port}")
    click.echo(f"隔离 Profile: {session.profile_dir}")
    if not verify_certificates:
        click.echo("提示: 该测试实例已忽略证书错误，请勿用于日常浏览")
    click.echo("关闭独立 Chrome 后，此命令会自动清理临时 Profile")

    try:
        session.wait()
    except ChromeLaunchError as exc:
        raise click.ClickException(str(exc)) from exc


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
