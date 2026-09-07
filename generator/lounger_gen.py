"""Generate executable Lounger YAML scenarios from captured browser traffic."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple
from urllib.parse import parse_qsl, urlsplit

import yaml

from generator.base import BaseGenerator
from generator.redaction import (
    is_sensitive_header,
    sensitive_field_config_name,
    sensitive_header_config_name,
)


_BROWSER_ONLY_HEADERS = {
    "accept-encoding",
    "connection",
    "content-length",
    "host",
    "origin",
    "priority",
    "referer",
    "sec-fetch-dest",
    "sec-fetch-mode",
    "sec-fetch-site",
    "te",
    "upgrade-insecure-requests",
    "user-agent",
}
_TOKEN_PATH_PATTERN = re.compile(r"(?:token|auth|session|(^|_)id)$", re.I)
_DYNAMIC_FIELD_PATTERN = re.compile(r"(?:tracking_?number|tracking_?no)$", re.I)
_TIMESTAMP_FIELD_PATTERN = re.compile(r"(?:timestamp|time_?ms)$", re.I)


def _json_value(raw: Any, default: Any) -> Any:
    if raw in (None, ""):
        return default
    if isinstance(raw, (dict, list)):
        return raw
    try:
        return json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return default


def _safe_name(value: str, fallback: str = "captured_core_flow") -> str:
    name = re.sub(r"[^0-9a-zA-Z_]+", "_", value).strip("_").lower()
    if not name:
        return fallback
    if name[0].isdigit():
        name = f"scenario_{name}"
    return name


def _origin(url: str) -> str:
    parsed = urlsplit(url)
    if not parsed.scheme or not parsed.netloc:
        return ""
    return f"{parsed.scheme}://{parsed.netloc}"


def _flatten_json(value: Any, prefix: str = "") -> Iterable[Tuple[str, Any]]:
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            yield from _flatten_json(child, path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            path = f"{prefix}[{index}]"
            yield from _flatten_json(child, path)
    elif prefix:
        yield prefix, value


def _candidate_value(path: str, value: Any) -> bool:
    """Only correlate values distinctive enough to avoid false dependencies."""
    if value in (None, "", True, False):
        return False
    leaf = re.split(r"[.\[\]]+", path)[-1]
    if _TOKEN_PATH_PATTERN.search(leaf):
        return len(str(value)) >= 4
    if leaf.lower() == "key" and isinstance(value, str):
        return len(value) >= 20
    if _DYNAMIC_FIELD_PATTERN.search(leaf):
        return len(str(value)) >= 6
    if isinstance(value, str) and re.fullmatch(
        r"[0-9a-f]{8}-[0-9a-f-]{27,}", value, re.I
    ):
        return True
    return isinstance(value, int) and abs(value) >= 100000


def _header_value(headers: Dict[str, Any], name: str) -> str:
    for key, value in headers.items():
        if key.lower() == name.lower():
            return str(value)
    return ""


@dataclass
class _ScenarioStep:
    record: Dict[str, Any]
    request: Dict[str, Any]
    response_body: Any
    name: str
    extract: Dict[str, str] = field(default_factory=dict)


class LoungerGenerator(BaseGenerator):
    """Generate a self-contained Lounger project for a captured API flow."""

    def generate(
        self,
        records: List[Dict],
        output_dir: Path,
        scenario_name: str = "captured_core_flow",
    ) -> List[Path]:
        if not records:
            return []

        scenario_name = _safe_name(scenario_name)
        output_dir.mkdir(parents=True, exist_ok=True)

        steps, base_url, config_values, dynamic_functions = self._build_steps(records)
        scenario = [{"teststeps": [self._render_step(step) for step in steps]}]

        case_dir = output_dir / "datas" / "captured"
        config_dir = output_dir / "config"
        reports_dir = output_dir / "reports"
        case_dir.mkdir(parents=True, exist_ok=True)
        config_dir.mkdir(parents=True, exist_ok=True)
        reports_dir.mkdir(parents=True, exist_ok=True)

        generated: List[Path] = []
        case_path = case_dir / f"test_{scenario_name}.yaml"
        self._write_yaml(case_path, scenario)
        generated.append(case_path)

        config = {
            "base_url": base_url,
            "test_project": {"captured": True},
            "global_test_config": config_values,
        }
        config_path = config_dir / "config.yaml"
        self._write_yaml(config_path, config)
        generated.append(config_path)

        test_api_path = output_dir / "test_api.py"
        test_api_path.write_text(
            "from typing import Dict\n\n"
            "from lounger.analyze_cases import load_teststeps\n"
            "from lounger.case import execute_teststeps\n\n\n"
            "@load_teststeps()\n"
            "def test_api(teststeps: Dict) -> None:\n"
            "    execute_teststeps(teststeps)\n",
            encoding="utf-8",
        )
        generated.append(test_api_path)

        pytest_path = output_dir / "pytest.ini"
        pytest_path.write_text(
            "[pytest]\n"
            "testpaths = test_dir\n"
            "log_format = %(asctime)s | %(levelname)-8s | %(filename)s | %(message)s\n"
            "log_date_format = %Y-%m-%d %H:%M:%S\n"
            "disable_test_id_escaping_and_forfeit_all_rights_to_community_support = true\n"
            "addopts = --html=./reports/result.html\n",
            encoding="utf-8",
        )
        generated.append(pytest_path)

        if dynamic_functions:
            conftest_path = output_dir / "conftest.py"
            conftest_path.write_text(self._conftest_content(dynamic_functions), encoding="utf-8")
            generated.append(conftest_path)

        readme_path = output_dir / "README_GENERATED.md"
        readme_path.write_text(
            self._readme_content(scenario_name, config_values),
            encoding="utf-8",
        )
        generated.append(readme_path)
        return generated

    def _build_steps(
        self, records: List[Dict]
    ) -> Tuple[List[_ScenarioStep], str, Dict[str, Any], set[str]]:
        origins = [_origin(str(record.get("url", ""))) for record in records]
        origins = [value for value in origins if value]
        base_url = origins[0] if origins and len(set(origins)) == 1 else ""
        config_values: Dict[str, Any] = {}
        dynamic_functions: set[str] = set()
        steps: List[_ScenarioStep] = []

        for index, record in enumerate(records, start=1):
            request = self._request_from_record(record, base_url)
            path = str(record.get("path") or urlsplit(str(record.get("url", ""))).path or "/")
            step_name = f"{index}. {str(record.get('method', 'GET')).upper()} {path}"
            steps.append(
                _ScenarioStep(
                    record=record,
                    request=request,
                    response_body=_json_value(record.get("response_body"), None),
                    name=step_name,
                )
            )

        self._link_response_dependencies(steps)
        for step in steps:
            step.request = self._parameterize_request(
                step.request,
                str(step.record.get("path", "")),
                config_values,
                dynamic_functions,
            )

        return steps, base_url, config_values, dynamic_functions

    def _request_from_record(self, record: Dict[str, Any], base_url: str) -> Dict[str, Any]:
        raw_url = str(record.get("url", ""))
        parsed_url = urlsplit(raw_url)
        path = str(record.get("path") or parsed_url.path or "/")
        request_url = (
            path
            if base_url and _origin(raw_url) == base_url
            else raw_url.split("?", 1)[0]
        )
        request: Dict[str, Any] = {
            "method": str(record.get("method", "GET")).upper(),
            "url": request_url,
        }

        query = _json_value(record.get("query_params"), {})
        if not query and parsed_url.query:
            query = dict(parse_qsl(parsed_url.query, keep_blank_values=True))
        if isinstance(query, dict) and query:
            request["params"] = query

        headers = _json_value(record.get("request_headers"), {})
        if isinstance(headers, dict):
            headers = {
                key: value
                for key, value in headers.items()
                if key.lower() not in _BROWSER_ONLY_HEADERS
                and not key.lower().startswith("sec-ch-")
            }
            if headers:
                request["headers"] = headers

        raw_body = record.get("request_body")
        body = _json_value(raw_body, None)
        content_type = _header_value(headers if isinstance(headers, dict) else {}, "content-type").lower()
        if body is not None:
            request["json"] = body
        elif raw_body not in (None, ""):
            if "application/x-www-form-urlencoded" in content_type:
                request["data"] = dict(parse_qsl(str(raw_body), keep_blank_values=True))
            else:
                request["data"] = str(raw_body)
        return request

    def _link_response_dependencies(self, steps: List[_ScenarioStep]) -> None:
        candidates: List[Tuple[str, Any, int, str]] = []
        variable_names: set[str] = set()

        for step_index, step in enumerate(steps):
            if step_index:
                step.request = self._replace_dependencies(
                    step.request,
                    candidates,
                    steps,
                    variable_names,
                )

            for path, value in _flatten_json(step.response_body):
                if _candidate_value(path, value):
                    candidates.append((str(value), value, step_index, path))
            candidates.sort(key=lambda item: len(item[0]), reverse=True)

    def _replace_dependencies(
        self,
        value: Any,
        candidates: List[Tuple[str, Any, int, str]],
        steps: List[_ScenarioStep],
        variable_names: set[str],
    ) -> Any:
        if isinstance(value, dict):
            return {
                key: self._replace_dependencies(child, candidates, steps, variable_names)
                for key, child in value.items()
            }
        if isinstance(value, list):
            return [self._replace_dependencies(child, candidates, steps, variable_names) for child in value]

        for candidate_text, candidate_value, producer_index, response_path in candidates:
            exact_match = value == candidate_value
            contained_match = (
                isinstance(value, str)
                and isinstance(candidate_value, str)
                and candidate_text in value
            )
            if not exact_match and not contained_match:
                continue

            producer = steps[producer_index]
            variable = next(
                (name for name, path in producer.extract.items() if path == response_path),
                None,
            )
            if variable is None:
                variable = self._variable_name(producer, response_path, variable_names)
                producer.extract[variable] = response_path
            template = f"${{extract({variable})}}"
            if exact_match:
                return template
            return str(value).replace(candidate_text, template)
        return value

    def _variable_name(self, step: _ScenarioStep, response_path: str, used: set[str]) -> str:
        leaf = re.split(r"[.\[\]]+", response_path)[-1]
        endpoint = self._path_to_func_name(str(step.record.get("path", ""))) or "step"
        if re.search(r"token|auth|session|key", leaf, re.I):
            base = "login_token" if "login" in endpoint or "auth" in endpoint else f"{endpoint}_{leaf}"
        else:
            base = f"{endpoint}_{leaf}"
        name = _safe_name(base, "extracted_value")
        suffix = 2
        while name in used:
            name = f"{_safe_name(base)}_{suffix}"
            suffix += 1
        used.add(name)
        return name

    def _parameterize_request(
        self,
        request: Dict[str, Any],
        path: str,
        config_values: Dict[str, Any],
        dynamic_functions: set[str],
    ) -> Dict[str, Any]:
        result = dict(request)
        if "headers" in result:
            result["headers"] = self._parameterize_headers(result["headers"], config_values)
        for key in ("params", "json", "data"):
            if key in result:
                result[key] = self._parameterize_fields(
                    result[key], path, config_values, dynamic_functions
                )
        return result

    def _parameterize_headers(
        self, headers: Dict[str, Any], config_values: Dict[str, Any]
    ) -> Dict[str, Any]:
        rendered: Dict[str, Any] = {}
        for key, value in headers.items():
            lower_key = key.lower()
            if not is_sensitive_header(key):
                rendered[key] = value
                continue
            # Browser Cookie 往往混有会话和分析标识，始终整体参数化，避免泄漏。
            if lower_key == "cookie":
                config_values.setdefault("session_cookie", "CHANGE_ME")
                rendered[key] = "${config(session_cookie)}"
                continue
            if isinstance(value, str) and "${extract(" in value:
                rendered[key] = value
                continue

            if lower_key == "authorization":
                match = re.match(r"^(Bearer|Token)\s+", str(value), re.I)
                prefix = f"{match.group(1)} " if match else ""
                config_values.setdefault("auth_token", "CHANGE_ME")
                rendered[key] = f"{prefix}${{config(auth_token)}}"
            else:
                config_name = sensitive_header_config_name(key)
                config_values.setdefault(config_name, "CHANGE_ME")
                rendered[key] = f"${{config({config_name})}}"
        return rendered

    def _parameterize_fields(
        self,
        value: Any,
        path: str,
        config_values: Dict[str, Any],
        dynamic_functions: set[str],
    ) -> Any:
        if isinstance(value, dict):
            rendered = {}
            for key, child in value.items():
                if isinstance(child, str) and "${extract(" in child:
                    rendered[key] = child
                elif config_name := sensitive_field_config_name(key, path, child):
                    config_values.setdefault(config_name, "CHANGE_ME")
                    rendered[key] = f"${{config({config_name})}}"
                elif _DYNAMIC_FIELD_PATTERN.search(key):
                    dynamic_functions.add("unique_tracking_number")
                    rendered[key] = "${unique_tracking_number()}"
                elif _TIMESTAMP_FIELD_PATTERN.search(key):
                    dynamic_functions.add("timestamp_ms")
                    rendered[key] = "${timestamp_ms()}"
                else:
                    rendered[key] = self._parameterize_fields(
                        child, path, config_values, dynamic_functions
                    )
            return rendered
        if isinstance(value, list):
            return [
                self._parameterize_fields(item, path, config_values, dynamic_functions)
                for item in value
            ]
        return value

    def _render_step(self, step: _ScenarioStep) -> Dict[str, Any]:
        rendered: Dict[str, Any] = {
            "step": step.name,
            "request": step.request,
        }
        if step.extract:
            rendered["extract"] = step.extract

        equal = [["status_code", int(step.record.get("response_code") or 0)]]
        if isinstance(step.response_body, dict):
            for key in ("code", "success", "status"):
                value = step.response_body.get(key)
                if isinstance(value, (str, int, float, bool)):
                    equal.append([f"body.{key}", value])
        rendered["validate"] = {"equal": equal}

        data = step.response_body.get("data") if isinstance(step.response_body, dict) else None
        if isinstance(data, dict) and data.get("id") not in (None, ""):
            rendered["validate"]["is_not_null"] = [["body.data.id", True]]
        return rendered

    @staticmethod
    def _write_yaml(path: Path, data: Any) -> None:
        path.write_text(
            yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=120),
            encoding="utf-8",
        )

    @staticmethod
    def _conftest_content(functions: set[str]) -> str:
        lines = ["import time", "import uuid", "", "from lounger.runtime import register_template_func", ""]
        if "unique_tracking_number" in functions:
            lines.extend(
                [
                    "",
                    "def unique_tracking_number() -> str:",
                    "    return f\"AUTO{int(time.time() * 1000)}{uuid.uuid4().hex[:6]}\"",
                    "",
                    "",
                    'register_template_func("unique_tracking_number", unique_tracking_number)',
                ]
            )
        if "timestamp_ms" in functions:
            lines.extend(
                [
                    "",
                    "",
                    "def timestamp_ms() -> int:",
                    "    return int(time.time() * 1000)",
                    "",
                    "",
                    'register_template_func("timestamp_ms", timestamp_ms)',
                ]
            )
        return "\n".join(lines).lstrip() + "\n"

    @staticmethod
    def _readme_content(scenario_name: str, config_values: Dict[str, Any]) -> str:
        lines = [
            f"# Generated Lounger scenario: {scenario_name}",
            "",
            "This directory is a self-contained Lounger API test project generated from browser traffic.",
            f"The primary pure-Python case is `test_dir/test_{scenario_name}.py`.",
            "The YAML representation remains under `datas/captured/` for optional data-driven execution.",
            "Captured credentials and tokens are not written into the case; unresolved values use Lounger config variables.",
            "",
        ]
        if config_values:
            lines.extend(["## Required runtime values", ""])
            for key in config_values:
                env_name = f"LOUNGER_GLOBAL_TEST_CONFIG__{key.upper()}"
                lines.append(f"- `{env_name}`")
            lines.append("")
        lines.extend(
            [
                "## Run",
                "",
                "```bash",
                "pip install lounger",
                "pytest -v",
                "```",
                "",
                "Run the YAML version explicitly with `pytest test_api.py -v`.",
                "",
            ]
        )
        return "\n".join(lines)
