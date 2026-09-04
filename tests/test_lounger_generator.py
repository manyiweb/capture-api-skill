import json
from pathlib import Path

import yaml

from analyzer.scanner import FrameworkPattern
from generator.lounger_gen import LoungerGenerator


def _record(
    *,
    method: str,
    url: str,
    request_body: dict,
    request_headers: dict,
    response_body: dict,
    response_code: int = 200,
) -> dict:
    return {
        "method": method,
        "url": url,
        "path": url.split("develop-gcp-bff.trackingmore.com", 1)[-1],
        "query_params": "{}",
        "request_body": json.dumps(request_body),
        "request_headers": json.dumps(request_headers),
        "response_code": response_code,
        "response_body": json.dumps(response_body),
        "response_headers": json.dumps({"Content-Type": "application/json"}),
    }


def test_generate_lounger_login_create_flow(tmp_path: Path):
    token = "captured-secret-token-1234567890"
    password = "captured-password"
    records = [
        _record(
            method="POST",
            url="https://develop-gcp-bff.trackingmore.com/api/admin/login",
            request_body={"username": "tester@example.com", "password": password},
            request_headers={"Content-Type": "application/json", "User-Agent": "Browser"},
            response_body={"code": 0, "data": {"token": token}},
        ),
        _record(
            method="POST",
            url="https://develop-gcp-bff.trackingmore.com/api/admin/tracking/create",
            request_body={
                "tracking_number": "1Z9999999999999999",
                "courier_code": "ups",
            },
            request_headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            },
            response_body={
                "code": 0,
                "data": {"id": "package-id-123", "tracking_number": "1Z9999999999999999"},
            },
        ),
    ]

    output_dir = tmp_path / "lounger"
    files = LoungerGenerator(FrameworkPattern()).generate(
        records,
        output_dir,
        scenario_name="TM login and create package",
    )

    assert files
    case_path = output_dir / "datas" / "captured" / "test_tm_login_and_create_package.yaml"
    config_path = output_dir / "config" / "config.yaml"
    assert case_path.exists()
    assert config_path.exists()
    assert (output_dir / "test_api.py").exists()
    assert (output_dir / "conftest.py").exists()

    case_text = case_path.read_text(encoding="utf-8")
    assert token not in case_text
    assert password not in case_text
    assert "Bearer ${extract(login_token)}" in case_text
    assert "${config(login_password)}" in case_text
    assert "${unique_tracking_number()}" in case_text

    case_data = yaml.safe_load(case_text)
    login_step, create_step = case_data[0]["teststeps"]
    assert login_step["extract"] == {"login_token": "data.token"}
    assert create_step["request"]["method"] == "POST"
    assert create_step["request"]["url"] == "/api/admin/tracking/create"
    assert ["status_code", 200] in create_step["validate"]["equal"]
    assert ["body.code", 0] in create_step["validate"]["equal"]
    assert ["body.data.id", True] in create_step["validate"]["is_not_null"]

    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert config["base_url"] == "https://develop-gcp-bff.trackingmore.com"
    assert config["test_project"] == {"captured": True}
    assert config["global_test_config"]["login_username"] == "CHANGE_ME"
    assert config["global_test_config"]["login_password"] == "CHANGE_ME"


def test_generate_lounger_respects_method_query_and_form_data(tmp_path: Path):
    record = {
        "method": "PUT",
        "url": "https://example.com/orders/1?dry_run=true",
        "path": "/orders/1",
        "query_params": json.dumps({"dry_run": "true"}),
        "request_body": "name=test&enabled=1",
        "request_headers": json.dumps(
            {"Content-Type": "application/x-www-form-urlencoded", "Cookie": "secret-cookie"}
        ),
        "response_code": 204,
        "response_body": "",
        "response_headers": "{}",
    }

    output_dir = tmp_path / "lounger"
    LoungerGenerator(FrameworkPattern()).generate([record], output_dir, "update order")
    case_path = output_dir / "datas" / "captured" / "test_update_order.yaml"
    case_text = case_path.read_text(encoding="utf-8")
    case = yaml.safe_load(case_text)[0]["teststeps"][0]

    assert case["request"]["method"] == "PUT"
    assert case["request"]["params"] == {"dry_run": "true"}
    assert case["request"]["data"] == {"name": "test", "enabled": "1"}
    assert case["request"]["headers"]["Cookie"] == "${config(session_cookie)}"
    assert "secret-cookie" not in case_text


