#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""完整功能测试脚本"""

from storage.db import Database
from analyzer.scanner import FrameworkPattern
from generator.api_gen import APIGenerator
from generator.data_gen import DataGenerator
from generator.case_gen import CaseGenerator
import json
import tempfile
from pathlib import Path
import os

def run_full_workflow():
    """测试完整工作流程"""
    print("=== API Capture Skill 功能测试 ===\n")

    # 创建临时数据库
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    try:
        db = Database(db_path)
        print("[1/8] 数据库初始化成功")

        # 模拟捕获的数据
        record = {
            'method': 'POST',
            'url': 'http://example.com/api/order/pay',
            'path': '/api/order/pay',
            'query_params': '{}',
            'request_body': json.dumps({
                'orderId': '12345',
                'amount': 100.0,
                'tokenId': 'abc123'
            }),
            'response_code': 200,
            'response_body': json.dumps({'code': '200', 'success': True}),
        }

        # 保存记录
        db.save_or_update(record)
        print("[2/8] 数据保存成功")

        # 查询记录
        records = db.get_all()
        print(f"[3/8] 查询到 {len(records)} 条记录")
        assert len(records) == 1, "应该有 1 条记录"

        # 标记为选中
        db.update_selected([r['id'] for r in records], True)
        selected = db.get_selected()
        print(f"[4/8] 选中 {len(selected)} 条记录")
        assert len(selected) == 1, "应该有 1 条选中记录"

        # 创建框架模式
        pattern = FrameworkPattern(library='httpx', wrapper_func='safe_post')
        print(f"[5/8] 框架模式: {pattern.library} + {pattern.wrapper_func}")

        # 生成代码
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)

            # 生成 API 文件
            api_gen = APIGenerator(pattern)
            api_files = api_gen.generate(selected, output_dir / 'api')
            print(f"[6/8] 生成 {len(api_files)} 个 API 文件")
            assert len(api_files) > 0, "应该生成 API 文件"

            # 生成数据文件
            data_gen = DataGenerator(pattern)
            data_files = data_gen.generate(selected, output_dir / 'data')
            print(f"[7/8] 生成 {len(data_files)} 个数据文件")
            assert len(data_files) > 0, "应该生成数据文件"

            # 生成用例文件
            case_gen = CaseGenerator(pattern)
            case_files = case_gen.generate(selected, output_dir / 'case')
            print(f"[8/8] 生成 {len(case_files)} 个用例文件")
            assert len(case_files) > 0, "应该生成用例文件"

            # 验证生成的内容
            print("\n=== 验证生成内容 ===")

            api_content = api_files[0].read_text(encoding='utf-8')
            assert 'def order_pay' in api_content, "API 函数应该存在"
            print("- API 函数生成正确: order_pay")

            data_content = data_files[0].read_text(encoding='utf-8')
            assert 'DYNAMIC' in data_content, "应该标记动态字段"
            print("- 动态字段标记正确: tokenId, orderId")

            case_content = case_files[0].read_text(encoding='utf-8')
            assert 'def test_' in case_content, "测试用例应该存在"
            print("- 测试用例生成正确: test_order_pay")

            # 显示生成的文件内容预览
            print("\n=== 生成文件预览 ===")
            print(f"\n[API 文件] {api_files[0].name}:")
            print(api_content[:300] + "...")

            print(f"\n[数据文件] {data_files[0].name}:")
            print(data_content[:200] + "...")

            print(f"\n[用例文件] {case_files[0].name}:")
            print(case_content[:300] + "...")

        db.close()
        print("\n=== 所有功能测试通过! ===")
        return True

    except Exception as e:
        print(f"\n!!! 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # 清理临时文件
        if os.path.exists(db_path):
            os.unlink(db_path)

if __name__ == '__main__':
    success = run_full_workflow()
    exit(0 if success else 1)
