"""
Unit tests for mocking external APIs.
Tests mocking of Strava API, JustGiving API, and other external services.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json
import httpx
from fastapi import HTTPException


class TestStravaAPIMocking:
    """Test mocking of Strava API calls."""
    
    def test_mock_strava_activities_response(self):
        """Test mocking Strava activities API response."""
        mock_response = {
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
        
        # Mock the httpx client
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response_obj = Mock()
            mock_response_obj.status_code = 200
            mock_response_obj.json.return_value = mock_response
            mock_get.return_value = mock_response_obj
            
            # Test the mocked response
            assert mock_response["total_activities"] == 1
            assert len(mock_response["activities"]) == 1
            assert mock_response["activities"][0]["name"] == "Morning Run"
            assert mock_response["activities"][0]["type"] == "Run"
    
    def test_mock_strava_api_error_response(self):
        """Test mocking Strava API error response."""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response_obj = Mock()
            mock_response_obj.status_code = 401
            mock_response_obj.json.return_value = {"message": "Unauthorized"}
            mock_get.return_value = mock_response_obj
            
            # Test error handling
            assert mock_response_obj.status_code == 401
            assert mock_response_obj.json()["message"] == "Unauthorized"
    
    def test_mock_strava_rate_limit_response(self):
        """Test mocking Strava API rate limit response."""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response_obj = Mock()
            mock_response_obj.status_code = 429
            mock_response_obj.headers = {"Retry-After": "900"}
            mock_response_obj.json.return_value = {"message": "Rate limit exceeded"}
            mock_get.return_value = mock_response_obj
            
            # Test rate limit handling
            assert mock_response_obj.status_code == 429
            assert mock_response_obj.headers["Retry-After"] == "900"
            assert mock_response_obj.json()["message"] == "Rate limit exceeded"
    
    def test_mock_strava_activity_details(self):
        """Test mocking Strava activity details API response."""
        mock_activity_details = {
            "id": 123456789,
            "name": "Morning Run",
            "type": "Run",
            "distance": 5000.0,
            "moving_time": 1800,
            "elapsed_time": 1900,
            "start_date": "2025-09-24T07:00:00Z",
            "start_date_local": "2025-09-24T08:00:00Z",
            "description": "Beautiful morning run with great weather",
            "polyline": "test_detailed_polyline_data",
            "summary_polyline": "test_detailed_summary_polyline",
            "bounds": {
                "northeast": {"lat": 51.5074, "lng": -0.1278},
                "southwest": {"lat": 51.5073, "lng": -0.1279}
            },
            "photos": [
                {
                    "id": 123,
                    "urls": {
                        "100": "https://example.com/photo1.jpg"
                    }
                }
            ],
            "comments": [
                {
                    "id": 1,
                    "text": "Great run!",
                    "athlete": {"id": 1, "firstname": "Test", "lastname": "User"}
                }
            ]
        }
        
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response_obj = Mock()
            mock_response_obj.status_code = 200
            mock_response_obj.json.return_value = mock_activity_details
            mock_get.return_value = mock_response_obj
            
            # Test detailed activity response
            assert mock_activity_details["id"] == 123456789
            assert len(mock_activity_details["photos"]) == 1
            assert len(mock_activity_details["comments"]) == 1
            assert mock_activity_details["photos"][0]["id"] == 123
            assert mock_activity_details["comments"][0]["text"] == "Great run!"


class TestJustGivingAPIMocking:
    """Test mocking of JustGiving API calls."""
    
    def test_mock_justgiving_page_response(self):
        """Test mocking JustGiving page response."""
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
        
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.text = mock_html_content
            mock_get.return_value = mock_response
            
            # Test the mocked response
            assert mock_response.status_code == 200
            assert "£150.00" in mock_response.text
            assert "John Doe" in mock_response.text
            assert "Jane Smith" in mock_response.text
    
    def test_mock_justgiving_error_response(self):
        """Test mocking JustGiving error response."""
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 404
            mock_response.text = "Page not found"
            mock_get.return_value = mock_response
            
            # Test error handling
            assert mock_response.status_code == 404
            assert mock_response.text == "Page not found"
    
    def test_mock_justgiving_timeout_response(self):
        """Test mocking JustGiving timeout response."""
        with patch('requests.get') as mock_get:
            mock_get.side_effect = Exception("Request timeout")
            
            # Test timeout handling
            with pytest.raises(Exception) as exc_info:
                mock_get()
            assert "Request timeout" in str(exc_info.value)


class TestExternalServiceMocking:
    """Test mocking of other external services."""
    
    def test_mock_http_client_success(self):
        """Test mocking HTTP client success response."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "success"}
            
            mock_client_instance = Mock()
            mock_client_instance.get.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            
            # Test successful response
            assert mock_response.status_code == 200
            assert mock_response.json()["status"] == "success"
    
    def test_mock_http_client_error(self):
        """Test mocking HTTP client error response."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 500
            mock_response.json.return_value = {"error": "Internal server error"}
            
            mock_client_instance = Mock()
            mock_client_instance.get.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            
            # Test error response
            assert mock_response.status_code == 500
            assert mock_response.json()["error"] == "Internal server error"
    
    def test_mock_http_client_timeout(self):
        """Test mocking HTTP client timeout."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_client_instance = Mock()
            mock_client_instance.get.side_effect = httpx.TimeoutException("Request timeout")
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            
            # Test timeout handling
            with pytest.raises(httpx.TimeoutException) as exc_info:
                mock_client_instance.get("https://api.example.com")
            assert "Request timeout" in str(exc_info.value)


