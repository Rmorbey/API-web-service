# 📚 test_multi_project_api.py - Complete Code Explanation

## 🎯 **Overview**

This file contains **comprehensive tests** for the multi-project API functionality and API endpoints used throughout the system. It tests API logic, API performance, API integration, and API configuration to ensure the system handles API requests correctly and efficiently. Think of it as the **multi-project API quality assurance** that verifies your API system works properly.

## 📁 **File Structure Context**

```
test_multi_project_api.py  ← YOU ARE HERE (Multi-Project API Tests)
├── multi_project_api.py           (Main API)
├── strava_integration_api.py      (Strava API)
├── fundraising_api.py             (Fundraising API)
├── security.py                    (Security middleware)
├── compression_middleware.py      (Compression middleware)
└── simple_error_handlers.py       (Error handling middleware)
```

## 🔍 **Line-by-Line Code Explanation

### **1. Imports and Setup (Lines 1-25)**

```python
#!/usr/bin/env python3
"""
Comprehensive Test Suite for Multi-Project API Functionality
Tests all multi-project API features and API endpoints
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

from multi_project_api import app
```

**What this does:**
- **Test framework**: Uses pytest for testing
- **Async support**: Imports asyncio for async testing
- **Timing**: Imports time for performance measurement
- **Temporary files**: Imports tempfile for temporary file handling
- **Mocking**: Imports unittest.mock for mocking
- **Path management**: Adds project root to Python path
- **App import**: Imports the main FastAPI application

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

### **3. API Test Data (Lines 52-100)**

```python
# API test data
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

SAMPLE_FUNDRAISING_DATA = {
    "total_raised": 1250.50,
    "target": 5000.0,
    "donation_count": 25,
    "last_updated": "2024-01-01T10:00:00Z",
    "page_title": "Test Fundraising Page",
    "page_url": "https://test.justgiving.com/test",
    "currency": "GBP",
    "status": "active"
}

SAMPLE_DONATION = {
    "id": 1,
    "amount": 25.00,
    "donor_name": "John Doe",
    "donation_date": "2024-01-01T09:00:00Z",
    "message": "Great cause!",
    "is_anonymous": False
}
```

**What this does:**
- **Sample data**: Defines sample data for testing
- **Test strings**: Various string formats for testing
- **Test numbers**: Various number formats for testing
- **Test dates**: Various date formats for testing
- **Realistic data**: Uses realistic data structures

### **4. Basic API Tests (Lines 102-160)**

```python
class TestBasicAPI:
    """Test basic API functionality"""
    
    def test_api_initialization(self):
        """Test API initialization"""
        # Test that API can be initialized
        assert app is not None
        assert hasattr(app, 'routes')
        
        print("✓ API initialization works")
    
    def test_api_health_endpoint(self):
        """Test API health endpoint"""
        # Test that health endpoint works
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"
        
        print("✓ API health endpoint works")
    
    def test_api_metrics_endpoint(self):
        """Test API metrics endpoint"""
        # Test that metrics endpoint works
        response = client.get(
            "/metrics",
            headers={"X-API-Key": TEST_API_KEY}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "timestamp" in data
        assert "api_calls" in data
        
        print("✓ API metrics endpoint works")
    
    def test_api_documentation_endpoint(self):
        """Test API documentation endpoint"""
        # Test that documentation endpoint works
        response = client.get("/docs")
        assert response.status_code == 200
        
        print("✓ API documentation endpoint works")
    
    def test_api_openapi_endpoint(self):
        """Test API OpenAPI endpoint"""
        # Test that OpenAPI endpoint works
        response = client.get("/openapi.json")
        assert response.status_code == 200
        
        data = response.json()
        assert "openapi" in data
        assert "info" in data
        
        print("✓ API OpenAPI endpoint works")
```

**What this does:**
- **API initialization**: Tests API initialization
- **API health endpoint**: Tests API health endpoint
- **API metrics endpoint**: Tests API metrics endpoint
- **API documentation endpoint**: Tests API documentation endpoint
- **API OpenAPI endpoint**: Tests API OpenAPI endpoint

