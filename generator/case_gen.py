import json
from pathlib import Path
from typing import List, Dict

from generator.base import BaseGenerator


class CaseGenerator(BaseGenerator):
    """测试用例生成器"""

    def generate(self, records: List[Dict], output_dir: Path) -> List[Path]:
        """生成测试用例"""
        output_dir.mkdir(parents=True, exist_ok=True)
        file_path = output_dir / "generated_cases.py"

        lines = [
            '"""自动生成的接口测试用例"""',
            '',
            'import pytest',
            '',
        ]

        for record in records:
            func_name = self._path_to_func_name(record['path'])
            lines.append(f'def test_{func_name}(client):')
            lines.append(f'    """测试 {record["path"]}"""')
            lines.append('    # TODO: 实现测试逻辑')
            lines.append('    pass')
            lines.append('')

        file_path.write_text('\n'.join(lines), encoding='utf-8')
        return [file_path]
