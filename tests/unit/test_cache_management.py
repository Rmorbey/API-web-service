"""
Unit tests for cache management functionality.
"""

import json
import os
import tempfile
import shutil
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
import pytest

from projects.fundraising_tracking_app.strava_integration.smart_strava_cache import SmartStravaCache
from projects.fundraising_tracking_app.fundraising_scraper.fundraising_scraper import SmartFundraisingCache


class TestSmartStravaCache:
    """Test cases for SmartStravaCache class."""
    
    def test_cache_initialization(self, temp_dir):
        """Test that cache initializes correctly with default values."""
        cache_file = os.path.join(temp_dir, "test_cache.json")
        cache = SmartStravaCache(cache_file)
        
        assert cache.cache_file == cache_file
        assert cache.cache_data == {
            "timestamp": None,
            "last_updated": None,
            "version": "1.0",
            "activities": [],
            "total_activities": 0
        }
        assert cache.ttl_hours == 6
        assert cache.max_backups == 5
    
    def test_load_cache_from_file(self, temp_dir, mock_cache_data):
        """Test loading cache data from an existing file."""
        cache_file = os.path.join(temp_dir, "test_cache.json")
        
        # Create a test cache file
        with open(cache_file, 'w') as f:
            json.dump(mock_cache_data, f)
        
        cache = SmartStravaCache(cache_file)
        cache.load_cache()
        
        assert cache.cache_data["total_activities"] == 1
        assert len(cache.cache_data["activities"]) == 1
        assert cache.cache_data["activities"][0]["name"] == "Test Activity"
    
    def test_load_cache_file_not_found(self, temp_dir):
        """Test loading cache when file doesn't exist."""
        cache_file = os.path.join(temp_dir, "nonexistent.json")
        cache = SmartStravaCache(cache_file)
        
        # Should not raise an exception, should use default data
        cache.load_cache()
        assert cache.cache_data["total_activities"] == 0
        assert len(cache.cache_data["activities"]) == 0
    
    def test_save_cache(self, temp_dir, mock_cache_data):
        """Test saving cache data to file."""
        cache_file = os.path.join(temp_dir, "test_cache.json")
        cache = SmartStravaCache(cache_file)
        cache.cache_data = mock_cache_data
        
        cache.save_cache()
        
        # Verify file was created and contains correct data
        assert os.path.exists(cache_file)
        with open(cache_file, 'r') as f:
            saved_data = json.load(f)
        assert saved_data["total_activities"] == 1
        assert saved_data["activities"][0]["name"] == "Test Activity"
    
    def test_is_cache_valid_fresh_cache(self, temp_dir):
        """Test cache validity with fresh data."""
        cache_file = os.path.join(temp_dir, "test_cache.json")
        cache = SmartStravaCache(cache_file)
        
        # Set cache timestamp to 1 hour ago (within TTL)
        cache.cache_data["timestamp"] = (datetime.now() - timedelta(hours=1)).isoformat()
        cache.cache_data["last_updated"] = (datetime.now() - timedelta(hours=1)).isoformat()
        
        assert cache.is_cache_valid() is True
    
    def test_is_cache_valid_expired_cache(self, temp_dir):
        """Test cache validity with expired data."""
        cache_file = os.path.join(temp_dir, "test_cache.json")
        cache = SmartStravaCache(cache_file)
        
        # Set cache timestamp to 8 hours ago (beyond TTL)
        cache.cache_data["timestamp"] = (datetime.now() - timedelta(hours=8)).isoformat()
        cache.cache_data["last_updated"] = (datetime.now() - timedelta(hours=8)).isoformat()
        
        assert cache.is_cache_valid() is False
    
    def test_is_cache_valid_no_timestamp(self, temp_dir):
        """Test cache validity when no timestamp exists."""
        cache_file = os.path.join(temp_dir, "test_cache.json")
        cache = SmartStravaCache(cache_file)
        
        # No timestamp set
        cache.cache_data["timestamp"] = None
        cache.cache_data["last_updated"] = None
        
        assert cache.is_cache_valid() is False
    
    def test_create_backup(self, temp_dir, mock_cache_data):
        """Test creating backup files."""
        cache_file = os.path.join(temp_dir, "test_cache.json")
        backup_dir = os.path.join(temp_dir, "backups")
        os.makedirs(backup_dir, exist_ok=True)
        
        cache = SmartStravaCache(cache_file, backup_dir=backup_dir)
        cache.cache_data = mock_cache_data
        
        backup_file = cache.create_backup()
        
        assert os.path.exists(backup_file)
        assert backup_file.startswith(backup_dir)
        assert "backup_" in backup_file
        assert backup_file.endswith(".json")
        
        # Verify backup content
        with open(backup_file, 'r') as f:
            backup_data = json.load(f)
        assert backup_data["total_activities"] == 1
    
    def test_cleanup_old_backups(self, temp_dir):
        """Test cleanup of old backup files."""
        backup_dir = os.path.join(temp_dir, "backups")
        os.makedirs(backup_dir, exist_ok=True)
        
        # Create multiple backup files
        for i in range(7):  # Create 7 backups (more than max_backups=5)
            backup_file = os.path.join(backup_dir, f"backup_{i}.json")
            with open(backup_file, 'w') as f:
                json.dump({"test": f"data_{i}"}, f)
        
        cache_file = os.path.join(temp_dir, "test_cache.json")
        cache = SmartStravaCache(cache_file, backup_dir=backup_dir)
        
        cache.cleanup_old_backups()
        
        # Should only keep the 5 most recent backups
        backup_files = [f for f in os.listdir(backup_dir) if f.endswith('.json')]
        assert len(backup_files) <= 5


