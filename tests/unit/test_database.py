"""
데이터베이스 연결 유틸리티 단위 테스트
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal
import os

# 이 파일의 모든 테스트를 단위 테스트로 표시
pytestmark = pytest.mark.unit

# 테스트할 모듈 import
from common.database import get_dynamodb, get_table, safe_decimal_convert


@patch('boto3.resource')
@patch.dict(os.environ, {}, clear=True)
def test_get_dynamodb_local_environment(mock_resource):
    """로컬 환경에서 DynamoDB 연결 테스트"""
    mock_db = MagicMock()
    mock_resource.return_value = mock_db
    
    result = get_dynamodb('us-east-1', 'test-table')
    
    assert result == mock_db
    mock_resource.assert_called_once_with(
        'dynamodb',
        endpoint_url='http://host.docker.internal:8000',
        region_name='us-east-1',
        aws_access_key_id='dummy',
        aws_secret_access_key='dummy'
    )


@patch('boto3.resource')
@patch.dict(os.environ, {'AWS_LAMBDA_FUNCTION_NAME': 'test-function'})
def test_get_dynamodb_lambda_environment(mock_resource):
    """AWS Lambda 환경에서 DynamoDB 연결 테스트"""
    mock_db = MagicMock()
    mock_resource.return_value = mock_db
    
    result = get_dynamodb('us-east-1', 'test-table')
    
    assert result == mock_db
    mock_resource.assert_called_once_with(
        'dynamodb', 
        region_name='us-east-1'
    )


@patch('boto3.resource')
@patch.dict(os.environ, {'AWS_SAM_LOCAL': 'true'})
def test_get_dynamodb_sam_local_environment(mock_resource):
    """SAM Local 환경에서 DynamoDB 연결 테스트"""
    mock_db = MagicMock()
    mock_resource.return_value = mock_db
    
    result = get_dynamodb('us-east-1', 'test-table')
    
    assert result == mock_db
    mock_resource.assert_called_once_with(
        'dynamodb',
        endpoint_url='http://host.docker.internal:8000',
        region_name='us-east-1',
        aws_access_key_id='dummy',
        aws_secret_access_key='dummy'
    )


@patch('boto3.resource')
def test_get_dynamodb_with_custom_endpoint(mock_resource):
    """커스텀 엔드포인트로 DynamoDB 연결 테스트"""
    mock_db = MagicMock()
    mock_resource.return_value = mock_db
    
    custom_endpoint = 'http://localhost:8001'
    result = get_dynamodb('us-west-2', 'test-table', custom_endpoint)
    
    assert result == mock_db
    mock_resource.assert_called_once_with(
        'dynamodb',
        endpoint_url=custom_endpoint,
        region_name='us-west-2',
        aws_access_key_id='dummy',
        aws_secret_access_key='dummy'
    )


@patch('boto3.resource')
@patch('builtins.print')
def test_get_dynamodb_connection_error(mock_print, mock_resource):
    """DynamoDB 연결 실패 테스트"""
    mock_resource.side_effect = Exception('Connection failed')
    
    result = get_dynamodb('us-east-1', 'test-table')
    
    assert result is None
    mock_print.assert_called()


def test_get_table_success():
    """테이블 가져오기 성공 테스트"""
    mock_dynamodb = MagicMock()
    mock_table = MagicMock()
    mock_dynamodb.Table.return_value = mock_table
    
    result = get_table(mock_dynamodb, 'test-table')
    
    assert result == mock_table
    mock_dynamodb.Table.assert_called_once_with('test-table')


@patch('builtins.print')
def test_get_table_none_resource(mock_print):
    """DynamoDB 리소스가 None인 경우 테스트"""
    result = get_table(None, 'test-table')
    
    assert result is None
    mock_print.assert_called_with('DynamoDB resource is None')


@patch('builtins.print')
def test_get_table_error(mock_print):
    """테이블 가져오기 실패 테스트"""
    mock_dynamodb = MagicMock()
    mock_dynamodb.Table.side_effect = Exception('Table not found')
    
    result = get_table(mock_dynamodb, 'test-table')
    
    assert result is None
    mock_print.assert_called()


def test_safe_decimal_convert_decimal_to_int():
    """Decimal을 int로 변환 테스트"""
    decimal_value = Decimal('42')
    result = safe_decimal_convert(decimal_value)
    assert result == 42
    assert isinstance(result, int)


def test_safe_decimal_convert_decimal_to_float():
    """Decimal을 float로 변환 테스트"""
    decimal_value = Decimal('42.5')
    result = safe_decimal_convert(decimal_value)
    assert result == 42.5
    assert isinstance(result, float)


def test_safe_decimal_convert_dict():
    """딕셔너리 내 Decimal 변환 테스트"""
    data = {
        'int_value': Decimal('10'),
        'float_value': Decimal('10.5'),
        'string_value': 'test',
        'nested': {
            'nested_decimal': Decimal('20')
        }
    }
    
    result = safe_decimal_convert(data)
    
    assert result['int_value'] == 10
    assert isinstance(result['int_value'], int)
    assert result['float_value'] == 10.5
    assert isinstance(result['float_value'], float)
    assert result['string_value'] == 'test'
    assert result['nested']['nested_decimal'] == 20
    assert isinstance(result['nested']['nested_decimal'], int)


def test_safe_decimal_convert_list():
    """리스트 내 Decimal 변환 테스트"""
    data = [
        Decimal('1'),
        Decimal('2.5'),
        'string',
        [Decimal('3'), Decimal('4.5')]
    ]
    
    result = safe_decimal_convert(data)
    
    assert result[0] == 1
    assert isinstance(result[0], int)
    assert result[1] == 2.5
    assert isinstance(result[1], float)
    assert result[2] == 'string'
    assert result[3][0] == 3
    assert isinstance(result[3][0], int)
    assert result[3][1] == 4.5
    assert isinstance(result[3][1], float)


def test_safe_decimal_convert_non_decimal():
    """Decimal이 아닌 값 변환 테스트"""
    assert safe_decimal_convert('string') == 'string'
    assert safe_decimal_convert(42) == 42
    assert safe_decimal_convert(42.5) == 42.5
    assert safe_decimal_convert(True) == True
    assert safe_decimal_convert(None) == None


def test_safe_decimal_convert_bytes():
    """bytes 타입 처리 테스트"""
    data = b'test bytes'
    result = safe_decimal_convert(data)
    assert result == data
    assert isinstance(result, bytes)


def test_safe_decimal_convert_empty_collections():
    """빈 컬렉션 처리 테스트"""
    assert safe_decimal_convert({}) == {}
    assert safe_decimal_convert([]) == []
    assert safe_decimal_convert(set()) == []  # set은 list로 변환됨
