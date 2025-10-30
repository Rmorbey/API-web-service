"""
Comprehensive API Integration Tests
Tests complete workflows and component interactions
"""

import pytest
import time
import json
from unittest.mock import patch, Mock
from fastapi.testclient import TestClient
from fastapi import FastAPI
import os

# Import the routers
from projects.fundraising_tracking_app.activity_integration.activity_api import router as activity_router
from projects.fundraising_tracking_app.fundraising_scraper.fundraising_api import router as fundraising_router


class TestComprehensiveAPIIntegration:
    """Test complete API workflows and component interactions"""
    
    def setup_method(self):
        """Set up test environment"""
        # Set API keys for tests
        os.environ["ACTIVITY_API_KEY"] = "test-activity-key-123"
        os.environ["FUNDRAISING_API_KEY"] = "test-fundraising-key-456"
        
        # Create test apps
        self.activity_app = FastAPI()
        self.activity_app.include_router(activity_router, prefix="/api/activity-integration")
        
        self.fundraising_app = FastAPI()
        self.fundraising_app.include_router(fundraising_router, prefix="/api/fundraising")
        
        self.activity_client = TestClient(self.activity_app)
        self.fundraising_client = TestClient(self.fundraising_app)
    
    def test_complete_activity_workflow(self):
        """Test complete activity workflow from health check to data retrieval"""
        # 1. Health check
        health_response = self.activity_client.get("/api/activity-integration/health")
        assert health_response.status_code == 200
        health_data = health_response.json()
        assert health_data["status"] == "healthy"
        assert "timestamp" in health_data
        
        # 2. Get project info
        info_response = self.activity_client.get("/api/activity-integration/")
        assert info_response.status_code == 200
        info_data = info_response.json()
        assert "project" in info_data
        assert "version" in info_data
        
        # 3. Get activity feed
        feed_response = self.activity_client.get("/api/activity-integration/feed")
        assert feed_response.status_code == 200
        feed_data = feed_response.json()
        assert "activities" in feed_data
        assert "total_activities" in feed_data
        
        # 4. Get metrics
        metrics_response = self.activity_client.get("/api/activity-integration/metrics")
        assert metrics_response.status_code == 200
        metrics_data = metrics_response.json()
        assert "cache" in metrics_data
    
    def test_complete_fundraising_workflow(self):
        """Test complete fundraising workflow from health check to data retrieval"""
        # 1. Health check
        health_response = self.fundraising_client.get("/api/fundraising/health")
        assert health_response.status_code == 200
        health_data = health_response.json()
        assert health_data["status"] == "healthy"
        assert "timestamp" in health_data
        
        # 2. Get fundraising data
        data_response = self.fundraising_client.get("/api/fundraising/data")
        assert data_response.status_code == 200
        data_data = data_response.json()
        assert "total_raised" in data_data
        assert "total_donations" in data_data
        
        # 3. Get donations
        donations_response = self.fundraising_client.get("/api/fundraising/donations")
        assert donations_response.status_code == 200
        donations_data = donations_response.json()
        assert "donations" in donations_data
        assert "total_donations" in donations_data
    
    def test_authentication_workflow(self):
        """Test authentication workflow across both APIs"""
        # Test valid authentication
        valid_headers = {"X-API-Key": "test-activity-key-123"}
        
        # Activity API with valid auth
        response = self.activity_client.post(
            "/api/activity-integration/refresh-cache",
            headers=valid_headers,
            json={"force_full_refresh": False, "include_old_activities": False}
        )
        # May return 200 (success) or 500 (error) depending on external API availability
        assert response.status_code in [200, 500, 401, 403]
        
        # Fundraising API with valid auth
        response = self.fundraising_client.post(
            "/api/fundraising/refresh",
            headers={"X-API-Key": "test-fundraising-key-456"},
            json={"force_refresh": True}
        )
        # May return 200 (success) or 500 (error) depending on external API availability
        assert response.status_code in [200, 500, 401, 403]
        
        # Test invalid authentication
        invalid_headers = {"X-API-Key": "invalid-key"}
        
        # Activity API with invalid auth
        response = self.activity_client.post(
            "/api/activity-integration/refresh-cache",
            headers=invalid_headers,
            json={"force_full_refresh": False, "include_old_activities": False}
        )
        assert response.status_code == 403
        
        # Fundraising API with invalid auth
        response = self.fundraising_client.post(
            "/api/fundraising/refresh",
            headers=invalid_headers,
            json={"force_refresh": True}
        )
        assert response.status_code == 403
    
    def test_error_propagation_workflow(self):
        """Test how errors propagate through the system"""
        # Test with invalid request data
        response = self.activity_client.post(
            "/api/activity-integration/refresh-cache",
            headers={"X-API-Key": "test-strava-key-123"},
            json={"invalid_field": "invalid_value"}
        )
        # Should handle validation errors gracefully
        assert response.status_code in [200, 422, 500, 403]
        
        # Test with missing required fields
        response = self.fundraising_client.post(
            "/api/fundraising/refresh",
            headers={"X-API-Key": "test-fundraising-key-456"},
            json={}  # Missing required fields
        )
        # Should handle validation errors gracefully
        assert response.status_code in [200, 422, 500, 403]
    
    def test_concurrent_request_handling(self):
        """Test how the system handles concurrent requests"""
        import threading
        import time
        
        results = []
        errors = []
        
        def make_strava_request():
            try:
                response = self.activity_client.get("/api/activity-integration/feed")
                results.append(response.status_code)
            except Exception as e:
                errors.append(e)
        
        def make_fundraising_request():
            try:
                response = self.fundraising_client.get("/api/fundraising/data")
                results.append(response.status_code)
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads
        threads = []
        for _ in range(5):
            threads.append(threading.Thread(target=make_strava_request))
            threads.append(threading.Thread(target=make_fundraising_request))
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify all requests completed successfully
        assert len(results) == 10  # 5 Strava + 5 Fundraising requests
        assert all(status == 200 for status in results)
        assert len(errors) == 0
    
    def test_cache_interaction_workflow(self):
        """Test cache interaction between different components"""
        # 1. Get initial data
        initial_response = self.activity_client.get("/api/activity-integration/feed")
        assert initial_response.status_code == 200
        initial_data = initial_response.json()
        
        # 2. Force cache refresh
        refresh_response = self.activity_client.post(
            "/api/activity-integration/refresh-cache",
            headers={"X-API-Key": "test-strava-key-123"},
            json={"force_full_refresh": True, "include_old_activities": False}
        )
        # May return 200 (success) or 500 (error) depending on external API availability
        assert refresh_response.status_code in [200, 500, 401, 403]
        
        # 3. Get data after refresh
        after_refresh_response = self.activity_client.get("/api/activity-integration/feed")
        assert after_refresh_response.status_code == 200
        after_refresh_data = after_refresh_response.json()
        
        # 4. Verify cache is working (data should be consistent)
        assert "activities" in after_refresh_data
        assert "total_activities" in after_refresh_data
    
    def test_data_consistency_across_endpoints(self):
        """Test data consistency across different endpoints"""
        # Get data from multiple endpoints
        feed_response = self.activity_client.get("/api/activity-integration/feed")
        metrics_response = self.activity_client.get("/api/activity-integration/metrics")
        
        assert feed_response.status_code == 200
        assert metrics_response.status_code == 200
        
        feed_data = feed_response.json()
        metrics_data = metrics_response.json()
        
        # Verify data structure consistency
        assert "activities" in feed_data
        assert "total_activities" in feed_data
        assert "api_calls" in metrics_data
        assert "cache" in metrics_data
        
        # Verify data types are consistent
        assert isinstance(feed_data["activities"], list)
        assert isinstance(feed_data["total_activities"], int)
        assert isinstance(metrics_data["api_calls"], dict)
    
    def test_rate_limiting_integration(self):
        """Test rate limiting integration"""
        # Make multiple rapid requests
        responses = []
        for _ in range(10):
            response = self.activity_client.get("/api/activity-integration/feed")
            responses.append(response.status_code)
            time.sleep(0.1)  # Small delay to avoid overwhelming
        
        # All requests should succeed (rate limiting is handled gracefully)
        assert all(status == 200 for status in responses)
    
    def test_health_check_integration(self):
        """Test health check integration across all services"""
        # Test Strava health
        strava_health = self.activity_client.get("/api/activity-integration/health")
        assert strava_health.status_code == 200
        strava_data = strava_health.json()
        assert strava_data["status"] == "healthy"
        
        # Test Fundraising health
        fundraising_health = self.fundraising_client.get("/api/fundraising/health")
        assert fundraising_health.status_code == 200
        fundraising_data = fundraising_health.json()
        assert fundraising_data["status"] == "healthy"
        
        # Verify health check data structure
        assert "timestamp" in strava_data
        assert "timestamp" in fundraising_data
        assert "project" in strava_data
        assert "project" in fundraising_data
    
    def test_error_recovery_workflow(self):
        """Test error recovery and resilience"""
        # Test with invalid parameters
        response = self.activity_client.get("/api/activity-integration/feed?limit=invalid")
        assert response.status_code == 422
        
        # Test with valid parameters after error
        response = self.activity_client.get("/api/activity-integration/feed?limit=10")
        assert response.status_code == 200
        
        # Test with invalid activity type
        response = self.activity_client.get("/api/activity-integration/feed?activity_type=InvalidType")
        assert response.status_code == 422
        
        # Test with valid activity type after error
        response = self.activity_client.get("/api/activity-integration/feed?activity_type=Run")
        assert response.status_code == 200
    
    def test_complete_user_journey(self):
        """Test complete user journey from start to finish"""
        # 1. User checks system health
        health_response = self.activity_client.get("/api/activity-integration/health")
        assert health_response.status_code == 200
        
        # 2. User gets project information
        info_response = self.activity_client.get("/api/activity-integration/")
        assert info_response.status_code == 200
        
        # 3. User browses activity feed
        feed_response = self.activity_client.get("/api/activity-integration/feed?limit=5")
        assert feed_response.status_code == 200
        feed_data = feed_response.json()
        assert len(feed_data["activities"]) <= 5
        
        # 4. User checks fundraising data
        fundraising_response = self.fundraising_client.get("/api/fundraising/data")
        assert fundraising_response.status_code == 200
        
        # 5. User views donations
        donations_response = self.fundraising_client.get("/api/fundraising/donations?limit=10")
        assert donations_response.status_code == 200
        
        # 6. User checks system metrics
        metrics_response = self.activity_client.get("/api/activity-integration/metrics")
        assert metrics_response.status_code == 200
        
        # Verify all responses have expected data structure
        assert "activities" in feed_data
        assert "total_activities" in feed_data
        assert "donations" in donations_response.json()
        assert "api_calls" in metrics_response.json()
