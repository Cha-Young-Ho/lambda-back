"""
애플리케이션 설정 관리 클래스
Stage별 설정을 관리하며, Secret Manager와 로컬 환경을 모두 지원합니다.
"""
import json
import os


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
                            'jwt_secret': local_config.get('jwt_secret', 'your-secret-key'),
                            'admin': local_config.get('admin', {
                                'username': 'admin',
                                'password': 'local_password'
                            }),
                            'dynamodb': {
                                'region': local_config.get('dynamodb_region', 'ap-northeast-2'),
                                'table_name': local_config.get('table_name', 'blog-table'),
                                'endpoint_url': 'http://host.docker.internal:8000'
                            }
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
            
            # 누락된 설정에 대한 기본값 추가
            if 'admin' not in secret:
                secret['admin'] = {
                    'username': 'admin',
                    'password': 'admin123'
                }
            
            if 'dynamodb' not in secret:
                secret['dynamodb'] = {
                    'region': secret.get('dynamodb_region', 'ap-northeast-2'),
                    'table_name': secret.get('table_name', 'blog-table-dev')
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
            'jwt_secret': os.environ.get('JWT_SECRET', 'your-secret-key'),
            'admin': {
                'username': 'admin',
                'password': os.environ.get('ADMIN_PASSWORD', 'admin123')
            },
            'dynamodb': {
                'region': os.environ.get('AWS_REGION', 'ap-northeast-2'),
                'table_name': os.environ.get('TABLE_NAME', 'blog-table-dev'),
                'endpoint_url': 'http://host.docker.internal:8000'
            }
        }
    
    def get_jwt_secret(self):
        """JWT Secret 반환"""
        return self.config.get('jwt_secret', 'your-secret-key')
    
    def get_admin_config(self):
        """Admin 설정 반환"""
        return self.config.get('admin', {
            'username': 'admin',
            'password': 'admin123'
        })
    
    def get_dynamodb_config(self):
        """DynamoDB 설정 반환"""
        return self.config.get('dynamodb', {
            'region': 'ap-northeast-2',
            'table_name': 'blog-table-dev'
        })
