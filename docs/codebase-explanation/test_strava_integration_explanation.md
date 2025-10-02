# 📚 test_strava_integration.py - Complete Code Explanation

## 🎯 **Overview**

This file contains **comprehensive tests** for the Strava integration functionality and Strava API endpoints used throughout the system. It tests Strava API logic, Strava API performance, Strava API integration, and Strava API configuration to ensure the system handles Strava API requests correctly and efficiently. Think of it as the **Strava integration quality assurance** that verifies your Strava API system works properly.

## 📁 **File Structure Context**

```
test_strava_integration.py  ← YOU ARE HERE (Strava Integration Tests)
├── strava_integration_api.py      (Strava API)
├── smart_strava_cache.py          (Strava cache)
├── security.py                    (Security middleware)
├── compression_middleware.py      (Compression middleware)
└── simple_error_handlers.py       (Error handling middleware)
```

## 🔍 **Line-by-Line Code Explanation

### **1. Imports and Setup (Lines 1-25)**

```python
#!/usr/bin/env python3
"""
Comprehensive Test Suite for Strava Integration Functionality
Tests all Strava integration features and Strava API endpoints
"""

import pytest
import asyncio
import json
import time
import os
import tempfile
from unittest.mock import patch, MagicMock, AsyncMock
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from strava_integration_api import app
```

**What this does:**
- **Test framework**: Uses pytest for testing
- **Async support**: Imports asyncio for async testing
- **Timing**: Imports time for performance measurement
- **Temporary files**: Imports tempfile for temporary file handling
- **Mocking**: Imports unittest.mock for mocking
- **Path management**: Adds project root to Python path
- **App import**: Imports the Strava integration FastAPI application

### **2. Test Configuration (Lines 27-50)**

```python
# Test configuration
TEST_API_KEY = "test_api_key_123"
TEST_FRONTEND_TOKEN = "test_frontend_token_456"

# Set test environment variables
os.environ.update({
    "API_KEY": TEST_API_KEY,
    "FRONTEND_ACCESS_TOKEN": TEST_FRONTEND_TOKEN,
    "ALLOWED_ORIGINS": "http://localhost:3000,https://test.com",
    "ENVIRONMENT": "test",
    "STRAVA_CLIENT_ID": "test_client_id",
    "STRAVA_CLIENT_SECRET": "test_client_secret",
    "STRAVA_ACCESS_TOKEN": "test_access_token",
    "JUSTGIVING_URL": "https://test.justgiving.com/test"
})

# Create test client
client = TestClient(app)
```

**What this does:**
- **Test credentials**: Sets up test API keys and tokens
- **Environment setup**: Configures test environment variables
- **Test client**: Creates FastAPI test client for testing

### **3. Strava API Test Data (Lines 52-100)**

```python
# Strava API test data
SAMPLE_ACTIVITY = {
    "id": 12345,
    "name": "Test Run",
    "type": "Run",
    "start_date_local": "2024-01-01T10:00:00Z",
    "distance": 5000.0,
    "moving_time": 1800,
    "total_elevation_gain": 100.0,
    "polyline": "test_polyline_data",
    "bounds": [51.5074, -0.1278, 51.5074, -0.1278]
}

SAMPLE_ACTIVITIES = [
    {
        "id": 1,
        "name": "Morning Run",
        "type": "Run",
        "start_date_local": "2024-01-01T08:00:00Z",
        "distance": 5000.0,
        "moving_time": 1800,
        "total_elevation_gain": 100.0,
        "polyline": "test_polyline_1",
        "bounds": [51.5074, -0.1278, 51.5074, -0.1278]
    },
    {
        "id": 2,
        "name": "Evening Bike Ride",
        "type": "Ride",
        "start_date_local": "2024-01-01T18:00:00Z",
        "distance": 15000.0,
        "moving_time": 3600,
        "total_elevation_gain": 200.0,
        "polyline": "test_polyline_2",
        "bounds": [51.5074, -0.1278, 51.5074, -0.1278]
    }
]

SAMPLE_METRICS = {
    "timestamp": "2024-01-01T10:00:00Z",
    "api_calls": {
        "total_made": 150,
        "max_per_15min": 100,
        "max_per_day": 1000,
        "reset_time": "2024-01-01T00:00:00Z"
    },
    "cache": {
        "in_memory_active": True,
        "cache_ttl": 3600,
        "cache_duration_hours": 1
    }
}
```

