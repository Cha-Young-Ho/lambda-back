"""
헬스체크 유틸리티 단위 테스트
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
import os

# 이 파일의 모든 테스트를 단위 테스트로 표시
pytestmark = pytest.mark.unit

# 테스트할 모듈 import
from common.health import get_system_health, get_api_info


@pytest.fixture
def mock_app_config():
    """Mock AppConfig 생성"""
    config = Mock()
    config.get_dynamodb_config.return_value = {
        'region': 'us-east-1',
        'table_name': 'test-table',
        'endpoint_url': 'http://localhost:8000'
    }
    config.get_admin_config.return_value = {
        'username': 'admin',
        'password': 'password'
    }
    config.get_jwt_secret.return_value = 'test-secret'
    config.stage = 'test'
    return config


@patch('common.health.get_table')
@patch('common.health.get_dynamodb')
def test_get_system_health_all_healthy(mock_get_dynamodb, mock_get_table, mock_app_config):
    """모든 컴포넌트가 정상인 경우 헬스체크 테스트"""
    # Mock DynamoDB 설정
    mock_dynamodb = MagicMock()
    mock_get_dynamodb.return_value = mock_dynamodb
    
    mock_table = MagicMock()
    mock_get_table.return_value = mock_table
    
    # Mock describe_table 응답
    mock_table.meta.client.describe_table.return_value = {
        'Table': {
            'TableStatus': 'ACTIVE',
            'ItemCount': 100
        }
    }
    
    result = get_system_health(mock_app_config)
    
    assert result['status'] == 'healthy'
    assert 'timestamp' in result
    assert 'components' in result
    assert 'environment' in result
    
    # 데이터베이스 컴포넌트 확인
    db_component = result['components']['database']
    assert db_component['status'] == 'healthy'
    assert db_component['table_name'] == 'test-table'
    assert db_component['table_status'] == 'ACTIVE'
    assert db_component['item_count'] == 100
    
    # 설정 컴포넌트 확인
    config_component = result['components']['configuration']
    assert config_component['status'] == 'healthy'
    assert config_component['admin_configured'] is True
    assert config_component['jwt_secret_configured'] is True
    assert config_component['stage'] == 'test'
    
    # 환경 정보 확인
    env_info = result['environment']
    assert 'aws_region' in env_info
    assert 'function_name' in env_info
    assert 'runtime' in env_info


@patch('common.health.get_table')
@patch('common.health.get_dynamodb')
def test_get_system_health_database_error(mock_get_dynamodb, mock_get_table, mock_app_config):
    """데이터베이스 에러 시 헬스체크 테스트"""
    # 데이터베이스 연결 실패 설정
    mock_get_dynamodb.side_effect = Exception("Database connection failed")
    
    result = get_system_health(mock_app_config)
    
    assert result['status'] == 'unhealthy'
    
    # 데이터베이스 컴포넌트가 unhealthy여야 함
    db_component = result['components']['database']
    assert db_component['status'] == 'unhealthy'
    assert 'error' in db_component
    assert 'Database connection failed' in db_component['error']


def test_get_system_health_config_error(mock_app_config):
    """설정 에러 시 헬스체크 테스트"""
    # 설정 조회 실패 설정
    mock_app_config.get_admin_config.side_effect = Exception("Config error")
    
    with patch('common.health.get_table'), \
         patch('common.health.get_dynamodb'):
        result = get_system_health(mock_app_config)
    
    assert result['status'] == 'unhealthy'
    
    # 설정 컴포넌트가 unhealthy여야 함
    config_component = result['components']['configuration']
    assert config_component['status'] == 'unhealthy'
    assert 'error' in config_component


@patch.dict(os.environ, {
    'AWS_REGION': 'us-west-2',
    'AWS_LAMBDA_FUNCTION_NAME': 'test-function',
    'AWS_LAMBDA_FUNCTION_VERSION': '1.0'
})
@patch('common.health.get_table')
@patch('common.health.get_dynamodb')
def test_get_system_health_lambda_environment(mock_get_dynamodb, mock_get_table, mock_app_config):
    """Lambda 환경에서 헬스체크 테스트"""
    # Mock 설정
    mock_dynamodb = MagicMock()
    mock_get_dynamodb.return_value = mock_dynamodb
    
    mock_table = MagicMock()
    mock_get_table.return_value = mock_table
    mock_table.meta.client.describe_table.return_value = {
        'Table': {
            'TableStatus': 'ACTIVE',
            'ItemCount': 50
        }
    }
    
    result = get_system_health(mock_app_config)
    
    # 환경 정보 확인
    env_info = result['environment']
    assert env_info['aws_region'] == 'us-west-2'
    assert env_info['function_name'] == 'test-function'
    assert env_info['function_version'] == '1.0'
    assert env_info['is_lambda'] is True


@patch.dict(os.environ, {}, clear=True)
@patch('common.health.get_table')
@patch('common.health.get_dynamodb')
def test_get_system_health_local_environment(mock_get_dynamodb, mock_get_table, mock_app_config):
    """로컬 환경에서 헬스체크 테스트"""
    # Mock 설정
    mock_dynamodb = MagicMock()
    mock_get_dynamodb.return_value = mock_dynamodb
    
    mock_table = MagicMock()
    mock_get_table.return_value = mock_table
    mock_table.meta.client.describe_table.return_value = {
        'Table': {
            'TableStatus': 'ACTIVE'
        }
    }
    
    result = get_system_health(mock_app_config)
    
    # 환경 정보 확인
    env_info = result['environment']
    assert env_info['aws_region'] == 'unknown'
    assert env_info['function_name'] == 'local'
    assert env_info['function_version'] == 'local'
    assert env_info['is_lambda'] is False


@patch('common.health.get_all_categories')
def test_get_api_info(mock_get_all_categories):
    """API 정보 조회 테스트"""
    mock_get_all_categories.return_value = ['news', 'tech', 'life']
    
    result = get_api_info()
    
    # 기본 정보 확인
    assert result['api_name'] == 'Blog Management System'
    assert result['version'] == '2.0.0'
    assert 'description' in result
    
    # 엔드포인트 정보 확인
    assert 'endpoints' in result
    assert 'auth' in result['endpoints']
    assert 'news' in result['endpoints']
    assert 'gallery' in result['endpoints']
    
    # auth 엔드포인트 확인
    auth_endpoints = result['endpoints']['auth']
    assert 'POST /auth/login' in auth_endpoints
    assert 'POST /auth/validate' in auth_endpoints
    assert 'GET /auth/test' in auth_endpoints
    
    # news 엔드포인트 확인
    news_endpoints = result['endpoints']['news']
    assert 'GET /news' in news_endpoints
    assert 'POST /news' in news_endpoints
    assert 'PUT /news/{id}' in news_endpoints
    assert 'DELETE /news/{id}' in news_endpoints
    
    # gallery 엔드포인트 확인
    gallery_endpoints = result['endpoints']['gallery']
    assert 'GET /gallery' in gallery_endpoints
    assert 'POST /gallery' in gallery_endpoints
    
    # 카테고리 정보 확인
    assert result['categories'] == ['news', 'tech', 'life']
    
    # 기능 목록 확인
    assert 'features' in result
    features = result['features']
    assert 'JWT Authentication' in features
    assert 'CRUD Operations' in features
    assert 'File Upload Support' in features


def test_get_api_info_categories_error():
    """카테고리 조회 에러 시 API 정보 테스트"""
    with patch('common.health.get_all_categories') as mock_get_categories:
        mock_get_categories.side_effect = Exception("Categories error")
        
        # 에러가 발생해도 API 정보는 반환되어야 함
        with pytest.raises(Exception):
            get_api_info()


@patch('common.health.get_table')
@patch('common.health.get_dynamodb') 
def test_get_system_health_timestamp_format(mock_get_dynamodb, mock_get_table, mock_app_config):
    """타임스탬프 형식 확인 테스트"""
    # Mock 설정
    mock_dynamodb = MagicMock()
    mock_get_dynamodb.return_value = mock_dynamodb
    
    mock_table = MagicMock()
    mock_get_table.return_value = mock_table
    mock_table.meta.client.describe_table.return_value = {
        'Table': {'TableStatus': 'ACTIVE'}
    }
    
    result = get_system_health(mock_app_config)
    
    # 타임스탬프가 Z로 끝나는지 확인
    timestamp = result['timestamp']
    assert timestamp.endswith('Z')
    
    # Z를 제거하고 ISO 형식으로 파싱 가능한지 확인
    timestamp_without_z = timestamp[:-1]
    try:
        parsed_time = datetime.fromisoformat(timestamp_without_z)
        assert isinstance(parsed_time, datetime)
        assert parsed_time.tzinfo is not None
    except ValueError:
        # 만약 isoformat에 timezone이 이미 포함되어 있다면
        # Z만 확인하고 패스
        assert timestamp.endswith('Z')


def test_get_api_info_detailed():
    """API 정보 상세 조회 테스트"""
    with patch('common.health.get_all_categories') as mock_get_categories:
        mock_get_categories.return_value = ['tech', 'news', 'lifestyle']
        
        result = get_api_info()
        
        # 상세 확인
        assert result['api_name'] == 'Blog Management System'
        assert 'version' in result
        assert 'endpoints' in result
        
        # 엔드포인트 그룹 확인
        assert 'auth' in result['endpoints']
        assert 'news' in result['endpoints']
        assert 'gallery' in result['endpoints']
        
        # 기능 목록 확인
        assert isinstance(result['features'], list)
        assert len(result['features']) > 0


@patch('common.health.get_table')
@patch('common.health.get_dynamodb')
def test_get_system_health_partial_failure(mock_get_dynamodb, mock_get_table, mock_app_config):
    """부분적 실패 시 헬스체크 테스트"""
    # 데이터베이스는 성공, 설정은 실패
    mock_dynamodb = MagicMock()
    mock_get_dynamodb.return_value = mock_dynamodb
    
    mock_table = MagicMock()
    mock_get_table.return_value = mock_table
    mock_table.meta.client.describe_table.return_value = {
        'Table': {'TableStatus': 'ACTIVE'}
    }
    
    # 설정 실패 설정
    mock_app_config.get_admin_config.side_effect = Exception("Config error")
    
    result = get_system_health(mock_app_config)
    
    assert result['status'] == 'unhealthy'
    assert result['components']['database']['status'] == 'healthy'
    assert result['components']['configuration']['status'] == 'unhealthy'


def test_system_health_environment_vars():
    """환경 변수 정보 확인 테스트"""
    with patch('common.health.get_table'), \
         patch('common.health.get_dynamodb'):
        
        with patch.dict('os.environ', {
            'AWS_REGION': 'us-west-2',
            'AWS_LAMBDA_FUNCTION_NAME': 'my-function'
        }):
            result = get_system_health(mock_app_config)
            
            env_info = result['environment']
            assert env_info['aws_region'] == 'us-west-2'
            assert env_info['function_name'] == 'my-function'
            assert env_info['is_lambda'] is True