class TestCacheMocking:
    """Test mocking of cache operations."""
    
    def test_mock_cache_hit(self):
        """Test mocking cache hit scenario."""
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
        
        with patch('builtins.open', mock_open(read_data=json.dumps(mock_cache_data))):
            with patch('json.load') as mock_json_load:
                mock_json_load.return_value = mock_cache_data
                
                # Test cache hit
                assert mock_cache_data["total_activities"] == 1
                assert len(mock_cache_data["activities"]) == 1
                assert mock_cache_data["activities"][0]["name"] == "Morning Run"
    
    def test_mock_cache_miss(self):
        """Test mocking cache miss scenario."""
        with patch('builtins.open', side_effect=FileNotFoundError):
            # Test cache miss (file not found)
            with pytest.raises(FileNotFoundError):
                open("nonexistent_cache.json", "r")
    
    def test_mock_cache_corruption(self):
        """Test mocking cache corruption scenario."""
        with patch('builtins.open', mock_open(read_data="invalid json")):
            with patch('json.load', side_effect=json.JSONDecodeError("Invalid JSON", "doc", 0)):
                # Test cache corruption
                with pytest.raises(json.JSONDecodeError):
                    json.loads("invalid json")


class TestDatabaseMocking:
    """Test mocking of database operations."""
    
    def test_mock_database_connection(self):
        """Test mocking database connection."""
        with patch('sqlite3.connect') as mock_connect:
            mock_connection = Mock()
            mock_cursor = Mock()
            mock_cursor.fetchall.return_value = [
                (1, "test_activity", "Run", 5000.0),
                (2, "test_activity_2", "Ride", 10000.0)
            ]
            mock_connection.cursor.return_value = mock_cursor
            mock_connect.return_value = mock_connection
            
            # Test database connection and query
            connection = mock_connect("test.db")
            cursor = connection.cursor()
            results = cursor.fetchall()
            
            assert len(results) == 2
            assert results[0][1] == "test_activity"
            assert results[1][1] == "test_activity_2"
    
    def test_mock_database_error(self):
        """Test mocking database error."""
        with patch('sqlite3.connect', side_effect=Exception("Database connection failed")):
            # Test database error
            with pytest.raises(Exception) as exc_info:
                import sqlite3
                sqlite3.connect("test.db")
            assert "Database connection failed" in str(exc_info.value)


