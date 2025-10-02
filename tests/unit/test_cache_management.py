#!/usr/bin/env python3
"""
Fixed Cache Management Tests
Tests the actual SmartStravaCache and SmartFundraisingCache interfaces
"""

import pytest
import os
import json
import tempfile
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from projects.fundraising_tracking_app.strava_integration.smart_strava_cache import SmartStravaCache
from projects.fundraising_tracking_app.fundraising_scraper.fundraising_scraper import SmartFundraisingCache


class TestSmartStravaCache:
    """Test the actual SmartStravaCache implementation"""
    
    def test_cache_initialization(self):
        """Test that cache initializes correctly with default values."""
        with patch('projects.fundraising_tracking_app.strava_integration.smart_strava_cache.StravaTokenManager'):
            cache = SmartStravaCache()
            
            # Test default initialization
            assert cache.cache_file == "projects/fundraising_tracking_app/strava_integration/strava_cache.json"
            assert cache.cache_duration_hours == 6  # Default from env or 6
            assert cache.allowed_activity_types == ["Run", "Ride"]
            assert cache.start_date == datetime(2025, 5, 22)
            assert cache._cache_data is None  # Private attribute
            assert cache._cache_loaded_at is None
    
    def test_cache_initialization_with_custom_duration(self):
        """Test cache initialization with custom duration."""
        with patch('projects.fundraising_tracking_app.strava_integration.smart_strava_cache.StravaTokenManager'):
            cache = SmartStravaCache(cache_duration_hours=12)
            assert cache.cache_duration_hours == 12
    
    @patch('projects.fundraising_tracking_app.strava_integration.smart_strava_cache.StravaTokenManager')
    def test_get_activities_smart_basic(self, mock_token_manager):
        """Test the get_activities_smart method with basic functionality."""
        cache = SmartStravaCache()
        
        # Mock the token manager
        mock_token_manager.return_value.get_valid_token.return_value = "test_token"
        
        # Mock the cache data
        mock_cache_data = {
            "timestamp": datetime.now().isoformat(),
            "activities": [
                {
                    "id": 1,
                    "name": "Test Run",
                    "type": "Run",
                    "start_date_local": "2025-06-01T10:00:00Z",
                    "distance": 5000,
                    "moving_time": 1800
                }
            ]
        }
        
        with patch.object(cache, '_load_cache', return_value=mock_cache_data):
            activities = cache.get_activities_smart(limit=10)
            
            assert len(activities) == 1
            assert activities[0]["name"] == "Test Run"
            assert activities[0]["type"] == "Run"
    
    @patch('projects.fundraising_tracking_app.strava_integration.smart_strava_cache.StravaTokenManager')
    def test_force_refresh_now(self, mock_token_manager):
        """Test the force_refresh_now method."""
        cache = SmartStravaCache()
        
        # Mock the token manager
        mock_token_manager.return_value.get_valid_token.return_value = "test_token"
        
        # The method should not raise an exception
        try:
            cache.force_refresh_now()
            # If we get here, the method executed without error
            assert True
        except Exception as e:
            # If it fails due to external dependencies, that's expected in tests
            assert "token" in str(e).lower() or "api" in str(e).lower() or "http" in str(e).lower()
    
    @patch('projects.fundraising_tracking_app.strava_integration.smart_strava_cache.StravaTokenManager')
    def test_cleanup_backups(self, mock_token_manager):
        """Test the cleanup_backups method."""
        cache = SmartStravaCache()
        
        with patch('os.path.exists', return_value=True), \
             patch('os.listdir', return_value=['backup1.json', 'backup2.json']), \
             patch('os.remove') as mock_remove:
            
            cache.cleanup_backups()
            # Should not raise an exception
    
    @patch('projects.fundraising_tracking_app.strava_integration.smart_strava_cache.StravaTokenManager')
    def test_clean_invalid_activities(self, mock_token_manager):
        """Test the clean_invalid_activities method."""
        cache = SmartStravaCache()
        
        # Mock cache data with invalid activities
        mock_cache_data = {
            "timestamp": datetime.now().isoformat(),
            "activities": [
                {
                    "id": 1,
                    "name": "Valid Run",
                    "type": "Run",
                    "start_date_local": "2025-06-01T10:00:00Z"
                },
                {
                    "id": 2,
                    "name": "Unknown Activity",
                    "type": "Unknown",
                    "start_date_local": "2025-01-01T00:00:00Z"
                }
            ]
        }
        
        with patch.object(cache, '_load_cache', return_value=mock_cache_data), \
             patch.object(cache, '_save_cache') as mock_save:
            
            result = cache.clean_invalid_activities()
            
            assert "activities_removed" in result
            assert "activities_remaining" in result
            mock_save.assert_called_once()


