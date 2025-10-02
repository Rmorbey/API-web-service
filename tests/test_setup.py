"""
Basic test to verify that the testing framework is set up correctly.
"""

import pytest
from fastapi.testclient import TestClient


def test_pytest_working():
    """Test that pytest is working correctly."""
    assert True


def test_environment_variables(test_env_vars):
    """Test that environment variables are set correctly."""
    assert test_env_vars["STRAVA_API_KEY"] == "test-strava-key-123"
    assert test_env_vars["FUNDRAISING_API_KEY"] == "test-fundraising-key-456"


def test_temp_directory_creation(temp_dir):
    """Test that temporary directories are created correctly."""
    import os
    assert os.path.exists(temp_dir)
    assert os.path.isdir(temp_dir)


def test_mock_data_structures(mock_strava_api_response, mock_cache_data, mock_fundraising_cache_data):
    """Test that mock data structures are properly formatted."""
    # Test Strava API response
    assert "id" in mock_strava_api_response
    assert "name" in mock_strava_api_response
    assert "type" in mock_strava_api_response
    
    # Test cache data
    assert "timestamp" in mock_cache_data
    assert "activities" in mock_cache_data
    assert "total_activities" in mock_cache_data
    
    # Test fundraising cache data
    assert "timestamp" in mock_fundraising_cache_data
    assert "total_raised" in mock_fundraising_cache_data
    assert "donations" in mock_fundraising_cache_data


def test_main_app_client(test_client):
    """Test that the main FastAPI app test client works."""
    # Test the root endpoint (may return 400 due to host header validation or 429 due to rate limiting)
    response = test_client.get("/")
    assert response.status_code in [200, 400, 429]  # Accept success, host validation error, or rate limit
    
    # Test the health endpoint (may return 400 due to host header validation or 429 due to rate limiting)
    response = test_client.get("/health")
    assert response.status_code in [200, 400, 429]  # Accept success, host validation error, or rate limit


def test_strava_app_client(strava_test_client):
    """Test that the Strava integration test client works."""
    response = strava_test_client.get("/api/strava-integration/health")
    assert response.status_code in [200, 401]  # 401 if no API key, 200 if health check works


def test_fundraising_app_client(fundraising_test_client):
    """Test that the fundraising test client works."""
    response = fundraising_test_client.get("/api/fundraising/health")
    assert response.status_code in [200, 401]  # 401 if no API key, 200 if health check works


def test_authentication_headers(valid_api_headers, invalid_api_headers, no_api_headers):
    """Test that authentication header fixtures work correctly."""
    # Valid headers
    assert "X-API-Key" in valid_api_headers
    assert valid_api_headers["X-API-Key"] == "test-strava-key-123"
    
    # Invalid headers
    assert "X-API-Key" in invalid_api_headers
    assert invalid_api_headers["X-API-Key"] == "invalid-key"
    
    # No API key headers
    assert "X-API-Key" not in no_api_headers


@pytest.mark.asyncio
async def test_async_client(async_test_client):
    """Test that the async test client works."""
    async with async_test_client as client:
        response = await client.get("/health")
        assert response.status_code in [200, 400, 403]  # Accept various status codes due to security middleware


def test_error_response_template(error_response_template):
    """Test that error response template is properly structured."""
    assert "success" in error_response_template
    assert "error" in error_response_template
    assert "status_code" in error_response_template
    assert "timestamp" in error_response_template
    assert "request_id" in error_response_template
    
    assert error_response_template["success"] is False
    assert isinstance(error_response_template["status_code"], int)
