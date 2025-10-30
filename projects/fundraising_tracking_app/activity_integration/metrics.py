"""
Comprehensive metrics collection and monitoring system
"""

import time
import logging
import threading
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict, deque
from dataclasses import dataclass, asdict
import psutil
import os

logger = logging.getLogger(__name__)


@dataclass
class RequestMetric:
    """Individual request metric"""
    timestamp: float
    endpoint: str
    method: str
    status_code: int
    response_time: float
    client_ip: str
    user_agent: str
    cache_hit: bool = False
    error_message: Optional[str] = None


@dataclass
class SystemMetric:
    """System performance metric"""
    timestamp: float
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_available_mb: float
    disk_usage_percent: float
    active_connections: int
    cache_size: int
    cache_hit_ratio: float


class MetricsCollector:
    """Centralized metrics collection and aggregation"""
    
    def __init__(self, max_requests: int = 10000, max_system_metrics: int = 1000):
        self.max_requests = max_requests
        self.max_system_metrics = max_system_metrics
        
        # Request metrics
        self.request_metrics = deque(maxlen=max_requests)
        self.endpoint_stats = defaultdict(lambda: {
            "total_requests": 0,
            "total_response_time": 0.0,
            "status_codes": defaultdict(int),
            "cache_hits": 0,
            "errors": 0
        })
        
        # System metrics
        self.system_metrics = deque(maxlen=max_system_metrics)
        self.start_time = time.time()
        
        # Thread safety
        self.lock = threading.RLock()
        
        # Start background collection
        self._start_background_collection()
    
    def record_request(
        self,
        endpoint: str,
        method: str,
        status_code: int,
        response_time: float,
        client_ip: str,
        user_agent: str,
        cache_hit: bool = False,
        error_message: Optional[str] = None
    ) -> None:
        """Record a request metric"""
        with self.lock:
            metric = RequestMetric(
                timestamp=time.time(),
                endpoint=endpoint,
                method=method,
                status_code=status_code,
                response_time=response_time,
                client_ip=client_ip,
                user_agent=user_agent,
                cache_hit=cache_hit,
                error_message=error_message
            )
            
            self.request_metrics.append(metric)
            
            # Update endpoint statistics
            stats = self.endpoint_stats[endpoint]
            stats["total_requests"] += 1
            stats["total_response_time"] += response_time
            stats["status_codes"][status_code] += 1
            
            if cache_hit:
                stats["cache_hits"] += 1
            
            if status_code >= 400:
                stats["errors"] += 1
    
    def record_system_metric(self, cache_size: int, cache_hit_ratio: float) -> None:
        """Record system performance metric"""
        try:
            # Get system information
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Count active connections (approximate)
            connections = len(psutil.net_connections())
            
            metric = SystemMetric(
                timestamp=time.time(),
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                memory_used_mb=memory.used / (1024 * 1024),
                memory_available_mb=memory.available / (1024 * 1024),
                disk_usage_percent=disk.percent,
                active_connections=connections,
                cache_size=cache_size,
                cache_hit_ratio=cache_hit_ratio
            )
            
            with self.lock:
                self.system_metrics.append(metric)
                
        except Exception as e:
            logger.error(f"Failed to collect system metrics: {e}")
    
    def _start_background_collection(self) -> None:
        """Start background system metrics collection"""
        def collect_loop():
            while True:
                try:
                    # Get cache stats (if available)
                    cache_size = 0
                    cache_hit_ratio = 0.0
                    
                    # This would be updated by the cache system
                    self.record_system_metric(cache_size, cache_hit_ratio)
                    
                    # Collect every 30 seconds
                    time.sleep(30)
                except Exception as e:
                    logger.error(f"Background metrics collection error: {e}")
                    time.sleep(60)
        
        thread = threading.Thread(target=collect_loop, daemon=True)
        thread.start()
    
    def get_request_stats(self, time_window: int = 3600) -> Dict[str, Any]:
        """Get request statistics for time window"""
        with self.lock:
            now = time.time()
            cutoff = now - time_window
            
            # Filter recent requests
            recent_requests = [
                req for req in self.request_metrics
                if req.timestamp >= cutoff
            ]
            
            if not recent_requests:
                return {
                    "total_requests": 0,
                    "avg_response_time": 0.0,
                    "error_rate": 0.0,
                    "cache_hit_rate": 0.0,
                    "endpoints": {}
                }
            
            # Calculate overall stats
            total_requests = len(recent_requests)
            total_response_time = sum(req.response_time for req in recent_requests)
            error_requests = sum(1 for req in recent_requests if req.status_code >= 400)
            cache_hits = sum(1 for req in recent_requests if req.cache_hit)
            
            # Calculate endpoint-specific stats
            endpoint_stats = {}
            for req in recent_requests:
                if req.endpoint not in endpoint_stats:
                    endpoint_stats[req.endpoint] = {
                        "requests": 0,
                        "total_response_time": 0.0,
                        "errors": 0,
                        "cache_hits": 0
                    }
                
                stats = endpoint_stats[req.endpoint]
                stats["requests"] += 1
                stats["total_response_time"] += req.response_time
                if req.status_code >= 400:
                    stats["errors"] += 1
                if req.cache_hit:
                    stats["cache_hits"] += 1
            
            # Calculate averages
            for stats in endpoint_stats.values():
                if stats["requests"] > 0:
                    stats["avg_response_time"] = stats["total_response_time"] / stats["requests"]
                    stats["error_rate"] = stats["errors"] / stats["requests"]
                    stats["cache_hit_rate"] = stats["cache_hits"] / stats["requests"]
            
            return {
                "total_requests": total_requests,
                "avg_response_time": total_response_time / total_requests if total_requests > 0 else 0.0,
                "error_rate": error_requests / total_requests if total_requests > 0 else 0.0,
                "cache_hit_rate": cache_hits / total_requests if total_requests > 0 else 0.0,
                "endpoints": endpoint_stats,
                "time_window_seconds": time_window
            }
    
    def get_system_stats(self, time_window: int = 3600) -> Dict[str, Any]:
        """Get system performance statistics"""
        with self.lock:
            now = time.time()
            cutoff = now - time_window
            
            # Filter recent system metrics
            recent_metrics = [
                metric for metric in self.system_metrics
                if metric.timestamp >= cutoff
            ]
            
            if not recent_metrics:
                return {
                    "uptime_seconds": time.time() - self.start_time,
                    "current_cpu": 0.0,
                    "current_memory": 0.0,
                    "avg_cpu": 0.0,
                    "avg_memory": 0.0,
                    "max_cpu": 0.0,
                    "max_memory": 0.0
                }
            
            # Calculate statistics
            cpu_values = [m.cpu_percent for m in recent_metrics]
            memory_values = [m.memory_percent for m in recent_metrics]
            
            return {
                "uptime_seconds": time.time() - self.start_time,
                "current_cpu": cpu_values[-1] if cpu_values else 0.0,
                "current_memory": memory_values[-1] if memory_values else 0.0,
                "avg_cpu": sum(cpu_values) / len(cpu_values) if cpu_values else 0.0,
                "avg_memory": sum(memory_values) / len(memory_values) if memory_values else 0.0,
                "max_cpu": max(cpu_values) if cpu_values else 0.0,
                "max_memory": max(memory_values) if memory_values else 0.0,
                "samples": len(recent_metrics),
                "time_window_seconds": time_window
            }
    
    def get_health_score(self) -> Dict[str, Any]:
        """Calculate overall health score"""
        request_stats = self.get_request_stats(300)  # Last 5 minutes
        system_stats = self.get_system_stats(300)
        
        # Health scoring (0-100)
        health_factors = []
        
        # Response time factor (0-25 points)
        avg_response_time = request_stats.get("avg_response_time", 0)
        if avg_response_time < 0.1:
            health_factors.append(25)
        elif avg_response_time < 0.5:
            health_factors.append(20)
        elif avg_response_time < 1.0:
            health_factors.append(15)
        elif avg_response_time < 2.0:
            health_factors.append(10)
        else:
            health_factors.append(5)
        
        # Error rate factor (0-25 points)
        error_rate = request_stats.get("error_rate", 0)
        if error_rate < 0.01:
            health_factors.append(25)
        elif error_rate < 0.05:
            health_factors.append(20)
        elif error_rate < 0.1:
            health_factors.append(15)
        elif error_rate < 0.2:
            health_factors.append(10)
        else:
            health_factors.append(5)
        
        # CPU usage factor (0-25 points)
        current_cpu = system_stats.get("current_cpu", 0)
        if current_cpu < 50:
            health_factors.append(25)
        elif current_cpu < 70:
            health_factors.append(20)
        elif current_cpu < 85:
            health_factors.append(15)
        elif current_cpu < 95:
            health_factors.append(10)
        else:
            health_factors.append(5)
        
        # Memory usage factor (0-25 points)
        current_memory = system_stats.get("current_memory", 0)
        if current_memory < 70:
            health_factors.append(25)
        elif current_memory < 80:
            health_factors.append(20)
        elif current_memory < 90:
            health_factors.append(15)
        elif current_memory < 95:
            health_factors.append(10)
        else:
            health_factors.append(5)
        
        total_score = sum(health_factors)
        
        # Determine health status
        if total_score >= 90:
            status = "excellent"
        elif total_score >= 75:
            status = "good"
        elif total_score >= 60:
            status = "fair"
        elif total_score >= 40:
            status = "poor"
        else:
            status = "critical"
        
        return {
            "overall_score": total_score,
            "status": status,
            "factors": {
                "response_time": health_factors[0],
                "error_rate": health_factors[1],
                "cpu_usage": health_factors[2],
                "memory_usage": health_factors[3]
            },
            "recommendations": self._get_recommendations(total_score, request_stats, system_stats)
        }
    
    def _get_recommendations(self, score: int, request_stats: Dict, system_stats: Dict) -> List[str]:
        """Get performance recommendations based on metrics"""
        recommendations = []
        
        if request_stats.get("avg_response_time", 0) > 1.0:
            recommendations.append("Consider implementing response caching for slow endpoints")
        
        if request_stats.get("error_rate", 0) > 0.05:
            recommendations.append("High error rate detected - investigate error sources")
        
        if system_stats.get("current_cpu", 0) > 80:
            recommendations.append("High CPU usage - consider scaling or optimization")
        
        if system_stats.get("current_memory", 0) > 85:
            recommendations.append("High memory usage - consider memory optimization")
        
        if request_stats.get("cache_hit_rate", 0) < 0.3:
            recommendations.append("Low cache hit rate - review caching strategy")
        
        if not recommendations:
            recommendations.append("System performance is optimal")
        
        return recommendations
    
    def clear_old_metrics(self, max_age_hours: int = 24) -> int:
        """Clear metrics older than specified age"""
        with self.lock:
            cutoff = time.time() - (max_age_hours * 3600)
            
            # Clear old request metrics
            old_requests = sum(1 for req in self.request_metrics if req.timestamp < cutoff)
            self.request_metrics = deque(
                [req for req in self.request_metrics if req.timestamp >= cutoff],
                maxlen=self.max_requests
            )
            
            # Clear old system metrics
            old_system = sum(1 for metric in self.system_metrics if metric.timestamp < cutoff)
            self.system_metrics = deque(
                [metric for metric in self.system_metrics if metric.timestamp >= cutoff],
                maxlen=self.max_system_metrics
            )
            
            total_cleared = old_requests + old_system
            logger.info(f"Cleared {total_cleared} old metrics (older than {max_age_hours}h)")
            return total_cleared


# Global metrics collector instance
metrics_collector = MetricsCollector()


def record_request_metric(
    endpoint: str,
    method: str,
    status_code: int,
    response_time: float,
    client_ip: str,
    user_agent: str,
    cache_hit: bool = False,
    error_message: Optional[str] = None
) -> None:
    """Record a request metric"""
    metrics_collector.record_request(
        endpoint, method, status_code, response_time,
        client_ip, user_agent, cache_hit, error_message
    )


def get_metrics_summary() -> Dict[str, Any]:
    """Get comprehensive metrics summary"""
    return {
        "requests": metrics_collector.get_request_stats(),
        "system": metrics_collector.get_system_stats(),
        "health": metrics_collector.get_health_score()
    }