**What this does:**
- **Sample activity**: Defines sample activity data for testing
- **Sample activities**: Defines sample activities list for testing
- **Sample metrics**: Defines sample metrics data for testing
- **Realistic data**: Uses realistic Strava data structures

### **4. Basic Strava API Tests (Lines 102-160)**

```python
class TestBasicStravaAPI:
    """Test basic Strava API functionality"""
    
    def test_strava_api_initialization(self):
        """Test Strava API initialization"""
        # Test that Strava API can be initialized
        assert app is not None
        assert hasattr(app, 'routes')
        
        print("✓ Strava API initialization works")
    
    def test_strava_health_endpoint(self):
        """Test Strava health endpoint"""
        # Test that Strava health endpoint works
        response = client.get(
            "/api/strava-integration/health",
            headers={"X-API-Key": TEST_API_KEY}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "project" in data
        assert data["project"] == "strava-integration"
        
        print("✓ Strava health endpoint works")
    
    def test_strava_feed_endpoint(self):
        """Test Strava feed endpoint"""
        # Test that Strava feed endpoint works
        response = client.get(
            "/api/strava-integration/feed",
            headers={
                "X-API-Key": TEST_API_KEY,
                "Referer": "https://test.com"
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "activities" in data
        
        print("✓ Strava feed endpoint works")
    
    def test_strava_metrics_endpoint(self):
        """Test Strava metrics endpoint"""
        # Test that Strava metrics endpoint works
        response = client.get(
            "/api/strava-integration/metrics",
            headers={"X-API-Key": TEST_API_KEY}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "api_calls" in data
        assert "cache" in data
        
        print("✓ Strava metrics endpoint works")
    
    def test_strava_refresh_cache_endpoint(self):
        """Test Strava refresh cache endpoint"""
        # Test that Strava refresh cache endpoint works
        response = client.post(
            "/api/strava-integration/refresh-cache",
            headers={"X-API-Key": TEST_API_KEY},
            json={"force_full_refresh": False}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "success" in data
        
        print("✓ Strava refresh cache endpoint works")
```

**What this does:**
- **Strava API initialization**: Tests Strava API initialization
- **Strava health endpoint**: Tests Strava health endpoint
- **Strava feed endpoint**: Tests Strava feed endpoint
- **Strava metrics endpoint**: Tests Strava metrics endpoint
- **Strava refresh cache endpoint**: Tests Strava refresh cache endpoint

### **5. Strava Cache Tests (Lines 162-220)**

```python
class TestStravaCache:
    """Test Strava cache functionality"""
    
    def test_strava_cache_initialization(self):
        """Test Strava cache initialization"""
        # Test that Strava cache can be initialized
        from smart_strava_cache import SmartStravaCache
        
        cache = SmartStravaCache()
        assert cache is not None
        assert hasattr(cache, 'get_activities_smart')
        
        print("✓ Strava cache initialization works")
    
    def test_strava_cache_get_activities(self):
        """Test Strava cache get activities"""
        # Test that Strava cache can get activities
        from smart_strava_cache import SmartStravaCache
        
        cache = SmartStravaCache()
        activities = cache.get_activities_smart(limit=10)
        
        assert isinstance(activities, list)
        
        print("✓ Strava cache get activities works")
    
    def test_strava_cache_force_refresh(self):
        """Test Strava cache force refresh"""
        # Test that Strava cache can force refresh
        from smart_strava_cache import SmartStravaCache
        
        cache = SmartStravaCache()
        success = cache.force_refresh_now(force_full_refresh=False)
        
        assert isinstance(success, bool)
        
        print("✓ Strava cache force refresh works")
    
    def test_strava_cache_cleanup_backups(self):
        """Test Strava cache cleanup backups"""
        # Test that Strava cache can cleanup backups
        from smart_strava_cache import SmartStravaCache
        
        cache = SmartStravaCache()
        success = cache.cleanup_backups(keep_last_n=5)
        
        assert isinstance(success, bool)
        
        print("✓ Strava cache cleanup backups works")
    
    def test_strava_cache_clean_invalid_activities(self):
        """Test Strava cache clean invalid activities"""
        # Test that Strava cache can clean invalid activities
        from smart_strava_cache import SmartStravaCache
        
        cache = SmartStravaCache()
        result = cache.clean_invalid_activities()
        
        assert isinstance(result, dict)
        assert "cleaned_count" in result
        
        print("✓ Strava cache clean invalid activities works")
```

