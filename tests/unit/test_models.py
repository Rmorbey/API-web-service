#!/usr/bin/env python3
"""
Unit tests for Pydantic models
Tests the validation logic and model behavior
"""

import pytest
from datetime import datetime, date
from pydantic import ValidationError

from projects.fundraising_tracking_app.activity_integration.models import (
    FeedRequest, RefreshRequest, CleanupRequest, ProjectInfoResponse,
    Activity, ActivityComment, ActivityPhoto, ActivityPhotos,
    ActivityFeedResponse, HealthResponse, MetricsResponse,
    JawgTokenResponse, RefreshResponse, CleanupResponse, MapTilesRequest
)


class TestFeedRequest:
    """Test FeedRequest model validation"""
    
    def test_feed_request_valid(self):
        """Test valid FeedRequest creation"""
        request = FeedRequest(
            limit=10,
            activity_type="Run",
            has_photos=True,
            date_from=datetime(2023, 1, 1),
            date_to=datetime(2023, 12, 31),
            min_distance=1000.0,
            max_distance=10000.0
        )
        
        assert request.limit == 10
        assert request.activity_type == "Run"
        assert request.has_photos is True
        assert request.date_from == datetime(2023, 1, 1)
        assert request.date_to == datetime(2023, 12, 31)
        assert request.min_distance == 1000.0
        assert request.max_distance == 10000.0
    
    def test_feed_request_defaults(self):
        """Test FeedRequest with default values"""
        request = FeedRequest()
        
        assert request.limit == 20
        assert request.activity_type is None
        assert request.has_photos is None
        assert request.date_from is None
        assert request.date_to is None
        assert request.min_distance is None
        assert request.max_distance is None
    
    def test_feed_request_date_validation_error(self):
        """Test date_to validation error when date_to <= date_from"""
        with pytest.raises(ValidationError) as exc_info:
            FeedRequest(
                date_from=datetime(2023, 12, 31, 0, 0, 0),
                date_to=datetime(2023, 1, 1, 0, 0, 0)  # date_to is before date_from
            )
        
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["type"] == "value_error"
        assert "date_to must be after date_from" in str(errors[0]["msg"])
    
    def test_feed_request_distance_validation_error(self):
        """Test max_distance validation error when max_distance <= min_distance"""
        with pytest.raises(ValidationError) as exc_info:
            FeedRequest(
                min_distance=5000.0,
                max_distance=1000.0  # max_distance is less than min_distance
            )
        
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["type"] == "value_error"
        assert "max_distance must be greater than min_distance" in str(errors[0]["msg"])
    
    def test_feed_request_valid_date_range(self):
        """Test valid date range validation"""
        request = FeedRequest(
            date_from=datetime(2023, 1, 1, 0, 0, 0),
            date_to=datetime(2023, 12, 31, 0, 0, 0)
        )
        
        assert request.date_from == datetime(2023, 1, 1, 0, 0, 0)
        assert request.date_to == datetime(2023, 12, 31, 0, 0, 0)
    
    def test_feed_request_valid_distance_range(self):
        """Test valid distance range validation"""
        request = FeedRequest(
            min_distance=1000.0,
            max_distance=5000.0
        )
        
        assert request.min_distance == 1000.0
        assert request.max_distance == 5000.0


class TestRefreshRequest:
    """Test RefreshRequest model validation"""
    
    def test_refresh_request_valid(self):
        """Test valid RefreshRequest creation"""
        request = RefreshRequest(
            force_full_refresh=True,
            include_old_activities=True
        )
        
        assert request.force_full_refresh is True
        assert request.include_old_activities is True
    
    def test_refresh_request_defaults(self):
        """Test RefreshRequest with default values"""
        request = RefreshRequest()
        
        assert request.force_full_refresh is False
        assert request.include_old_activities is False


class TestCleanupRequest:
    """Test CleanupRequest model validation"""
    
    def test_cleanup_request_valid(self):
        """Test valid CleanupRequest creation"""
        request = CleanupRequest(
            keep_backups=5,
            force_cleanup=True
        )
        
        assert request.keep_backups == 5
        assert request.force_cleanup is True
    
    def test_cleanup_request_defaults(self):
        """Test CleanupRequest with default values"""
        request = CleanupRequest()
        
        assert request.keep_backups == 1
        assert request.force_cleanup is False


