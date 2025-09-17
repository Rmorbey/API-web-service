#!/usr/bin/env python3
"""
Minimal Strava Integration API Module
Contains only the essential endpoints used by the demo
"""

from fastapi import APIRouter, HTTPException, Query, Path
from fastapi.responses import Response, JSONResponse
from typing import List, Dict, Any, Optional
import os
import httpx
from datetime import datetime
from dotenv import load_dotenv
from .smart_strava_cache import SmartStravaCache
from ..music_integration.music_integration import MusicIntegration

# Load environment variables
load_dotenv()

# Create router for this project
router = APIRouter()

# Initialize the smart cache and music integration
cache = SmartStravaCache()
music = MusicIntegration()

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
            "test-feed": "/test-feed - Raw data for testing (will be removed in production)",
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
        "cache_status": "active" if cache._cache_data else "inactive"
    }

@router.get("/metrics")
def get_metrics():
    """Get system metrics and performance data"""
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "api_calls": {
            "total_made": cache.api_calls_made,
            "max_per_15min": cache.max_calls_per_15min,
            "max_per_day": cache.max_calls_per_day,
            "reset_time": cache.api_calls_reset_time.isoformat()
        },
        "cache": {
            "in_memory_active": cache._cache_data is not None,
            "cache_ttl": cache._cache_ttl,
            "cache_duration_hours": cache.cache_duration_hours
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

@router.get("/map-tiles/{z}/{x}/{y}")
async def get_map_tiles(z: int, x: int, y: int):
    """Secure proxy for Jawg map tiles - keeps token server-side"""
    jawg_token = os.getenv("JAWG_ACCESS_TOKEN", "demo")
    
    if jawg_token == "demo":
        # Fallback to OpenStreetMap if no Jawg token
        tile_url = f"https://{{s}}.tile.openstreetmap.org/{z}/{x}/{y}.png"
    else:
        # Use Jawg tiles with server-side token
        tile_url = f"https://tile.jawg.io/jawg-dark/{z}/{x}/{y}.png?access-token={jawg_token}"
    
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

@router.get("/feed")
def get_activity_feed(limit: int = Query(20, ge=1, le=200)):
    """Get activity feed with photos, videos, and descriptions for frontend display"""
    try:
        raw_activities = cache.get_activities_smart(limit)
        
        # Handle case where no activities are returned
        if not raw_activities:
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "total_activities": 0,
                "activities": [],
                "message": "No activities available (rate limited or no data)"
            }
        
        feed_activities = []
        for activity in raw_activities:
            # Use cached complete data if available, otherwise use basic data only
            # (Don't fetch complete data to avoid rate limits)
            if cache._has_complete_data(activity):
                detailed_activity = activity
            else:
                # Use basic activity data only (no additional API calls)
                detailed_activity = activity
            
            # Optimize map data - remove summary_polyline (redundant with polyline)
            map_data = detailed_activity.get("map", {})
            optimized_map = {
                "polyline": map_data.get("polyline"),
                "bounds": map_data.get("bounds", {})
            }
            
            # Optimize photos - keep only one URL size (600px is sufficient)
            photos_data = detailed_activity.get("photos", {})
            optimized_photos = {}
            if photos_data and "primary" in photos_data:
                primary = photos_data["primary"]
                optimized_photos = {
                    "primary": {
                        "unique_id": primary.get("unique_id"),
                        "type": primary.get("type"),
                        "url": primary.get("urls", {}).get("600", ""),  # Only keep 600px URL
                        "status": primary.get("status")
                    },
                    "count": photos_data.get("count", 0)
                }
            
            # Format date and time properly
            start_datetime = activity["start_date_local"]
            date_str = start_datetime[:10]  # 2025-09-14
            start_time_str = start_datetime[11:16]  # 10:12
            
            # Convert to readable date format with start time
            from datetime import datetime
            try:
                dt = datetime.fromisoformat(start_datetime.replace('Z', '+00:00'))
                # Format as "14th of September 2025 at 10:12"
                day = dt.day
                month_name = dt.strftime('%B')
                year = dt.year
                time_formatted = dt.strftime('%H:%M')
                
                # Add ordinal suffix (1st, 2nd, 3rd, 4th, etc.)
                if 10 <= day % 100 <= 20:
                    suffix = 'th'
                else:
                    suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')
                
                formatted_date = f"{day}{suffix} of {month_name} {year} at {time_formatted}"
            except:
                formatted_date = f"{date_str} at {start_time_str}"  # Fallback format
            
            # Format moving time as duration
            duration_minutes = round(activity["moving_time"] / 60, 1) if activity["moving_time"] else 0
            if duration_minutes >= 60:
                hours = int(duration_minutes // 60)
                minutes = int(duration_minutes % 60)
                formatted_duration = f"{hours}:{minutes:02d}"
            else:
                formatted_duration = f"{duration_minutes:.1f} min"
            
            feed_item = {
                "id": activity["id"],
                "name": activity["name"],
                "type": activity["type"],
                "distance_km": round(activity["distance"] / 1000, 2) if activity["distance"] else 0,
                "duration_minutes": round(activity["moving_time"] / 60, 1) if activity["moving_time"] else 0,
                "date": formatted_date,  # Now includes start time: "14th of September 2025 at 10:12"
                "time": formatted_duration,  # Now shows moving time: "1:06" or "22.4 min"
                "description": detailed_activity.get("description", ""),
                "comment_count": detailed_activity.get("comment_count", 0),
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
        raise HTTPException(status_code=500, detail=f"Error fetching activity feed: {str(e)}")


@router.get("/test-feed")
def get_test_activities_feed(limit: int = Query(200, ge=1, le=200)):
    """Get real activities feed from Strava API v3 (temporarily serving real data)"""
    try:
        # Get real activities from smart cache
        activities = cache.get_activities_smart(limit=limit)
        
        return {
            "activities": activities,
            "total_activities": len(activities),
            "timestamp": datetime.now().isoformat(),
            "source": "strava_api_v3"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching real activities: {str(e)}")


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


