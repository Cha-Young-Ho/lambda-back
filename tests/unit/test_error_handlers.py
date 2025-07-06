"""
에러 핸들러 단위 테스트
"""
import pytest
from unittest.mock import Mock, patch

# 이 파일의 모든 테스트를 단위 테스트로 표시
pytestmark = pytest.mark.unit

# 테스트할 모듈 import
from common.error_handlers import (
    APIError, ValidationError, NotFoundError, UnauthorizedError, 
    ForbiddenError, ConflictError, handle_api_error, 
    validate_required_fields, validate_field_length,
    validate_pagination_params, safe_execute, ErrorContext
)


def test_validate_required_fields_missing_field():
    """필수 필드가 누락된 경우 검증 테스트"""
    data = {"name": "John"}
    required_fields = ["name", "email"]
    
    with pytest.raises(ValidationError) as exc_info:
        validate_required_fields(data, required_fields)
    
    assert "Missing required fields" in str(exc_info.value)


def test_api_error_initialization():
    """APIError 초기화 테스트"""
    error = APIError("Test error", 500, "TEST_ERROR")
    
    assert error.message == "Test error"
    assert error.status_code == 500
    assert error.error_code == "TEST_ERROR"
    assert str(error) == "Test error"


def test_api_error_default_values():
    """APIError 기본값 테스트"""
    error = APIError("Test error")
    
    assert error.message == "Test error"
    assert error.status_code == 500
    assert error.error_code == "INTERNAL_ERROR"


def test_validation_error():
    """ValidationError 테스트"""
    error = ValidationError("Invalid input", "email")
    
    assert error.message == "Invalid input"
    assert error.status_code == 400
    assert error.error_code == "VALIDATION_ERROR"
    assert error.field == "email"


def test_validation_error_no_field():
    """ValidationError 필드 없음 테스트"""
    error = ValidationError("Invalid input")
    
    assert error.field is None


def test_not_found_error():
    """NotFoundError 테스트"""
    error = NotFoundError("User", "123")
    
    assert error.message == "User not found: 123"
    assert error.status_code == 404
    assert error.error_code == "NOT_FOUND"


def test_unauthorized_error():
    """UnauthorizedError 테스트"""
    error = UnauthorizedError()
    
    assert error.message == "Unauthorized"
    assert error.status_code == 401
    assert error.error_code == "UNAUTHORIZED"


def test_unauthorized_error_custom_message():
    """UnauthorizedError 커스텀 메시지 테스트"""
    error = UnauthorizedError("Invalid token")
    
    assert error.message == "Invalid token"
    assert error.status_code == 401
    assert error.error_code == "UNAUTHORIZED"


def test_forbidden_error():
    """ForbiddenError 테스트"""
    error = ForbiddenError()
    
    assert error.message == "Forbidden"
    assert error.status_code == 403
    assert error.error_code == "FORBIDDEN"


def test_forbidden_error_custom_message():
    """ForbiddenError 커스텀 메시지 테스트"""
    error = ForbiddenError("Access denied")
    
    assert error.message == "Access denied"
    assert error.status_code == 403
    assert error.error_code == "FORBIDDEN"


def test_conflict_error():
    """ConflictError 테스트"""
    error = ConflictError("Resource already exists")
    
    assert error.message == "Resource already exists"
    assert error.status_code == 409
    assert error.error_code == "CONFLICT"


@patch('common.error_handlers.log_error')
@patch('common.error_handlers.create_error_response')
def test_handle_api_error_custom_error(mock_create_response, mock_log_error):
    """커스텀 API 에러 처리 테스트"""
    mock_create_response.return_value = {'statusCode': 400, 'body': '{"error": "test"}'}
    
    error = ValidationError("Invalid email")
    result = handle_api_error(error, "req-123")
    
    mock_log_error.assert_called_once()
    mock_create_response.assert_called_once_with(
        "Invalid email",
        400,
        "VALIDATION_ERROR"
    )
    assert result == {'statusCode': 400, 'body': '{"error": "test"}'}