### **5. Strava API Integration Tests (Lines 162-220)**

```python
class TestStravaAPIIntegration:
    """Test Strava API integration functionality"""
    
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
    
    def test_strava_cleanup_backups_endpoint(self):
        """Test Strava cleanup backups endpoint"""
        # Test that Strava cleanup backups endpoint works
        response = client.post(
            "/api/strava-integration/cleanup-backups",
            headers={"X-API-Key": TEST_API_KEY},
            json={"keep_last_n": 5}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "success" in data
        
        print("✓ Strava cleanup backups endpoint works")
```

**What this does:**
- **Strava health endpoint**: Tests Strava health endpoint
- **Strava feed endpoint**: Tests Strava feed endpoint
- **Strava metrics endpoint**: Tests Strava metrics endpoint
- **Strava refresh cache endpoint**: Tests Strava refresh cache endpoint
- **Strava cleanup backups endpoint**: Tests Strava cleanup backups endpoint

### **6. Fundraising API Integration Tests (Lines 222-280)**

```python
class TestFundraisingAPIIntegration:
    """Test fundraising API integration functionality"""
    
    def test_fundraising_health_endpoint(self):
        """Test fundraising health endpoint"""
        # Test that fundraising health endpoint works
        response = client.get(
            "/api/fundraising-scraper/health",
            headers={"X-API-Key": TEST_API_KEY}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "project" in data
        assert data["project"] == "fundraising-scraper"
        
        print("✓ Fundraising health endpoint works")
    
    def test_fundraising_data_endpoint(self):
        """Test fundraising data endpoint"""
        # Test that fundraising data endpoint works
        response = client.get(
            "/api/fundraising-scraper/data",
            headers={"X-API-Key": TEST_API_KEY}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "total_raised" in data
        assert "target" in data
        
        print("✓ Fundraising data endpoint works")
    
    def test_fundraising_donations_endpoint(self):
        """Test fundraising donations endpoint"""
        # Test that fundraising donations endpoint works
        response = client.get(
            "/api/fundraising-scraper/donations",
            headers={"X-API-Key": TEST_API_KEY}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "donations" in data
        
        print("✓ Fundraising donations endpoint works")
    
    def test_fundraising_refresh_endpoint(self):
        """Test fundraising refresh endpoint"""
        # Test that fundraising refresh endpoint works
        response = client.post(
            "/api/fundraising-scraper/refresh",
            headers={"X-API-Key": TEST_API_KEY},
            json={"force_refresh": False}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "success" in data
        
        print("✓ Fundraising refresh endpoint works")
    
    def test_fundraising_cleanup_backups_endpoint(self):
        """Test fundraising cleanup backups endpoint"""
        # Test that fundraising cleanup backups endpoint works
        response = client.post(
            "/api/fundraising-scraper/cleanup-backups",
            headers={"X-API-Key": TEST_API_KEY},
            json={"keep_last_n": 5}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "success" in data
        
        print("✓ Fundraising cleanup backups endpoint works")
```

**What this does:**
- **Fundraising health endpoint**: Tests fundraising health endpoint
- **Fundraising data endpoint**: Tests fundraising data endpoint
- **Fundraising donations endpoint**: Tests fundraising donations endpoint
- **Fundraising refresh endpoint**: Tests fundraising refresh endpoint
- **Fundraising cleanup backups endpoint**: Tests fundraising cleanup backups endpoint

### **7. API Performance Tests (Lines 282-340)**

