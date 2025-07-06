"""
Performance monitoring and metrics utilities
성능 모니터링 및 메트릭 수집을 위한 유틸리티
"""
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from contextlib import contextmanager

from .logging import get_logger

logger = get_logger(__name__)

class PerformanceMonitor:
    """성능 모니터링 클래스"""
    
    def __init__(self):
        self.metrics = {}
        self.start_time = None
    
    def start_request(self, request_id: str, operation: str):
        """요청 시작 기록"""
        self.start_time = time.time()
        self.metrics[request_id] = {
            'operation': operation,
            'start_time': self.start_time,
            'end_time': None,
            'duration': None,
            'database_calls': 0,
            'database_duration': 0,
            'errors': []
        }
        
        logger.info(f"Request started - ID: {request_id}, Operation: {operation}")
    
    def end_request(self, request_id: str, status_code: int = 200):
        """요청 종료 기록"""
        if request_id not in self.metrics:
            return
        
        end_time = time.time()
        metric = self.metrics[request_id]
        metric['end_time'] = end_time
        metric['duration'] = end_time - metric['start_time']
        metric['status_code'] = status_code
        
        # 성능 로그 기록
        self._log_performance_metrics(request_id)
    
    def record_database_call(self, request_id: str, operation: str, duration: float):
        """데이터베이스 호출 기록"""
        if request_id in self.metrics:
            self.metrics[request_id]['database_calls'] += 1
            self.metrics[request_id]['database_duration'] += duration
            
            logger.info(f"DB Call - Request: {request_id}, Operation: {operation}, Duration: {duration:.3f}s")
    
    def record_error(self, request_id: str, error: Exception):
        """에러 기록"""
        if request_id in self.metrics:
            self.metrics[request_id]['errors'].append({
                'type': type(error).__name__,
                'message': str(error),
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
    
    def _log_performance_metrics(self, request_id: str):
        """성능 메트릭 로깅"""
        metric = self.metrics[request_id]
        
        log_data = {
            'request_id': request_id,
            'operation': metric['operation'],
            'duration_ms': round(metric['duration'] * 1000, 2),
            'status_code': metric.get('status_code', 'unknown'),
            'database_calls': metric['database_calls'],
            'database_duration_ms': round(metric['database_duration'] * 1000, 2),
            'error_count': len(metric['errors'])
        }
        
        # 성능 임계값 확인
        if metric['duration'] > 5.0:  # 5초 이상
            logger.warning(f"Slow request detected: {log_data}")
        elif metric['duration'] > 1.0:  # 1초 이상
            logger.info(f"Request performance: {log_data}")
        else:
            logger.debug(f"Request performance: {log_data}")

# 글로벌 성능 모니터 인스턴스
_performance_monitor = PerformanceMonitor()

@contextmanager
def monitor_request(request_id: str, operation: str):
    """요청 모니터링 컨텍스트 매니저"""
    _performance_monitor.start_request(request_id, operation)
    try:
        yield _performance_monitor
        _performance_monitor.end_request(request_id, 200)
    except Exception as e:
        _performance_monitor.record_error(request_id, e)
        _performance_monitor.end_request(request_id, 500)
        raise

@contextmanager
def monitor_database_operation(request_id: str, operation: str):
    """데이터베이스 작업 모니터링 컨텍스트 매니저"""
    start_time = time.time()
    try:
        yield
    finally:
        duration = time.time() - start_time
        _performance_monitor.record_database_call(request_id, operation, duration)

def get_performance_summary(request_id: str) -> Optional[Dict[str, Any]]:
    """성능 요약 정보 반환"""
    if request_id in _performance_monitor.metrics:
        return _performance_monitor.metrics[request_id].copy()
    return None

def log_cold_start():
    """Lambda 콜드 스타트 로깅"""
    logger.info("Lambda cold start detected", extra_fields={
        'event_type': 'cold_start',
        'timestamp': datetime.now(timezone.utc).isoformat()
    })

def log_memory_usage():
    """메모리 사용량 로깅 (가능한 경우)"""
    try:
        import psutil
        memory_info = psutil.Process().memory_info()
        
        logger.info("Memory usage", extra_fields={
            'event_type': 'memory_usage',
            'rss_mb': round(memory_info.rss / 1024 / 1024, 2),
            'vms_mb': round(memory_info.vms / 1024 / 1024, 2)
        })
    except ImportError:
        # psutil이 없으면 스킵
        pass
    except Exception as e:
        logger.warning(f"Failed to get memory usage: {str(e)}")

class CacheMetrics:
    """캐시 메트릭 수집"""
    
    def __init__(self):
        self.hits = 0
        self.misses = 0
        self.total_requests = 0
    
    def record_hit(self):
        """캐시 히트 기록"""
        self.hits += 1
        self.total_requests += 1
    
    def record_miss(self):
        """캐시 미스 기록"""
        self.misses += 1
        self.total_requests += 1
    
    def get_hit_rate(self) -> float:
        """캐시 히트율 반환"""
        if self.total_requests == 0:
            return 0.0
        return self.hits / self.total_requests
    
    def get_summary(self) -> Dict[str, Any]:
        """캐시 메트릭 요약 반환"""
        return {
            'hits': self.hits,
            'misses': self.misses,
            'total_requests': self.total_requests,
            'hit_rate': self.get_hit_rate()
        }

# 글로벌 캐시 메트릭 인스턴스
cache_metrics = CacheMetrics()
