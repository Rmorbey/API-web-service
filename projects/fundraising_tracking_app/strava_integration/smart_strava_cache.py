#!/usr/bin/env python3
"""
Minimal Smart Strava Caching Strategy
Contains only essential methods used by the API
"""

import os
import json
import httpx
import time
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dotenv import load_dotenv
from .strava_token_manager import StravaTokenManager
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from ..music_integration.music_integration import MusicIntegration

# Configure enhanced logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('strava_integration.log')
    ]
)
logger = logging.getLogger(__name__)

# Create performance logger
perf_logger = logging.getLogger('performance')
perf_logger.setLevel(logging.INFO)

load_dotenv()

class SmartStravaCache:
    def __init__(self, cache_duration_hours: int = None):
        self.token_manager = StravaTokenManager()
        self.music_integration = MusicIntegration()
        self.base_url = "https://www.strava.com/api/v3"
        self.cache_file = "projects/fundraising_tracking_app/strava_integration/strava_cache.json"
        
        # Allow custom cache duration, default to 6 hours
        self.cache_duration_hours = cache_duration_hours or int(os.getenv("STRAVA_CACHE_HOURS", "6"))
        
        # Filtering criteria
        self.allowed_activity_types = ["Run", "Ride"]  # Only runs and bike rides
        
        # Rate limiting tracking
        self.api_calls_made = 0
        self.api_calls_reset_time = datetime.now()
        self.max_calls_per_15min = 200
        self.max_calls_per_day = 2000
        
        # Performance optimizations
        self._cache_data = None  # In-memory cache
        self._cache_loaded_at = None
        self._cache_ttl = 300  # 5 minutes in-memory cache TTL
        self.start_date = datetime(2025, 5, 22)  # May 22nd, 2025 onwards
        
    def _load_cache(self) -> Dict[str, Any]:
        """Load cache from file with in-memory optimization"""
        now = datetime.now()
        
        # Check if in-memory cache is still valid
        if (self._cache_data is not None and 
            self._cache_loaded_at is not None and 
            (now - self._cache_loaded_at).total_seconds() < self._cache_ttl):
            return self._cache_data
        
        # Load from file
        try:
            with open(self.cache_file, 'r') as f:
                self._cache_data = json.load(f)
                self._cache_loaded_at = now
                return self._cache_data
        except (FileNotFoundError, json.JSONDecodeError):
            self._cache_data = {"timestamp": None, "activities": []}
            self._cache_loaded_at = now
            return self._cache_data
    
    def _save_cache(self, data: Dict[str, Any]):
        """Save cache to file and update in-memory cache"""
        with open(self.cache_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        # Update in-memory cache
        self._cache_data = data
        self._cache_loaded_at = datetime.now()
    
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
    
    def _check_api_limits(self) -> Tuple[bool, str]:
        """Check if we can make API calls without hitting rate limits"""
        now = datetime.now()
        
        # Reset counter if 15 minutes have passed
        if (now - self.api_calls_reset_time).total_seconds() > 900:  # 15 minutes
            self.api_calls_made = 0
            self.api_calls_reset_time = now
        
        # Check 15-minute limit
        if self.api_calls_made >= self.max_calls_per_15min:
            return False, f"Rate limit exceeded: {self.api_calls_made}/{self.max_calls_per_15min} calls in 15 minutes"
        
        # Check daily limit (simplified - would need more sophisticated tracking in production)
        if self.api_calls_made >= self.max_calls_per_day:
            return False, f"Daily rate limit exceeded: {self.api_calls_made}/{self.max_calls_per_day} calls"
        
        return True, "OK"
    
    def _record_api_call(self):
        """Record that an API call was made"""
        self.api_calls_made += 1
        logger.info(f"API call made. Total: {self.api_calls_made}")
    
    def _make_api_call_with_retry(self, url: str, headers: Dict[str, str], max_retries: int = 3) -> httpx.Response:
        """Make an API call with retry logic and error handling"""
        for attempt in range(max_retries):
            try:
                # Check rate limits before making call
                can_call, message = self._check_api_limits()
                if not can_call:
                    raise Exception(f"Rate limit exceeded: {message}")
                
                # Make the API call
                with httpx.Client(timeout=30.0) as client:
                    response = client.get(url, headers=headers)
                    
                    # Record the API call
                    self._record_api_call()
                    
                    # Handle specific HTTP status codes
                    if response.status_code == 200:
                        return response
                    elif response.status_code == 401:
                        logger.warning("Token expired, attempting refresh...")
                        # Token might be expired, try to refresh
                        self.token_manager.get_valid_access_token()
                        if attempt < max_retries - 1:
                            continue
                        raise Exception("Authentication failed after token refresh")
                    elif response.status_code == 429:
                        # Rate limited by Strava
                        retry_after = int(response.headers.get('Retry-After', 60))
                        logger.warning(f"Rate limited by Strava, waiting {retry_after} seconds...")
                        if attempt < max_retries - 1:
                            time.sleep(retry_after)
                            continue
                        raise Exception(f"Rate limited by Strava: {response.text}")
                    elif response.status_code == 404:
                        raise Exception(f"Resource not found: {url}")
                    else:
                        response.raise_for_status()
                        
            except httpx.TimeoutException:
                logger.warning(f"Timeout on attempt {attempt + 1}/{max_retries}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                raise Exception("API call timed out after all retries")
            except httpx.RequestError as e:
                logger.warning(f"Request error on attempt {attempt + 1}/{max_retries}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                raise Exception(f"API request failed: {str(e)}")
        
        raise Exception("API call failed after all retries")
    
    def get_activities_smart(self, limit: int = 200, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        Get activities with smart caching strategy
        Uses cache if valid, otherwise fetches from Strava API
        """
        start_time = time.time()
        cache_data = self._load_cache()
        
        # Use cache if valid and not forcing refresh
        if not force_refresh and self._is_cache_valid(cache_data):
            logger.info(f"Using cached data ({len(cache_data['activities'])} activities)")
            perf_logger.info(f"Cache hit - {time.time() - start_time:.3f}s")
            return cache_data["activities"][:limit]
        
        # Cache is invalid or force refresh - fetch from Strava
        logger.info("Cache expired or invalid, fetching fresh data from Strava...")
        
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
            
            execution_time = time.time() - start_time
            logger.info(f"Cached {len(filtered_activities)} activities (filtered from {len(fresh_activities)})")
            perf_logger.info(f"API fetch complete - {execution_time:.3f}s")
            return filtered_activities[:limit]
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Error fetching from Strava: {e}")
            perf_logger.error(f"API fetch failed - {execution_time:.3f}s")
            
            # Fallback to cached data even if expired
            if cache_data.get("activities"):
                logger.warning("Using stale cached data as fallback")
                return cache_data["activities"][:limit]
            else:
                logger.error("No cached data available, returning empty list")
                return []
    
    def _fetch_from_strava(self, limit: int) -> List[Dict[str, Any]]:
        """Fetch activities from Strava API with enhanced error handling"""
        try:
            access_token = self.token_manager.get_valid_access_token()
            headers = {'Authorization': f'Bearer {access_token}'}
            
            # Use the new retry-enabled API call method
            response = self._make_api_call_with_retry(
                f"{self.base_url}/athlete/activities?per_page={min(limit, 200)}&page=1",
                headers
            )
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Failed to fetch activities from Strava: {str(e)}")
            raise Exception(f"Strava API error: {str(e)}")

    def get_complete_activity_data(self, activity_id: int) -> Dict[str, Any]:
        """Get complete activity data including photos, comments, map, and description"""
        print(f"🔍 DEBUG: get_complete_activity_data called for activity {activity_id}")
        print(f"🔍 DEBUG: Stack trace:")
        import traceback
        traceback.print_stack()
        
        cache_data = self._load_cache()
        
        # ALWAYS use cached data only - never make API calls
        for activity in cache_data.get("activities", []):
            if activity.get("id") == activity_id:
                print(f"✅ Using cached data for activity {activity_id} (6-hour cache strategy)")
                return activity
        
        # Activity not found in cache - return basic data
        print(f"⚠️ Activity {activity_id} not found in cache, returning basic data")
        return {
            "id": activity_id,
            "name": "Unknown Activity",
            "type": "Unknown",
            "distance": 0,
            "moving_time": 0,
            "start_date_local": "2025-01-01T00:00:00Z",
            "description": "",
            "photos": {},
            "comments": [],
            "map": {},
            "music": {}
        }

    def _has_complete_data(self, activity: Dict[str, Any]) -> bool:
        """Check if activity has complete data (photos, comments, map, description)"""
        has_description = bool(activity.get("description"))
        has_photos = bool(activity.get("photos") and activity.get("photos").get("primary"))
        has_comments = "comments" in activity
        has_map = bool(activity.get("map") and activity.get("map").get("polyline"))
        
        return has_description and has_photos and has_comments and has_map

    def _fetch_complete_activity_data(self, activity_id: int) -> Dict[str, Any]:
        """Fetch complete activity data from Strava API with enhanced error handling"""
        print(f"🚨 BLOCKED: _fetch_complete_activity_data called for activity {activity_id}")
        print(f"🚨 BLOCKED: This method is DISABLED with 6-hour cache strategy!")
        print(f"🚨 BLOCKED: Returning cached data instead of making API calls")
        
        # Return cached data instead of making API calls
        cache_data = self._load_cache()
        for activity in cache_data.get("activities", []):
            if activity.get("id") == activity_id:
                print(f"✅ Using cached data for activity {activity_id} (6-hour cache strategy)")
                return activity
        
        # Activity not found in cache - return basic data
        print(f"⚠️ Activity {activity_id} not found in cache, returning basic data")
        return {
            "id": activity_id,
            "name": "Unknown Activity",
            "type": "Unknown",
            "distance": 0,
            "moving_time": 0,
            "start_date_local": "2025-01-01T00:00:00Z",
            "description": "",
            "photos": {},
            "comments": [],
            "map": {},
            "music": {}
        }

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
            # Get available URLs from Strava API
            urls = primary_photo.get("urls", {})
            
            # Map available sizes to our expected format
            photo_urls = {}
            if "600" in urls and urls["600"]:
                photo_urls["600"] = urls["600"]
            elif "1000" in urls and urls["1000"]:
                photo_urls["600"] = urls["1000"]  # Use 1000 as 600 fallback
            elif "1800" in urls and urls["1800"]:
                photo_urls["600"] = urls["1800"]  # Use 1800 as 600 fallback
                photo_urls["1000"] = urls["1800"]  # Use 1800 as 1000 fallback
            elif "5000" in urls and urls["5000"]:
                photo_urls["600"] = urls["5000"]  # Use 5000 as 600 fallback
                photo_urls["1000"] = urls["5000"]  # Use 5000 as 1000 fallback
            
            # If no URLs available, use placeholder
            if not photo_urls:
                placeholder = primary_photo.get("placeholder_image", {})
                if placeholder.get("light_url"):
                    photo_urls["600"] = placeholder["light_url"]
                    photo_urls["1000"] = placeholder["light_url"]
            
            return {
                "primary": {
                    "id": primary_photo.get("unique_id"),  # Use unique_id instead of id
                    "media_type": primary_photo.get("type", 1),  # Use type instead of media_type
                    "urls": photo_urls,
                    "status": primary_photo.get("status", 0),  # Add status info
                    "placeholder": primary_photo.get("placeholder_image", {})  # Add placeholder info
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

    def _decode_polyline(self, polyline_str: str) -> List[List[float]]:
        """Decode Google polyline string to lat/lng coordinates"""
        if not polyline_str:
            return []
        
        try:
            # Simple polyline decoder
            index = 0
            lat = 0
            lng = 0
            coordinates = []
            
            while index < len(polyline_str):
                # Decode latitude
                shift = 0
                result = 0
                while True:
                    b = ord(polyline_str[index]) - 63
                    index += 1
                    result |= (b & 0x1f) << shift
                    shift += 5
                    if b < 0x20:
                        break
                lat += ~(result >> 1) if result & 1 else result >> 1
                
                # Decode longitude
                shift = 0
                result = 0
                while True:
                    b = ord(polyline_str[index]) - 63
                    index += 1
                    result |= (b & 0x1f) << shift
                    shift += 5
                    if b < 0x20:
                        break
                lng += ~(result >> 1) if result & 1 else result >> 1
                
                coordinates.append([lat / 1e5, lng / 1e5])
            
            return coordinates
        except Exception as e:
            logger.warning(f"Failed to decode polyline: {e}")
            return []

    def _process_map_data(self, activity_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process map data from basic activity response (polyline only)"""
        map_data = activity_data.get("map", {})
        
        # Extract polyline and bounds from basic activity data
        polyline = map_data.get("polyline")
        summary_polyline = map_data.get("summary_polyline")
        bounds = map_data.get("bounds", {})
        
        # Decode polyline to get coordinates
        coordinates = []
        if polyline:
            coordinates = self._decode_polyline(polyline)
        
        # Calculate bounds from coordinates if not provided
        if not bounds and coordinates:
            lats = [coord[0] for coord in coordinates]
            lngs = [coord[1] for coord in coordinates]
            bounds = {
                "south": min(lats),
                "west": min(lngs),
                "north": max(lats),
                "east": max(lngs)
            }
        
        # Get start and end coordinates
        start_latlng = coordinates[0] if coordinates else None
        end_latlng = coordinates[-1] if coordinates else None
        
        return {
            "polyline": polyline,
            "summary_polyline": summary_polyline,
            "bounds": bounds,
            "coordinates": coordinates,
            "start_latlng": start_latlng,
            "end_latlng": end_latlng
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
    
    def _detect_music(self, description: str) -> Dict[str, Any]:
        """Detect music information from activity description"""
        if not description:
            return {}
        
        import re
        
        # Music detection patterns - fixed to properly capture full text
        # Pattern: "Album: Gulag Orkestar by Beirut" -> Album: "Gulag Orkestar", Artist: "Beirut"
        album_pattern = r"Album:\s*([^,\n]+?)\s+by\s+([^,\n]+)"
        # Pattern: "Russell Radio: Allstar by smash mouth" -> Track: "Allstar", Artist: "smash mouth"  
        russell_radio_pattern = r"Russell Radio:\s*([^,\n]+?)\s+by\s+([^,\n]+)"
        # Legacy patterns for other formats
        track_pattern = r"Track:\s*([^,\n]+?)(?:\s+by\s+([^,\n]+))?"
        playlist_pattern = r"Playlist:\s*([^,\n]+)"
        
        music_data = {}
        detected = {}
        
        # Check for track
        track_match = re.search(track_pattern, description, re.IGNORECASE)
        if track_match:
            detected = {
                "type": "track",
                "title": track_match.group(1).strip(),
                "artist": track_match.group(2).strip() if track_match.group(2) else None,
                "source": "description"
            }
            music_data["track"] = {
                "name": track_match.group(1).strip(),
                "artist": track_match.group(2).strip() if track_match.group(2) else None
            }
        
        # Check for album
        album_match = re.search(album_pattern, description, re.IGNORECASE)
        if album_match:
            detected = {
                "type": "album",
                "title": album_match.group(1).strip(),
                "artist": album_match.group(2).strip() if album_match.group(2) else None,
                "source": "description"
            }
            music_data["album"] = {
                "name": album_match.group(1).strip(),
                "artist": album_match.group(2).strip() if album_match.group(2) else None
            }
        
        # Check for playlist
        playlist_match = re.search(playlist_pattern, description, re.IGNORECASE)
        if playlist_match:
            detected = {
                "type": "playlist",
                "title": playlist_match.group(1).strip(),
                "artist": "Various Artists",
                "source": "description"
            }
            music_data["playlist"] = {
                "name": playlist_match.group(1).strip()
            }
        
        # Check for Russell Radio format
        russell_radio_match = re.search(russell_radio_pattern, description, re.IGNORECASE)
        if russell_radio_match:
            detected = {
                "type": "track",
                "title": russell_radio_match.group(1).strip(),
                "artist": russell_radio_match.group(2).strip() if russell_radio_match.group(2) else None,
                "source": "russell_radio"
            }
            music_data["track"] = {
                "name": russell_radio_match.group(1).strip(),
                "artist": russell_radio_match.group(2).strip() if russell_radio_match.group(2) else None
            }
        
        # Add detected field for frontend compatibility
        if detected:
            music_data["detected"] = detected
        
        return music_data
