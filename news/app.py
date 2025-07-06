"""
News API - Standardized Lambda Handler
표준화된 뉴스 API 핸들러
- 베이스 핸들러 사용
- 표준화된 에러 처리
- 성능 모니터링
"""
import json
import os
from typing import Dict, Any, Optional

from common.repositories import NewsRepository
from common.categories import validate_category_value, get_allowed_categories
from common.s3_service import S3Service, get_allowed_content_types, get_file_extension_from_content_type
from common.response import (
    create_response, create_error_response, create_success_response,
    create_not_found_response, create_created_response, DecimalEncoder
)
from common.logging import get_logger, log_api_call, performance_monitor
from common.config import AppConfig
from common.base_handler import BaseAPIHandler
from common.error_handlers import (
    ValidationError, NotFoundError, validate_required_fields, 
    validate_field_length, validate_pagination_params
)
from common.auth_decorators import admin_required

logger = get_logger(__name__)

class NewsService:
    """뉴스 비즈니스 로직 서비스"""
    
    def __init__(self, app_config):
        self.repo = NewsRepository(app_config)
        self.s3_service = S3Service(app_config)
    
    def get_news_list(self, page: int = 1, limit: int = 10, category: Optional[str] = None):
        """뉴스 목록 조회"""
        # 파라미터 검증
        if page < 1:
            raise ValueError("Page must be greater than 0")
        
        if limit > 50:
            limit = 50  # 최대 50개로 제한
        
        if category and not validate_category_value('news', category):
            raise ValueError(f"Invalid category: {category}")
        
        # 데이터 조회
        result = self.repo.list_items(limit=50, category=category)
        
        # 페이지네이션 처리
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        paginated_items = result['items'][start_idx:end_idx]
        
        return {
            'items': paginated_items,
            'total': result['total'],
            'page': page,
            'limit': limit,
            'has_next': end_idx < result['total']
        }
    
    def get_recent_news(self, limit: int = 5):
        """최근 뉴스 조회"""
        return self.repo.get_recent_items(limit)
    
    def get_news_by_id(self, news_id: str, increment_view: bool = False):
        """뉴스 상세 조회"""
        if not news_id:
            raise ValueError("News ID is required")
        
        return self.repo.get_item_by_id(news_id, increment_view)
    
    def create_news(self, data: Dict[str, Any]):
        """뉴스 생성"""
        # 필수 필드 검증
        required_fields = ['title', 'content']
        for field in required_fields:
            if not data.get(field):
                raise ValueError(f"Field '{field}' is required")
        
        # 카테고리 검증
        category = data.get('category', '')
        if category and not validate_category_value('news', category):
            allowed = get_allowed_categories('news')
            raise ValueError(f"Invalid category. Allowed: {', '.join(allowed)}")
        
        # 데이터 정제
        news_data = {
            'title': data['title'].strip(),
            'content': data['content'].strip(),
            'category': category.strip() if category else '',
            'image_url': data.get('image_url', '').strip(),
            'short_description': data.get('short_description', '').strip()
        }
        
        return self.repo.create_item(news_data)
    
    def update_news(self, news_id: str, data: Dict[str, Any]):
        """뉴스 수정"""
        if not news_id:
            raise ValueError("News ID is required")
        
        # 존재 확인
        existing = self.repo.get_item_by_id(news_id)
        if not existing:
            return None
        
        # 카테고리 검증
        if 'category' in data:
            category = data['category']
            if category and not validate_category_value('news', category):
                allowed = get_allowed_categories('news')
                raise ValueError(f"Invalid category. Allowed: {', '.join(allowed)}")
        
        # 업데이트 가능한 필드만 필터링
        updatable_fields = ['title', 'content', 'category', 'image_url', 'short_description']
        update_data = {}
        
        for field in updatable_fields:
            if field in data:
                value = data[field]
                update_data[field] = value.strip() if isinstance(value, str) else value
        
        if not update_data:
            raise ValueError("No valid fields to update")
        
        success = self.repo.update_item(news_id, update_data)
        return news_id if success else None
    
    def delete_news(self, news_id: str):
        """뉴스 삭제 (관련 이미지도 함께 삭제)"""
        if not news_id:
            raise ValueError("News ID is required")
        
        # 존재 확인 및 이미지 URL 수집
        existing = self.repo.get_item_by_id(news_id)
        if not existing:
            return None
        
        # 삭제할 이미지 파일 키 수집
        file_keys_to_delete = []
        
        # 메인 이미지
        if existing.get('image_url'):
            file_key = self.s3_service.extract_file_key_from_url(existing['image_url'])
            if file_key:
                file_keys_to_delete.append(file_key)
        
        # 뉴스 삭제
        success = self.repo.delete_item(news_id)
        if not success:
            return None
        
        # 관련 이미지 파일들 삭제
        if file_keys_to_delete:
            delete_results = self.s3_service.delete_files(file_keys_to_delete)
            failed_deletes = [key for key, success in delete_results.items() if not success]
            if failed_deletes:
                logger.warning(f"Failed to delete some files for news {news_id}: {failed_deletes}")
        
        return news_id

    def upload_news_image(self, news_id: str, file_content: bytes, content_type: str):
        """뉴스 이미지 업로드"""
        if not news_id:
            raise ValueError("News ID is required")
        
        # 확장자 및 콘텐츠 타입 검증
        allowed_types = get_allowed_content_types('image')
        if content_type not in allowed_types:
            raise ValueError(f"Invalid content type: {content_type}. Allowed: {', '.join(allowed_types)}")
        
        # 파일 업로드
        file_extension = get_file_extension_from_content_type(content_type)
        file_name = f"news/{news_id}/image{file_extension}"
        
        self.s3_service.upload_file(file_name, file_content, content_type)
        
        # 이미지 URL 반환
        bucket_name = self.s3_service.bucket_name
        return f"https://{bucket_name}.s3.amazonaws.com/{file_name}"

