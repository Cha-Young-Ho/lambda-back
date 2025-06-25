import json
import os
from datetime import datetime, timedelta

# PyJWT가 없는 경우를 위한 간단한 토큰 생성
def create_simple_token(payload):
    """간단한 JWT 대체 토큰 생성"""
    import base64
    import hashlib
    
    # 간단한 토큰 형태로 생성 (실제 환경에서는 PyJWT 사용 권장)
    token_data = {
        'payload': payload,
        'secret': os.environ.get('JWT_SECRET', 'your-secret-key')
    }
    
    token_string = json.dumps(token_data)
    encoded_token = base64.b64encode(token_string.encode()).decode()
    return encoded_token

def get_secret():
    """AWS Secrets Manager에서 설정 가져오기"""
    try:
        # Stage별 Secret 이름 설정
        stage = os.environ.get('STAGE', 'local')
        
        if stage == 'local':
            # 로컬 환경에서는 env.json 파일에서 읽기
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
                # env.json 읽기 실패시 환경변수 사용
                return {
                    'admin': {
                        'username': 'admin',
                        'password': 'local_password'
                    },
                    'jwt_secret': os.environ.get('JWT_SECRET', 'your-secret-key')
                }
        
        # AWS 환경에서는 Secrets Manager 사용
        import boto3
        client = boto3.client('secretsmanager')
        secret_name = f"blog/{stage}/config"
        
        response = client.get_secret_value(SecretId=secret_name)
        secret = json.loads(response['SecretString'])
        return secret
        
    except Exception as e:
        print(f"Error getting secret for stage {stage}: {str(e)}")
        # Secret이 없는 경우 기본값 사용
        return {
            'admin': {
                'username': 'admin',
                'password': 'local_password'
            },
            'jwt_secret': 'your-secret-key'
        }

def lambda_handler(event, context):
    """
    관리자 로그인 API
    POST /auth/login
    """
    
    # CORS 헤더
    headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization'
    }
    
    try:
        # OPTIONS 요청 처리
        if event.get('httpMethod') == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': headers,
                'body': ''
            }
        
        # POST 요청만 허용
        if event.get('httpMethod') != 'POST':
            return {
                'statusCode': 405,
                'headers': headers,
                'body': json.dumps({'error': 'Method not allowed'})
            }
        
        # 요청 본문 파싱
        try:
            body = json.loads(event.get('body', '{}'))
        except json.JSONDecodeError:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'Invalid JSON'})
            }
        
        username = body.get('username')
        password = body.get('password')
        
        if not username or not password:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'Username and password required'})
            }
        
        # Secrets Manager에서 관리자 설정 가져오기
        config = get_secret()
        admin_config = config.get('admin', {})
        
        admin_username = admin_config.get('username', 'admin')
        admin_password = admin_config.get('password', 'admin123')
        jwt_secret = config.get('jwt_secret', os.environ.get('JWT_SECRET', 'your-secret-key'))
        
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
            
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({
                    'message': 'Login successful',
                    'token': token,
                    'expiresIn': 86400  # 24시간 (초)
                })
            }
        else:
            return {
                'statusCode': 401,
                'headers': headers,
                'body': json.dumps({'error': 'Invalid credentials'})
            }
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': 'Internal server error'})
        }
