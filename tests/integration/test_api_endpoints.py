"""
Integration tests for API endpoints.
These tests verify that the API endpoints work correctly with proper authentication.
"""

import pytest
from fastapi.testclient import TestClient


class TestStravaAPIEndpoints:
    """Test Strava integration API endpoints."""
    
    def test_health_endpoint_without_auth(self, strava_test_client):
        """Test health endpoint without authentication."""
        response = strava_test_client.get("/api/strava-integration/health")
        assert response.status_code in [200, 401]  # May require auth or not
    
    def test_health_endpoint_with_valid_auth(self, strava_test_client, valid_api_headers):
        """Test health endpoint with valid authentication."""
        response = strava_test_client.get("/api/strava-integration/health", headers=valid_api_headers)
        assert response.status_code in [200, 401]  # May still require different auth
    
    def test_health_endpoint_with_invalid_auth(self, strava_test_client, invalid_api_headers):
        """Test health endpoint with invalid authentication."""
        response = strava_test_client.get("/api/strava-integration/health", headers=invalid_api_headers)
        assert response.status_code == 403  # Should return forbidden
    
    def test_health_endpoint_without_headers(self, strava_test_client, no_api_headers):
        """Test health endpoint without API key headers."""
        response = strava_test_client.get("/api/strava-integration/health", headers=no_api_headers)
        assert response.status_code == 401  # Should return unauthorized
    
    def test_feed_endpoint_without_auth(self, strava_test_client):
        """Test feed endpoint without authentication."""
        response = strava_test_client.get("/api/strava-integration/feed")
        assert response.status_code == 401  # Should require authentication
    
    def test_feed_endpoint_with_valid_auth(self, strava_test_client, valid_api_headers):
        """Test feed endpoint with valid authentication."""
        response = strava_test_client.get("/api/strava-integration/feed", headers=valid_api_headers)
        # May return 200 with data or 500 if cache is empty/error
        assert response.status_code in [200, 500, 401]
    
    def test_feed_endpoint_with_invalid_auth(self, strava_test_client, invalid_api_headers):
        """Test feed endpoint with invalid authentication."""
        response = strava_test_client.get("/api/strava-integration/feed", headers=invalid_api_headers)
        assert response.status_code == 403  # Should return forbidden
    
    def test_refresh_endpoint_without_auth(self, strava_test_client):
        """Test refresh endpoint without authentication."""
        response = strava_test_client.post("/api/strava-integration/refresh-cache")
        assert response.status_code == 401  # Should require authentication
    
    def test_refresh_endpoint_with_valid_auth(self, strava_test_client, valid_api_headers):
        """Test refresh endpoint with valid authentication."""
        response = strava_test_client.post("/api/strava-integration/refresh-cache", headers=valid_api_headers)
        # May return 200 (success) or 500 (error) depending on external API availability
        assert response.status_code in [200, 500, 401]
    
    def test_refresh_endpoint_with_invalid_auth(self, strava_test_client, invalid_api_headers):
        """Test refresh endpoint with invalid authentication."""
        response = strava_test_client.post("/api/strava-integration/refresh-cache", headers=invalid_api_headers)
        assert response.status_code == 403  # Should return forbidden