def lambda_handler(event, context):
    """뉴스 API Lambda 핸들러"""
    try:
        # 기본 설정
        stage = event.get('requestContext', {}).get('stage', 'local')
        app_config = AppConfig(stage)
        
        # OPTIONS 요청 처리
        if event.get('httpMethod') == 'OPTIONS':
            return create_response(200, '', cors=True)
        
        # API 호출 로깅
        log_api_call(logger, event, context)
        
        # 라우팅
        method = event.get('httpMethod', '').upper()
        path = event.get('path', '')
        path_parameters = event.get('pathParameters') or {}
        
        # 서비스 인스턴스 생성
        service = NewsService(app_config)
        
        # 라우팅 처리
        if method == 'GET' and path == '/news':
            return handle_list_news(event, service)
        elif method == 'GET' and path == '/news/recent':
            return handle_recent_news(event, service)
        elif method == 'POST' and path == '/news/upload-url':
            return handle_generate_upload_url(event, service)
        elif method == 'GET' and '/news/' in path and path_parameters.get('newsId'):
            return handle_get_news(event, service)
        elif method == 'POST' and path == '/news':
            return handle_create_news(event, service)
        elif method == 'PUT' and '/news/' in path and path_parameters.get('newsId'):
            return handle_update_news(event, service)
        elif method == 'DELETE' and '/news/' in path and path_parameters.get('newsId'):
            return handle_delete_news(event, service)
        else:
            return create_error_response(404, f"Route not found: {method} {path}")
    
    except Exception as e:
        logger.error(f"Unhandled error in news handler: {str(e)}")
        return create_error_response(500, "Internal server error")

def handle_list_news(event, service: NewsService):
    """뉴스 목록 조회 핸들러"""
    try:
        query_params = event.get('queryStringParameters') or {}
        page = int(query_params.get('page', '1'))
        limit = int(query_params.get('limit', '10'))
        category = query_params.get('category')
        
        result = service.get_news_list(page, limit, category)
        
        return create_response(200, {
            'success': True,
            'data': result['items'],
            'total': result['total'],
            'page': result['page'],
            'limit': result['limit'],
            'has_next': result['has_next']
        })
        
    except ValueError as e:
        return create_error_response(400, str(e))
    except Exception as e:
        logger.error(f"Error in handle_list_news: {str(e)}")
        return create_error_response(500, "Failed to retrieve news list")

