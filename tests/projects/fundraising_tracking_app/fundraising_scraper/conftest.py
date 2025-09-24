"""
Pytest fixtures specific to fundraising scraper testing.
"""

import os
import tempfile
from typing import Generator, Dict, Any, List
from unittest.mock import Mock, patch
import pytest

@pytest.fixture(scope="function")
def fundraising_cache_file(temp_dir: str) -> str:
    """Create a temporary fundraising cache file for testing."""
    cache_file = os.path.join(temp_dir, "fundraising_cache.json")
    return cache_file

@pytest.fixture(scope="function")
def fundraising_backup_dir(temp_dir: str) -> str:
    """Create a temporary backup directory for fundraising cache."""
    backup_dir = os.path.join(temp_dir, "backups")
    os.makedirs(backup_dir, exist_ok=True)
    return backup_dir

@pytest.fixture(scope="function")
def sample_justgiving_html() -> str:
    """Sample JustGiving HTML content for testing."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Fundraising Page</title>
    </head>
    <body>
        <div class="total-raised">
            <span class="amount">£150.00</span>
        </div>
        <div class="donations">
            <div class="donation">
                <div class="donor-name">John Doe</div>
                <div class="amount">£25.00</div>
                <div class="message">Great cause!</div>
                <div class="date">2 days ago</div>
            </div>
            <div class="donation">
                <div class="donor-name">Jane Smith</div>
                <div class="amount">£50.00</div>
                <div class="message">Keep up the good work!</div>
                <div class="date">1 week ago</div>
            </div>
        </div>
    </body>
    </html>
    """

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

@pytest.fixture(scope="function")
def mock_justgiving_scraping(sample_justgiving_html: str):
    """Mock JustGiving web scraping."""
    with patch('requests.get') as mock_get:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = sample_justgiving_html
        mock_response.content = sample_justgiving_html.encode('utf-8')
        mock_get.return_value = mock_response
        
        yield mock_get

@pytest.fixture(scope="function")
def mock_justgiving_scraping_error():
    """Mock JustGiving scraping errors."""
    with patch('requests.get') as mock_get:
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Page not found"
        mock_response.raise_for_status.side_effect = Exception("404 Not Found")
        mock_get.return_value = mock_response
        
        yield mock_get

@pytest.fixture(scope="function")
def mock_justgiving_scraping_timeout():
    """Mock JustGiving scraping timeout."""
    with patch('requests.get') as mock_get:
        mock_get.side_effect = Exception("Request timeout")
        yield mock_get

@pytest.fixture(scope="function")
def fundraising_test_data():
    """Comprehensive test data for fundraising scraper."""
    return {
        "justgiving_url": "https://test-justgiving.com/test-page",
        "expected_total_raised": 150.0,
        "expected_donations": [
            {
                "donor_name": "John Doe",
                "amount": 25.0,
                "message": "Great cause!",
                "date": "2 days ago"
            },
            {
                "donor_name": "Jane Smith",
                "amount": 50.0, 
                "message": "Keep up the good work!",
                "date": "1 week ago"
            }
        ],
        "expected_cache_structure": {
            "timestamp": "2025-01-01T10:00:00Z",
            "last_updated": "2025-01-01T10:00:00Z",
            "version": "1.0",
            "total_raised": 150.0,
            "total_donations": 2,
            "donations": []
        }
    }

@pytest.fixture(scope="function")
def mock_beautifulsoup():
    """Mock BeautifulSoup for HTML parsing."""
    with patch('bs4.BeautifulSoup') as mock_soup:
        # Create a mock soup object
        mock_soup_instance = Mock()
        mock_soup_instance.find.return_value = Mock()
        mock_soup_instance.find_all.return_value = []
        mock_soup.return_value = mock_soup_instance
        
        yield mock_soup
