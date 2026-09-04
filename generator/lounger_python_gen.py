"""Generate readable Lounger/pytest Python scenarios from captured traffic."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List

import yaml

from generator.base import BaseGenerator
from generator.lounger_gen import LoungerGenerator, _safe_name


_TEMPLATE_PATTERN = re.compile(
    r"\$\{(?:(extract|config)\(([a-zA-Z_][a-zA-Z0-9_]*)\)|"
    r"(unique_tracking_number|timestamp_ms)\(\))\}"
)
_METHOD_FIXTURES = {
    "GET": "get",
    "POST": "post",
    "PUT": "put",
    "PATCH": "patch",
    "DELETE": "delete",
}


class _Expression:
    def __init__(self, code: str, source: str | None = None):
        self.code = code
        self.source = source


def _template_expression(kind: str | None, name: str | None, function: str | None) -> str:
    if kind == "extract":
        return str(name)
    if kind == "config":
        return f"global_test_config({name!r})"
    if function == "unique_tracking_number":
        return "_unique_tracking_number()"
    if function == "timestamp_ms":
        return "_timestamp_ms()"
    raise ValueError("Unsupported generated template")


def _convert_templates(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _convert_templates(child) for key, child in value.items()}
    if isinstance(value, list):
        return [_convert_templates(child) for child in value]
    if not isinstance(value, str):
        return value

    matches = list(_TEMPLATE_PATTERN.finditer(value))
    if not matches:
        return value
    if len(matches) == 1 and matches[0].span() == (0, len(value)):
        match = matches[0]
        return _Expression(
            _template_expression(match.group(1), match.group(2), match.group(3)),
            source=value,
        )

    parts: List[str] = []
    cursor = 0
    for match in matches:
        if match.start() > cursor:
            parts.append(repr(value[cursor:match.start()]))
        expression = _template_expression(match.group(1), match.group(2), match.group(3))
        parts.append(f"str({expression})")
        cursor = match.end()
    if cursor < len(value):
        parts.append(repr(value[cursor:]))
    return _Expression(" + ".join(parts), source=value)


def _python_literal(value: Any) -> str:
    def render(child: Any, level: int = 0) -> str:
        indent = "    " * level
        child_indent = "    " * (level + 1)
        if isinstance(child, _Expression):
            return child.code
        if isinstance(child, dict):
            if not child:
                return "{}"
            items = [
                f"{child_indent}{key!r}: {render(item, level + 1)},"
                for key, item in child.items()
            ]
            return "{\n" + "\n".join(items) + f"\n{indent}}}"
        if isinstance(child, list):
            if not child:
                return "[]"
            items = [f"{child_indent}{render(item, level + 1)}," for item in child]
            return "[\n" + "\n".join(items) + f"\n{indent}]"
        return repr(child)

    return render(value)


def _indent_following_lines(value: str, spaces: int) -> str:
    prefix = " " * spaces
    return value.replace("\n", f"\n{prefix}")


class LoungerPythonGenerator(BaseGenerator):
    """Generate one sequential pure-Python pytest function per captured scenario."""

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
        test_dir = output_dir / "test_dir"
        config_dir = output_dir / "config"
        test_dir.mkdir(parents=True, exist_ok=True)
        config_dir.mkdir(parents=True, exist_ok=True)

        builder = LoungerGenerator(self.pattern)
        steps, base_url, config_values, dynamic_functions = builder._build_steps(records)

        case_path = test_dir / f"test_{scenario_name}.py"
        case_path.write_text(
            self._render_case(scenario_name, steps, config_values, dynamic_functions),
            encoding="utf-8",
        )

        init_path = test_dir / "__init__.py"
        if not init_path.exists():
            init_path.write_text("", encoding="utf-8")

        config_path = config_dir / "config.yaml"
        self._merge_config(config_path, base_url, config_values)

        return [case_path, init_path, config_path]

    def _render_case(
        self,
        scenario_name: str,
        steps,
        config_values: Dict[str, Any],
        dynamic_functions: set[str],
    ) -> str:
        fixtures: List[str] = []
        for step in steps:
            method = str(step.request.get("method", "GET")).upper()
            fixture = _METHOD_FIXTURES.get(method, "req")
            if fixture not in fixtures:
                fixtures.append(fixture)

        imports = [
            '"""由浏览器流量自动生成的 Lounger Python 接口场景。"""',
            "",
        ]
        if "timestamp_ms" in dynamic_functions or "unique_tracking_number" in dynamic_functions:
            imports.append("import time")
        if "unique_tracking_number" in dynamic_functions:
            imports.append("import uuid")
        if len(imports) > 2:
            imports.append("")
        imports.append("from pytest_req.assertions import expect")
        if any(step.extract for step in steps) or any(
            isinstance(step.response_body, dict)
            and isinstance(step.response_body.get("data"), dict)
            and step.response_body["data"].get("id") not in (None, "")
            for step in steps
        ):
            imports.append("from pytest_req.utils.jmespath import jmespath")
        load_config_imports = ["base_url"]
        if config_values:
            load_config_imports.append("global_test_config")
        imports.extend(
            [
                f"from lounger.commons.load_config import {', '.join(load_config_imports)}",
                "",
                "",
            ]
        )

        helpers: List[str] = []
        if "unique_tracking_number" in dynamic_functions:
            helpers.extend(
                [
                    "def _unique_tracking_number() -> str:",
                    '    return f"AUTO{int(time.time() * 1000)}{uuid.uuid4().hex[:6]}"',
                    "",
                    "",
                ]
            )
        if "timestamp_ms" in dynamic_functions:
            helpers.extend(
                [
                    "def _timestamp_ms() -> int:",
                    "    return int(time.time() * 1000)",
                    "",
                    "",
                ]
            )

        lines = imports + helpers
        lines.append(f"def test_{scenario_name}({', '.join(fixtures)}):")
        lines.append(f'    """按捕获顺序执行 {scenario_name} 核心接口链路。"""')

        for index, step in enumerate(steps, start=1):
            request = _convert_templates(step.request)
            method = str(request.pop("method", "GET")).upper()
            request_url = request.pop("url")
            fixture = _METHOD_FIXTURES.get(method, "req")
            response_name = f"response_{index}"

            lines.append("")
            lines.append(
                f"    # Step {index}: {method} {step.record.get('path', request_url)}"
            )

            argument_names: List[str] = []
            for argument in ("params", "headers", "json", "data"):
                if argument not in request:
                    continue
                variable_name = f"{argument}_{index}"
                literal = _indent_following_lines(_python_literal(request[argument]), 4)
                lines.append(f"    {variable_name} = {literal}")
                argument_names.append(f"{argument}={variable_name}")

            url_code = self._url_code(request_url)
            positional = [url_code]
            if fixture == "req":
                positional.insert(0, repr(method))
            if argument_names:
                lines.append(f"    {response_name} = {fixture}(")
                for argument in positional:
                    lines.append(f"        {argument},")
                for argument in argument_names:
                    lines.append(f"        {argument},")
                lines.append("    )")
            else:
                lines.append(f"    {response_name} = {fixture}({', '.join(positional)})")

            status_code = int(step.record.get("response_code") or 0)
            if status_code == 200:
                lines.append(f"    expect({response_name}).to_be_ok()")
            else:
                lines.append(
                    f"    expect({response_name}).to_have_status_code({status_code})"
                )

            if isinstance(step.response_body, dict):
                for key in ("code", "success", "status"):
                    value = step.response_body.get(key)
                    if isinstance(value, (str, int, float, bool)):
                        lines.append(
                            f"    expect({response_name}).to_have_path_value({key!r}, {value!r})"
                        )
                data = step.response_body.get("data")
                if isinstance(data, dict) and data.get("id") not in (None, ""):
                    lines.append(
                        f"    assert jmespath({response_name}.json(), 'data.id') is not None"
                    )

            for variable_name, response_path in step.extract.items():
                lines.append(
                    f"    {variable_name} = jmespath({response_name}.json(), {response_path!r})"
                )
                lines.append(f"    assert {variable_name} is not None")

        return "\n".join(lines).rstrip() + "\n"

    @staticmethod
    def _url_code(url: Any) -> str:
        if isinstance(url, _Expression):
            if (url.source or "").startswith(("http://", "https://")):
                return url.code
            return f"str(base_url) + ({url.code})"
        url = str(url)
        if url.startswith(("http://", "https://")):
            return repr(url)
        if re.fullmatch(r"/[a-zA-Z0-9_./~-]*", url):
            return f'f"{{base_url}}{url}"'
        return f"str(base_url) + {url!r}"

    @staticmethod
    def _merge_config(
        config_path: Path,
        base_url: str,
        config_values: Dict[str, Any],
    ) -> None:
        config: Dict[str, Any] = {}
        if config_path.exists():
            config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        config["base_url"] = base_url
        config.setdefault("test_project", {"captured": True})
        existing_values = config.setdefault("global_test_config", {})
        for key, value in config_values.items():
            existing_values.setdefault(key, value)
        config_path.write_text(
            yaml.safe_dump(config, allow_unicode=True, sort_keys=False, width=120),
            encoding="utf-8",
        )
