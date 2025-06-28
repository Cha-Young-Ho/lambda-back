"""
공통 응답 처리 유틸리티
모든 Lambda 함수에서 일관된 HTTP 응답을 생성합니다.
"""
import json


def create_response(status_code, body, headers=None):
    """통합 Response 생성"""
    default_headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization'
    }
    
    if headers:
        default_headers.update(headers)
    
    return {
        'statusCode': status_code,
        'headers': default_headers,
        'body': json.dumps(body) if isinstance(body, (dict, list)) else body
    }


def create_error_response(status_code, error_message, error_details=None):
    """에러 응답 생성"""
    error_body = {
        'error': error_message,
        'status_code': status_code
    }
    
    if error_details:
        error_body['details'] = error_details
    
    return create_response(status_code, error_body)


def create_success_response(data, message=None):
    """성공 응답 생성"""
    response_body = {
        'success': True,
        'data': data
    }
    
    if message:
        response_body['message'] = message
    
    return create_response(200, response_body)
