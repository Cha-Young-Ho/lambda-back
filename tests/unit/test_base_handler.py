"""
베이스 핸들러 모듈 단위 테스트
"""
import pytest
import json
from unittest.mock import Mock, patch, MagicMock

# 이 파일의 모든 테스트를 단위 테스트로 표시
pytestmark = pytest.mark.unit

# 테스트할 모듈 import
from common.base_handler import BaseAPIHandler


class ConcreteAPIHandler(BaseAPIHandler):
    """테스트용 구체적인 API 핸들러"""
    
    def handle_get(self, event, context):
        return self.success_response({'message': 'GET request handled'})
    
    def handle_post(self, event, context):
        return self.success_response({'message': 'POST request handled'})


class TestBaseAPIHandler:
    """BaseAPIHandler 클래스 테스트"""
    
    @pytest.fixture
    def mock_app_config(self):
        """앱 설정 모킹"""
        config = Mock()
        return config
    
    @pytest.fixture
    def handler(self, mock_app_config):
        """핸들러 인스턴스"""
        return ConcreteAPIHandler(mock_app_config)
    
    def test_init(self, mock_app_config):
        """BaseAPIHandler 초기화 테스트"""
        handler = ConcreteAPIHandler(mock_app_config)
        
        assert handler.app_config == mock_app_config
    
    def test_success_response_basic(self, handler):
        """기본 성공 응답 테스트"""
        data = {'message': 'success'}
        
        response = handler.success_response(data)
        
        assert response['statusCode'] == 200
        assert 'headers' in response
        assert response['headers']['Content-Type'] == 'application/json'
        assert response['headers']['Access-Control-Allow-Origin'] == '*'
        
        body = json.loads(response['body'])
        assert body['success'] is True
        assert body['data'] == data
    
    def test_success_response_with_custom_status(self, handler):
        """사용자 정의 상태 코드로 성공 응답 테스트"""
        data = {'message': 'created'}
        status_code = 201
        
        response = handler.success_response(data, status_code)
        
        assert response['statusCode'] == 201
        body = json.loads(response['body'])
        assert body['success'] is True
        assert body['data'] == data
    
    def test_error_response_basic(self, handler):
        """기본 오류 응답 테스트"""
        message = 'Something went wrong'
        
        response = handler.error_response(message)
        
        assert response['statusCode'] == 400
        assert response['headers']['Content-Type'] == 'application/json'
        
        body = json.loads(response['body'])
        assert body['success'] is False
        assert body['error'] == message
    
    def test_error_response_with_custom_status(self, handler):
        """사용자 정의 상태 코드로 오류 응답 테스트"""
        message = 'Not found'
        status_code = 404
        
        response = handler.error_response(message, status_code)
        
        assert response['statusCode'] == 404
        body = json.loads(response['body'])
        assert body['success'] is False
        assert body['error'] == message
    
    def test_validation_error_response(self, handler):
        """유효성 검사 오류 응답 테스트"""
        errors = {
            'title': '제목은 필수입니다',
            'content': '내용은 10자 이상이어야 합니다'
        }
        
        response = handler.validation_error_response(errors)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['success'] is False
        assert body['error'] == '유효성 검사 실패'
        assert body['validation_errors'] == errors
    
    def test_parse_json_body_valid(self, handler):
        """유효한 JSON 본문 파싱 테스트"""
        event = {
            'body': json.dumps({'title': '테스트', 'content': '내용'})
        }
        
        result = handler.parse_json_body(event)
        
        assert result == {'title': '테스트', 'content': '내용'}
    
    def test_parse_json_body_invalid_json(self, handler):
        """잘못된 JSON 본문 파싱 테스트"""
        event = {
            'body': 'invalid json'
        }
        
        result = handler.parse_json_body(event)
        
        assert result is None
    
    def test_parse_json_body_empty(self, handler):
        """빈 본문 파싱 테스트"""
        event = {
            'body': None
        }
        
        result = handler.parse_json_body(event)
        
        assert result is None
    
    def test_parse_json_body_empty_string(self, handler):
        """빈 문자열 본문 파싱 테스트"""
        event = {
            'body': ''
        }
        
        result = handler.parse_json_body(event)
        
        assert result is None
    
    def test_get_query_params_basic(self, handler):
        """기본 쿼리 파라미터 추출 테스트"""
        event = {
            'queryStringParameters': {
                'page': '1',
                'limit': '10',
                'category': '뉴스'
            }
        }
        
        result = handler.get_query_params(event)
        
        assert result == {'page': '1', 'limit': '10', 'category': '뉴스'}
    
    def test_get_query_params_none(self, handler):
        """쿼리 파라미터가 None인 경우 테스트"""
        event = {
            'queryStringParameters': None
        }
        
        result = handler.get_query_params(event)
        
        assert result == {}
    
    def test_get_query_params_missing(self, handler):
        """쿼리 파라미터 키가 없는 경우 테스트"""
        event = {}
        
        result = handler.get_query_params(event)
        
        assert result == {}
    
    def test_get_path_params_basic(self, handler):
        """기본 경로 파라미터 추출 테스트"""
        event = {
            'pathParameters': {
                'id': 'test-id',
                'category': 'news'
            }
        }
        
        result = handler.get_path_params(event)
        
        assert result == {'id': 'test-id', 'category': 'news'}
    
    def test_get_path_params_none(self, handler):
        """경로 파라미터가 None인 경우 테스트"""
        event = {
            'pathParameters': None
        }
        
        result = handler.get_path_params(event)
        
        assert result == {}
    
    def test_validate_required_fields_success(self, handler):
        """필수 필드 유효성 검사 성공 테스트"""
        data = {
            'title': '테스트 제목',
            'content': '테스트 내용',
            'category': '뉴스'
        }
        required_fields = ['title', 'content']
        
        errors = handler.validate_required_fields(data, required_fields)
        
        assert errors == {}
    
    def test_validate_required_fields_missing(self, handler):
        """필수 필드 누락 유효성 검사 테스트"""
        data = {
            'title': '테스트 제목'
            # content 누락
        }
        required_fields = ['title', 'content']
        
        errors = handler.validate_required_fields(data, required_fields)
        
        assert 'content' in errors
        assert errors['content'] == 'content 필드는 필수입니다'
    
    def test_validate_required_fields_empty_value(self, handler):
        """필수 필드 빈 값 유효성 검사 테스트"""
        data = {
            'title': '',  # 빈 문자열
            'content': '   '  # 공백만
        }
        required_fields = ['title', 'content']
        
        errors = handler.validate_required_fields(data, required_fields)
        
        assert 'title' in errors
        assert 'content' in errors
    
    def test_handle_request_get_method(self, handler):
        """GET 요청 처리 테스트"""
        event = {
            'httpMethod': 'GET'
        }
        context = {}
        
        response = handler.handle_request(event, context)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['data']['message'] == 'GET request handled'
    
    def test_handle_request_post_method(self, handler):
        """POST 요청 처리 테스트"""
        event = {
            'httpMethod': 'POST'
        }
        context = {}
        
        response = handler.handle_request(event, context)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['data']['message'] == 'POST request handled'
    
    def test_handle_request_unsupported_method(self, handler):
        """지원하지 않는 HTTP 메서드 테스트"""
        event = {
            'httpMethod': 'DELETE'
        }
        context = {}
        
        response = handler.handle_request(event, context)
        
        assert response['statusCode'] == 405
        body = json.loads(response['body'])
        assert body['error'] == 'Method not allowed: DELETE'
    
    def test_handle_request_exception_handling(self, handler):
        """요청 처리 중 예외 발생 테스트"""
        # handle_get 메서드가 예외를 발생하도록 설정
        original_handle_get = handler.handle_get
        
        def mock_handle_get(event, context):
            raise Exception("Test exception")
        
        handler.handle_get = mock_handle_get
        
        event = {'httpMethod': 'GET'}
        context = {}
        
        response = handler.handle_request(event, context)
        
        assert response['statusCode'] == 500
        body = json.loads(response['body'])
        assert body['error'] == 'Internal server error'
        
        # 원래 메서드 복원
        handler.handle_get = original_handle_get
    
    def test_cors_headers_included(self, handler):
        """CORS 헤더 포함 테스트"""
        response = handler.success_response({'test': 'data'})
        
        headers = response['headers']
        assert headers['Access-Control-Allow-Origin'] == '*'
        assert headers['Access-Control-Allow-Methods'] == 'GET, POST, PUT, DELETE, OPTIONS'
        assert headers['Access-Control-Allow-Headers'] == 'Content-Type, Authorization'
    
    def test_options_method_handling(self, handler):
        """OPTIONS 메서드 처리 테스트 (CORS preflight)"""
        event = {
            'httpMethod': 'OPTIONS'
        }
        context = {}
        
        response = handler.handle_request(event, context)
        
        assert response['statusCode'] == 200
        assert response['body'] == ''
        assert 'Access-Control-Allow-Origin' in response['headers']
    
    def test_extract_user_from_context(self, handler):
        """컨텍스트에서 사용자 정보 추출 테스트"""
        context = {
            'user': {
                'user_id': 'test-user',
                'role': 'admin',
                'email': 'test@example.com'
            }
        }
        
        user = handler.extract_user_from_context(context)
        
        assert user['user_id'] == 'test-user'
        assert user['role'] == 'admin'
        assert user['email'] == 'test@example.com'
    
    def test_extract_user_from_context_no_user(self, handler):
        """사용자 정보가 없는 컨텍스트에서 추출 테스트"""
        context = {}
        
        user = handler.extract_user_from_context(context)
        
        assert user is None
    
    def test_format_datetime_response(self, handler):
        """날짜/시간 응답 포맷팅 테스트"""
        from datetime import datetime, timezone
        
        data = {
            'title': '테스트',
            'created_at': datetime(2025, 7, 6, 12, 0, 0, tzinfo=timezone.utc),
            'updated_at': datetime(2025, 7, 6, 13, 0, 0, tzinfo=timezone.utc)
        }
        
        formatted = handler.format_datetime_response(data)
        
        assert formatted['created_at'] == '2025-07-06T12:00:00+00:00'
        assert formatted['updated_at'] == '2025-07-06T13:00:00+00:00'
        assert formatted['title'] == '테스트'
    
    def test_format_datetime_response_no_datetime(self, handler):
        """날짜/시간이 없는 데이터 포맷팅 테스트"""
        data = {
            'title': '테스트',
            'count': 5
        }
        
        formatted = handler.format_datetime_response(data)
        
        assert formatted == data  # 변경되지 않음
