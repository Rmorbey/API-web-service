"""
Simple unit tests for metrics collection and monitoring system
Tests core functionality without complex mocking
"""

import pytest
import time
import threading
from unittest.mock import Mock, patch

from projects.fundraising_tracking_app.activity_integration.metrics import (
    MetricsCollector,
    RequestMetric,
    SystemMetric
)


class TestRequestMetric:
    """Test RequestMetric dataclass"""
    
    def test_request_metric_creation(self):
        """Test RequestMetric creation with all parameters"""
        metric = RequestMetric(
            timestamp=1234567890.0,
            endpoint="/api/test",
            method="GET",
            status_code=200,
            response_time=0.5,
            client_ip="127.0.0.1",
            user_agent="test-agent",
            cache_hit=True,
            error_message=None
        )
        
        assert metric.timestamp == 1234567890.0
        assert metric.endpoint == "/api/test"
        assert metric.method == "GET"
        assert metric.status_code == 200
        assert metric.response_time == 0.5
        assert metric.client_ip == "127.0.0.1"
        assert metric.user_agent == "test-agent"
        assert metric.cache_hit is True
        assert metric.error_message is None
    
    def test_request_metric_creation_minimal(self):
        """Test RequestMetric creation with minimal parameters"""
        metric = RequestMetric(
            timestamp=1234567890.0,
            endpoint="/api/test",
            method="GET",
            status_code=200,
            response_time=0.5,
            client_ip="127.0.0.1",
            user_agent="test-agent"
        )
        
        assert metric.cache_hit is False  # Default value
        assert metric.error_message is None  # Default value


class TestSystemMetric:
    """Test SystemMetric dataclass"""
    
    def test_system_metric_creation(self):
        """Test SystemMetric creation"""
        metric = SystemMetric(
            timestamp=1234567890.0,
            cpu_percent=25.5,
            memory_percent=60.0,
            memory_used_mb=1024.0,
            memory_available_mb=2048.0,
            disk_usage_percent=45.0,
            active_connections=10,
            cache_size=100,
            cache_hit_ratio=0.85
        )
        
        assert metric.timestamp == 1234567890.0
        assert metric.cpu_percent == 25.5
        assert metric.memory_percent == 60.0
        assert metric.memory_used_mb == 1024.0
        assert metric.memory_available_mb == 2048.0
        assert metric.disk_usage_percent == 45.0
        assert metric.active_connections == 10
        assert metric.cache_size == 100
        assert metric.cache_hit_ratio == 0.85


