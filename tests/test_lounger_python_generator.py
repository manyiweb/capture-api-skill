import ast
import json
from pathlib import Path

import yaml

from analyzer.scanner import FrameworkPattern
from generator.lounger_gen import LoungerGenerator
from generator.lounger_python_gen import LoungerPythonGenerator


def _record(
    *,
    method: str,
    path: str,
    request_body: dict,
    request_headers: dict,
    response_body: dict,
    response_code: int = 200,
) -> dict:
    return {
        "method": method,
        "url": f"https://develop-gcp-bff.trackingmore.com{path}",
        "path": path,
        "query_params": "{}",
        "request_body": json.dumps(request_body),
        "request_headers": json.dumps(request_headers),
        "response_code": response_code,
        "response_body": json.dumps(response_body),
        "response_headers": json.dumps({"Content-Type": "application/json"}),
    }


def test_generate_pure_python_lounger_flow(tmp_path: Path):
    request_key = "captured-login-key"
    token = "captured-response-token-123456"
    records = [
        _record(
            method="POST",
            path="/api/admin/login",
            request_body={"auth_key": request_key},
            request_headers={"Content-Type": "application/json"},
            response_body={"code": 0, "data": {"access_token": token}},
        ),
        _record(
            method="POST",
            path="/api/admin/tracking/create",
            request_body={"tracking_number": "1Z999999999", "courier_code": "ups"},
            request_headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            },
            response_body={"code": 0, "data": {"id": "package-id-123"}},
        ),
    ]
    output_dir = tmp_path / "lounger"
    LoungerGenerator(FrameworkPattern()).generate(records, output_dir, "TM core flow")
    files = LoungerPythonGenerator(FrameworkPattern()).generate(
        records,
        output_dir,
        "TM core flow",
    )

    case_path = output_dir / "test_dir" / "test_tm_core_flow.py"
    assert case_path in files
    case_text = case_path.read_text(encoding="utf-8")
    ast.parse(case_text)

    assert "from pytest_req.assertions import expect" in case_text
    assert "from lounger.commons.load_config import base_url, global_test_config" in case_text
    assert "def test_tm_core_flow(post):" in case_text
    assert 'response_1 = post(' in case_text
    assert 'login_token = jmespath(response_1.json(), \'data.access_token\')' in case_text
    assert "'Bearer ' + str(login_token)" in case_text
    assert "expect(response_2).to_have_path_value('code', 0)" in case_text
    assert "assert jmespath(response_2.json(), 'data.id') is not None" in case_text
    assert "_unique_tracking_number()" in case_text
    assert request_key not in case_text
    assert token not in case_text

    config = yaml.safe_load(
        (output_dir / "config" / "config.yaml").read_text(encoding="utf-8")
    )
    assert config["global_test_config"]["login_request_auth_key"] == "CHANGE_ME"
    assert "testpaths = test_dir" in (output_dir / "pytest.ini").read_text(encoding="utf-8")


def test_dynamic_path_keeps_base_url_prefix(tmp_path: Path):
    records = [
        _record(
            method="POST",
            path="/orders",
            request_body={},
            request_headers={},
            response_body={"code": 0, "data": {"id": "order-id-123"}},
        ),
        _record(
            method="GET",
            path="/orders/order-id-123",
            request_body={},
            request_headers={},
            response_body={"code": 0},
        ),
    ]
    output_dir = tmp_path / "lounger"
    LoungerGenerator(FrameworkPattern()).generate(records, output_dir, "dynamic path")
    LoungerPythonGenerator(FrameworkPattern()).generate(records, output_dir, "dynamic path")
    case_text = (output_dir / "test_dir" / "test_dynamic_path.py").read_text(
        encoding="utf-8"
    )

    ast.parse(case_text)
    assert "str(base_url) + ('/orders/' + str(orders_id))" in case_text
