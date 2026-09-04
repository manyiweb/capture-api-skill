import json
from pathlib import Path

import yaml

from analyzer.scanner import FrameworkPattern
from generator.data_gen import DataGenerator
from generator.lounger_gen import LoungerGenerator
from generator.lounger_python_gen import LoungerPythonGenerator
from generator.redaction import (
    is_sensitive_header,
    sensitive_field_config_name,
)


def test_sensitive_field_and_header_rules_cover_common_credentials():
    assert sensitive_field_config_name("password", "/auth/login") == "login_password"
    assert sensitive_field_config_name("otp", "/auth/login") == "login_request_otp"
    assert sensitive_field_config_name("accessToken", "/v1/orders") == "access_token"
    assert sensitive_field_config_name("refresh_token", "/v1/orders") == "refresh_token"
    assert sensitive_field_config_name("key", "/v1/orders", "short-enum") is None
    assert sensitive_field_config_name("key", "/v1/orders", "a" * 30) == "key"
    assert is_sensitive_header("Authorization") is True
    assert is_sensitive_header("X-CSRF-Token") is True
    assert is_sensitive_header("X-API-Key") is True
    assert is_sensitive_header("Content-Type") is False


def test_all_generated_artifacts_remove_nested_secrets(tmp_path: Path):
    secrets = {
        "password": "raw-password-value",
        "access_token": "raw-access-token-value",
        "refresh_token": "raw-refresh-token-value",
        "csrf": "raw-csrf-token-value",
        "api_key": "raw-api-key-value",
    }
    record = {
        "method": "POST",
        "url": "https://api.example.com/v1/orders?refresh_token=raw-refresh-token-value",
        "path": "/v1/orders",
        "query_params": json.dumps({"refresh_token": secrets["refresh_token"]}),
        "request_body": json.dumps(
            {
                "customer": {
                    "password": secrets["password"],
                    "accessToken": secrets["access_token"],
                },
                "order_name": "safe-name",
            }
        ),
        "request_headers": json.dumps(
            {
                "Content-Type": "application/json",
                "X-CSRF-Token": secrets["csrf"],
                "X-API-Key": secrets["api_key"],
            }
        ),
        "response_code": 200,
        "response_body": json.dumps({"code": 0}),
        "response_headers": "{}",
    }
    lounger_dir = tmp_path / "lounger"
    data_dir = tmp_path / "data"
    pattern = FrameworkPattern()
    LoungerGenerator(pattern).generate([record], lounger_dir, "redacted")
    LoungerPythonGenerator(pattern).generate([record], lounger_dir, "redacted")
    DataGenerator(pattern).generate([record], data_dir)

    generated_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in [
            lounger_dir / "datas" / "captured" / "test_redacted.yaml",
            lounger_dir / "test_dir" / "test_redacted.py",
            lounger_dir / "config" / "config.yaml",
            data_dir / "generated_data.yaml",
        ]
    )
    for secret in secrets.values():
        assert secret not in generated_text

    config = yaml.safe_load(
        (lounger_dir / "config" / "config.yaml").read_text(encoding="utf-8")
    )["global_test_config"]
    assert config["refresh_token"] == "CHANGE_ME"
    assert config["access_token"] == "CHANGE_ME"
    assert config["x_csrf_token"] == "CHANGE_ME"
    assert config["api_key"] == "CHANGE_ME"
