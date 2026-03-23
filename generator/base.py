import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict

from analyzer.scanner import FrameworkPattern


class BaseGenerator(ABC):
    """生成器基类"""

    def __init__(self, pattern: FrameworkPattern):
        self.pattern = pattern

    @abstractmethod
    def generate(self, records: List[Dict], output_dir: Path) -> List[Path]:
        """生成代码文件"""
        pass

    def _path_to_func_name(self, path: str) -> str:
        """将 API 路径转换为函数名"""
        path = re.sub(r'^/api/', '', path)
        parts = re.split(r'[/_.-]', path)
        return '_'.join(p.lower() for p in parts if p)

    def _path_to_module_name(self, path: str) -> str:
        """将 API 路径转换为模块名"""
        path = re.sub(r'^/api/', '', path)
        parts = path.split('/')
        return parts[0] if parts else 'default'
