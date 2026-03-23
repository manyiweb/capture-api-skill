import ast
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class FrameworkPattern:
    """框架模式定义"""
    library: str = "httpx"
    wrapper_func: str = "safe_post"
    wrapper_params: List[str] = field(default_factory=list)
    data_format: str = "yaml"
    use_allure: bool = True
    success_field: str = "code"
    success_value: str = "200"

    def to_dict(self) -> dict:
        return {
            'library': self.library,
            'wrapper_func': self.wrapper_func,
            'data_format': self.data_format,
            'use_allure': self.use_allure,
            'success_field': self.success_field,
        }


class FrameworkScanner:
    """AST 框架扫描器"""

    def __init__(self):
        self.last_pattern: Optional[FrameworkPattern] = None

    def scan(self, framework_path: str) -> Optional[FrameworkPattern]:
        """扫描目标框架"""
        path = Path(framework_path)
        if not path.exists():
            return None

        pattern = FrameworkPattern()
        self._scan_conftest(path, pattern)
        self._scan_api_base(path, pattern)
        self.last_pattern = pattern
        return pattern

    def _scan_conftest(self, path: Path, pattern: FrameworkPattern):
        """扫描 conftest.py"""
        conftest = path / "conftest.py"
        if not conftest.exists():
            return

        try:
            tree = ast.parse(conftest.read_text(encoding='utf-8'))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name == 'httpx':
                            pattern.library = 'httpx'
                        elif alias.name == 'requests':
                            pattern.library = 'requests'
        except:
            pass

    def _scan_api_base(self, path: Path, pattern: FrameworkPattern):
        """扫描 api/base.py"""
        base_py = path / "api" / "base.py"
        if not base_py.exists():
            return

        try:
            tree = ast.parse(base_py.read_text(encoding='utf-8'))
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    if any(kw in node.name.lower() for kw in ['post', 'request', 'safe']):
                        pattern.wrapper_func = node.name
                        pattern.wrapper_params = [arg.arg for arg in node.args.args]
                        break
        except:
            pass
