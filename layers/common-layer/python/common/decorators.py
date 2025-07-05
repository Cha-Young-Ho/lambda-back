"""
Lambda function decorators for common functionality
실제 업계에서 사용하는 패턴을 적용한 데코레이터 모음
"""
import json
import functools
import traceback
from datetime import datetime
from typing import Dict, Any, Callable, List, Optional

from .response import create_response, create_error_response
from .config import AppConfig
from .logging import get_logger

logger = get_logger(__name__)

def lambda_handler(cors_enabled=True, require_auth=False):
    """
    Lambda 핸들러 데코레이터
    - CORS 처리
    - 에러 핸들링
    - 로깅
    - 설정 주입
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
            # 요청 시작 시간 기록
            start_time = datetime.utcnow()
            request_id = context.aws_request_id if hasattr(context, 'aws_request_id') else 'local'
            
            logger.info(f"Request started - ID: {request_id}")
            
            try:
                # CORS OPTIONS 처리
                if cors_enabled and event.get('httpMethod') == 'OPTIONS':
                    return create_response(200, '', cors=True)
                
                # Stage 정보 추출 및 설정 로드
                stage = event.get('requestContext', {}).get('stage', 'local')
                app_config = AppConfig(stage)
                
                # 인증 확인 (필요한 경우)
                if require_auth:
                    auth_result = _check_authentication(event, app_config)
                    if auth_result:
                        return auth_result
                
                # 메인 핸들러 실행
                result = func(event, context, app_config)
                
                # 실행 시간 로깅
                duration = (datetime.utcnow() - start_time).total_seconds()
                logger.info(f"Request completed - ID: {request_id}, Duration: {duration:.3f}s")
                
                return result
                
            except Exception as e:
                # 실행 시간 로깅 (에러 케이스)
                duration = (datetime.utcnow() - start_time).total_seconds()
                logger.error(f"Request failed - ID: {request_id}, Duration: {duration:.3f}s, Error: {str(e)}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                
                return create_error_response(
                    500, 
                    "Internal server error",
                    {
                        'request_id': request_id,
                        'error_type': type(e).__name__,
                        'error_message': str(e),
                        'duration': duration
                    }
                )
        
        return wrapper
    return decorator

def route_handler(routes: Dict[str, Dict[str, Callable]]):
    """
    라우팅 데코레이터
    업계 표준 라우팅 패턴 적용
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(event: Dict[str, Any], context: Any, app_config: AppConfig) -> Dict[str, Any]:
            method = event.get('httpMethod', '').upper()
            path = event.get('path', '')
            path_parameters = event.get('pathParameters') or {}
            
            # 라우팅 매칭
            for route_pattern, methods in routes.items():
                if _match_route(path, route_pattern, path_parameters):
                    if method in methods:
                        handler = methods[method]
                        return handler(event, context, app_config)
            
            # 매칭되는 라우트가 없을 경우
            logger.warning(f"Route not found: {method} {path}")
            return create_error_response(404, f"Route not found: {method} {path}")
        
        return wrapper
    return decorator

def validate_json_body(schema: Optional[Dict] = None):
    """
    JSON 바디 검증 데코레이터
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(event: Dict[str, Any], context: Any, app_config: AppConfig) -> Dict[str, Any]:
            try:
                # JSON 파싱
                body_str = event.get('body', '{}')
                if body_str:
                    body = json.loads(body_str)
                    event['parsed_body'] = body
                else:
                    event['parsed_body'] = {}
                
                # 스키마 검증 (선택사항)
                if schema:
                    validation_errors = _validate_schema(event['parsed_body'], schema)
                    if validation_errors:
                        return create_error_response(400, "Validation error", validation_errors)
                
                return func(event, context, app_config)
                
            except json.JSONDecodeError as e:
                logger.warning(f"Invalid JSON body: {str(e)}")
                return create_error_response(400, "Invalid JSON format", {'error': str(e)})
        
        return wrapper
    return decorator

def require_fields(fields: List[str]):
    """
    필수 필드 검증 데코레이터
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(event: Dict[str, Any], context: Any, app_config: AppConfig) -> Dict[str, Any]:
            body = event.get('parsed_body', {})
            missing_fields = [field for field in fields if not body.get(field)]
            
            if missing_fields:
                return create_error_response(
                    400, 
                    "Missing required fields", 
                    {'missing_fields': missing_fields}
                )
            
            return func(event, context, app_config)
        
        return wrapper
    return decorator

def validate_category(content_type: str):
    """
    카테고리 검증 데코레이터
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(event: Dict[str, Any], context: Any, app_config: AppConfig) -> Dict[str, Any]:
            body = event.get('parsed_body', {})
            category = body.get('category', '')
            
            if category:  # 카테고리가 제공된 경우에만 검증
                from .categories import get_allowed_categories, validate_category_value
                
                allowed_categories = get_allowed_categories(content_type)
                if not validate_category_value(content_type, category):
                    return create_error_response(
                        400, 
                        f"Invalid category for {content_type}",
                        {
                            'provided_category': category,
                            'allowed_categories': allowed_categories
                        }
                    )
            
            return func(event, context, app_config)
        
        return wrapper
    return decorator

# Helper functions
def _check_authentication(event: Dict[str, Any], app_config: AppConfig) -> Optional[Dict[str, Any]]:
    """인증 확인 (JWT 토큰 검증)"""
    # 실제 JWT 검증 로직 구현
    # 현재는 간단하게 Authorization 헤더 존재 여부만 확인
    headers = event.get('headers', {})
    auth_header = headers.get('Authorization') or headers.get('authorization')
    
    if not auth_header or not auth_header.startswith('Bearer '):
        return create_error_response(401, "Authentication required", {'error': 'Missing or invalid Authorization header'})
    
    # JWT 토큰 검증 로직 (실제 구현 필요)
    return None

def _match_route(path: str, pattern: str, path_params: Dict[str, str]) -> bool:
    """라우트 패턴 매칭"""
    # 단순한 패턴 매칭 구현
    if pattern == path:
        return True
    
    # 파라미터가 있는 패턴 처리 (예: /news/{newsId})
    pattern_parts = pattern.split('/')
    path_parts = path.split('/')
    
    if len(pattern_parts) != len(path_parts):
        return False
    
    for pattern_part, path_part in zip(pattern_parts, path_parts):
        if pattern_part.startswith('{') and pattern_part.endswith('}'):
            # 파라미터 부분은 매칭으로 간주
            continue
        elif pattern_part != path_part:
            return False
    
    return True

def _validate_schema(data: Dict[str, Any], schema: Dict[str, Any]) -> List[str]:
    """간단한 스키마 검증"""
    errors = []
    
    # 필수 필드 검증
    required_fields = schema.get('required', [])
    for field in required_fields:
        if field not in data:
            errors.append(f"Missing required field: {field}")
    
    # 타입 검증
    field_types = schema.get('types', {})
    for field, expected_type in field_types.items():
        if field in data:
            if expected_type == 'string' and not isinstance(data[field], str):
                errors.append(f"Field '{field}' must be a string")
            elif expected_type == 'number' and not isinstance(data[field], (int, float)):
                errors.append(f"Field '{field}' must be a number")
            elif expected_type == 'boolean' and not isinstance(data[field], bool):
                errors.append(f"Field '{field}' must be a boolean")
    
    return errors
