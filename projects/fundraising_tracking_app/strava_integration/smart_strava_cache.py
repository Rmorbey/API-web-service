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
import shutil
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dotenv import load_dotenv
from .strava_token_manager import StravaTokenManager
import os

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

# Performance logging is handled by the main logger

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
        
        # Automated refresh system
        self._refresh_thread = None
        self._batch_thread = None
        self._refresh_running = False
        self._batch_running = False
        self._last_refresh = None
        self._batch_queue = []
        
        # Start the automated refresh system
        self._start_automated_refresh()
        
    def _load_cache(self) -> Dict[str, Any]:
        """Load cache from file with in-memory optimization and corruption detection"""
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
                
                # Validate cache integrity
                if self._validate_cache_integrity(self._cache_data):
                    return self._cache_data
                else:
                    logger.warning("Cache integrity check failed, attempting to restore from backup...")
                    if self._restore_from_backup():
                        return self._cache_data
                    else:
                        logger.error("All backups failed, triggering immediate refresh to rebuild cache...")
                        self._cache_data = {"timestamp": None, "activities": []}
                        # Trigger immediate refresh to rebuild cache
                        self._trigger_emergency_refresh()
                        return self._cache_data
                        
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.warning(f"Cache file error: {e}, attempting to restore from backup...")
            if self._restore_from_backup():
                return self._cache_data
            else:
                logger.error("All backups failed, triggering immediate refresh to rebuild cache...")
                self._cache_data = {"timestamp": None, "activities": []}
                self._cache_loaded_at = now
                # Trigger immediate refresh to rebuild cache
                self._trigger_emergency_refresh()
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
            logger.info(f"Cache hit - {time.time() - start_time:.3f}s")
            return cache_data["activities"][:limit]
        
        # Cache is invalid or force refresh - SMART MERGE with existing data
        logger.info("Cache expired or invalid, performing smart refresh...")
        
        try:
            # Fetch fresh basic data from Strava
            fresh_activities = self._fetch_from_strava(limit * 2)  # Fetch more to account for filtering
            
            # Filter activities
            filtered_activities = self._filter_activities(fresh_activities)
            
            # SMART MERGE: Preserve existing rich data, update only basic fields
            existing_activities = cache_data.get("activities", [])
            merged_activities = self._smart_merge_activities(existing_activities, filtered_activities)
            
            # Update cache with merged data
            cache_data = {
                "timestamp": datetime.now().isoformat(),
                "activities": merged_activities,
                "total_fetched": len(fresh_activities),
                "total_filtered": len(filtered_activities),
                "smart_merge": True  # Flag to indicate smart merge was used
            }
            
            self._save_cache(cache_data)
            
            execution_time = time.time() - start_time
            logger.info(f"Smart merged {len(merged_activities)} activities (preserved rich data)")
            logger.info(f"Smart merge complete - {execution_time:.3f}s")
            return merged_activities[:limit]
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Error fetching from Strava: {e}")
            logger.error(f"API fetch failed - {execution_time:.3f}s")
            
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


    def _has_complete_data(self, activity: Dict[str, Any]) -> bool:
        """Check if activity has complete data (photos, comments, map, description)"""
        has_description = bool(activity.get("description"))
        has_photos = bool(activity.get("photos") and activity.get("photos").get("primary"))
        has_comments = "comments" in activity
        has_map = bool(activity.get("map") and activity.get("map").get("polyline"))
        
        return has_description and has_photos and has_comments and has_map

    def _fetch_complete_activity_data(self, activity_id: int) -> Dict[str, Any]:
        """Fetch complete activity data from Strava API with enhanced error handling - OPTIMIZED FOR FRONTEND"""
        print(f"🔄 ENABLED: Fetching complete data for activity {activity_id}")
        print(f"🔄 ENABLED: Making API calls to get descriptions, comments, photos, music")
        
        try:
            # Fetch complete activity data from Strava API
            activity_url = f"{self.base_url}/activities/{activity_id}"
            headers = {"Authorization": f"Bearer {self.token_manager.get_valid_access_token()}"}
            
            response = self._make_api_call_with_retry(activity_url, headers)
            activity_data = response.json()
            
            # Fetch photos and comments
            photos_data = self._fetch_activity_photos(activity_id)
            comments_data = self._fetch_activity_comments(activity_id)
            
            # OPTIMIZED: Only cache essential fields needed by frontend
            # Based on frontend analysis, we only need these fields:
            processed_activity = {
                # Core activity data (required by frontend)
                "id": activity_data.get("id"),
                "name": activity_data.get("name", ""),
                "type": activity_data.get("type", ""),
                "distance": activity_data.get("distance", 0),
                "moving_time": activity_data.get("moving_time", 0),
                "start_date_local": activity_data.get("start_date_local", ""),
                "description": activity_data.get("description", ""),
                
                # Rich data (photos, comments, music, map)
                "photos": photos_data,
                "comments": comments_data,
                "map": self._process_map_data(activity_data),
                "music": self._detect_music(activity_data.get("description", ""))
            }
            
            print(f"✅ Fetched complete data for activity {activity_id} (OPTIMIZED - essential fields only)")
            return processed_activity
            
        except Exception as e:
            print(f"❌ Error fetching complete data for activity {activity_id}: {e}")
            # Return minimal data on error
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
        """Process map data - OPTIMIZED: Only essential fields for frontend"""
        map_data = activity_data.get("map", {})
        
        # Extract only essential map data
        polyline = map_data.get("polyline")
        bounds = map_data.get("bounds", {})
        
        # Calculate bounds from polyline if not provided
        if not bounds and polyline:
            coordinates = self._decode_polyline(polyline)
            if coordinates:
                lats = [coord[0] for coord in coordinates]
                lngs = [coord[1] for coord in coordinates]
            bounds = {
                    "south": min(lats),
                    "west": min(lngs),
                "north": max(lats),
                    "east": max(lngs)
            }
        
        # OPTIMIZED: Only return essential fields (frontend only needs polyline + bounds)
        return {
            "polyline": polyline,
            "bounds": bounds
        }

    def _smart_merge_activities(self, existing_activities: List[Dict[str, Any]], fresh_activities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Smart merge: Preserve ALL existing data, update only basic fields from fresh data
        FIXED: Never overwrite existing activities with fresh data to prevent data loss
        """
        # Create lookup maps
        existing_by_id = {activity.get("id"): activity for activity in existing_activities}
        fresh_by_id = {activity.get("id"): activity for activity in fresh_activities}
        
        merged_activities = []
        
        # Process fresh activities (maintains order from Strava)
        for fresh_activity in fresh_activities:
            activity_id = fresh_activity.get("id")
            existing_activity = existing_by_id.get(activity_id)
            
            if existing_activity:
                # PRESERVE: Always keep existing data, update only basic fields
                merged_activity = existing_activity.copy()
                
                # Update only basic fields that might have changed
                basic_fields = ["name", "type", "distance", "moving_time", "elapsed_time", 
                              "start_date", "start_date_local", "timezone", "total_elevation_gain"]
                
                for field in basic_fields:
                    if field in fresh_activity:
                        merged_activity[field] = fresh_activity[field]
                
                logger.info(f"Preserved existing data for activity {activity_id}: {fresh_activity.get('name', 'Unknown')}")
                
            else:
                # NEW ACTIVITY: Use fresh data (will be processed later if needed)
                merged_activity = fresh_activity
                logger.info(f"New activity {activity_id}: {fresh_activity.get('name', 'Unknown')}")
            
            merged_activities.append(merged_activity)
        
        # Add any existing activities that weren't in fresh data (shouldn't happen with Strava)
        for activity_id, existing_activity in existing_by_id.items():
            if activity_id not in fresh_by_id:
                merged_activities.append(existing_activity)
                logger.info(f"Preserved existing activity not in fresh data: {activity_id}")
        
        return merged_activities

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
            
            # Generate Deezer widget HTML
            music_data["widget_html"] = self._generate_deezer_widget(detected)
        
        return music_data
    
    def _search_deezer_for_id(self, title: str, artist: str, music_type: str) -> tuple[str, str]:
        """
        Search Deezer API for specific album/track ID
        Returns: (id_type, deezer_id) or (None, None) if not found
        """
        try:
            # Search Deezer API for the specific type (album or track)
            search_query = f"{title} {artist}".replace(" ", "%20")
            
            # Use different search endpoints based on type
            if music_type == "album":
                search_url = f"https://api.deezer.com/search/album?q={search_query}&limit=5"
            elif music_type == "track":
                search_url = f"https://api.deezer.com/search/track?q={search_query}&limit=5"
            else:
                # Default to general search
                search_url = f"https://api.deezer.com/search?q={search_query}&limit=5"
            
            response = self._make_api_call_with_retry(search_url, {})
            data = response.json()
            
            if not data.get("data"):
                print(f"❌ No Deezer results for: {artist} - {title} ({music_type})")
                return None, None
            
            # Look for the best match
            for item in data["data"]:
                item_title = item.get("title", "").lower()
                item_artist = item.get("artist", {}).get("name", "").lower()
                
                # Check if this is a good match
                if (title.lower() in item_title or item_title in title.lower()) and \
                   (artist.lower() in item_artist or item_artist in artist.lower()):
                    
                    # Return the specific type we're looking for
                    if music_type == "album" and item.get("type") == "album":
                        return "album", str(item["id"])
                    elif music_type == "track" and item.get("type") == "track":
                        return "track", str(item["id"])
                    elif music_type == "playlist" and item.get("type") == "playlist":
                        return "playlist", str(item["id"])
            
            print(f"❌ No matching {music_type} found for: {artist} - {title}")
            return None, None
            
        except Exception as e:
            print(f"❌ Error searching Deezer for {artist} - {title}: {e}")
            return None, None

    def _generate_deezer_widget(self, detected: Dict[str, Any]) -> str:
        """Generate Deezer widget HTML for detected music"""
        if not detected:
            return ""
        
        music_type = detected.get("type", "")
        title = detected.get("title", "")
        artist = detected.get("artist", "")
        
        if not title or not artist:
            return ""
        
        # Search Deezer for the specific album/track ID
        id_type, deezer_id = self._search_deezer_for_id(title, artist, music_type)
        
        if id_type and deezer_id:
            # Use the specific album/track ID for better experience
            print(f"✅ Found Deezer {id_type} ID {deezer_id} for: {artist} - {title}")
            return f'<iframe title="deezer-widget" src="https://widget.deezer.com/widget/auto/{id_type}/{deezer_id}" width="100%" height="300" frameborder="0" allowtransparency="true" allow="encrypted-media; clipboard-write"></iframe>'
        else:
            # Fall back to search format if no specific ID found
            print(f"⚠️ Falling back to search for: {artist} - {title}")
            search_query = f"{title}%20by%20{artist}".replace(" ", "%20")
            return f'<iframe title="deezer-widget" src="https://widget.deezer.com/widget/auto/search/{search_query}" width="100%" height="300" frameborder="0" allowtransparency="true" allow="encrypted-media; clipboard-write"></iframe>'
    
    def _fetch_activity_photos(self, activity_id: int) -> Dict[str, Any]:
        """Fetch photos for a specific activity - OPTIMIZED: Only essential fields"""
        try:
            # Add size parameter to get actual photos instead of placeholders
            photos_url = f"{self.base_url}/activities/{activity_id}/photos?size=5000"
            headers = {"Authorization": f"Bearer {self.token_manager.get_valid_access_token()}"}
            
            response = self._make_api_call_with_retry(photos_url, headers)
            photos_data = response.json()
            
            # Process photos data - OPTIMIZED: Only essential fields for frontend
            if photos_data and len(photos_data) > 0:
                primary_photo = photos_data[0]  # First photo is usually primary
                urls = primary_photo.get("urls", {})
                placeholder = primary_photo.get("placeholder_image", {})
                status = primary_photo.get("status", 0)
                
                # Handle different photo statuses and sizes
                if status == 3 and not urls.get("5000"):  # Still processing, no real photo yet
                    # Use placeholder image
                    photo_url = placeholder.get("light_url", "")
                    photo_urls = {
                        "600": photo_url,
                        "1000": photo_url
                    }
                else:
                    # Photo is ready (even if status=3, we have the 5000px version)
                    # Use 5000px as base and create smaller sizes
                    base_url = urls.get("5000", urls.get("1800", urls.get("1000", urls.get("600", ""))))
                    photo_url = base_url
                    photo_urls = {
                        "600": base_url,  # Use same URL for all sizes (5000px will scale down)
                        "1000": base_url
                    }
                
                return {
                    "primary": {
                        "unique_id": primary_photo.get("unique_id"),
                        "type": primary_photo.get("type"),
                        "url": photo_url,  # Single URL for compatibility
                        "urls": photo_urls,  # Multiple sizes for frontend
                        "status": status,
                        "is_placeholder": status == 3 and not urls.get("5000")
                    },
                    "count": len(photos_data)
                }
            else:
                return {}
                
        except Exception as e:
            print(f"❌ Error fetching photos for activity {activity_id}: {e}")
            return {}
    
    def _fetch_activity_comments(self, activity_id: int) -> List[Dict[str, Any]]:
        """Fetch comments for a specific activity - OPTIMIZED: Only essential fields"""
        try:
            comments_url = f"{self.base_url}/activities/{activity_id}/comments"
            headers = {"Authorization": f"Bearer {self.token_manager.get_valid_access_token()}"}
            
            response = self._make_api_call_with_retry(comments_url, headers)
            comments_data = response.json()
            
            # Process comments data - OPTIMIZED: Only essential fields for frontend
            processed_comments = []
            for comment in comments_data:
                processed_comments.append({
                    "id": comment.get("id"),
                    "text": comment.get("text"),
                    "created_at": comment.get("created_at"),
                    "athlete": {
                        "firstname": comment.get("athlete", {}).get("firstname"),
                        "lastname": comment.get("athlete", {}).get("lastname")
                    }
                })
            
            return processed_comments
                
        except Exception as e:
            print(f"❌ Error fetching comments for activity {activity_id}: {e}")
            return []
    
    def _start_automated_refresh(self):
        """Start the automated refresh system with 6-hour intervals"""
        if self._refresh_thread and self._refresh_thread.is_alive():
            return
        
        self._refresh_thread = threading.Thread(target=self._automated_refresh_loop, daemon=True)
        self._refresh_thread.start()
        logger.info("🔄 Automated refresh system started (6-hour intervals)")
    
    def _automated_refresh_loop(self):
        """Main loop for automated refresh every 6 hours"""
        while True:
            try:
                now = datetime.now()
                
                # Check if it's time for a refresh (00:00, 06:00, 12:00, 18:00)
                current_hour = now.hour
                if current_hour in [0, 6, 12, 18] and (self._last_refresh is None or 
                    (now - self._last_refresh).total_seconds() > 3600):  # At least 1 hour since last refresh
                    
                    logger.info(f"🔄 Starting scheduled refresh at {now.strftime('%H:%M')}")
                    self._perform_scheduled_refresh()
                    self._last_refresh = now
                
                # Sleep for 1 hour and check again
                time.sleep(3600)
                
            except Exception as e:
                logger.error(f"❌ Error in automated refresh loop: {e}")
                time.sleep(300)  # Wait 5 minutes before retrying
    
    def _perform_scheduled_refresh(self):
        """Perform a scheduled refresh with backup and batch processing"""
        try:
            # Create backup before refresh
            self._create_backup()
            
            # Start batch processing
            self._start_batch_processing()
            
        except Exception as e:
            logger.error(f"❌ Scheduled refresh failed: {e}")
    
    def _create_backup(self):
        """Create a backup of the current cache before refresh - keeps only 1 backup"""
        try:
            # Clean up old backups first
            self._cleanup_old_backups()
            
            # Create new backup in backups folder
            backup_dir = os.path.join(os.path.dirname(self.cache_file), "backups")
            os.makedirs(backup_dir, exist_ok=True)
            backup_filename = f"strava_cache_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            backup_file = os.path.join(backup_dir, backup_filename)
            shutil.copy2(self.cache_file, backup_file)
            logger.info(f"✅ Cache backup created: {backup_file}")
        except Exception as e:
            logger.error(f"❌ Failed to create backup: {e}")
    
    def _cleanup_old_backups(self):
        """Remove old backup files, keeping only the most recent one"""
        try:
            import glob
            
            # Find all backup files in backups folder
            backup_dir = os.path.join(os.path.dirname(self.cache_file), "backups")
            backup_pattern = os.path.join(backup_dir, "strava_cache_backup_*.json")
            backup_files = glob.glob(backup_pattern)
            
            if len(backup_files) > 1:
                # Sort by modification time (newest first)
                backup_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
                
                # Keep the newest, delete the rest
                for old_backup in backup_files[1:]:
                    try:
                        os.remove(old_backup)
                        logger.info(f"🗑️ Removed old backup: {os.path.basename(old_backup)}")
                    except Exception as e:
                        logger.warning(f"⚠️ Could not remove old backup {old_backup}: {e}")
                
                logger.info(f"🧹 Cleaned up {len(backup_files) - 1} old backup files")
            
        except Exception as e:
            logger.warning(f"⚠️ Error cleaning up old backups: {e}")
    
    def _start_batch_processing(self):
        """Start batch processing of activities (20 every 15 minutes)"""
        if self._batch_thread and self._batch_thread.is_alive():
            return
        
        self._batch_thread = threading.Thread(target=self._batch_processing_loop, daemon=True)
        self._batch_thread.start()
        logger.info("🔄 Batch processing started (20 activities every 15 minutes)")
    
    def _batch_processing_loop(self):
        """Process activities in batches of 20 every 15 minutes"""
        try:
            # Get all activities that need processing
            activities_to_process = self._get_activities_needing_update()
            
            if not activities_to_process:
                logger.info("✅ No activities need updating")
                return
            
            # Process in batches of 20
            batch_size = 20
            for i in range(0, len(activities_to_process), batch_size):
                batch = activities_to_process[i:i + batch_size]
                
                logger.info(f"🔄 Processing batch {i//batch_size + 1}: {len(batch)} activities")
                
                # Process the batch
                self._process_activity_batch(batch)
                
                # Wait 15 minutes before next batch (except for last batch)
                if i + batch_size < len(activities_to_process):
                    logger.info("⏳ Waiting 15 minutes before next batch...")
                    time.sleep(900)  # 15 minutes
            
            logger.info("✅ Batch processing complete")
            
        except Exception as e:
            logger.error(f"❌ Batch processing failed: {e}")
    
    def _get_activities_needing_update(self) -> List[Dict[str, Any]]:
        """Get activities that need updating (not older than 3 weeks)"""
        try:
            cache_data = self._load_cache()
            activities = cache_data.get('activities', [])
            
            # Filter activities not older than 3 weeks
            three_weeks_ago = datetime.now() - timedelta(weeks=3)
            activities_to_update = []
            
            for activity in activities:
                start_date_str = activity.get('start_date_local', '')
                if start_date_str:
                    try:
                        start_date = datetime.fromisoformat(start_date_str.replace('Z', '+00:00'))
                        if start_date >= three_weeks_ago:
                            activities_to_update.append(activity)
                    except:
                        # If date parsing fails, include the activity to be safe
                        activities_to_update.append(activity)
            
            logger.info(f"📊 Found {len(activities_to_update)} activities needing update (last 3 weeks)")
            return activities_to_update
            
        except Exception as e:
            logger.error(f"❌ Error getting activities for update: {e}")
            return []
    
    def _process_activity_batch(self, batch: List[Dict[str, Any]]):
        """Process a batch of activities to update their data - FIXED to fetch complete data"""
        try:
            for activity in batch:
                activity_id = activity.get('id')
                if activity_id:
                    # FIXED: Check if activity needs complete data, then fetch it
                    if not self._has_complete_data(activity):
                        logger.info(f"🔄 Fetching complete data for activity {activity_id}: {activity.get('name', 'Unknown')}")
                        try:
                            # Fetch complete data from Strava API
                            complete_data = self._fetch_complete_activity_data(activity_id)
                            # Update the activity in cache with complete data
                            self._update_activity_in_cache(activity_id, complete_data)
                            logger.info(f"✅ Updated activity {activity_id} with complete data")
                        except Exception as e:
                            logger.warning(f"⚠️ Failed to fetch complete data for activity {activity_id}: {e}")
                    else:
                        logger.info(f"✅ Activity {activity_id} already has complete data, skipping")
                    
                    time.sleep(1)  # Small delay to respect API limits
                    
        except Exception as e:
            logger.error(f"❌ Error processing activity batch: {e}")
    
    def force_refresh_now(self):
        """Force an immediate refresh (for manual trigger) - FIXED to actually fetch fresh data"""
        try:
            logger.info("🔄 Manual refresh triggered - fetching fresh data from Strava")
            self._create_backup()
            
            # FIXED: Actually fetch fresh data from Strava API instead of just processing existing cache
            logger.info("📡 Fetching fresh activities from Strava API...")
            fresh_activities = self._fetch_from_strava(200)  # Fetch up to 200 activities
            filtered_activities = self._filter_activities(fresh_activities)
            
            logger.info(f"✅ Fetched {len(fresh_activities)} activities, {len(filtered_activities)} after filtering")
            
            # Load existing cache for smart merge
            cache_data = self._load_cache()
            existing_activities = cache_data.get("activities", [])
            
            # Smart merge: preserve rich data, update basic fields
            merged_activities = self._smart_merge_activities(existing_activities, filtered_activities)
            
            # Update cache with merged data
            updated_cache = {
                "timestamp": datetime.now().isoformat(),
                "activities": merged_activities,
                "total_fetched": len(fresh_activities),
                "total_filtered": len(filtered_activities),
                "manual_refresh": True
            }
            
            self._save_cache(updated_cache)
            logger.info(f"✅ Manual refresh complete: {len(merged_activities)} activities in cache")
            
            # Now start batch processing for activities that need complete data
            self._start_batch_processing()
            return True
            
        except Exception as e:
            logger.error(f"❌ Manual refresh failed: {e}")
            return False
    
    def cleanup_backups(self):
        """Manually clean up old backup files"""
        try:
            self._cleanup_old_backups()
            return True
        except Exception as e:
            logger.error(f"❌ Backup cleanup failed: {e}")
            return False
    
    def _validate_cache_integrity(self, cache_data: Dict[str, Any]) -> bool:
        """Validate cache integrity - check for data loss indicators"""
        try:
            activities = cache_data.get("activities", [])
            if not activities:
                logger.warning("Cache has no activities")
                return False
            
            # Check for significant data loss
            polyline_count = sum(1 for activity in activities if activity.get("map", {}).get("polyline"))
            total_activities = len(activities)
            
            # If less than 50% of activities have polyline data, consider it corrupted
            if polyline_count < total_activities * 0.5:
                logger.warning(f"Cache integrity check failed: Only {polyline_count}/{total_activities} activities have polyline data")
                return False
            
            # Check for recent activities (should have more data)
            recent_activities = [a for a in activities if a.get("start_date_local", "").startswith("2025-09")]
            if recent_activities:
                recent_polyline_count = sum(1 for activity in recent_activities if activity.get("map", {}).get("polyline"))
                if recent_polyline_count < len(recent_activities) * 0.8:
                    logger.warning(f"Cache integrity check failed: Recent activities missing polyline data ({recent_polyline_count}/{len(recent_activities)})")
                    return False
            
            logger.info(f"Cache integrity check passed: {polyline_count}/{total_activities} activities have polyline data")
            return True
            
        except Exception as e:
            logger.error(f"Cache integrity check error: {e}")
            return False
    
    def _restore_from_backup(self) -> bool:
        """Restore cache from the most recent backup"""
        try:
            import glob
            
            # Find all backup files in backups folder
            backup_dir = os.path.join(os.path.dirname(self.cache_file), "backups")
            backup_pattern = os.path.join(backup_dir, "strava_cache_backup_*.json")
            backup_files = glob.glob(backup_pattern)
            
            if not backup_files:
                logger.error("No backup files found")
                return False
            
            # Sort by modification time (newest first)
            backup_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
            
            # Try to restore from the most recent backup
            for backup_file in backup_files:
                try:
                    with open(backup_file, 'r') as f:
                        backup_data = json.load(f)
                    
                    # Validate backup integrity
                    if self._validate_cache_integrity(backup_data):
                        # Restore the backup
                        shutil.copy2(backup_file, self.cache_file)
                        self._cache_data = backup_data
                        self._cache_loaded_at = datetime.now()
                        logger.info(f"Successfully restored cache from backup: {os.path.basename(backup_file)}")
                        return True
                    else:
                        logger.warning(f"Backup {os.path.basename(backup_file)} also appears corrupted, trying next...")
                        continue
                        
                except Exception as e:
                    logger.warning(f"Failed to restore from {os.path.basename(backup_file)}: {e}")
                    continue
            
            logger.error("All backup files are corrupted or invalid")
            return False
            
        except Exception as e:
            logger.error(f"Failed to restore from backup: {e}")
            return False
    
    def _trigger_emergency_refresh(self):
        """Trigger an immediate refresh when all data is lost"""
        try:
            logger.info("🚨 EMERGENCY REFRESH: All data lost, triggering immediate refresh...")
            
            # Create a backup of the empty cache before refresh
            self._create_backup()
            
            # Start emergency refresh in a separate thread to avoid blocking
            import threading
            emergency_thread = threading.Thread(target=self._perform_emergency_refresh, daemon=True)
            emergency_thread.start()
            
            logger.info("🚨 Emergency refresh started in background thread")
            
        except Exception as e:
            logger.error(f"Failed to trigger emergency refresh: {e}")
    
    def _perform_emergency_refresh(self):
        """Perform the actual emergency refresh"""
        try:
            logger.info("🔄 Performing emergency refresh...")
            
            # Fetch fresh data from Strava
            fresh_activities = self._fetch_from_strava(200)
            filtered_activities = self._filter_activities(fresh_activities)
            
            logger.info(f"✅ Emergency refresh: Fetched {len(fresh_activities)} activities, {len(filtered_activities)} after filtering")
            
            # Create new cache with fresh data
            emergency_cache = {
                "timestamp": datetime.now().isoformat(),
                "activities": filtered_activities,
                "total_fetched": len(fresh_activities),
                "total_filtered": len(filtered_activities),
                "emergency_refresh": True
            }
            
            # Save the emergency cache
            self._save_cache(emergency_cache)
            
            # Update in-memory cache
            self._cache_data = emergency_cache
            self._cache_loaded_at = datetime.now()
            
            logger.info(f"✅ Emergency refresh complete: {len(filtered_activities)} activities restored")
            
            # Start batch processing for complete data
            self._start_batch_processing()
            
        except Exception as e:
            logger.error(f"Emergency refresh failed: {e}")
            # If emergency refresh fails, at least we have an empty cache
            logger.warning("System will continue with empty cache until next scheduled refresh")