class TestSmartFundraisingCache:
    """Test cases for SmartFundraisingCache class."""
    
    def test_cache_initialization(self, temp_dir):
        """Test that fundraising cache initializes correctly."""
        cache_file = os.path.join(temp_dir, "test_fundraising_cache.json")
        cache = SmartFundraisingCache(cache_file)
        
        assert cache.cache_file == cache_file
        assert cache.cache_data == {
            "timestamp": None,
            "last_updated": None,
            "version": "1.0",
            "total_raised": 0.0,
            "total_donations": 0,
            "donations": []
        }
        assert cache.ttl_minutes == 15
        assert cache.max_backups == 5
    
    def test_load_fundraising_cache_from_file(self, temp_dir, mock_fundraising_cache_data):
        """Test loading fundraising cache data from an existing file."""
        cache_file = os.path.join(temp_dir, "test_fundraising_cache.json")
        
        # Create a test cache file
        with open(cache_file, 'w') as f:
            json.dump(mock_fundraising_cache_data, f)
        
        cache = SmartFundraisingCache(cache_file)
        cache.load_cache()
        
        assert cache.cache_data["total_raised"] == 150.0
        assert cache.cache_data["total_donations"] == 1
        assert len(cache.cache_data["donations"]) == 1
        assert cache.cache_data["donations"][0]["donor_name"] == "Test Donor"
    
    def test_is_fundraising_cache_valid_fresh(self, temp_dir):
        """Test fundraising cache validity with fresh data."""
        cache_file = os.path.join(temp_dir, "test_fundraising_cache.json")
        cache = SmartFundraisingCache(cache_file)
        
        # Set cache timestamp to 5 minutes ago (within TTL)
        cache.cache_data["timestamp"] = (datetime.now() - timedelta(minutes=5)).isoformat()
        cache.cache_data["last_updated"] = (datetime.now() - timedelta(minutes=5)).isoformat()
        
        assert cache.is_cache_valid() is True
    
    def test_is_fundraising_cache_valid_expired(self, temp_dir):
        """Test fundraising cache validity with expired data."""
        cache_file = os.path.join(temp_dir, "test_fundraising_cache.json")
        cache = SmartFundraisingCache(cache_file)
        
        # Set cache timestamp to 20 minutes ago (beyond TTL)
        cache.cache_data["timestamp"] = (datetime.now() - timedelta(minutes=20)).isoformat()
        cache.cache_data["last_updated"] = (datetime.now() - timedelta(minutes=20)).isoformat()
        
        assert cache.is_cache_valid() is False
    
    def test_save_fundraising_cache(self, temp_dir, mock_fundraising_cache_data):
        """Test saving fundraising cache data to file."""
        cache_file = os.path.join(temp_dir, "test_fundraising_cache.json")
        cache = SmartFundraisingCache(cache_file)
        cache.cache_data = mock_fundraising_cache_data
        
        cache.save_cache()
        
        # Verify file was created and contains correct data
        assert os.path.exists(cache_file)
        with open(cache_file, 'r') as f:
            saved_data = json.load(f)
        assert saved_data["total_raised"] == 150.0
        assert saved_data["total_donations"] == 1
        assert saved_data["donations"][0]["donor_name"] == "Test Donor"
