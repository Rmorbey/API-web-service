#!/usr/bin/env python3
"""
Unit tests for AsyncProcessor module
Tests parallel processing of activities and donations
"""

import pytest
import asyncio
from unittest.mock import Mock, patch
from datetime import datetime

from projects.fundraising_tracking_app.strava_integration.async_processor import AsyncProcessor


class TestAsyncProcessor:
    """Test AsyncProcessor functionality"""
    
    def test_async_processor_init(self):
        """Test AsyncProcessor initialization"""
        processor = AsyncProcessor(max_workers=2)
        assert processor.max_workers == 2
        assert processor.executor is not None
        processor.shutdown()
    
    @pytest.mark.asyncio
    async def test_process_activities_parallel_empty_list(self):
        """Test processing empty activities list"""
        processor = AsyncProcessor()
        result = await processor.process_activities_parallel([])
        assert result == []
        processor.shutdown()
    
    @pytest.mark.asyncio
    async def test_process_activities_parallel_single_activity(self):
        """Test processing single activity"""
        processor = AsyncProcessor()
        
        activity = {
            "id": 1,
            "name": "Test Run",
            "type": "Run",
            "distance": 5000,
            "moving_time": 1800,
            "description": "Great run listening to Track: Song Name by Artist",
            "start_date_local": "2023-01-01T12:00:00Z",
            "photos": {"primary": {"urls": {"600": "test.jpg"}}}
        }
        
        result = await processor.process_activities_parallel([activity])
        
        assert len(result) == 1
        processed_activity = result[0]
        assert processed_activity["id"] == 1
        assert "music" in processed_activity
        assert "detected" in processed_activity["music"]
        assert processed_activity["music"]["detected"]["type"] == "track"
        assert processed_activity["music"]["detected"]["title"] == "Song Name"
        assert processed_activity["music"]["detected"]["artist"] == "Artist"
        
        processor.shutdown()
    
    @pytest.mark.asyncio
    async def test_process_activities_parallel_multiple_activities(self):
        """Test processing multiple activities in parallel"""
        processor = AsyncProcessor()
        
        activities = [
            {
                "id": 1,
                "name": "Test Run",
                "type": "Run",
                "distance": 5000,
                "moving_time": 1800,
                "description": "Track: Song 1 by Artist 1",
                "start_date_local": "2023-01-01T12:00:00Z"
            },
            {
                "id": 2,
                "name": "Test Ride",
                "type": "Ride",
                "distance": 10000,
                "moving_time": 3600,
                "description": "Album: Album 1 by Artist 2",
                "start_date_local": "2023-01-02T12:00:00Z"
            }
        ]
        
        result = await processor.process_activities_parallel(activities)
        
        assert len(result) == 2
        assert result[0]["music"]["detected"]["type"] == "track"
        assert result[1]["music"]["detected"]["type"] == "album"
        
        processor.shutdown()
    
    @pytest.mark.asyncio
    async def test_process_activities_parallel_with_exception(self):
        """Test processing activities with one causing exception"""
        processor = AsyncProcessor()
        
        activities = [
            {
                "id": 1,
                "name": "Valid Activity",
                "type": "Run",
                "distance": 5000,
                "moving_time": 1800,
                "description": "Track: Song by Artist",
                "start_date_local": "2023-01-01T12:00:00Z"
            }
        ]
        
        # Mock the processing to cause an exception
        with patch.object(processor, '_process_single_activity', side_effect=Exception("Processing failed")):
            result = await processor.process_activities_parallel(activities)
            # Should return empty list due to exception
            assert len(result) == 0
        
        processor.shutdown()
    
    @pytest.mark.asyncio
    async def test_process_donations_parallel_empty_list(self):
        """Test processing empty donations list"""
        processor = AsyncProcessor()
        result = await processor.process_donations_parallel([])
        assert result == []
        processor.shutdown()
    
    @pytest.mark.asyncio
    async def test_process_donations_parallel_single_donation(self):
        """Test processing single donation"""
        processor = AsyncProcessor()
        
        donation = {
            "id": "1",
            "amount": 25.50,
            "donor_name": "John Doe",
            "date": "1 Jan 2023",
            "message": "Great cause!"
        }
        
        result = await processor.process_donations_parallel([donation])
        
        assert len(result) == 1
        processed_donation = result[0]
        assert processed_donation["amount_formatted"] == "£25.50"
        assert processed_donation["donor_name_anonymized"] == "John D."
        assert "date_formatted" in processed_donation
        
        processor.shutdown()
    
    @pytest.mark.asyncio
    async def test_process_donations_parallel_multiple_donations(self):
        """Test processing multiple donations in parallel"""
        processor = AsyncProcessor()
        
        donations = [
            {
                "id": "1",
                "amount": 25.50,
                "donor_name": "John Doe",
                "date": "1 Jan 2023",
                "message": "Great cause!"
            },
            {
                "id": "2",
                "amount": 50.00,
                "donor_name": "Jane Smith",
                "date": "2 Jan 2023",
                "message": "Keep it up!"
            }
        ]
        
        result = await processor.process_donations_parallel(donations)
        
        assert len(result) == 2
        assert result[0]["amount_formatted"] == "£25.50"
        assert result[1]["amount_formatted"] == "£50.00"
        assert result[0]["donor_name_anonymized"] == "John D."
        assert result[1]["donor_name_anonymized"] == "Jane S."
        
        processor.shutdown()
    
    def test_detect_music_sync_track(self):
        """Test synchronous music detection for track"""
        processor = AsyncProcessor()
        
        description = "Great run listening to Track: Song Name by Artist Name"
        result = processor._detect_music_sync(description)
        
        assert "detected" in result
        assert result["detected"]["type"] == "track"
        assert result["detected"]["title"] == "Song Name"
        assert result["detected"]["artist"] == "Artist Name"
        
        processor.shutdown()
    
    def test_detect_music_sync_album(self):
        """Test synchronous music detection for album"""
        processor = AsyncProcessor()
        
        description = "Workout with Album: Album Name by Artist Name"
        result = processor._detect_music_sync(description)
        
        assert "detected" in result
        assert result["detected"]["type"] == "album"
        assert result["detected"]["title"] == "Album Name"
        assert result["detected"]["artist"] == "Artist Name"
        
        processor.shutdown()
    
    def test_detect_music_sync_russell_radio(self):
        """Test synchronous music detection for Russell Radio"""
        processor = AsyncProcessor()
        
        description = "Russell Radio: Song Name by Artist Name"
        result = processor._detect_music_sync(description)
        
        assert "detected" in result
        assert result["detected"]["type"] == "track"
        assert result["detected"]["title"] == "Song Name"
        assert result["detected"]["artist"] == "Artist Name"
        assert result["detected"]["source"] == "russell_radio"
        
        processor.shutdown()
    
    def test_detect_music_sync_no_music(self):
        """Test synchronous music detection with no music"""
        processor = AsyncProcessor()
        
        description = "Just a regular run"
        result = processor._detect_music_sync(description)
        
        assert result == {}
        
        processor.shutdown()
    
    def test_format_activity_sync(self):
        """Test synchronous activity formatting"""
        processor = AsyncProcessor()
        
        activity = {
            "id": 1,
            "distance": 5000,
            "moving_time": 1800,
            "type": "Run",
            "start_date_local": "2023-01-01T12:00:00Z"
        }
        
        result = processor._format_activity_sync(activity)
        
        assert result["distance_formatted"] == "5.0 km"
        assert result["duration_formatted"] == "30m 0s"
        assert result["pace_per_km"] == "6:00/km"
        assert result["date_formatted"] == "1st of January 2023 at 12:00"
        
        processor.shutdown()
    
    def test_format_activity_date(self):
        """Test activity date formatting"""
        processor = AsyncProcessor()
        
        # Test various date formats
        test_cases = [
            ("2023-01-01T12:00:00Z", "1st of January 2023 at 12:00"),
            ("2023-02-02T09:30:00Z", "2nd of February 2023 at 09:30"),
            ("2023-03-03T15:45:00Z", "3rd of March 2023 at 15:45"),
            ("2023-04-04T08:15:00Z", "4th of April 2023 at 08:15"),
            ("2023-11-11T20:00:00Z", "11th of November 2023 at 20:00"),
            ("2023-12-21T14:30:00Z", "21st of December 2023 at 14:30"),
            ("2023-12-22T14:30:00Z", "22nd of December 2023 at 14:30"),
            ("2023-12-23T14:30:00Z", "23rd of December 2023 at 14:30"),
        ]
        
        for input_date, expected_output in test_cases:
            result = processor._format_activity_date(input_date)
            assert result == expected_output, f"Failed for {input_date}: got {result}, expected {expected_output}"
        
        processor.shutdown()
    
    def test_format_donation_sync(self):
        """Test synchronous donation formatting"""
        processor = AsyncProcessor()
        
        donation = {
            "amount": 25.50,
            "donor_name": "John Doe",
            "date": "1 Jan 2023"
        }
        
        result = processor._format_donation_sync(donation)
        
        assert result["amount_formatted"] == "£25.50"
        assert result["donor_name_anonymized"] == "John D."
        assert "date_formatted" in result
        
        processor.shutdown()
    
    def test_format_donation_sync_anonymous(self):
        """Test synchronous donation formatting for anonymous donor"""
        processor = AsyncProcessor()
        
        donation = {
            "amount": 25.50,
            "donor_name": "",
            "date": "1 Jan 2023"
        }
        
        result = processor._format_donation_sync(donation)
        
        assert result["amount_formatted"] == "£25.50"
        assert result["donor_name_anonymized"] == "Anonymous"
        
        processor.shutdown()
    
    def test_shutdown(self):
        """Test AsyncProcessor shutdown"""
        processor = AsyncProcessor()
        processor.shutdown()
        # Should not raise any exceptions
        assert True
