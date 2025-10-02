# 📚 Strava Integration API - Complete Code Explanation

## 🎯 **Overview**

This file contains all the **API endpoints** for the Strava integration service. It's a **FastAPI router** that gets included in the main application. Think of it as a **module** that handles all Strava-related requests.

## 📁 **File Structure Context**

```
strava_integration_api.py  ← YOU ARE HERE (API Endpoints)
├── smart_strava_cache.py  (Data fetching & caching)
├── models.py              (Data structures)
├── async_processor.py     (Background processing)
├── security.py            (Authentication)
└── caching.py             (HTTP caching)
```

## 🔍 **Line-by-Line Code Explanation**

### **1. Imports and Setup (Lines 1-46)**

```python
#!/usr/bin/env python3
"""
Minimal Strava Integration API Module
Contains only the essential endpoints used by the demo
"""

from fastapi import FastAPI, APIRouter, HTTPException, Query, Path, Header, Depends, Request
from fastapi.responses import Response, JSONResponse, HTMLResponse
from typing import List, Dict, Any, Optional
import os
import httpx
import logging
```

**What this does:**
- **FastAPI imports**: All the tools needed to create API endpoints
- **`APIRouter`**: Groups related endpoints together (like a mini-app)
- **`Depends`**: For dependency injection (like requiring API keys)
- **`httpx`**: Modern HTTP client for making requests to external APIs
- **`logging`**: For recording what happens in the application

```python
from .smart_strava_cache import SmartStravaCache
from .caching import cache_manager
from .async_processor import async_processor
from .models import (
    ActivityFeedResponse, 
    HealthResponse, 
    MetricsResponse, 
    JawgTokenResponse,
    RefreshResponse,
    CleanupResponse,
    ProjectInfoResponse,
    Activity,
    FeedRequest,
    RefreshRequest,
    CleanupRequest,
    MapTilesRequest
)
```

**What this does:**
- **Relative imports** (`.`) from the same package
- **`SmartStravaCache`**: The main class that fetches and caches Strava data
- **`cache_manager`**: Manages HTTP response caching
- **`async_processor`**: Handles background processing (music detection, etc.)
- **`models`**: Pydantic models that define data structures and validation

```python
# Create router for this project
router = APIRouter()
```

**What this does:**
- **Creates a router** - a collection of endpoints
- **This router gets included** in the main app later
- **All endpoints in this file** will be prefixed with `/api/strava-integration`

### **2. Lazy Initialization Pattern (Lines 48-56)**

```python
# Lazy initialization for smart cache to prevent multiple instances
_cache_instance = None

def get_cache():
    """Get the cache instance, creating it only when first needed (lazy initialization)"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = SmartStravaCache()
    return _cache_instance
```

**What this does:**
- **Lazy initialization**: Only creates the cache when it's first needed
- **Singleton pattern**: Ensures only one cache instance exists
- **Why this matters**: Prevents multiple cache instances from running simultaneously
- **Memory efficient**: Doesn't create the cache until it's actually used

**Learning Point**: This is a common pattern in Python for expensive objects that should only be created once.

### **3. Security Functions (Lines 58-103)**

```python
# API Key for protected endpoints
API_KEY = os.getenv("STRAVA_API_KEY")
if not API_KEY:
    raise ValueError("STRAVA_API_KEY environment variable is required")

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
- **Gets API key** from environment variables
- **Raises error** if API key is not configured
- **`verify_api_key` function**: Validates API keys sent in requests
- **`Header(None)`**: Extracts the `X-API-Key` header from the request
- **Returns 401**: If no API key is provided
- **Returns 403**: If API key is wrong

```python
def verify_frontend_access(request: Request):
    """Verify that requests are coming from allowed frontend domains"""
    # Get client IP
    client_ip = request.client.host if request.client else "unknown"
    
    # Get referer header
    referer = request.headers.get("referer", "")
    
    # Allowed domains (your frontend domains)
    allowed_domains = [
        "http://localhost:3000",
        "http://localhost:5173", 
        "http://localhost:8000",
        "https://www.russellmorbey.co.uk",
        "https://russellmorbey.co.uk"
    ]
    
    # Check if referer is from allowed domain
    if not any(domain in referer for domain in allowed_domains):
        # Allow localhost for development
        if not (client_ip.startswith("127.0.0.1") or client_ip.startswith("::1")):
            raise HTTPException(
                status_code=403,
                detail="Access denied - Request must come from authorized frontend"
            )
    
    return True
