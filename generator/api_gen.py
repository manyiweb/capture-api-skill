import json
from pathlib import Path
from typing import List, Dict

from generator.base import BaseGenerator
from capture.filters import extract_dynamic_fields


class APIGenerator(BaseGenerator):
    """API 层代码生成器"""

    def generate(self, records: List[Dict], output_dir: Path) -> List[Path]:
        """生成 API 封装函数"""
        output_dir.mkdir(parents=True, exist_ok=True)

        modules = {}
        for record in records:
            module = self._path_to_module_name(record['path'])
            if module not in modules:
                modules[module] = []
            modules[module].append(record)

        generated_files = []
        for module_name, module_records in modules.items():
            file_path = output_dir / f"generated_{module_name}.py"
            content = self._generate_module(module_name, module_records)
            file_path.write_text(content, encoding='utf-8')
            generated_files.append(file_path)

        return generated_files

    def _generate_module(self, module_name: str, records: List[Dict]) -> str:
        """生成单个模块的代码"""
        lines = [
            '"""自动生成的 API 接口封装"""',
            '',
            f'import {self.pattern.library}',
            '',
        ]

        for record in records:
            func_name = self._path_to_func_name(record['path'])
            lines.append(f'def {func_name}(client, **kwargs):')
            lines.append(f'    """调用 {record["path"]}"""')
            lines.append(f'    return client.post("{record["path"]}", json=kwargs)')
            lines.append('')

        return '\n'.join(lines)
