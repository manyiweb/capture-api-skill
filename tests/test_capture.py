import pytest
from capture.filters import should_capture, is_dynamic_field, extract_dynamic_fields


class TestFilters:
    def test_should_capture_normal_api(self):
        """测试正常 API 请求应该被捕获"""
        class MockRequest:
            url = 'http://example.com/api/order/list'
            path = '/api/order/list'

        assert should_capture(MockRequest()) is True

    def test_should_exclude_js_file(self):
        """测试 JS 文件应该被排除"""
        class MockRequest:
            url = 'http://example.com/static/app.js'
            path = '/static/app.js'

        assert should_capture(MockRequest()) is False

    def test_should_exclude_health_endpoint(self):
        """测试健康检查端点应该被排除"""
        class MockRequest:
            url = 'http://example.com/health'
            path = '/health'

        assert should_capture(MockRequest()) is False

    def test_should_exclude_analytics(self):
        """测试埋点接口应该被排除"""
        class MockRequest:
            url = 'http://example.com/analytics/track'
            path = '/analytics/track'

        assert should_capture(MockRequest()) is False


class TestDynamicFieldDetection:
    def test_detect_id_field(self):
        """测试识别 ID 字段"""
        assert is_dynamic_field('orderId') is True
        assert is_dynamic_field('tokenId') is True
        assert is_dynamic_field('user_id') is True

    def test_detect_timestamp(self):
        """测试识别时间戳"""
        assert is_dynamic_field('timestamp') is True
        assert is_dynamic_field('createTime') is True

    def test_normal_field(self):
        """测试普通字段不被标记"""
        assert is_dynamic_field('name') is False
        assert is_dynamic_field('status') is False
        assert is_dynamic_field('amount') is False

    def test_extract_dynamic_fields(self):
        """测试提取动态字段"""
        data = {
            'tokenId': 'abc123',
            'orderId': 'ORD-001',
            'timestamp': 1234567890123,
            'name': '测试订单',
            'amount': 100.0,
            'nested': {
                'userId': 'USR-001',
                'status': 'pending'
            }
        }

        dynamic_fields = extract_dynamic_fields(data)

        assert 'tokenId' in dynamic_fields
        assert 'orderId' in dynamic_fields
        assert 'timestamp' in dynamic_fields
        assert 'nested.userId' in dynamic_fields
        assert 'name' not in dynamic_fields
        assert 'amount' not in dynamic_fields
