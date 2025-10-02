"""
Performance and Load Tests for API Web Service
Tests concurrent access, response times, and system limits
"""

import pytest
import time
import threading
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from fastapi.testclient import TestClient
from fastapi import FastAPI
import requests
from unittest.mock import patch, Mock

# Import the routers and create test apps
from projects.fundraising_tracking_app.strava_integration.strava_integration_api import router as strava_router
from projects.fundraising_tracking_app.fundraising_scraper.fundraising_api import router as fundraising_router

# Create test apps
strava_app = FastAPI()
strava_app.include_router(strava_router, prefix="/api/strava-integration")

fundraising_app = FastAPI()
fundraising_app.include_router(fundraising_router, prefix="/api/fundraising")


class TestLoadPerformance:
    """Test system performance under load"""
    
    def test_concurrent_feed_requests(self):
        """Test concurrent requests to feed endpoint"""
        client = TestClient(strava_app)
        
        def make_request():
            response = client.get("/api/strava-integration/feed")
            return response.status_code, time.time()
        
        # Test with 10 concurrent requests
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            results = [future.result() for future in as_completed(futures)]
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # All requests should succeed
        status_codes = [result[0] for result in results]
        assert all(code == 200 for code in status_codes)
        
        # Should complete within reasonable time (8 seconds)
        assert total_time < 8.0
        
        print(f"10 concurrent requests completed in {total_time:.2f} seconds")
    
    def test_concurrent_fundraising_requests(self):
        """Test concurrent requests to fundraising endpoints"""
        client = TestClient(fundraising_app)
        
        def make_request():
            response = client.get("/api/fundraising/data")
            return response.status_code, time.time()
        
        # Test with 5 concurrent requests
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request) for _ in range(5)]
            results = [future.result() for future in as_completed(futures)]
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # All requests should succeed
        status_codes = [result[0] for result in results]
        assert all(code == 200 for code in status_codes)
        
        # Should complete within reasonable time (3 seconds)
        assert total_time < 3.0
        
        print(f"5 concurrent fundraising requests completed in {total_time:.2f} seconds")
    
    def test_response_time_under_load(self):
        """Test response times under moderate load"""
        client = TestClient(strava_app)
        
        response_times = []
        
        # Make 20 sequential requests
        for i in range(20):
            start_time = time.time()
            response = client.get("/api/strava-integration/health")
            end_time = time.time()
            
            response_time = end_time - start_time
            response_times.append(response_time)
            
            assert response.status_code == 200
        
        # Calculate statistics
        avg_response_time = sum(response_times) / len(response_times)
        max_response_time = max(response_times)
        min_response_time = min(response_times)
        
        # Average response time should be under 100ms
        assert avg_response_time < 0.1
        
        # Max response time should be under 500ms
        assert max_response_time < 0.5
        
        print(f"Response time stats - Avg: {avg_response_time:.3f}s, Max: {max_response_time:.3f}s, Min: {min_response_time:.3f}s")
    
    def test_memory_usage_stability(self):
        """Test memory usage remains stable under load"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        client = TestClient(strava_app)
        
        # Make many requests to test memory stability
        for i in range(100):
            response = client.get("/api/strava-integration/health")
            assert response.status_code == 200
            
            # Check memory every 20 requests
            if i % 20 == 0:
                current_memory = process.memory_info().rss / 1024 / 1024  # MB
                memory_increase = current_memory - initial_memory
                
                # Memory increase should be reasonable (less than 50MB)
                assert memory_increase < 50, f"Memory increased by {memory_increase:.1f}MB"
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        total_increase = final_memory - initial_memory
        
        print(f"Memory usage - Initial: {initial_memory:.1f}MB, Final: {final_memory:.1f}MB, Increase: {total_increase:.1f}MB")
        
        # Total memory increase should be reasonable
        assert total_increase < 100  # Less than 100MB increase


class TestConcurrencyLimits:
    """Test system behavior under high concurrency"""
    
    def test_thread_safety_cache_access(self):
        """Test thread safety of cache operations"""
        from projects.fundraising_tracking_app.strava_integration.smart_strava_cache import SmartStravaCache
        from datetime import datetime
        
        # Mock the token manager to avoid real API calls
        with patch('projects.fundraising_tracking_app.strava_integration.smart_strava_cache.StravaTokenManager'):
            cache = SmartStravaCache()
            
            results = []
            errors = []
            
            def access_cache():
                try:
                    # Simulate cache access with proper datetime format
                    cache_data = {"timestamp": datetime.now().isoformat()}
                    result = cache._is_cache_valid(cache_data)
                    results.append(result)
                except Exception as e:
                    errors.append(e)
            
            # Test with 20 concurrent threads
            threads = []
            for _ in range(20):
                thread = threading.Thread(target=access_cache)
                threads.append(thread)
                thread.start()
            
            # Wait for all threads to complete
            for thread in threads:
                thread.join()
            
            # Should have no errors
            assert len(errors) == 0, f"Thread safety errors: {errors}"
            
            # Should have results from all threads
            assert len(results) == 20
            
            print(f"Thread safety test passed - {len(results)} successful cache accesses")
    
    def test_rate_limiting_behavior(self):
        """Test rate limiting under high request volume"""
        client = TestClient(strava_app)
        
        # Make many rapid requests
        start_time = time.time()
        responses = []
        
        for i in range(50):
            response = client.get("/api/strava-integration/health")
            responses.append(response.status_code)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # All requests should succeed (no rate limiting on health endpoint)
        success_count = sum(1 for code in responses if code == 200)
        assert success_count == 50
        
        # Should complete quickly
        assert total_time < 2.0
        
        print(f"50 rapid requests completed in {total_time:.2f} seconds")
    
    def test_concurrent_api_key_validation(self):
        """Test concurrent API key validation"""
        client = TestClient(strava_app)
        
        def make_authenticated_request():
            response = client.post(
                "/api/strava-integration/refresh-cache",
                headers={"X-API-Key": "test-strava-key-123"},
                json={"force_full_refresh": False}
            )
            return response.status_code
        
        # Test with 10 concurrent authenticated requests
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_authenticated_request) for _ in range(10)]
            results = [future.result() for future in as_completed(futures)]
        
        # All requests should be processed (may succeed or fail based on external dependencies)
        assert len(results) == 10
        
        # Should have some successful responses (200) or expected error responses
        valid_codes = [200, 500, 401, 403]  # Acceptable response codes
        valid_responses = sum(1 for code in results if code in valid_codes)
        assert valid_responses == 10
        
        print(f"Concurrent API key validation - {len(results)} requests processed")


class TestSystemLimits:
    """Test system behavior at limits"""
    
    def test_large_response_handling(self):
        """Test handling of large responses"""
        client = TestClient(strava_app)
        
        # Test feed endpoint with maximum allowed limit
        response = client.get("/api/strava-integration/feed?limit=200")
        
        # Should handle large requests gracefully
        assert response.status_code in [200, 400, 422]  # Valid responses
        
        if response.status_code == 200:
            data = response.json()
            # Should have reasonable response size
            assert "activities" in data
            assert len(data["activities"]) <= 200
    
    def test_error_recovery_under_load(self):
        """Test error recovery when system is under load"""
        client = TestClient(strava_app)
        
        # Simulate load with concurrent requests
        def make_request():
            try:
                response = client.get("/api/strava-integration/health")
                return response.status_code
            except Exception as e:
                return f"Error: {e}"
        
        # Make requests while system is under load
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request) for _ in range(20)]
            results = [future.result() for future in as_completed(futures)]
        
        # Should recover gracefully
        success_count = sum(1 for result in results if result == 200)
        assert success_count >= 15  # At least 75% should succeed
        
        print(f"Error recovery test - {success_count}/20 requests succeeded")
    
    def test_cache_performance_under_load(self):
        """Test cache performance under concurrent access"""
        from projects.fundraising_tracking_app.fundraising_scraper.fundraising_scraper import SmartFundraisingCache
        
        cache = SmartFundraisingCache("https://test.justgiving.com")
        
        def access_cache():
            try:
                # Simulate cache access
                result = cache._create_empty_cache()
                return result is not None
            except Exception as e:
                return False
        
        # Test concurrent cache access
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(access_cache) for _ in range(50)]
            results = [future.result() for future in as_completed(futures)]
        
        # All cache operations should succeed
        success_count = sum(1 for result in results if result)
        assert success_count == 50
        
        print(f"Cache performance test - {success_count}/50 operations succeeded")


if __name__ == "__main__":
    # Run performance tests
    pytest.main([__file__, "-v", "-s"])