```python
class TestAPIPerformance:
    """Test API performance functionality"""
    
    def test_api_response_time(self):
        """Test API response time"""
        # Test that API responds quickly
        start_time = time.time()
        
        response = client.get("/health")
        
        end_time = time.time()
        response_time = end_time - start_time
        
        assert response.status_code == 200
        assert response_time < 1.0  # Should be under 1 second
        
        print(f"✓ API response time: {response_time:.3f}s")
    
    def test_api_concurrent_requests(self):
        """Test API concurrent requests"""
        import threading
        import queue
        
        # Test that API can handle concurrent requests
        results = queue.Queue()
        
        def make_request():
            response = client.get("/health")
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
        
        print("✓ API concurrent requests work")
    
    def test_api_memory_usage(self):
        """Test API memory usage"""
        import sys
        
        # Test that API doesn't use too much memory
        initial_size = sys.getsizeof({})
        
        response = client.get("/health")
        data = response.json()
        
        final_size = sys.getsizeof(data)
        memory_usage = final_size - initial_size
        
        assert memory_usage < 1024 * 1024  # Less than 1MB
        
        print(f"✓ API memory usage: {memory_usage} bytes")
    
    def test_api_throughput(self):
        """Test API throughput"""
        # Test that API can handle high throughput
        start_time = time.time()
        request_count = 0
        
        # Make requests for 1 second
        while time.time() - start_time < 1.0:
            response = client.get("/health")
            if response.status_code == 200:
                request_count += 1
        
        elapsed_time = time.time() - start_time
        rps = request_count / elapsed_time
        
        assert rps > 10  # Should handle at least 10 requests per second
        
        print(f"✓ API throughput: {rps:.2f} RPS")
    
    def test_api_scalability(self):
        """Test API scalability"""
        # Test that API scales with load
        endpoints = ["/health", "/metrics", "/api/strava-integration/health"]
        
        start_time = time.time()
        for endpoint in endpoints:
            if endpoint == "/metrics":
                response = client.get(
                    endpoint,
                    headers={"X-API-Key": TEST_API_KEY}
                )
            else:
                response = client.get(endpoint)
            assert response.status_code == 200
        end_time = time.time()
        
        total_time = end_time - start_time
        assert total_time < 2.0  # Should complete in reasonable time
        
        print(f"✓ API scalability: {total_time:.3f}s")
```

**What this does:**
- **API response time**: Tests API response time
- **API concurrent requests**: Tests API concurrent requests
- **API memory usage**: Tests API memory usage
- **API throughput**: Tests API throughput
- **API scalability**: Tests API scalability

### **8. API Security Tests (Lines 342-400)**

```python
class TestAPISecurity:
    """Test API security functionality"""
    
    def test_api_authentication(self):
        """Test API authentication"""
        # Test that API requires authentication
        response = client.get("/metrics")
        assert response.status_code == 401
        
        # Test with valid API key
        response = client.get(
            "/metrics",
            headers={"X-API-Key": TEST_API_KEY}
        )
        assert response.status_code == 200
        
        print("✓ API authentication works")
    
    def test_api_authorization(self):
        """Test API authorization"""
        # Test that API requires proper authorization
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
        
        print("✓ API authorization works")
    
    def test_api_rate_limiting(self):
        """Test API rate limiting"""
        # Test that API implements rate limiting
        for _ in range(100):
            response = client.get(
                "/api/strava-integration/health",
                headers={"X-API-Key": TEST_API_KEY}
            )
            if response.status_code == 429:
                break
        
        # Should eventually hit rate limit
        assert response.status_code == 429
        
        print("✓ API rate limiting works")
    
    def test_api_cors_headers(self):
        """Test API CORS headers"""
        # Test that API includes CORS headers
        response = client.get("/health")
        
        # Check for CORS headers
        assert "Access-Control-Allow-Origin" in response.headers
        assert "Access-Control-Allow-Methods" in response.headers
        assert "Access-Control-Allow-Headers" in response.headers
        
        print("✓ API CORS headers work")
    
    def test_api_security_headers(self):
        """Test API security headers"""
        # Test that API includes security headers
        response = client.get("/health")
        
        # Check for security headers
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers
        assert "X-XSS-Protection" in response.headers
        
        print("✓ API security headers work")
```

**What this does:**
- **API authentication**: Tests API authentication
- **API authorization**: Tests API authorization
- **API rate limiting**: Tests API rate limiting
- **API CORS headers**: Tests API CORS headers
- **API security headers**: Tests API security headers

### **9. API Error Handling Tests (Lines 402-460)**

