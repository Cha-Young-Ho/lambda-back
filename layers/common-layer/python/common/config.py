"""
애플리케이션 설정 관리 클래스
Stage별 설정을 관리하며, Secret Manager와 로컬 환경을 모두 지원합니다.
"""
import json
import os


class AppConfig:
    """애플리케이션 설정 관리 클래스"""
    
    # 클래스 변수로 설정 캐싱 (성능 최적화)
    _cached_configs = {}
    
    def __init__(self, stage='local'):
        self.stage = stage
        
        # 캐시된 설정이 있으면 사용, 없으면 새로 로드
        if stage in AppConfig._cached_configs:
            print(f"Using cached config for stage: {stage}")
            self.config = AppConfig._cached_configs[stage]
        else:
            print(f"Loading new config for stage: {stage}")
            self.config = self._load_config()
            AppConfig._cached_configs[stage] = self.config
    
    def _load_config(self):
        """stage에 따른 설정 로드"""
        # AWS Lambda 환경 감지
        is_lambda = os.environ.get('AWS_LAMBDA_FUNCTION_NAME') is not None
        is_local_sam = os.environ.get('AWS_SAM_LOCAL') is not None
        
        # 로컬 환경 (SAM Local 또는 env.json 존재)
        if not is_lambda or is_local_sam or os.path.exists('env.json'):
            print(f"Loading local config for stage: {self.stage}")
            try:
                with open('env.json', 'r') as f:
                    env_config = json.load(f)
                    local_config = env_config.get('local', {})
                    return {
                        'jwt_secret': local_config.get('jwt_secret', 'your-local-secret-key'),
                        'admin': local_config.get('admin', {
                            'username': 'admin',
                            'password': 'local_password'
                        }),
                        'dynamodb': {
                            'region': local_config.get('dynamodb_region', 'ap-northeast-2'),
                            'table_name': local_config.get('table_name', 'blog-table'),
                            'endpoint_url': local_config.get('dynamodb_endpoint', 'http://host.docker.internal:8000')
                        },
                        's3': (local_config['s3'] if isinstance(local_config.get('s3'), dict) else {
                            'bucket_name': local_config.get('s3_bucket_name', 'blog-uploads'),
                            'region': local_config.get('s3_region', 'ap-northeast-2')
                        })
                    }
            except Exception as e:
                print(f"Error reading env.json: {str(e)}")
                return self._get_default_config()
        
        # AWS 환경에서는 Secrets Manager 사용
        print(f"Loading AWS config for stage: {self.stage}")
        try:
            import boto3
            client = boto3.client('secretsmanager')
            secret_name = f"blog/config/{self.stage}"
            
            print(f"Getting secret: {secret_name}")
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
                    'table_name': secret.get('table_name', 'blog-table')
                }
            
            if 's3' not in secret:
                # s3가 없으면 최상위에 s3_bucket_name, s3_region이 있는지 확인 후, 없으면 기본값 사용
                s3_dict = secret.get('s3', {})
                bucket_name = s3_dict.get('bucket_name') or secret.get('s3_bucket_name', 'blog-uploads')
                region = s3_dict.get('region') or secret.get('s3_region', 'ap-northeast-2')
                secret['s3'] = {
                    'bucket_name': bucket_name,
                    'region': region
                }
            
            # Secrets Manager에서 불러온 전체 시크릿 값 로깅
            print(f"[AppConfig] Loaded secret from Secrets Manager: {json.dumps(secret, ensure_ascii=False)}")
            
            return secret
            
        except Exception as e:
            print(f"Failed to load from Secrets Manager: {str(e)}")
            print("Using fallback configuration")
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
                'table_name': os.environ.get('TABLE_NAME', 'blog-table'),
                'endpoint_url': 'http://host.docker.internal:8000'
            },
            's3': {
                'bucket_name': os.environ.get('S3_BUCKET_NAME', 'blog-uploads'),
                'region': os.environ.get('S3_REGION', 'ap-northeast-2')
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
            'table_name': 'blog-table'
        })
    
    def get_s3_config(self):
        """S3 설정 반환"""
        return self.config.get('s3', {
            'bucket_name': 'blog-uploads',
            'region': 'ap-northeast-2'
        })
    
    def get_config_value(self, key, default=None):
        """지정된 키의 설정값 반환"""
        keys = key.split('.')
        value = self.config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