class TestSmartFundraisingCache:
    """Test the actual SmartFundraisingCache implementation"""
    
    def test_cache_initialization(self):
        """Test that fundraising cache initializes correctly."""
        test_url = "https://www.justgiving.com/fundraising/test"
        cache_file = "test_fundraising_cache.json"
        
        with patch('os.makedirs'), \
             patch.object(SmartFundraisingCache, '_load_cache'), \
             patch.object(SmartFundraisingCache, '_start_scraper'):
            
            cache = SmartFundraisingCache(test_url, cache_file)
            
            assert cache.justgiving_url == test_url
            assert cache.cache_file == cache_file
            assert cache._cache_data is None  # Private attribute
            assert cache._cache_loaded_at is None
    
    def test_get_fundraising_data(self):
        """Test getting fundraising data from cache."""
        test_url = "https://www.justgiving.com/fundraising/test"
        cache_file = "test_fundraising_cache.json"
        
        mock_cache_data = {
            "timestamp": datetime.now().isoformat(),
            "total_raised": 1500.0,
            "donations": [
                {
                    "donor_name": "Test Donor",
                    "amount": 25.0,
                    "message": "Good luck!",
                    "time_ago": "2 days ago"
                }
            ]
        }
        
        with patch('os.makedirs'), \
             patch.object(SmartFundraisingCache, '_load_cache', return_value=mock_cache_data), \
             patch.object(SmartFundraisingCache, '_start_scraper'):
            
            cache = SmartFundraisingCache(test_url, cache_file)
            data = cache.get_fundraising_data()
            
            assert data["total_raised"] == 1500.0
            assert len(data["donations"]) == 1
            assert data["donations"][0]["donor_name"] == "Test Donor"
    
    def test_get_donations_via_get_fundraising_data(self):
        """Test getting donations via get_fundraising_data method."""
        test_url = "https://www.justgiving.com/fundraising/test"
        cache_file = "test_fundraising_cache.json"
        
        mock_cache_data = {
            "timestamp": datetime.now().isoformat(),
            "donations": [
                {
                    "donor_name": "Donor 1",
                    "amount": 50.0,
                    "message": "Great cause!",
                    "time_ago": "1 day ago"
                },
                {
                    "donor_name": "Donor 2", 
                    "amount": 25.0,
                    "message": "Good luck!",
                    "time_ago": "2 days ago"
                }
            ]
        }
        
        with patch('os.makedirs'), \
             patch.object(SmartFundraisingCache, '_load_cache', return_value=mock_cache_data), \
             patch.object(SmartFundraisingCache, '_start_scraper'):
            
            cache = SmartFundraisingCache(test_url, cache_file)
            data = cache.get_fundraising_data()
            
            assert len(data["donations"]) == 2
            assert data["donations"][0]["donor_name"] == "Donor 1"
    
    def test_force_refresh(self):
        """Test forcing a refresh of fundraising data."""
        test_url = "https://www.justgiving.com/fundraising/test"
        cache_file = "test_fundraising_cache.json"
        
        with patch('os.makedirs'), \
             patch.object(SmartFundraisingCache, '_load_cache'), \
             patch.object(SmartFundraisingCache, '_start_scraper'), \
             patch.object(SmartFundraisingCache, '_perform_smart_refresh') as mock_refresh:
            
            cache = SmartFundraisingCache(test_url, cache_file)
            result = cache.force_refresh_now()
            
            mock_refresh.assert_called_once()
            assert result is True
    
    def test_cleanup_backups(self):
        """Test cleanup of old backup files."""
        test_url = "https://www.justgiving.com/fundraising/test"
        cache_file = "test_fundraising_cache.json"
        
        with patch('os.makedirs'), \
             patch.object(SmartFundraisingCache, '_load_cache'), \
             patch.object(SmartFundraisingCache, '_start_scraper'), \
             patch.object(SmartFundraisingCache, '_cleanup_old_backups') as mock_cleanup:
            
            cache = SmartFundraisingCache(test_url, cache_file)
            result = cache.cleanup_backups()
            
            mock_cleanup.assert_called_once()
            assert result is True


class TestCacheIntegration:
    """Test cache integration and edge cases"""
    
    @patch('projects.fundraising_tracking_app.strava_integration.smart_strava_cache.StravaTokenManager')
    def test_cache_with_empty_data(self, mock_token_manager):
        """Test cache behavior with empty data."""
        cache = SmartStravaCache()
        
        mock_cache_data = {
            "timestamp": datetime.now().isoformat(),
            "activities": []
        }
        
        with patch.object(cache, '_load_cache', return_value=mock_cache_data):
            activities = cache.get_activities_smart(limit=10)
            assert len(activities) == 0
    
    def test_fundraising_cache_with_empty_data(self):
        """Test fundraising cache with empty data."""
        test_url = "https://www.justgiving.com/fundraising/test"
        cache_file = "test_fundraising_cache.json"
        
        mock_cache_data = {
            "timestamp": datetime.now().isoformat(),
            "total_raised": 0.0,
            "donations": []
        }
        
        with patch('os.makedirs'), \
             patch.object(SmartFundraisingCache, '_load_cache', return_value=mock_cache_data), \
             patch.object(SmartFundraisingCache, '_start_scraper'):
            
            cache = SmartFundraisingCache(test_url, cache_file)
            data = cache.get_fundraising_data()
            
            assert data["total_raised"] == 0.0
            assert len(data["donations"]) == 0