class TestProjectInfoResponse:
    """Test ProjectInfoResponse model"""
    
    def test_project_info_response_creation(self):
        """Test ProjectInfoResponse creation"""
        response = ProjectInfoResponse(
            project="test-project",
            version="1.0.0",
            description="Test project",
            endpoints={
                "health": "/health - Health check endpoint",
                "feed": "/feed - Get activity feed"
            },
            features=["caching", "rate_limiting"],
            cache_duration="1 hour",
            rate_limits={"requests_per_minute": 100}
        )
        
        assert response.project == "test-project"
        assert response.version == "1.0.0"
        assert response.description == "Test project"
        assert "health" in response.endpoints
        assert "feed" in response.endpoints


class TestActivity:
    """Test Activity model"""
    
    def test_activity_creation(self):
        """Test Activity creation"""
        activity = Activity(
            id=123456789,
            name="Morning Run",
            type="Run",
            distance=5000.0,
            moving_time=1800,
            elapsed_time=2000,
            start_date="2023-01-01T08:00:00Z",
            start_date_local="2023-01-01T08:00:00Z",
            timezone="UTC",
            total_elevation_gain=100.0,
            description="Great run!",
            formatted_duration="30:00"
        )
        
        assert activity.id == 123456789
        assert activity.name == "Morning Run"
        assert activity.type == "Run"
        assert activity.distance == 5000.0
        assert activity.moving_time == 1800
        assert activity.elapsed_time == 2000
        assert activity.start_date == "2023-01-01T08:00:00Z"
        assert activity.start_date_local == "2023-01-01T08:00:00Z"
        assert activity.timezone == "UTC"
        assert activity.total_elevation_gain == 100.0
        assert activity.description == "Great run!"


class TestActivityComment:
    """Test ActivityComment model"""
    
    def test_activity_comment_creation(self):
        """Test ActivityComment creation"""
        comment = ActivityComment(
            id=1,
            text="Great job!",
            created_at="2023-01-01T09:00:00Z",
            athlete={"id": 987654321, "name": "John Doe"}
        )
        
        assert comment.id == 1
        assert comment.text == "Great job!"
        assert comment.created_at == "2023-01-01T09:00:00Z"
        assert comment.athlete["id"] == 987654321
        assert comment.athlete["name"] == "John Doe"


class TestActivityPhoto:
    """Test ActivityPhoto model"""
    
    def test_activity_photo_creation(self):
        """Test ActivityPhoto creation"""
        photo = ActivityPhoto(
            url="https://example.com/photo.jpg",
            caption="Beautiful view"
        )
        
        assert photo.url == "https://example.com/photo.jpg"
        assert photo.caption == "Beautiful view"


class TestActivityPhotos:
    """Test ActivityPhotos model"""
    
    def test_activity_photos_creation(self):
        """Test ActivityPhotos creation"""
        primary_photo = ActivityPhoto(url="https://example.com/primary.jpg")
        photos = ActivityPhotos(
            primary=primary_photo,
            count=5
        )
        
        assert photos.primary.url == "https://example.com/primary.jpg"
        assert photos.count == 5


class TestActivityFeedResponse:
    """Test ActivityFeedResponse model"""
    
    def test_activity_feed_response_creation(self):
        """Test ActivityFeedResponse creation"""
        response = ActivityFeedResponse(
            activities=[{
                "id": 1, 
                "name": "Test Run",
                "type": "Run",
                "distance": 1000.0,
                "moving_time": 600,
                "elapsed_time": 700,
                "start_date": "2023-01-01T08:00:00Z",
                "start_date_local": "2023-01-01T08:00:00Z",
                "timezone": "UTC",
                "total_elevation_gain": 50.0,
                "formatted_duration": "10:00"
            }],
            total=1,
            timestamp=datetime.now()
        )
        
        assert len(response.activities) == 1
        assert response.total == 1
        assert response.timestamp is not None


class TestHealthResponse:
    """Test HealthResponse model"""
    
    def test_health_response_creation(self):
        """Test HealthResponse creation"""
        response = HealthResponse(
            project="test-project",
            status="healthy",
            timestamp=datetime.now(),
            activity_configured=True,
            jawg_configured=True,
            cache_status="active"
        )
        
        assert response.status == "healthy"
        assert response.timestamp is not None
        assert response.project == "test-project"
        assert response.activity_configured is True
        assert response.jawg_configured is True
        assert response.cache_status == "active"


class TestMetricsResponse:
    """Test MetricsResponse model"""
    
    def test_metrics_response_creation(self):
        """Test MetricsResponse creation"""
        response = MetricsResponse(
            project="test-project",
            cache_hits=50,
            cache_misses=50,
            api_calls_made=100,
            activities_cached=200,
            cache_size_mb=5.5
        )
        
        assert response.project == "test-project"
        assert response.cache_hits == 50
        assert response.cache_misses == 50
        assert response.api_calls_made == 100
        assert response.activities_cached == 200
        assert response.cache_size_mb == 5.5


