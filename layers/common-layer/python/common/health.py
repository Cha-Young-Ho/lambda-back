"""
Health check and utility endpoints
시스템 상태 확인 및 유틸리티 엔드포인트
"""
import os
from datetime import datetime
from typing import Dict, Any

from .config import AppConfig
from .response import create_success_response, create_error_response
from .database import get_dynamodb, get_table
from .categories import get_all_categories
from .logging import get_logger

logger = get_logger(__name__)

def get_system_health(app_config: AppConfig) -> Dict[str, Any]:
    """시스템 전체 상태 확인"""
    health_status = {
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'components': {}
    }
    
    # 데이터베이스 연결 확인
    try:
        dynamodb_config = app_config.get_dynamodb_config()
        dynamodb = get_dynamodb(
            region=dynamodb_config['region'],
            table_name=dynamodb_config['table_name'],
            endpoint_url=dynamodb_config.get('endpoint_url')
        )
        table = get_table(dynamodb, dynamodb_config['table_name'])
        
        # 간단한 테이블 정보 조회
        table_info = table.meta.client.describe_table(TableName=dynamodb_config['table_name'])
        
        health_status['components']['database'] = {
            'status': 'healthy',
            'table_name': dynamodb_config['table_name'],
            'table_status': table_info['Table']['TableStatus'],
            'item_count': table_info['Table'].get('ItemCount', 0)
        }
        
    except Exception as e:
        health_status['status'] = 'unhealthy'
        health_status['components']['database'] = {
            'status': 'unhealthy',
            'error': str(e)
        }
    
    # 설정 상태 확인
    try:
        admin_config = app_config.get_admin_config()
        jwt_secret = app_config.get_jwt_secret()
        
        health_status['components']['configuration'] = {
            'status': 'healthy',
            'admin_configured': bool(admin_config.get('username')),
            'jwt_secret_configured': bool(jwt_secret),
            'stage': app_config.stage
        }
        
    except Exception as e:
        health_status['status'] = 'unhealthy'
        health_status['components']['configuration'] = {
            'status': 'unhealthy',
            'error': str(e)
        }
    
    # 환경 정보
    health_status['environment'] = {
        'aws_region': os.environ.get('AWS_REGION', 'unknown'),
        'function_name': os.environ.get('AWS_LAMBDA_FUNCTION_NAME', 'local'),
        'function_version': os.environ.get('AWS_LAMBDA_FUNCTION_VERSION', 'local'),
        'runtime': 'python3.11',
        'is_lambda': os.environ.get('AWS_LAMBDA_FUNCTION_NAME') is not None
    }
    
    return health_status

def get_api_info() -> Dict[str, Any]:
    """API 정보 반환"""
    return {
        'api_name': 'Blog Management System',
        'version': '2.0.0',
        'description': 'Blog management API with news, gallery, and board functionality',
        'endpoints': {
            'auth': [
                'POST /auth/login',
                'POST /auth/validate',
                'GET /auth/test'
            ],
            'news': [
                'GET /news',
                'GET /news/recent',
                'GET /news/{id}',
                'POST /news',
                'PUT /news/{id}',
                'DELETE /news/{id}'
            ],
            'gallery': [
                'GET /gallery',
                'GET /gallery/recent',
                'GET /gallery/{id}',
                'POST /gallery',
                'PUT /gallery/{id}',
                'DELETE /gallery/{id}'
            ],
            'board': [
                'GET /board',
                'GET /board/recent',
                'GET /board/{id}',
                'POST /board',
                'PUT /board/{id}',
                'DELETE /board/{id}',
                'POST /board/upload'
            ]
        },
        'categories': get_all_categories(),
        'features': [
            'JWT Authentication',
            'Category Validation',
            'CRUD Operations',
            'File Upload Support',
            'Performance Monitoring',
            'Structured Logging'
        ]
    }

def get_metrics_summary() -> Dict[str, Any]:
    """메트릭 요약 정보 반환"""
    try:
        from .metrics import cache_metrics
        
        return {
            'cache_metrics': cache_metrics.get_summary(),
            'collection_time': datetime.utcnow().isoformat() + 'Z'
        }
    except ImportError:
        return {
            'error': 'Metrics module not available',
            'collection_time': datetime.utcnow().isoformat() + 'Z'
        }

def create_health_check_handler(app_config: AppConfig):
    """헬스 체크 핸들러 생성"""
    def health_check_handler(event, context):
        try:
            health_status = get_system_health(app_config)
            
            if health_status['status'] == 'healthy':
                return create_success_response(health_status, "System is healthy")
            else:
                return create_error_response(503, "System is unhealthy", health_status)
                
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return create_error_response(500, "Health check failed", {'error': str(e)})
    
    return health_check_handler

def create_info_handler():
    """정보 핸들러 생성"""
    def info_handler(event, context):
        try:
            api_info = get_api_info()
            return create_success_response(api_info, "API information")
            
        except Exception as e:
            logger.error(f"Info endpoint failed: {str(e)}")
            return create_error_response(500, "Info endpoint failed", {'error': str(e)})
    
    return info_handler

def create_metrics_handler():
    """메트릭 핸들러 생성"""
    def metrics_handler(event, context):
        try:
            metrics_summary = get_metrics_summary()
            return create_success_response(metrics_summary, "Metrics summary")
            
        except Exception as e:
            logger.error(f"Metrics endpoint failed: {str(e)}")
            return create_error_response(500, "Metrics endpoint failed", {'error': str(e)})
    
    return metrics_handler
