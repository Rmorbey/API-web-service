#!/usr/bin/env python3
"""
Pydantic models for Strava Integration API
Defines request and response models for type safety and validation
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
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
