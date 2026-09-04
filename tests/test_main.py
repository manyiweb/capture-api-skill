from click.testing import CliRunner

from main import cli
from storage.db import Database


def test_capture_runs_master_inside_asyncio_loop(monkeypatch, tmp_path):
    state = {"running": False}

    class FakeMaster:
        async def run(self):
            state["running"] = True

    monkeypatch.setattr(
        "capture.proxy.start_proxy",
        lambda db, port, include_hosts, api_only: FakeMaster(),
    )

    result = CliRunner().invoke(
        cli,
        ["capture", "--port", "19527", "--db", str(tmp_path / "capture.db")],
    )

    assert result.exit_code == 0, result.output
    assert state["running"] is True


def test_capture_clears_existing_records_by_default(monkeypatch, tmp_path):
    db_path = tmp_path / "capture.db"
    db = Database(str(db_path))
    db.save_or_update(
        {
            "method": "GET",
            "url": "https://api.example.com/old",
            "path": "/old",
            "request_body": "",
        }
    )
    db.close()

    class FakeMaster:
        async def run(self):
            return None

    monkeypatch.setattr(
        "capture.proxy.start_proxy",
        lambda db, port, include_hosts, api_only: FakeMaster(),
    )

    result = CliRunner().invoke(cli, ["capture", "--db", str(db_path)])

    assert result.exit_code == 0, result.output
    assert "已清空旧捕获: 1 条" in result.output
    db = Database(str(db_path))
    assert db.get_all() == []
    db.close()


def test_capture_can_keep_existing_records(monkeypatch, tmp_path):
    db_path = tmp_path / "capture.db"
    db = Database(str(db_path))
    db.save_or_update(
        {
            "method": "GET",
            "url": "https://api.example.com/old",
            "path": "/old",
            "request_body": "",
        }
    )
    db.close()

    class FakeMaster:
        async def run(self):
            return None

    monkeypatch.setattr(
        "capture.proxy.start_proxy",
        lambda db, port, include_hosts, api_only: FakeMaster(),
    )

    result = CliRunner().invoke(
        cli,
        ["capture", "--db", str(db_path), "--keep-existing"],
    )

    assert result.exit_code == 0, result.output
    assert "历史数据: 保留" in result.output
    db = Database(str(db_path))
    assert len(db.get_all()) == 1
    db.close()
