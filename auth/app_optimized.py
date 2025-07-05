"""
Auth API - 업계 표준 패턴
- Clean Architecture
- Service Layer Pattern
- Dependency Injection
- Exception Handling
- JWT Token Management
"""
import json
from typing import Dict, Any

from common.config import AppConfig
from common.response import create_response, create_error_response, create_success_response
from common.logging import get_logger, log_api_call
from common.exceptions import ValidationError, AuthenticationError, BlogException
from common.jwt_service import JWTService
from common.utils import validate_required_fields, sanitize_string

logger = get_logger(__name__)


class AuthService:
    """인증 비즈니스 로직 서비스 - DI 패턴"""
    
    def __init__(self, config: AppConfig, jwt_service: JWTService):
        self.config = config
        self.jwt_service = jwt_service
    
    def authenticate_user(self, username: str, password: str) -> Dict[str, Any]:
        """사용자 인증"""
        # 입력값 검증
        if not username or not password:
            raise ValidationError("Username and password are required")
        
        # 입력값 정리
        username = sanitize_string(username, max_length=50)
        password = sanitize_string(password, max_length=100)
        
        # 관리자 정보 가져오기
        admin_config = self.config.get_admin_config()
        admin_username = admin_config.get('username', 'admin')
        admin_password = admin_config.get('password', 'admin123')
        
        # 인증 확인
        if username == admin_username and password == admin_password:
            return {
                'username': username,
                'role': 'admin',
                'authenticated': True
            }
        
        raise AuthenticationError("Invalid username or password")
    
    def create_access_token(self, user_info: Dict[str, Any]) -> str:
        """액세스 토큰 생성"""
        payload = {
            'username': user_info['username'],
            'role': user_info['role'],
            'authenticated': user_info['authenticated']
        }
        return self.jwt_service.create_token(payload)
    
    def validate_token(self, auth_header: str) -> Dict[str, Any]:
        """토큰 검증"""
        if not auth_header:
            raise AuthenticationError("Authorization header is required")
        
        token = self.jwt_service.extract_token_from_header(auth_header)
        return self.jwt_service.verify_token(token)


# 글로벌 서비스 인스턴스 (DI 컨테이너 패턴)
def get_auth_service() -> AuthService:
    """AuthService 인스턴스 생성 (Factory Pattern)"""
    config = AppConfig()
    jwt_service = JWTService(
        secret_key=config.get_jwt_secret(),
        algorithm="HS256",
        expires_hours=24
    )
    return AuthService(config, jwt_service)


def handle_login(event: Dict[str, Any]) -> Dict[str, Any]:
    """로그인 처리"""
    try:
        # 요청 본문 파싱
        body = json.loads(event.get('body', '{}'))
        username = body.get('username', '').strip()
        password = body.get('password', '').strip()
        
        # 필수 필드 검증
        missing_fields = validate_required_fields(body, ['username', 'password'])
        if missing_fields:
            raise ValidationError(f"Missing required fields: {', '.join(missing_fields)}")
        
        # 인증 서비스 실행
        auth_service = get_auth_service()
        user_info = auth_service.authenticate_user(username, password)
        
        # JWT 토큰 생성
        access_token = auth_service.create_access_token(user_info)
        
        response_data = {
            'user': {
                'username': user_info['username'],
                'role': user_info['role']
            },
            'token': access_token,
            'expires_in': 86400  # 24시간
        }
        
        logger.info(f"User {username} logged in successfully")
        return create_success_response(
            data=response_data,
            message="Login successful"
        )
        
    except BlogException as e:
        logger.warning(f"Login failed: {e.message}")
        return create_error_response(
            message=e.message,
            status_code=e.status_code
        )
    except Exception as e:
        logger.error(f"Unexpected login error: {str(e)}")
        return create_error_response(
            message="Internal server error during login",
            status_code=500
        )


def handle_validate(event: Dict[str, Any]) -> Dict[str, Any]:
    """토큰 검증"""
    try:
        # Authorization 헤더에서 토큰 추출
        headers = event.get('headers', {})
        auth_header = headers.get('Authorization') or headers.get('authorization', '')
        
        # 토큰 검증
        auth_service = get_auth_service()
        token_payload = auth_service.validate_token(auth_header)
        
        logger.info(f"Token validated for user: {token_payload.get('username')}")
        return create_success_response(
            data=token_payload,
            message="Token is valid"
        )
        
    except BlogException as e:
        logger.warning(f"Token validation failed: {e.message}")
        return create_error_response(
            message=e.message,
            status_code=e.status_code
        )
    except Exception as e:
        logger.error(f"Unexpected token validation error: {str(e)}")
        return create_error_response(
            message="Internal server error during token validation",
            status_code=500
        )


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """메인 Lambda 핸들러 - 라우팅"""
    try:
        http_method = event.get('httpMethod')
        path = event.get('path', '')
        
        # API 호출 로깅
        log_api_call(logger, event, context)
        
        logger.info(f"Auth API Request: {http_method} {path}")
        
        # 라우팅
        if http_method == 'POST' and path == '/auth/login':
            return handle_login(event)
        elif http_method == 'POST' and path == '/auth/validate':
            return handle_validate(event)
        elif http_method == 'OPTIONS':
            # CORS preflight 요청 처리
            return create_response(200, '', cors=True)
        else:
            return create_error_response(
                message=f"Route not found: {http_method} {path}",
                status_code=404
            )
            
    except Exception as e:
        logger.error(f"Unexpected error in auth handler: {str(e)}")
        return create_error_response(
            message="Internal server error",
            status_code=500
        )
