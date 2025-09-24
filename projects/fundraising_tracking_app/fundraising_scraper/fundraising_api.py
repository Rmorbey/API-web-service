#!/usr/bin/env python3
"""
Fundraising API Module
Provides endpoints for fundraising data from JustGiving scraper
"""

from fastapi import APIRouter, HTTPException, Header, Depends
from typing import Dict, Any, Optional
import logging
from datetime import datetime
import os
from .fundraising_scraper import SmartFundraisingCache
from .models import (
    FundraisingDataResponse, 
    DonationsResponse, 
    HealthResponse, 
    RefreshResponse, 
    CleanupResponse,
    ProjectInfoResponse
)
from ..strava_integration.error_handlers import (
    AuthenticationException,
    AuthorizationException,
    APIException
)

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Initialize the smart cache
JUSTGIVING_URL = "https://www.justgiving.com/fundraising/RussellMorbey-HackneyHalf?utm_medium=FR&utm_source=CL&utm_campaign=015"
cache = SmartFundraisingCache(JUSTGIVING_URL)

# API Key for protected endpoints
API_KEY = os.getenv("FUNDRAISING_API_KEY")
if not API_KEY:
    raise ValueError("FUNDRAISING_API_KEY environment variable is required")

def verify_api_key(x_api_key: Optional[str] = Header(None)):
    """Verify API key for protected endpoints"""
    if not x_api_key:
        raise HTTPException(
            status_code=401,
            detail="API key required - X-API-Key header is missing"
        )
    if x_api_key != API_KEY:
        raise HTTPException(
            status_code=403,
            detail="Invalid API key - The provided API key is not valid"
        )
    return x_api_key

@router.get("/", response_model=ProjectInfoResponse)
def fundraising_root() -> ProjectInfoResponse:
    """Root endpoint for fundraising project"""
    return ProjectInfoResponse(
        project="fundraising-scraper",
        description="JustGiving fundraising data scraper and API",
        version="1.0.0",
        endpoints={
            "data": "/data - Get current fundraising data",
            "refresh": "/refresh - Manually trigger scrape",
            "health": "/health - Health check"
        },
        source="JustGiving",
        scrape_interval="15 minutes"
    )

@router.get("/health", response_model=HealthResponse)
def fundraising_health() -> HealthResponse:
    """Health check for fundraising scraper"""
    try:
        cache_data = cache.get_fundraising_data()
        return HealthResponse(
            project="fundraising-scraper",
            status="healthy",
            timestamp=datetime.now(),
            scraper_running=cache.running,
            last_scrape=datetime.fromisoformat(cache_data.get("last_updated")) if cache_data.get("last_updated") else None,
            cache_status="active"
        )
    except Exception as e:
        logger.error(f"Fundraising health check failed: {e}")
        return HealthResponse(
            project="fundraising-scraper",
            status="unhealthy",
            timestamp=datetime.now(),
            scraper_running=False,
            last_scrape=None,
            cache_status="error"
        )

@router.get("/data", response_model=FundraisingDataResponse)
def get_fundraising_data() -> FundraisingDataResponse:
    """Get current fundraising data from cache"""
    try:
        data = cache.get_fundraising_data()
        
        # Format the data for frontend consumption
        return FundraisingDataResponse(
            timestamp=datetime.fromisoformat(data.get("timestamp")) if data.get("timestamp") else datetime.now(),
            total_raised=data.get("total_raised", 0),
            target_amount=300,  # Your target
            progress_percentage=round((data.get("total_raised", 0) / 300) * 100, 1),
            donations=data.get("donations", []),
            total_donations=data.get("total_donations", 0),
            last_updated=datetime.fromisoformat(data.get("last_updated")) if data.get("last_updated") else datetime.now(),
            justgiving_url=JUSTGIVING_URL
        )
        
    except Exception as e:
        logger.error(f"Failed to get fundraising data: {e}")
        raise APIException(
            error_code="INTERNAL_SERVER_ERROR",
            message="Error fetching fundraising data",
            detail=f"Failed to retrieve fundraising data: {str(e)}",
            status_code=500
        )

@router.post("/refresh", response_model=RefreshResponse)
def refresh_fundraising_data(api_key: str = Depends(verify_api_key)) -> RefreshResponse:
    """Manually trigger a fundraising data scrape (requires API key)"""
    try:
        success = cache.force_refresh_now()
        
        if success:
            # Get updated data to include in response
            data = cache.get_fundraising_data()
            return RefreshResponse(
                success=True,
                message="Fundraising data refresh triggered successfully",
                timestamp=datetime.now(),
                total_raised=data.get("total_raised", 0),
                donations_count=data.get("total_donations", 0)
            )
        else:
            return RefreshResponse(
                success=False,
                message="Failed to trigger fundraising data refresh",
                timestamp=datetime.now()
            )
            
    except Exception as e:
        logger.error(f"Manual refresh failed: {e}")
        return RefreshResponse(
            success=False,
            message=f"Refresh failed: {str(e)}",
            timestamp=datetime.now()
        )

@router.get("/donations", response_model=DonationsResponse)
def get_donations() -> DonationsResponse:
    """Get just the donations data for the scrolling footer"""
    try:
        data = cache.get_fundraising_data()
        donations = data.get("donations", [])
        
        return DonationsResponse(
            donations=donations,
            total_donations=len(donations),
            last_updated=datetime.fromisoformat(data.get("last_updated")) if data.get("last_updated") else datetime.now()
        )
        
    except Exception as e:
        logger.error(f"Failed to get donations: {e}")
        raise APIException(
            error_code="INTERNAL_SERVER_ERROR",
            message="Error fetching donations",
            detail=f"Failed to retrieve donations data: {str(e)}",
            status_code=500
        )

@router.post("/cleanup-backups", response_model=CleanupResponse)
def cleanup_backups(api_key: str = Depends(verify_api_key)) -> CleanupResponse:
    """Manually trigger backup cleanup (requires API key)"""
    try:
        success = cache.cleanup_backups()
        
        if success:
            return CleanupResponse(
                success=True,
                message="Backup cleanup completed successfully",
                timestamp=datetime.now()
            )
        else:
            return CleanupResponse(
                success=False,
                message="Failed to cleanup backups",
                timestamp=datetime.now()
            )
            
    except Exception as e:
        logger.error(f"Backup cleanup failed: {e}")
        return CleanupResponse(
            success=False,
            message=f"Cleanup failed: {str(e)}",
            timestamp=datetime.now()
        )
