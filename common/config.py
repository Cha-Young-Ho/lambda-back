"""
공통 설정 관리 모듈
Secrets Manager에서 환경별 설정을 가져와서 사용
"""
import json
import os
import boto3
from botocore.exceptions import ClientError
from typing import Dict, Any, Optional

class ConfigManager:
    def __init__(self):
        self.secrets_client = boto3.client('secretsmanager')
        self.stage = os.environ.get('STAGE', 'dev')
        self._config_cache: Optional[Dict[str, Any]] = None
    
    def get_config(self) -> Dict[str, Any]:
        """환경별 설정을 Secrets Manager에서 가져옴"""
        if self._config_cache is not None:
            return self._config_cache
        
        # 로컬 환경이면 Secrets Manager 건너뛰고 기본 설정 사용
        if self.stage == "local":
            print("Local environment detected, using default config")
            self._config_cache = self._get_default_config()
            return self._config_cache
        
        secret_name = f"myapp/{self.stage}/config"
        
        try:
            response = self.secrets_client.get_secret_value(SecretId=secret_name)
            config = json.loads(response['SecretString'])
            self._config_cache = config
            return config
        except ClientError as e:
            print(f"Failed to get config from Secrets Manager: {e}")
            # Fallback to default config for local development
            print("Falling back to default config")
            self._config_cache = self._get_default_config()
            return self._config_cache
    
    def _get_default_config(self) -> Dict[str, Any]:
        """로컬 개발용 기본 설정"""
        # Lambda 컨테이너에서는 host.docker.internal을 사용하여 호스트의 DynamoDB Local에 연결
        dynamodb_endpoint = "http://host.docker.internal:8000" if self.stage == "local" else None
        
        return {
            "dynamodb": {
                "table_name": f"myapp-{self.stage}-table",
                "endpoint_url": dynamodb_endpoint
            },
            "external_apis": {
                "some_service": {
                    "endpoint": "https://api.example.com"
                }
            }
        }
    
    def get_dynamodb_config(self) -> Dict[str, Any]:
        """DynamoDB 설정 반환"""
        config = self.get_config()
        return config.get("dynamodb", {})
    
    def get_table_name(self) -> str:
        """DynamoDB 테이블명 반환"""
        dynamodb_config = self.get_dynamodb_config()
        return dynamodb_config.get("table_name", f"myapp-{self.stage}-table")
    
    def get_external_endpoint(self, service_name: str) -> Optional[str]:
        """외부 서비스 엔드포인트 반환"""
        config = self.get_config()
        external_apis = config.get("external_apis", {})
        service_config = external_apis.get(service_name, {})
        return service_config.get("endpoint")

# 싱글톤 인스턴스
config_manager = ConfigManager()
