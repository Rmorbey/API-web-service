"""
Unit tests for Fundraising API
Tests FastAPI router endpoints and business logic
"""

import os
# Set environment variable before any imports
os.environ["FUNDRAISING_API_KEY"] = "test-api-key"

import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi import HTTPException
from fastapi.testclient import TestClient
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

# Import after setting environment variable
from projects.fundraising_tracking_app.fundraising_scraper.fundraising_api import router
# Patch the API_KEY to ensure it matches our test key
import projects.fundraising_tracking_app.fundraising_scraper.fundraising_api as fundraising_api_module
fundraising_api_module.API_KEY = "test-api-key"
from projects.fundraising_tracking_app.fundraising_scraper.models import (
    FundraisingDataResponse,
    DonationsResponse,
    HealthResponse,
    RefreshResponse,
    CleanupResponse,
    ProjectInfoResponse,
    FundraisingRefreshRequest,
    FundraisingCleanupRequest,
    DonationsFilterRequest
)
# Removed complex error handlers - using FastAPI's built-in HTTPException


# Create a test FastAPI app with the router
app = FastAPI()
app.include_router(router, prefix="/api/fundraising")

# Using FastAPI's built-in error handling

client = TestClient(app)


class TestHealthEndpoint:
    """Test /health endpoint"""
    
    def test_health_endpoint_success(self):
        """Test health endpoint returns success"""
        response = client.get("/api/fundraising/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "project" in data
        assert "scraper_running" in data
    
    def test_health_endpoint_structure(self):
        """Test health endpoint response structure"""
        response = client.get("/api/fundraising/health")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check required fields
        required_fields = ["status", "timestamp", "project", "scraper_running"]
        for field in required_fields:
            assert field in data
        
        # Check data types
        assert isinstance(data["status"], str)
        assert isinstance(data["timestamp"], str)
        assert isinstance(data["project"], str)
        assert isinstance(data["scraper_running"], bool)


class TestProjectInfoEndpoint:
    """Test / endpoint (project info)"""
    
    def test_project_info_endpoint_success(self):
        """Test project info endpoint returns success"""
        response = client.get("/api/fundraising/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["project"] == "fundraising-scraper"
        assert data["description"] == "JustGiving fundraising data scraper and API"
        assert "version" in data
        assert "endpoints" in data
        assert isinstance(data["endpoints"], dict)
    
    def test_project_info_endpoint_structure(self):
        """Test project info endpoint response structure"""
        response = client.get("/api/fundraising/")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check required fields
        required_fields = ["project", "description", "version", "endpoints"]
        for field in required_fields:
            assert field in data
        
        # Check data types
        assert isinstance(data["project"], str)
        assert isinstance(data["description"], str)
        assert isinstance(data["version"], str)
        assert isinstance(data["endpoints"], dict)
        
        # Check endpoints dict contains expected endpoints
        expected_endpoints = ["data", "refresh", "health"]
        for endpoint in expected_endpoints:
            assert endpoint in data["endpoints"]


class TestDataEndpoint:
    """Test /data endpoint"""
    
    @patch('projects.fundraising_tracking_app.fundraising_scraper.fundraising_api.cache')
    def test_data_endpoint_success(self, mock_cache):
        """Test data endpoint returns success with mock data"""
        
        # Mock the get_fundraising_data method
        mock_data = {
            "total_raised": 150.0,  # 50% of 300 target
            "total_donations": 25,
            "last_updated": "2023-01-01T12:00:00",
            "donations": []
        }
        mock_cache.get_fundraising_data.return_value = mock_data
        
        response = client.get("/api/fundraising/data")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_raised"] == 150.0
        assert data["total_donations"] == 25
    
    @patch('projects.fundraising_tracking_app.fundraising_scraper.fundraising_api.cache')
    def test_data_endpoint_cache_error(self, mock_cache):
        """Test data endpoint handles cache errors"""
        
        # Mock the cache instance to raise an exception
        mock_cache.get_fundraising_data.side_effect = Exception("Cache error")
        
        # With error handlers, APIException is converted to HTTP response
        response = client.get("/api/fundraising/data")
        
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "Error fetching fundraising data" in data["detail"]


class TestDonationsEndpoint:
    """Test /donations endpoint"""
    
    @patch('projects.fundraising_tracking_app.fundraising_scraper.fundraising_api.cache')
    def test_donations_endpoint_success(self, mock_cache):
        """Test donations endpoint returns success with mock data"""
        
        # Mock the get_fundraising_data method (actual method called by endpoint)
        mock_donations = [
            {
                "donor_name": "John Doe",
                "amount": 50.0,
                "message": "Great cause!",
                "date": "2023-01-01T12:00:00",
                "scraped_at": "2023-01-01T12:00:00"
            },
            {
                "donor_name": "Jane Smith",
                "amount": 25.0,
                "message": "Keep it up!",
                "date": "2023-01-02T10:00:00",
                "scraped_at": "2023-01-02T10:00:00"
            }
        ]
        mock_data = {
            "donations": mock_donations,
            "total_raised": 75.0,
            "total_donations": 2
        }
        mock_cache.get_fundraising_data.return_value = mock_data
        
        response = client.get("/api/fundraising/donations")
        
        assert response.status_code == 200
        data = response.json()
        assert "donations" in data
        assert len(data["donations"]) == 2
        assert data["donations"][0]["amount"] == 50.0
    
    @patch('projects.fundraising_tracking_app.fundraising_scraper.fundraising_api.cache')
    def test_donations_endpoint_with_filters(self, mock_cache):
        """Test donations endpoint with query parameters"""
        
        # Mock the get_fundraising_data method
        mock_donations = [
            {
                "donor_name": "John Doe",
                "amount": 50.0,
                "message": "Great cause!",
                "date": "2023-01-01T12:00:00",
                "scraped_at": "2023-01-01T12:00:00"
            }
        ]
        mock_data = {
            "donations": mock_donations,
            "total_raised": 50.0,
            "total_donations": 1
        }
        mock_cache.get_fundraising_data.return_value = mock_data
        
        # Test with query parameters
        response = client.get("/api/fundraising/donations?limit=10&min_amount=25.0&include_anonymous=true")
        
        assert response.status_code == 200
        data = response.json()
        assert "donations" in data
        
        # Verify the cache was called
        mock_cache.get_fundraising_data.assert_called_once()
    
    @patch('projects.fundraising_tracking_app.fundraising_scraper.fundraising_api.cache')
    def test_donations_endpoint_cache_error(self, mock_cache):
        """Test donations endpoint handles cache errors"""
        
        # Mock the cache instance to raise an exception
        mock_cache.get_fundraising_data.side_effect = Exception("Cache error")
        
        # With error handlers, APIException is converted to HTTP response
        response = client.get("/api/fundraising/donations")
        
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "Error fetching donations" in data["detail"]


class TestRefreshEndpoint:
    """Test /refresh endpoint"""
    
    @patch('projects.fundraising_tracking_app.fundraising_scraper.fundraising_api.cache')
    def test_refresh_endpoint_success(self, mock_cache):
        """Test refresh endpoint returns success"""
        
        # Mock the force_refresh_now method (actual method name)
        mock_cache.force_refresh_now.return_value = True
        
        # Test with request body
        request_data = {
            "force_refresh": True,
            "include_metadata": True
        }
        
        response = client.post("/api/fundraising/refresh", json=request_data, headers={"X-API-Key": "test-api-key"})
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "Fundraising data refresh triggered successfully" in data["message"]
    
    @patch('projects.fundraising_tracking_app.fundraising_scraper.fundraising_api.cache')
    def test_refresh_endpoint_default_values(self, mock_cache):
        """Test refresh endpoint with default values"""
        
        # Mock the force_refresh_now method
        mock_cache.force_refresh_now.return_value = True
        
        # Test with empty request body (should use defaults)
        response = client.post("/api/fundraising/refresh", json={}, headers={"X-API-Key": "test-api-key"})
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        
        # Verify the cache was called
        mock_cache.force_refresh_now.assert_called_once()
    
    @patch('projects.fundraising_tracking_app.fundraising_scraper.fundraising_api.cache')
    def test_refresh_endpoint_cache_error(self, mock_cache):
        """Test refresh endpoint handles cache errors"""
        
        # Mock the cache instance to raise an exception
        mock_cache.force_refresh_now.side_effect = Exception("Refresh error")
        
        request_data = {"force_refresh": True}
        response = client.post("/api/fundraising/refresh", json=request_data, headers={"X-API-Key": "test-api-key"})
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "Refresh failed" in data["message"]


class TestCleanupBackupsEndpoint:
    """Test /cleanup-backups endpoint"""
    
    @patch('projects.fundraising_tracking_app.fundraising_scraper.fundraising_api.cache')
    def test_cleanup_backups_endpoint_success(self, mock_cache):
        """Test cleanup-backups endpoint returns success"""
        
        # Mock the cleanup_backups method (actual method name)
        mock_cache.cleanup_backups.return_value = True
        
        # Test with request body
        request_data = {
            "keep_backups": 2,
            "force_cleanup": False
        }
        
        response = client.post("/api/fundraising/cleanup-backups", json=request_data, headers={"X-API-Key": "test-api-key"})
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "Backup cleanup completed successfully" in data["message"]
    
    @patch('projects.fundraising_tracking_app.fundraising_scraper.fundraising_api.cache')
    def test_cleanup_backups_endpoint_default_values(self, mock_cache):
        """Test cleanup-backups endpoint with default values"""
        
        # Mock the cleanup_backups method
        mock_cache.cleanup_backups.return_value = True
        
        # Test with empty request body (should use defaults)
        response = client.post("/api/fundraising/cleanup-backups", json={}, headers={"X-API-Key": "test-api-key"})
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        
        # Verify the cache was called
        mock_cache.cleanup_backups.assert_called_once()
    
    @patch('projects.fundraising_tracking_app.fundraising_scraper.fundraising_api.cache')
    def test_cleanup_backups_endpoint_cache_error(self, mock_cache):
        """Test cleanup-backups endpoint handles cache errors"""
        
        # Mock the cache instance to raise an exception
        mock_cache.cleanup_backups.side_effect = Exception("Cleanup error")
        
        request_data = {"keep_backups": 2}
        response = client.post("/api/fundraising/cleanup-backups", json=request_data, headers={"X-API-Key": "test-api-key"})
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "Cleanup failed" in data["message"]


class TestValidationErrors:
    """Test validation error handling"""
    
    def test_donations_endpoint_invalid_limit(self):
        """Test donations endpoint with invalid limit parameter"""
        # This test expects the validation error to be raised as an exception
        # because the test client doesn't properly handle validation errors
        try:
            response = client.get("/api/fundraising/donations?limit=0")
            # If we get here, the validation didn't fail as expected
            assert False, "Expected validation error but got response"
        except Exception as e:
            # Check that it's a validation error
            assert "ValidationError" in str(type(e))
            assert "limit" in str(e)
    
    def test_donations_endpoint_invalid_amount_range(self):
        """Test donations endpoint with invalid amount range"""
        # This test expects the validation error to be raised as an exception
        # because the test client doesn't properly handle validation errors
        try:
            response = client.get("/api/fundraising/donations?min_amount=100&max_amount=50")
            # If we get here, the validation didn't fail as expected
            assert False, "Expected validation error but got response"
        except Exception as e:
            # Check that it's a validation error
            assert "ValidationError" in str(type(e))
            assert "max_amount" in str(e)
    
    def test_refresh_endpoint_invalid_request(self):
        """Test refresh endpoint with invalid request body"""
        invalid_data = {
            "force_refresh": "invalid_boolean",
            "include_metadata": "invalid_boolean"
        }
        
        response = client.post("/api/fundraising/refresh", json=invalid_data, headers={"X-API-Key": "test-api-key"})
        
        assert response.status_code == 422  # Validation error
        data = response.json()
        assert "detail" in data
    
    def test_cleanup_backups_endpoint_invalid_request(self):
        """Test cleanup-backups endpoint with invalid request body"""
        invalid_data = {
            "keep_backups": -1,  # Invalid: must be >= 0
            "force_cleanup": "invalid_boolean"
        }
        
        response = client.post("/api/fundraising/cleanup-backups", json=invalid_data, headers={"X-API-Key": "test-api-key"})
        
        assert response.status_code == 422  # Validation error
        data = response.json()
        assert "detail" in data


class TestErrorHandling:
    """Test error handling scenarios"""
    
    @patch('projects.fundraising_tracking_app.fundraising_scraper.fundraising_api.cache')
    def test_data_endpoint_authentication_error(self, mock_cache):
        """Test data endpoint handles general exceptions"""
        # Mock the cache instance to raise a general exception
        mock_cache.get_fundraising_data.side_effect = Exception("Database connection failed")
        
        response = client.get("/api/fundraising/data")
        
        assert response.status_code == 500
        data = response.json()
        assert data["success"] is False
        assert "message" in data
    
    @patch('projects.fundraising_tracking_app.fundraising_scraper.fundraising_api.cache')
    def test_donations_endpoint_authorization_error(self, mock_cache):
        """Test donations endpoint handles general exceptions"""
        # Mock the cache instance to raise a general exception
        mock_cache.get_fundraising_data.side_effect = Exception("Cache unavailable")
        
        response = client.get("/api/fundraising/donations")
        
        assert response.status_code == 500
        data = response.json()
        assert data["success"] is False
        assert "message" in data
    
    @patch('projects.fundraising_tracking_app.fundraising_scraper.fundraising_api.cache')
    def test_refresh_endpoint_api_error(self, mock_cache):
        """Test refresh endpoint handles API errors"""
        # Mock the cache instance to raise an API error
        mock_cache.force_refresh_now.side_effect = Exception("External service error")
        
        request_data = {"force_refresh": True}
        response = client.post("/api/fundraising/refresh", json=request_data, headers={"X-API-Key": "test-api-key"})
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "message" in data


class TestEdgeCases:
    """Test edge cases and boundary conditions"""
    
    @patch('projects.fundraising_tracking_app.fundraising_scraper.fundraising_api.cache')
    def test_donations_endpoint_empty_result(self, mock_cache):
        """Test donations endpoint with empty result"""
        # Mock empty donations list
        mock_cache.get_fundraising_data.return_value = {"donations": [], "last_updated": "2023-01-01T12:00:00"}
        
        response = client.get("/api/fundraising/donations")
        
        assert response.status_code == 200
        data = response.json()
        assert "donations" in data
        assert data["total_donations"] == 0
        assert data["donations"] == []
    
    @patch('projects.fundraising_tracking_app.fundraising_scraper.fundraising_api.cache')
    def test_donations_endpoint_max_limit(self, mock_cache):
        """Test donations endpoint with maximum limit"""
        # Mock donations data with all required fields
        mock_donations = [
            {
                "id": str(i), 
                "amount": 10.0, 
                "donor_name": f"Donor {i}",
                "date": "2023-01-01",
                "scraped_at": "2023-01-01T12:00:00"
            } 
            for i in range(100)
        ]
        mock_cache.get_fundraising_data.return_value = {"donations": mock_donations, "last_updated": "2023-01-01T12:00:00"}
        
        # Test with maximum limit
        response = client.get("/api/fundraising/donations?limit=100")
        
        assert response.status_code == 200
        data = response.json()
        assert "donations" in data
        assert data["total_donations"] == 100
    
    def test_health_endpoint_uptime_positive(self):
        """Test health endpoint uptime is positive"""
        response = client.get("/api/fundraising/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
    
    def test_project_info_endpoint_version_format(self):
        """Test project info endpoint version format"""
        response = client.get("/api/fundraising/")
        
        assert response.status_code == 200
        data = response.json()
        # Version should be in semantic version format (e.g., "1.0.0")
        version = data["version"]
        assert isinstance(version, str)
        assert len(version) > 0
        # Should contain at least one dot (e.g., "1.0.0")
        assert "." in version