**What this does:**
- **Strava cache initialization**: Tests Strava cache initialization
- **Strava cache get activities**: Tests Strava cache get activities
- **Strava cache force refresh**: Tests Strava cache force refresh
- **Strava cache cleanup backups**: Tests Strava cache cleanup backups
- **Strava cache clean invalid activities**: Tests Strava cache clean invalid activities

### **6. Strava API Performance Tests (Lines 222-280)**

```python
class TestStravaAPIPerformance:
    """Test Strava API performance functionality"""
    
    def test_strava_api_response_time(self):
        """Test Strava API response time"""
        # Test that Strava API responds quickly
        start_time = time.time()
        
        response = client.get(
            "/api/strava-integration/health",
            headers={"X-API-Key": TEST_API_KEY}
        )
        
        end_time = time.time()
        response_time = end_time - start_time
        
        assert response.status_code == 200
        assert response_time < 1.0  # Should be under 1 second
        
        print(f"✓ Strava API response time: {response_time:.3f}s")
    
    def test_strava_api_concurrent_requests(self):
        """Test Strava API concurrent requests"""
        import threading
        import queue
        
        # Test that Strava API can handle concurrent requests
        results = queue.Queue()
        
        def make_request():
            response = client.get(
                "/api/strava-integration/health",
                headers={"X-API-Key": TEST_API_KEY}
            )
            results.put(response.status_code)
        
        # Test concurrent requests
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Check results
        success_count = 0
        while not results.empty():
            if results.get() == 200:
                success_count += 1
        
        assert success_count == 10
        
        print("✓ Strava API concurrent requests work")
    
    def test_strava_api_memory_usage(self):
        """Test Strava API memory usage"""
        import sys
        
        # Test that Strava API doesn't use too much memory
        initial_size = sys.getsizeof({})
        
        response = client.get(
            "/api/strava-integration/health",
            headers={"X-API-Key": TEST_API_KEY}
        )
        data = response.json()
        
        final_size = sys.getsizeof(data)
        memory_usage = final_size - initial_size
        
        assert memory_usage < 1024 * 1024  # Less than 1MB
        
        print(f"✓ Strava API memory usage: {memory_usage} bytes")
    
    def test_strava_api_throughput(self):
        """Test Strava API throughput"""
        # Test that Strava API can handle high throughput
        start_time = time.time()
        request_count = 0
        
        # Make requests for 1 second
        while time.time() - start_time < 1.0:
            response = client.get(
                "/api/strava-integration/health",
                headers={"X-API-Key": TEST_API_KEY}
            )
            if response.status_code == 200:
                request_count += 1
        
        elapsed_time = time.time() - start_time
        rps = request_count / elapsed_time
        
        assert rps > 10  # Should handle at least 10 requests per second
        
        print(f"✓ Strava API throughput: {rps:.2f} RPS")
    
    def test_strava_api_scalability(self):
        """Test Strava API scalability"""
        # Test that Strava API scales with load
        endpoints = [
            "/api/strava-integration/health",
            "/api/strava-integration/metrics",
            "/api/strava-integration/feed"
        ]
        
        start_time = time.time()
        for endpoint in endpoints:
            if endpoint == "/api/strava-integration/metrics":
                response = client.get(
                    endpoint,
                    headers={"X-API-Key": TEST_API_KEY}
                )
            elif endpoint == "/api/strava-integration/feed":
                response = client.get(
                    endpoint,
                    headers={
                        "X-API-Key": TEST_API_KEY,
                        "Referer": "https://test.com"
                    }
                )
            else:
                response = client.get(
                    endpoint,
                    headers={"X-API-Key": TEST_API_KEY}
                )
            assert response.status_code == 200
        end_time = time.time()
        
        total_time = end_time - start_time
        assert total_time < 2.0  # Should complete in reasonable time
        
        print(f"✓ Strava API scalability: {total_time:.3f}s")
```

