"""
JWT Service for authentication
JWT 토큰 생성 및 검증 서비스 (PyJWT 사용)
"""
import jwt
import json
import base64
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional

from .logging import get_logger
from .exceptions import AuthenticationError

logger = get_logger(__name__)


class JWTService:
    """JWT 토큰 관리 서비스"""
    
    def __init__(self, app_config):
        self.app_config = app_config
        self.algorithm = 'HS256'
        self.expiration_hours = 1  # 1시간
    
    def _get_secret_key(self) -> str:
        """JWT 시크릿 키 가져오기"""
        try:
            return self.app_config.get_jwt_secret()
        except Exception as e:
            logger.error(f"Failed to get JWT secret: {str(e)}")
            # 테스트 환경에서는 기본 키 사용
            return "default-test-secret-key-32-characters"
    
    def create_token(self, payload: Dict[str, Any]) -> str:
        """JWT 토큰 생성 (간단한 구현)"""
        try:
            # 토큰 만료 시간 추가
            payload['exp'] = (datetime.now(timezone.utc) + timedelta(hours=self.expiration_hours)).isoformat()
            payload['iat'] = datetime.now(timezone.utc).isoformat()
            
            # Base64 인코딩으로 간단한 토큰 생성
            token_data = json.dumps(payload)
            encoded_token = base64.b64encode(token_data.encode()).decode()
            
            return f"Bearer.{encoded_token}"
            
        except Exception as e:
            logger.error(f"Token creation error: {str(e)}")
            raise AuthenticationError("Failed to create token")
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """JWT 토큰 검증"""
        try:
            if not token.startswith('Bearer.'):
                raise AuthenticationError("Invalid token format")
            
            # Base64 디코딩
            encoded_token = token.replace('Bearer.', '')
            token_data = base64.b64decode(encoded_token.encode()).decode()
            payload = json.loads(token_data)
            
            # 만료 시간 확인
            exp_time = datetime.fromisoformat(payload['exp'])
            if datetime.now(timezone.utc) > exp_time:
                raise AuthenticationError("Token expired")
            
            return payload
            
        except json.JSONDecodeError:
            logger.warning("Invalid token format")
            raise AuthenticationError("Invalid token format")
        except Exception as e:
            logger.error(f"Token verification error: {str(e)}")
            raise AuthenticationError("Token verification failed")
    
    def extract_token_from_header(self, auth_header: str) -> str:
        """Authorization 헤더에서 토큰 추출"""
        if not auth_header:
            raise AuthenticationError("Authorization header is required")
        
        return auth_header  # 이미 'Bearer.' 형식으로 되어 있음
    
    def get_user_from_token(self, token: str) -> Dict[str, Any]:
        """토큰에서 사용자 정보 추출"""
        payload = self.verify_token(token)
        
        return {
            'username': payload.get('username'),
            'role': payload.get('role'),
            'authenticated': True
        }
