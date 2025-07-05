"""
Category management system
카테고리 관리 중앙화 및 확장 가능한 구조
"""
from typing import Dict, List, Optional
from enum import Enum

class ContentType(Enum):
    """컨텐츠 타입 열거형"""
    NEWS = "news"
    GALLERY = "gallery"

# 카테고리 정의 (확장 가능한 구조)
CATEGORY_DEFINITIONS = {
    ContentType.NEWS: {
        "allowed_categories": ["센터소식", "프로그램소식", "행사소식", "생활정보", "기타"],
        "default_category": "기타",
        "required": False,
        "description": "뉴스 카테고리"
    },
    ContentType.GALLERY: {
        "allowed_categories": ["공지사항", "질문", "건의", "참고자료", "기타", "세미나", "일정"],
        "default_category": "공지사항",
        "required": False,
        "description": "갤러리 카테고리"
    }
}

def get_allowed_categories(content_type: str) -> List[str]:
    """
    컨텐츠 타입에 따른 허용 카테고리 목록 반환
    
    Args:
        content_type: 'news', 'gallery'
    
    Returns:
        허용된 카테고리 목록
    """
    try:
        content_enum = ContentType(content_type.lower())
        return CATEGORY_DEFINITIONS[content_enum]["allowed_categories"]
    except (ValueError, KeyError):
        return []

def get_default_category(content_type: str) -> Optional[str]:
    """
    컨텐츠 타입에 따른 기본 카테고리 반환
    
    Args:
        content_type: 'news', 'gallery'
    
    Returns:
        기본 카테고리
    """
    try:
        content_enum = ContentType(content_type.lower())
        return CATEGORY_DEFINITIONS[content_enum]["default_category"]
    except (ValueError, KeyError):
        return None

def validate_category_value(content_type: str, category: str) -> bool:
    """
    카테고리 값이 유효한지 검증
    
    Args:
        content_type: 'news', 'gallery'
        category: 검증할 카테고리 값
    
    Returns:
        유효성 여부
    """
    if not category:  # 빈 값은 허용
        return True
    
    allowed_categories = get_allowed_categories(content_type)
    return category in allowed_categories

def is_category_required(content_type: str) -> bool:
    """
    컨텐츠 타입에서 카테고리가 필수인지 확인
    
    Args:
        content_type: 'news', 'gallery'
    
    Returns:
        필수 여부
    """
    try:
        content_enum = ContentType(content_type.lower())
        return CATEGORY_DEFINITIONS[content_enum]["required"]
    except (ValueError, KeyError):
        return False

def get_category_info(content_type: str) -> Dict:
    """
    컨텐츠 타입의 카테고리 정보 전체 반환
    
    Args:
        content_type: 'news', 'gallery'
    
    Returns:
        카테고리 정보 딕셔너리
    """
    try:
        content_enum = ContentType(content_type.lower())
        return CATEGORY_DEFINITIONS[content_enum].copy()
    except (ValueError, KeyError):
        return {
            "allowed_categories": [],
            "default_category": None,
            "required": False,
            "description": "Unknown content type"
        }

def normalize_category(content_type: str, category: Optional[str]) -> Optional[str]:
    """
    카테고리 값을 정규화
    - 빈 값이면 기본값 사용 (설정에 따라)
    - 트림 처리
    
    Args:
        content_type: 'news', 'gallery'
        category: 정규화할 카테고리 값
    
    Returns:
        정규화된 카테고리 값
    """
    if not category or not category.strip():
        # 필수가 아니면 빈 값 허용, 필수면 기본값 사용
        if is_category_required(content_type):
            return get_default_category(content_type)
        return None
    
    # 공백 제거
    normalized = category.strip()
    
    # 유효성 검증
    if validate_category_value(content_type, normalized):
        return normalized
    
    # 유효하지 않으면 None 반환 (에러 처리는 상위에서)
    return None

def get_validation_error_message(content_type: str, category: str) -> str:
    """
    카테고리 검증 실패 시 에러 메시지 생성
    
    Args:
        content_type: 'news', 'gallery'
        category: 실패한 카테고리 값
    
    Returns:
        에러 메시지
    """
    allowed_categories = get_allowed_categories(content_type)
    return (f"Invalid category '{category}' for {content_type}. "
            f"Allowed categories: {', '.join(allowed_categories)}")

# 카테고리 관리 API (관리자용)
def add_category(content_type: str, category: str) -> bool:
    """
    새 카테고리 추가 (런타임 중 추가 - 실제로는 설정 파일 수정 필요)
    
    Args:
        content_type: 'news', 'gallery'
        category: 추가할 카테고리
    
    Returns:
        성공 여부
    """
    try:
        content_enum = ContentType(content_type.lower())
        current_categories = CATEGORY_DEFINITIONS[content_enum]["allowed_categories"]
        
        if category not in current_categories:
            current_categories.append(category)
            return True
        return False
    except (ValueError, KeyError):
        return False

def remove_category(content_type: str, category: str) -> bool:
    """
    카테고리 제거 (런타임 중 제거 - 실제로는 설정 파일 수정 필요)
    
    Args:
        content_type: 'news', 'gallery'
        category: 제거할 카테고리
    
    Returns:
        성공 여부
    """
    try:
        content_enum = ContentType(content_type.lower())
        current_categories = CATEGORY_DEFINITIONS[content_enum]["allowed_categories"]
        
        if category in current_categories and len(current_categories) > 1:
            current_categories.remove(category)
            return True
        return False
    except (ValueError, KeyError):
        return False

def get_all_categories() -> Dict[str, List[str]]:
    """
    모든 컨텐츠 타입의 카테고리 반환
    
    Returns:
        {content_type: [categories]} 형태의 딕셔너리
    """
    return {
        content_type.value: definition["allowed_categories"]
        for content_type, definition in CATEGORY_DEFINITIONS.items()
    }
