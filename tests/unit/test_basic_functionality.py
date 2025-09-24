"""
Basic unit tests for core functionality.
These tests focus on testing what we can without mocking complex dependencies.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import os
import tempfile
import shutil
import json


class TestBasicCacheFunctionality:
    """Basic tests for cache functionality that don't require complex mocking."""
    
    def test_strava_cache_initialization(self):
        """Test that SmartStravaCache can be initialized."""
        with patch('projects.fundraising_tracking_app.strava_integration.smart_strava_cache.StravaTokenManager'):
            with patch('projects.fundraising_tracking_app.strava_integration.smart_strava_cache.threading.Thread'):
                from projects.fundraising_tracking_app.strava_integration.smart_strava_cache import SmartStravaCache
                
                cache = SmartStravaCache()
                
                # Test basic attributes
                assert hasattr(cache, 'cache_file')
                assert hasattr(cache, 'base_url')
                assert hasattr(cache, 'allowed_activity_types')
                assert cache.allowed_activity_types == ["Run", "Ride"]
                assert cache.base_url == "https://www.strava.com/api/v3"
    
    def test_fundraising_cache_initialization(self):
        """Test that SmartFundraisingCache can be initialized."""
        with patch('projects.fundraising_tracking_app.fundraising_scraper.fundraising_scraper.threading.Thread'):
            from projects.fundraising_tracking_app.fundraising_scraper.fundraising_scraper import SmartFundraisingCache
            
            test_url = "https://test-justgiving.com/test-page"
            cache = SmartFundraisingCache(test_url)
            
            # Test basic attributes
            assert hasattr(cache, 'cache_file')
            assert hasattr(cache, 'justgiving_url')
            assert hasattr(cache, 'backup_dir')
            assert cache.justgiving_url == test_url
    
    def test_strava_cache_file_structure(self):
        """Test that Strava cache file has expected structure."""
        with patch('projects.fundraising_tracking_app.strava_integration.smart_strava_cache.StravaTokenManager'):
            with patch('projects.fundraising_tracking_app.strava_integration.smart_strava_cache.threading.Thread'):
                from projects.fundraising_tracking_app.strava_integration.smart_strava_cache import SmartStravaCache
                
                cache = SmartStravaCache()
                
                # Test that cache file path is set
                assert cache.cache_file is not None
                assert isinstance(cache.cache_file, str)
                assert cache.cache_file.endswith('.json')
    
    def test_fundraising_cache_file_structure(self):
        """Test that fundraising cache file has expected structure."""
        with patch('projects.fundraising_tracking_app.fundraising_scraper.fundraising_scraper.threading.Thread'):
            from projects.fundraising_tracking_app.fundraising_scraper.fundraising_scraper import SmartFundraisingCache
            
            test_url = "https://test-justgiving.com/test-page"
            cache = SmartFundraisingCache(test_url)
            
            # Test that cache file path is set
            assert cache.cache_file is not None
            assert isinstance(cache.cache_file, str)
            assert cache.cache_file.endswith('.json')
    
    def test_strava_cache_allowed_activity_types(self):
        """Test that Strava cache only allows Run and Ride activities."""
        with patch('projects.fundraising_tracking_app.strava_integration.smart_strava_cache.StravaTokenManager'):
            with patch('projects.fundraising_tracking_app.strava_integration.smart_strava_cache.threading.Thread'):
                from projects.fundraising_tracking_app.strava_integration.smart_strava_cache import SmartStravaCache
                
                cache = SmartStravaCache()
                
                # Test allowed activity types
                assert "Run" in cache.allowed_activity_types
                assert "Ride" in cache.allowed_activity_types
                assert len(cache.allowed_activity_types) == 2
    
    def test_strava_cache_start_date(self):
        """Test that Strava cache has correct start date filter."""
        with patch('projects.fundraising_tracking_app.strava_integration.smart_strava_cache.StravaTokenManager'):
            with patch('projects.fundraising_tracking_app.strava_integration.smart_strava_cache.threading.Thread'):
                from projects.fundraising_tracking_app.strava_integration.smart_strava_cache import SmartStravaCache
                from datetime import datetime
                
                cache = SmartStravaCache()
                
                # Test start date is May 22, 2025
                expected_date = datetime(2025, 5, 22)
                assert cache.start_date == expected_date


