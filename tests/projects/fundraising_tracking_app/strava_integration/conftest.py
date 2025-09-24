"""
Pytest fixtures specific to Strava integration testing.
"""

import os
import tempfile
import shutil
from typing import Generator, Dict, Any, List
from unittest.mock import Mock, patch
import pytest
from fastapi.testclient import TestClient

@pytest.fixture(scope="function")
def strava_cache_file(temp_dir: str) -> str:
    """Create a temporary Strava cache file for testing."""
    cache_file = os.path.join(temp_dir, "strava_cache.json")
    return cache_file

@pytest.fixture(scope="function")
def strava_backup_dir(temp_dir: str) -> str:
    """Create a temporary backup directory for Strava cache."""
    backup_dir = os.path.join(temp_dir, "backups")
    os.makedirs(backup_dir, exist_ok=True)
    return backup_dir

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
def mock_strava_api_responses(sample_strava_activities: List[Dict[str, Any]]):
    """Mock Strava API responses."""
    with patch('httpx.AsyncClient') as mock_client:
        # Mock the activities endpoint
        activities_response = Mock()
        activities_response.status_code = 200
        activities_response.json.return_value = sample_strava_activities
        
        # Mock the detailed activity endpoint
        detailed_response = Mock()
        detailed_response.status_code = 200
        detailed_response.json.return_value = sample_strava_activities[0]
        
        mock_client.return_value.__aenter__.return_value.get.side_effect = [
            activities_response,  # First call for activities list
            detailed_response,    # Second call for detailed activity
        ]
        
        yield mock_client

@pytest.fixture(scope="function")
def mock_strava_api_error():
    """Mock Strava API error responses."""
    with patch('httpx.AsyncClient') as mock_client:
        error_response = Mock()
        error_response.status_code = 401
        error_response.json.return_value = {"message": "Unauthorized"}
        error_response.raise_for_status.side_effect = Exception("401 Unauthorized")
        
        mock_client.return_value.__aenter__.return_value.get.return_value = error_response
        
        yield mock_client

@pytest.fixture(scope="function")
def mock_strava_rate_limit():
    """Mock Strava API rate limiting."""
    with patch('httpx.AsyncClient') as mock_client:
        rate_limit_response = Mock()
        rate_limit_response.status_code = 429
        rate_limit_response.headers = {"X-RateLimit-Limit": "100", "X-RateLimit-Usage": "100"}
        rate_limit_response.json.return_value = {"message": "Rate limit exceeded"}
        
        mock_client.return_value.__aenter__.return_value.get.return_value = rate_limit_response
        
        yield mock_client

@pytest.fixture(scope="function")
def strava_test_data():
    """Comprehensive test data for Strava integration."""
    return {
        "access_token": "test-access-token-123",
        "athlete_id": 12345,
        "activities": [
            {
                "id": 15806551007,
                "name": "Test Run",
                "type": "Run",
                "distance": 5000.0,
                "moving_time": 1800,
                "start_date_local": "2025-09-06T08:00:00Z",
                "description": "Test run description",
                "polyline": "test_polyline",
                "bounds": {"northeast": {"lat": 51.5, "lng": -0.1}, "southwest": {"lat": 51.4, "lng": -0.2}}
            }
        ],
        "expected_cache_structure": {
            "timestamp": "2025-01-01T10:00:00Z",
            "last_updated": "2025-01-01T10:00:00Z",
            "version": "1.0",
            "activities": [],
            "total_activities": 0
        }
    }
