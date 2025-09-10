#!/usr/bin/env python3
"""
Minimal Strava Integration API Module
Contains only the essential endpoints used by the demo
"""

from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional
import os
from datetime import datetime
from dotenv import load_dotenv
from .smart_strava_cache import SmartStravaCache

# Load environment variables
load_dotenv()

# Create router for this project
router = APIRouter()

# Initialize the smart cache
cache = SmartStravaCache()

# Project endpoints
@router.get("/")
def project_root():
    """Root endpoint for Strava integration project"""
    return {
        "project": "strava-integration",
        "description": "Personal Strava data integration API",
        "version": "1.0.0",
        "endpoints": {
            "feed": "/feed - Get basic activity feed",
            "feed-complete": "/feed-complete - Get complete feed with maps and comments",
            "map": "/activities/{id}/map - Get GPS data for maps",
            "comments": "/activities/{id}/comments - Get activity comments",
            "jawg-token": "/jawg-token - Get Jawg Maps token"
        }
    }

@router.get("/health")
def health_check():
    """Health check for Strava integration project"""
    return {
        "project": "strava-integration",
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "strava_configured": bool(os.getenv("STRAVA_ACCESS_TOKEN"))
    }

@router.get("/jawg-token")
def get_jawg_token():
    """Get Jawg Maps access token for frontend use"""
    jawg_token = os.getenv("JAWG_ACCESS_TOKEN", "demo")
    return {
        "jawg_access_token": jawg_token,
        "has_token": jawg_token != "demo"
    }

@router.get("/feed")
def get_activity_feed(limit: int = 20):
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
            # Get complete activity data including photos, videos, and descriptions
            detailed_activity = cache.get_complete_activity_data(activity["id"])
            
            feed_item = {
                "id": activity["id"],
                "name": activity["name"],
                "type": activity["type"],
                "distance_km": round(activity["distance"] / 1000, 2) if activity["distance"] else 0,
                "duration_minutes": round(activity["moving_time"] / 60, 1) if activity["moving_time"] else 0,
                "elevation_gain_m": activity.get("total_elevation_gain", 0),
                "date": activity["start_date_local"][:10],
                "time": activity["start_date_local"][11:16],
                "start_date_local": activity["start_date_local"],
                "description": detailed_activity.get("description", ""),
                "kudos_count": detailed_activity.get("kudos_count", 0),
                "comment_count": detailed_activity.get("comment_count", 0),
                "photos": detailed_activity.get("photos", {}),
                "comments": detailed_activity.get("comments", []),
                "map": detailed_activity.get("map", {})
            }
            feed_activities.append(feed_item)
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "total_activities": len(feed_activities),
            "activities": feed_activities
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching activity feed: {str(e)}")


@router.get("/activities/{activity_id}/map")
def get_activity_map(activity_id: int):
    """Get GPS data for activity map visualization"""
    try:
        # Get complete activity data (includes map data)
        activity_data = cache.get_complete_activity_data(activity_id)
        
        # Check if we have map data
        if "map" in activity_data and "gps_points" in activity_data["map"]:
            map_data = activity_data["map"]
            return {
                "activity_id": activity_id,
                "gps_points": map_data.get("gps_points", []),
                "bounds": map_data.get("bounds"),
                "total_points": map_data.get("point_count", 0),
                "source": "complete_cache"
            }
        
        # Fallback to summary polyline if available
        if "map" in activity_data and "summary_polyline" in activity_data["map"]:
            try:
                from polyline import decode
                polyline = activity_data["map"]["summary_polyline"]
                gps_points = [{"lat": lat, "lng": lng} for lat, lng in decode(polyline)]
                
                # Calculate bounds
                bounds = None
                if gps_points:
                    lats = [p["lat"] for p in gps_points]
                    lngs = [p["lng"] for p in gps_points]
                    bounds = {
                        "north": max(lats),
                        "south": min(lats),
                        "east": max(lngs),
                        "west": min(lngs)
                    }
                
                return {
                    "activity_id": activity_id,
                    "gps_points": gps_points,
                    "bounds": bounds,
                    "total_points": len(gps_points),
                    "source": "polyline_cache"
                }
            except ImportError:
                pass
        
        # No map data available
        return {
            "activity_id": activity_id,
            "gps_points": [],
            "bounds": None,
            "total_points": 0,
            "source": "none"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching activity map data: {str(e)}")

@router.get("/activities/{activity_id}/comments")
def get_activity_comments(activity_id: int):
    """Get actual comments for a specific activity"""
    try:
        # Get complete activity data (includes comments)
        activity_data = cache.get_complete_activity_data(activity_id)
        
        comments = activity_data.get("comments", [])
        return {
            "activity_id": activity_id,
            "comments": comments,
            "total_count": len(comments)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching activity comments: {str(e)}")

@router.get("/activities/{activity_id}/complete")
def get_complete_activity(activity_id: int):
    """Get complete activity data including photos, comments, map, and description"""
    try:
        # Get complete activity data
        activity_data = cache.get_complete_activity_data(activity_id)
        
        if not activity_data:
            raise HTTPException(status_code=404, detail="Activity not found")
        
        return activity_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching complete activity data: {str(e)}")