**What this does:**
- **Strava API response time**: Tests Strava API response time
- **Strava API concurrent requests**: Tests Strava API concurrent requests
- **Strava API memory usage**: Tests Strava API memory usage
- **Strava API throughput**: Tests Strava API throughput
- **Strava API scalability**: Tests Strava API scalability

### **7. Strava API Security Tests (Lines 282-340)**

```python
class TestStravaAPISecurity:
    """Test Strava API security functionality"""
    
    def test_strava_api_authentication(self):
        """Test Strava API authentication"""
        # Test that Strava API requires authentication
        response = client.get("/api/strava-integration/metrics")
        assert response.status_code == 401
        
        # Test with valid API key
        response = client.get(
            "/api/strava-integration/metrics",
            headers={"X-API-Key": TEST_API_KEY}
        )
        assert response.status_code == 200
        
        print("✓ Strava API authentication works")
    
    def test_strava_api_authorization(self):
        """Test Strava API authorization"""
        # Test that Strava API requires proper authorization
        response = client.get(
            "/api/strava-integration/feed",
            headers={"X-API-Key": TEST_API_KEY}
        )
        assert response.status_code == 403  # Missing Referer header
        
        # Test with proper authorization
        response = client.get(
            "/api/strava-integration/feed",
            headers={
                "X-API-Key": TEST_API_KEY,
                "Referer": "https://test.com"
            }
        )
        assert response.status_code == 200
        
        print("✓ Strava API authorization works")
    
    def test_strava_api_rate_limiting(self):
        """Test Strava API rate limiting"""
        # Test that Strava API implements rate limiting
        for _ in range(100):
            response = client.get(
                "/api/strava-integration/health",
                headers={"X-API-Key": TEST_API_KEY}
            )
            if response.status_code == 429:
                break
        
        # Should eventually hit rate limit
        assert response.status_code == 429
        
        print("✓ Strava API rate limiting works")
    
    def test_strava_api_cors_headers(self):
        """Test Strava API CORS headers"""
        # Test that Strava API includes CORS headers
        response = client.get(
            "/api/strava-integration/health",
            headers={"X-API-Key": TEST_API_KEY}
        )
        
        # Check for CORS headers
        assert "Access-Control-Allow-Origin" in response.headers
        assert "Access-Control-Allow-Methods" in response.headers
        assert "Access-Control-Allow-Headers" in response.headers
        
        print("✓ Strava API CORS headers work")
    
    def test_strava_api_security_headers(self):
        """Test Strava API security headers"""
        # Test that Strava API includes security headers
        response = client.get(
            "/api/strava-integration/health",
            headers={"X-API-Key": TEST_API_KEY}
        )
        
        # Check for security headers
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers
        assert "X-XSS-Protection" in response.headers
        
        print("✓ Strava API security headers work")
```

**What this does:**
- **Strava API authentication**: Tests Strava API authentication
- **Strava API authorization**: Tests Strava API authorization
- **Strava API rate limiting**: Tests Strava API rate limiting
- **Strava API CORS headers**: Tests Strava API CORS headers
- **Strava API security headers**: Tests Strava API security headers

### **8. Strava API Error Handling Tests (Lines 342-400)**