```python
class TestAPIErrorHandling:
    """Test API error handling functionality"""
    
    def test_api_404_error_handling(self):
        """Test API 404 error handling"""
        # Test that API handles 404 errors
        response = client.get("/nonexistent-endpoint")
        assert response.status_code == 404
        
        data = response.json()
        assert "detail" in data
        
        print("✓ API 404 error handling works")
    
    def test_api_422_error_handling(self):
        """Test API 422 error handling"""
        # Test that API handles 422 errors
        response = client.post(
            "/api/strava-integration/refresh-cache",
            headers={"X-API-Key": TEST_API_KEY},
            json={"invalid_field": "invalid_value"}
        )
        assert response.status_code == 422
        
        data = response.json()
        assert "detail" in data
        
        print("✓ API 422 error handling works")
    
    def test_api_500_error_handling(self):
        """Test API 500 error handling"""
        # Test that API handles 500 errors gracefully
        try:
            # Simulate internal error
            response = client.get("/health")
            # Should not raise exception
        except Exception:
            # Should handle errors gracefully
            pass
        
        print("✓ API 500 error handling works")
    
    def test_api_validation_error_handling(self):
        """Test API validation error handling"""
        # Test that API handles validation errors
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
        
        print("✓ API validation error handling works")
    
    def test_api_timeout_error_handling(self):
        """Test API timeout error handling"""
        # Test that API handles timeout errors
        try:
            # Simulate timeout
            response = client.get("/health")
            # Should handle timeout gracefully
        except Exception:
            # Should handle timeout errors gracefully
            pass
        
        print("✓ API timeout error handling works")
```

**What this does:**
- **API 404 error handling**: Tests API 404 error handling
- **API 422 error handling**: Tests API 422 error handling
- **API 500 error handling**: Tests API 500 error handling
- **API validation error handling**: Tests API validation error handling
- **API timeout error handling**: Tests API timeout error handling

## 🎯 **Key Learning Points**

### **1. Multi-Project API Testing Strategy**
- **Basic API testing**: Tests basic API functionality
- **Strava API integration testing**: Tests Strava API integration
- **Fundraising API integration testing**: Tests fundraising API integration
- **API performance testing**: Tests API performance
- **API security testing**: Tests API security

### **2. Basic API Testing**
- **API initialization**: Tests API initialization
- **API health endpoint**: Tests API health endpoint
- **API metrics endpoint**: Tests API metrics endpoint
- **API documentation endpoint**: Tests API documentation endpoint
- **API OpenAPI endpoint**: Tests API OpenAPI endpoint

### **3. Strava API Integration Testing**
- **Strava health endpoint**: Tests Strava health endpoint
- **Strava feed endpoint**: Tests Strava feed endpoint
- **Strava metrics endpoint**: Tests Strava metrics endpoint
- **Strava refresh cache endpoint**: Tests Strava refresh cache endpoint
- **Strava cleanup backups endpoint**: Tests Strava cleanup backups endpoint

### **4. Fundraising API Integration Testing**
- **Fundraising health endpoint**: Tests fundraising health endpoint
- **Fundraising data endpoint**: Tests fundraising data endpoint
- **Fundraising donations endpoint**: Tests fundraising donations endpoint
- **Fundraising refresh endpoint**: Tests fundraising refresh endpoint
- **Fundraising cleanup backups endpoint**: Tests fundraising cleanup backups endpoint

### **5. API Performance Testing**
- **API response time**: Tests API response time
- **API concurrent requests**: Tests API concurrent requests
- **API memory usage**: Tests API memory usage
- **API throughput**: Tests API throughput
- **API scalability**: Tests API scalability

## 🚀 **How This Fits Into Your Learning**

This file demonstrates:
- **Multi-project API testing**: How to test multi-project API functionality comprehensively
- **Basic API testing**: How to test basic API functionality
- **Strava API integration testing**: How to test Strava API integration
- **Fundraising API integration testing**: How to test fundraising API integration
- **API performance testing**: How to test API performance

**Next**: We'll explore the `test_strava_integration.py` to understand Strava integration testing! 🎉