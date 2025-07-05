"""
업계 표준 유틸리티 함수
"""
import uuid
import re
from datetime import datetime
from typing import Any, Dict, List, Optional


def generate_uuid() -> str:
    """UUID 생성"""
    return str(uuid.uuid4())


def get_current_timestamp() -> str:
    """현재 ISO 타임스탬프 반환"""
    return datetime.utcnow().isoformat() + 'Z'


def validate_email(email: str) -> bool:
    """이메일 형식 검증"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> List[str]:
    """필수 필드 검증"""
    missing_fields = []
    for field in required_fields:
        if field not in data or not data[field]:
            missing_fields.append(field)
    return missing_fields


def clean_html_tags(text: str) -> str:
    """HTML 태그 제거"""
    import re
    clean = re.compile('<.*?>')
    return re.sub(clean, '', text)


def paginate_list(items: List[Any], page: int, limit: int) -> Dict[str, Any]:
    """리스트 페이지네이션"""
    total_count = len(items)
    total_pages = (total_count + limit - 1) // limit
    offset = (page - 1) * limit
    
    paginated_items = items[offset:offset + limit]
    
    return {
        'items': paginated_items,
        'pagination': {
            'current_page': page,
            'total_pages': total_pages,
            'total_count': total_count,
            'limit': limit,
            'has_next': page < total_pages,
            'has_prev': page > 1
        }
    }


def sanitize_string(text: str, max_length: int = None) -> str:
    """문자열 정리 및 길이 제한"""
    if not text:
        return ""
    
    # 앞뒤 공백 제거
    text = text.strip()
    
    # 길이 제한
    if max_length and len(text) > max_length:
        text = text[:max_length]
    
    return text


def safe_get(data: Dict[str, Any], key: str, default: Any = None) -> Any:
    """안전한 딕셔너리 값 가져오기"""
    return data.get(key, default) if isinstance(data, dict) else default


def format_file_size(size_bytes: int) -> str:
    """파일 크기 포맷팅"""
    if size_bytes == 0:
        return "0B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f}{size_names[i]}"
