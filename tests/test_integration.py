import pytest
import tempfile
import json
from pathlib import Path

from storage.db import Database
from analyzer.scanner import FrameworkPattern
from generator.api_gen import APIGenerator
from generator.data_gen import DataGenerator
from generator.case_gen import CaseGenerator


class TestIntegration:
    """集成测试"""

    def test_full_workflow(self):
        """测试完整工作流程"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 1. 创建数据库并保存记录
            db_path = Path(tmpdir) / "test.db"
            db = Database(str(db_path))

            record = {
                'method': 'POST',
                'url': 'http://example.com/api/order/pay',
                'path': '/api/order/pay',
                'query_params': '{}',
                'request_body': json.dumps({'orderId': '12345', 'amount': 100.0}),
                'response_code': 200,
                'response_body': json.dumps({'code': '200', 'success': True}),
            }
            db.save_or_update(record)

            # 2. 标记为选中
            all_records = db.get_all()
            db.update_selected([r['id'] for r in all_records], True)
            selected = db.get_selected()
            assert len(selected) == 1

            # 3. 创建框架模式
            pattern = FrameworkPattern(library='httpx', wrapper_func='safe_post')

            # 4. 生成代码
            output_dir = Path(tmpdir) / "output"
            api_gen = APIGenerator(pattern)
            data_gen = DataGenerator(pattern)
            case_gen = CaseGenerator(pattern)

            api_files = api_gen.generate(selected, output_dir / "api")
            data_files = data_gen.generate(selected, output_dir / "data")
            case_files = case_gen.generate(selected, output_dir / "case")

            # 5. 验证生成结果
            assert len(api_files) > 0
            assert len(data_files) > 0
            assert len(case_files) > 0

            db.close()
