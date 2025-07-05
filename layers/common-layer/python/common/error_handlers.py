"""
Standardized error handling for Lambda functions
표준화된 에러 처리 및 응답 생성
"""
import traceback
from typing import Dict, Any, Optional, Union
from common.response import create_error_response
from common.logging import get_logger, log_error

logger = get_logger(__name__)

class APIError(Exception):
    """API 관련 기본 에러 클래스"""
    def __init__(self, message: str, status_code: int = 500, error_code: str = "INTERNAL_ERROR"):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(self.message)

class ValidationError(APIError):
    """입력 검증 에러"""
    def __init__(self, message: str, field: Optional[str] = None):
        self.field = field
        super().__init__(message, 400, "VALIDATION_ERROR")

class NotFoundError(APIError):
    """리소스를 찾을 수 없는 에러"""
    def __init__(self, resource: str, identifier: str):
        message = f"{resource} not found: {identifier}"
        super().__init__(message, 404, "NOT_FOUND")

class UnauthorizedError(APIError):
    """인증 에러"""
    def __init__(self, message: str = "Unauthorized"):
        super().__init__(message, 401, "UNAUTHORIZED")

class ForbiddenError(APIError):
    """권한 에러"""
    def __init__(self, message: str = "Forbidden"):
        super().__init__(message, 403, "FORBIDDEN")

class ConflictError(APIError):
    """리소스 충돌 에러"""
    def __init__(self, message: str):
        super().__init__(message, 409, "CONFLICT")

def handle_api_error(error: Exception, request_id: Optional[str] = None) -> Dict[str, Any]:
    """
    API 에러를 표준화된 응답으로 변환
    
    Args:
        error: 발생한 에러
        request_id: 요청 ID
    
    Returns:
        표준화된 에러 응답
    """
    if isinstance(error, APIError):
        # 커스텀 API 에러
        log_error(logger, error, {'error_code': error.error_code}, request_id)
        
        return create_error_response(
            error.message,
            error.status_code,
            error.error_code
        )
    
    elif isinstance(error, ValueError):
        # 입력 검증 에러
        log_error(logger, error, {'error_type': 'validation'}, request_id)
        
        return create_error_response(
            str(error),
            400,
            "VALIDATION_ERROR"
        )
    
    elif isinstance(error, KeyError):
        # 필수 필드 누락
        log_error(logger, error, {'error_type': 'missing_field'}, request_id)
        
        return create_error_response(
            f"Missing required field: {str(error)}",
            400,
            "MISSING_FIELD"
        )
    
    else:
        # 예상치 못한 에러
        log_error(logger, error, {'error_type': 'unexpected'}, request_id)
        
        return create_error_response(
            "Internal server error",
            500,
            "INTERNAL_ERROR"
        )

def validate_required_fields(data: Dict[str, Any], required_fields: list) -> None:
    """
    필수 필드 검증
    
    Args:
        data: 검증할 데이터
        required_fields: 필수 필드 목록
    
    Raises:
        ValidationError: 필수 필드가 누락된 경우
    """
    missing_fields = []
    
    for field in required_fields:
        if field not in data or data[field] is None or str(data[field]).strip() == '':
            missing_fields.append(field)
    
    if missing_fields:
        raise ValidationError(f"Missing required fields: {', '.join(missing_fields)}")

def validate_field_length(data: Dict[str, Any], field_limits: Dict[str, int]) -> None:
    """
    필드 길이 검증
    
    Args:
        data: 검증할 데이터
        field_limits: 필드별 최대 길이 제한
    
    Raises:
        ValidationError: 필드 길이가 초과된 경우
    """
    for field, max_length in field_limits.items():
        if field in data and data[field] is not None:
            value = str(data[field])
            if len(value) > max_length:
                raise ValidationError(
                    f"Field '{field}' exceeds maximum length of {max_length} characters",
                    field
                )

def validate_pagination_params(page: Union[str, int], limit: Union[str, int]) -> tuple:
    """
    페이지네이션 파라미터 검증
    
    Args:
        page: 페이지 번호
        limit: 페이지당 항목 수
    
    Returns:
        (validated_page, validated_limit) 튜플
    
    Raises:
        ValidationError: 파라미터가 유효하지 않은 경우
    """
    try:
        page_int = int(page) if page else 1
        limit_int = int(limit) if limit else 10
        
        if page_int < 1:
            raise ValidationError("Page must be greater than 0")
        
        if limit_int < 1:
            raise ValidationError("Limit must be greater than 0")
        
        if limit_int > 50:
            limit_int = 50  # 최대 50개로 제한
        
        return page_int, limit_int
        
    except ValueError:
        raise ValidationError("Page and limit must be valid integers")

def safe_execute(func, *args, **kwargs):
    """
    안전한 함수 실행 (에러 핸들링 포함)
    
    Args:
        func: 실행할 함수
        *args: 함수 인자
        **kwargs: 함수 키워드 인자
    
    Returns:
        (success: bool, result: Any, error: Exception or None)
    """
    try:
        result = func(*args, **kwargs)
        return True, result, None
    except Exception as e:
        return False, None, e

class ErrorContext:
    """에러 컨텍스트 관리"""
    
    def __init__(self, operation: str, resource: str = None, request_id: str = None):
        self.operation = operation
        self.resource = resource
        self.request_id = request_id
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            context = {
                'operation': self.operation,
                'resource': self.resource
            }
            log_error(logger, exc_val, context, self.request_id)
        return False  # 에러를 다시 발생시킴