```

**What this does:**
- **Frontend verification**: Ensures requests come from your authorized domains
- **Gets client IP**: To check if it's localhost
- **Gets referer header**: To see which website made the request
- **Allowed domains**: List of your frontend domains
- **Security check**: Only allows requests from authorized domains
- **Localhost exception**: Allows localhost for development

**Learning Point**: This is **defense in depth** - multiple layers of security.

### **4. Project Information Endpoint (Lines 105-125)**

```python
@router.get("/")
def project_root():
    """Root endpoint for Strava integration project"""
    return {
        "project": "strava-integration",
        "description": "Personal Strava data integration API - Production Ready",
        "version": "2.0.0",
        "endpoints": {
            "feed": "/feed - Get optimized activity feed with all data",
            "jawg-token": "/jawg-token - Get Jawg Maps token",
            "health": "/health - Health check",
            "metrics": "/metrics - System metrics"
        },
        "optimizations": {
            "api_calls": "1 call per activity (80% reduction)",
            "cache_size": "25.6% reduction with polyline-only maps",
            "data_structure": "Optimized for frontend consumption",
            "redundant_endpoints": "5 endpoints removed"
        }
    }
```

**What this does:**
- **`@router.get("/")`**: Creates a GET endpoint at the root of this router
- **Project information**: Returns metadata about this service
- **Available endpoints**: Lists all the endpoints this service provides
- **Optimizations**: Shows performance improvements made

**URL**: `GET /api/strava-integration/`

### **5. Health Check Endpoint (Lines 127-137)**

```python
@router.get("/health")
def health_check():
    """Health check for Strava integration project"""
    return {
        "project": "strava-integration",
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "strava_configured": bool(os.getenv("STRAVA_ACCESS_TOKEN")),
        "jawg_configured": bool(os.getenv("JAWG_ACCESS_TOKEN")),
        "cache_status": "active" if get_cache()._cache_data else "inactive"
    }
```

**What this does:**
- **Health check**: Tells you if the service is working
- **Configuration status**: Checks if required environment variables are set
- **Cache status**: Checks if the cache is active
- **Used by monitoring**: Load balancers and monitoring systems use this

**URL**: `GET /api/strava-integration/health`

### **6. Cache Management Endpoints (Lines 139-175)**

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
```

**What this does:**
- **`Depends(verify_api_key)`**: Requires valid API key to access
- **Cache statistics**: Shows how well the cache is performing
- **Error handling**: Catches exceptions and returns proper HTTP errors
- **Logging**: Records errors for debugging

```python
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
- **Cache invalidation**: Clears cached responses
- **Pattern matching**: Can clear specific cache entries
- **Returns count**: Shows how many entries were cleared
- **Admin function**: Only accessible with API key

### **7. Metrics Endpoint (Lines 177-198)**

```python
@router.get("/metrics")
def get_metrics(api_key: str = Depends(verify_api_key)):
    """Get system metrics and performance data"""
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "api_calls": {
            "total_made": get_cache().api_calls_made,
            "max_per_15min": get_cache().max_calls_per_15min,
            "max_per_day": get_cache().max_calls_per_day,
            "reset_time": get_cache().api_calls_reset_time.isoformat()
        },
        "cache": {
            "in_memory_active": get_cache()._cache_data is not None,
            "cache_ttl": get_cache()._cache_ttl,
            "cache_duration_hours": get_cache().cache_duration_hours
        },
        "system": {
            "strava_configured": bool(os.getenv("STRAVA_ACCESS_TOKEN")),
            "jawg_configured": bool(os.getenv("JAWG_ACCESS_TOKEN")),
            "music_integration": "active"
        }
    }
```

**What this does:**
- **Performance metrics**: Shows how the system is performing
- **API call tracking**: Monitors Strava API usage
- **Cache status**: Shows cache configuration and status
- **System status**: Shows what services are configured

**Learning Point**: This is **observability** - making your system transparent and monitorable.

### **8. Jawg Maps Integration (Lines 200-270)**

```python
@router.get("/jawg-token")
def get_jawg_token():
    """Get Jawg Maps access token for frontend use - SECURE VERSION"""
    jawg_token = os.getenv("JAWG_ACCESS_TOKEN", "demo")
    
    # SECURITY: Don't expose the actual token to frontend
    # Instead, return a flag indicating if token is available
    # The frontend will use our backend proxy for map tiles
    return {
        "has_token": jawg_token != "demo",
        "token_length": len(jawg_token) if jawg_token != "demo" else 0,
        "message": "Token available" if jawg_token != "demo" else "Using demo token"
    }
