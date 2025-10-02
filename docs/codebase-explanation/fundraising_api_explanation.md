# 📚 Fundraising API - Complete Code Explanation

## 🎯 **Overview**

This module provides **API endpoints** for the fundraising integration, allowing you to access JustGiving fundraising data, donations, and manage the fundraising cache. Think of it as the **fundraising service** that handles all donation-related requests and data processing.

## 📁 **File Structure Context**

```
fundraising_api.py  ← YOU ARE HERE (Fundraising API Endpoints)
├── fundraising_scraper.py  (Uses this for data scraping)
├── models.py               (Uses these for data structures)
├── async_processor.py      (Uses this for data processing)
└── caching.py              (Uses this for HTTP caching)
```

## 🔍 **Line-by-Line Code Explanation**

### **1. Imports and Setup (Lines 1-34)**

```python
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
```

**What this does:**
- **FastAPI imports**: Core FastAPI functionality for API endpoints
- **Standard library**: `logging`, `datetime`, `os` for basic functionality
- **Cross-module imports**: Uses shared components from Strava integration
- **Local imports**: Uses fundraising-specific models and scraper
- **Type hints**: For better code documentation and error catching

### **2. Router and Cache Setup (Lines 33-45)**

```python
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
```

**What this does:**
- **Router creation**: Creates FastAPI router for fundraising endpoints
- **JustGiving URL**: Your specific fundraising page URL
- **Lazy initialization**: Only creates cache when first needed
- **Singleton pattern**: Ensures only one cache instance exists
- **URL configuration**: Centralized URL management

### **3. API Key Authentication (Lines 47-64)**

```python
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
```

**What this does:**
- **Environment variable**: Gets API key from environment
- **Validation**: Ensures API key is configured
- **Header extraction**: Gets API key from `X-API-Key` header
- **Authentication**: Validates API key for protected endpoints
- **Error responses**: Returns appropriate HTTP status codes

### **4. Project Information Endpoint (Lines 66-80)**

```python
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
```

**What this does:**
- **Project information**: Returns metadata about the fundraising service
- **Available endpoints**: Lists all available API endpoints
- **Configuration info**: Shows scrape interval and data source
- **API documentation**: Helps users understand the service

### **5. Cache Management Endpoints (Lines 82-118)**

```python
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
```

**What this does:**
- **Cache statistics**: Shows HTTP cache performance metrics
- **Cache invalidation**: Clears cached responses
- **Pattern matching**: Can clear specific cache entries
- **Admin functions**: Only accessible with API key
- **Error handling**: Graceful error management

### **6. Health Check Endpoint (Lines 120-143)**

```python
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
```

**What this does:**
- **Health monitoring**: Checks if the fundraising service is working
- **Scraper status**: Shows if the scraper is running
- **Last scrape time**: Shows when data was last updated
- **Cache status**: Shows if cache is active
- **Error handling**: Returns unhealthy status on errors

### **7. Main Data Endpoint (Lines 145-173)**

```python
@router.get("/data", response_model=FundraisingDataResponse)
async def get_fundraising_data(api_key: str = Depends(verify_api_key)) -> FundraisingDataResponse:
    """Get current fundraising data from cache with async processing"""
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
        logger.error(f"Failed to get fundraising data: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching fundraising data: {str(e)}"
        )
```

**What this does:**
- **Data retrieval**: Gets fundraising data from cache
- **Async processing**: Processes donations in parallel
- **Progress calculation**: Calculates progress percentage
- **Data formatting**: Formats data for frontend consumption
- **Target tracking**: Shows progress towards £300 target

**Data Structure:**
- **`total_raised`**: Amount raised so far
- **`target_amount`**: Your fundraising target (£300)
- **`progress_percentage`**: Percentage of target achieved
- **`donations`**: List of individual donations
- **`total_donations`**: Number of donations received

### **8. Manual Refresh Endpoint (Lines 175-219)**

```python
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
```

**What this does:**
- **Manual refresh**: Forces immediate data scraping
- **Force option**: Can override recent update checks
- **Metadata inclusion**: Can include current data in response
- **Success/failure handling**: Returns appropriate responses
- **Error handling**: Graceful error management

### **9. Donations Filtering Endpoint (Lines 221-267)**

```python
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
```

**What this does:**
- **Donation filtering**: Filters donations by various criteria
- **Amount filtering**: Min/max amount filtering
- **Anonymous filtering**: Include/exclude anonymous donations
- **Limit application**: Limits number of results
- **Async processing**: Processes donations in parallel
- **Privacy protection**: Handles anonymous donations appropriately

**Filtering Options:**
- **`min_amount`**: Minimum donation amount
- **`max_amount`**: Maximum donation amount
- **`include_anonymous`**: Whether to include anonymous donations
- **`limit`**: Maximum number of donations to return

### **10. Backup Cleanup Endpoint (Lines 269-305)**

```python
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
```

**What this does:**
- **Backup cleanup**: Removes old backup files
- **Configurable retention**: Can specify how many backups to keep
- **Force option**: Can force cleanup even if cache is recent
- **Admin function**: Only accessible with API key
- **Future enhancement**: Placeholder for parameter support

## 🎯 **Key Learning Points**

### **1. API Design**
- **RESTful endpoints**: Following REST conventions
- **Response models**: Consistent response structure
- **Error handling**: Proper HTTP status codes
- **Documentation**: Clear endpoint descriptions

### **2. Authentication**
- **API key protection**: Securing sensitive endpoints
- **Header validation**: Extracting API keys from headers
- **Error responses**: Clear authentication error messages
- **Environment variables**: Secure credential storage

### **3. Data Processing**
- **Async processing**: Parallel donation processing
- **Data filtering**: Multiple filtering options
- **Data formatting**: Frontend-ready data structure
- **Progress calculation**: Target tracking and percentages

### **4. Cache Management**
- **Cache statistics**: Performance monitoring
- **Cache invalidation**: Manual cache clearing
- **Cache integration**: Using shared cache manager
- **Admin functions**: Cache management endpoints

### **5. Error Handling**
- **Try/catch blocks**: Comprehensive error handling
- **HTTP exceptions**: Proper error responses
- **Logging**: Error recording for debugging
- **Graceful degradation**: Fallback responses

## 🚀 **How This Fits Into Your Learning**

This module demonstrates:
- **FastAPI routing**: Organizing API endpoints
- **Authentication patterns**: API key validation
- **Data processing**: Async and parallel processing
- **Cache management**: HTTP caching integration
- **API design**: RESTful endpoint design

**Next**: We'll explore the `fundraising_scraper.py` to understand how data is scraped from JustGiving! 🎉
