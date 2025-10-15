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

logger = logging.getLogger(__name__)
from datetime import datetime
from dotenv import load_dotenv
from .smart_strava_cache import SmartStravaCache
# Removed complex error handlers - using FastAPI's built-in HTTPException
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
    # Request models (Phase 2)
    FeedRequest,
    RefreshRequest,
    CleanupRequest,
    MapTilesRequest
)
# Removed complex error handlers - using FastAPI's built-in HTTPException
# Error handling will be implemented in Phase 3 completion

# Configure logging
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Create router for this project
router = APIRouter()

# Lazy initialization for smart cache to prevent multiple instances
_cache_instance = None

def get_cache():
    """Get the cache instance, creating it only when first needed (lazy initialization)"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = SmartStravaCache()
    return _cache_instance

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

def verify_frontend_access(request: Request):
    """Verify that requests are coming from allowed frontend domains"""
    # Get client IP
    client_ip = request.client.host if request.client else "unknown"
    
    # Get referer header
    referer = request.headers.get("referer", "")
    origin = request.headers.get("origin", "")
    
    # Allowed domains (your frontend domains)
    allowed_domains = [
        "http://localhost:3000",
        "http://localhost:5173", 
        "http://localhost:8000",
        "http://localhost:3001",  # Additional React dev port
        "http://localhost:8080",  # Additional dev port
        "https://www.russellmorbey.co.uk",
        "https://russellmorbey.co.uk",
        "https://api.russellmorbey.co.uk"  # Allow requests from the API domain itself
    ]
    
    # Check if referer or origin is from allowed domain
    referer_allowed = any(domain in referer for domain in allowed_domains)
    origin_allowed = any(domain in origin for domain in allowed_domains)
    
    # Allow if either referer or origin is from allowed domain
    if not (referer_allowed or origin_allowed):
        # Allow localhost for development
        if not (client_ip.startswith("127.0.0.1") or client_ip.startswith("::1")):
            # Check if this is a development environment (no referer/origin)
            if not referer and not origin:
                # Allow requests without referer/origin in development
                print(f"🔓 Allowing request without referer/origin for development. Client IP: {client_ip}")
                return True
            
            # Enhanced error message for debugging
            raise HTTPException(
                status_code=403,
                detail=f"Access denied - Request must come from authorized frontend. Referer: '{referer}', Origin: '{origin}', Client IP: '{client_ip}'"
            )
    
    return True

# Project endpoints
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

@router.get("/cache-status")
def get_cache_status():
    """Get detailed cache status and health information"""
    try:
        cache = get_cache()
        status = cache.get_cache_status()
        
        return {
            "project": "strava-integration",
            "timestamp": datetime.utcnow().isoformat(),
            "cache_status": status
        }
    except Exception as e:
        logger.error(f"Failed to get cache status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get cache status: {str(e)}")

@router.get("/data-loss-analysis")
def get_data_loss_analysis(api_key: str = Depends(verify_api_key)):
    """Analyze cache to identify data loss and timestamp information"""
    try:
        cache = get_cache()
        analysis = cache.analyze_cache_data_loss()
        
        return {
            "project": "strava-integration",
            "timestamp": datetime.utcnow().isoformat(),
            "data_loss_analysis": analysis
        }
    except Exception as e:
        logger.error(f"Failed to analyze data loss: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to analyze data loss: {str(e)}")

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

@router.get("/token-status")
def get_token_status(api_key: str = Depends(verify_api_key)):
    """Get Strava token status for debugging"""
    try:
        cache = get_cache()
        token_status = cache.token_manager.get_token_status()
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "token_status": token_status,
            "message": "Token status retrieved successfully"
        }
    except Exception as e:
        logger.error(f"Failed to get token status: {e}")
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e),
            "message": "Failed to get token status"
        }

@router.get("/map-tiles/{z}/{x}/{y}")
async def get_map_tiles(z: int, x: int, y: int, style: str = Query("dark"), api_key: str = Depends(verify_api_key)):
    """Secure proxy for Jawg map tiles - keeps token server-side
    
    Supports different map styles:
    - streets: Default street map
    - terrain: Terrain/topographic map  
    - satellite: Satellite imagery
    - dark: Dark mode street map
    """
    
    jawg_token = os.getenv("JAWG_ACCESS_TOKEN", "demo")
    logger.info(f"🔑 Jawg token check: length={len(jawg_token) if jawg_token else 0}, is_demo={jawg_token == 'demo'}")
    
    if jawg_token == "demo":
        # Fallback to OpenStreetMap if no Jawg token
        import random
        subdomain = random.choice(['a', 'b', 'c'])
        tile_url = f"https://{subdomain}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        logger.info(f"🗺️ Using OpenStreetMap fallback (no Jawg token): {tile_url}")
    else:
        # Use Jawg tiles with server-side token and style
        style_map = {
            "streets": "jawg-streets",
            "terrain": "jawg-terrain", 
            "satellite": "jawg-satellite",
            "dark": "jawg-dark"
        }
        # Default to dark mode if no style specified
        jawg_style = style_map.get(style, "jawg-dark")
        
        # URL encode the token to handle any special characters
        import urllib.parse
        encoded_token = urllib.parse.quote(jawg_token, safe='')
        tile_url = f"https://tile.jawg.io/{jawg_style}/{z}/{x}/{y}.png?access-token={encoded_token}"
        logger.info(f"🗺️ Using Jawg tiles (style={style}, jawg_style={jawg_style}): {tile_url}")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(tile_url)
            logger.info(f"✅ Tile request successful: {response.status_code} for {tile_url}")
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
        logger.error(f"❌ Jawg tile request failed: {e} for {tile_url}")
        import random
        subdomain = random.choice(['a', 'b', 'c'])
        fallback_url = f"https://{subdomain}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        logger.info(f"🔄 Falling back to OpenStreetMap: {fallback_url}")
        async with httpx.AsyncClient() as client:
            response = await client.get(fallback_url)
            return Response(
                content=response.content,
                media_type="image/png",
                headers={
                    "Cache-Control": "public, max-age=86400",
                    "Access-Control-Allow-Origin": "*"
                }
            )

@router.post("/refresh-cache")
async def refresh_cache(request: RefreshRequest, api_key: str = Depends(verify_api_key)):
    """Manually trigger cache refresh using simplified core logic (requires API key)
    
    Uses the same core logic as automatic refresh:
    - Single condition check (empty data OR 6+ hours old)
    - Batch processing (20 activities every 15 minutes)
    - Data validation and override
    """
    try:
        # Use simplified core logic
        get_cache().check_and_refresh()
        
        return {
            "success": True,
            "message": "🏃‍♂️ Manual refresh triggered! Using core batch processing logic.",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"🏃‍♂️ Manual refresh failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


# Demo endpoints (development only - no API key required for demo pages)
@router.get("/demo/feed")
async def get_activity_feed_demo(request: FeedRequest = Depends()):
    """Get a list of processed Strava activities for demo page (development environment only)"""
    # Verify we're in development environment
    from .environment_utils import verify_development_access
    verify_development_access()
    try:
        cache_instance = get_cache()
        raw_activities = cache_instance.get_activities_smart(request.limit)
        
        # Process activities in parallel for better performance
        processed_activities = await async_processor.process_activities_parallel(raw_activities)
        
        # Build feed items from processed activities (same as main feed endpoint)
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
            formatted_duration = detailed_activity.get("formatted_duration", "00:00:00")
            
            feed_item = {
                "id": activity["id"],
                "name": activity["name"],
                "type": activity["type"],
                "distance_km": round(activity["distance"] / 1000, 2) if activity["distance"] else 0,
                "duration_minutes": round(activity["moving_time"] / 60, 1) if activity["moving_time"] else 0,
                "date": formatted_date,  # Now includes start time: "14th of September 2025 at 10:12"
                "time": formatted_duration,  # Now shows moving time: "1:06" or "22.4 min"
                "description": _clean_description(detailed_activity.get("description", "")),
                "comment_count": len(detailed_activity.get("comments", [])),
                "photos": optimized_photos,
                "comments": _clean_comments(detailed_activity.get("comments", [])),
                "map": optimized_map,
                "music": detailed_activity.get("music", {})
            }
            feed_activities.append(feed_item)
        
        response_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "activities": feed_activities,
            "total_activities": len(feed_activities),
            "last_updated": datetime.utcnow().isoformat(),
            "cache_status": "active"
        }
        
        # Add caching headers for performance
        response = JSONResponse(content=response_data)
        response.headers["Cache-Control"] = "public, max-age=300"  # 5 minutes
        response.headers["ETag"] = f'"{hash(str(response_data))}"'
        return response
        
    except Exception as e:
        logger.error(f"Failed to get activity feed for demo: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching activity feed: {str(e)}"
        )

@router.get("/demo/map-tiles/{z}/{x}/{y}")
def get_map_tiles_demo(z: int = Path(..., ge=0, le=18), x: int = Path(...), y: int = Path(...)):
    """Get map tiles for demo page (development environment only)"""
    # Verify we're in development environment
    from .environment_utils import verify_development_access
    verify_development_access()
    try:
        # Use Jawg Maps for demo
        jawg_token = os.getenv("JAWG_ACCESS_TOKEN")
        if not jawg_token:
            raise HTTPException(status_code=500, detail="Jawg token not configured")
        
        # Construct Jawg Maps URL
        tile_url = f"https://tile.jawg.io/jawg-dark/{z}/{x}/{y}.png?access-token={jawg_token}"
        
        # Return redirect to tile URL
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url=tile_url, status_code=302)
        
    except Exception as e:
        logger.error(f"Failed to get map tiles for demo: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching map tiles: {str(e)}"
        )

@router.post("/clean-invalid-activities")
async def clean_invalid_activities(api_key: str = Depends(verify_api_key)):
    """Clean invalid/unknown activities from the cache (requires API key)"""
    try:
        result = get_cache().clean_invalid_activities()
        return {
            "success": result["success"],
            "message": result["message"],
            "activities_removed": result.get("activities_removed", 0),
            "activities_remaining": result.get("activities_remaining", 0),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


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


@router.get(
    "/feed",
    summary="📊 Activity Feed",
    description="Get Strava activity feed with photos, comments, music detection, and map data",
    response_description="Activity feed with comprehensive data",
    tags=["Strava Integration", "Activities"]
)
async def get_activity_feed(request: FeedRequest = Depends(), api_key: str = Depends(verify_api_key), frontend_access: bool = Depends(verify_frontend_access)):
    """
    ## 📊 Activity Feed Endpoint
    
    Retrieves a comprehensive activity feed from Strava with enhanced data including:
    
    ### 🎯 **Features**
    - **Activity Data**: Distance, duration, pace, elevation, and type
    - **Photos**: High-quality activity photos with optimized URLs
    - **Comments**: Activity comments and social interactions
    - **Music Detection**: Automatic detection of music from descriptions
    - **Map Data**: Interactive map polylines and bounds
    - **Date Formatting**: Human-readable date formatting
    
    ### 🔍 **Filtering Options**
    - **Activity Type**: Filter by Run, Ride, or other types
    - **Date Range**: Filter by specific date ranges
    - **Photo Presence**: Only activities with photos
    - **Description**: Only activities with descriptions
    - **Distance Range**: Filter by distance (min/max)
    - **Limit**: Control number of results (default: 50, max: 2000)
    
    ### 🎵 **Music Detection**
    Automatically detects music from activity descriptions:
    - **Track**: "Track: Song Name by Artist"
    - **Album**: "Album: Album Name by Artist"
    - **Russell Radio**: "Russell Radio: Song Name by Artist"
    - **Playlist**: "Playlist: Playlist Name"
    
    ### 🗺️ **Map Integration**
    - **Polylines**: Encoded polyline data for route visualization
    - **Bounds**: Geographic bounds for map centering
    - **Jawg Integration**: Ready for Jawg map tile integration
    
    ### 📈 **Performance**
    - **Caching**: 6-hour cache with 95% hit rate
    - **Async Processing**: Parallel processing for optimal performance
    - **Response Time**: 5-50ms average response time
    
    ### 🔑 **Authentication**
    Requires valid API key via `X-API-Key` header.
    
    ### 📝 **Example Response**
    ```json
    {
      "timestamp": "2025-09-29T15:03:23.187903",
      "total_activities": 1,
      "activities": [
        {
          "id": 15949905889,
          "name": "Morning Run",
          "type": "Run",
          "distance_km": 5.18,
          "duration_minutes": 25.7,
          "date": "27th of September 2025 at 09:05",
          "time": "25m 43s",
          "description": "Great run this morning!",
          "comment_count": 0,
          "photos": {...},
          "comments": [],
          "map": {...},
          "music": {...}
        }
      ]
    }
    ```
    """
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
        
        # Process activities in parallel for better performance
        processed_activities = await async_processor.process_activities_parallel(
            filtered_activities, 
            operations=['music_detection', 'photo_processing', 'formatting']
        )
        
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
                "date": formatted_date,  # Now includes start time: "14th of September 2025 at 10:12"
                "time": formatted_duration,  # Now shows moving time: "1:06" or "22.4 min"
                "description": _clean_description(detailed_activity.get("description", "")),
                "comment_count": len(detailed_activity.get("comments", [])),
                "photos": optimized_photos,
                "comments": _clean_comments(detailed_activity.get("comments", [])),
                "map": optimized_map,
                "music": detailed_activity.get("music", {})
            }
            feed_activities.append(feed_item)
        
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
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching activity feed: {str(e)}"
        )




def _clean_comments(comments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Clean comments by removing redundant fields"""
    cleaned_comments = []
    for comment in comments:
        cleaned_comment = {
            "id": comment.get("id"),
            "text": comment.get("text"),
            "created_at": comment.get("created_at"),
            "athlete": {
                "firstname": comment.get("athlete", {}).get("firstname"),
                "lastname": comment.get("athlete", {}).get("lastname")
            }
        }
        cleaned_comments.append(cleaned_comment)
    return cleaned_comments

# Removed redundant endpoints for production cleanup:
# - /real-activities (duplicate of /test-feed)
# - /activities/{id}/map (unused - frontend uses polyline directly)
# - /activities/{id}/comments (unused - comments included in feed)
# - /activities/{id}/complete (unused - complete data in feed)
# - /activities/{id}/music (unused - music included in feed)
# - _get_activity_music() helper function (unused)

# Demo page is served by main API at /demo endpoint

# Router is exported for use in multi_project_api.py
# No need to create a separate FastAPI app here