```

**What this does:**
- **Security first**: Doesn't expose the actual token to frontend
- **Token availability**: Just tells frontend if token is available
- **Demo fallback**: Uses "demo" if no token is configured
- **Why this matters**: Prevents token theft from frontend

```python
@router.get("/map-tiles/{z}/{x}/{y}")
async def get_map_tiles(z: int, x: int, y: int, style: str = Query("dark"), token: str = Query(None)):
    """Secure proxy for Jawg map tiles - keeps token server-side"""
    # Validate frontend token
    if not token or token != os.getenv("STRAVA_API_KEY"):
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing token for map tiles"
        )
    
    jawg_token = os.getenv("JAWG_ACCESS_TOKEN", "demo")
    
    if jawg_token == "demo":
        # Fallback to OpenStreetMap if no Jawg token
        tile_url = f"https://{{s}}.tile.openstreetmap.org/{z}/{x}/{y}.png"
    else:
        # Use Jawg tiles with server-side token and style
        style_map = {
            "streets": "jawg-streets",
            "terrain": "jawg-terrain", 
            "satellite": "jawg-satellite",
            "dark": "jawg-dark"
        }
        jawg_style = style_map.get(style, "jawg-dark")
        tile_url = f"https://tile.jawg.io/{jawg_style}/{z}/{x}/{y}.png?access-token={jawg_token}"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(tile_url)
            return Response(
                content=response.content,
                media_type=response.headers.get("content-type", "image/png"),
                headers={
                    "Cache-Control": "public, max-age=86400",  # Cache for 24 hours
                    "Access-Control-Allow-Origin": "*"
                }
            )
    except Exception as e:
        # Fallback to OpenStreetMap on error
        async with httpx.AsyncClient() as client:
            response = await client.get(f"https://tile.openstreetmap.org/{z}/{x}/{y}.png")
            return Response(
                content=response.content,
                media_type="image/png",
                headers={
                    "Cache-Control": "public, max-age=86400",
                    "Access-Control-Allow-Origin": "*"
                }
            )
```

**What this does:**
- **Map tile proxy**: Serves map tiles through your backend
- **Path parameters**: `{z}/{x}/{y}` are standard map tile coordinates
- **Token validation**: Requires your API key to access tiles
- **Style support**: Different map styles (dark, streets, satellite)
- **Fallback system**: Uses OpenStreetMap if Jawg fails
- **Caching**: Caches tiles for 24 hours
- **CORS headers**: Allows frontend to load tiles

**Learning Point**: This is a **proxy pattern** - your backend acts as a middleman to keep tokens secure.

### **9. Cache Management Endpoints (Lines 272-352)**

```python
@router.post("/refresh-cache")
async def refresh_cache(request: RefreshRequest, api_key: str = Depends(verify_api_key)):
    """Manually trigger cache refresh with batch processing (requires API key)"""
    try:
        # Force an immediate refresh using the automated system
        success = get_cache().force_refresh_now()
        
        if success:
            return {
                "success": True,
                "message": "Cache refresh started! Processing activities in 20-activity batches every 15 minutes.",
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "success": False,
                "error": "Failed to start cache refresh",
                "timestamp": datetime.now().isoformat()
            }
    except Exception as e:
        logger.error(f"Cache refresh failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
```

**What this does:**
- **Manual cache refresh**: Forces the cache to update immediately
- **Batch processing**: Updates activities in batches to avoid rate limits
- **Success/failure handling**: Returns appropriate responses
- **Admin function**: Only accessible with API key

### **10. The Main Feed Endpoint (Lines 425-573)**

This is the **most important endpoint** - it's what your frontend uses to get activity data.

```python
@router.get(
    "/feed",
    summary="📊 Activity Feed",
    description="Get Strava activity feed with photos, comments, music detection, and map data",
    response_description="Activity feed with comprehensive data",
    tags=["Strava Integration", "Activities"]
)
async def get_activity_feed(request: FeedRequest = Depends(), api_key: str = Depends(verify_api_key), frontend_access: bool = Depends(verify_frontend_access)):
```

**What this does:**
- **`@router.get("/feed")`**: Creates the main feed endpoint
- **`FeedRequest = Depends()`**: Automatically parses query parameters
- **`api_key: str = Depends(verify_api_key)`**: Requires API key
- **`frontend_access: bool = Depends(verify_frontend_access)`**: Verifies frontend domain

```python
try:
    # Get activities from cache (backend already filters by Run/Ride and date)
    raw_activities = get_cache().get_activities_smart(request.limit)
    
    # Apply additional filtering based on request parameters
    filtered_activities = _apply_feed_filters(raw_activities, request)
    
    # Handle case where no activities are returned
    if not filtered_activities:
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "total_activities": 0,
            "activities": [],
            "message": "No activities available (rate limited or no data)"
        }
