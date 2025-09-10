#!/usr/bin/env python3
"""
Minimal Smart Strava Caching Strategy
Contains only essential methods used by the API
"""

import os
import json
import httpx
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from .strava_token_manager import StravaTokenManager

load_dotenv()

class SmartStravaCache:
    def __init__(self, cache_duration_hours: int = None):
        self.token_manager = StravaTokenManager()
        self.base_url = "https://www.strava.com/api/v3"
        self.cache_file = "projects/fundraising_tracking_app/strava_integration/strava_cache.json"
        
        # Allow custom cache duration, default to 6 hours
        self.cache_duration_hours = cache_duration_hours or int(os.getenv("STRAVA_CACHE_HOURS", "6"))
        
        # Filtering criteria
        self.allowed_activity_types = ["Run", "Ride"]  # Only runs and bike rides
        self.start_date = datetime(2025, 5, 22)  # May 22nd, 2025 onwards
        
    def _load_cache(self) -> Dict[str, Any]:
        """Load cache from file"""
        try:
            with open(self.cache_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {"timestamp": None, "activities": []}
    
    def _save_cache(self, data: Dict[str, Any]):
        """Save cache to file"""
        with open(self.cache_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _is_cache_valid(self, cache_data: Dict[str, Any]) -> bool:
        """Check if cache is still valid"""
        if not cache_data.get("timestamp"):
            return False
        
        cache_time = datetime.fromisoformat(cache_data["timestamp"])
        expiry_time = cache_time + timedelta(hours=self.cache_duration_hours)
        
        return datetime.now() < expiry_time
    
    def _filter_activities(self, activities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter activities based on type and date"""
        filtered = []
        
        for activity in activities:
            # Filter by activity type
            if activity.get("type") not in self.allowed_activity_types:
                continue
            
            # Filter by date (May 22nd, 2025 onwards)
            try:
                activity_date = datetime.fromisoformat(activity["start_date"].replace('Z', '+00:00'))
                # Convert to naive datetime for comparison
                activity_date_naive = activity_date.replace(tzinfo=None)
                if activity_date_naive < self.start_date:
                    continue
            except (ValueError, KeyError):
                continue
            
            filtered.append(activity)
        
        return filtered
    
    def get_activities_smart(self, limit: int = 200, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        Get activities with smart caching strategy
        Uses cache if valid, otherwise fetches from Strava API
        """
        cache_data = self._load_cache()
        
        # Use cache if valid and not forcing refresh
        if not force_refresh and self._is_cache_valid(cache_data):
            print(f"📋 Using cached data ({len(cache_data['activities'])} activities)")
            return cache_data["activities"][:limit]
        
        # Cache is invalid or force refresh - fetch from Strava
        print("🔄 Cache expired or invalid, fetching fresh data from Strava...")
        
        try:
            # Fetch fresh data from Strava
            fresh_activities = self._fetch_from_strava(limit * 2)  # Fetch more to account for filtering
            
            # Filter activities
            filtered_activities = self._filter_activities(fresh_activities)
            
            # Update cache
            cache_data = {
                "timestamp": datetime.now().isoformat(),
                "activities": filtered_activities,
                "total_fetched": len(fresh_activities),
                "total_filtered": len(filtered_activities)
            }
            
            self._save_cache(cache_data)
            
            print(f"✅ Cached {len(filtered_activities)} activities (filtered from {len(fresh_activities)})")
            return filtered_activities[:limit]
            
        except Exception as e:
            print(f"❌ Error fetching from Strava: {e}")
            # Fallback to cached data even if expired
            if cache_data.get("activities"):
                print("⚠️  Using stale cached data as fallback")
                return cache_data["activities"][:limit]
            else:
                print("❌ No cached data available, returning empty list")
                return []
    
    def _fetch_from_strava(self, limit: int) -> List[Dict[str, Any]]:
        """Fetch activities directly from Strava API"""
        access_token = self.token_manager.get_valid_access_token()
        
        import asyncio
        
        async def fetch_activities():
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/athlete/activities",
                    headers={"Authorization": f"Bearer {access_token}"},
                    params={"per_page": min(limit, 200), "page": 1}
                )
                response.raise_for_status()
                return response.json()
        
        return asyncio.run(fetch_activities())

    def get_complete_activity_data(self, activity_id: int) -> Dict[str, Any]:
        """Get complete activity data including photos, comments, map, and description"""
        cache_data = self._load_cache()
        
        # Check if we have complete data in cache
        for activity in cache_data.get("activities", []):
            if activity.get("id") == activity_id:
                # Check if this activity has complete data
                if self._has_complete_data(activity):
                    print(f"✅ Using complete cached data for activity {activity_id}")
                    return activity
                else:
                    print(f"🔄 Activity {activity_id} has incomplete data, fetching details...")
                    break
        
        # Fetch complete data from Strava
        try:
            complete_data = self._fetch_complete_activity_data(activity_id)
            
            # Update cache with complete data
            self._update_activity_in_cache(activity_id, complete_data)
            
            print(f"✅ Fetched complete data for activity {activity_id}")
            return complete_data
            
        except Exception as e:
            print(f"❌ Error fetching complete data for activity {activity_id}: {e}")
            # Return basic data from cache if available
            for activity in cache_data.get("activities", []):
                if activity.get("id") == activity_id:
                    return activity
            return {}

    def _has_complete_data(self, activity: Dict[str, Any]) -> bool:
        """Check if activity has complete data (photos, comments, map, description)"""
        has_description = bool(activity.get("description"))
        has_photos = bool(activity.get("photos") and activity.get("photos").get("primary"))
        has_comments = "comments" in activity
        has_map = bool(activity.get("map") and activity.get("map").get("summary_polyline"))
        
        return has_description and has_photos and has_comments and has_map

    def _fetch_complete_activity_data(self, activity_id: int) -> Dict[str, Any]:
        """Fetch complete activity data from Strava API"""
        access_token = self.token_manager.get_valid_access_token()
        
        import httpx
        import asyncio
        import concurrent.futures
        
        async def fetch_all_data():
            async with httpx.AsyncClient() as client:
                headers = {"Authorization": f"Bearer {access_token}"}
                
                # Fetch basic activity data
                activity_response = await client.get(
                    f"{self.base_url}/activities/{activity_id}",
                    headers=headers
                )
                activity_data = activity_response.json()
                
                # Fetch photos
                photos_response = await client.get(
                    f"{self.base_url}/activities/{activity_id}/photos",
                    headers=headers
                )
                photos_data = photos_response.json() if photos_response.status_code == 200 else []
                
                # Fetch comments
                comments_response = await client.get(
                    f"{self.base_url}/activities/{activity_id}/comments",
                    headers=headers
                )
                comments_data = comments_response.json() if comments_response.status_code == 200 else []
                
                # Fetch streams (GPS data)
                streams_response = await client.get(
                    f"{self.base_url}/activities/{activity_id}/streams",
                    headers=headers,
                    params={"keys": "latlng,altitude,time", "key_by_type": "true"}
                )
                streams_data = streams_response.json() if streams_response.status_code == 200 else {}
                
                return activity_data, photos_data, comments_data, streams_data
        
        # Use ThreadPoolExecutor to avoid asyncio.run() in running event loop
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, fetch_all_data())
            activity_data, photos_data, comments_data, streams_data = future.result()
        
        # Process and combine all data
        complete_data = self._process_activity_data(activity_data)
        complete_data["photos"] = self._process_photos_data(photos_data)
        complete_data["comments"] = self._process_comments_data(comments_data)
        complete_data["map"] = self._process_streams_data(streams_data)
        
        return complete_data

    def _process_activity_data(self, activity_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process basic activity data"""
        return {
            "id": activity_data.get("id"),
            "name": activity_data.get("name", ""),
            "type": activity_data.get("type", ""),
            "distance": activity_data.get("distance", 0),
            "moving_time": activity_data.get("moving_time", 0),
            "elapsed_time": activity_data.get("elapsed_time", 0),
            "total_elevation_gain": activity_data.get("total_elevation_gain", 0),
            "start_date": activity_data.get("start_date", ""),
            "start_date_local": activity_data.get("start_date_local", ""),
            "timezone": activity_data.get("timezone", ""),
            "description": activity_data.get("description", ""),
            "kudos_count": activity_data.get("kudos_count", 0),
            "comment_count": activity_data.get("comment_count", 0),
            "achievement_count": activity_data.get("achievement_count", 0),
            "photo_count": activity_data.get("photo_count", 0),
            "trainer": activity_data.get("trainer", False),
            "commute": activity_data.get("commute", False),
            "manual": activity_data.get("manual", False),
            "private": activity_data.get("private", False),
            "flagged": activity_data.get("flagged", False),
            "gear_id": activity_data.get("gear_id"),
            "start_latlng": activity_data.get("start_latlng", []),
            "end_latlng": activity_data.get("end_latlng", []),
            "map": activity_data.get("map", {}),
            "athlete": activity_data.get("athlete", {}),
            "resource_state": activity_data.get("resource_state", 2)
        }

    def _process_photos_data(self, photos_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Process photos data"""
        if not photos_data:
            return {}
        
        # Find primary photo
        primary_photo = None
        for photo in photos_data:
            if photo.get("default_photo", False):
                primary_photo = photo
                break
        
        if not primary_photo and photos_data:
            primary_photo = photos_data[0]
        
        if primary_photo:
            return {
                "primary": {
                    "id": primary_photo.get("id"),
                    "media_type": primary_photo.get("media_type", 1),
                    "urls": {
                        "600": primary_photo.get("urls", {}).get("600", ""),
                        "1000": primary_photo.get("urls", {}).get("1000", "")
                    }
                },
                "count": len(photos_data)
            }
        
        return {}

    def _process_comments_data(self, comments_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process comments data"""
        formatted_comments = []
        for comment in comments_data:
            formatted_comments.append({
                "id": comment.get("id"),
                "text": comment.get("text", ""),
                "athlete": {
                    "id": comment.get("athlete", {}).get("id"),
                    "firstname": comment.get("athlete", {}).get("firstname", ""),
                    "lastname": comment.get("athlete", {}).get("lastname", ""),
                    "username": comment.get("athlete", {}).get("username", ""),
                },
                "created_at": comment.get("created_at"),
                "activity_id": comment.get("activity_id")
            })
        return formatted_comments

    def _process_streams_data(self, streams_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process GPS streams data"""
        if "latlng" not in streams_data or not streams_data["latlng"]:
            return {}
        
        latlng_data = streams_data["latlng"]["data"]
        altitude_data = streams_data.get("altitude", {}).get("data", [])
        time_data = streams_data.get("time", {}).get("data", [])
        
        gps_points = []
        for i, (lat, lng) in enumerate(latlng_data):
            point = {
                "lat": lat,
                "lng": lng,
                "altitude": altitude_data[i] if i < len(altitude_data) else None,
                "time": time_data[i] if i < len(time_data) else None
            }
            gps_points.append(point)
        
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
            "gps_points": gps_points,
            "bounds": bounds,
            "point_count": len(gps_points)
        }

    def _update_activity_in_cache(self, activity_id: int, complete_data: Dict[str, Any]):
        """Update activity in cache with complete data"""
        cache_data = self._load_cache()
        
        # Find and update the activity
        for i, activity in enumerate(cache_data.get("activities", [])):
            if activity.get("id") == activity_id:
                cache_data["activities"][i] = complete_data
                break
        
        # Save updated cache
        self._save_cache(cache_data)
