import json

from fastapi.testclient import TestClient

from storage.db import Database
from web.server import create_app


def test_review_api_returns_only_safe_request_summary(tmp_path):
    db_path = tmp_path / "capture.db"
    db = Database(str(db_path))
    db.save_or_update(
        {
            "method": "POST",
            "url": "https://api.example.com/auth/login",
            "path": "/auth/login",
            "query_params": "{}",
            "request_body": json.dumps({"password": "secret"}),
            "request_headers": json.dumps({"Authorization": "Bearer secret"}),
            "response_code": 200,
            "response_body": json.dumps({"token": "secret"}),
            "response_headers": "{}",
        }
    )
    db.close()

    response = TestClient(create_app(str(db_path))).get("/api/requests")

    assert response.status_code == 200
    item = response.json()[0]
    assert item["method"] == "POST"
    assert item["path"] == "/auth/login"
    assert item["response_code"] == 200
    assert "request_body" not in item
    assert "request_headers" not in item
    assert "response_body" not in item
