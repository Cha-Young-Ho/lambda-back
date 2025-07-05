"""
Repository pattern for DynamoDB operations
데이터베이스 작업을 추상화하고 재사용 가능하게 만드는 리포지토리 패턴
"""
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from boto3.dynamodb.conditions import Key, Attr

from .database import get_dynamodb, get_table, safe_decimal_convert
from .logging import get_logger, log_database_operation

logger = get_logger(__name__)

class BaseRepository(ABC):
    """기본 리포지토리 클래스"""
    
    def __init__(self, app_config, content_type: str):
        self.app_config = app_config
        self.content_type = content_type
        self.dynamodb_config = app_config.get_dynamodb_config()
        
        # DynamoDB 연결 설정
        self.dynamodb = get_dynamodb(
            region=self.dynamodb_config['region'],
            table_name=self.dynamodb_config['table_name'],
            endpoint_url=self.dynamodb_config.get('endpoint_url')
        )
        self.table = get_table(self.dynamodb, self.dynamodb_config['table_name'])
    
    def create_item(self, data: Dict[str, Any], item_id: Optional[str] = None) -> str:
        """
        새 아이템 생성
        
        Args:
            data: 생성할 데이터
            item_id: 지정할 ID (없으면 자동 생성)
        
        Returns:
            생성된 아이템의 ID
        """
        start_time = datetime.utcnow()
        
        if not item_id:
            item_id = str(uuid.uuid4())
        
        current_time = datetime.utcnow().isoformat() + 'Z'
        
        # 기본 필드 설정
        item = {
            'id': item_id,
            'content_type': self.content_type,
            'created_at': current_time,
            'updated_at': current_time,
            'status': 'published',
            **data
        }
        
        # 컨텐츠 타입별 데이터 정제
        item = self._clean_item_data(item)
        
        try:
            self.table.put_item(Item=item)
            
            # 로깅
            duration = (datetime.utcnow() - start_time).total_seconds()
            log_database_operation(
                logger, 'CREATE', self.dynamodb_config['table_name'], 
                {'id': item_id}, duration
            )
            
            return item_id
            
        except Exception as e:
            logger.error(f"Failed to create item: {str(e)}")
            raise

    def get_item_by_id(self, item_id: str, increment_view: bool = False) -> Optional[Dict[str, Any]]:
        """
        ID로 아이템 조회
        
        Args:
            item_id: 조회할 아이템 ID
            increment_view: 조회수 증가 여부
        
        Returns:
            아이템 데이터 또는 None
        """
        start_time = datetime.utcnow()
        
        try:
            response = self.table.get_item(Key={'id': item_id})
            
            if 'Item' not in response:
                return None
            
            item = response['Item']
            
            # 컨텐츠 타입 확인
            if item.get('content_type') != self.content_type:
                return None
            
            # 조회수 증가 제거됨
            
            # 로깅
            duration = (datetime.utcnow() - start_time).total_seconds()
            log_database_operation(
                logger, 'GET', self.dynamodb_config['table_name'], 
                {'id': item_id}, duration
            )
            
            return self._clean_output_data(item)
            
        except Exception as e:
            logger.error(f"Failed to get item {item_id}: {str(e)}")
            raise

    def update_item(self, item_id: str, data: Dict[str, Any]) -> bool:
        """
        아이템 업데이트
        
        Args:
            item_id: 업데이트할 아이템 ID
            data: 업데이트할 데이터
        
        Returns:
            성공 여부
        """
        start_time = datetime.utcnow()
        
        try:
            # 기존 아이템 존재 확인
            existing_item = self.get_item_by_id(item_id)
            if not existing_item:
                return False
            
            # 업데이트 표현식 구성
            update_expression = 'SET updated_at = :updated_at'
            expression_values = {':updated_at': datetime.utcnow().isoformat() + 'Z'}
            
            # 업데이트할 필드들 추가
            updatable_fields = self._get_updatable_fields()
            for field in updatable_fields:
                if field in data:
                    update_expression += f', {field} = :{field}'
                    expression_values[f':{field}'] = data[field]
            
            if len(expression_values) == 1:  # updated_at만 있으면 업데이트할 것이 없음
                return True
            
            self.table.update_item(
                Key={'id': item_id},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values
            )
            
            # 로깅
            duration = (datetime.utcnow() - start_time).total_seconds()
            log_database_operation(
                logger, 'UPDATE', self.dynamodb_config['table_name'], 
                {'id': item_id}, duration
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update item {item_id}: {str(e)}")
            raise

    def delete_item(self, item_id: str) -> bool:
        """
        아이템 삭제
        
        Args:
            item_id: 삭제할 아이템 ID
        
        Returns:
            성공 여부
        """
        start_time = datetime.utcnow()
        
        try:
            # 존재 확인
            existing_item = self.get_item_by_id(item_id)
            if not existing_item:
                return False
            
            self.table.delete_item(Key={'id': item_id})
            
            # 로깅
            duration = (datetime.utcnow() - start_time).total_seconds()
            log_database_operation(
                logger, 'DELETE', self.dynamodb_config['table_name'], 
                {'id': item_id}, duration
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete item {item_id}: {str(e)}")
            raise

    def list_items(self, limit: int = 50, category: Optional[str] = None, 
                   last_evaluated_key: Optional[str] = None) -> Dict[str, Any]:
        """
        아이템 목록 조회
        
        Args:
            limit: 조회할 아이템 수
            category: 카테고리 필터
            last_evaluated_key: 페이징을 위한 마지막 키
        
        Returns:
            {items: List, next_key: str, total: int} 형태
        """
        start_time = datetime.utcnow()
        
        try:
            # 필터 조건 구성
            filter_expression = Attr('content_type').eq(self.content_type)
            if category:
                filter_expression = filter_expression & Attr('category').eq(category)
            
            # 스캔 파라미터 구성
            scan_params = {
                'FilterExpression': filter_expression,
                'Limit': limit
            }
            
            if last_evaluated_key:
                scan_params['ExclusiveStartKey'] = {'id': last_evaluated_key}
            
            # 스캔 실행 (실제로는 GSI 쿼리 사용 권장)
            response = self.table.scan(**scan_params)
            
            items = [self._clean_output_data(item) for item in response.get('Items', [])]
            
            # 생성일 기준 정렬 (최신순)
            items.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            
            # 로깅
            duration = (datetime.utcnow() - start_time).total_seconds()
            log_database_operation(
                logger, 'SCAN', self.dynamodb_config['table_name'], 
                {'content_type': self.content_type, 'limit': limit}, duration
            )
            
            return {
                'items': items,
                'next_key': response.get('LastEvaluatedKey', {}).get('id'),
                'total': len(items)
            }
            
        except Exception as e:
            logger.error(f"Failed to list items: {str(e)}")
            raise

    def get_recent_items(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        최근 아이템 조회
        
        Args:
            limit: 조회할 아이템 수
        
        Returns:
            최근 아이템 목록
        """
        result = self.list_items(limit=limit)
        return result['items'][:limit]

    # _increment_view_count 메서드 제거됨

    @abstractmethod
    def _get_updatable_fields(self) -> List[str]:
        """업데이트 가능한 필드 목록 반환"""
        pass

    @abstractmethod
    def _clean_item_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """저장 전 데이터 정제"""
        pass

    @abstractmethod
    def _clean_output_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """출력 전 데이터 정제"""
        pass

class NewsRepository(BaseRepository):
    """뉴스 리포지토리"""
    
    def __init__(self, app_config):
        super().__init__(app_config, 'news')
    
    def _get_updatable_fields(self) -> List[str]:
        return ['title', 'content', 'category', 'image_url', 'short_description']
    
    def _clean_item_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """뉴스 데이터 정제"""
        cleaned = data.copy()
        
        # 기본값 설정
        cleaned.setdefault('image_url', '')
        cleaned.setdefault('short_description', '')
        
        return cleaned
    
    def _clean_output_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """뉴스 출력 데이터 정제"""
        return {
            'id': data.get('id', ''),
            'title': data.get('title', ''),
            'content': data.get('content', ''),
            'category': data.get('category', ''),
            'created_at': data.get('created_at', ''),
            'updated_at': data.get('updated_at', ''),
            'status': data.get('status', ''),
            'image_url': data.get('image_url', ''),
            'short_description': data.get('short_description', ''),
            'date': data.get('created_at', '').split('T')[0] if data.get('created_at') else ''
        }

class GalleryRepository(BaseRepository):
    """갤러리 리포지토리"""
    
    def __init__(self, app_config):
        super().__init__(app_config, 'gallery')
    
    def _get_updatable_fields(self) -> List[str]:
        return ['title', 'content', 'category', 'image_url', 'short_description']
    
    def _clean_item_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """갤러리 데이터 정제"""
        cleaned = data.copy()
        
        # 기본값 설정
        cleaned.setdefault('image_url', '')
        cleaned.setdefault('short_description', '')
        
        return cleaned
    
    def _clean_output_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """갤러리 출력 데이터 정제"""
        return {
            'id': data.get('id', ''),
            'title': data.get('title', ''),
            'content': data.get('content', ''),
            'category': data.get('category', ''),
            'created_at': data.get('created_at', ''),
            'updated_at': data.get('updated_at', ''),
            'status': data.get('status', ''),
            'image_url': data.get('image_url', ''),
            'short_description': data.get('short_description', ''),
            'date': data.get('created_at', '').split('T')[0] if data.get('created_at') else ''
        }