```python
class TestStravaAPIErrorHandling:
    """Test Strava API error handling functionality"""
    
    def test_strava_api_404_error_handling(self):
        """Test Strava API 404 error handling"""
        # Test that Strava API handles 404 errors
        response = client.get(
            "/api/strava-integration/nonexistent-endpoint",
            headers={"X-API-Key": TEST_API_KEY}
        )
        assert response.status_code == 404
        
        data = response.json()
        assert "detail" in data
        
        print("✓ Strava API 404 error handling works")
    
    def test_strava_api_422_error_handling(self):
        """Test Strava API 422 error handling"""
        # Test that Strava API handles 422 errors
        response = client.post(
            "/api/strava-integration/refresh-cache",
            headers={"X-API-Key": TEST_API_KEY},
            json={"invalid_field": "invalid_value"}
        )
        assert response.status_code == 422
        
        data = response.json()
        assert "detail" in data
        
        print("✓ Strava API 422 error handling works")
    
    def test_strava_api_500_error_handling(self):
        """Test Strava API 500 error handling"""
        # Test that Strava API handles 500 errors gracefully
        try:
            # Simulate internal error
            response = client.get(
                "/api/strava-integration/health",
                headers={"X-API-Key": TEST_API_KEY}
            )
            # Should not raise exception
        except Exception:
            # Should handle errors gracefully
            pass
        
        print("✓ Strava API 500 error handling works")
    
    def test_strava_api_validation_error_handling(self):
        """Test Strava API validation error handling"""
        # Test that Strava API handles validation errors
        response = client.get(
            "/api/strava-integration/feed?limit=invalid",
            headers={
                "X-API-Key": TEST_API_KEY,
                "Referer": "https://test.com"
            }
        )
        assert response.status_code == 422
        
        data = response.json()
        assert "detail" in data
        
        print("✓ Strava API validation error handling works")
    
    def test_strava_api_timeout_error_handling(self):
        """Test Strava API timeout error handling"""
        # Test that Strava API handles timeout errors
        try:
            # Simulate timeout
            response = client.get(
                "/api/strava-integration/health",
                headers={"X-API-Key": TEST_API_KEY}
            )
            # Should handle timeout gracefully
        except Exception:
            # Should handle timeout errors gracefully
            pass
        
        print("✓ Strava API timeout error handling works")
```

**What this does:**
- **Strava API 404 error handling**: Tests Strava API 404 error handling
- **Strava API 422 error handling**: Tests Strava API 422 error handling
- **Strava API 500 error handling**: Tests Strava API 500 error handling
- **Strava API validation error handling**: Tests Strava API validation error handling
- **Strava API timeout error handling**: Tests Strava API timeout error handling

## 🎯 **Key Learning Points**

### **1. Strava Integration Testing Strategy**
- **Basic Strava API testing**: Tests basic Strava API functionality
- **Strava cache testing**: Tests Strava cache functionality
- **Strava API performance testing**: Tests Strava API performance
- **Strava API security testing**: Tests Strava API security
- **Strava API error handling testing**: Tests Strava API error handling

### **2. Basic Strava API Testing**
- **Strava API initialization**: Tests Strava API initialization
- **Strava health endpoint**: Tests Strava health endpoint
- **Strava feed endpoint**: Tests Strava feed endpoint
- **Strava metrics endpoint**: Tests Strava metrics endpoint
- **Strava refresh cache endpoint**: Tests Strava refresh cache endpoint

### **3. Strava Cache Testing**
- **Strava cache initialization**: Tests Strava cache initialization
- **Strava cache get activities**: Tests Strava cache get activities
- **Strava cache force refresh**: Tests Strava cache force refresh
- **Strava cache cleanup backups**: Tests Strava cache cleanup backups
- **Strava cache clean invalid activities**: Tests Strava cache clean invalid activities

### **4. Strava API Performance Testing**
- **Strava API response time**: Tests Strava API response time
- **Strava API concurrent requests**: Tests Strava API concurrent requests
- **Strava API memory usage**: Tests Strava API memory usage
- **Strava API throughput**: Tests Strava API throughput
- **Strava API scalability**: Tests Strava API scalability

### **5. Strava API Security Testing**
- **Strava API authentication**: Tests Strava API authentication
- **Strava API authorization**: Tests Strava API authorization
- **Strava API rate limiting**: Tests Strava API rate limiting
- **Strava API CORS headers**: Tests Strava API CORS headers
- **Strava API security headers**: Tests Strava API security headers

## 🚀 **How This Fits Into Your Learning**

This file demonstrates:
- **Strava integration testing**: How to test Strava integration functionality comprehensively
- **Basic Strava API testing**: How to test basic Strava API functionality
- **Strava cache testing**: How to test Strava cache functionality
- **Strava API performance testing**: How to test Strava API performance
- **Strava API security testing**: How to test Strava API security

**Next**: We'll explore the `test_fundraising_scraper.py` to understand fundraising scraper testing! 🎉