class TestJawgTokenResponse:
    """Test JawgTokenResponse model"""
    
    def test_jawg_token_response_creation(self):
        """Test JawgTokenResponse creation"""
        response = JawgTokenResponse(
            token="test_token",
            expires_at=datetime.now()
        )
        
        assert response.token == "test_token"
        assert response.expires_at is not None


class TestRefreshResponse:
    """Test RefreshResponse model"""
    
    def test_refresh_response_creation(self):
        """Test RefreshResponse creation"""
        response = RefreshResponse(
            success=True,
            message="Data refreshed successfully",
            timestamp=datetime.now(),
            activities_updated=5
        )
        
        assert response.success is True
        assert response.message == "Data refreshed successfully"
        assert response.activities_updated == 5
        assert response.timestamp is not None


class TestCleanupResponse:
    """Test CleanupResponse model"""
    
    def test_cleanup_response_creation(self):
        """Test CleanupResponse creation"""
        response = CleanupResponse(
            success=True,
            message="Cleanup completed",
            timestamp=datetime.now(),
            backups_removed=3
        )
        
        assert response.success is True
        assert response.message == "Cleanup completed"
        assert response.backups_removed == 3
        assert response.timestamp is not None


class TestMapTilesRequest:
    """Test MapTilesRequest model"""
    
    def test_map_tiles_request_creation(self):
        """Test MapTilesRequest creation"""
        request = MapTilesRequest(
            z=10,
            x=512,
            y=384,
            style="dark"
        )
        
        assert request.z == 10
        assert request.x == 512
        assert request.y == 384
        assert request.style == "dark"


class TestModelSerialization:
    """Test model serialization and deserialization"""
    
    def test_feed_request_serialization(self):
        """Test FeedRequest serialization"""
        request = FeedRequest(limit=10, activity_type="Run")
        data = request.model_dump()
        
        assert data["limit"] == 10
        assert data["activity_type"] == "Run"
        assert data["has_photos"] is None
    
    def test_feed_request_deserialization(self):
        """Test FeedRequest deserialization"""
        data = {"limit": 15, "activity_type": "Ride", "has_photos": True}
        request = FeedRequest.model_validate(data)
        
        assert request.limit == 15
        assert request.activity_type == "Ride"
        assert request.has_photos is True
    
    def test_activity_serialization(self):
        """Test Activity serialization"""
        activity = Activity(
            id=123,
            name="Test Run",
            type="Run",
            distance=5000.0,
            moving_time=1800,
            elapsed_time=2000,
            start_date="2023-01-01T08:00:00Z",
            start_date_local="2023-01-01T08:00:00Z",
            timezone="UTC",
            total_elevation_gain=100.0,
            formatted_duration="30:00"
        )
        data = activity.model_dump()
        
        assert data["id"] == 123
        assert data["name"] == "Test Run"
        assert data["type"] == "Run"
        assert data["distance"] == 5000.0


class TestEdgeCases:
    """Test edge cases and boundary conditions"""
    
    def test_feed_request_minimum_values(self):
        """Test FeedRequest with minimum valid values"""
        request = FeedRequest(
            limit=1,
            min_distance=0.1,
            max_distance=0.2
        )
        
        assert request.limit == 1
        assert request.min_distance == 0.1
        assert request.max_distance == 0.2
    
    def test_feed_request_maximum_values(self):
        """Test FeedRequest with maximum valid values"""
        request = FeedRequest(
            limit=200,
            min_distance=999999.9,
            max_distance=1000000.0
        )
        
        assert request.limit == 200
        assert request.min_distance == 999999.9
        assert request.max_distance == 1000000.0
    
    def test_cleanup_request_zero_backups(self):
        """Test CleanupRequest with zero backups"""
        request = CleanupRequest(keep_backups=0)
        assert request.keep_backups == 0
    
    def test_activity_optional_fields(self):
        """Test Activity with optional fields as None"""
        activity = Activity(
            id=123,
            name="Test",
            type="Run",
            distance=1000.0,
            moving_time=600,
            elapsed_time=700,
            start_date="2023-01-01T08:00:00Z",
            start_date_local="2023-01-01T08:00:00Z",
            timezone="UTC",
            total_elevation_gain=50.0,
            description=None,
            photos=None,
            comments=None,
            formatted_duration="10:00"
        )
        
        assert activity.description is None
        assert activity.photos is None
        assert activity.comments is None
