import json
from pathlib import Path
from typing import List, Dict

from generator.base import BaseGenerator
from capture.filters import extract_dynamic_fields


class DataGenerator(BaseGenerator):
    """数据层代码生成器"""

    def generate(self, records: List[Dict], output_dir: Path) -> List[Path]:
        """生成数据文件"""
        output_dir.mkdir(parents=True, exist_ok=True)
        file_path = output_dir / "generated_data.yaml"

        lines = ['# 自动生成的测试数据', '']

        for record in records:
            func_name = self._path_to_func_name(record['path'])
            lines.append(f'{func_name}:')

            try:
                body = json.loads(record.get('request_body', '{}') or '{}')
                dynamic_fields = extract_dynamic_fields(body)

                for key, value in body.items():
                    if key in dynamic_fields:
                        lines.append(f'  {key}: "DYNAMIC"')
                    else:
                        lines.append(f'  {key}: {json.dumps(value)}')
            except:
                lines.append('  # 解析失败')

            lines.append('')

        file_path.write_text('\n'.join(lines), encoding='utf-8')
        return [file_path]
