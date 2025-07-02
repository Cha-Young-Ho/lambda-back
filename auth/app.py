import json
import os
from datetime import datetime, timedelta

# Lambda Layer에서 공통 모듈 임포트 (Layer 사용 시)
# 로컬 개발 시에는 fallback으로 로컬 클래스 사용
try:
    from common.config import AppConfig
    from common.response import create_response, create_error_response, create_success_response
    print("Using Lambda Layer modules")
except ImportError:
    print("Lambda Layer not available, using local implementations")
    
    class AppConfig:
        """애플리케이션 설정 관리 클래스"""
        def __init__(self, stage='local'):
            self.stage = stage
            self.config = self._load_config()
        
        def _load_config(self):
            """stage에 따른 설정 로드"""
            try:
                import boto3
                
                # AWS Lambda 환경 감지
                is_lambda = os.environ.get('AWS_LAMBDA_FUNCTION_NAME') is not None
                is_local_sam = os.environ.get('AWS_SAM_LOCAL') is not None
                
                # 로컬 환경에서는 env.json 사용
                if not is_lambda and (is_local_sam or os.path.exists('env.json')):
                    try:
                        with open('env.json', 'r') as f:
                            env_config = json.load(f)
                            local_config = env_config.get('local', {})
                            return {
                                'admin': local_config.get('admin', {
                                    'username': 'admin',
                                    'password': 'local_password'
                                }),
                                'jwt_secret': local_config.get('jwt_secret', 'your-secret-key')
                            }
                    except Exception as e:
                        print(f"Error reading env.json: {str(e)}")
                        return self._get_default_config()
                
                # AWS Lambda 환경에서는 Secrets Manager 사용
                print(f"Loading config for stage: {self.stage}")
                client = boto3.client('secretsmanager')
                secret_name = f"blog/config/{self.stage}"
                
                print(f"Attempting to get secret: {secret_name}")
                response = client.get_secret_value(SecretId=secret_name)
                secret = json.loads(response['SecretString'])
                print(f"Successfully loaded secret for stage: {self.stage}")
                
                # admin 설정이 없는 경우 기본값 추가
                if 'admin' not in secret:
                    secret['admin'] = {
                        'username': 'admin',
                        'password': 'admin123'
                    }
                
                return secret
                
            except Exception as e:
                import traceback
                print(f"Error getting secret for stage {self.stage}: {str(e)}")
                print(f"Full traceback: {traceback.format_exc()}")
                return self._get_default_config()
        
        def _get_default_config(self):
            """기본 설정값 반환"""
            return {
                'admin': {
                    'username': 'admin',
                    'password': os.environ.get('ADMIN_PASSWORD', 'admin123')
                },
                'jwt_secret': os.environ.get('JWT_SECRET', 'your-secret-key')
            }
    
    def create_response(status_code, body, headers=None):
        """통합 Response 생성"""
        default_headers = {
            'Content-Type': 'application/json; charset=utf-8',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, OPTIONS, GET',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization'
        }
        
        if headers:
            default_headers.update(headers)
        
        return {
            'statusCode': status_code,
            'headers': default_headers,
            'body': json.dumps(body, ensure_ascii=False) if isinstance(body, (dict, list)) else body
        }
    
    def create_error_response(status_code, error_message, error_details=None):
        """에러 응답 생성"""
        error_body = {
            'error': error_message,
            'status_code': status_code
        }
        
        if error_details:
            error_body['details'] = error_details
        
        return create_response(status_code, error_body)
    
    def create_success_response(data, message=None):
        """성공 응답 생성"""
        response_body = {
            'success': True,
            'data': data
        }
        
        if message:
            response_body['message'] = message
        
        return create_response(200, response_body)

# PyJWT가 없는 경우를 위한 간단한 토큰 생성
def create_simple_token(payload):
    """간단한 JWT 대체 토큰 생성"""
    import base64
    import hashlib
    
    # 간단한 토큰 형태로 생성 (실제 환경에서는 PyJWT 사용 권장)
    token_data = {
        'payload': payload,
        'secret': 'token-secret'  # 고정값 사용
    }
    
    token_string = json.dumps(token_data)
    encoded_token = base64.b64encode(token_string.encode()).decode()
    return encoded_token


