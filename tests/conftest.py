"""
Shared pytest fixtures and configuration for the entire test suite.
"""

import os
import sys
import tempfile
import shutil
from typing import Generator, Dict, Any, List
from unittest.mock import Mock, patch
import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient

# Add project root to Python path for imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Set test environment variables
os.environ["STRAVA_API_KEY"] = "test-strava-key-123"
os.environ["FUNDRAISING_API_KEY"] = "test-fundraising-key-456"
os.environ["STRAVA_ACCESS_TOKEN"] = "test-strava-token-789"
os.environ["JAWG_API_KEY"] = "test-jawg-key-abc"
os.environ["JUSTGIVING_URL"] = "https://test-justgiving.com/test-page"

@pytest.fixture(scope="session")
def test_env_vars() -> Dict[str, str]:
    """Provide test environment variables."""
    return {
        "STRAVA_API_KEY": "test-strava-key-123",
        "FUNDRAISING_API_KEY": "test-fundraising-key-456", 
        "STRAVA_ACCESS_TOKEN": "test-strava-token-789",
        "JAWG_API_KEY": "test-jawg-key-abc",
        "JUSTGIVING_URL": "https://test-justgiving.com/test-page"
    }

@pytest.fixture(scope="function")
def temp_dir() -> Generator[str, None, None]:
    """Create a temporary directory for test files."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)

@pytest.fixture(scope="function")
def mock_strava_api_response() -> Dict[str, Any]:
    """Mock Strava API response data."""
    return {
        "id": 123456789,
        "name": "Test Activity",
        "type": "Run",
        "distance": 5000.0,
        "moving_time": 1800,
        "elapsed_time": 1900,
        "start_date": "2025-01-01T10:00:00Z",
        "start_date_local": "2025-01-01T10:00:00Z",
        "description": "Test run description",
        "polyline": "test_polyline_data",
        "summary_polyline": "test_summary_polyline_data",
        "photos": {
            "primary": {
                "id": 123,
                "urls": {
                    "100": "https://example.com/photo.jpg"
                }
            }
        },
        "comments": [
            {
                "id": 1,
                "text": "Great run!",
                "athlete": {"id": 1, "firstname": "Test", "lastname": "User"}
            }
        ]
    }

@pytest.fixture(scope="function")
def mock_justgiving_html() -> str:
    """Mock JustGiving HTML content."""
    return """
    <html>
        <body>
            <div class="total-raised">£150.00</div>
            <div class="donation">
                <span class="donor-name">Test Donor</span>
                <span class="amount">£25.00</span>
                <span class="message">Great cause!</span>
                <span class="date">2 days ago</span>
            </div>
        </body>
    </html>
    """

@pytest.fixture(scope="function")
def mock_cache_data() -> Dict[str, Any]:
    """Mock cache data structure."""
    return {
        "timestamp": "2025-01-01T10:00:00Z",
        "last_updated": "2025-01-01T10:00:00Z",
        "version": "1.0",
        "activities": [
            {
                "id": 123456789,
                "name": "Test Activity",
                "type": "Run",
                "distance": 5000.0,
                "moving_time": 1800,
                "start_date_local": "2025-01-01T10:00:00Z",
                "description": "Test description",
                "polyline": "test_polyline",
                "bounds": {"northeast": {"lat": 51.5, "lng": -0.1}, "southwest": {"lat": 51.4, "lng": -0.2}},
                "photos": [],
                "comments": []
            }
        ],
        "total_activities": 1
    }

@pytest.fixture(scope="function")
def mock_fundraising_cache_data() -> Dict[str, Any]:
    """Mock fundraising cache data structure."""
    return {
        "timestamp": "2025-01-01T10:00:00Z",
        "last_updated": "2025-01-01T10:00:00Z",
        "version": "1.0",
        "total_raised": 150.0,
        "total_donations": 1,
        "donations": [
            {
                "donor_name": "Test Donor",
                "amount": 25.0,
                "message": "Great cause!",
                "date": "2 days ago",
                "scraped_at": "2025-01-01T10:00:00Z"
            }
        ]
    }

@pytest.fixture(scope="function")
def mock_httpx_client():
    """Mock httpx client for external API calls."""
    with patch('httpx.AsyncClient') as mock_client:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}
        mock_response.text = "Mock response"
        
        mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
        mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
        
        yield mock_client

@pytest.fixture(scope="function")
def mock_requests():
    """Mock requests library for web scraping."""
    with patch('requests.get') as mock_get:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "<html>Mock HTML</html>"
        mock_response.content = b"<html>Mock HTML</html>"
        mock_get.return_value = mock_response
        yield mock_get

# FastAPI Test Client fixtures
@pytest.fixture(scope="function")
def test_client():
    """Create a test client for the main FastAPI app."""
    from multi_project_api import app
    with TestClient(app) as client:
        yield client

@pytest.fixture(scope="function")
def strava_test_client():
    """Create a test client for Strava integration endpoints."""
    from fastapi import FastAPI
    from fastapi.exceptions import RequestValidationError
    from projects.fundraising_tracking_app.strava_integration.strava_integration_api import router as strava_router
    from projects.fundraising_tracking_app.strava_integration.error_handlers import (
        api_exception_handler,
        validation_exception_handler,
        http_exception_handler,
        general_exception_handler
    )
    
    # Create a test app with the Strava router
    test_app = FastAPI()
    test_app.include_router(strava_router, prefix="/api/strava-integration")
    
    # Import APIException and add its handler first (more specific)
    from projects.fundraising_tracking_app.strava_integration.error_handlers import APIException
    test_app.add_exception_handler(APIException, api_exception_handler)
    
    # Add other error handlers (less specific)
    test_app.add_exception_handler(RequestValidationError, validation_exception_handler)
    test_app.add_exception_handler(Exception, general_exception_handler)
    
    with TestClient(test_app) as client:
        yield client

@pytest.fixture(scope="function")
def fundraising_test_client():
    """Create a test client for fundraising endpoints."""
    from fastapi import FastAPI
    from projects.fundraising_tracking_app.fundraising_scraper.fundraising_api import router as fundraising_router
    
    # Create a test app with the fundraising router
    test_app = FastAPI()
    test_app.include_router(fundraising_router, prefix="/api/fundraising")
    
    with TestClient(test_app) as client:
        yield client

# Async test client for testing async endpoints
@pytest.fixture(scope="function")
def async_test_client():
    """Create an async test client."""
    from multi_project_api import app
    return AsyncClient(base_url="http://test")

# Authentication fixtures
@pytest.fixture(scope="function")
def valid_api_headers() -> Dict[str, str]:
    """Provide valid API headers for testing."""
    return {
        "X-API-Key": "test-strava-key-123",
        "Content-Type": "application/json"
    }

@pytest.fixture(scope="function")
def invalid_api_headers() -> Dict[str, str]:
    """Provide invalid API headers for testing."""
    return {
        "X-API-Key": "invalid-key",
        "Content-Type": "application/json"
    }

@pytest.fixture(scope="function")
def no_api_headers() -> Dict[str, str]:
    """Provide headers without API key for testing."""
    return {
        "Content-Type": "application/json"
    }

# Error testing fixtures
@pytest.fixture(scope="function")
def error_response_template() -> Dict[str, Any]:
    """Template for error response structure."""
    return {
        "success": False,
        "error": "Error message",
        "status_code": 400,
        "timestamp": "2025-01-01T10:00:00Z",
        "request_id": "test-request-id"
    }

@pytest.fixture(scope="function")
def sample_strava_activities() -> List[Dict[str, Any]]:
    """Sample Strava activities for testing."""
    return [
        {
            "id": 15806551007,
            "name": "Morning Run",
            "type": "Run",
            "distance": 5000.0,
            "moving_time": 1800,
            "elapsed_time": 1900,
            "start_date": "2025-09-06T07:00:00Z",
            "start_date_local": "2025-09-06T08:00:00Z",
            "description": "Beautiful morning run",
            "polyline": "test_polyline_data_1",
            "summary_polyline": "test_summary_polyline_1",
            "bounds": {
                "northeast": {"lat": 51.5074, "lng": -0.1278},
                "southwest": {"lat": 51.5073, "lng": -0.1279}
            },
            "photos": [],
            "comments": []
        },
        {
            "id": 15723207147,
            "name": "Evening Ride",
            "type": "Ride",
            "distance": 15000.0,
            "moving_time": 3600,
            "elapsed_time": 3700,
            "start_date": "2025-09-05T18:00:00Z",
            "start_date_local": "2025-09-05T19:00:00Z",
            "description": "Evening cycling session",
            "polyline": "test_polyline_data_2",
            "summary_polyline": "test_summary_polyline_2",
            "bounds": {
                "northeast": {"lat": 51.5084, "lng": -0.1268},
                "southwest": {"lat": 51.5063, "lng": -0.1289}
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
                    "text": "Great ride!",
                    "athlete": {"id": 1, "firstname": "Test", "lastname": "User"}
                }
            ]
        }
    ]

@pytest.fixture(scope="function")
def sample_donations_data() -> List[Dict[str, Any]]:
    """Sample donations data for testing."""
    return [
        {
            "donor_name": "John Doe",
            "amount": 25.0,
            "message": "Great cause!",
            "date": "2 days ago",
            "scraped_at": "2025-01-01T10:00:00Z"
        },
        {
            "donor_name": "Jane Smith", 
            "amount": 50.0,
            "message": "Keep up the good work!",
            "date": "1 week ago",
            "scraped_at": "2025-01-01T10:00:00Z"
        }
    ]
