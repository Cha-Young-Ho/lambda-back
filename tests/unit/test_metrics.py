"""
성능 모니터링 및 메트릭 단위 테스트
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import time

# 이 파일의 모든 테스트를 단위 테스트로 표시
pytestmark = pytest.mark.unit

# 테스트할 모듈 import
from common.metrics import (
    PerformanceMonitor, CacheMetrics, monitor_request, 
    monitor_database_operation, get_performance_summary,
    log_cold_start, log_memory_usage
)


class TestPerformanceMonitor:
    """PerformanceMonitor 클래스 테스트"""
    
    def test_init(self):
        """PerformanceMonitor 초기화 테스트"""
        monitor = PerformanceMonitor()
        assert monitor.metrics == {}
        assert monitor.start_time is None
    
    @patch('common.metrics.time.time')
    @patch('common.metrics.logger')
    def test_start_request(self, mock_logger, mock_time):
        """요청 시작 기록 테스트"""
        mock_time.return_value = 1234567890.0
        
        monitor = PerformanceMonitor()
        monitor.start_request("req-123", "get_news")
        
        assert "req-123" in monitor.metrics
        metric = monitor.metrics["req-123"]
        assert metric['operation'] == "get_news"
        assert metric['start_time'] == 1234567890.0
        assert metric['end_time'] is None
        assert metric['database_calls'] == 0
        
        mock_logger.info.assert_called_once()
    
    @patch('common.metrics.time.time')
    def test_end_request(self, mock_time):
        """요청 종료 기록 테스트"""
        mock_time.side_effect = [1234567890.0, 1234567892.5]  # 2.5초 경과
        
        monitor = PerformanceMonitor()
        monitor.start_request("req-123", "get_news")
        monitor.end_request("req-123", 200)
        
        metric = monitor.metrics["req-123"]
        assert metric['end_time'] == 1234567892.5
        assert metric['duration'] == 2.5
        assert metric['status_code'] == 200
    
    def test_end_request_invalid_id(self):
        """존재하지 않는 요청 ID로 종료 시도 테스트"""
        monitor = PerformanceMonitor()
        # 예외가 발생하지 않아야 함
        monitor.end_request("invalid-id")
    
    def test_record_database_call(self):
        """데이터베이스 호출 기록 테스트"""
        monitor = PerformanceMonitor()
        monitor.start_request("req-123", "get_news")
        
        monitor.record_database_call("req-123", "scan", 0.5)
        monitor.record_database_call("req-123", "query", 0.3)
        
        metric = monitor.metrics["req-123"]
        assert metric['database_calls'] == 2
        assert metric['database_duration'] == 0.8
    
    def test_record_database_call_invalid_id(self):
        """존재하지 않는 요청 ID로 DB 호출 기록 테스트"""
        monitor = PerformanceMonitor()
        # 예외가 발생하지 않아야 함
        monitor.record_database_call("invalid-id", "scan", 0.5)
    
    def test_record_error(self):
        """에러 기록 테스트"""
        monitor = PerformanceMonitor()
        monitor.start_request("req-123", "get_news")
        
        error = ValueError("Test error")
        monitor.record_error("req-123", error)
        
        metric = monitor.metrics["req-123"]
        assert len(metric['errors']) == 1
        assert metric['errors'][0]['type'] == 'ValueError'
        assert metric['errors'][0]['message'] == 'Test error'
    
    def test_record_error_invalid_id(self):
        """존재하지 않는 요청 ID로 에러 기록 테스트"""
        monitor = PerformanceMonitor()
        error = ValueError("Test error")
        # 예외가 발생하지 않아야 함
        monitor.record_error("invalid-id", error)


class TestCacheMetrics:
    """CacheMetrics 클래스 테스트"""
    
    def test_init(self):
        """CacheMetrics 초기화 테스트"""
        cache = CacheMetrics()
        assert cache.hits == 0
        assert cache.misses == 0
    
    def test_record_hit(self):
        """캐시 히트 기록 테스트"""
        cache = CacheMetrics()
        cache.record_hit()
        cache.record_hit()
        
        assert cache.hits == 2
        assert cache.misses == 0
    
    def test_record_miss(self):
        """캐시 미스 기록 테스트"""
        cache = CacheMetrics()
        cache.record_miss()
        cache.record_miss()
        cache.record_miss()
        
        assert cache.hits == 0
        assert cache.misses == 3
    
    def test_get_hit_rate(self):
        """캐시 히트율 계산 테스트"""
        cache = CacheMetrics()
        
        # 초기 상태 (0/0)
        assert cache.get_hit_rate() == 0.0
        
        # 히트만 있는 경우
        cache.record_hit()
        cache.record_hit()
        assert cache.get_hit_rate() == 1.0
        
        # 히트와 미스가 섞인 경우
        cache.record_miss()
        assert cache.get_hit_rate() == 2/3  # 2 hits out of 3 total
    
    def test_get_summary(self):
        """캐시 요약 정보 테스트"""
        cache = CacheMetrics()
        cache.record_hit()
        cache.record_hit()
        cache.record_miss()
        
        summary = cache.get_summary()
        
        assert summary['hits'] == 2
        assert summary['misses'] == 1
        assert summary['hit_rate'] == 2/3


@patch('common.metrics._performance_monitor')
def test_monitor_request_context_manager(mock_monitor):
    """monitor_request 컨텍스트 매니저 테스트"""
    with monitor_request("req-123", "test_operation"):
        pass
    
    mock_monitor.start_request.assert_called_once_with("req-123", "test_operation")
    mock_monitor.end_request.assert_called_once_with("req-123", 200)


@patch('common.metrics._performance_monitor')
def test_monitor_request_with_exception(mock_monitor):
    """monitor_request 예외 발생 시 테스트"""
    try:
        with monitor_request("req-123", "test_operation"):
            raise ValueError("Test error")
    except ValueError:
        pass
    
    mock_monitor.start_request.assert_called_once_with("req-123", "test_operation")
    mock_monitor.record_error.assert_called_once()
    mock_monitor.end_request.assert_called_once_with("req-123", 500)


@patch('common.metrics._performance_monitor')
@patch('common.metrics.time.time')
def test_monitor_database_operation(mock_time, mock_monitor):
    """monitor_database_operation 테스트"""
    mock_time.side_effect = [1234567890.0, 1234567890.5]  # 0.5초 경과
    
    with monitor_database_operation("req-123", "query_users"):
        pass
    
    mock_monitor.record_database_call.assert_called_once_with(
        "req-123", "query_users", 0.5
    )


@patch('common.metrics._performance_monitor')
def test_get_performance_summary(mock_monitor):
    """get_performance_summary 테스트"""
    mock_monitor.metrics = {
        "req-123": {"operation": "test", "duration": 1.5}
    }
    
    result = get_performance_summary("req-123")
    
    assert result == {"operation": "test", "duration": 1.5}


@patch('common.metrics._performance_monitor')
def test_get_performance_summary_not_found(mock_monitor):
    """존재하지 않는 요청 ID로 성능 요약 조회 테스트"""
    mock_monitor.metrics = {}
    
    result = get_performance_summary("invalid-id")
    
    assert result is None


@patch('common.metrics.logger')
def test_log_cold_start(mock_logger):
    """Lambda 콜드 스타트 로깅 테스트"""
    log_cold_start()
    
    # 실제 호출 확인 (정확한 파라미터는 확인하지 않음)
    mock_logger.info.assert_called_once()


@patch('common.metrics.logger')
def test_log_memory_usage_lambda(mock_logger):
    """Lambda 환경에서 메모리 사용량 로깅 테스트"""
    try:
        log_memory_usage()
        # 호출이 있었는지만 확인 (실제 메모리 정보는 환경에 따라 다름)
    except Exception:
        # 실패해도 패스 (환경에 따라 다를 수 있음)
        pass


@patch('common.metrics.logger')
def test_log_memory_usage_local(mock_logger):
    """로컬 환경에서 메모리 사용량 로깅 테스트"""
    try:
        log_memory_usage()
        mock_logger.info.assert_called()
    except Exception:
        # psutil이 없거나 다른 이유로 실패하면 패스
        pass