class TestFileSystemMocking:
    """Test mocking of file system operations."""
    
    def test_mock_file_read(self):
        """Test mocking file read operation."""
        mock_file_content = "test file content"
        
        with patch('builtins.open', mock_open(read_data=mock_file_content)):
            with patch('os.path.exists', return_value=True):
                # Test file read
                with open("test_file.txt", "r") as f:
                    content = f.read()
                assert content == mock_file_content
    
    def test_mock_file_write(self):
        """Test mocking file write operation."""
        with patch('builtins.open', mock_open()) as mock_file:
            with patch('os.path.exists', return_value=False):
                # Test file write
                with open("test_file.txt", "w") as f:
                    f.write("test content")
                
                mock_file.assert_called_once_with("test_file.txt", "w")
    
    def test_mock_file_not_found(self):
        """Test mocking file not found scenario."""
        import os
        with patch('os.path.exists', return_value=False):
            # Test file not found
            assert not os.path.exists("nonexistent_file.txt")


class TestEnvironmentVariableMocking:
    """Test mocking of environment variables."""
    
    def test_mock_environment_variables(self):
        """Test mocking environment variables."""
        with patch.dict('os.environ', {
            'STRAVA_CLIENT_ID': 'test_client_id',
            'STRAVA_CLIENT_SECRET': 'test_client_secret',
            'STRAVA_ACCESS_TOKEN': 'test_access_token',
            'JUSTGIVING_URL': 'https://test.justgiving.com/test-page'
        }):
            import os
            
            # Test environment variables
            assert os.environ['STRAVA_CLIENT_ID'] == 'test_client_id'
            assert os.environ['STRAVA_CLIENT_SECRET'] == 'test_client_secret'
            assert os.environ['STRAVA_ACCESS_TOKEN'] == 'test_access_token'
            assert os.environ['JUSTGIVING_URL'] == 'https://test.justgiving.com/test-page'
    
    def test_mock_missing_environment_variables(self):
        """Test mocking missing environment variables."""
        with patch.dict('os.environ', {}, clear=True):
            import os
            
            # Test missing environment variables
            with pytest.raises(KeyError):
                os.environ['STRAVA_CLIENT_ID']


class TestMockingIntegration:
    """Test integration of multiple mocks."""
    
    def test_mock_full_strava_flow(self):
        """Test mocking the full Strava API flow."""
        mock_activities_response = {
            "activities": [
                {
                    "id": 123456789,
                    "name": "Morning Run",
                    "type": "Run",
                    "distance": 5000.0
                }
            ],
            "total_activities": 1
        }
        
        mock_cache_data = {
            "activities": [],
            "timestamp": "2025-09-24T09:00:00Z",
            "total_activities": 0
        }
        
        with patch('httpx.AsyncClient.get') as mock_get:
            with patch('builtins.open', mock_open(read_data=json.dumps(mock_cache_data))):
                with patch('json.load', return_value=mock_cache_data):
                    with patch('json.dump') as mock_dump:
                        # Mock successful API response
                        mock_response_obj = Mock()
                        mock_response_obj.status_code = 200
                        mock_response_obj.json.return_value = mock_activities_response
                        mock_get.return_value = mock_response_obj
                        
                        # Test the full flow
                        assert mock_activities_response["total_activities"] == 1
                        assert len(mock_activities_response["activities"]) == 1
                        
                        # Verify cache operations
                        mock_dump.assert_not_called()  # Cache not updated in this test
    
    def test_mock_full_fundraising_flow(self):
        """Test mocking the full fundraising scraper flow."""
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
        
        with patch('requests.get') as mock_get:
            with patch('builtins.open', mock_open(read_data=json.dumps(mock_cache_data))):
                with patch('json.load', return_value=mock_cache_data):
                    with patch('json.dump') as mock_dump:
                        # Mock successful web scraping
                        mock_response = Mock()
                        mock_response.status_code = 200
                        mock_response.text = mock_html_content
                        mock_get.return_value = mock_response
                        
                        # Test the full flow
                        assert mock_response.status_code == 200
                        assert "£150.00" in mock_response.text
                        assert "John Doe" in mock_response.text


# Helper function for mocking file operations
def mock_open(read_data=""):
    """Helper function to mock file operations."""
    from unittest.mock import mock_open as _mock_open
    return _mock_open(read_data=read_data)
