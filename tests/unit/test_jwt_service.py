"""
JWT 서비스 단위 테스트
"""
import pytest
from unittest.mock import Mock, patch
import json
import base64
from datetime import datetime, timezone, timedelta

# 이 파일의 모든 테스트를 단위 테스트로 표시
pytestmark = pytest.mark.unit

# 테스트할 모듈 import
from common.jwt_service import JWTService
from common.exceptions import AuthenticationError


def test_jwt_service_init():
    """JWTService 초기화 테스트"""
    mock_app_config = Mock()
    service = JWTService(mock_app_config)
    
    assert service.app_config == mock_app_config
    assert service.algorithm == 'HS256'
    assert service.expiration_hours == 1


def test_get_secret_key():
    """시크릿 키 가져오기 테스트"""
    mock_app_config = Mock()
    mock_app_config.get_jwt_secret.return_value = 'test-secret'
    
    service = JWTService(mock_app_config)
    secret = service._get_secret_key()
    
    assert secret == 'test-secret'


def test_get_secret_key_fallback():
    """시크릿 키 가져오기 실패 시 기본값 테스트"""
    mock_app_config = Mock()
    mock_app_config.get_jwt_secret.side_effect = Exception("No secret")
    
    service = JWTService(mock_app_config)
    secret = service._get_secret_key()
    
    assert secret == "default-test-secret-key-32-characters"


def test_create_token():
    """토큰 생성 테스트"""
    mock_app_config = Mock()
    service = JWTService(mock_app_config)
    
    payload = {'user_id': 'test-user', 'role': 'admin'}
    token = service.create_token(payload)
    
    assert isinstance(token, str)
    assert token.startswith('Bearer.')


def test_verify_token_valid():
    """유효한 토큰 검증 테스트"""
    mock_app_config = Mock()
    service = JWTService(mock_app_config)
    
    # 토큰 생성
    payload = {'user_id': 'test-user', 'role': 'admin'}
    token = service.create_token(payload)
    
    # 토큰 검증
    result = service.verify_token(token)
    
    assert result['user_id'] == 'test-user'
    assert result['role'] == 'admin'


def test_verify_token_invalid_format():
    """잘못된 형식 토큰 검증 테스트"""
    mock_app_config = Mock()
    service = JWTService(mock_app_config)
    
    with pytest.raises(AuthenticationError, match="Token verification failed"):
        service.verify_token('invalid-token')


def test_verify_token_empty():
    """빈 토큰 검증 테스트"""
    mock_app_config = Mock()
    service = JWTService(mock_app_config)
    
    with pytest.raises(AuthenticationError, match="Token verification failed"):
        service.verify_token('')


def test_verify_token_expired():
    """만료된 토큰 검증 테스트"""
    mock_app_config = Mock()
    service = JWTService(mock_app_config)
    
    # 만료된 토큰 생성 (수동으로)
    past_time = datetime.now(timezone.utc) - timedelta(hours=2)
    expired_payload = {
        'user_id': 'test-user',
        'exp': past_time.isoformat(),
        'iat': (past_time - timedelta(hours=1)).isoformat()
    }
    
    token_data = json.dumps(expired_payload)
    encoded_token = base64.b64encode(token_data.encode()).decode()
    expired_token = f"Bearer.{encoded_token}"
    
    with pytest.raises(AuthenticationError, match="Token verification failed"):
        service.verify_token(expired_token)


def test_extract_token_from_header():
    """헤더에서 토큰 추출 테스트"""
    mock_app_config = Mock()
    service = JWTService(mock_app_config)
    
    auth_header = 'Bearer.some-token'
    result = service.extract_token_from_header(auth_header)
    
    assert result == auth_header


def test_extract_token_from_header_empty():
    """빈 헤더에서 토큰 추출 테스트"""
    mock_app_config = Mock()
    service = JWTService(mock_app_config)
    
    with pytest.raises(AuthenticationError, match="Authorization header is required"):
        service.extract_token_from_header('')


def test_get_user_from_token():
    """토큰에서 사용자 정보 추출 테스트"""
    mock_app_config = Mock()
    service = JWTService(mock_app_config)
    
    # 토큰 생성
    payload = {'username': 'testuser', 'role': 'admin'}
    token = service.create_token(payload)
    
    # 사용자 정보 추출
    user_info = service.get_user_from_token(token)
    
    assert user_info['username'] == 'testuser'
    assert user_info['role'] == 'admin'
    assert user_info['authenticated'] is True


def test_jwt_service_with_config_error():
    """설정 오류 시 기본값 사용 테스트"""
    mock_app_config = Mock()
    mock_app_config.get_jwt_secret.side_effect = Exception("Config error")
    
    service = JWTService(mock_app_config)
    
    # 기본 시크릿으로 토큰 생성 및 검증이 가능한지 확인
    payload = {'user_id': 'test-user'}
    token = service.create_token(payload)
    
    result = service.verify_token(token)
    assert result['user_id'] == 'test-user'


def test_jwt_service_create_token_with_extra_fields():
    """추가 필드와 함께 토큰 생성 테스트"""
    mock_app_config = Mock()
    service = JWTService(mock_app_config)
    
    payload = {
        'user_id': 'test-user',
        'role': 'admin',
        'email': 'test@example.com',
        'permissions': ['read', 'write']
    }
    
    token = service.create_token(payload)
    result = service.verify_token(token)
    
    assert result['user_id'] == 'test-user'
    assert result['role'] == 'admin'
    assert result['email'] == 'test@example.com'
    assert result['permissions'] == ['read', 'write']


def test_jwt_service_malformed_base64():
    """잘못된 Base64 토큰 테스트"""
    mock_app_config = Mock()
    service = JWTService(mock_app_config)
    
    # 잘못된 Base64 형식
    invalid_token = "Bearer.invalid-base64!"
    
    with pytest.raises(AuthenticationError):
        service.verify_token(invalid_token)


def test_get_user_from_token_missing_fields():
    """토큰에서 필드가 누락된 경우 테스트"""
    mock_app_config = Mock()
    service = JWTService(mock_app_config)
    
    # username이 없는 토큰
    payload = {'user_id': 'test-user', 'role': 'admin'}
    token = service.create_token(payload)
    
    user_info = service.get_user_from_token(token)
    
    assert user_info['username'] is None  # get()로 안전하게 가져옴
    assert user_info['role'] == 'admin'
    assert user_info['authenticated'] is True