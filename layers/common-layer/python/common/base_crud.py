"""
업계 표준 CRUD 베이스 클래스 - DRY 원칙 적용
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import uuid
from datetime import datetime

from .database import get_dynamodb, get_table
from .config import AppConfig
from .logging import get_logger
from .exceptions import ValidationError, ResourceNotFoundError, DatabaseError
from .utils import generate_uuid, get_current_timestamp, validate_required_fields, paginate_list

logger = get_logger(__name__)


class BaseCRUDService(ABC):
    """CRUD 작업을 위한 베이스 서비스 클래스"""
    
    def __init__(self, config: AppConfig, content_type: str = None):
        self.config = config
        self.content_type = content_type
        self.table = self._get_table()
    
    def _get_table(self):
        """DynamoDB 테이블 연결"""
        try:
            dynamodb_config = self.config.get_dynamodb_config()
            dynamodb = get_dynamodb(
                region=dynamodb_config['region'],
                table_name=dynamodb_config['table_name'],
                endpoint_url=dynamodb_config.get('endpoint_url')
            )
            
            if not dynamodb:
                raise DatabaseError("Failed to connect to DynamoDB")
            
            table = get_table(dynamodb, dynamodb_config['table_name'])
            if not table:
                raise DatabaseError("Failed to access table")
            
            return table
            
        except Exception as e:
            logger.error(f"Database connection error: {str(e)}")
            raise DatabaseError(f"Database connection failed: {str(e)}")
    
    @abstractmethod
    def get_allowed_categories(self) -> List[str]:
        """각 서비스별 허용된 카테고리 반환"""
        pass
    
    @abstractmethod
    def get_required_fields(self) -> List[str]:
        """각 서비스별 필수 필드 반환"""
        pass
    
    @abstractmethod
    def get_sample_data(self) -> List[Dict[str, Any]]:
        """각 서비스별 샘플 데이터 반환"""
        pass
    
    def validate_category(self, category: str) -> None:
        """카테고리 검증"""
        if not category:
            return  # 빈 카테고리는 허용
        
        allowed_categories = self.get_allowed_categories()
        if category not in allowed_categories:
            raise ValidationError(f"Invalid category. Allowed categories: {', '.join(allowed_categories)}")
    
    def validate_item_data(self, data: Dict[str, Any]) -> None:
        """아이템 데이터 검증"""
        # 필수 필드 검증
        required_fields = self.get_required_fields()
        missing_fields = validate_required_fields(data, required_fields)
        if missing_fields:
            raise ValidationError(f"Missing required fields: {', '.join(missing_fields)}")
        
        # 카테고리 검증
        category = data.get('category', '')
        self.validate_category(category)
    
    def create_item(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """아이템 생성"""
        try:
            # 데이터 검증
            self.validate_item_data(data)
            
            # 기본 필드 추가
            item_id = generate_uuid()
            current_time = get_current_timestamp()
            
            item = {
                'id': item_id,
                'created_at': current_time,
                'updated_at': current_time,
                'status': 'published',
                **data
            }
            
            # content_type 추가 (필요한 경우)
            if self.content_type:
                item['content_type'] = self.content_type
            
            # DynamoDB에 저장
            self.table.put_item(Item=item)
            
            logger.info(f"Created item: {item_id}")
            return item
            
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Create item error: {str(e)}")
            raise DatabaseError(f"Failed to create item: {str(e)}")
    
    def get_item(self, item_id: str) -> Dict[str, Any]:
        """아이템 조회"""
        try:
            response = self.table.get_item(Key={'id': item_id})
            
            if 'Item' not in response:
                raise ResourceNotFoundError(f"Item not found: {item_id}")
            
            item = response['Item']
            
            # 조회수 증가
                        item['view_count'] = item.get('view_count', 0) + 1
            
            return item
            
        except ResourceNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Get item error: {str(e)}")
            # Fallback to sample data
            sample_data = self.get_sample_data()
            if sample_data:
                return sample_data[0]  # 첫 번째 샘플 아이템 반환
            raise DatabaseError(f"Failed to get item: {str(e)}")
    
    def update_item(self, item_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """아이템 수정"""
        try:
            # 기존 아이템 확인
            existing_item = self.get_item(item_id)
            
            # 데이터 검증
            self.validate_item_data(data)
            
            # 수정 시간 업데이트
            data['updated_at'] = get_current_timestamp()
            
            # 업데이트 표현식 생성
            update_expression = "SET "
            expression_values = {}
            
            for key, value in data.items():
                if key != 'id':  # ID는 수정 불가
                    update_expression += f"{key} = :{key}, "
                    expression_values[f":{key}"] = value
            
            update_expression = update_expression.rstrip(', ')
            
            # DynamoDB 업데이트
            self.table.update_item(
                Key={'id': item_id},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values,
                ReturnValues='ALL_NEW'
            )
            
            # 업데이트된 아이템 반환
            updated_item = {**existing_item, **data}
            
            logger.info(f"Updated item: {item_id}")
            return updated_item
            
        except (ValidationError, ResourceNotFoundError):
            raise
        except Exception as e:
            logger.error(f"Update item error: {str(e)}")
            raise DatabaseError(f"Failed to update item: {str(e)}")
    
    def delete_item(self, item_id: str) -> None:
        """아이템 삭제"""
        try:
            # 기존 아이템 확인
            self.get_item(item_id)
            
            # DynamoDB에서 삭제
            self.table.delete_item(Key={'id': item_id})
            
            logger.info(f"Deleted item: {item_id}")
            
        except ResourceNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Delete item error: {str(e)}")
            raise DatabaseError(f"Failed to delete item: {str(e)}")
    
    def list_items(self, page: int = 1, limit: int = 10, category: str = None) -> Dict[str, Any]:
        """아이템 목록 조회"""
        try:
            # DynamoDB 스캔
            scan_kwargs = {}
            
            if self.content_type:
                scan_kwargs['FilterExpression'] = 'content_type = :content_type'
                scan_kwargs['ExpressionAttributeValues'] = {':content_type': self.content_type}
            
            response = self.table.scan(**scan_kwargs)
            items = response.get('Items', [])
            
            # 상태가 published인 것만 필터링
            published_items = [item for item in items if item.get('status') == 'published']
            
            # 카테고리 필터링
            if category:
                published_items = [item for item in published_items if item.get('category') == category]
            
            # 생성일시 기준 내림차순 정렬
            published_items.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            
            # 페이지네이션 적용
            return paginate_list(published_items, page, limit)
            
        except Exception as e:
            logger.error(f"List items error: {str(e)}")
            # Fallback to sample data
            sample_data = self.get_sample_data()
            return paginate_list(sample_data, page, limit)
    
    def get_recent_items(self, limit: int = 5, category: str = None) -> List[Dict[str, Any]]:
        """최근 아이템 조회"""
        try:
            items_data = self.list_items(page=1, limit=limit, category=category)
            return items_data['items']
            
        except Exception as e:
            logger.error(f"Get recent items error: {str(e)}")
            sample_data = self.get_sample_data()
            return sample_data[:limit]
    
                logger.warning(f"Failed to increment view count: {str(e)}")
            # 조회수 증가 실패는 치명적이지 않으므로 무시
