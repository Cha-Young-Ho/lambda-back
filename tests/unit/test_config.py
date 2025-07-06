"""
Unit tests for config module
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import os
import json

# Mark all tests in this file as unit tests
pytestmark = pytest.mark.unit

# Import the module under test
from common.config import AppConfig


class TestAppConfig:
    """Test AppConfig class"""
    
    @patch('builtins.open', side_effect=FileNotFoundError)
    def test_init_with_defaults(self, mock_open):
        """Test AppConfig initialization with default values"""
        # Clear cached configs for clean test
        AppConfig._cached_configs.clear()
        
        # Temporarily remove environment variables that might affect test
        temp_env = {}
        env_vars_to_remove = ['AWS_LAMBDA_FUNCTION_NAME', 'TABLE_NAME', 'STAGE']
        for var in env_vars_to_remove:
            if var in os.environ:
                temp_env[var] = os.environ.pop(var)
        
        try:
            config = AppConfig()
            
            dynamodb_config = config.get_dynamodb_config()
            jwt_secret = config.get_jwt_secret()
            admin_config = config.get_admin_config()
            
            assert dynamodb_config['table_name'] == 'blog-table'
            assert dynamodb_config['region'] == 'ap-northeast-2'
            assert jwt_secret is not None
            assert admin_config['username'] == 'admin'
        finally:
            # Restore the environment variables
            for var, value in temp_env.items():
                os.environ[var] = value
    
    @patch('builtins.open')
    def test_init_with_env_json(self, mock_open):
        """Test AppConfig initialization with env.json"""
        # Clear cached configs for clean test
        AppConfig._cached_configs.clear()
        
        # Temporarily remove AWS_LAMBDA_FUNCTION_NAME if it exists
        lambda_func_name = os.environ.pop('AWS_LAMBDA_FUNCTION_NAME', None)
        
        try:
            mock_env_data = {
                'local': {
                    'table_name': 'test-table',
                    'dynamodb_region': 'us-east-1',
                    'jwt_secret': 'test-secret',
                    'admin': {
                        'username': 'testuser',
                        'password': 'testpass'
                    }
                }
            }
            mock_file = mock_open.return_value.__enter__.return_value
            mock_file.read.return_value = json.dumps(mock_env_data)
            
            config = AppConfig()
            
            dynamodb_config = config.get_dynamodb_config()
            jwt_secret = config.get_jwt_secret()
            admin_config = config.get_admin_config()
            
            assert dynamodb_config['table_name'] == 'test-table'
            assert dynamodb_config['region'] == 'us-east-1'
            assert jwt_secret == 'test-secret'
            assert admin_config['username'] == 'testuser'
        finally:
            # Restore the environment variable if it existed
            if lambda_func_name is not None:
                os.environ['AWS_LAMBDA_FUNCTION_NAME'] = lambda_func_name
    
    def test_get_dynamodb_config(self):
        """Test get_dynamodb_config method"""
        # Clear cached configs for clean test
        AppConfig._cached_configs.clear()
        
        # Temporarily remove environment variables that might affect test
        temp_env = {}
        env_vars_to_remove = ['AWS_LAMBDA_FUNCTION_NAME', 'TABLE_NAME', 'STAGE']
        for var in env_vars_to_remove:
            if var in os.environ:
                temp_env[var] = os.environ.pop(var)
        
        try:
            config = AppConfig()
            
            db_config = config.get_dynamodb_config()
            
            assert 'table_name' in db_config
            assert 'region' in db_config
            assert db_config['table_name'] == 'blog-table'
            assert db_config['region'] == 'ap-northeast-2'
        finally:
            # Restore the environment variables
            for var, value in temp_env.items():
                os.environ[var] = value
    
    @patch.dict(os.environ, {'DYNAMODB_ENDPOINT': 'http://localhost:8000'})
    def test_get_dynamodb_config_with_endpoint(self):
        """Test get_dynamodb_config method with local endpoint"""
        # Clear cached configs for clean test
        AppConfig._cached_configs.clear()
        
        config = AppConfig()
        
        db_config = config.get_dynamodb_config()
        
        # Should have endpoint_url in config
        assert 'endpoint_url' in db_config or 'endpoint_url' in str(config.config)
    
    def test_get_jwt_secret(self):
        """Test get_jwt_secret method"""
        config = AppConfig()
        
        jwt_secret = config.get_jwt_secret()
        
        assert jwt_secret is not None
        assert isinstance(jwt_secret, str)
        assert len(jwt_secret) > 0
    
    def test_get_admin_config(self):
        """Test get_admin_config method"""
        config = AppConfig()
        
        admin_config = config.get_admin_config()
        
        assert 'username' in admin_config
        assert 'password' in admin_config
        assert admin_config['username'] == 'admin'
    
    @patch.dict(os.environ, {'AWS_LAMBDA_FUNCTION_NAME': 'test-function'})
    @patch('os.path.exists')
    @patch('boto3.client')
    def test_aws_environment_secrets_manager_success(self, mock_boto3_client, mock_exists):
        """AWS 환경에서 Secrets Manager로부터 설정 로드 성공 테스트"""
        AppConfig._cached_configs.clear()
        mock_exists.return_value = False  # env.json이 없다고 가정
        
        # Mock Secrets Manager client
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        
        mock_secret = {
            'jwt_secret': 'aws-secret-key',
            'admin': {
                'username': 'aws-admin',
                'password': 'aws-password'
            },
            'dynamodb': {
                'region': 'us-east-1',
                'table_name': 'aws-blog-table'
            },
            's3': {
                'bucket_name': 'aws-blog-uploads',
                'region': 'us-east-1'
            }
        }
        
        mock_client.get_secret_value.return_value = {
            'SecretString': json.dumps(mock_secret)
        }
        
        config = AppConfig('production')
        
        assert config.get_jwt_secret() == 'aws-secret-key'
        assert config.get_admin_config()['username'] == 'aws-admin'
        assert config.get_dynamodb_config()['table_name'] == 'aws-blog-table'
        assert config.get_s3_config()['bucket_name'] == 'aws-blog-uploads'


    @patch.dict(os.environ, {'AWS_LAMBDA_FUNCTION_NAME': 'test-function'}, clear=True)
    @patch('os.path.exists')
    @patch('boto3.client')
    def test_aws_environment_secrets_manager_failure(self, mock_boto3_client, mock_exists):
        """AWS 환경에서 Secrets Manager 실패 시 기본값 사용 테스트"""
        AppConfig._cached_configs.clear()
        mock_exists.return_value = False  # env.json이 없다고 가정
        
        # Mock Secrets Manager client to raise exception
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        mock_client.get_secret_value.side_effect = Exception("Access denied")
        
        config = AppConfig('production')
        
        # Should fall back to default config
        assert config.get_jwt_secret() == 'your-secret-key'
        assert config.get_admin_config()['username'] == 'admin'
        assert config.get_dynamodb_config()['table_name'] == 'blog-table'


    @patch.dict(os.environ, {'AWS_LAMBDA_FUNCTION_NAME': 'test-function'})
    @patch('os.path.exists')
    @patch('boto3.client')
    def test_aws_environment_incomplete_secret(self, mock_boto3_client, mock_exists):
        """AWS 환경에서 불완전한 Secret 처리 테스트"""
        AppConfig._cached_configs.clear()
        mock_exists.return_value = False  # env.json이 없다고 가정
        
        # Mock Secrets Manager client
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        
        # Incomplete secret (missing some sections)
        mock_secret = {
            'jwt_secret': 'aws-secret-key'
            # admin, dynamodb, s3 sections missing
        }
        
        mock_client.get_secret_value.return_value = {
            'SecretString': json.dumps(mock_secret)
        }
        
        config = AppConfig('production')
        
        assert config.get_jwt_secret() == 'aws-secret-key'
        # Missing sections should have default values
        assert config.get_admin_config()['username'] == 'admin'
        assert config.get_dynamodb_config()['table_name'] == 'blog-table'
        assert config.get_s3_config()['bucket_name'] == 'blog-uploads'


    @patch('os.path.exists')
    def test_env_json_read_error(self, mock_exists):
        """env.json 읽기 오류 시 기본값 사용 테스트"""
        AppConfig._cached_configs.clear()
        mock_exists.return_value = True
        
        with patch('builtins.open', side_effect=IOError("Permission denied")):
            config = AppConfig('local')
            
            # Should fall back to default config
            assert config.get_jwt_secret() == 'your-secret-key'
            assert config.get_admin_config()['username'] == 'admin'


    @patch('os.path.exists')
    @patch('builtins.open')
    def test_env_json_invalid_json(self, mock_open, mock_exists):
        """env.json이 유효하지 않은 JSON일 때 테스트"""
        AppConfig._cached_configs.clear()
        mock_exists.return_value = True
        
        # Mock invalid JSON
        mock_file = MagicMock()
        mock_file.read.return_value = '{ invalid json }'
        mock_open.return_value.__enter__.return_value = mock_file
        
        with patch('json.load', side_effect=json.JSONDecodeError("Invalid JSON", "", 0)):
            config = AppConfig('local')
            
            # Should fall back to default config
            assert config.get_jwt_secret() == 'your-secret-key'


    @patch.dict(os.environ, {'AWS_SAM_LOCAL': 'true'})
    @patch('os.path.exists')
    @patch('builtins.open')
    def test_sam_local_environment(self, mock_open, mock_exists):
        """SAM Local 환경에서 env.json 사용 테스트"""
        AppConfig._cached_configs.clear()
        mock_exists.return_value = True
        
        mock_env_data = {
            'local': {
                'jwt_secret': 'sam-local-secret',
                'admin': {
                    'username': 'sam-admin',
                    'password': 'sam-password'
                }
            }
        }
        
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file
        
        with patch('json.load', return_value=mock_env_data):
            config = AppConfig('local')
            
            assert config.get_jwt_secret() == 'sam-local-secret'
            assert config.get_admin_config()['username'] == 'sam-admin'


    def test_get_config_value_nested(self):
        """중첩된 설정값 가져오기 테스트"""
        AppConfig._cached_configs.clear()
        
        with patch('builtins.open', side_effect=FileNotFoundError):
            config = AppConfig()
            
            # Test nested key access
            assert config.get_config_value('admin.username') == 'admin'
            assert config.get_config_value('dynamodb.region') == 'ap-northeast-2'
            assert config.get_config_value('s3.bucket_name') == 'blog-uploads'


    def test_get_config_value_nonexistent(self):
        """존재하지 않는 설정값 가져오기 테스트"""
        AppConfig._cached_configs.clear()
        
        with patch('builtins.open', side_effect=FileNotFoundError):
            config = AppConfig()
            
            # Test non-existent keys
            assert config.get_config_value('nonexistent.key') is None
            assert config.get_config_value('nonexistent.key', 'default') == 'default'
            assert config.get_config_value('admin.nonexistent') is None


    def test_get_config_value_invalid_path(self):
        """잘못된 경로로 설정값 가져오기 테스트"""
        AppConfig._cached_configs.clear()
        
        with patch('builtins.open', side_effect=FileNotFoundError):
            config = AppConfig()
            
            # Test accessing string as dict
            assert config.get_config_value('jwt_secret.invalid') is None
            assert config.get_config_value('jwt_secret.invalid', 'default') == 'default'


    @patch.dict(os.environ, {
        'JWT_SECRET': 'env-jwt-secret',
        'ADMIN_PASSWORD': 'env-admin-password',
        'AWS_REGION': 'us-west-2',
        'TABLE_NAME': 'env-blog-table',
        'S3_BUCKET_NAME': 'env-blog-uploads',
        'S3_REGION': 'us-west-2'
    })
    def test_default_config_with_env_vars(self):
        """환경변수가 설정된 상태에서 기본 설정 테스트"""
        AppConfig._cached_configs.clear()
        
        with patch('builtins.open', side_effect=FileNotFoundError):
            config = AppConfig()
            
            assert config.get_jwt_secret() == 'env-jwt-secret'
            assert config.get_admin_config()['password'] == 'env-admin-password'
            assert config.get_dynamodb_config()['region'] == 'us-west-2'
            assert config.get_dynamodb_config()['table_name'] == 'env-blog-table'
            assert config.get_s3_config()['bucket_name'] == 'env-blog-uploads'
            assert config.get_s3_config()['region'] == 'us-west-2'


    def test_config_caching(self):
        """설정 캐싱 동작 테스트"""
        AppConfig._cached_configs.clear()
        
        with patch('builtins.open', side_effect=FileNotFoundError):
            # First instance should load config
            config1 = AppConfig('test')
            
            # Second instance should use cached config
            with patch('common.config.AppConfig._load_config') as mock_load:
                config2 = AppConfig('test')
                
                # _load_config should not be called for cached stage
                mock_load.assert_not_called()
                
                # Both instances should have same config
                assert config1.config == config2.config


    def test_different_stages_different_configs(self):
        """다른 스테이지는 다른 설정을 가져야 함"""
        AppConfig._cached_configs.clear()
        
        with patch('builtins.open', side_effect=FileNotFoundError):
            config_dev = AppConfig('dev')
            config_prod = AppConfig('prod')
            
            # Different stages should have separate cache entries
            assert 'dev' in AppConfig._cached_configs
            assert 'prod' in AppConfig._cached_configs
            assert config_dev.stage == 'dev'
            assert config_prod.stage == 'prod'


    def test_clear_cache(self):
        """캐시 클리어 테스트"""
        AppConfig._cached_configs['test'] = {'test': 'data'}
        
        AppConfig._cached_configs.clear()
        
        assert len(AppConfig._cached_configs) == 0
