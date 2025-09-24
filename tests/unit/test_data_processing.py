"""
Unit tests for data processing functionality.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from projects.fundraising_tracking_app.strava_integration.smart_strava_cache import SmartStravaCache
from projects.fundraising_tracking_app.fundraising_scraper.fundraising_scraper import SmartFundraisingCache


class TestStravaDataProcessing:
    """Test cases for Strava data processing functions."""
    
    def test_filter_activities_by_type(self, sample_strava_activities):
        """Test filtering activities by type (Run/Ride only)."""
        cache = SmartStravaCache("test.json")
        
        # Test with mixed activity types
        mixed_activities = [
            {"id": 1, "type": "Run", "name": "Morning Run"},
            {"id": 2, "type": "Ride", "name": "Evening Ride"},
            {"id": 3, "type": "Swim", "name": "Pool Swim"},
            {"id": 4, "type": "Walk", "name": "Evening Walk"}
        ]
        
        filtered = cache._filter_activities_by_type(mixed_activities)
        
        assert len(filtered) == 2
        assert filtered[0]["type"] == "Run"
        assert filtered[1]["type"] == "Ride"
    
    def test_filter_activities_by_date(self, sample_strava_activities):
        """Test filtering activities by date (after May 22, 2025)."""
        cache = SmartStravaCache("test.json")
        
        # Test with activities from different dates
        activities = [
            {
                "id": 1,
                "type": "Run",
                "start_date_local": "2025-05-21T10:00:00Z",  # Before cutoff
                "name": "Old Run"
            },
            {
                "id": 2,
                "type": "Run", 
                "start_date_local": "2025-05-22T10:00:00Z",  # On cutoff date
                "name": "Cutoff Run"
            },
            {
                "id": 3,
                "type": "Run",
                "start_date_local": "2025-05-23T10:00:00Z",  # After cutoff
                "name": "New Run"
            }
        ]
        
        filtered = cache._filter_activities_by_date(activities)
        
        assert len(filtered) == 2  # Should include cutoff date and after
        assert filtered[0]["name"] == "Cutoff Run"
        assert filtered[1]["name"] == "New Run"
    
    def test_clean_description_text(self):
        """Test cleaning description text by removing music-related content."""
        cache = SmartStravaCache("test.json")
        
        test_cases = [
            {
                "input": "Great run! Russell Radio: Song Name - Artist",
                "expected": "Great run!"
            },
            {
                "input": "Album: Album Name - Artist. Beautiful morning!",
                "expected": "Beautiful morning!"
            },
            {
                "input": "Russell Radio: Song - Artist. Album: Album - Artist. Nice weather!",
                "expected": "Nice weather!"
            },
            {
                "input": "Just a regular description without music info",
                "expected": "Just a regular description without music info"
            },
            {
                "input": "",
                "expected": ""
            }
        ]
        
        for case in test_cases:
            result = cache._clean_description_text(case["input"])
            assert result == case["expected"]
    
    def test_has_complete_data(self, sample_strava_activities):
        """Test checking if activity has complete data."""
        cache = SmartStravaCache("test.json")
        
        # Activity with complete data
        complete_activity = {
            "id": 1,
            "name": "Test Run",
            "type": "Run",
            "polyline": "test_polyline",
            "bounds": {"northeast": {"lat": 51.5, "lng": -0.1}, "southwest": {"lat": 51.4, "lng": -0.2}},
            "description": "Test description"
        }
        
        # Activity with missing essential data
        incomplete_activity = {
            "id": 2,
            "name": "Test Run",
            "type": "Run",
            "description": "Test description"
            # Missing polyline and bounds
        }
        
        assert cache._has_complete_data(complete_activity) is True
        assert cache._has_complete_data(incomplete_activity) is False
    
    def test_validate_activity_data(self, sample_strava_activities):
        """Test validating activity data structure."""
        cache = SmartStravaCache("test.json")
        
        # Valid activity
        valid_activity = {
            "id": 123456789,
            "name": "Test Activity",
            "type": "Run",
            "distance": 5000.0,
            "moving_time": 1800,
            "start_date_local": "2025-09-06T08:00:00Z"
        }
        
        # Invalid activity (missing required fields)
        invalid_activity = {
            "id": 123456789,
            "name": "Test Activity"
            # Missing type, distance, etc.
        }
        
        assert cache._validate_activity_data(valid_activity) is True
        assert cache._validate_activity_data(invalid_activity) is False
    
    def test_merge_activities_smart_merge(self, sample_strava_activities):
        """Test smart merging of activities."""
        cache = SmartStravaCache("test.json")
        
        existing_activities = [
            {
                "id": 1,
                "name": "Existing Run",
                "type": "Run",
                "description": "Old description",
                "polyline": "old_polyline",
                "bounds": {"northeast": {"lat": 51.5, "lng": -0.1}, "southwest": {"lat": 51.4, "lng": -0.2}}
            }
        ]
        
        new_activities = [
            {
                "id": 1,
                "name": "Existing Run",
                "type": "Run", 
                "description": "Updated description",
                "polyline": "new_polyline",
                "bounds": {"northeast": {"lat": 51.5, "lng": -0.1}, "southwest": {"lat": 51.4, "lng": -0.2}}
            },
            {
                "id": 2,
                "name": "New Run",
                "type": "Run",
                "description": "New activity",
                "polyline": "new_polyline_2",
                "bounds": {"northeast": {"lat": 51.5, "lng": -0.1}, "southwest": {"lat": 51.4, "lng": -0.2}}
            }
        ]
        
        merged = cache._merge_activities(existing_activities, new_activities)
        
        assert len(merged) == 2
        # First activity should be updated
        assert merged[0]["description"] == "Updated description"
        assert merged[0]["polyline"] == "new_polyline"
        # Second activity should be new
        assert merged[1]["name"] == "New Run"


class TestFundraisingDataProcessing:
    """Test cases for fundraising data processing functions."""
    
    def test_parse_donation_amount(self):
        """Test parsing donation amounts from text."""
        cache = SmartFundraisingCache("test.json")
        
        test_cases = [
            ("£25.00", 25.0),
            ("£150.50", 150.5),
            ("£1,000.00", 1000.0),
            ("£0.50", 0.5),
            ("25.00", 25.0),  # Without £ symbol
            ("", 0.0),
            ("Invalid", 0.0)
        ]
        
        for amount_text, expected in test_cases:
            result = cache._parse_donation_amount(amount_text)
            assert result == expected
    
    def test_clean_donor_name(self):
        """Test cleaning donor names."""
        cache = SmartFundraisingCache("test.json")
        
        test_cases = [
            ("John Doe", "John Doe"),
            ("  Jane Smith  ", "Jane Smith"),
            ("Anonymous", "Anonymous"),
            ("", "Anonymous"),
            ("   ", "Anonymous")
        ]
        
        for name, expected in test_cases:
            result = cache._clean_donor_name(name)
            assert result == expected
    
    def test_clean_donation_message(self):
        """Test cleaning donation messages."""
        cache = SmartFundraisingCache("test.json")
        
        test_cases = [
            ("Great cause!", "Great cause!"),
            ("  Keep it up!  ", "Keep it up!"),
            ("", ""),
            ("   ", "")
        ]
        
        for message, expected in test_cases:
            result = cache._clean_donation_message(message)
            assert result == expected
    
    def test_merge_donations_smart_merge(self, sample_donations_data):
        """Test smart merging of donations."""
        cache = SmartFundraisingCache("test.json")
        
        existing_donations = [
            {
                "donor_name": "John Doe",
                "amount": 25.0,
                "message": "Great cause!",
                "date": "2 days ago",
                "scraped_at": "2025-01-01T10:00:00Z"
            }
        ]
        
        new_donations = [
            {
                "donor_name": "John Doe",
                "amount": 25.0,
                "message": "Great cause!",
                "date": "3 days ago",  # Date changed
                "scraped_at": "2025-01-01T11:00:00Z"
            },
            {
                "donor_name": "Jane Smith",
                "amount": 50.0,
                "message": "Keep it up!",
                "date": "1 week ago",
                "scraped_at": "2025-01-01T11:00:00Z"
            }
        ]
        
        merged = cache._merge_donations(existing_donations, new_donations)
        
        assert len(merged) == 2
        # First donation should be updated with new date
        assert merged[0]["date"] == "3 days ago"
        assert merged[0]["scraped_at"] == "2025-01-01T11:00:00Z"
        # Second donation should be new
        assert merged[1]["donor_name"] == "Jane Smith"
    
    def test_validate_donation_data(self, sample_donations_data):
        """Test validating donation data structure."""
        cache = SmartFundraisingCache("test.json")
        
        # Valid donation
        valid_donation = {
            "donor_name": "John Doe",
            "amount": 25.0,
            "message": "Great cause!",
            "date": "2 days ago",
            "scraped_at": "2025-01-01T10:00:00Z"
        }
        
        # Invalid donation (missing required fields)
        invalid_donation = {
            "donor_name": "John Doe",
            "amount": 25.0
            # Missing message, date, scraped_at
        }
        
        assert cache._validate_donation_data(valid_donation) is True
        assert cache._validate_donation_data(invalid_donation) is False