def test_login_request_token_and_key_are_parameterized(tmp_path: Path):
    request_token = "captured-one-time-login-token"
    auth_key = "captured-auth-key"
    record = _record(
        method="POST",
        url="https://develop-gcp-bff.trackingmore.com/auth/login",
        request_body={"token": request_token, "key": auth_key},
        request_headers={"Content-Type": "application/json"},
        response_body={"code": 0, "data": {"token": "response-token"}},
    )

    output_dir = tmp_path / "lounger"
    LoungerGenerator(FrameworkPattern()).generate([record], output_dir, "secure login")
    case_text = (
        output_dir / "datas" / "captured" / "test_secure_login.yaml"
    ).read_text(encoding="utf-8")

    assert request_token not in case_text
    assert auth_key not in case_text
    assert "${config(login_request_token)}" in case_text
    assert "${config(login_request_key)}" in case_text


def test_form_encoded_login_credentials_are_parameterized(tmp_path: Path):
    record = {
        "method": "POST",
        "url": "https://www.trackingmore.com/loginaction.php",
        "path": "/loginaction.php",
        "query_params": "{}",
        "request_body": "email=user%40example.com&password=raw-password&token=raw-login-token",
        "request_headers": json.dumps(
            {"Content-Type": "application/x-www-form-urlencoded"}
        ),
        "response_code": 200,
        "response_body": json.dumps({"code": 200}),
        "response_headers": "{}",
    }
    output_dir = tmp_path / "lounger"
    LoungerGenerator(FrameworkPattern()).generate([record], output_dir, "form login")
    case_text = (
        output_dir / "datas" / "captured" / "test_form_login.yaml"
    ).read_text(encoding="utf-8")

    assert "user@example.com" not in case_text
    assert "raw-password" not in case_text
    assert "raw-login-token" not in case_text
    assert "${config(login_email)}" in case_text
    assert "${config(login_password)}" in case_text
    assert "${config(login_request_token)}" in case_text


def test_multiple_origins_keep_absolute_request_urls(tmp_path: Path):
    records = [
        {
            **_record(
                method="POST",
                url="https://develop-gcp-bff.trackingmore.com/api/admin/login",
                request_body={},
                request_headers={},
                response_body={"code": 0},
            ),
            "path": "/api/admin/login",
        },
        {
            **_record(
                method="POST",
                url="https://develop-gcp-adminapi.trackingmore.com/v1/orders",
                request_body={},
                request_headers={},
                response_body={"code": 200},
            ),
            "path": "/v1/orders",
        },
    ]
    output_dir = tmp_path / "lounger"
    LoungerGenerator(FrameworkPattern()).generate(records, output_dir, "multi origin")
    steps = yaml.safe_load(
        (output_dir / "datas" / "captured" / "test_multi_origin.yaml").read_text(
            encoding="utf-8"
        )
    )[0]["teststeps"]

    assert steps[0]["request"]["url"] == records[0]["url"]
    assert steps[1]["request"]["url"] == records[1]["url"]


def test_common_response_name_does_not_create_false_url_dependency(tmp_path: Path):
    records = [
        _record(
            method="GET",
            url="https://develop-gcp-bff.trackingmore.com/v1/layout",
            request_body={},
            request_headers={},
            response_body={"code": 0, "data": {"name": "notifications"}},
        ),
        _record(
            method="GET",
            url="https://develop-gcp-bff.trackingmore.com/v1/notifications/list",
            request_body={},
            request_headers={},
            response_body={"code": 0},
        ),
    ]
    output_dir = tmp_path / "lounger"
    LoungerGenerator(FrameworkPattern()).generate(records, output_dir, "no false link")
    steps = yaml.safe_load(
        (output_dir / "datas" / "captured" / "test_no_false_link.yaml").read_text(
            encoding="utf-8"
        )
    )[0]["teststeps"]

    assert steps[0].get("extract") is None
    assert steps[1]["request"]["url"] == "/v1/notifications/list"