def lambda_handler(event, context):
    """
    관리자 로그인 API
    POST /auth/login
    GET /auth/test
    """
    
    # stage 정보 추출
    stage = event.get('requestContext', {}).get('stage', 'local')
    
    # 설정 로드
    app_config = AppConfig(stage)
    
    try:
        # OPTIONS 요청 처리
        if event.get('httpMethod') == 'OPTIONS':
            return create_response(200, '')
        
        method = event.get('httpMethod')
        path = event.get('path', '')
        
        # 테스트 엔드포인트
        if method == 'GET' and path == '/auth/test':
            is_lambda = os.environ.get('AWS_LAMBDA_FUNCTION_NAME') is not None
            is_local_sam = os.environ.get('AWS_SAM_LOCAL') is not None
            
            env_info = {
                'message': 'Auth Test endpoint reached',
                'stage': stage,
                'config': app_config.config,
                'environment': {
                    'is_lambda': is_lambda,
                    'is_local_sam': is_local_sam,
                    'aws_lambda_function_name': os.environ.get('AWS_LAMBDA_FUNCTION_NAME'),
                    'aws_region': os.environ.get('AWS_REGION'),
                    'stage': os.environ.get('STAGE', 'unknown'),
                    'env_json_exists': os.path.exists('env.json'),
                    'determined_env': 'lambda' if is_lambda else 'sam_local' if is_local_sam else 'local'
                },
                'event_dump': event
            }
            
            return create_response(200, env_info)
        
        # 로그인 엔드포인트
        elif method == 'POST' and path == '/auth/login':
            return handle_login(event, app_config)
        
        else:
            return create_response(404, {'error': 'Not found'})
    
    except Exception as e:
        import traceback
        error_detail = {
            'error': 'Internal server error',
            'error_type': type(e).__name__,
            'error_message': str(e),
            'traceback': traceback.format_exc(),
            'stage': stage,
            'config_loaded': hasattr(app_config, 'config')
        }
        print(f"Error: {str(e)}")
        print(f"Full traceback: {traceback.format_exc()}")
        return create_response(500, error_detail)

def handle_login(event, app_config):
    """로그인 처리"""
    try:
        # 요청 본문 파싱
        try:
            body = json.loads(event.get('body', '{}'))
        except json.JSONDecodeError as e:
            error_detail = {
                'error': 'Invalid JSON',
                'error_type': 'JSONDecodeError',
                'error_message': str(e),
                'body_received': event.get('body', 'No body')
            }
            return create_response(400, error_detail)
        
        username = body.get('username')
        password = body.get('password')
        
        if not username or not password:
            return create_response(400, {'error': 'Username and password required'})
        
        # 설정에서 관리자 정보 가져오기
        admin_config = app_config.config.get('admin', {})
        
        admin_username = admin_config.get('username', 'admin')
        admin_password = admin_config.get('password', 'admin123')
        
        # 관리자 인증
        if username == admin_username and password == admin_password:
            # 간단한 토큰 생성 (PyJWT 대신)
            payload = {
                'username': username,
                'role': 'admin',
                'exp': (datetime.utcnow() + timedelta(hours=24)).isoformat(),
                'iat': datetime.utcnow().isoformat()
            }
            
            token = create_simple_token(payload)
            
            return create_response(200, {
                'message': 'Login successful',
                'token': token,
                'expiresIn': 86400  # 24시간 (초)
            })
        else:
            return create_response(401, {'error': 'Invalid credentials'})
    
    except Exception as e:
        import traceback
        error_detail = {
            'error': 'Error during login',
            'error_type': type(e).__name__,
            'error_message': str(e),
            'traceback': traceback.format_exc()
        }
        print(f"Error during login: {str(e)}")
        print(f"Full traceback: {traceback.format_exc()}")
        return create_response(500, error_detail)
