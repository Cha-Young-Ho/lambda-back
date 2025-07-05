"""
업계 표준 데코레이터 패턴 - 횡단 관심사 분리
"""
import json
from functools import wraps
from typing import Dict, Any, Callable

from .config import AppConfig
from .jwt_service import JWTService
from .response import create_error_response
from .exceptions import AuthenticationError, AuthorizationError
from .logging import get_logger

logger = get_logger(__name__)


def require_auth(required_role: str = None):
    """
    인증이 필요한 엔드포인트를 위한 데코레이터
    
    Args:
        required_role: 필요한 권한 (예: 'admin')
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(event: Dict[str, Any], *args, **kwargs) -> Dict[str, Any]:
            try:
                # Authorization 헤더 검증
                headers = event.get('headers', {})
                auth_header = headers.get('Authorization') or headers.get('authorization', '')
                
                if not auth_header:
                    logger.warning("Missing authorization header")
                    return create_error_response(
                        message="Authorization header is required",
                        status_code=401
                    )
                
                # JWT 토큰 검증
                config = AppConfig()
                jwt_service = JWTService(secret_key=config.get_jwt_secret())
                
                token_payload = jwt_service.verify_token(auth_header)
                
                # 권한 확인
                if required_role:
                    user_role = token_payload.get('role')
                    if user_role != required_role:
                        logger.warning(f"Insufficient permissions. Required: {required_role}, Got: {user_role}")
                        return create_error_response(
                            message="Insufficient permissions",
                            status_code=403
                        )
                
                # 사용자 정보를 이벤트에 추가
                event['user'] = token_payload
                
                # 원래 함수 실행
                return func(event, *args, **kwargs)
                
            except AuthenticationError as e:
                logger.warning(f"Authentication failed: {e.message}")
                return create_error_response(
                    message=e.message,
                    status_code=e.status_code
                )
            except Exception as e:
                logger.error(f"Auth decorator error: {str(e)}")
                return create_error_response(
                    message="Authentication error",
                    status_code=500
                )
        
        return wrapper
    return decorator


def cors_enabled(func: Callable) -> Callable:
    """CORS 지원 데코레이터"""
    @wraps(func)
    def wrapper(event: Dict[str, Any], *args, **kwargs) -> Dict[str, Any]:
        # OPTIONS 요청 처리
        if event.get('httpMethod') == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS',
                    'Access-Control-Allow-Headers': 'Content-Type,Authorization'
                },
                'body': ''
            }
        
        # 일반 요청 처리
        response = func(event, *args, **kwargs)
        
        # CORS 헤더 추가
        if 'headers' not in response:
            response['headers'] = {}
        
        response['headers'].update({
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type,Authorization'
        })
        
        return response
    
    return wrapper


def validate_request_body(required_fields: list = None):
    """요청 본문 검증 데코레이터"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(event: Dict[str, Any], *args, **kwargs) -> Dict[str, Any]:
            try:
                # JSON 파싱
                body = event.get('body', '{}')
                if isinstance(body, str):
                    body = json.loads(body)
                
                event['parsed_body'] = body
                
                # 필수 필드 검증
                if required_fields:
                    missing_fields = []
                    for field in required_fields:
                        if field not in body or not body[field]:
                            missing_fields.append(field)
                    
                    if missing_fields:
                        return create_error_response(
                            message=f"Missing required fields: {', '.join(missing_fields)}",
                            status_code=400
                        )
                
                return func(event, *args, **kwargs)
                
            except json.JSONDecodeError:
                return create_error_response(
                    message="Invalid JSON format",
                    status_code=400
                )
            except Exception as e:
                logger.error(f"Request validation error: {str(e)}")
                return create_error_response(
                    message="Request validation failed",
                    status_code=400
                )
        
        return wrapper
    return decorator


def rate_limit(requests_per_minute: int = 60):
    """간단한 Rate Limiting 데코레이터 (메모리 기반)"""
    request_counts = {}
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(event: Dict[str, Any], *args, **kwargs) -> Dict[str, Any]:
            import time
            
            # 클라이언트 IP 추출
            client_ip = event.get('requestContext', {}).get('identity', {}).get('sourceIp', 'unknown')
            current_time = int(time.time() / 60)  # 분 단위
            
            # 요청 카운트 초기화
            if client_ip not in request_counts:
                request_counts[client_ip] = {}
            
            # 이전 분의 데이터 정리
            request_counts[client_ip] = {
                minute: count for minute, count in request_counts[client_ip].items()
                if minute >= current_time - 1
            }
            
            # 현재 분의 요청 수 증가
            request_counts[client_ip][current_time] = request_counts[client_ip].get(current_time, 0) + 1
            
            # Rate limit 확인
            total_requests = sum(request_counts[client_ip].values())
            if total_requests > requests_per_minute:
                logger.warning(f"Rate limit exceeded for IP: {client_ip}")
                return create_error_response(
                    message="Rate limit exceeded. Please try again later.",
                    status_code=429
                )
            
            return func(event, *args, **kwargs)
        
        return wrapper
    return decorator


def admin_required(func: Callable) -> Callable:
    """관리자 권한이 필요한 엔드포인트를 위한 데코레이터"""
    return require_auth('admin')(func)
