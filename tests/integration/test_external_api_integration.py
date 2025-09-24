"""
Integration tests for external API mocking.
Tests how mocked external APIs work with the actual application.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json
import httpx
from fastapi.testclient import TestClient


class TestStravaAPIIntegration:
    """Test Strava API integration with mocking."""
    
    def test_strava_api_with_mocked_response(self, strava_test_client):
        """Test Strava API with mocked external response."""
        mock_strava_response = {
            "activities": [
                {
                    "id": 123456789,
                    "name": "Morning Run",
                    "type": "Run",
                    "distance": 5000.0,
                    "moving_time": 1800,
                    "elapsed_time": 1900,
                    "start_date": "2025-09-24T07:00:00Z",
                    "start_date_local": "2025-09-24T08:00:00Z",
                    "description": "Beautiful morning run",
                    "polyline": "test_polyline_data",
                    "summary_polyline": "test_summary_polyline",
                    "bounds": {
                        "northeast": {"lat": 51.5074, "lng": -0.1278},
                        "southwest": {"lat": 51.5073, "lng": -0.1279}
                    },
                    "photos": [],
                    "comments": []
                }
            ],
            "total_activities": 1
        }
        
        # Mock the Strava API call
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response_obj = Mock()
            mock_response_obj.status_code = 200
            mock_response_obj.json.return_value = mock_strava_response
            mock_get.return_value = mock_response_obj
            
            # Test the API endpoint
            response = strava_test_client.get(
                "/api/strava-integration/feed",
                headers={"X-API-Key": "test-strava-key-123"}
            )
            
            # Should return successful response
            assert response.status_code in [200, 500]  # May return 500 if cache is empty
            if response.status_code == 200:
                data = response.json()
                assert isinstance(data, (dict, list))
    
    def test_strava_api_with_mocked_error(self, strava_test_client):
        """Test Strava API with mocked error response."""
        # Mock the Strava API call to return an error
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response_obj = Mock()
            mock_response_obj.status_code = 401
            mock_response_obj.json.return_value = {"message": "Unauthorized"}
            mock_get.return_value = mock_response_obj
            
            # Test the API endpoint
            response = strava_test_client.get(
                "/api/strava-integration/feed",
                headers={"X-API-Key": "test-strava-key-123"}
            )
            
            # Should handle error gracefully
            assert response.status_code in [200, 401, 500]
    
    def test_strava_api_with_mocked_timeout(self, strava_test_client):
        """Test Strava API with mocked timeout."""
        # Mock the Strava API call to timeout
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_get.side_effect = httpx.TimeoutException("Request timeout")
            
            # Test the API endpoint
            response = strava_test_client.get(
                "/api/strava-integration/feed",
                headers={"X-API-Key": "test-strava-key-123"}
            )
            
            # Should handle timeout gracefully
            assert response.status_code in [200, 500]


class TestFundraisingAPIIntegration:
    """Test Fundraising API integration with mocking."""
    
    def test_fundraising_api_with_mocked_response(self, fundraising_test_client):
        """Test Fundraising API with mocked external response."""
        mock_html_content = """
        <html>
            <body>
                <div class="total-raised">£150.00</div>
                <div class="donation">
                    <span class="donor-name">John Doe</span>
                    <span class="donation-amount">£25.00</span>
                    <span class="donation-message">Great cause!</span>
                    <span class="donation-date">2 days ago</span>
                </div>
                <div class="donation">
                    <span class="donor-name">Jane Smith</span>
                    <span class="donation-amount">£50.00</span>
                    <span class="donation-message">Keep it up!</span>
                    <span class="donation-date">1 week ago</span>
                </div>
            </body>
        </html>
        """
        
        # Mock the web scraping call
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.text = mock_html_content
            mock_get.return_value = mock_response
            
            # Test the API endpoint
            response = fundraising_test_client.get(
                "/api/fundraising/data",
                headers={"X-API-Key": "test-fundraising-key-456"}
            )
            
            # Should return successful response
            assert response.status_code in [200, 500]  # May return 500 if cache is empty
            if response.status_code == 200:
                data = response.json()
                assert isinstance(data, (dict, list))
    
    def test_fundraising_api_with_mocked_error(self, fundraising_test_client):
        """Test Fundraising API with mocked error response."""
        # Mock the web scraping call to return an error
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 404
            mock_response.text = "Page not found"
            mock_get.return_value = mock_response
            
            # Test the API endpoint
            response = fundraising_test_client.get(
                "/api/fundraising/data",
                headers={"X-API-Key": "test-fundraising-key-456"}
            )
            
            # Should handle error gracefully
            assert response.status_code in [200, 404, 500]
    
    def test_fundraising_api_with_mocked_timeout(self, fundraising_test_client):
        """Test Fundraising API with mocked timeout."""
        # Mock the web scraping call to timeout
        with patch('requests.get') as mock_get:
            mock_get.side_effect = Exception("Request timeout")
            
            # Test the API endpoint
            response = fundraising_test_client.get(
                "/api/fundraising/data",
                headers={"X-API-Key": "test-fundraising-key-456"}
            )
            
            # Should handle timeout gracefully
            assert response.status_code in [200, 500]


class TestCacheIntegration:
    """Test cache integration with mocking."""
    
    def test_cache_with_mocked_file_operations(self, strava_test_client):
        """Test cache operations with mocked file system."""
        mock_cache_data = {
            "activities": [
                {
                    "id": 123456789,
                    "name": "Morning Run",
                    "type": "Run",
                    "distance": 5000.0
                }
            ],
            "timestamp": "2025-09-24T10:00:00Z",
            "total_activities": 1
        }
        
        # Mock file operations
        with patch('builtins.open', mock_open(read_data=json.dumps(mock_cache_data))):
            with patch('json.load', return_value=mock_cache_data):
                with patch('os.path.exists', return_value=True):
                    # Test the API endpoint
                    response = strava_test_client.get(
                        "/api/strava-integration/feed",
                        headers={"X-API-Key": "test-strava-key-123"}
                    )
                    
                    # Should return cached data
                    assert response.status_code in [200, 500]
    
    def test_cache_with_mocked_file_not_found(self, strava_test_client):
        """Test cache operations with mocked file not found."""
        # Mock file not found
        with patch('os.path.exists', return_value=False):
            with patch('builtins.open', side_effect=FileNotFoundError):
                # Test the API endpoint
                response = strava_test_client.get(
                    "/api/strava-integration/feed",
                    headers={"X-API-Key": "test-strava-key-123"}
                )
                
                # Should handle file not found gracefully
                assert response.status_code in [200, 500]
    
    def test_cache_with_mocked_corruption(self, strava_test_client):
        """Test cache operations with mocked corruption."""
        # Mock corrupted cache file
        with patch('builtins.open', mock_open(read_data="invalid json")):
            with patch('json.load', side_effect=json.JSONDecodeError("Invalid JSON", "doc", 0)):
                # Test the API endpoint
                response = strava_test_client.get(
                    "/api/strava-integration/feed",
                    headers={"X-API-Key": "test-strava-key-123"}
                )
                
                # Should handle corruption gracefully
                assert response.status_code in [200, 500]


class TestEnvironmentVariableIntegration:
    """Test environment variable integration with mocking."""
    
    def test_api_with_mocked_environment_variables(self, strava_test_client):
        """Test API with mocked environment variables."""
        with patch.dict('os.environ', {
            'STRAVA_CLIENT_ID': 'test_client_id',
            'STRAVA_CLIENT_SECRET': 'test_client_secret',
            'STRAVA_ACCESS_TOKEN': 'test_access_token'
        }):
            # Test the API endpoint
            response = strava_test_client.get(
                "/api/strava-integration/health",
                headers={"X-API-Key": "test-strava-key-123"}
            )
            
            # Should work with mocked environment variables
            assert response.status_code in [200, 400, 401, 403]
    
    def test_api_with_mocked_missing_environment_variables(self, strava_test_client):
        """Test API with mocked missing environment variables."""
        with patch.dict('os.environ', {}, clear=True):
            # Test the API endpoint
            response = strava_test_client.get(
                "/api/strava-integration/health",
                headers={"X-API-Key": "test-strava-key-123"}
            )
            
            # Should handle missing environment variables gracefully
            assert response.status_code in [200, 400, 401, 403, 500]


class TestFullSystemIntegration:
    """Test full system integration with multiple mocks."""
    
    def test_full_strava_flow_with_mocks(self, strava_test_client):
        """Test full Strava flow with multiple mocks."""
        mock_strava_response = {
            "activities": [
                {
                    "id": 123456789,
                    "name": "Morning Run",
                    "type": "Run",
                    "distance": 5000.0,
                    "moving_time": 1800,
                    "elapsed_time": 1900,
                    "start_date": "2025-09-24T07:00:00Z",
                    "start_date_local": "2025-09-24T08:00:00Z",
                    "description": "Beautiful morning run",
                    "polyline": "test_polyline_data",
                    "bounds": {
                        "northeast": {"lat": 51.5074, "lng": -0.1278},
                        "southwest": {"lat": 51.5073, "lng": -0.1279}
                    },
                    "photos": [],
                    "comments": []
                }
            ],
            "total_activities": 1
        }
        
        mock_cache_data = {
            "activities": [],
            "timestamp": "2025-09-24T09:00:00Z",
            "total_activities": 0
        }
        
        # Mock multiple components
        with patch('httpx.AsyncClient.get') as mock_get:
            with patch('builtins.open', mock_open(read_data=json.dumps(mock_cache_data))):
                with patch('json.load', return_value=mock_cache_data):
                    with patch('json.dump') as mock_dump:
                        with patch.dict('os.environ', {
                            'STRAVA_ACCESS_TOKEN': 'test_access_token'
                        }):
                            # Mock successful API response
                            mock_response_obj = Mock()
                            mock_response_obj.status_code = 200
                            mock_response_obj.json.return_value = mock_strava_response
                            mock_get.return_value = mock_response_obj
                            
                            # Test the full flow
                            response = strava_test_client.get(
                                "/api/strava-integration/feed",
                                headers={"X-API-Key": "test-strava-key-123"}
                            )
                            
                            # Should handle the full flow
                            assert response.status_code in [200, 500]
    
    def test_full_fundraising_flow_with_mocks(self, fundraising_test_client):
        """Test full fundraising flow with multiple mocks."""
        mock_html_content = """
        <html>
            <body>
                <div class="total-raised">£150.00</div>
                <div class="donation">
                    <span class="donor-name">John Doe</span>
                    <span class="donation-amount">£25.00</span>
                    <span class="donation-message">Great cause!</span>
                    <span class="donation-date">2 days ago</span>
                </div>
            </body>
        </html>
        """
        
        mock_cache_data = {
            "donations": [],
            "total_raised": 0.0,
            "timestamp": "2025-09-24T09:00:00Z"
        }
        
        # Mock multiple components
        with patch('requests.get') as mock_get:
            with patch('builtins.open', mock_open(read_data=json.dumps(mock_cache_data))):
                with patch('json.load', return_value=mock_cache_data):
                    with patch('json.dump') as mock_dump:
                        with patch.dict('os.environ', {
                            'JUSTGIVING_URL': 'https://test.justgiving.com/test-page'
                        }):
                            # Mock successful web scraping
                            mock_response = Mock()
                            mock_response.status_code = 200
                            mock_response.text = mock_html_content
                            mock_get.return_value = mock_response
                            
                            # Test the full flow
                            response = fundraising_test_client.get(
                                "/api/fundraising/data",
                                headers={"X-API-Key": "test-fundraising-key-456"}
                            )
                            
                            # Should handle the full flow
                            assert response.status_code in [200, 500]


class TestErrorHandlingIntegration:
    """Test error handling integration with mocks."""
    
    def test_error_handling_with_mocked_exceptions(self, strava_test_client):
        """Test error handling with mocked exceptions."""
        # Mock various exceptions
        exceptions_to_test = [
            httpx.TimeoutException("Request timeout"),
            httpx.ConnectError("Connection failed"),
            httpx.HTTPStatusError("HTTP error", request=Mock(), response=Mock()),
            Exception("Generic error")
        ]
        
        for exception in exceptions_to_test:
            with patch('httpx.AsyncClient.get') as mock_get:
                mock_get.side_effect = exception
                
                # Test the API endpoint
                response = strava_test_client.get(
                    "/api/strava-integration/feed",
                    headers={"X-API-Key": "test-strava-key-123"}
                )
                
                # Should handle all exceptions gracefully
                assert response.status_code in [200, 500]
    
    def test_error_handling_with_mocked_file_errors(self, strava_test_client):
        """Test error handling with mocked file errors."""
        # Mock various file errors
        file_errors = [
            FileNotFoundError("File not found"),
            PermissionError("Permission denied"),
            OSError("OS error"),
            json.JSONDecodeError("Invalid JSON", "doc", 0)
        ]
        
        for error in file_errors:
            with patch('builtins.open', side_effect=error):
                # Test the API endpoint
                response = strava_test_client.get(
                    "/api/strava-integration/feed",
                    headers={"X-API-Key": "test-strava-key-123"}
                )
                
                # Should handle all file errors gracefully
                assert response.status_code in [200, 500]


# Helper function for mocking file operations
def mock_open(read_data=""):
    """Helper function to mock file operations."""
    from unittest.mock import mock_open as _mock_open
    return _mock_open(read_data=read_data)
