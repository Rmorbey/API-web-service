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
        raise HTTPException(status_code=401, detail="API key required")
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return x_api_key

@router.get("/")
def fundraising_root():
    """Root endpoint for fundraising project"""
    return {
        "project": "fundraising-scraper",
        "description": "JustGiving fundraising data scraper and API",
        "version": "1.0.0",
        "endpoints": {
            "data": "/data - Get current fundraising data",
            "refresh": "/refresh - Manually trigger scrape",
            "health": "/health - Health check"
        },
        "source": "JustGiving",
        "scrape_interval": "15 minutes"
    }

@router.get("/health")
def fundraising_health():
    """Health check for fundraising scraper"""
    try:
        cache_data = cache.get_fundraising_data()
        return {
            "project": "fundraising-scraper",
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "scraper_running": cache.running,
            "last_updated": cache_data.get("last_updated"),
            "total_raised": cache_data.get("total_raised", 0),
            "total_donations": cache_data.get("total_donations", 0)
        }
    except Exception as e:
        logger.error(f"Fundraising health check failed: {e}")
        return {
            "project": "fundraising-scraper",
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

@router.get("/data")
def get_fundraising_data():
    """Get current fundraising data from cache"""
    try:
        data = cache.get_fundraising_data()
        
        # Format the data for frontend consumption
        formatted_data = {
            "timestamp": data.get("timestamp"),
            "total_raised": data.get("total_raised", 0),
            "target_amount": 300,  # Your target
            "progress_percentage": round((data.get("total_raised", 0) / 300) * 100, 1),
            "donations": data.get("donations", []),
            "total_donations": data.get("total_donations", 0),
            "last_updated": data.get("last_updated"),
            "justgiving_url": JUSTGIVING_URL
        }
        
        return formatted_data
        
    except Exception as e:
        logger.error(f"Failed to get fundraising data: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching fundraising data: {str(e)}")

@router.post("/refresh")
def refresh_fundraising_data(api_key: str = Depends(verify_api_key)):
    """Manually trigger a fundraising data scrape (requires API key)"""
    try:
        success = cache.force_refresh_now()
        
        if success:
            return {
                "success": True,
                "message": "Fundraising data refresh triggered successfully",
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "success": False,
                "error": "Failed to trigger fundraising data refresh",
                "timestamp": datetime.now().isoformat()
            }
            
    except Exception as e:
        logger.error(f"Manual refresh failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@router.get("/donations")
def get_donations():
    """Get just the donations data for the scrolling footer"""
    try:
        data = cache.get_fundraising_data()
        donations = data.get("donations", [])
        
        # Format donations for the scrolling text
        formatted_donations = []
        for donation in donations:
            donor_name = donation.get("donor_name", "Anonymous")
            amount = donation.get("amount", 0)
            message = donation.get("message", "")
            
            # Create formatted donation string
            if message:
                donation_text = f"£{amount:.0f} {donor_name}: \"{message}\""
            else:
                donation_text = f"£{amount:.0f} {donor_name}"
            
            formatted_donations.append(donation_text)
        
        return {
            "donations": formatted_donations,
            "total_donations": len(formatted_donations),
            "last_updated": data.get("last_updated")
        }
        
    except Exception as e:
        logger.error(f"Failed to get donations: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching donations: {str(e)}")

@router.post("/cleanup-backups")
def cleanup_backups(api_key: str = Depends(verify_api_key)):
    """Manually trigger backup cleanup (requires API key)"""
    try:
        success = cache.cleanup_backups()
        
        if success:
            return {
                "success": True,
                "message": "Backup cleanup completed successfully",
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "success": False,
                "error": "Failed to cleanup backups",
                "timestamp": datetime.now().isoformat()
            }
            
    except Exception as e:
        logger.error(f"Backup cleanup failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