```

**What this does:**
- **Gets cached data**: No API calls to Strava (fast!)
- **Applies filters**: Based on request parameters
- **Handles empty results**: Returns appropriate message

```python
    # Process activities in parallel for better performance
    processed_activities = await async_processor.process_activities_parallel(
        filtered_activities, 
        operations=['music_detection', 'photo_processing', 'formatting']
    )
```

**What this does:**
- **Parallel processing**: Processes multiple activities at once
- **Music detection**: Finds music in activity descriptions
- **Photo processing**: Optimizes photo URLs
- **Date formatting**: Formats dates for display

```python
    # Build feed items from processed activities
    feed_activities = []
    for activity in processed_activities:
        # Use cached data only - no additional API calls
        detailed_activity = activity
        
        # Optimize map data - only use polyline (not summary_polyline)
        map_data = detailed_activity.get("map", {})
        optimized_map = {
            "polyline": map_data.get("polyline"),
            "bounds": map_data.get("bounds", {})
        }
        
        # Use processed photos from async processor
        optimized_photos = detailed_activity.get("photos", {})
        
        # Use processed date formatting from async processor
        formatted_date = detailed_activity.get("date_formatted", activity["start_date_local"])
        formatted_duration = detailed_activity.get("duration_formatted", "00:00:00")
        
        feed_item = {
            "id": activity["id"],
            "name": activity["name"],
            "type": activity["type"],
            "distance_km": round(activity["distance"] / 1000, 2) if activity["distance"] else 0,
            "duration_minutes": round(activity["moving_time"] / 60, 1) if activity["moving_time"] else 0,
            "date": formatted_date,
            "time": formatted_duration,
            "description": _clean_description(detailed_activity.get("description", "")),
            "comment_count": len(detailed_activity.get("comments", [])),
            "photos": optimized_photos,
            "comments": _clean_comments(detailed_activity.get("comments", [])),
            "map": optimized_map,
            "music": detailed_activity.get("music", {})
        }
        feed_activities.append(feed_item)
```

**What this does:**
- **Builds response**: Creates the final data structure for frontend
- **Optimizes data**: Only includes what the frontend needs
- **Formats data**: Converts units (meters to km, seconds to minutes)
- **Cleans data**: Removes unnecessary fields

```python
    response_data = {
        "timestamp": datetime.utcnow().isoformat(),
        "total_activities": len(feed_activities),
        "activities": feed_activities
    }
    
    # Add caching headers for performance
    response = JSONResponse(content=response_data)
    response.headers["Cache-Control"] = "public, max-age=300"  # 5 minutes
    response.headers["ETag"] = f'"{hash(str(response_data))}"'
    return response
```

**What this does:**
- **Final response**: Packages everything into the response
- **Caching headers**: Tells browsers to cache for 5 minutes
- **ETag**: For cache validation
- **Returns JSON**: Standard API response format

### **11. Helper Functions (Lines 355-422)**

```python
def _clean_description(description: str) -> str:
    """Clean description by removing music-related text patterns"""
    if not description:
        return ""
    
    import re
    
    # Remove music-related patterns
    patterns_to_remove = [
        r'Russell Radio:.*?(?=\n|$)',  # Remove "Russell Radio: ..." lines
        r'Album:.*?(?=\n|$)',          # Remove "Album: ..." lines
        r'Artist:.*?(?=\n|$)',         # Remove "Artist: ..." lines (if any)
        r'Song:.*?(?=\n|$)',           # Remove "Song: ..." lines (if any)
        r'Track:.*?(?=\n|$)',          # Remove "Track: ..." lines (if any)
    ]
    
    cleaned = description
    for pattern in patterns_to_remove:
        cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE | re.MULTILINE)
    
    # Clean up extra whitespace and newlines
    cleaned = re.sub(r'\n\s*\n', '\n', cleaned)  # Remove multiple newlines
    cleaned = cleaned.strip()  # Remove leading/trailing whitespace
    
    return cleaned
