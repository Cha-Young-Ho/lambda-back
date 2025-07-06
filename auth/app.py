"""
Auth API - Standardized Lambda Handler
표준화된 인증 API 핸들러
- 베이스 핸들러 사용
- JWT 토큰 관리
- 표준화된 에러 처리
"""
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import os

from common.config import AppConfig
from common.response import (
    create_response, create_error_response, create_success_response
)
from common.logging import get_logger, performance_monitor
from common.jwt_service import JWTService
from common.error_handlers import (
    ValidationError, UnauthorizedError, validate_required_fields
)

logger = get_logger(__name__)

class AuthService:
    """인증 비즈니스 로직 서비스"""
    
    def __init__(self, app_config):
        self.app_config = app_config
        self.jwt_service = JWTService(app_config)
    
    @performance_monitor('auth_login')
    def authenticate_user(self, username: str, password: str) -> Dict[str, Any]:
        """사용자 인증 및 토큰 생성"""
        # 입력 검증
        if not username or not username.strip():
            raise ValidationError("Username is required")
        
        if not password or not password.strip():
            raise ValidationError("Password is required")
        
        # 관리자 정보 가져오기
        admin_config = self.app_config.get_admin_config()
        admin_username = admin_config.get('username', 'admin')
        admin_password = admin_config.get('password', 'admin123')
        
        # 인증 확인
        if username.strip() != admin_username or password != admin_password:
            raise UnauthorizedError("Invalid username or password")
        
        # 사용자 정보
        user_info = {
            'username': username.strip(),
            'role': 'admin',
            'authenticated': True
        }
        
        # JWT 토큰 생성
        token = self.jwt_service.create_token(user_info)
        
        return {
            'user': user_info,
            'token': token,
            'expires_in': 3600,  # 1시간
            'token_type': 'Bearer'
        }
    
    @performance_monitor('auth_validate')
    def validate_token(self, token: str) -> Dict[str, Any]:
        """토큰 검증"""
        if not token or not token.strip():
            raise ValidationError("Token is required")
        
        try:
            # Bearer 접두사 제거
            if token.startswith('Bearer '):
                token = token[7:]
            
            # 토큰 검증
            payload = self.jwt_service.verify_token(token)
            
            return {
                'valid': True,
                'user': {
                    'username': payload.get('username'),
                    'role': payload.get('role'),
                    'authenticated': True
                },
                'expires_at': payload.get('exp')
            }
            
        except Exception as e:
            raise UnauthorizedError("Invalid or expired token")

class AuthAPIHandler:
    """인증 API 핸들러"""
    
    def __init__(self):
        stage = os.environ.get('STAGE', 'local')
        self.app_config = AppConfig(stage)
        self.service = AuthService(self.app_config)
        self.cold_start = True
    
    def lambda_handler(self, event: Dict[str, Any], context: Any) -> Dict[str, Any]:
        """Lambda 핸들러"""
        request_id = getattr(context, 'aws_request_id', 'local')
        
        try:
            # 콜드 스타트 로깅
            if self.cold_start:
                logger.info("Cold start for AuthAPIHandler", 
                          extra={'cold_start': True, 'request_id': request_id})
                self.cold_start = False
            
            # 라우팅
            path = event.get('path', '')
            method = event.get('httpMethod', '').upper()
            
            # CORS 처리
            if method == 'OPTIONS':
                return self._handle_options()
            
            # 경로별 라우팅
            if '/login' in path:
                return self._handle_login(event)
            elif '/validate' in path:
                return self._handle_validate(event)
            elif '/test' in path:
                return self._handle_test()
            else:
                return create_error_response("Not found", 404)
            
        except Exception as e:
            from common.error_handlers import handle_api_error
            return handle_api_error(e, request_id)
    
    def _handle_options(self) -> Dict[str, Any]:
        """CORS OPTIONS 요청 처리"""
        return create_response(
            {},
            200,
            {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type, Authorization'
            }
        )
    
    def _handle_login(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """로그인 처리"""
        if event.get('httpMethod') != 'POST':
            return create_error_response("Method not allowed", 405)
        
        # 요청 본문 파싱
        body = event.get('body', '{}')
        if isinstance(body, str):
            data = json.loads(body) if body else {}
        else:
            data = body
        
        # 요청 값 로깅 (비밀번호 제외)
        logger.info(f"Login attempt: username={data.get('username')}")
        
        # 시크릿 키 목록 로깅
        try:
            secret_dict = self.service.app_config.config
            logger.info(f"Loaded secret keys: {list(secret_dict.keys())}")
        except Exception as e:
            logger.warning(f"Secret keys logging failed: {e}")
        
        # 필수 필드 검증
        validate_required_fields(data, ['username', 'password'])
        
        # 인증 처리
        result = self.service.authenticate_user(
            data['username'], 
            data['password']
        )
        
        return create_success_response(result)
    
    def _handle_validate(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """토큰 검증 처리"""
        if event.get('httpMethod') != 'POST':
            return create_error_response("Method not allowed", 405)
        
        # 헤더에서 토큰 추출
        headers = event.get('headers', {})
        auth_header = headers.get('Authorization', '')
        
        if not auth_header:
            # 요청 본문에서 토큰 추출
            body = event.get('body', '{}')
            if isinstance(body, str):
                data = json.loads(body) if body else {}
            else:
                data = body
            
            token = data.get('token', '')
        else:
            token = auth_header
        
        # 토큰 검증
        result = self.service.validate_token(token)
        return create_success_response(result)
    
    def _handle_test(self) -> Dict[str, Any]:
        """테스트 엔드포인트"""
        return create_success_response({
            'message': 'Auth API is working',
            'timestamp': datetime.now(timezone.utc).isoformat() + 'Z',
            'service': 'auth'
        })

# Lambda 핸들러 인스턴스
handler = AuthAPIHandler()

def lambda_handler(event, context):
    """Lambda 엔트리 포인트"""
    return handler.lambda_handler(event, context)
