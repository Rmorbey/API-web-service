#!/usr/bin/env python3
"""
Optimized Smart Strava Caching Strategy
Only stores essential data needed by the frontend
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
from music_integration.music_integration import MusicIntegration

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

class OptimizedSmartStravaCache:
    def __init__(self, cache_duration_hours: int = None):
        self.token_manager = StravaTokenManager()
        self.music_integration = MusicIntegration()
        self.base_url = "https://www.strava.com/api/v3"
        self.cache_file = "projects/fundraising_tracking_app/strava_integration/strava_cache.json"
        
        # Allow custom cache duration, default to 6 hours
        self.cache_duration_hours = cache_duration_hours or int(os.getenv("STRAVA_CACHE_HOURS", "6"))
        
        # Filtering criteria
        self.allowed_activity_types = ["Run", "Ride"]  # Only runs and bike rides
        
        # API rate limiting
        self.api_calls_made = 0
        self.api_calls_reset_time = time.time() + 900  # 15 minutes
        self.max_calls_per_15min = 200
        self.max_calls_per_day = 2000
        
        # In-memory cache for faster access
        self._cache_data = None
        self._cache_loaded_at = None
        self._cache_ttl = 300  # 5 minutes in-memory cache

    def _check_api_limits(self) -> bool:
        """Check if we can make API calls without hitting rate limits"""
        current_time = time.time()
        
        # Reset counter if 15 minutes have passed
        if current_time >= self.api_calls_reset_time:
            self.api_calls_made = 0
            self.api_calls_reset_time = current_time + 900
        
        # Check 15-minute limit
        if self.api_calls_made >= self.max_calls_per_15min:
            logger.warning(f"Rate limit reached: {self.api_calls_made}/{self.max_calls_per_15min} calls in 15 minutes")
            return False
        
        return True

    def _record_api_call(self):
        """Record that an API call was made"""
        self.api_calls_made += 1

    def _make_api_call_with_retry(self, url: str, headers: Dict[str, str], max_retries: int = 3) -> httpx.Response:
        """Make API call with retry logic and rate limiting"""
        if not self._check_api_limits():
            raise Exception("API rate limit reached")
        
        for attempt in range(max_retries):
            try:
                with httpx.Client(timeout=30.0) as client:
                    response = client.get(url, headers=headers)
                    
                    if response.status_code == 200:
                        self._record_api_call()
                        return response
                    elif response.status_code == 401:
                        logger.warning("Access token expired, refreshing...")
                        self.token_manager.refresh_access_token()
                        headers["Authorization"] = f"Bearer {self.token_manager.get_valid_access_token()}"
                        continue
                    elif response.status_code == 429:
                        wait_time = 2 ** attempt
                        logger.warning(f"Rate limited, waiting {wait_time} seconds...")
                        time.sleep(wait_time)
                        continue
                    elif response.status_code == 404:
                        logger.warning(f"Resource not found: {url}")
                        raise Exception(f"Resource not found: {url}")
                    else:
                        logger.error(f"API call failed: {response.status_code} - {response.text}")
                        if attempt == max_retries - 1:
                            raise Exception(f"API call failed after {max_retries} attempts: {response.status_code}")
                        time.sleep(2 ** attempt)
                        
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                logger.warning(f"API call attempt {attempt + 1} failed: {e}")
                time.sleep(2 ** attempt)
        
        raise Exception(f"API call failed after {max_retries} attempts")

    def _extract_essential_data(self, activity: Dict[str, Any]) -> Dict[str, Any]:
        """Extract only essential data needed by the frontend"""
        essential_fields = {
            'id': activity.get('id'),
            'name': activity.get('name'),
            'type': activity.get('type'),
            'distance': activity.get('distance'),
            'moving_time': activity.get('moving_time'),
            'start_date_local': activity.get('start_date_local'),
            'description': activity.get('description', ''),
            'comment_count': activity.get('comment_count', 0)
        }
        
        # Add map data (polyline only, no GPS points)
        if 'map' in activity:
            map_data = activity['map']
            essential_map = {}
            
            # Keep only polyline data (much smaller than GPS points)
            if 'polyline' in map_data:
                essential_map['polyline'] = map_data['polyline']
            if 'summary_polyline' in map_data:
                essential_map['summary_polyline'] = map_data['summary_polyline']
            if 'bounds' in map_data:
                essential_map['bounds'] = map_data['bounds']
            
            essential_fields['map'] = essential_map
        
        return essential_fields

    def _process_photos_data(self, photos_response: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Process photos data to extract only what we need"""
        if not photos_response:
            return {}
        
        # Get the first photo (primary)
        primary_photo = photos_response[0]
        
        return {
            'primary': {
                'unique_id': primary_photo.get('unique_id'),
                'type': primary_photo.get('type'),
                'urls': {
                    '600': primary_photo.get('urls', {}).get('1800', ''),  # Map 1800 to 600
                    '1000': primary_photo.get('urls', {}).get('5000', '')  # Map 5000 to 1000
                },
                'status': primary_photo.get('status'),
                'placeholder_image': primary_photo.get('placeholder_image', False)
            },
            'count': len(photos_response)
        }

    def _detect_music(self, description: str) -> Optional[Dict[str, Any]]:
        """Detect music information from activity description"""
        if not description:
            return None
        
        # Pattern for "Album: [Album Name] by [Artist]"
        album_pattern = r'Album:\s*([^,\n]+?)\s+by\s+([^,\n]+)'
        album_match = re.search(album_pattern, description, re.IGNORECASE)
        
        # Pattern for "Russell Radio: [Track Name] by [Artist]"
        track_pattern = r'Russell Radio:\s*([^,\n]+?)\s+by\s+([^,\n]+)'
        track_match = re.search(track_pattern, description, re.IGNORECASE)
        
        if album_match:
            album_name = album_match.group(1).strip()
            artist = album_match.group(2).strip()
            return {
                'album': {'name': album_name, 'artist': artist},
                'detected': {
                    'type': 'album',
                    'title': album_name,
                    'artist': artist,
                    'source': 'album'
                }
            }
        elif track_match:
            track_name = track_match.group(1).strip()
            artist = track_match.group(2).strip()
            return {
                'track': {'name': track_name, 'artist': artist},
                'detected': {
                    'type': 'track',
                    'title': track_name,
                    'artist': artist,
                    'source': 'russell_radio'
                }
            }
        
        return None

    def _fetch_complete_activity_data(self, activity: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch complete activity data with only essential fields"""
        activity_id = activity.get("id")
        
        try:
            access_token = self.token_manager.get_valid_access_token()
            headers = {"Authorization": f"Bearer {access_token}"}
            
            # Start with essential data
            enhanced_activity = self._extract_essential_data(activity)
            
            # Fetch complete activity data for description
            complete_activity_response = self._make_api_call_with_retry(
                f"{self.base_url}/activities/{activity_id}",
                headers
            )
            complete_activity = complete_activity_response.json()
            
            # Update with complete description
            enhanced_activity['description'] = complete_activity.get('description', '')
            
            # Add music detection from description
            try:
                description = enhanced_activity['description']
                if description:
                    music_data = self._detect_music(description)
                    if music_data and music_data.get('detected'):
                        # Get Deezer widget data
                        deezer_data = self.music_integration.get_music_widget(description)
                        if deezer_data:
                            music_data.update(deezer_data)
                    enhanced_activity["music"] = music_data if music_data else {}
                else:
                    enhanced_activity["music"] = {}
            except Exception as e:
                logger.warning(f"Failed to process music for activity {activity_id}: {e}")
                enhanced_activity["music"] = {}
            
            # Fetch photos (only if needed)
            try:
                photos_response = self._make_api_call_with_retry(
                    f"{self.base_url}/activities/{activity_id}/photos?size=5000",
                    headers
                )
                photos_data = self._process_photos_data(photos_response.json())
                enhanced_activity["photos"] = photos_data
            except Exception as e:
                logger.warning(f"Failed to fetch photos for activity {activity_id}: {e}")
                enhanced_activity["photos"] = {}
            
            # Fetch comments
            try:
                comments_response = self._make_api_call_with_retry(
                    f"{self.base_url}/activities/{activity_id}/comments",
                    headers
                )
                comments_data = comments_response.json()
                enhanced_activity["comments"] = comments_data
            except Exception as e:
                logger.warning(f"Failed to fetch comments for activity {activity_id}: {e}")
                enhanced_activity["comments"] = []
            
            return enhanced_activity
            
        except Exception as e:
            logger.warning(f"Failed to fetch complete data for activity {activity_id}: {e}")
            # Return basic essential data as fallback
            return self._extract_essential_data(activity)

    def get_activities_smart(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get activities with smart caching and essential data only"""
        start_time = time.time()
        
        try:
            # Load cache
            cache_data = self._load_cache()
            
            # Check if cache is valid
            if self._is_cache_valid(cache_data):
                logger.info("Using cached data")
                activities = cache_data.get('activities', [])
                perf_logger.info(f"Cache hit - {time.time() - start_time:.3f}s")
                return activities[:limit]
            
            # Cache is invalid, fetch from Strava
            logger.info("Cache invalid, fetching from Strava API")
            
            access_token = self.token_manager.get_valid_access_token()
            headers = {"Authorization": f"Bearer {access_token}"}
            
            # Fetch basic activities
            activities_response = self._make_api_call_with_retry(
                f"{self.base_url}/athlete/activities?per_page={limit}",
                headers
            )
            activities = activities_response.json()
            
            # Filter activities by type
            filtered_activities = [
                activity for activity in activities 
                if activity.get('type') in self.allowed_activity_types
            ]
            
            # For the first few activities, fetch complete data
            enhanced_activities = []
            for i, activity in enumerate(filtered_activities[:limit]):
                if i < 5:  # Only enhance first 5 activities to avoid too many API calls
                    try:
                        enhanced_activity = self._fetch_complete_activity_data(activity)
                        enhanced_activities.append(enhanced_activity)
                    except Exception as e:
                        logger.warning(f"Failed to enhance activity {activity.get('id', 'unknown')}: {e}")
                        enhanced_activities.append(self._extract_essential_data(activity))
                else:
                    # For remaining activities, use basic essential data
                    enhanced_activities.append(self._extract_essential_data(activity))
            
            # Save to cache
            cache_data = {
                'timestamp': datetime.now().isoformat(),
                'activities': enhanced_activities
            }
            self._save_cache(cache_data)
            
            perf_logger.info(f"API fetch - {time.time() - start_time:.3f}s")
            return enhanced_activities[:limit]
            
        except Exception as e:
            logger.error(f"Error in get_activities_smart: {e}")
            return []

    def _load_cache(self) -> Dict[str, Any]:
        """Load cache with in-memory optimization"""
        # Check in-memory cache first
        if (self._cache_data and 
            self._cache_loaded_at and 
            time.time() - self._cache_loaded_at < self._cache_ttl):
            return self._cache_data
        
        # Load from file
        try:
            with open(self.cache_file, 'r') as f:
                cache_data = json.load(f)
            
            # Store in memory for faster access
            self._cache_data = cache_data
            self._cache_loaded_at = time.time()
            
            return cache_data
        except FileNotFoundError:
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"Cache file corrupted: {e}")
            return {}

    def _save_cache(self, cache_data: Dict[str, Any]):
        """Save cache to file"""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
            
            with open(self.cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
            
            # Update in-memory cache
            self._cache_data = cache_data
            self._cache_loaded_at = time.time()
            
            logger.info(f"Cache saved to {self.cache_file}")
        except Exception as e:
            logger.error(f"Failed to save cache: {e}")

    def _is_cache_valid(self, cache_data: Dict[str, Any]) -> bool:
        """Check if cache is still valid"""
        if not cache_data or 'timestamp' not in cache_data:
            return False
        
        try:
            cache_time = datetime.fromisoformat(cache_data['timestamp'])
            expiry_time = cache_time + timedelta(hours=self.cache_duration_hours)
            return datetime.now() < expiry_time
        except Exception:
            return False

    def get_complete_activity_data(self, activity_id: int) -> Dict[str, Any]:
        """Get complete data for a specific activity"""
        try:
            access_token = self.token_manager.get_valid_access_token()
            headers = {"Authorization": f"Bearer {access_token}"}
            
            # Fetch basic activity data
            activity_response = self._make_api_call_with_retry(
                f"{self.base_url}/activities/{activity_id}",
                headers
            )
            activity = activity_response.json()
            
            # Return enhanced data
            return self._fetch_complete_activity_data(activity)
            
        except Exception as e:
            logger.error(f"Error fetching complete activity data for {activity_id}: {e}")
            return {}

# Import regex for music detection
import re