```

**What this does:**
- **Text cleaning**: Removes music-related text from descriptions
- **Regex patterns**: Uses regular expressions to find and remove text
- **Whitespace cleanup**: Removes extra spaces and newlines
- **Returns clean text**: For better display in frontend

```python
def _apply_feed_filters(activities: List[Dict[str, Any]], request: FeedRequest) -> List[Dict[str, Any]]:
    """Apply additional filtering to activities based on request parameters"""
    filtered = activities.copy()
    
    # Filter by activity type (additional to backend filtering)
    if request.activity_type:
        filtered = [a for a in filtered if a.get("type") == request.activity_type]
    
    # Filter by date range
    if request.date_from or request.date_to:
        for activity in filtered[:]:  # Use slice copy to avoid modification during iteration
            try:
                activity_date = datetime.fromisoformat(activity["start_date_local"].replace('Z', '+00:00'))
                activity_date_naive = activity_date.replace(tzinfo=None)
                
                if request.date_from and activity_date_naive < request.date_from:
                    filtered.remove(activity)
                    continue
                if request.date_to and activity_date_naive > request.date_to:
                    filtered.remove(activity)
                    continue
            except (ValueError, KeyError):
                # If date parsing fails, keep the activity
                continue
    
    # Filter by photo presence
    if request.has_photos is not None:
        filtered = [a for a in filtered if bool(a.get("photos", {}).get("primary", {}).get("url")) == request.has_photos]
    
    # Filter by description presence
    if request.has_description is not None:
        filtered = [a for a in filtered if bool(a.get("description", "").strip()) == request.has_description]
    
    # Filter by distance range
    if request.min_distance is not None:
        filtered = [a for a in filtered if a.get("distance", 0) >= request.min_distance]
    
    if request.max_distance is not None:
        filtered = [a for a in filtered if a.get("distance", 0) <= request.max_distance]
    
    return filtered
```

**What this does:**
- **Advanced filtering**: Applies additional filters to activities
- **Activity type**: Filter by Run, Ride, etc.
- **Date range**: Filter by start date
- **Photo presence**: Only activities with/without photos
- **Description presence**: Only activities with/without descriptions
- **Distance range**: Filter by distance (min/max)

## 🎯 **Key Learning Points**

### **1. FastAPI Router Pattern**
- **Modular design**: Each service has its own router
- **Dependency injection**: Using `Depends()` for authentication and validation
- **Error handling**: Proper HTTP status codes and error messages

### **2. Security Best Practices**
- **API key authentication**: Protecting sensitive endpoints
- **Frontend verification**: Ensuring requests come from authorized domains
- **Token security**: Not exposing sensitive tokens to frontend

### **3. Performance Optimization**
- **Caching**: Multiple layers of caching (HTTP, in-memory)
- **Parallel processing**: Processing multiple activities simultaneously
- **Data optimization**: Only sending what the frontend needs

### **4. Error Handling**
- **Try/catch blocks**: Catching and handling errors gracefully
- **HTTP exceptions**: Returning proper HTTP status codes
- **Logging**: Recording errors for debugging

### **5. API Design**
- **RESTful endpoints**: Following REST conventions
- **Rich documentation**: Detailed descriptions and examples
- **Consistent responses**: Standard response format

## 🚀 **How This Fits Into Your Learning**

This file demonstrates:
- **FastAPI routing**: How to organize endpoints
- **Security patterns**: Authentication and authorization
- **Performance patterns**: Caching and parallel processing
- **Error handling**: Graceful error management
- **API design**: Creating user-friendly APIs

**Next**: We'll explore the `SmartStravaCache` class to understand how data is fetched and cached! 🎉
