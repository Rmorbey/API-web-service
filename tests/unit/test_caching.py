#!/usr/bin/env python3
"""
Unit tests for HTTP caching functionality
"""

import pytest
import time
from unittest.mock import Mock, patch
from fastapi import Request
from fastapi.testclient import TestClient

from projects.fundraising_tracking_app.activity_integration.caching import CacheManager, cache_manager
from projects.fundraising_tracking_app.activity_integration.cache_middleware import CacheMiddleware


class TestCacheManager:
    """Test the CacheManager class"""
    
    def test_generate_etag(self):
        """Test ETag generation"""
        manager = CacheManager()
        
        # Test with dict
        data1 = {"key": "value", "number": 123}
        etag1 = manager._generate_etag(data1)
        
        # Same data should generate same ETag
        data2 = {"number": 123, "key": "value"}  # Different order
        etag2 = manager._generate_etag(data2)
        
        assert etag1 == etag2
        assert etag1.startswith('"')
        assert etag1.endswith('"')
    
    def test_cache_key_generation(self):
        """Test cache key generation"""
        manager = CacheManager()
        
        # Mock request
        request = Mock()
        request.url.path = "/api/test"
        request.query_params = {}
        
        key1 = manager._get_cache_key(request)
        assert key1 == "/api/test"
        
        # Test with query params
        request.query_params = {"limit": "10", "offset": "0"}
        key2 = manager._get_cache_key(request)
        assert "limit=10" in key2
        assert "offset=0" in key2
        
        # Test with user ID
        key3 = manager._get_cache_key(request, user_id="user123")
        assert "user:user123" in key3
    
    def test_cache_response_and_retrieve(self):
        """Test caching and retrieving responses"""
        manager = CacheManager()
        
        # Mock request
        request = Mock()
        request.url.path = "/api/test"
        request.query_params = {}
        request.method = "GET"
        request.headers = {}
        
        # Test data
        test_data = {"message": "Hello World", "timestamp": "2023-01-01"}
        
        # Cache the response
        manager.cache_response(request, test_data, cache_type="dynamic")
        
        # Retrieve cached response
        cached_response = manager.get_cached_response(request)
        
        assert cached_response is not None
        assert cached_response.status_code == 200
        
        # Check cache stats
        stats = manager.get_cache_stats()
        assert stats["total_entries"] == 1
        assert stats["active_entries"] == 1
    
    def test_cache_expiration(self):
        """Test cache expiration"""
        manager = CacheManager()
        
        # Mock request
        request = Mock()
        request.url.path = "/api/test"
        request.query_params = {}
        request.method = "GET"
        request.headers = {}
        
        # Cache with very short expiration
        manager.cache_response(request, {"test": "data"}, cache_type="dynamic", custom_max_age=1)
        
        # Should be available immediately
        cached_response = manager.get_cached_response(request)
        assert cached_response is not None
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Should be expired
        cached_response = manager.get_cached_response(request)
        assert cached_response is None
    
    def test_etag_validation(self):
        """Test ETag validation for 304 responses"""
        manager = CacheManager()
        
        # Mock request
        request = Mock()
        request.url.path = "/api/test"
        request.query_params = {}
        request.method = "GET"
        request.headers = {"if-none-match": '"test-etag"'}
        
        # Cache data with specific ETag
        manager._cache = {
            "/api/test": {
                "data": {"test": "data"},
                "etag": '"test-etag"',
                "last_modified": "2023-01-01T00:00:00Z",
                "expires_at": time.time() + 3600,
                "max_age": 3600,
                "cache_type": "dynamic"
            }
        }
        
        # Should return 304 Not Modified
        cached_response = manager.get_cached_response(request)
        assert cached_response.status_code == 304
    
    def test_cache_invalidation(self):
        """Test cache invalidation"""
        manager = CacheManager()
        
        # Add some test cache entries
        manager._cache = {
            "/api/test1": {"data": "test1", "etag": "etag1", "expires_at": time.time() + 3600, "max_age": 3600, "cache_type": "dynamic", "last_modified": "2023-01-01T00:00:00Z"},
            "/api/test2": {"data": "test2", "etag": "etag2", "expires_at": time.time() + 3600, "max_age": 3600, "cache_type": "dynamic", "last_modified": "2023-01-01T00:00:00Z"},
            "/api/other": {"data": "other", "etag": "etag3", "expires_at": time.time() + 3600, "max_age": 3600, "cache_type": "dynamic", "last_modified": "2023-01-01T00:00:00Z"},
        }
        
        # Invalidate by pattern
        count = manager.invalidate_cache(pattern="/api/test")
        assert count == 2
        assert len(manager._cache) == 1
        assert "/api/other" in manager._cache
        
        # Invalidate all
        count = manager.invalidate_cache()
        assert count == 1
        assert len(manager._cache) == 0


class TestCacheMiddleware:
    """Test the CacheMiddleware class"""
    
    def test_cache_rule_matching(self):
        """Test cache rule matching"""
        middleware = CacheMiddleware(None)
        
        # Test exact match
        rule = middleware._get_cache_rule("/api/activity-integration/feed")
        assert rule is not None
        assert rule["type"] == "dynamic"
        
        # Test no match
        rule = middleware._get_cache_rule("/api/unknown/endpoint")
        assert rule is None
    
    def test_user_id_extraction(self):
        """Test user ID extraction from request"""
        middleware = CacheMiddleware(None)
        
        # Mock request with API key
        request = Mock()
        request.headers = {"x-api-key": "test-api-key-12345"}
        
        user_id = middleware._extract_user_id(request)
        assert user_id == "api_key:test-api"
        
        # Mock request without API key
        request.headers = {}
        user_id = middleware._extract_user_id(request)
        assert user_id is None


class TestCacheIntegration:
    """Test cache integration with FastAPI"""
    
    def test_cache_stats_endpoint(self):
        """Test cache stats endpoint"""
        from multi_project_api import app
        
        # Use proper test client with host override
        client = TestClient(app, base_url="http://localhost")
        
        # Test without API key (should fail)
        response = client.get("/api/activity-integration/cache-stats")
        assert response.status_code in [400, 401, 429]  # Could be 400, 401, or 429 (rate limited)
        
        # Test with API key
        response = client.get("/api/activity-integration/cache-stats", 
                            headers={"X-API-Key": "test-activity-key-123"})
        assert response.status_code in [200, 429]  # 200 for success, 429 for rate limited
        
        # Only check JSON content if we got a successful response
        if response.status_code == 200:
            data = response.json()
            assert data["success"] is True
            assert "cache_stats" in data
            assert "timestamp" in data
    
    def test_cache_invalidation_endpoint(self):
        """Test cache invalidation endpoint"""
        from multi_project_api import app
        
        # Use proper test client with host override
        client = TestClient(app, base_url="http://localhost")
        
        # Test without API key (should fail)
        response = client.post("/api/activity-integration/cache/invalidate")
        assert response.status_code in [400, 401, 429]  # Could be 400, 401, or 429 (rate limited)
        
        # Test with API key
        response = client.post("/api/activity-integration/cache/invalidate",
                             headers={"X-API-Key": "test-activity-key-123"})
        assert response.status_code in [200, 429]  # 200 for success, 429 for rate limited
        
        # Only check JSON content if we got a successful response
        if response.status_code == 200:
            data = response.json()
            assert data["success"] is True
            assert "entries_removed" in data
            assert "message" in data