class TestMetricsCollector:
    """Test MetricsCollector class"""
    
    def test_metrics_collector_init(self):
        """Test MetricsCollector initialization"""
        collector = MetricsCollector()
        
        assert collector.max_requests == 10000
        assert collector.max_system_metrics == 1000
        assert len(collector.request_metrics) == 0
        assert len(collector.system_metrics) == 0
        assert collector.lock is not None
        assert hasattr(collector.lock, 'acquire')  # Check it's a lock-like object
    
    def test_metrics_collector_init_custom_max(self):
        """Test MetricsCollector initialization with custom max values"""
        collector = MetricsCollector(max_requests=500, max_system_metrics=100)
        
        assert collector.max_requests == 500
        assert collector.max_system_metrics == 100
        assert len(collector.request_metrics) == 0
        assert len(collector.system_metrics) == 0
    
    def test_record_request(self):
        """Test recording a request metric"""
        collector = MetricsCollector()
        
        collector.record_request(
            endpoint="/api/test",
            method="GET",
            status_code=200,
            response_time=0.5,
            client_ip="127.0.0.1",
            user_agent="test-agent"
        )
        
        assert len(collector.request_metrics) == 1
        metric = collector.request_metrics[0]
        assert metric.endpoint == "/api/test"
        assert metric.method == "GET"
        assert metric.status_code == 200
        assert metric.response_time == 0.5
        assert metric.client_ip == "127.0.0.1"
        assert metric.user_agent == "test-agent"
    
    def test_record_request_multiple(self):
        """Test recording multiple request metrics"""
        collector = MetricsCollector()
        
        for i in range(5):
            collector.record_request(
                endpoint=f"/api/test{i}",
                method="GET",
                status_code=200,
                response_time=0.5,
                client_ip="127.0.0.1",
                user_agent="test-agent"
            )
        
        assert len(collector.request_metrics) == 5
        for i, metric in enumerate(collector.request_metrics):
            assert metric.endpoint == f"/api/test{i}"
    
    def test_record_request_with_cache_hit(self):
        """Test recording a request metric with cache hit"""
        collector = MetricsCollector()
        
        collector.record_request(
            endpoint="/api/test",
            method="GET",
            status_code=200,
            response_time=0.1,
            client_ip="127.0.0.1",
            user_agent="test-agent",
            cache_hit=True
        )
        
        assert len(collector.request_metrics) == 1
        metric = collector.request_metrics[0]
        assert metric.cache_hit is True
        assert metric.response_time == 0.1
    
    def test_record_request_with_error(self):
        """Test recording a request metric with error"""
        collector = MetricsCollector()
        
        collector.record_request(
            endpoint="/api/test",
            method="GET",
            status_code=500,
            response_time=2.0,
            client_ip="127.0.0.1",
            user_agent="test-agent",
            error_message="Internal server error"
        )
        
        assert len(collector.request_metrics) == 1
        metric = collector.request_metrics[0]
        assert metric.status_code == 500
        assert metric.error_message == "Internal server error"
    
    def test_record_system_metric(self):
        """Test recording a system metric"""
        collector = MetricsCollector()
        
        # Mock psutil to prevent real system calls
        with patch('psutil.cpu_percent', return_value=25.0), \
             patch('psutil.virtual_memory') as mock_memory, \
             patch('psutil.disk_usage') as mock_disk, \
             patch('psutil.net_connections', return_value=[]):
            
            # Mock memory object
            mock_memory.return_value.percent = 50.0
            mock_memory.return_value.used = 1024 * 1024 * 100  # 100MB
            mock_memory.return_value.available = 1024 * 1024 * 200  # 200MB
            
            # Mock disk object
            mock_disk.return_value.percent = 75.0
            
            collector.record_system_metric(
                cache_size=100,
                cache_hit_ratio=0.85
            )
            
            assert len(collector.system_metrics) == 1
            metric = collector.system_metrics[0]
            assert metric.cache_size == 100
            assert metric.cache_hit_ratio == 0.85
            assert metric.timestamp > 0  # Should have a timestamp
    
    def test_get_request_stats(self):
        """Test getting request statistics"""
        collector = MetricsCollector()
        
        # Add some test metrics
        collector.record_request("/api/test1", "GET", 200, 0.5, "127.0.0.1", "test-agent")
        collector.record_request("/api/test1", "GET", 200, 0.3, "127.0.0.1", "test-agent")
        collector.record_request("/api/test2", "POST", 201, 0.8, "127.0.0.1", "test-agent")
        collector.record_request("/api/test1", "GET", 404, 0.1, "127.0.0.1", "test-agent")
        
        stats = collector.get_request_stats()
        
        assert "total_requests" in stats
        assert "avg_response_time" in stats
        assert "endpoints" in stats
        
        assert stats["total_requests"] == 4
        assert stats["avg_response_time"] == (0.5 + 0.3 + 0.8 + 0.1) / 4
        
        # Check endpoint stats
        assert "/api/test1" in stats["endpoints"]
        assert "/api/test2" in stats["endpoints"]
        assert stats["endpoints"]["/api/test1"]["requests"] == 3
        assert stats["endpoints"]["/api/test2"]["requests"] == 1
        
        # Check error rates
        assert stats["endpoints"]["/api/test1"]["error_rate"] == 1/3  # 1 error out of 3 requests
        assert stats["endpoints"]["/api/test2"]["error_rate"] == 0  # No errors
    
    def test_get_request_stats_empty(self):
        """Test getting request statistics with no metrics"""
        collector = MetricsCollector()
        
        stats = collector.get_request_stats()
        
        assert stats["total_requests"] == 0
        assert stats["avg_response_time"] == 0.0
        assert len(stats["endpoints"]) == 0
    
    def test_get_system_stats(self):
        """Test getting system statistics"""
        collector = MetricsCollector()
        
        # Mock psutil to prevent real system calls
        with patch('psutil.cpu_percent', return_value=25.0), \
             patch('psutil.virtual_memory') as mock_memory, \
             patch('psutil.disk_usage') as mock_disk, \
             patch('psutil.net_connections', return_value=[]):
            
            # Mock memory object
            mock_memory.return_value.percent = 50.0
            mock_memory.return_value.used = 1024 * 1024 * 100  # 100MB
            mock_memory.return_value.available = 1024 * 1024 * 200  # 200MB
            
            # Mock disk object
            mock_disk.return_value.percent = 75.0
            
            # Add some test metrics
            collector.record_system_metric(cache_size=100, cache_hit_ratio=0.8)
            collector.record_system_metric(cache_size=150, cache_hit_ratio=0.85)
            collector.record_system_metric(cache_size=200, cache_hit_ratio=0.9)
            
            stats = collector.get_system_stats()
            
            assert "uptime_seconds" in stats
            assert "current_cpu" in stats
            assert "current_memory" in stats
    
    def test_get_system_stats_empty(self):
        """Test getting system statistics with no metrics"""
        collector = MetricsCollector()
        
        stats = collector.get_system_stats()
        
        assert "uptime_seconds" in stats
        assert stats["current_cpu"] == 0.0
        assert stats["current_memory"] == 0.0
    
    def test_get_health_score(self):
        """Test getting health score"""
        collector = MetricsCollector()
        
        # Add some test metrics
        collector.record_request("/api/test", "GET", 200, 0.5, "127.0.0.1", "test-agent")
        collector.record_system_metric(cache_size=100, cache_hit_ratio=0.85)
        
        health_score = collector.get_health_score()
        
        assert "overall_score" in health_score
        assert "status" in health_score
        assert "factors" in health_score
        assert "recommendations" in health_score
        
        # Scores should be between 0 and 100
        assert 0 <= health_score["overall_score"] <= 100
        
        # Status should be one of the expected values
        assert health_score["status"] in ["excellent", "good", "fair", "poor", "critical"]
    
    def test_clear_old_metrics(self):
        """Test clearing old metrics"""
        collector = MetricsCollector()
        
        # Add some metrics
        for i in range(5):
            collector.record_request(
                endpoint=f"/api/test{i}",
                method="GET",
                status_code=200,
                response_time=0.5,
                client_ip="127.0.0.1",
                user_agent="test-agent"
            )
        
        assert len(collector.request_metrics) == 5
        
        # Clear metrics older than 1 hour (should clear all since they're recent)
        cleared = collector.clear_old_metrics(max_age_hours=1)
        
        # Should not clear any metrics since they're recent
        assert cleared == 0
        assert len(collector.request_metrics) == 5