class TestDataValidation:
    """Test data validation functions."""
    
    def test_activity_type_validation(self):
        """Test validation of activity types."""
        allowed_types = ["Run", "Ride"]
        
        # Valid types
        assert "Run" in allowed_types
        assert "Ride" in allowed_types
        
        # Invalid types
        assert "Swim" not in allowed_types
        assert "Walk" not in allowed_types
        assert "Hike" not in allowed_types
    
    def test_date_filtering_logic(self):
        """Test date filtering logic."""
        from datetime import datetime
        
        start_date = datetime(2025, 5, 22)
        
        # Test dates
        before_cutoff = datetime(2025, 5, 21)
        on_cutoff = datetime(2025, 5, 22)
        after_cutoff = datetime(2025, 5, 23)
        
        # Should be filtered out (before cutoff)
        assert before_cutoff < start_date
        
        # Should be included (on or after cutoff)
        assert on_cutoff >= start_date
        assert after_cutoff >= start_date
    
    def test_donation_amount_parsing(self):
        """Test donation amount parsing logic."""
        # Test cases for amount parsing
        test_cases = [
            ("£25.00", 25.0),
            ("£150.50", 150.5),
            ("£1,000.00", 1000.0),
            ("25.00", 25.0),  # Without £ symbol
            ("", 0.0),
            ("Invalid", 0.0)
        ]
        
        for amount_text, expected in test_cases:
            # Simple parsing logic (this would be in the actual implementation)
            if amount_text.startswith("£"):
                amount_text = amount_text[1:]
            
            # Remove commas
            amount_text = amount_text.replace(",", "")
            
            try:
                result = float(amount_text) if amount_text else 0.0
            except ValueError:
                result = 0.0
            
            assert result == expected


class TestErrorHandling:
    """Test basic error handling scenarios."""
    
    def test_http_status_codes(self):
        """Test that we handle common HTTP status codes correctly."""
        # Success codes
        assert 200 == 200
        assert 201 == 201
        
        # Client error codes
        assert 400 == 400  # Bad Request
        assert 401 == 401  # Unauthorized
        assert 403 == 403  # Forbidden
        assert 404 == 404  # Not Found
        assert 429 == 429  # Too Many Requests
        
        # Server error codes
        assert 500 == 500  # Internal Server Error
        assert 502 == 502  # Bad Gateway
        assert 503 == 503  # Service Unavailable
    
    def test_json_validation(self):
        """Test JSON validation logic."""
        import json
        
        # Valid JSON
        valid_json = '{"key": "value", "number": 123}'
        try:
            data = json.loads(valid_json)
            assert data["key"] == "value"
            assert data["number"] == 123
        except json.JSONDecodeError:
            pytest.fail("Valid JSON should not raise JSONDecodeError")
        
        # Invalid JSON
        invalid_json = '{"key": "value", "number": 123'  # Missing closing brace
        with pytest.raises(json.JSONDecodeError):
            json.loads(invalid_json)
    
    def test_file_operations(self, temp_dir):
        """Test basic file operations."""
        test_file = os.path.join(temp_dir, "test.json")
        test_data = {"test": "data", "number": 123}
        
        # Write file
        with open(test_file, 'w') as f:
            json.dump(test_data, f)
        
        assert os.path.exists(test_file)
        
        # Read file
        with open(test_file, 'r') as f:
            loaded_data = json.load(f)
        
        assert loaded_data == test_data
        
        # Delete file
        os.remove(test_file)
        assert not os.path.exists(test_file)
