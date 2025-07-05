"""
Auth API - 실용적인 업계 표준 패턴
- 클린 아키텍처
- 서비스 레이어
- 표준화된 에러 처리
- JWT 토큰 관리
"""
import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from common.config import AppConfig
from common.response import (
    create_response, create_error_response, create_success_response,
    create_created_response
)
from common.logging import get_logger, log_api_call

logger = get_logger(__name__)

class AuthService:
    """인증 비즈니스 로직 서비스"""
    
    def __init__(self, app_config):
        self.app_config = app_config
    
    def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """사용자 인증"""
        if not username or not password:
            raise ValueError("Username and password are required")
        
        # 관리자 정보 가져오기
        admin_config = self.app_config.get_admin_config()
        admin_username = admin_config.get('username', 'admin')
        admin_password = admin_config.get('password', 'admin123')
        
        # 인증 확인
        if username == admin_username and password == admin_password:
            return {
                'username': username,
                'role': 'admin',
                'authenticated': True
            }
        
        return None
    
    def create_token(self, user_info: Dict[str, Any]) -> str:
        """JWT 토큰 생성 (간단한 구현)"""
        # 실제 운영에서는 PyJWT 라이브러리 사용 권장
        payload = {
            'username': user_info['username'],
            'role': user_info['role'],
            'exp': (datetime.utcnow() + timedelta(hours=24)).isoformat(),
            'iat': datetime.utcnow().isoformat()
        }
        
        # 간단한 토큰 인코딩 (실제로는 JWT 라이브러리 사용)
        import base64
        token_data = json.dumps(payload)
        encoded_token = base64.b64encode(token_data.encode()).decode()
        return f"Bearer.{encoded_token}"
    
    def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """JWT 토큰 검증"""
        try:
            if not token.startswith('Bearer.'):
                return None
            
            import base64
            encoded_token = token.replace('Bearer.', '')
            token_data = base64.b64decode(encoded_token.encode()).decode()
            payload = json.loads(token_data)
            
            # 만료 시간 확인
            exp_time = datetime.fromisoformat(payload['exp'])
            if datetime.utcnow() > exp_time:
                return None
            
            return payload
            
        except Exception as e:
            logger.error(f"Token validation error: {str(e)}")
            return None

# 글로벌 인스턴스
app_config = AppConfig()
auth_service = AuthService(app_config)

def handle_login(event):
    """로그인 처리"""
    try:
        # 요청 본문 파싱
        body = json.loads(event.get('body', '{}'))
        username = body.get('username', '').strip()
        password = body.get('password', '').strip()
        
        # 입력 값 검증
        if not username or not password:
            return create_error_response(
                message="Username and password are required",
                status_code=400
            )
        
        # 사용자 인증
        user_info = auth_service.authenticate_user(username, password)
        if not user_info:
            return create_error_response(
                message="Invalid username or password",
                status_code=401
            )
        
        # JWT 토큰 생성
        token = auth_service.create_token(user_info)
        
        response_data = {
            'user': user_info,
            'token': token,
            'expires_in': 86400  # 24시간
        }
        
        return create_success_response(
            data=response_data,
            message="Login successful"
        )
        
    except ValueError as e:
        logger.warning(f"Login validation error: {str(e)}")
        return create_error_response(message=str(e), status_code=400)
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return create_error_response(
            message="Internal server error during login",
            status_code=500
        )

def handle_validate(event):
    """토큰 검증"""
    try:
        # Authorization 헤더에서 토큰 추출
        headers = event.get('headers', {})
        auth_header = headers.get('Authorization') or headers.get('authorization', '')
        
        if not auth_header:
            return create_error_response(
                message="Authorization header is required",
                status_code=401
            )
        
        # 토큰 검증
        token_payload = auth_service.validate_token(auth_header)
        if not token_payload:
            return create_error_response(
                message="Invalid or expired token",
                status_code=401
            )
        
        return create_success_response(
            data=token_payload,
            message="Token is valid"
        )
        
    except Exception as e:
        logger.error(f"Token validation error: {str(e)}")
        return create_error_response(
            message="Internal server error during token validation",
            status_code=500
        )

def lambda_handler(event, context):
    """메인 Lambda 핸들러"""
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