#!/usr/bin/env python3
"""
Pydantic models for Strava Integration API
Defines request and response models for type safety and validation
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime


class ActivityPhoto(BaseModel):
    """Activity photo data"""
    url: str = Field(..., description="Photo URL")
    caption: Optional[str] = Field(None, description="Photo caption")


class ActivityPhotos(BaseModel):
    """Activity photos container"""
    primary: Optional[ActivityPhoto] = Field(None, description="Primary photo")
    count: int = Field(default=0, description="Total photo count")


class ActivityComment(BaseModel):
    """Activity comment data"""
    id: int = Field(..., description="Comment ID")
    text: str = Field(..., description="Comment text")
    created_at: str = Field(..., description="Comment creation date")
    athlete: Dict[str, Any] = Field(..., description="Commenter information")


class Activity(BaseModel):
    """Strava activity data"""
    id: int = Field(..., description="Activity ID")
    name: str = Field(..., description="Activity name")
    type: str = Field(..., description="Activity type")
    distance: float = Field(..., description="Distance in meters")
    moving_time: int = Field(..., description="Moving time in seconds")
    elapsed_time: int = Field(..., description="Total elapsed time in seconds")
    start_date: str = Field(..., description="Activity start date")
    start_date_local: str = Field(..., description="Local start date")
    timezone: str = Field(..., description="Activity timezone")
    total_elevation_gain: float = Field(..., description="Total elevation gain in meters")
    description: Optional[str] = Field(None, description="Activity description")
    photos: Optional[ActivityPhotos] = Field(None, description="Activity photos")
    comments: Optional[List[ActivityComment]] = Field(None, description="Activity comments")
    polyline: Optional[str] = Field(None, description="GPS polyline data")
    bounds: Optional[List[float]] = Field(None, description="Activity bounds")
    has_media: bool = Field(default=False, description="Whether activity has media")
    media_type: str = Field(default="none", description="Type of media (photo/video/none)")
    photo_url: Optional[str] = Field(None, description="Primary photo URL")
    formatted_duration: str = Field(..., description="Formatted duration (HH:MM:SS)")


class ActivityFeedResponse(BaseModel):
    """Response model for activity feed endpoint"""
    activities: List[Activity] = Field(..., description="List of activities")
    total: int = Field(..., description="Total number of activities")
    timestamp: datetime = Field(..., description="Response timestamp")


class HealthResponse(BaseModel):
    """Response model for health check endpoint"""
    project: str = Field(..., description="Project name")
    status: str = Field(..., description="Health status")
    timestamp: datetime = Field(..., description="Health check timestamp")
    strava_configured: bool = Field(..., description="Whether Strava is configured")
    jawg_configured: bool = Field(..., description="Whether Jawg Maps is configured")
    cache_status: str = Field(..., description="Cache status")


class MetricsResponse(BaseModel):
    """Response model for metrics endpoint"""
    project: str = Field(..., description="Project name")
    cache_hits: int = Field(..., description="Number of cache hits")
    cache_misses: int = Field(..., description="Number of cache misses")
    api_calls_made: int = Field(..., description="Number of API calls made")
    last_refresh: Optional[datetime] = Field(None, description="Last refresh timestamp")
    activities_cached: int = Field(..., description="Number of activities in cache")
    cache_size_mb: float = Field(..., description="Cache size in MB")


class JawgTokenResponse(BaseModel):
    """Response model for Jawg token endpoint"""
    token: str = Field(..., description="Jawg Maps access token")
    expires_at: Optional[datetime] = Field(None, description="Token expiration time")


class RefreshResponse(BaseModel):
    """Response model for refresh endpoint"""
    success: bool = Field(..., description="Whether refresh was successful")
    message: str = Field(..., description="Refresh result message")
    timestamp: datetime = Field(..., description="Refresh timestamp")
    activities_updated: Optional[int] = Field(None, description="Number of activities updated")


class CleanupResponse(BaseModel):
    """Response model for cleanup endpoint"""
    success: bool = Field(..., description="Whether cleanup was successful")
    message: str = Field(..., description="Cleanup result message")
    timestamp: datetime = Field(..., description="Cleanup timestamp")
    backups_removed: Optional[int] = Field(None, description="Number of old backups removed")


class ProjectInfoResponse(BaseModel):
    """Response model for project root endpoint"""
    project: str = Field(..., description="Project name")
    description: str = Field(..., description="Project description")
    version: str = Field(..., description="Project version")
    endpoints: Dict[str, str] = Field(..., description="Available endpoints")
    features: List[str] = Field(..., description="Available features")
    cache_duration: str = Field(..., description="Cache duration")
    rate_limits: Dict[str, Any] = Field(..., description="Rate limit information")


# ============================================================================
# REQUEST MODELS (Phase 2)
# ============================================================================

class FeedRequest(BaseModel):
    """Request model for activity feed endpoint with filtering options"""
    limit: int = Field(default=20, ge=1, le=200, description="Number of activities to return")
    activity_type: Optional[Literal["Run", "Ride"]] = Field(
        default=None, 
        description="Filter by activity type (Run or Ride)"
    )
    date_from: Optional[datetime] = Field(
        default=None, 
        description="Filter activities from this date onwards"
    )
    date_to: Optional[datetime] = Field(
        default=None, 
        description="Filter activities up to this date"
    )
    has_photos: Optional[bool] = Field(
        default=None, 
        description="Filter activities that have photos (true) or don't have photos (false)"
    )
    has_description: Optional[bool] = Field(
        default=None, 
        description="Filter activities that have descriptions (true) or don't have descriptions (false)"
    )
    min_distance: Optional[float] = Field(
        default=None, 
        ge=0, 
        description="Minimum distance in meters"
    )
    max_distance: Optional[float] = Field(
        default=None, 
        ge=0, 
        description="Maximum distance in meters"
    )

    @validator('date_to')
    def validate_date_range(cls, v, values):
        """Validate that date_to is after date_from"""
        if v and 'date_from' in values and values['date_from']:
            if v <= values['date_from']:
                raise ValueError('date_to must be after date_from')
        return v

    @validator('max_distance')
    def validate_distance_range(cls, v, values):
        """Validate that max_distance is greater than min_distance"""
        if v and 'min_distance' in values and values['min_distance']:
            if v <= values['min_distance']:
                raise ValueError('max_distance must be greater than min_distance')
        return v


class RefreshRequest(BaseModel):
    """Request model for manual refresh endpoint"""
    force_full_refresh: bool = Field(
        default=False, 
        description="Force a full refresh instead of smart merge"
    )
    include_old_activities: bool = Field(
        default=False, 
        description="Include activities older than 3 weeks in refresh"
    )
    batch_size: int = Field(
        default=20, 
        ge=1, 
        le=50, 
        description="Number of activities to process in each batch"
    )


class CleanupRequest(BaseModel):
    """Request model for cleanup endpoints"""
    keep_backups: int = Field(
        default=1, 
        ge=0, 
        le=10, 
        description="Number of recent backups to keep"
    )
    force_cleanup: bool = Field(
        default=False, 
        description="Force cleanup even if cache is recent"
    )


class MapTilesRequest(BaseModel):
    """Request model for map tiles endpoint"""
    z: int = Field(..., ge=0, le=18, description="Zoom level")
    x: int = Field(..., ge=0, description="Tile X coordinate")
    y: int = Field(..., ge=0, description="Tile Y coordinate")
    style: Optional[Literal["streets", "terrain", "satellite", "dark"]] = Field(
        default="streets", 
        description="Map style"
    )
