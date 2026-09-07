import pytest
from capture.filters import should_capture, is_dynamic_field, extract_dynamic_fields


class TestFilters:
    def test_should_capture_normal_api(self):
        """测试正常 API 请求应该被捕获"""
        class MockRequest:
            url = 'http://example.com/api/order/list'
            path = '/api/order/list'
            method = 'POST'
            headers = {'Sec-Fetch-Dest': 'empty'}

        assert should_capture(MockRequest()) is True

    def test_should_exclude_js_file(self):
        """测试 JS 文件应该被排除"""
        class MockRequest:
            url = 'http://example.com/static/app.js'
            path = '/static/app.js'
            method = 'GET'
            headers = {'Sec-Fetch-Dest': 'script'}

        assert should_capture(MockRequest()) is False

    def test_should_exclude_health_endpoint(self):
        """测试健康检查端点应该被排除"""
        class MockRequest:
            url = 'http://example.com/health'
            path = '/health'
            method = 'GET'
            headers = {'Sec-Fetch-Dest': 'empty'}

        assert should_capture(MockRequest()) is False

    def test_should_exclude_analytics(self):
        """测试埋点接口应该被排除"""
        class MockRequest:
            url = 'http://example.com/analytics/track'
            path = '/analytics/track'
            method = 'POST'
            headers = {'Sec-Fetch-Dest': 'empty'}

        assert should_capture(MockRequest()) is False

    def test_should_exclude_cors_preflight(self):
        class MockRequest:
            url = 'https://api.example.com/v1/orders'
            path = '/v1/orders'
            method = 'OPTIONS'
            headers = {'Sec-Fetch-Dest': 'empty'}

        assert should_capture(MockRequest()) is False

    def test_should_exclude_page_resources_in_api_only_mode(self):
        class MockRequest:
            url = 'https://app.example.com/home'
            path = '/home'
            method = 'GET'
            headers = {'Sec-Fetch-Dest': 'document'}

        assert should_capture(MockRequest()) is False
        assert should_capture(MockRequest(), api_only=False) is True

    def test_fetch_destination_header_is_case_insensitive(self):
        class MockRequest:
            url = 'https://app.example.com/home'
            path = '/home'
            method = 'GET'
            headers = {'sec-fetch-dest': 'document'}

        assert should_capture(MockRequest()) is False

    def test_should_capture_only_matching_host(self):
        class ApiRequest:
            url = 'https://develop-gcp-adminapi.trackingmore.com/v1/shipments/list'
            path = '/v1/shipments/list'
            method = 'POST'
            headers = {'Sec-Fetch-Dest': 'empty'}

        class ThirdPartyRequest:
            url = 'https://example.com/v1/events'
            path = '/v1/events'
            method = 'POST'
            headers = {'Sec-Fetch-Dest': 'empty'}

        assert should_capture(ApiRequest(), include_hosts=['trackingmore.com']) is True
        assert should_capture(ThirdPartyRequest(), include_hosts=['trackingmore.com']) is False

    def test_tracking_api_path_is_not_mistaken_for_analytics(self):
        class MockRequest:
            url = 'https://api.example.com/api/tracking/create'
            path = '/api/tracking/create'
            method = 'POST'
            headers = {'Sec-Fetch-Dest': 'empty'}

        assert should_capture(MockRequest()) is True


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