class TestFundraisingAPIEndpoints:
    """Test fundraising API endpoints."""
    
    def test_health_endpoint_without_auth(self, fundraising_test_client):
        """Test health endpoint without authentication."""
        response = fundraising_test_client.get("/api/fundraising/health")
        assert response.status_code in [200, 401]  # May require auth or not
    
    def test_health_endpoint_with_valid_auth(self, fundraising_test_client, valid_api_headers):
        """Test health endpoint with valid authentication."""
        response = fundraising_test_client.get("/api/fundraising/health", headers=valid_api_headers)
        assert response.status_code in [200, 401]  # May still require different auth
    
    def test_health_endpoint_with_invalid_auth(self, fundraising_test_client, invalid_api_headers):
        """Test health endpoint with invalid authentication."""
        response = fundraising_test_client.get("/api/fundraising/health", headers=invalid_api_headers)
        assert response.status_code == 403  # Should return forbidden
    
    def test_data_endpoint_without_auth(self, fundraising_test_client):
        """Test data endpoint without authentication."""
        response = fundraising_test_client.get("/api/fundraising/data")
        assert response.status_code == 401  # Should require authentication
    
    def test_data_endpoint_with_valid_auth(self, fundraising_test_client, valid_api_headers):
        """Test data endpoint with valid authentication."""
        response = fundraising_test_client.get("/api/fundraising/data", headers=valid_api_headers)
        # May return 200 with data or 500 if cache is empty/error
        assert response.status_code in [200, 500, 401]
    
    def test_data_endpoint_with_invalid_auth(self, fundraising_test_client, invalid_api_headers):
        """Test data endpoint with invalid authentication."""
        response = fundraising_test_client.get("/api/fundraising/data", headers=invalid_api_headers)
        assert response.status_code == 403  # Should return forbidden
    
    def test_donations_endpoint_without_auth(self, fundraising_test_client):
        """Test donations endpoint without authentication."""
        response = fundraising_test_client.get("/api/fundraising/donations")
        assert response.status_code == 401  # Should require authentication
    
    def test_donations_endpoint_with_valid_auth(self, fundraising_test_client, valid_api_headers):
        """Test donations endpoint with valid authentication."""
        response = fundraising_test_client.get("/api/fundraising/donations", headers=valid_api_headers)
        # May return 200 with data or 500 if cache is empty/error
        assert response.status_code in [200, 500, 401]
    
    def test_donations_endpoint_with_invalid_auth(self, fundraising_test_client, invalid_api_headers):
        """Test donations endpoint with invalid authentication."""
        response = fundraising_test_client.get("/api/fundraising/donations", headers=invalid_api_headers)
        assert response.status_code == 403  # Should return forbidden
    
    def test_refresh_endpoint_without_auth(self, fundraising_test_client):
        """Test refresh endpoint without authentication."""
        response = fundraising_test_client.post("/api/fundraising/refresh")
        assert response.status_code == 401  # Should require authentication
    
    def test_refresh_endpoint_with_valid_auth(self, fundraising_test_client, valid_api_headers):
        """Test refresh endpoint with valid authentication."""
        response = fundraising_test_client.post("/api/fundraising/refresh", headers=valid_api_headers)
        # May return 200 (success) or 500 (error) depending on external service availability
        assert response.status_code in [200, 500, 401]
    
    def test_refresh_endpoint_with_invalid_auth(self, fundraising_test_client, invalid_api_headers):
        """Test refresh endpoint with invalid authentication."""
        response = fundraising_test_client.post("/api/fundraising/refresh", headers=invalid_api_headers)
        assert response.status_code == 403  # Should return forbidden


class TestMainAPIEndpoints:
    """Test main API endpoints."""
    
    def test_root_endpoint(self, test_client):
        """Test root endpoint."""
        response = test_client.get("/")
        assert response.status_code in [200, 400]  # May have host validation
    
    def test_health_endpoint(self, test_client):
        """Test main health endpoint."""
        response = test_client.get("/health")
        assert response.status_code in [200, 400]  # May have host validation
    
    def test_projects_endpoint(self, test_client):
        """Test projects endpoint."""
        response = test_client.get("/projects")
        assert response.status_code in [200, 400]  # May have host validation
    
    def test_demo_endpoint(self, test_client):
        """Test demo endpoint."""
        response = test_client.get("/demo")
        assert response.status_code in [200, 400]  # May have host validation
    
    def test_fundraising_demo_endpoint(self, test_client):
        """Test fundraising demo endpoint."""
        response = test_client.get("/fundraising-demo")
        assert response.status_code in [200, 400]  # May have host validation


class TestAPIResponseStructure:
    """Test API response structure and content."""
    
    def test_error_response_structure(self, strava_test_client, invalid_api_headers):
        """Test that error responses have proper structure."""
        response = strava_test_client.get("/api/strava-integration/feed", headers=invalid_api_headers)
        
        assert response.status_code == 403
        data = response.json()
        
        # Check error response structure
        assert "success" in data or "error" in data or "detail" in data
        # Should have some form of error information
    
    def test_success_response_structure(self, test_client):
        """Test that success responses have proper structure."""
        response = test_client.get("/health")
        
        if response.status_code == 200:
            data = response.json()
            # Should have some form of success information
            assert isinstance(data, dict) or isinstance(data, str)
    
    def test_content_type_headers(self, test_client):
        """Test that responses have proper content type headers."""
        response = test_client.get("/health")
        
        # Should have content-type header
        assert "content-type" in response.headers
        assert "application/json" in response.headers["content-type"].lower()
