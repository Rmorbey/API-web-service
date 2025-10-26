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
# Removed complex error handlers - using FastAPI's built-in HTTPException
from ..strava_integration.caching import cache_manager
from ..strava_integration.async_processor import async_processor
from .fundraising_scraper import SmartFundraisingCache
from .models import (
    FundraisingDataResponse, 
    DonationsResponse, 
    HealthResponse, 
    RefreshResponse, 
    CleanupResponse,
    ProjectInfoResponse,
    # Request models (Phase 2)
    FundraisingRefreshRequest,
    FundraisingCleanupRequest,
    DonationsFilterRequest
)
# Removed complex error handlers - using FastAPI's built-in HTTPException

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Lazy initialization for smart cache to prevent multiple instances
JUSTGIVING_URL = "https://www.justgiving.com/fundraising/RussellMorbey-HackneyHalf?utm_medium=FR&utm_source=CL&utm_campaign=015"
_cache_instance = None

def get_cache():
    """Get the cache instance, creating it only when first needed (lazy initialization)"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = SmartFundraisingCache(JUSTGIVING_URL)
    return _cache_instance

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

@router.get("/cache-stats")
def get_cache_stats(api_key: str = Depends(verify_api_key)) -> dict:
    """Get HTTP cache statistics"""
    try:
        stats = cache_manager.get_cache_stats()
        return {
            "success": True,
            "cache_stats": stats,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get cache stats: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching cache statistics: {str(e)}"
        )

@router.post("/cache/invalidate")
def invalidate_cache(
    pattern: Optional[str] = None,
    api_key: str = Depends(verify_api_key)
) -> dict:
    """Invalidate HTTP cache entries"""
    try:
        count = cache_manager.invalidate_cache(pattern)
        return {
            "success": True,
            "message": f"Invalidated {count} cache entries",
            "entries_removed": count,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to invalidate cache: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error invalidating cache: {str(e)}"
        )

@router.get("/health", response_model=HealthResponse)
def fundraising_health() -> HealthResponse:
    """Health check for fundraising scraper"""
    try:
        cache = get_cache()
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

@router.get("/cache-status")
def get_fundraising_cache_status():
    """Get detailed fundraising cache status and health information"""
    try:
        cache = get_cache()
        status = cache.get_cache_status()
        
        return {
            "project": "fundraising-scraper",
            "timestamp": datetime.now().isoformat(),
            "cache_status": status
        }
    except Exception as e:
        logger.error(f"Failed to get fundraising cache status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get fundraising cache status: {str(e)}")

@router.get("/data", response_model=FundraisingDataResponse)
async def get_fundraising_data(api_key: str = Depends(verify_api_key)) -> FundraisingDataResponse:
    """Get current fundraising data from cache with async processing"""
    try:
        cache = get_cache()
        data = cache.get_fundraising_data()
        
        # Process donations in parallel for better performance
        raw_donations = data.get("donations", [])
        
        # Sort donations by date (oldest first - first donor should be first)
        def parse_donation_date(donation):
            date_str = donation.get("date", "")
            if not date_str:
                return 0
            
            # Handle different date formats more robustly
            if "months ago" in date_str:
                try:
                    months = int(date_str.split()[0])
                    return -months  # Negative so older donations come first
                except (ValueError, IndexError):
                    return 0
            elif "weeks ago" in date_str:
                try:
                    weeks = int(date_str.split()[0])
                    return -weeks * 4  # Convert weeks to approximate months
                except (ValueError, IndexError):
                    return 0
            elif "days ago" in date_str:
                try:
                    days = int(date_str.split()[0])
                    return -days / 30  # Convert days to approximate months
                except (ValueError, IndexError):
                    return 0
            elif "hours ago" in date_str:
                try:
                    hours = int(date_str.split()[0])
                    return -hours / (30 * 24)  # Convert hours to approximate months
                except (ValueError, IndexError):
                    return 0
            elif "minutes ago" in date_str:
                try:
                    minutes = int(date_str.split()[0])
                    return -minutes / (30 * 24 * 60)  # Convert minutes to approximate months
                except (ValueError, IndexError):
                    return 0
            else:
                # For unknown formats, try to extract any number
                try:
                    import re
                    numbers = re.findall(r'\d+', date_str)
                    if numbers:
                        return -int(numbers[0])  # Use first number found
                except:
                    pass
                return 0
        
        raw_donations.sort(key=parse_donation_date)
        processed_donations = await async_processor.process_donations_parallel(raw_donations)
        
        # Format the data for frontend consumption
        total_raised = data.get("total_raised", 0)
        target_amount = data.get("target_amount", 300)  # Use scraped target or default to 300
        progress_percentage = round((total_raised / target_amount) * 100, 1) if target_amount > 0 else 0
        
        return FundraisingDataResponse(
            timestamp=datetime.fromisoformat(data.get("timestamp")) if data.get("timestamp") else datetime.now(),
            total_raised=total_raised,
            target_amount=target_amount,
            progress_percentage=progress_percentage,
            donations=processed_donations,
            total_donations=data.get("total_donations", 0),
            last_updated=datetime.fromisoformat(data.get("last_updated")) if data.get("last_updated") else datetime.now(),
            justgiving_url=data.get("justgiving_url", JUSTGIVING_URL)
        )
        
    except Exception as e:
        logger.error(f"Failed to get fundraising data: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching fundraising data: {str(e)}"
        )

@router.post("/refresh", response_model=RefreshResponse)
def refresh_fundraising_data(
    request: FundraisingRefreshRequest, 
    api_key: str = Depends(verify_api_key)
) -> RefreshResponse:
    """Manually trigger a fundraising data scrape with customizable options (requires API key)
    
    Supports:
    - Force refresh even if recently updated
    - Include metadata in response
    """
    try:
        cache = get_cache()
        success = cache.force_refresh_now()
        
        if success:
            response_data = {
                "success": True,
                "message": "Fundraising data refresh triggered successfully",
                "timestamp": datetime.now()
            }
            
            # Include metadata if requested
            if request.include_metadata:
                data = cache.get_fundraising_data()
                response_data.update({
                    "total_raised": data.get("total_raised", 0),
                    "donations_count": data.get("total_donations", 0)
                })
            
            return RefreshResponse(**response_data)
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
async def get_donations(request: DonationsFilterRequest = Depends(), api_key: str = Depends(verify_api_key)) -> DonationsResponse:
    """Get filtered donations data for the scrolling footer with async processing
    
    Supports filtering by:
    - Amount range (min/max)
    - Limit number of results
    - Include/exclude anonymous donations
    """
    try:
        cache = get_cache()
        data = cache.get_fundraising_data()
        all_donations = data.get("donations", [])
        
        # Apply filters
        filtered_donations = all_donations.copy()
        
        # Filter by amount range
        if request.min_amount is not None:
            filtered_donations = [d for d in filtered_donations if d.get("amount", 0) >= request.min_amount]
        
        if request.max_amount is not None:
            filtered_donations = [d for d in filtered_donations if d.get("amount", 0) <= request.max_amount]
        
        # Filter anonymous donations
        if not request.include_anonymous:
            filtered_donations = [d for d in filtered_donations if d.get("donor_name", "").lower() not in ["anonymous", "anon", ""]]
        
        # Sort donations by date (oldest first - first donor should be first)
        # Parse dates and sort chronologically
        def parse_donation_date(donation):
            date_str = donation.get("date", "")
            if not date_str:
                return 0
            
            # Handle different date formats more robustly
            if "months ago" in date_str:
                try:
                    months = int(date_str.split()[0])
                    return -months  # Negative so older donations come first
                except (ValueError, IndexError):
                    return 0
            elif "weeks ago" in date_str:
                try:
                    weeks = int(date_str.split()[0])
                    return -weeks * 4  # Convert weeks to approximate months
                except (ValueError, IndexError):
                    return 0
            elif "days ago" in date_str:
                try:
                    days = int(date_str.split()[0])
                    return -days / 30  # Convert days to approximate months
                except (ValueError, IndexError):
                    return 0
            elif "hours ago" in date_str:
                try:
                    hours = int(date_str.split()[0])
                    return -hours / (30 * 24)  # Convert hours to approximate months
                except (ValueError, IndexError):
                    return 0
            elif "minutes ago" in date_str:
                try:
                    minutes = int(date_str.split()[0])
                    return -minutes / (30 * 24 * 60)  # Convert minutes to approximate months
                except (ValueError, IndexError):
                    return 0
            else:
                # For unknown formats, try to extract any number
                try:
                    import re
                    numbers = re.findall(r'\d+', date_str)
                    if numbers:
                        return -int(numbers[0])  # Use first number found
                except:
                    pass
                return 0
        
        filtered_donations.sort(key=parse_donation_date)
        
        # Apply limit
        if request.limit is not None:
            filtered_donations = filtered_donations[:request.limit]
        
        # Process donations in parallel for better performance
        processed_donations = await async_processor.process_donations_parallel(filtered_donations)
        
        return DonationsResponse(
            donations=processed_donations,
            total_donations=len(processed_donations),
            last_updated=datetime.fromisoformat(data.get("last_updated")) if data.get("last_updated") else datetime.now()
        )
        
    except Exception as e:
        logger.error(f"Failed to get donations: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching donations: {str(e)}"
        )

# Demo endpoints (development only - no API key required for demo pages)
@router.get("/demo/data", response_model=FundraisingDataResponse)
async def get_fundraising_data_demo() -> FundraisingDataResponse:
    """Get fundraising data for demo page (development environment only)"""
    # Verify we're in development environment
    from ..strava_integration.environment_utils import verify_development_access
    verify_development_access()
    try:
        cache = get_cache()
        data = cache.get_fundraising_data()
        
        # Process donations in parallel for better performance
        raw_donations = data.get("donations", [])
        processed_donations = await async_processor.process_donations_parallel(raw_donations)
        
        # Format the data for frontend consumption
        return FundraisingDataResponse(
            timestamp=datetime.fromisoformat(data.get("timestamp")) if data.get("timestamp") else datetime.now(),
            total_raised=data.get("total_raised", 0),
            target_amount=300,  # Your target
            progress_percentage=round((data.get("total_raised", 0) / 300) * 100, 1),
            donations=processed_donations,
            total_donations=data.get("total_donations", 0),
            last_updated=datetime.fromisoformat(data.get("last_updated")) if data.get("last_updated") else datetime.now(),
            justgiving_url=JUSTGIVING_URL
        )
        
    except Exception as e:
        logger.error(f"Failed to get fundraising data for demo: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching fundraising data: {str(e)}"
        )

@router.get("/demo/donations", response_model=DonationsResponse)
async def get_donations_demo(request: DonationsFilterRequest = Depends()) -> DonationsResponse:
    """Get donations for demo page (development environment only)"""
    # Verify we're in development environment
    from ..strava_integration.environment_utils import verify_development_access
    verify_development_access()
    try:
        cache = get_cache()
        data = cache.get_fundraising_data()
        all_donations = data.get("donations", [])
        
        # Apply filters
        filtered_donations = all_donations.copy()
        
        # Filter by amount range
        if request.min_amount is not None:
            filtered_donations = [d for d in filtered_donations if d.get("amount", 0) >= request.min_amount]
        
        if request.max_amount is not None:
            filtered_donations = [d for d in filtered_donations if d.get("amount", 0) <= request.max_amount]
        
        # Filter anonymous donations
        if not request.include_anonymous:
            filtered_donations = [d for d in filtered_donations if d.get("donor_name", "").lower() not in ["anonymous", "anon", ""]]
        
        # Apply limit
        if request.limit is not None:
            filtered_donations = filtered_donations[:request.limit]
        
        # Process donations in parallel for better performance
        processed_donations = await async_processor.process_donations_parallel(filtered_donations)
        
        return DonationsResponse(
            donations=processed_donations,
            total_donations=len(processed_donations),
            last_updated=datetime.fromisoformat(data.get("last_updated")) if data.get("last_updated") else datetime.now()
        )
        
    except Exception as e:
        logger.error(f"Failed to get donations for demo: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching donations: {str(e)}"
        )

@router.post("/cleanup-backups", response_model=CleanupResponse)
def cleanup_backups(
    request: FundraisingCleanupRequest, 
    api_key: str = Depends(verify_api_key)
) -> CleanupResponse:
    """Manually trigger backup cleanup with customizable options (requires API key)
    
    Supports:
    - Configurable number of backups to keep
    - Force cleanup even if cache is recent
    """
    try:
        cache = get_cache()
        # Note: The current cache.cleanup_backups() doesn't accept parameters
        # This is a placeholder for future enhancement
        success = cache.cleanup_backups()
        
        if success:
            return CleanupResponse(
                success=True,
                message=f"Backup cleanup completed successfully (keeping {request.keep_backups} backups)",
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
