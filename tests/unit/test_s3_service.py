"""
S3 서비스 단위 테스트
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from botocore.exceptions import ClientError

# 이 파일의 모든 테스트를 단위 테스트로 표시
pytestmark = pytest.mark.unit

# 테스트할 모듈 import
from common.s3_service import S3Service


@pytest.fixture
def mock_app_config():
    """Mock AppConfig 생성"""
    config = Mock()
    config.get_config_value.return_value = 'test-bucket'
    config.stage = 'test'
    return config


@patch('common.s3_service.boto3')
def test_s3_service_init(mock_boto3, mock_app_config):
    """S3Service 초기화 테스트"""
    mock_s3_client = MagicMock()
    mock_boto3.client.return_value = mock_s3_client
    
    service = S3Service(mock_app_config)
    
    assert service.config == mock_app_config
    assert service.bucket_name == 'test-bucket'
    assert service.s3_client == mock_s3_client
    mock_boto3.client.assert_called_once_with('s3')


@patch('common.s3_service.boto3')
@patch('common.s3_service.datetime')
@patch('common.s3_service.uuid')
def test_generate_presigned_upload_url_success(mock_uuid, mock_datetime, mock_boto3, mock_app_config):
    """presigned URL 생성 성공 테스트"""
    # Mock 설정
    mock_s3_client = MagicMock()
    mock_boto3.client.return_value = mock_s3_client
    
    mock_datetime.now.return_value.strftime.return_value = '20231201_120000'
    mock_uuid.uuid4.return_value = Mock()
    mock_uuid.uuid4.return_value.__str__ = Mock(return_value='12345678-1234-1234-1234-123456789012')
    
    mock_s3_client.generate_presigned_url.return_value = 'https://test-presigned-url.com'
    
    service = S3Service(mock_app_config)
    
    result = service.generate_presigned_upload_url(
        content_type='image/jpeg',
        file_extension='.jpg',
        folder='test-folder'
    )
    
    # 결과 검증
    assert 'upload_url' in result
    assert 'file_key' in result
    assert 'file_url' in result
    assert 'expires_in' in result
    assert 'expires_at' in result
    assert result['upload_url'] == 'https://test-presigned-url.com'
    assert result['expires_in'] == 900


@patch('common.s3_service.boto3')
def test_delete_file_success(mock_boto3, mock_app_config):
    """파일 삭제 성공 테스트"""
    mock_s3_client = MagicMock()
    mock_boto3.client.return_value = mock_s3_client
    
    service = S3Service(mock_app_config)
    
    result = service.delete_file('test/file.jpg')
    
    assert result is True
    mock_s3_client.delete_object.assert_called_once_with(
        Bucket='test-bucket',
        Key='test/file.jpg'
    )


@patch('common.s3_service.boto3')
def test_delete_file_client_error(mock_boto3, mock_app_config):
    """파일 삭제 시 ClientError 처리 테스트"""
    mock_s3_client = MagicMock()
    mock_boto3.client.return_value = mock_s3_client
    
    # ClientError 발생 설정
    mock_s3_client.delete_object.side_effect = ClientError(
        error_response={'Error': {'Code': 'NoSuchKey', 'Message': 'Key not found'}},
        operation_name='delete_object'
    )
    
    service = S3Service(mock_app_config)
    
    result = service.delete_file('nonexistent/file.jpg')
    
    assert result is False


@patch('common.s3_service.boto3')
def test_delete_files_batch_success(mock_boto3, mock_app_config):
    """여러 파일 일괄 삭제 성공 테스트"""
    mock_s3_client = MagicMock()
    mock_boto3.client.return_value = mock_s3_client
    
    # Mock delete_objects 응답
    mock_s3_client.delete_objects.return_value = {
        'Deleted': [
            {'Key': 'file1.jpg'},
            {'Key': 'file2.png'}
        ],
        'Errors': []
    }
    
    service = S3Service(mock_app_config)
    
    file_keys = ['file1.jpg', 'file2.png']
    result = service.delete_files(file_keys)
    
    assert result['file1.jpg'] is True
    assert result['file2.png'] is True
    mock_s3_client.delete_objects.assert_called_once()


@patch('common.s3_service.boto3')
def test_delete_files_batch_with_errors(mock_boto3, mock_app_config):
    """일괄 삭제에서 일부 실패 테스트"""
    mock_s3_client = MagicMock()
    mock_boto3.client.return_value = mock_s3_client
    
    # Mock delete_objects 응답 (일부 성공, 일부 실패)
    mock_s3_client.delete_objects.return_value = {
        'Deleted': [
            {'Key': 'file1.jpg'}
        ],
        'Errors': [
            {'Key': 'file2.png', 'Code': 'NoSuchKey', 'Message': 'Key not found'}
        ]
    }
    
    service = S3Service(mock_app_config)
    
    file_keys = ['file1.jpg', 'file2.png']
    result = service.delete_files(file_keys)
    
    assert result['file1.jpg'] is True
    assert result['file2.png'] is False


@patch('common.s3_service.boto3')
def test_delete_files_empty_list(mock_boto3, mock_app_config):
    """빈 파일 목록으로 삭제 테스트"""
    mock_s3_client = MagicMock()
    mock_boto3.client.return_value = mock_s3_client
    
    service = S3Service(mock_app_config)
    
    result = service.delete_files([])
    
    assert result == {}
    mock_s3_client.delete_objects.assert_not_called()


@patch('common.s3_service.boto3')
def test_delete_files_client_error(mock_boto3, mock_app_config):
    """일괄 삭제에서 ClientError 처리 테스트"""
    mock_s3_client = MagicMock()
    mock_boto3.client.return_value = mock_s3_client
    
    # ClientError 발생 설정
    mock_s3_client.delete_objects.side_effect = ClientError(
        error_response={'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}},
        operation_name='delete_objects'
    )
    
    service = S3Service(mock_app_config)
    
    file_keys = ['file1.jpg', 'file2.png']
    result = service.delete_files(file_keys)
    
    assert result['file1.jpg'] is False
    assert result['file2.png'] is False


def test_extract_file_key_from_url(mock_app_config):
    """URL에서 파일 키 추출 테스트"""
    service = S3Service(mock_app_config)
    
    # 일반적인 S3 URL 형태
    url1 = 'https://test-bucket.s3.amazonaws.com/uploads/image.jpg'
    result1 = service.extract_file_key_from_url(url1)
    assert result1 == 'uploads/image.jpg'
    
    # 다른 형태의 S3 URL
    url2 = 'https://s3.amazonaws.com/test-bucket/documents/file.pdf'
    result2 = service.extract_file_key_from_url(url2)
    assert result2 == 'documents/file.pdf'
    
    # 잘못된 URL
    url3 = 'https://other-domain.com/file.jpg'
    result3 = service.extract_file_key_from_url(url3)
    assert result3 is None
    
    # 빈 URL
    result4 = service.extract_file_key_from_url('')
    assert result4 is None
    
    # None URL
    result5 = service.extract_file_key_from_url(None)
    assert result5 is None


@patch('common.s3_service.boto3')
def test_get_file_info_success(mock_boto3, mock_app_config):
    """파일 정보 조회 성공 테스트"""
    mock_s3_client = MagicMock()
    mock_boto3.client.return_value = mock_s3_client
    
    from datetime import datetime
    mock_datetime = datetime(2023, 12, 1, 12, 0, 0)
    
    # Mock head_object 응답
    mock_s3_client.head_object.return_value = {
        'ContentLength': 1024,
        'LastModified': mock_datetime,
        'ContentType': 'image/jpeg',
        'ETag': '"abc123def456"'
    }
    
    service = S3Service(mock_app_config)
    
    result = service.get_file_info('uploads/image.jpg')
    
    assert result['file_key'] == 'uploads/image.jpg'
    assert result['size'] == 1024
    assert result['content_type'] == 'image/jpeg'
    assert result['etag'] == 'abc123def456'
    assert 'last_modified' in result


@patch('common.s3_service.boto3')
def test_get_file_info_not_found(mock_boto3, mock_app_config):
    """존재하지 않는 파일 정보 조회 테스트"""
    mock_s3_client = MagicMock()
    mock_boto3.client.return_value = mock_s3_client
    
    # 404 에러 발생 설정
    mock_s3_client.head_object.side_effect = ClientError(
        error_response={'Error': {'Code': '404', 'Message': 'Not Found'}},
        operation_name='head_object'
    )
    
    service = S3Service(mock_app_config)
    
    result = service.get_file_info('nonexistent/file.jpg')
    
    assert result is None


@patch('common.s3_service.boto3')
def test_get_file_info_client_error(mock_boto3, mock_app_config):
    """파일 정보 조회 시 다른 ClientError 처리 테스트"""
    mock_s3_client = MagicMock()
    mock_boto3.client.return_value = mock_s3_client
    
    # 다른 에러 발생 설정
    mock_s3_client.head_object.side_effect = ClientError(
        error_response={'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}},
        operation_name='head_object'
    )
    
    service = S3Service(mock_app_config)
    
    result = service.get_file_info('restricted/file.jpg')
    
    assert result is None


# 유틸리티 함수 테스트
def test_get_allowed_content_types():
    """허용되는 콘텐츠 타입 테스트"""
    from common.s3_service import get_allowed_content_types
    
    # 이미지 타입만
    image_types = get_allowed_content_types('image')
    assert 'image/jpeg' in image_types
    assert 'image/png' in image_types
    assert 'application/pdf' not in image_types
    
    # 문서 타입만
    doc_types = get_allowed_content_types('document')
    assert 'application/pdf' in doc_types
    assert 'text/plain' in doc_types
    assert 'image/jpeg' not in doc_types
    
    # 모든 타입
    all_types = get_allowed_content_types('all')
    assert 'image/jpeg' in all_types
    assert 'application/pdf' in all_types
    
    # 기본값 (all)
    default_types = get_allowed_content_types()
    assert len(default_types) == len(all_types)


def test_get_file_extension_from_content_type():
    """콘텐츠 타입에서 파일 확장자 추출 테스트"""
    from common.s3_service import get_file_extension_from_content_type
    
    assert get_file_extension_from_content_type('image/jpeg') == '.jpg'
    assert get_file_extension_from_content_type('image/png') == '.png'
    assert get_file_extension_from_content_type('application/pdf') == '.pdf'
    assert get_file_extension_from_content_type('text/plain') == '.txt'
    
    # 지원하지 않는 타입
    assert get_file_extension_from_content_type('unknown/type') == ''


@patch('common.s3_service.boto3')
@patch('common.s3_service.datetime')
@patch('common.s3_service.uuid')
def test_generate_presigned_upload_url_client_error(mock_uuid, mock_datetime, mock_boto3, mock_app_config):
    """presigned URL 생성 시 ClientError 처리 테스트"""
    mock_s3_client = MagicMock()
    mock_boto3.client.return_value = mock_s3_client
    
    mock_datetime.now.return_value.strftime.return_value = '20231201_120000'
    mock_uuid.uuid4.return_value = Mock()
    mock_uuid.uuid4.return_value.__str__ = Mock(return_value='12345678-1234-1234-1234-123456789012')
    
    # ClientError 발생 설정
    mock_s3_client.generate_presigned_url.side_effect = ClientError(
        error_response={'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}},
        operation_name='generate_presigned_url'
    )
    
    service = S3Service(mock_app_config)
    
    with pytest.raises(Exception) as exc_info:
        service.generate_presigned_upload_url('image/jpeg')
    
    assert 'Failed to generate upload URL' in str(exc_info.value)


@patch('common.s3_service.boto3')
@patch('common.s3_service.datetime')
@patch('common.s3_service.uuid')
def test_generate_presigned_upload_url_no_extension(mock_uuid, mock_datetime, mock_boto3, mock_app_config):
    """파일 확장자 없이 presigned URL 생성 테스트"""
    # Mock 설정
    mock_s3_client = MagicMock()
    mock_boto3.client.return_value = mock_s3_client
    
    mock_datetime.now.return_value.strftime.return_value = '20231201_120000'
    mock_uuid.uuid4.return_value = Mock()
    mock_uuid.uuid4.return_value.__str__ = Mock(return_value='12345678-1234-1234-1234-123456789012')
    
    mock_s3_client.generate_presigned_url.return_value = 'https://test-presigned-url.com'
    
    service = S3Service(mock_app_config)
    
    result = service.generate_presigned_upload_url(
        content_type='application/octet-stream',
        file_extension=None,
        folder='uploads'
    )
    
    assert 'upload_url' in result
    assert 'file_key' in result
    # 확장자가 없으므로 파일 키에 확장자가 포함되지 않아야 함
    assert not result['file_key'].endswith('.')


@patch('common.s3_service.boto3')
@patch('common.s3_service.datetime')
@patch('common.s3_service.uuid')
def test_generate_presigned_upload_url_extension_without_dot(mock_uuid, mock_datetime, mock_boto3, mock_app_config):
    """점 없는 확장자로 presigned URL 생성 테스트"""
    # Mock 설정
    mock_s3_client = MagicMock()
    mock_boto3.client.return_value = mock_s3_client
    
    mock_datetime.now.return_value.strftime.return_value = '20231201_120000'
    mock_uuid.uuid4.return_value = Mock()
    mock_uuid.uuid4.return_value.__str__ = Mock(return_value='12345678-1234-1234-1234-123456789012')
    
    mock_s3_client.generate_presigned_url.return_value = 'https://test-presigned-url.com'
    
    service = S3Service(mock_app_config)
    
    result = service.generate_presigned_upload_url(
        content_type='image/png',
        file_extension='png',  # 점 없는 확장자
        folder='images'
    )
    
    assert 'file_key' in result
    # 점이 자동으로 추가되어야 함
    assert result['file_key'].endswith('.png')