class TestEdgeCases:
    """Test edge cases and error conditions"""
    
    def test_metrics_collector_zero_max_requests(self):
        """Test MetricsCollector with zero max_requests"""
        collector = MetricsCollector(max_requests=0, max_system_metrics=0)
        
        assert collector.max_requests == 0
        assert collector.max_system_metrics == 0
        
        collector.record_request(
            endpoint="/api/test",
            method="GET",
            status_code=200,
            response_time=0.5,
            client_ip="127.0.0.1",
            user_agent="test-agent"
        )
        
        # With zero max, the deque should not accept any items
        assert len(collector.request_metrics) == 0
    
    def test_record_request_zero_response_time(self):
        """Test recording request with zero response time"""
        collector = MetricsCollector()
        
        collector.record_request(
            endpoint="/api/test",
            method="GET",
            status_code=200,
            response_time=0.0,
            client_ip="127.0.0.1",
            user_agent="test-agent"
        )
        
        assert len(collector.request_metrics) == 1
        metric = collector.request_metrics[0]
        assert metric.response_time == 0.0
    
    def test_record_request_very_large_response_time(self):
        """Test recording request with very large response time"""
        collector = MetricsCollector()
        
        collector.record_request(
            endpoint="/api/test",
            method="GET",
            status_code=200,
            response_time=999999.0,
            client_ip="127.0.0.1",
            user_agent="test-agent"
        )
        
        assert len(collector.request_metrics) == 1
        metric = collector.request_metrics[0]
        assert metric.response_time == 999999.0
    
    def test_record_system_metric_zero_values(self):
        """Test recording system metric with zero values"""
        collector = MetricsCollector()
        
        # Mock psutil to prevent real system calls
        with patch('psutil.cpu_percent', return_value=0.0), \
             patch('psutil.virtual_memory') as mock_memory, \
             patch('psutil.disk_usage') as mock_disk, \
             patch('psutil.net_connections', return_value=[]):
            
            # Mock memory object
            mock_memory.return_value.percent = 0.0
            mock_memory.return_value.used = 0
            mock_memory.return_value.available = 1024 * 1024 * 100
            
            # Mock disk object
            mock_disk.return_value.percent = 0.0
            
            collector.record_system_metric(
                cache_size=0,
                cache_hit_ratio=0.0
            )
            
            assert len(collector.system_metrics) == 1
            metric = collector.system_metrics[0]
            assert metric.cache_size == 0
            assert metric.cache_hit_ratio == 0.0
    
    def test_record_system_metric_max_values(self):
        """Test recording system metric with maximum values"""
        collector = MetricsCollector()
        
        # Mock psutil to prevent real system calls
        with patch('psutil.cpu_percent', return_value=100.0), \
             patch('psutil.virtual_memory') as mock_memory, \
             patch('psutil.disk_usage') as mock_disk, \
             patch('psutil.net_connections', return_value=[]):
            
            # Mock memory object
            mock_memory.return_value.percent = 100.0
            mock_memory.return_value.used = 1024 * 1024 * 1000  # 1GB
            mock_memory.return_value.available = 0
            
            # Mock disk object
            mock_disk.return_value.percent = 100.0
            
            collector.record_system_metric(
                cache_size=999999,
                cache_hit_ratio=1.0
            )
            
            assert len(collector.system_metrics) == 1
            metric = collector.system_metrics[0]
            assert metric.cache_size == 999999
            assert metric.cache_hit_ratio == 1.0
    
    def test_thread_safety(self):
        """Test thread safety of metrics collection"""
        collector = MetricsCollector()
        
        def add_metrics():
            for i in range(100):
                collector.record_request(
                    endpoint=f"/api/test{i}",
                    method="GET",
                    status_code=200,
                    response_time=0.5,
                    client_ip="127.0.0.1",
                    user_agent="test-agent"
                )
        
        # Create multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=add_metrics)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Should have exactly 500 metrics (5 threads * 100 metrics each)
        assert len(collector.request_metrics) == 500
