"""
공통 응답 처리 유틸리티
모든 Lambda 함수에서 일관된 HTTP 응답을 생성합니다.
실제 업계 표준에 맞는 응답 형식과 CORS 처리
"""
import json
from typing import Any, Dict, Optional, Union
from decimal import Decimal


class DecimalEncoder(json.JSONEncoder):
    """DynamoDB Decimal 타입을 JSON으로 인코딩"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        return super(DecimalEncoder, self).default(obj)


def create_response(status_code: int, body: Any, headers: Optional[Dict[str, str]] = None, 
                   cors: bool = True) -> Dict[str, Any]:
    """
    표준 HTTP 응답 생성
    
    Args:
        status_code: HTTP 상태 코드
        body: 응답 본문
        headers: 추가 헤더
        cors: CORS 헤더 포함 여부
    
    Returns:
        Lambda 응답 형식
    """
    response_headers = {
        'Content-Type': 'application/json; charset=utf-8'
    }
    
    # CORS 헤더 추가
    if cors:
        response_headers.update({
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Max-Age': '86400'
        })
    
    # 사용자 정의 헤더 추가
    if headers:
        response_headers.update(headers)
    
    # 응답 본문이 문자열이 아니면 JSON으로 변환
    if not isinstance(body, str):
        body = json.dumps(body, cls=DecimalEncoder, ensure_ascii=False)
    
    return {
        'statusCode': status_code,
        'headers': response_headers,
        'body': body
    }


def create_error_response(status_code: int, message: str, details: Optional[Dict] = None,
                         error_code: Optional[str] = None) -> Dict[str, Any]:
    """
    표준 에러 응답 생성
    
    Args:
        status_code: HTTP 상태 코드
        message: 에러 메시지
        details: 추가 에러 상세정보
        error_code: 에러 코드
    
    Returns:
        에러 응답
    """
    error_body = {
        'success': False,
        'error': {
            'message': message,
            'status_code': status_code
        }
    }
    
    if error_code:
        error_body['error']['code'] = error_code
    
    if details:
        error_body['error']['details'] = details
    
    # 타임스탬프 추가
    from datetime import datetime
    error_body['timestamp'] = datetime.utcnow().isoformat() + 'Z'
    
    return create_response(status_code, error_body)


def create_success_response(data: Any, message: Optional[str] = None, 
                           metadata: Optional[Dict] = None) -> Dict[str, Any]:
    """
    표준 성공 응답 생성
    
    Args:
        data: 응답 데이터
        message: 성공 메시지
        metadata: 메타데이터 (페이징 정보 등)
    
    Returns:
        성공 응답
    """
    response_body = {
        'success': True,
        'data': data
    }
    
    if message:
        response_body['message'] = message
    
    if metadata:
        response_body['metadata'] = metadata
    
    # 타임스탬프 추가
    from datetime import datetime
    response_body['timestamp'] = datetime.utcnow().isoformat() + 'Z'
    
    return create_response(200, response_body)


def create_paginated_response(items: list, total: int, page: int, limit: int, 
                             has_next: bool = False, next_key: Optional[str] = None) -> Dict[str, Any]:
    """
    페이지네이션 응답 생성
    
    Args:
        items: 아이템 목록
        total: 총 아이템 수
        page: 현재 페이지
        limit: 페이지 크기
        has_next: 다음 페이지 존재 여부
        next_key: 다음 페이지 키
    
    Returns:
        페이지네이션 응답
    """
    metadata = {
        'pagination': {
            'total': total,
            'page': page,
            'limit': limit,
            'has_next': has_next
        }
    }
    
    if next_key:
        metadata['pagination']['next_key'] = next_key
    
    return create_success_response(items, metadata=metadata)


def create_validation_error_response(errors: Union[str, list, dict]) -> Dict[str, Any]:
    """
    유효성 검사 실패 응답 생성
    
    Args:
        errors: 유효성 검사 에러 정보
    
    Returns:
        유효성 검사 실패 응답
    """
    if isinstance(errors, str):
        errors = [errors]
    
    return create_error_response(
        400,
        "Validation failed",
        {'validation_errors': errors},
        'VALIDATION_ERROR'
    )


def create_not_found_response(resource: str, identifier: Optional[str] = None) -> Dict[str, Any]:
    """
    리소스 없음 응답 생성
    
    Args:
        resource: 리소스 이름
        identifier: 리소스 식별자
    
    Returns:
        Not Found 응답
    """
    message = f"{resource} not found"
    if identifier:
        message += f" (ID: {identifier})"
    
    return create_error_response(404, message, error_code='NOT_FOUND')


def create_unauthorized_response(message: str = "Authentication required") -> Dict[str, Any]:
    """
    인증 실패 응답 생성
    
    Args:
        message: 인증 실패 메시지
    
    Returns:
        Unauthorized 응답
    """
    return create_error_response(401, message, error_code='UNAUTHORIZED')


def create_forbidden_response(message: str = "Access denied") -> Dict[str, Any]:
    """
    권한 없음 응답 생성
    
    Args:
        message: 권한 없음 메시지
    
    Returns:
        Forbidden 응답
    """
    return create_error_response(403, message, error_code='FORBIDDEN')


def create_created_response(data: Any, message: str = "Resource created successfully") -> Dict[str, Any]:
    """
    생성 성공 응답 생성
    
    Args:
        data: 생성된 리소스 데이터
        message: 생성 성공 메시지
    
    Returns:
        Created 응답
    """
    response_body = {
        'success': True,
        'message': message,
        'data': data
    }
    
    from datetime import datetime
    response_body['timestamp'] = datetime.utcnow().isoformat() + 'Z'
    
    return create_response(201, response_body)


def create_no_content_response() -> Dict[str, Any]:
    """
    No Content 응답 생성 (삭제 성공 등)
    
    Returns:
        No Content 응답
    """
    return create_response(204, '')


# 기존 함수들과의 호환성을 위한 별칭
def create_cors_response(status_code: int, body: Any) -> Dict[str, Any]:
    """기존 코드와의 호환성을 위한 함수"""
    return create_response(status_code, body, cors=True)
