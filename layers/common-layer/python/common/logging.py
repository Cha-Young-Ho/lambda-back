"""
Structured logging for Lambda functions
AWS CloudWatch와 호환되는 구조화된 로깅 시스템
성능 모니터링 및 메트릭 수집 기능 포함
"""
import json
import logging
import os
import time
from datetime import datetime
from typing import Dict, Any, Optional, Union
from functools import wraps


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
        
        # 성능 메트릭 포함
        if hasattr(record, 'metrics'):
            log_entry['metrics'] = record.metrics
        
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

def log_performance_metric(logger: logging.Logger, metric_name: str, value: Union[int, float], 
                          unit: str = 'count', context: Optional[Dict] = None,
                          request_id: Optional[str] = None):
    """성능 메트릭 로그"""
    log_entry = {
        'event_type': 'performance_metric',
        'metric_name': metric_name,
        'value': value,
        'unit': unit,
        'context': context or {}
    }
    
    log_with_context(
        logger,
        'INFO',
        f"Metric: {metric_name} = {value} {unit}",
        request_id=request_id,
        metrics=log_entry
    )


def performance_monitor(metric_name: str, logger: Optional[logging.Logger] = None):
    """성능 모니터링 데코레이터"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            _logger = logger or get_logger(func.__module__)
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                success = True
                error_type = None
            except Exception as e:
                success = False
                error_type = type(e).__name__
                raise
            finally:
                duration = time.time() - start_time
                
                # 성능 메트릭 로그
                log_performance_metric(
                    _logger,
                    f"{metric_name}_duration",
                    duration,
                    'seconds',
                    {
                        'function': func.__name__,
                        'success': success,
                        'error_type': error_type
                    }
                )
                
                # 성공/실패 카운트 메트릭
                status_metric = f"{metric_name}_{'success' if success else 'error'}"
                log_performance_metric(_logger, status_metric, 1, 'count')
            
            return result
        return wrapper
    return decorator


class PerformanceTimer:
    """성능 측정용 컨텍스트 매니저"""
    
    def __init__(self, metric_name: str, logger: Optional[logging.Logger] = None, 
                 context: Optional[Dict] = None):
        self.metric_name = metric_name
        self.logger = logger or get_logger(__name__)
        self.context = context or {}
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        
        # 성능 메트릭 로그
        self.context.update({
            'success': exc_type is None,
            'error_type': exc_type.__name__ if exc_type else None
        })
        
        log_performance_metric(
            self.logger,
            f"{self.metric_name}_duration",
            duration,
            'seconds',
            self.context
        )


def log_memory_usage(logger: logging.Logger, context: str = "general", 
                    request_id: Optional[str] = None):
    """메모리 사용량 로그"""
    try:
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        
        log_performance_metric(
            logger,
            "memory_usage_mb",
            memory_info.rss / 1024 / 1024,
            'megabytes',
            {'context': context},
            request_id
        )
    except ImportError:
        # psutil이 없으면 무시
        pass


def log_cold_start(logger: logging.Logger, is_cold_start: bool, 
                  request_id: Optional[str] = None):
    """Lambda 콜드 스타트 메트릭"""
    log_performance_metric(
        logger,
        "cold_start",
        1 if is_cold_start else 0,
        'count',
        {'cold_start': is_cold_start},
        request_id
    )