@patch('common.error_handlers.log_error')
@patch('common.error_handlers.create_error_response')
def test_handle_api_error_value_error(mock_create_response, mock_log_error):
    """ValueError 처리 테스트"""
    mock_create_response.return_value = {'statusCode': 400, 'body': '{"error": "validation"}'}
    
    error = ValueError("Invalid value")
    result = handle_api_error(error)
    
    mock_log_error.assert_called_once()
    mock_create_response.assert_called_once_with(
        "Invalid value",
        400,
        "VALIDATION_ERROR"
    )


@patch('common.error_handlers.log_error')
@patch('common.error_handlers.create_error_response')
def test_handle_api_error_key_error(mock_create_response, mock_log_error):
    """KeyError 처리 테스트"""
    mock_create_response.return_value = {'statusCode': 400, 'body': '{"error": "missing_field"}'}
    
    error = KeyError("'email'")
    result = handle_api_error(error)
    
    mock_log_error.assert_called_once()
    mock_create_response.assert_called_once_with(
        'Missing required field: "\'email\'"',
        400,
        "MISSING_FIELD"
    )


@patch('common.error_handlers.log_error')
@patch('common.error_handlers.create_error_response')
def test_handle_api_error_unexpected_error(mock_create_response, mock_log_error):
    """예상치 못한 에러 처리 테스트"""
    mock_create_response.return_value = {'statusCode': 500, 'body': '{"error": "internal"}'}
    
    error = RuntimeError("Unexpected error")
    result = handle_api_error(error)
    
    mock_log_error.assert_called_once()
    mock_create_response.assert_called_once_with(
        "Internal server error",
        500,
        "INTERNAL_ERROR"
    )


def test_validate_required_fields_success():
    """필수 필드 검증 성공 테스트"""
    data = {"name": "John", "email": "john@example.com"}
    required_fields = ["name", "email"]
    
    # 예외가 발생하지 않아야 함
    validate_required_fields(data, required_fields)


def test_validate_required_fields_missing_field():
    """필수 필드 누락 테스트"""
    data = {"name": "John"}
    required_fields = ["name", "email"]
    
    with pytest.raises(ValidationError) as exc_info:
        validate_required_fields(data, required_fields)
    
    assert "Missing required fields" in str(exc_info.value)


def test_validate_required_fields_none_value():
    """필수 필드가 None인 경우 테스트"""
    data = {"name": "John", "email": None}
    required_fields = ["name", "email"]
    
    with pytest.raises(ValidationError) as exc_info:
        validate_required_fields(data, required_fields)
    
    assert "Missing required fields" in str(exc_info.value)


def test_validate_required_fields_empty_string():
    """필수 필드가 빈 문자열인 경우 테스트"""
    data = {"name": "John", "email": ""}
    required_fields = ["name", "email"]
    
    with pytest.raises(ValidationError) as exc_info:
        validate_required_fields(data, required_fields)
    
    assert "Missing required fields" in str(exc_info.value)


def test_validate_field_length_success():
    """필드 길이 검증 성공 테스트"""
    # 올바른 시그니처: validate_field_length(data, field_limits)
    data = {"name": "John"}
    field_limits = {"name": 10}
    
    # 예외가 발생하지 않아야 함
    validate_field_length(data, field_limits)


def test_validate_field_length_too_short():
    """필드 길이가 최대값을 초과한 경우 테스트"""
    data = {"name": "This is a very long name that exceeds limit"}
    field_limits = {"name": 10}
    
    with pytest.raises(ValidationError) as exc_info:
        validate_field_length(data, field_limits)
    
    assert "exceeds maximum length" in str(exc_info.value)


def test_validate_field_length_too_long():
    """필드 길이가 최대값보다 긴 경우 테스트"""
    data = {"description": "This is a very very very long description that definitely exceeds the maximum allowed length"}
    field_limits = {"description": 20}
    
    with pytest.raises(ValidationError) as exc_info:
        validate_field_length(data, field_limits)
    
    assert "exceeds maximum length" in str(exc_info.value)


def test_validate_field_length_none_value():
    """필드 값이 None인 경우 테스트"""
    data = {"name": None}
    field_limits = {"name": 10}
    
    # None 값은 허용되어야 함 (필수 필드 검증은 별도)
    validate_field_length(data, field_limits)


def test_validate_pagination_params_default():
    """기본 페이지네이션 파라미터 테스트"""
    page, limit = validate_pagination_params(None, None)
    
    assert page == 1
    assert limit == 10


