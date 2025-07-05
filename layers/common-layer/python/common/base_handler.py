"""
Base API handler for standardized Lambda function structure
표준화된 Lambda 함수 구조를 위한 베이스 핸들러
"""
import json
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Callable
from datetime import datetime

from common.config import AppConfig
from common.logging import get_logger, log_api_call, PerformanceTimer
from common.error_handlers import handle_api_error, ErrorContext
from common.response import create_response, create_error_response
from common.auth_decorators import admin_required

logger = get_logger(__name__)

class BaseAPIHandler(ABC):
    """표준화된 API 핸들러 베이스 클래스"""
    
    def __init__(self):
        self.app_config = AppConfig()
        self.cold_start = True
    
    @abstractmethod
    def get_service(self):
        """서비스 인스턴스 반환"""
        pass
    
    def lambda_handler(self, event: Dict[str, Any], context: Any) -> Dict[str, Any]:
        """
        표준화된 Lambda 핸들러
        
        Args:
            event: Lambda 이벤트
            context: Lambda 컨텍스트
        
        Returns:
            API Gateway 응답
        """
        request_id = getattr(context, 'aws_request_id', 'local')
        
        with PerformanceTimer('api_request', logger, {'handler': self.__class__.__name__}):
            try:
                # 콜드 스타트 로깅
                if self.cold_start:
                    logger.info(f"Cold start for {self.__class__.__name__}", 
                              extra={'cold_start': True, 'request_id': request_id})
                    self.cold_start = False
                
                # API 호출 로깅
                start_time = datetime.utcnow()
                log_api_call(logger, event, context)
                
                # HTTP 메서드와 경로 추출
                method = event.get('httpMethod', '').upper()
                path = event.get('path', '')
                
                # 라우팅 및 처리
                response = self._route_request(event, context, method, path)
                
                # 성공 로깅
                duration = (datetime.utcnow() - start_time).total_seconds()
                logger.info(f"Request completed successfully", 
                           extra={
                               'request_id': request_id,
                               'duration': duration,
                               'status_code': response.get('statusCode', 200)
                           })
                
                return response
                
            except Exception as e:
                # 에러 처리
                return handle_api_error(e, request_id)
    
    def _route_request(self, event: Dict[str, Any], context: Any, 
                      method: str, path: str) -> Dict[str, Any]:
        """
        요청 라우팅
        
        Args:
            event: Lambda 이벤트
            context: Lambda 컨텍스트
            method: HTTP 메서드
            path: 요청 경로
        
        Returns:
            API 응답
        """
        request_id = getattr(context, 'aws_request_id', 'local')
        
        with ErrorContext('route_request', path, request_id):
            # CORS 처리
            if method == 'OPTIONS':
                return self._handle_options()
            
            # 경로별 라우팅
            if '/health' in path:
                return self._handle_health()
            elif '/upload-url' in path:
                return self._handle_upload_url(event, context)
            elif path.endswith('/recent'):
                return self._handle_get_recent(event, context)
            elif self._is_item_path(path):
                return self._handle_item_request(event, context, method)
            else:
                return self._handle_collection_request(event, context, method)
    
    def _is_item_path(self, path: str) -> bool:
        """아이템별 경로인지 확인"""
        # /news/123, /gallery/456 같은 패턴 확인
        path_parts = [p for p in path.split('/') if p]
        return len(path_parts) >= 2 and path_parts[-1] != 'recent'
    
    def _handle_options(self) -> Dict[str, Any]:
        """CORS OPTIONS 요청 처리"""
        return create_response(
            {},
            200,
            {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type, Authorization'
            }
        )
    
    def _handle_health(self) -> Dict[str, Any]:
        """헬스 체크 처리"""
        from common.health import get_health_status
        health_data = get_health_status()
        return create_response(health_data)
    
    def _handle_collection_request(self, event: Dict[str, Any], context: Any, 
                                 method: str) -> Dict[str, Any]:
        """컬렉션 요청 처리 (목록 조회, 생성)"""
        service = self.get_service()
        
        if method == 'GET':
            return self._handle_list(event, service)
        elif method == 'POST':
            return self._handle_create(event, service)
        else:
            return create_error_response(f"Method {method} not allowed", 405)
    
    def _handle_item_request(self, event: Dict[str, Any], context: Any, 
                           method: str) -> Dict[str, Any]:
        """아이템별 요청 처리 (상세 조회, 수정, 삭제)"""
        service = self.get_service()
        item_id = self._extract_item_id(event.get('path', ''))
        
        if not item_id:
            return create_error_response("Item ID is required", 400)
        
        if method == 'GET':
            return self._handle_get_by_id(item_id, service)
        elif method == 'PUT':
            return self._handle_update(event, item_id, service)
        elif method == 'DELETE':
            return self._handle_delete(item_id, service)
        else:
            return create_error_response(f"Method {method} not allowed", 405)
    
    def _extract_item_id(self, path: str) -> Optional[str]:
        """경로에서 아이템 ID 추출"""
        path_params = [p for p in path.split('/') if p]
        return path_params[-1] if path_params else None
    
    @abstractmethod
    def _handle_list(self, event: Dict[str, Any], service) -> Dict[str, Any]:
        """목록 조회 처리"""
        pass
    
    @abstractmethod
    def _handle_get_recent(self, event: Dict[str, Any], context: Any) -> Dict[str, Any]:
        """최근 아이템 조회 처리"""
        pass
    
    @abstractmethod
    def _handle_get_by_id(self, item_id: str, service) -> Dict[str, Any]:
        """ID별 조회 처리"""
        pass
    
    @abstractmethod
    def _handle_create(self, event: Dict[str, Any], service) -> Dict[str, Any]:
        """생성 처리"""
        pass
    
    @abstractmethod
    def _handle_update(self, event: Dict[str, Any], item_id: str, service) -> Dict[str, Any]:
        """수정 처리"""
        pass
    
    @abstractmethod
    def _handle_delete(self, item_id: str, service) -> Dict[str, Any]:
        """삭제 처리"""
        pass
    
    @abstractmethod
    def _handle_upload_url(self, event: Dict[str, Any], context: Any) -> Dict[str, Any]:
        """업로드 URL 생성 처리"""
        pass
    
    def _parse_body(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """요청 본문 파싱"""
        body = event.get('body', '{}')
        if isinstance(body, str):
            return json.loads(body) if body else {}
        return body
    
    def _get_query_params(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """쿼리 파라미터 추출"""
        return event.get('queryStringParameters') or {}
    
    def _requires_admin(self, func: Callable) -> Callable:
        """관리자 권한 필요 데코레이터"""
        return admin_required(func)