def handle_recent_news(event, service: NewsService):
    """최근 뉴스 조회 핸들러"""
    try:
        items = service.get_recent_news(5)
        
        return create_response(200, {
            'success': True,
            'type': 'news',
            'data': items,
            'total': len(items),
            'is_recent': True
        })
        
    except Exception as e:
        logger.error(f"Error in handle_recent_news: {str(e)}", exc_info=True)
        # 개발 환경에서는 더 구체적인 오류 메시지 제공
        error_detail = str(e) if os.environ.get('STAGE') == 'dev' else "Failed to retrieve recent news"
        return create_error_response(500, error_detail)

def handle_get_news(event, service: NewsService):
    """뉴스 상세 조회 핸들러"""
    try:
        news_id = event.get('pathParameters', {}).get('newsId')
        news_item = service.get_news_by_id(news_id, increment_view=True)
        
        if not news_item:
            return create_not_found_response("News", news_id)
        
        return create_success_response(news_item)
        
    except ValueError as e:
        return create_error_response(400, str(e))
    except Exception as e:
        logger.error(f"Error in handle_get_news: {str(e)}")
        return create_error_response(500, "Failed to retrieve news")

def handle_create_news(event, service: NewsService):
    """뉴스 생성 핸들러"""
    try:
        # JSON 파싱
        body = json.loads(event.get('body', '{}'))
        
        news_id = service.create_news(body)
        
        return create_created_response(
            {'id': news_id},
            "News created successfully"
        )
        
    except json.JSONDecodeError:
        return create_error_response(400, "Invalid JSON format")
    except ValueError as e:
        return create_error_response(400, str(e))
    except Exception as e:
        logger.error(f"Error in handle_create_news: {str(e)}")
        return create_error_response(500, "Failed to create news")

def handle_update_news(event, service: NewsService):
    """뉴스 수정 핸들러"""
    try:
        news_id = event.get('pathParameters', {}).get('newsId')
        body = json.loads(event.get('body', '{}'))
        
        result = service.update_news(news_id, body)
        
        if not result:
            return create_not_found_response("News", news_id)
        
        return create_success_response(
            {'id': result},
            "News updated successfully"
        )
        
    except json.JSONDecodeError:
        return create_error_response(400, "Invalid JSON format")
    except ValueError as e:
        return create_error_response(400, str(e))
    except Exception as e:
        logger.error(f"Error in handle_update_news: {str(e)}")
        return create_error_response(500, "Failed to update news")

def handle_delete_news(event, service: NewsService):
    """뉴스 삭제 핸들러"""
    try:
        news_id = event.get('pathParameters', {}).get('newsId')
        
        result = service.delete_news(news_id)
        
        if not result:
            return create_not_found_response("News", news_id)
        
        return create_success_response(
            {'id': result},
            "News deleted successfully"
        )
        
    except ValueError as e:
        return create_error_response(400, str(e))
    except Exception as e:
        logger.error(f"Error in handle_delete_news: {str(e)}")
        return create_error_response(500, "Failed to delete news")

def handle_generate_upload_url(event, service: NewsService):
    """파일 업로드용 presigned URL 생성 핸들러"""
    try:
        # JSON 파싱
        body = json.loads(event.get('body', '{}'))
        
        # 필수 파라미터 검증
        content_type = body.get('content_type')
        if not content_type:
            return create_error_response(400, "content_type is required")
        
        # 허용되는 파일 타입 검증 (뉴스도 이미지만 허용)
        allowed_types = get_allowed_content_types('image')
        if content_type not in allowed_types:
            return create_error_response(
                400, 
                f"News only supports image files. Allowed: {', '.join(allowed_types)}"
            )
        
        # 파일 확장자 결정
        file_extension = get_file_extension_from_content_type(content_type)
        
        # Presigned URL 생성
        upload_info = service.s3_service.generate_presigned_upload_url(
            content_type=content_type,
            file_extension=file_extension,
            folder="news"
        )
        
        return create_success_response({
            'upload_url': upload_info['upload_url'],
            'file_url': upload_info['file_url'],
            'file_key': upload_info['file_key'],
            'expires_in': upload_info['expires_in'],
            'expires_at': upload_info['expires_at']
        }, "Upload URL generated successfully")
        
    except json.JSONDecodeError:
        return create_error_response(400, "Invalid JSON format")
    except Exception as e:
        logger.error(f"Error in handle_generate_upload_url: {str(e)}")
        return create_error_response(500, "Failed to generate upload URL")
