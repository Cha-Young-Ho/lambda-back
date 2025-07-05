"""
Structured logging for Lambda functions
AWS CloudWatch와 호환되는 구조화된 로깅 시스템
"""
import json
import logging
import os
from datetime import datetime
from typing import Dict, Any, Optional

class LambdaFormatter(logging.Formatter):
    """Lambda용 JSON 구조 로그 포매터"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'function_name': os.environ.get('AWS_LAMBDA_FUNCTION_NAME', 'local'),
            'function_version': os.environ.get('AWS_LAMBDA_FUNCTION_VERSION', 'local'),
            'request_id': getattr(record, 'request_id', 'unknown'),
        }
        
        # 추가 필드가 있으면 포함
        if hasattr(record, 'extra_fields'):
            log_entry.update(record.extra_fields)
        
        # 에러 정보 포함
        if record.exc_info:
            log_entry['error'] = {
                'type': record.exc_info[0].__name__ if record.exc_info[0] else None,
                'message': str(record.exc_info[1]) if record.exc_info[1] else None,
                'traceback': self.formatException(record.exc_info)
            }
        
        return json.dumps(log_entry, ensure_ascii=False)

def get_logger(name: str) -> logging.Logger:
    """구조화된 로거 인스턴스 반환"""
    logger = logging.getLogger(name)
    
    # 이미 핸들러가 설정되어 있으면 반환
    if logger.handlers:
        return logger
    
    # 로그 레벨 설정
    log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
    logger.setLevel(getattr(logging, log_level, logging.INFO))
    
    # 핸들러 생성
    handler = logging.StreamHandler()
    handler.setFormatter(LambdaFormatter())
    logger.addHandler(handler)
    
    # 중복 로그 방지
    logger.propagate = False
    
    return logger

def log_with_context(logger: logging.Logger, level: str, message: str, 
                    request_id: Optional[str] = None, **kwargs):
    """컨텍스트 정보와 함께 로그 기록"""
    record = logging.LogRecord(
        name=logger.name,
        level=getattr(logging, level.upper()),
        pathname='',
        lineno=0,
        msg=message,
        args=(),
        exc_info=None
    )
    
    # 추가 필드 설정
    record.request_id = request_id or 'unknown'
    record.extra_fields = kwargs
    
    logger.handle(record)

def log_api_call(logger: logging.Logger, event: Dict[str, Any], 
                context: Any, duration: Optional[float] = None):
    """API 호출 로그"""
    log_entry = {
        'event_type': 'api_call',
        'method': event.get('httpMethod'),
        'path': event.get('path'),
        'source_ip': event.get('requestContext', {}).get('identity', {}).get('sourceIp'),
        'user_agent': event.get('headers', {}).get('User-Agent'),
        'query_params': event.get('queryStringParameters'),
        'path_params': event.get('pathParameters'),
    }
    
    if duration is not None:
        log_entry['duration_seconds'] = duration
    
    log_with_context(
        logger, 
        'INFO', 
        f"API Call: {event.get('httpMethod')} {event.get('path')}",
        request_id=getattr(context, 'aws_request_id', 'local'),
        **log_entry
    )

def log_database_operation(logger: logging.Logger, operation: str, table_name: str, 
                          key: Optional[Dict] = None, duration: Optional[float] = None,
                          request_id: Optional[str] = None):
    """데이터베이스 작업 로그"""
    log_entry = {
        'event_type': 'database_operation',
        'operation': operation,
        'table_name': table_name,
        'key': key
    }
    
    if duration is not None:
        log_entry['duration_seconds'] = duration
    
    log_with_context(
        logger,
        'INFO',
        f"DB Operation: {operation} on {table_name}",
        request_id=request_id,
        **log_entry
    )

def log_error(logger: logging.Logger, error: Exception, context: Optional[Dict] = None,
              request_id: Optional[str] = None):
    """에러 로그"""
    import traceback
    
    log_entry = {
        'event_type': 'error',
        'error_type': type(error).__name__,
        'error_message': str(error),
        'traceback': traceback.format_exc()
    }
    
    if context:
        log_entry['context'] = context
    
    log_with_context(
        logger,
        'ERROR',
        f"Error occurred: {type(error).__name__}: {str(error)}",
        request_id=request_id,
        **log_entry
    )
