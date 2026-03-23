import pytest
import tempfile
import os
from storage.db import Database


@pytest.fixture
def temp_db():
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    db = Database(db_path)
    yield db
    db.close()
    os.unlink(db_path)


# 测试数据示例
TEST_DATA = {
    'method': 'POST',
    'url': 'http://example.com/api/test',
    'path': '/api/test',
    'query_params': '{}',
    'request_body': '{"key": "value"}',
    'response_code': 200,
    'response_body': '{"success": true}',
}


class TestDatabase:
    def test_init_creates_table(self, temp_db):
        """测试初始化创建表"""
        cursor = temp_db.conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='captured_requests'"
        )
        result = cursor.fetchone()
        assert result is not None, "Table 'captured_requests' should exist"

        # 验证列结构
        cursor.execute("PRAGMA table_info(captured_requests)")
        columns = {row[1] for row in cursor.fetchall()}
        expected_columns = {
            'id', 'timestamp', 'method', 'url', 'path',
            'query_params', 'request_body', 'response_code',
            'response_body', 'selected'
        }
        assert expected_columns.issubset(columns), (
            f"Missing columns: {expected_columns - columns}"
        )

    def test_save_record(self, temp_db):
        """测试保存记录"""
        temp_db.save_or_update(TEST_DATA)
        records = temp_db.get_all()
        assert len(records) == 1
        record = records[0]
        assert record['method'] == 'POST'
        assert record['url'] == 'http://example.com/api/test'
        assert record['path'] == '/api/test'
        assert record['query_params'] == '{}'
        assert record['request_body'] == '{"key": "value"}'
        assert record['response_code'] == 200
        assert record['response_body'] == '{"success": true}'
        assert record['selected'] == 0

    def test_deduplication(self, temp_db):
        """测试相同 path + body 去重（只保留最新）"""
        # 插入第一条记录
        data1 = dict(TEST_DATA)
        data1['response_code'] = 200
        temp_db.save_or_update(data1)

        # 插入相同 path + request_body 的记录（不同 response_code）
        data2 = dict(TEST_DATA)
        data2['response_code'] = 201
        temp_db.save_or_update(data2)

        records = temp_db.get_all()
        # 相同 path + request_body 应只保留 1 条
        assert len(records) == 1, (
            f"Expected 1 record after dedup, got {len(records)}"
        )
        # 保留的应是最新的记录（response_code=201）
        assert records[0]['response_code'] == 201

        # 插入不同 path 的记录，总数应为 2
        data3 = dict(TEST_DATA)
        data3['path'] = '/api/other'
        data3['url'] = 'http://example.com/api/other'
        temp_db.save_or_update(data3)
        records = temp_db.get_all()
        assert len(records) == 2, (
            f"Expected 2 records for different paths, got {len(records)}"
        )

    def test_filter_by_method(self, temp_db):
        """测试按方法过滤"""
        # 插入 POST 记录
        post_data = dict(TEST_DATA)
        post_data['method'] = 'POST'
        post_data['path'] = '/api/post'
        post_data['url'] = 'http://example.com/api/post'
        temp_db.save_or_update(post_data)

        # 插入 GET 记录
        get_data = dict(TEST_DATA)
        get_data['method'] = 'GET'
        get_data['path'] = '/api/get'
        get_data['url'] = 'http://example.com/api/get'
        get_data['request_body'] = None
        temp_db.save_or_update(get_data)

        # 按 POST 过滤
        post_records = temp_db.get_all(filters={'method': 'POST'})
        assert len(post_records) == 1
        assert post_records[0]['method'] == 'POST'

        # 按 GET 过滤
        get_records = temp_db.get_all(filters={'method': 'GET'})
        assert len(get_records) == 1
        assert get_records[0]['method'] == 'GET'

        # 不过滤返回全部
        all_records = temp_db.get_all()
        assert len(all_records) == 2

        # 按关键字过滤（匹配 URL/path）
        keyword_records = temp_db.get_all(filters={'keyword': 'post'})
        assert len(keyword_records) == 1
        assert keyword_records[0]['path'] == '/api/post'

    def test_update_selected(self, temp_db):
        """测试更新选中状态"""
        # 插入两条记录
        data1 = dict(TEST_DATA)
        data1['path'] = '/api/one'
        data1['url'] = 'http://example.com/api/one'
        temp_db.save_or_update(data1)

        data2 = dict(TEST_DATA)
        data2['path'] = '/api/two'
        data2['url'] = 'http://example.com/api/two'
        data2['request_body'] = '{"key": "two"}'
        temp_db.save_or_update(data2)

        records = temp_db.get_all()
        assert len(records) == 2

        ids = [r['id'] for r in records]

        # 选中第一条
        temp_db.update_selected([ids[0]], selected=True)
        selected = temp_db.get_selected()
        assert len(selected) == 1
        assert selected[0]['id'] == ids[0]

        # 选中所有
        temp_db.update_selected(ids, selected=True)
        selected = temp_db.get_selected()
        assert len(selected) == 2

        # 取消选中第一条
        temp_db.update_selected([ids[0]], selected=False)
        selected = temp_db.get_selected()
        assert len(selected) == 1
        assert selected[0]['id'] == ids[1]

    def test_clear(self, temp_db):
        """测试清空数据"""
        # 插入记录
        temp_db.save_or_update(TEST_DATA)
        records = temp_db.get_all()
        assert len(records) == 1

        # 清空
        temp_db.clear()
        records = temp_db.get_all()
        assert len(records) == 0, (
            f"Expected 0 records after clear, got {len(records)}"
        )