def test_validate_pagination_params_valid():
    """유효한 페이지네이션 파라미터 테스트"""
    page, limit = validate_pagination_params("2", "20")
    
    assert page == 2
    assert limit == 20


def test_validate_pagination_params_invalid_page_zero():
    """페이지가 0인 경우 테스트"""
    with pytest.raises(ValidationError) as exc_info:
        validate_pagination_params("0", "10")
    
    assert "Page must be greater than 0" in str(exc_info.value)


def test_validate_pagination_params_invalid_page_negative():
    """페이지가 음수인 경우 테스트"""
    with pytest.raises(ValidationError) as exc_info:
        validate_pagination_params("-1", "10")
    
    assert "Page must be greater than 0" in str(exc_info.value)


def test_validate_pagination_params_invalid_limit_zero():
    """제한이 0인 경우 테스트"""
    with pytest.raises(ValidationError) as exc_info:
        validate_pagination_params("1", "0")
    
    assert "Limit must be greater than 0" in str(exc_info.value)


def test_validate_pagination_params_invalid_limit_negative():
    """제한이 음수인 경우 테스트"""
    with pytest.raises(ValidationError) as exc_info:
        validate_pagination_params("1", "-5")
    
    assert "Limit must be greater than 0" in str(exc_info.value)


def test_validate_pagination_params_limit_over_max():
    """제한이 최대값을 초과하는 경우 테스트"""
    page, limit = validate_pagination_params("1", "100")
    
    assert page == 1
    assert limit == 50  # 최대 50으로 제한


def test_validate_pagination_params_invalid_format():
    """잘못된 형식의 파라미터 테스트"""
    with pytest.raises(ValidationError) as exc_info:
        validate_pagination_params("abc", "10")
    
    assert "Page and limit must be valid integers" in str(exc_info.value)


def test_safe_execute_success():
    """안전한 함수 실행 성공 테스트"""
    def test_func(x, y):
        return x + y
    
    success, result, error = safe_execute(test_func, 1, 2)
    
    assert success is True
    assert result == 3
    assert error is None


def test_safe_execute_with_kwargs():
    """키워드 인자가 있는 안전한 함수 실행 테스트"""
    def test_func(x, y=10):
        return x + y
    
    success, result, error = safe_execute(test_func, 1, y=5)
    
    assert success is True
    assert result == 6
    assert error is None


def test_safe_execute_failure():
    """안전한 함수 실행 실패 테스트"""
    def test_func():
        raise ValueError("Test error")
    
    success, result, error = safe_execute(test_func)
    
    assert success is False
    assert result is None
    assert isinstance(error, ValueError)
    assert str(error) == "Test error"


@patch('common.error_handlers.log_error')
def test_error_context_success(mock_log_error):
    """에러 컨텍스트 성공 테스트"""
    with ErrorContext("test_operation", "test_resource", "req-123"):
        pass
    
    # 에러가 없으므로 로그는 호출되지 않아야 함
    mock_log_error.assert_not_called()


@patch('common.error_handlers.log_error')
def test_error_context_with_exception(mock_log_error):
    """에러 컨텍스트 예외 발생 테스트"""
    test_error = ValueError("Test error")
    
    with pytest.raises(ValueError):
        with ErrorContext("test_operation", "test_resource", "req-123"):
            raise test_error
    
    # 로그가 호출되어야 함
    mock_log_error.assert_called_once()
    args = mock_log_error.call_args
    
    assert args[0][1] == test_error  # 두 번째 인자가 에러
    assert args[0][2]['operation'] == "test_operation"  # 컨텍스트 정보
    assert args[0][2]['resource'] == "test_resource"
    assert args[0][3] == "req-123"  # request_id


@patch('common.error_handlers.log_error')
def test_error_context_minimal(mock_log_error):
    """최소한의 에러 컨텍스트 테스트"""
    test_error = RuntimeError("Test error")
    
    with pytest.raises(RuntimeError):
        with ErrorContext("test_operation"):
            raise test_error
    
    # 로그가 호출되어야 함
    mock_log_error.assert_called_once()
    args = mock_log_error.call_args
    
    assert args[0][1] == test_error
    assert args[0][2]['operation'] == "test_operation"
    assert args[0][2]['resource'] is None
    assert args[0][3] is None
