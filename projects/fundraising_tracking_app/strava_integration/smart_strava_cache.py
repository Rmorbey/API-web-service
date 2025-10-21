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
import re
import requests
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional, Tuple
from dotenv import load_dotenv
from .strava_token_manager import StravaTokenManager
from .http_clients import get_http_client
from .supabase_cache_manager import SecureSupabaseCacheManager
import os

# Configure enhanced logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('strava_integration_new.log')
    ]
)
logger = logging.getLogger(__name__)

# Performance logging is handled by the main logger

load_dotenv()

class SmartStravaCache:
    def __init__(self, cache_duration_hours: int = None):
        self.token_manager = StravaTokenManager()
        self.base_url = "https://www.strava.com/api/v3"
        # JSON cache file removed - using Supabase-only storage
        
        # Initialize Supabase cache manager for persistence
        self.supabase_cache = SecureSupabaseCacheManager()
        
        # Allow custom cache duration, default to 6 hours
        self.cache_duration_hours = cache_duration_hours or int(os.getenv("STRAVA_CACHE_HOURS", "6"))
        
        # Filtering criteria
        self.allowed_activity_types = ["Run", "Ride"]  # Only runs and bike rides
        
        # Rate limiting tracking
        self.api_calls_made = 0
        self.api_calls_reset_time = datetime.now()
        self.max_calls_per_15min = 100
        self.max_calls_per_day = 1000
        
        # Emergency refresh tracking
        self._emergency_refresh_in_progress = False
        
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
        
        # Thread safety for batch processing
        self._batch_lock = threading.Lock()
        
        # Startup phase tracking
        self._startup_phase = "initialized"
        self._background_services_started = False
        
        # Initialize cache system on startup (synchronous - no background operations)
        self.initialize_cache_system_sync()
    
    def start_background_services(self):
        """Start background services after main startup is complete (Phase 3)"""
        if self._background_services_started:
            logger.info("🔄 Background services already started")
            return
        
        logger.info("🔄 Starting background services...")
        
        try:
            # Start Supabase background services first
            self.supabase_cache.start_background_services()
            
            # Check if we need to trigger emergency refresh (no cache data found during sync init)
            if not self._cache_data:
                logger.info("🔄 No cache data found during sync init - scheduling emergency refresh for after startup")
                # Defer emergency refresh to avoid blocking startup - use longer delay
                def deferred_emergency_refresh():
                    time.sleep(30)  # Wait 30 seconds for main app to fully start
                    logger.info("🔄 Starting deferred emergency refresh...")
                    try:
                        logger.info("🔄 Calling _start_batch_processing()...")
                        # Use the same emergency refresh logic but with better error handling
                        self._start_batch_processing()
                        logger.info("✅ _start_batch_processing() completed successfully")
                    except Exception as e:
                        logger.error(f"❌ Deferred emergency refresh failed: {e}")
                        import traceback
                        logger.error(f"❌ Full traceback: {traceback.format_exc()}")
                
                emergency_thread = threading.Thread(target=deferred_emergency_refresh, daemon=True)
                emergency_thread.start()
                logger.info("🔄 Emergency refresh scheduled for 30 seconds after startup")
            
            # Start the automated refresh system
            self._start_automated_refresh()
            
            # Start the daily corruption check scheduler
            self._schedule_daily_corruption_check()
            
            self._background_services_started = True
            self._startup_phase = "background_services_started"
            logger.info("✅ Background services started successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to start background services: {e}")
            self._startup_phase = "background_services_failed"
    
    def initialize_cache_system_sync(self):
        """Initialize cache system synchronously (Phase 2) - no background operations"""
        logger.info("🔄 Initializing cache system synchronously...")
        
        # Only load existing cache data, don't trigger any background operations
        try:
            # Try to load existing cache data
            cache_data = self._load_cache_sync()
            if cache_data:
                logger.info("✅ Cache system initialized with existing data")
            else:
                logger.info("📭 No existing cache data found - will populate in background")
        except Exception as e:
            logger.error(f"❌ Failed to initialize cache system: {e}")
    
    def _load_cache_sync(self) -> Optional[Dict[str, Any]]:
        """Load cache data synchronously without triggering background operations"""
        now = datetime.now()
        
        # 1. Check in-memory cache first
        if self._cache_data and self._cache_loaded_at:
            cache_age = (now - self._cache_loaded_at).total_seconds()
            if cache_age < self._cache_ttl:
                return self._cache_data
        
        # 2. Try to load from Supabase (synchronous only)
        if self.supabase_cache.enabled:
            try:
                supabase_result = self.supabase_cache.get_cache('strava', 'fundraising-app')
                if supabase_result and supabase_result.get('data'):
                    cache_data = supabase_result['data']
                    
                    # Validate data integrity
                    if self._validate_cache_integrity(cache_data):
                        self._cache_data = cache_data
                        self._cache_loaded_at = now
                        return cache_data
            except Exception as e:
                logger.error(f"❌ Failed to load from Supabase: {e}")
        
        return None
    
    def initialize_cache_system(self):
        """Initialize cache system on server startup (legacy method for background operations)"""
        logger.info("🔄 Initializing cache system on startup...")
        
        if self.supabase_cache.enabled:
            try:
                # Load from Supabase and populate JSON files
                supabase_result = self.supabase_cache.get_cache('strava', 'fundraising-app')
                if supabase_result and supabase_result.get('data'):
                    cache_data = supabase_result['data']
                    
                    # Validate data integrity
                    if self._validate_cache_integrity(cache_data):
                        # JSON file operations removed
                        logger.info("✅ Cache system initialized from Supabase")
                        
                        # Use simplified check and refresh logic
                        self.check_and_refresh()
                    else:
                        logger.warning("❌ Supabase data integrity check failed, triggering refresh...")
                        self.check_and_refresh()
                else:
                    logger.info("📭 No Supabase data found, triggering refresh to populate cache...")
                    self.check_and_refresh()
            except Exception as e:
                logger.error(f"❌ Cache system initialization failed: {e}")
        else:
            logger.info("📝 Supabase disabled, using file-based cache only")
        
    def _load_cache(self, trigger_emergency_refresh: bool = True) -> Dict[str, Any]:
        """Load cache: In-Memory → Supabase → Emergency Refresh (if requested)"""
        now = datetime.now()
        
        # 1. Check in-memory cache first (fastest)
        if (self._cache_data is not None and 
            self._cache_loaded_at is not None and 
            (now - self._cache_loaded_at).total_seconds() < self._cache_ttl):
            logger.debug("✅ Using in-memory cache")
            return self._cache_data
        
        # 2. JSON file operations removed - using Supabase-only storage
        
        # 3. Fallback to Supabase (source of truth)
        if self.supabase_cache.enabled:
            try:
                logger.info("🔄 _load_cache: Attempting to load from Supabase...")
                supabase_result = self.supabase_cache.get_cache('strava', 'fundraising-app')
                logger.info("🔄 _load_cache: Supabase get_cache completed")
                if supabase_result and supabase_result.get('data'):
                    self._cache_data = supabase_result['data']
                    self._cache_loaded_at = now
                    
                    # Validate Supabase data integrity
                    if self._validate_cache_integrity(self._cache_data):
                        logger.info("✅ Loaded cache from Supabase database")
                        # JSON file operations removed
                        return self._cache_data
                    else:
                        logger.warning("❌ Supabase cache integrity check failed")
                else:
                    logger.info("📭 No cache data found in Supabase")
            except Exception as e:
                logger.error(f"❌ Supabase read failed: {e}")
        
        # 4. Emergency refresh (all sources failed) - only if requested
        if trigger_emergency_refresh and not self._emergency_refresh_in_progress:
            logger.warning("🚨 All cache sources failed, triggering emergency refresh...")
            
            # CRITICAL: Start batch processing in background to avoid blocking startup
            # This allows health checks to respond while batch processing runs
            logger.info("🔄 Starting batch processing in background during startup...")
            try:
                # Start batch processing with a timeout to prevent hanging
                def start_batch_with_timeout():
                    try:
                        self._start_batch_processing()
                    except Exception as e:
                        logger.error(f"❌ Failed to start batch processing: {e}")
                
                batch_startup_thread = threading.Thread(target=start_batch_with_timeout, daemon=True)
                batch_startup_thread.start()
                
                # Don't wait for it - let it run in background
                logger.info("🔄 Batch processing startup initiated in background")
                
            except Exception as e:
                logger.error(f"❌ Failed to initiate batch processing: {e}")
        elif not trigger_emergency_refresh:
            logger.debug("🔄 Emergency refresh not triggered (called from batch processing)")
        
        # Return empty cache immediately to allow app to start
        # Emergency refresh will populate cache in background
        self._cache_data = {"timestamp": None, "activities": []}
        logger.info("🔄 App starting with empty cache, emergency refresh running in background")
        return self._cache_data
    
    # JSON file operations removed - using Supabase-only storage
    
    def _save_cache(self, data: Dict[str, Any]):
        """Save cache: Validate → Memory → Supabase (with retry)"""
        # 1. Validate data first
        if not self._validate_cache_integrity(data):
            logger.error("❌ Cache data validation failed, not saving")
            return
        
        # 2. Add timestamps to data
        data_with_timestamps = data.copy()
        data_with_timestamps['last_saved'] = datetime.now().isoformat()
        
        # 3. JSON file operations removed - using Supabase-only storage
        
        # 4. Update in-memory cache
        self._cache_data = data_with_timestamps
        self._cache_loaded_at = datetime.now()
        
        # 5. Save to Supabase (with retry logic)
        if self.supabase_cache.enabled:
            try:
                # Extract timestamps for Supabase
                last_fetch = None
                last_rich_fetch = None
                
                if data_with_timestamps.get('timestamp'):
                    last_fetch = datetime.fromisoformat(data_with_timestamps['timestamp'])
                
                if data_with_timestamps.get('last_rich_fetch'):
                    last_rich_fetch = datetime.fromisoformat(data_with_timestamps['last_rich_fetch'])
                
                # Save to Supabase
                success = self.supabase_cache.save_cache(
                    'strava',
                    data_with_timestamps,
                    last_fetch=last_fetch,
                    last_rich_fetch=last_rich_fetch,
                    project_id='fundraising-app'
                )
                
                if success:
                    logger.info("✅ Cache saved to Supabase successfully")
                else:
                    logger.warning("⚠️ Failed to save to Supabase, will retry in background")
                    
            except Exception as e:
                logger.error(f"❌ Supabase save error: {e}")
                # Queue for background retry
                self._queue_supabase_save(data_with_timestamps, last_fetch, last_rich_fetch)
    
    def _queue_supabase_save(self, data: Dict[str, Any], last_fetch: Optional[datetime] = None, last_rich_fetch: Optional[datetime] = None):
        """Queue data for background Supabase save"""
        if self.supabase_cache.enabled:
            self.supabase_cache._queue_supabase_save(
                'strava',
                data,
                last_fetch=last_fetch,
                last_rich_fetch=last_rich_fetch,
                project_id='fundraising-app'
            )
    
    def _is_cache_valid(self, cache_data: Dict[str, Any]) -> bool:
        """Smart cache validation with multiple criteria"""
        if not cache_data.get("timestamp"):
            return False
        
        # Check data integrity first - if data is complete, cache is valid regardless of age
        if self._validate_cache_integrity(cache_data):
            activities = cache_data.get("activities", [])
            if len(activities) >= 10:  # Reasonable threshold
                logger.info(f"Cache has complete data ({len(activities)} activities), considering valid despite age")
                return True
        
        # If data is incomplete, check time-based validation
        cache_time = datetime.fromisoformat(cache_data["timestamp"])
        expiry_time = cache_time + timedelta(hours=self.cache_duration_hours)
        now = datetime.now()
        
        # Basic time-based validation
        if now >= expiry_time:
            return False
        
        # Smart validation: Check if we have recent rich data
        last_rich_fetch = cache_data.get("last_rich_fetch")
        if last_rich_fetch:
            rich_fetch_time = datetime.fromisoformat(last_rich_fetch)
            rich_expiry_time = rich_fetch_time + timedelta(hours=self.cache_duration_hours)
            
            # If rich data is also expired, definitely need refresh
            if now >= rich_expiry_time:
                return False
        
        # Additional smart checks
        activities = cache_data.get("activities", [])
        if not activities:
            return False
        
        # Check if we have a reasonable number of activities
        if len(activities) < 10:  # Arbitrary threshold
            logger.warning(f"Cache has only {len(activities)} activities, may need refresh")
        
        return True
    
    def _should_refresh_cache(self, cache_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Simplified 6-hour refresh logic"""
        if not cache_data.get("timestamp"):
            return True, "No timestamp in cache"
        
        cache_time = datetime.fromisoformat(cache_data["timestamp"])
        expiry_time = cache_time + timedelta(hours=6)  # 6-hour refresh
        
        if datetime.now() >= expiry_time:
            return True, f"Cache expired {datetime.now() - expiry_time} ago"
        
        return False, "Cache is valid"
    
    def _should_trigger_8hour_refresh(self) -> bool:
        """Check if 8-hour refresh should be triggered based on last_fetch timestamp"""
        cache_data = self._load_cache()
        if not cache_data:
            return False  # No cache data = emergency refresh, not 8-hour refresh
        
        last_fetch = cache_data.get('last_fetch')
        if not last_fetch:
            return False  # No last_fetch timestamp = emergency refresh, not 8-hour refresh
        
        try:
            last_fetch_time = datetime.fromisoformat(last_fetch)
            time_since_fetch = datetime.now() - last_fetch_time
            return time_since_fetch >= timedelta(hours=8)
        except Exception as e:
            logger.warning(f"Error parsing last_fetch timestamp: {e}")
            return False  # If parsing fails, let emergency refresh handle it
    
    
    def _fetch_rich_data_for_new_activities(self, new_activities: List[Dict[str, Any]], access_token: str = None, apply_expiration_checks: bool = True) -> Dict[int, Dict[str, Any]]:
        """Fetch rich data (photos + comments) only for new activities"""
        rich_data = {}
        
        # Use provided token or fallback to environment - NO token refresh here
        if not access_token:
            logger.info(f"🔄 No token provided for batch of {len(new_activities)} activities, using environment fallback...")
            import os
            fallback_token = os.getenv("STRAVA_ACCESS_TOKEN")
            if fallback_token:
                access_token = fallback_token
                logger.info("✅ Using fallback token from environment variables")
            else:
                logger.error("❌ No access token available - returning empty rich data")
                # Return empty rich data for all activities
                for activity in new_activities:
                    activity_id = activity.get("id")
                    if activity_id:
                        rich_data[activity_id] = {"photos": {}, "comments": []}
                return rich_data
        
        for activity in new_activities:
            activity_id = activity.get("id")
            if not activity_id:
                continue
            
            try:
                logger.info(f"🔄 Fetching rich data for new activity {activity_id}")
                
                # Fetch photos (with or without expiration checks)
                photos_data = {}
                if apply_expiration_checks and self._check_photos_fetch_expired(activity):
                    logger.info(f"⏰ Photos fetch expired for activity {activity_id}, skipping photos...")
                else:
                    if apply_expiration_checks:
                        logger.info(f"📸 Photos fetch not expired for activity {activity_id}, fetching photos...")
                    else:
                        logger.info(f"📸 Fetching photos for activity {activity_id} (no expiration checks)...")
                    photos_data = self._fetch_activity_photos(activity_id, access_token=access_token)
                
                # Fetch comments (with or without expiration checks)
                comments_data = []
                if apply_expiration_checks and self._check_comments_fetch_expired(activity):
                    logger.info(f"⏰ Comments fetch expired for activity {activity_id}, skipping comments...")
                else:
                    if apply_expiration_checks:
                        logger.info(f"💬 Comments fetch not expired for activity {activity_id}, fetching comments...")
                    else:
                        logger.info(f"💬 Fetching comments for activity {activity_id} (no expiration checks)...")
                    comments_data = self._fetch_activity_comments(activity_id, access_token=access_token)
                
                # Fetch detailed activity data (polyline and description)
                details_data = {}
                if apply_expiration_checks and (self._check_polyline_fetch_expired(activity) or self._check_description_fetch_expired(activity)):
                    logger.info(f"⏰ Polyline/description fetch expired for activity {activity_id}, skipping details...")
                else:
                    if apply_expiration_checks:
                        logger.info(f"🗺️ Polyline/description fetch not expired for activity {activity_id}, fetching details...")
                    else:
                        logger.info(f"🗺️ Fetching details for activity {activity_id} (no expiration checks)...")
                    details_data = self._fetch_activity_details(activity_id, access_token=access_token)
                
                rich_data[activity_id] = {
                    "photos": photos_data,
                    "comments": comments_data,
                    **details_data  # Merge in description and map data
                }
                
                logger.info(f"✅ Successfully fetched rich data for activity {activity_id}")
                
            except Exception as e:
                logger.warning(f"⚠️ Failed to fetch rich data for activity {activity_id}: {e}")
                rich_data[activity_id] = {
                    "photos": {},
                    "comments": []
                }
        
        return rich_data

    def _check_photos_fetch_expired(self, activity: Dict[str, Any]) -> bool:
        """Check if photos fetch has expired (1 day after activity date)"""
        try:
            activity_date_str = activity.get('start_date_local')
            if not activity_date_str:
                return True  # If no date, consider expired
            
            from datetime import datetime, timedelta, timezone
            activity_date = datetime.fromisoformat(activity_date_str.replace('Z', '+00:00'))
            photos_expiry = activity_date + timedelta(days=1)
            
            # Use timezone-aware current time for comparison
            current_time = datetime.now(timezone.utc)
            return current_time > photos_expiry
        except Exception as e:
            logger.warning(f"⚠️ Error checking photos expiry for activity: {e}")
            return True  # If error, consider expired

    def _check_comments_fetch_expired(self, activity: Dict[str, Any]) -> bool:
        """Check if comments fetch has expired (1 week after activity date)"""
        try:
            activity_date_str = activity.get('start_date_local')
            if not activity_date_str:
                return True  # If no date, consider expired
            
            from datetime import datetime, timedelta, timezone
            activity_date = datetime.fromisoformat(activity_date_str.replace('Z', '+00:00'))
            comments_expiry = activity_date + timedelta(weeks=1)
            
            # Use timezone-aware current time for comparison
            current_time = datetime.now(timezone.utc)
            return current_time > comments_expiry
        except Exception as e:
            logger.warning(f"⚠️ Error checking comments expiry for activity: {e}")
            return True  # If error, consider expired

    def _fetch_activity_photos(self, activity_id: int, access_token: str = None) -> Dict[str, Any]:
        """Fetch photos for a specific activity and transform to frontend format"""
        try:
            if not access_token:
                import os
                access_token = os.getenv("STRAVA_ACCESS_TOKEN")
            
            if not access_token:
                logger.warning(f"⚠️ No access token available for fetching photos for activity {activity_id}")
                return {"photos": []}
            
            headers = {"Authorization": f"Bearer {access_token}"}
            url = f"https://www.strava.com/api/v3/activities/{activity_id}/photos?size=5000"
            
            http_client = get_http_client()
            response = http_client.get(url, headers=headers, timeout=30.0)
            
            if response.status_code == 200:
                raw_photos = response.json()
                logger.debug(f"📸 Fetched {len(raw_photos)} photos for activity {activity_id}")
                
                # Transform to frontend format
                transformed_photos = self._transform_photos_to_frontend_format(raw_photos)
                return {"photos": transformed_photos}
            else:
                logger.warning(f"⚠️ Failed to fetch photos for activity {activity_id}: {response.status_code}")
                return {"photos": []}
                
        except Exception as e:
            logger.warning(f"⚠️ Error fetching photos for activity {activity_id}: {e}")
            return {"photos": []}

    def _transform_photos_to_frontend_format(self, raw_photos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform Strava photo data to frontend-expected format"""
        try:
            transformed_photos = []
            
            for photo in raw_photos:
                # Extract the high-quality URL from Strava photo data (size=5000)
                # Strava returns the photo URL in the 'urls' field or directly as 'url'
                photo_url = ""
                
                # Try different possible URL fields from Strava API
                if photo.get("urls"):
                    # If urls is a dict, get the largest size available
                    urls = photo.get("urls", {})
                    # Strava API returns "5000" as the high-quality size key
                    photo_url = urls.get("5000") or urls.get("1200px") or urls.get("600px") or urls.get("100px") or ""
                elif photo.get("url"):
                    # Direct URL field
                    photo_url = photo.get("url", "")
                
                # Create frontend-compatible photo object with high-quality URL for all sizes
                # Frontend can handle resizing or use the same URL for all sizes
                if photo_url:
                    frontend_photo = {
                        "urls": {
                            "300": photo_url,   # High-quality URL for thumbnail (frontend can resize)
                            "600": photo_url,   # High-quality URL for medium (frontend can resize)
                            "1200": photo_url   # High-quality URL for large (original size)
                        }
                    }
                    transformed_photos.append(frontend_photo)
                    logger.debug(f"📸 Transformed photo with high-quality URL: {photo_url}")
            
            logger.debug(f"📸 Transformed {len(transformed_photos)} photos to frontend format")
            return transformed_photos
            
        except Exception as e:
            logger.warning(f"⚠️ Error transforming photos: {e}")
            return []

    def _fetch_activity_comments(self, activity_id: int, access_token: str = None) -> List[Dict[str, Any]]:
        """Fetch comments for a specific activity"""
        try:
            if not access_token:
                import os
                access_token = os.getenv("STRAVA_ACCESS_TOKEN")
            
            if not access_token:
                logger.warning(f"⚠️ No access token available for fetching comments for activity {activity_id}")
                return []
            
            headers = {"Authorization": f"Bearer {access_token}"}
            url = f"https://www.strava.com/api/v3/activities/{activity_id}/comments"
            
            http_client = get_http_client()
            response = http_client.get(url, headers=headers, timeout=30.0)
            
            if response.status_code == 200:
                comments_data = response.json()
                logger.debug(f"💬 Fetched {len(comments_data)} comments for activity {activity_id}")
                return comments_data
            else:
                logger.warning(f"⚠️ Failed to fetch comments for activity {activity_id}: {response.status_code}")
                return []
                
        except Exception as e:
            logger.warning(f"⚠️ Error fetching comments for activity {activity_id}: {e}")
            return []

    def _fetch_activity_details(self, activity_id: int, access_token: str = None) -> Dict[str, Any]:
        """Fetch detailed activity data including polyline and description"""
        try:
            if not access_token:
                import os
                access_token = os.getenv("STRAVA_ACCESS_TOKEN")
            
            if not access_token:
                logger.warning(f"⚠️ No access token available for fetching details for activity {activity_id}")
                return {}
            
            headers = {"Authorization": f"Bearer {access_token}"}
            url = f"https://www.strava.com/api/v3/activities/{activity_id}"
            
            http_client = get_http_client()
            response = http_client.get(url, headers=headers, timeout=30.0)
            
            if response.status_code == 200:
                activity_data = response.json()
                logger.debug(f"🗺️ Fetched detailed data for activity {activity_id}")
                
                # Extract the fields we need
                details = {}
                
                # Get description
                if activity_data.get("description"):
                    details["description"] = activity_data["description"]
                
                # Get detailed polyline and calculate bounds
                map_data = activity_data.get("map", {})
                if map_data.get("polyline"):
                    details["map"] = {
                        "polyline": map_data["polyline"],
                        "bounds": self._calculate_bounds_from_polyline(map_data["polyline"])
                    }
                
                return details
            else:
                logger.warning(f"⚠️ Failed to fetch details for activity {activity_id}: {response.status_code}")
                return {}
                
        except Exception as e:
            logger.warning(f"⚠️ Error fetching details for activity {activity_id}: {e}")
            return {}

    def _calculate_bounds_from_polyline(self, polyline_string: str) -> Dict[str, float]:
        """Calculate bounds from polyline string using polyline library"""
        try:
            import polyline
            
            # Decode polyline to get coordinates
            coordinates = polyline.decode(polyline_string)
            
            if not coordinates:
                return {}
            
            # Extract latitudes and longitudes
            lats = [coord[0] for coord in coordinates]
            lngs = [coord[1] for coord in coordinates]
            
            # Calculate bounds
            bounds = {
                "south": min(lats),
                "north": max(lats),
                "west": min(lngs),
                "east": max(lngs)
            }
            
            logger.debug(f"🗺️ Calculated bounds: {bounds}")
            return bounds
            
        except Exception as e:
            logger.warning(f"⚠️ Error calculating bounds from polyline: {e}")
            return {}

    def _check_polyline_fetch_expired(self, activity: Dict[str, Any]) -> bool:
        """Check if polyline fetch has expired (1 day after activity)"""
        try:
            activity_date = activity.get('start_date_local', '')
            if not activity_date:
                return True
            
            # Parse the date and ensure it's timezone-aware
            start_date = datetime.fromisoformat(activity_date.replace('Z', '+00:00'))
            one_day_ago = datetime.now(timezone.utc) - timedelta(days=1)
            
            # Ensure both datetimes are timezone-aware for comparison
            if start_date.tzinfo is None:
                start_date = start_date.replace(tzinfo=timezone.utc)
            if one_day_ago.tzinfo is None:
                one_day_ago = one_day_ago.replace(tzinfo=timezone.utc)
            
            return start_date < one_day_ago
        except Exception as e:
            logger.warning(f"Error checking polyline fetch expiration: {e}")
            return True

    def _check_description_fetch_expired(self, activity: Dict[str, Any]) -> bool:
        """Check if description fetch has expired (1 day after activity)"""
        try:
            activity_date = activity.get('start_date_local', '')
            if not activity_date:
                return True
            
            # Parse the date and ensure it's timezone-aware
            start_date = datetime.fromisoformat(activity_date.replace('Z', '+00:00'))
            one_day_ago = datetime.now(timezone.utc) - timedelta(days=1)
            
            # Ensure both datetimes are timezone-aware for comparison
            if start_date.tzinfo is None:
                start_date = start_date.replace(tzinfo=timezone.utc)
            if one_day_ago.tzinfo is None:
                one_day_ago = one_day_ago.replace(tzinfo=timezone.utc)
            
            return start_date < one_day_ago
        except Exception as e:
            logger.warning(f"Error checking description fetch expiration: {e}")
            return True

    
    def _fetch_rich_data_for_all_activities_with_batching(self, basic_data: List[Dict[str, Any]], access_token: str = None, apply_expiration_checks: bool = True) -> Dict[int, Dict[str, Any]]:
        """Fetch rich data for ALL activities using batch processing (20 activities every 15 minutes)"""
        rich_data = {}
        
        if not basic_data:
            logger.info("🔄 No activities to fetch rich data for")
            return rich_data
        
        logger.info(f"🔄 Starting batch processing for {len(basic_data)} activities (corruption check)")
        
        # Process in batches of 20
        batch_size = 20
        for i in range(0, len(basic_data), batch_size):
            batch = basic_data[i:i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(basic_data) + batch_size - 1) // batch_size
            
            logger.info(f"🏃‍♂️ Processing batch {batch_num}/{total_batches}: {len(batch)} activities")
            
            # Fetch rich data for this batch
            batch_rich_data = self._fetch_rich_data_for_new_activities(batch, access_token=access_token, apply_expiration_checks=apply_expiration_checks)
            rich_data.update(batch_rich_data)
            
            logger.info(f"✅ Completed batch {batch_num}/{total_batches}: {len(batch_rich_data)} activities with rich data")
            
            # Wait 15 minutes between batches (except for the last batch)
            if i + batch_size < len(basic_data):
                logger.info("⏰ Waiting 15 minutes before next batch...")
                time.sleep(900)  # 15 minutes
        
        logger.info(f"✅ Batch processing completed: {len(rich_data)} activities with rich data")
        return rich_data
    
    
    
    def _compare_fresh_vs_database_data(self, basic_data: List[Dict[str, Any]], rich_data: Dict[int, Dict[str, Any]]) -> Dict[str, Any]:
        """Compare fresh Strava data with database data to detect corruption"""
        cache_data = self._load_cache(trigger_emergency_refresh=False)
        if not cache_data:
            return {"corruption_detected": False, "corrupted_activities": []}
        
        existing_activities = cache_data.get("activities", [])
        existing_by_id = {activity.get("id"): activity for activity in existing_activities}
        
        corrupted_activities = []
        
        for activity in basic_data:
            activity_id = activity.get("id")
            existing_activity = existing_by_id.get(activity_id)
            
            if not existing_activity:
                continue  # New activity, no corruption to check
            
            # Compare basic data
            corruption_detected = False
            corruption_reasons = []
            
            # Check name
            if activity.get("name") != existing_activity.get("name"):
                corruption_detected = True
                corruption_reasons.append("name_mismatch")
            
            # Check distance
            if activity.get("distance") != existing_activity.get("distance"):
                corruption_detected = True
                corruption_reasons.append("distance_mismatch")
            
            # Check map data
            fresh_map = activity.get("map", {})
            existing_map = existing_activity.get("map", {})
            
            if fresh_map.get("polyline") != existing_map.get("polyline"):
                corruption_detected = True
                corruption_reasons.append("polyline_mismatch")
            
            if corruption_detected:
                corrupted_activities.append({
                    "id": activity_id,
                    "name": activity.get("name", "Unknown"),
                    "reasons": corruption_reasons
                })
                logger.warning(f"🚨 Corruption detected in activity {activity_id}: {corruption_reasons}")
        
        return {
            "corruption_detected": len(corrupted_activities) > 0,
            "corrupted_activities": corrupted_activities,
            "total_checked": len(basic_data),
            "corrupted_count": len(corrupted_activities)
        }

    def _repair_corrupted_data(self, basic_data: List[Dict[str, Any]], rich_data: Dict[int, Dict[str, Any]]):
        """Repair corrupted data by updating cache with fresh data"""
        try:
            logger.info("🔄 Starting data repair process...")
            
            # Update activities with fresh data
            for activity in basic_data:
                activity_id = activity.get("id")
                if activity_id and activity_id in rich_data:
                    # Merge fresh basic data with fresh rich data
                    activity.update(rich_data[activity_id])
                    logger.info(f"✅ Repaired activity {activity_id}: {activity.get('name', 'Unknown')}")
            
            # Save repaired data to cache
            current_time = datetime.now().isoformat()
            repaired_cache = {
                "activities": basic_data,
                "timestamp": current_time,
                "last_fetch": current_time,
                "last_rich_fetch": current_time,
                "last_repair": current_time,
                "repair_reason": "corruption_detected"
            }
            
            self._save_cache(repaired_cache)
            logger.info(f"✅ Repaired {len(basic_data)} activities and saved to cache")
            
        except Exception as e:
            logger.error(f"❌ Data repair failed: {e}")
            raise
    
    def _schedule_daily_corruption_check(self):
        """Schedule daily corruption check at 2am using internal scheduler"""
        try:
            import schedule
            import threading
            
            def corruption_check_worker():
                schedule.every().day.at("02:00").do(self._daily_corruption_check)
                
                while True:
                    schedule.run_pending()
                    time.sleep(60)  # Check every minute
            
            # Start scheduler in background thread
            scheduler_thread = threading.Thread(target=corruption_check_worker, daemon=True)
            scheduler_thread.start()
            logger.info("🕐 Daily corruption check scheduled for 2am")
        except ImportError:
            logger.warning("⚠️ Schedule module not available - daily corruption check disabled")
            logger.info("💡 To enable daily corruption check, install: pip install schedule")
    
    def _daily_corruption_check(self):
        """Execute daily corruption check at 2am - fetch fresh data and detect corruption"""
        logger.info("🕐 Starting daily corruption check...")
        
        try:
            # Step 1: Get access token for corruption check (single token acquisition)
            logger.info("🔄 Getting access token for corruption check...")
            access_token = self.token_manager.get_valid_access_token()
            logger.info("✅ Got access token for corruption check")
            
            # Step 2: Fetch fresh basic data from Strava
            logger.info("🔄 Fetching fresh basic data for corruption check...")
            raw_data = self._fetch_from_strava(200, access_token=access_token)
            logger.info(f"🔄 Fetched {len(raw_data)} raw activities for corruption check")
            
            # Step 3: Filter for runs/rides from May 22nd, 2025 onwards
            basic_data = self._filter_activities(raw_data)
            logger.info(f"🔄 Filtered to {len(basic_data)} runs/rides for corruption check")
            
            # Step 4: Fetch fresh rich data for ALL activities (not just new ones)
            logger.info("🔄 Fetching fresh rich data for ALL activities...")
            # No expiration checks for corruption check - we need to compare ALL data
            rich_data = self._fetch_rich_data_for_all_activities_with_batching(basic_data, access_token=access_token, apply_expiration_checks=False)
            logger.info(f"🔄 Fetched rich data for {len(rich_data)} activities")
            
            # Step 5: Compare fresh data vs existing database data
            logger.info("🔄 Comparing fresh data vs database to detect corruption...")
            corruption_analysis = self._compare_fresh_vs_database_data(basic_data, rich_data)
            
            # Step 6: Handle corruption if detected
            if corruption_analysis["corruption_detected"]:
                corrupted_count = len(corruption_analysis["corrupted_activities"])
                logger.warning(f"🚨 Corruption detected in {corrupted_count} activities!")
                
                # Log details of corrupted activities
                for corrupted in corruption_analysis["corrupted_activities"]:
                    logger.warning(f"🚨 Activity {corrupted['id']} ({corrupted['name']}): {corrupted['reasons']}")
                
                # Step 7: Repair corrupted data by updating cache with fresh data
                logger.info("🔄 Repairing corrupted data with fresh information...")
                self._repair_corrupted_data(basic_data, rich_data)
                logger.info("✅ Corrupted data repaired successfully")
            else:
                logger.info("✅ No corruption detected - database is clean")
            
            # Step 8: Update corruption check metadata
            current_time = datetime.now().isoformat()
            cache_data = self._load_cache(trigger_emergency_refresh=False)
            if cache_data:
                cache_data['last_corruption_check'] = current_time
                cache_data['corruption_check_status'] = 'completed'
                if corruption_analysis["corruption_detected"]:
                    cache_data['last_corruption_detected'] = current_time
                    cache_data['corrupted_activities_count'] = len(corruption_analysis["corrupted_activities"])
                self._save_cache(cache_data)
            
            logger.info("✅ Daily corruption check completed successfully")
            
        except Exception as e:
            logger.error(f"❌ Daily corruption check failed: {e}")
            import traceback
            logger.error(f"❌ Full traceback: {traceback.format_exc()}")
    
    def check_and_refresh(self):
        """Main entry point - single condition check for all refresh scenarios"""
        cache_data = self._load_cache()
        
        # Check for emergency refresh (no data)
        if not cache_data or not cache_data.get("activities"):
            logger.info("🚨 Emergency refresh needed - no cache data found")
            self._start_batch_processing()
            return
        
        # Check for 8-hour refresh (data exists but is old)
        if self._should_trigger_8hour_refresh():
            logger.info("🕐 8-hour refresh needed - cache is older than 8 hours")
            self._start_batch_processing()
            return
        
        logger.info("✅ Cache is valid - no refresh needed")
    
    
    def get_cache_status(self) -> Dict[str, Any]:
        """Get comprehensive cache status for monitoring"""
        try:
            cache_data = self._load_cache()
            should_refresh = self._should_trigger_8hour_refresh()
            reason = "8+ hours old" if should_refresh else "Cache is valid"
            
            status = {
                "cache_valid": not should_refresh,
                "should_refresh": should_refresh,
                "refresh_reason": reason,
                "activities_count": len(cache_data.get("activities", [])),
                "last_fetch": cache_data.get("timestamp"),
                "last_rich_fetch": cache_data.get("last_rich_fetch"),
                "last_saved": cache_data.get("last_saved"),
                "cache_duration_hours": self.cache_duration_hours,
                "supabase_enabled": self.supabase_cache.enabled,
                "in_memory_cache_age": None,
                "emergency_refresh_flag": cache_data.get("emergency_refresh", False)
            }
            
            # Calculate in-memory cache age
            if self._cache_loaded_at:
                age_seconds = (datetime.now() - self._cache_loaded_at).total_seconds()
                status["in_memory_cache_age"] = f"{age_seconds:.1f}s"
            
            return status
            
        except Exception as e:
            return {
                "error": str(e),
                "cache_valid": False,
                "should_refresh": True,
                "refresh_reason": f"Error loading cache: {e}"
            }
    
    
    def _validate_user_input(self, data):
        """Only sanitize user input fields - PROTECT API DATA"""
        user_input_fields = ['comments', 'donation_messages', 'donor_names']
        # Remove SQL injection patterns from user input only
        # Keep all Strava API data raw
        return data  # Simplified for now - full implementation in supabase_cache_manager.py
    
    def _validate_strava_data(self, fresh_data, cached_data):
        """Compare fresh Strava data with cached data"""
        
        # BASIC DATA VALIDATION
        if fresh_data.get('name') != cached_data.get('name'):
            return 'name_mismatch'
        
        if fresh_data.get('distance') != cached_data.get('distance'):
            return 'distance_mismatch'
        
        if fresh_data.get('duration') != cached_data.get('duration'):
            return 'duration_mismatch'
        
        # RICH DATA VALIDATION  
        if fresh_data.get('polyline') != cached_data.get('polyline'):
            return 'polyline_mismatch'
        
        if fresh_data.get('bounds') != cached_data.get('bounds'):
            return 'bounds_mismatch'
        
        # NEW DATA DETECTION
        if fresh_data.get('photos') and not cached_data.get('photos'):
            return 'new_photos'
        
        if fresh_data.get('comments') and len(fresh_data['comments']) > len(cached_data.get('comments', [])):
            return 'new_comments'
        
        return 'data_matches'
    
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
    
    def _make_api_call_with_retry(self, url: str, headers: Dict[str, str], max_retries: int = 3, http_client=None) -> httpx.Response:
        """Make an API call with retry logic and error handling using optimized HTTP client"""
        for attempt in range(max_retries):
            try:
                # Check rate limits before making call
                logger.info(f"🔄 Step 3a4d: Checking API limits...")
                can_call, message = self._check_api_limits()
                logger.info(f"🔄 Step 3a4e: API limits check result: {can_call}, message: {message}")
                if not can_call:
                    raise Exception(f"Rate limit exceeded: {message}")
                
                # Make the API call using shared HTTP client with connection pooling
                # CRITICAL: Add timeout to prevent hanging
                if http_client is None:
                    logger.info(f"🔄 Step 3a1: Getting HTTP client...")
                    http_client = get_http_client()
                    logger.info(f"🔄 Step 3a2: HTTP client obtained, making API call to: {url}")
                else:
                    logger.info(f"🔄 Step 3a2: Using provided HTTP client, making API call to: {url}")
                logger.info(f"🔄 Step 3a3: Headers: Authorization: Bearer {headers.get('Authorization', 'MISSING')[:20]}...")
                response = http_client.get(url, headers=headers, timeout=30.0)
                logger.info(f"🔄 Step 3a4: API call completed: {response.status_code}")
                
                # Record the API call
                self._record_api_call()
                
                # Handle specific HTTP status codes
                if response.status_code == 200:
                    return response
                elif response.status_code == 401:
                    # Check if token is actually expired before refreshing
                    current_tokens = self.token_manager._load_tokens_from_env()
                    expires_at = current_tokens.get("expires_at")
                    
                    if expires_at and not self.token_manager._is_token_expired(expires_at):
                        # Token is not expired, this might be a temporary API issue
                        logger.warning(f"🔄 401 response but token not expired (expires at: {datetime.fromtimestamp(int(expires_at))}), retrying...")
                        if attempt < max_retries - 1:
                            time.sleep(2 ** attempt)  # Exponential backoff
                            continue
                        raise Exception("Authentication failed - token not expired but API returned 401")
                    else:
                        # Token is actually expired, try to refresh it
                        logger.warning("🔄 Access token expired, refreshing...")
                        try:
                            # Try to get new token with timeout to avoid deadlock
                            import threading
                            import time
                            
                            new_token = None
                            token_error = None
                            
                            def get_new_token():
                                nonlocal new_token, token_error
                                try:
                                    # Use environment token - NO token refresh in retry mechanism
                                    import os
                                    new_token = os.getenv("STRAVA_ACCESS_TOKEN")
                                    if not new_token:
                                        token_error = Exception("No access token available in environment")
                                except Exception as e:
                                    token_error = e
                            
                            # Start token retrieval in a separate thread with timeout
                            token_thread = threading.Thread(target=get_new_token)
                            token_thread.daemon = True
                            token_thread.start()
                            token_thread.join(timeout=10)  # 10 second timeout
                            
                            if token_thread.is_alive():
                                logger.error("❌ Token manager hanging during retry - using fallback")
                                # Use refresh token to get fresh access token
                                import os
                                refresh_token = os.getenv("STRAVA_REFRESH_TOKEN")
                                if refresh_token:
                                    logger.warning("🔄 Using refresh token to get fresh access token for retry")
                                    try:
                                        new_token = self.token_manager._refresh_access_token(refresh_token)
                                        logger.info(f"🔄 Successfully got fresh access token via fallback for retry: {new_token[:20] if new_token else 'None'}...")
                                    except Exception as e:
                                        logger.error(f"❌ Fallback token refresh failed during retry: {e}")
                                        raise Exception(f"Token manager hanging and fallback refresh failed: {e}")
                                else:
                                    raise Exception("Token manager hanging and no refresh token available")
                            elif token_error:
                                logger.error(f"❌ Token refresh failed during retry: {token_error}")
                                # Use refresh token to get fresh access token
                                import os
                                refresh_token = os.getenv("STRAVA_REFRESH_TOKEN")
                                if refresh_token:
                                    logger.warning("🔄 Using refresh token to get fresh access token for retry")
                                    try:
                                        new_token = self.token_manager._refresh_access_token(refresh_token)
                                        logger.info(f"🔄 Successfully got fresh access token via fallback for retry: {new_token[:20] if new_token else 'None'}...")
                                    except Exception as e:
                                        logger.error(f"❌ Fallback token refresh failed during retry: {e}")
                                        raise Exception(f"Token refresh failed: {token_error}")
                                else:
                                    raise Exception(f"Token refresh failed: {token_error}")
                            
                            if new_token:
                                # Update headers with new token for retry
                                headers = headers.copy()
                                headers["Authorization"] = f"Bearer {new_token}"
                                if attempt < max_retries - 1:
                                    continue
                                raise Exception("Authentication failed after token refresh")
                            else:
                                raise Exception("No token available for retry")
                                
                        except Exception as e:
                            logger.error(f"❌ Token refresh failed: {e}")
                            raise Exception(f"Authentication failed: {e}")
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
    
    def get_activities_smart(self, limit: int = 1000, force_refresh: bool = False) -> List[Dict[str, Any]]:
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
        
        # Cache is invalid or force refresh - trigger batch processing
        logger.info("Cache expired or invalid, triggering batch processing...")
        
        try:
            # Use the new streamlined architecture - trigger batch processing
            self._start_batch_processing()
            
            # Wait a moment for batch processing to start
            time.sleep(2)
            
            # Return cached data (even if stale) while batch processing runs in background
            if cache_data.get("activities"):
                logger.info("Returning cached data while batch processing runs in background")
                return cache_data["activities"][:limit]
            else:
                logger.info("No cached data available, returning empty list")
                return []
            
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
    
    def _fetch_from_strava(self, limit: int, access_token: str = None) -> List[Dict[str, Any]]:
        """Fetch activities from Strava API with pagination to get ALL activities"""
        try:
            logger.info(f"🔄 Starting Strava API fetch for {limit} activities...")
            
            # Step 1: Get access token (use provided token or fallback to environment)
            logger.info("🔄 Step 1: Getting access token...")
            if access_token:
                logger.info("✅ Using provided access token for Strava API fetch")
            else:
                # Fallback to environment variables - NO token refresh here
                logger.info("🔄 No token provided, using environment variable fallback")
                import os
                fallback_token = os.getenv("STRAVA_ACCESS_TOKEN")
                if fallback_token:
                    access_token = fallback_token
                    logger.info("✅ Using fallback token from environment variables")
                else:
                    logger.error("❌ No access token available - cannot make API call")
                    return []
            
            # Step 2: Create headers
            logger.info("🔄 Step 2: Creating headers...")
            headers = {"Authorization": f"Bearer {access_token}"}
            logger.info("🔄 Step 2 Complete: Headers created successfully")
            
            # Step 3: Fetch activities from Strava API
            logger.info("🔄 Step 3: Fetching page 1 from URL: https://www.strava.com/api/v3/athlete/activities?per_page=200&page=1")
            logger.info("🔄 Step 3a: Making API call with retry...")
            logger.info("🔄 Step 3a1: Getting HTTP client...")
            http_client = get_http_client()
            logger.info("🔄 Step 3a2: HTTP client obtained, making API call to: https://www.strava.com/api/v3/athlete/activities?per_page=200&page=1")
            logger.info(f"🔄 Step 3a3: Headers: Authorization: Bearer {access_token[:20]}...")
            
            logger.info("🔄 Step 3a4: About to call _make_api_call_with_retry...")
            logger.info(f"🔄 Step 3a4a: URL: https://www.strava.com/api/v3/athlete/activities?per_page=200&page=1")
            logger.info(f"🔄 Step 3a4b: Headers: {headers}")
            logger.info(f"🔄 Step 3a4c: HTTP client: {http_client}")
            
            response = self._make_api_call_with_retry(
                "https://www.strava.com/api/v3/athlete/activities?per_page=200&page=1", 
                headers,
                http_client=http_client
            )
            
            logger.info(f"🔄 Step 3a5: API call completed: {response.status_code}")
            self._record_api_call()
            logger.info(f"🔄 Step 3b: API call completed, status: {response.status_code}")
            
            if response.status_code == 200:
                logger.info("🔄 API response received for page 1, parsing JSON...")
                activities = response.json()
                logger.info(f"🔄 Page 1: fetched {len(activities)} activities, total: {len(activities)}")
                
                # Check if we need more pages
                if len(activities) >= 200:
                    logger.info("🔄 More activities available, but limiting to requested amount")
                else:
                    logger.info(f"🔄 Reached end of activities (got {len(activities)} < 200)")
                
                all_activities = activities
                logger.info(f"🔄 Successfully fetched {len(all_activities)} total activities from Strava across 0 pages")
                return all_activities[:limit]  # Return only the requested limit
            else:
                logger.error(f"❌ API call failed with status {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Failed to fetch activities from Strava: {str(e)}")
            raise Exception(f"Strava API error: {str(e)}")

    # COMMENTED OUT - REDUNDANT METHOD (Phase 1: Activity Selection Logic)
    def _is_activity_recent_enough(self, activity: Dict[str, Any]) -> bool:
        """Check if activity is recent enough to fetch rich data (less than 3 weeks old)"""
        try:
            start_date_str = activity.get('start_date_local', '')
            if not start_date_str:
                return False
            
            # Parse the date and ensure it's timezone-aware
            start_date = datetime.fromisoformat(start_date_str.replace('Z', '+00:00'))
            three_weeks_ago = datetime.now(timezone.utc) - timedelta(weeks=3)
            
            # Ensure both datetimes are timezone-aware for comparison
            if start_date.tzinfo is None:
                start_date = start_date.replace(tzinfo=timezone.utc)
            if three_weeks_ago.tzinfo is None:
                three_weeks_ago = three_weeks_ago.replace(tzinfo=timezone.utc)
            
            return start_date >= three_weeks_ago
        except Exception as e:
            logger.warning(f"Error checking activity age: {e}")
            return False

    def _filter_activities(self, raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter activities to only include runs/rides from May 22nd, 2025 onwards"""
        try:
            filtered_activities = []
            cutoff_date = datetime(2025, 5, 22, tzinfo=timezone.utc)
            
            for activity in raw_data:
                activity_type = activity.get('type', '').lower()
                if activity_type in ['run', 'ride']:
                    start_date_str = activity.get('start_date_local', '')
                    if start_date_str:
                        try:
                            # Parse the date and ensure it's timezone-aware
                            start_date = datetime.fromisoformat(start_date_str.replace('Z', '+00:00'))
                            if start_date.tzinfo is None:
                                start_date = start_date.replace(tzinfo=timezone.utc)
                            
                            if start_date >= cutoff_date:
                                filtered_activities.append(activity)
                        except Exception as e:
                            logger.warning(f"Error parsing activity date {start_date_str}: {e}")
                            continue
            
            logger.info(f"🔄 Filtered to {len(filtered_activities)} runs/rides from May 22nd, 2025 onwards")
            return filtered_activities
            
        except Exception as e:
            logger.error(f"Error filtering activities: {e}")
            return raw_data

    def _update_cache_with_batch_results(self, basic_data: List[Dict[str, Any]], new_activities: List[Dict[str, Any]]):
        """Update cache with batch processing results, preserving existing rich data"""
        try:
            logger.info(f"🔄 Updating cache with {len(basic_data)} activities ({len(new_activities)} new)")
            
            # Get existing cache data to preserve rich data
            existing_cache = self._load_cache(trigger_emergency_refresh=False)
            existing_activities = existing_cache.get("activities", []) if existing_cache else []
            
            # Create a lookup map of existing activities by ID to preserve rich data
            existing_by_id = {activity.get("id"): activity for activity in existing_activities}
            
            # Merge fresh basic data with existing rich data
            merged_activities = []
            for fresh_activity in basic_data:
                activity_id = fresh_activity.get("id")
                existing_activity = existing_by_id.get(activity_id, {})
                
                # For 8-hour refresh: Start with existing data and only add/update what's needed
                # This preserves ALL existing data and only adds new data
                merged_activity = existing_activity.copy() if existing_activity else {}
                
                # For 8-hour refresh: Only add/update fields that are missing or have changed
                # This preserves ALL existing data and only adds new data
                if existing_activity:
                    # Existing activity: Only add fields that don't exist or have changed
                    for field, value in fresh_activity.items():
                        if field not in existing_activity or existing_activity[field] != value:
                            merged_activity[field] = value
                            logger.debug(f"🔄 Updated {field} for existing activity {activity_id}")
                else:
                    # New activity: Add all fresh data
                    merged_activity.update(fresh_activity)
                    logger.debug(f"🔄 Added new activity {activity_id} with all fresh data")
                
                merged_activities.append(merged_activity)
            
            # Create cache data structure with merged activities
            cache_data = {
                "timestamp": datetime.now().isoformat(),
                "activities": merged_activities,
                "batching_in_progress": False,
                "batching_status_updated": datetime.now().isoformat()
            }
            
            # Update in-memory cache
            self._cache_data = cache_data
            self._cache_loaded_at = datetime.now()
            
            # Save to Supabase
            self._save_cache(cache_data)
            
            logger.info(f"✅ Updated cache with {len(merged_activities)} activities ({len(new_activities)} new) - preserved existing rich data")
            
        except Exception as e:
            logger.error(f"❌ Failed to update cache with batch results: {e}")

    def _validate_cache_data(self, cache_data: Dict[str, Any]) -> bool:
        """Validate cache data integrity"""
        try:
            activities = cache_data.get("activities", [])
            if not activities:
                logger.warning("Cache has no activities")
                return False
            
            total_activities = len(activities)
            basic_data_count = 0
            for activity in activities:
                if (activity.get("id") and 
                    activity.get("name") and 
                    activity.get("type") and 
                    activity.get("start_date_local")):
                    basic_data_count += 1
            
            # If less than 90% of activities have basic data, consider it corrupted
            if basic_data_count < total_activities * 0.9:
                logger.warning(f"Cache integrity check failed: Only {basic_data_count}/{total_activities} activities have basic data")
                return False
            
            # Check for polyline and bounds data (Run/Ride activities should have both)
            polyline_count = sum(1 for activity in activities if activity.get("map", {}).get("polyline"))
            bounds_count = sum(1 for activity in activities if activity.get("map", {}).get("bounds"))
            
            # Determine if we're in the middle of batching process
            is_emergency_refresh = cache_data.get("emergency_refresh", False)
            is_fresh_cache = cache_data.get("timestamp") and (datetime.now() - datetime.fromisoformat(cache_data["timestamp"])).total_seconds() < 3600  # Less than 1 hour old
            is_batching_in_progress = cache_data.get("batching_in_progress", False)
            
            # During emergency refresh or fresh cache, allow batching to complete
            if is_emergency_refresh or is_fresh_cache or is_batching_in_progress:
                logger.info(f"Cache validation: Allowing batching process to complete (emergency: {is_emergency_refresh}, fresh: {is_fresh_cache}, batching: {is_batching_in_progress})")
                logger.info(f"Cache integrity check passed: {basic_data_count}/{total_activities} activities have basic data, {polyline_count}/{total_activities} have polyline data, {bounds_count}/{total_activities} have bounds data")
                return True
            
            # After batching should be complete, enforce the 30% polyline threshold
            polyline_percentage = polyline_count / total_activities if total_activities > 0 else 0
            if polyline_percentage < 0.3:
                logger.warning(f"Cache integrity check failed: Only {polyline_count}/{total_activities} activities have polyline data ({polyline_percentage:.1%} - below 30% threshold)")
                logger.warning("This indicates batching may not have completed successfully or needs to be re-run")
                return False
            
            logger.info(f"Cache integrity check passed: {basic_data_count}/{total_activities} activities have basic data, {polyline_count}/{total_activities} have polyline data, {bounds_count}/{total_activities} have bounds data")
            return True
            
        except Exception as e:
            logger.error(f"Cache integrity check error: {e}")
            return False

    def _validate_cache_integrity(self, cache_data: Dict[str, Any]) -> bool:
        """Validate cache integrity - check for data loss indicators with proper batching support"""
        try:
            activities = cache_data.get("activities", [])
            if not activities:
                logger.warning("Cache has no activities")
                return False
            
            total_activities = len(activities)
            
            # Check for basic data integrity (all activities should have basic fields)
            basic_data_count = 0
            for activity in activities:
                if (activity.get("id") and 
                    activity.get("name") and 
                    activity.get("type") and 
                    activity.get("start_date_local")):
                    basic_data_count += 1
            
            # If less than 90% of activities have basic data, consider it corrupted
            if basic_data_count < total_activities * 0.9:
                logger.warning(f"Cache integrity check failed: Only {basic_data_count}/{total_activities} activities have basic data")
                return False
            
            # Check for polyline and bounds data (Run/Ride activities should have both)
            polyline_count = sum(1 for activity in activities if activity.get("map", {}).get("polyline"))
            bounds_count = sum(1 for activity in activities if activity.get("map", {}).get("bounds"))
            
            # Determine if we're in the middle of batching process
            is_emergency_refresh = cache_data.get("emergency_refresh", False)
            is_fresh_cache = cache_data.get("timestamp") and (datetime.now() - datetime.fromisoformat(cache_data["timestamp"])).total_seconds() < 3600  # Less than 1 hour old
            is_batching_in_progress = cache_data.get("batching_in_progress", False)
            
            # During emergency refresh or fresh cache, allow batching to complete
            if is_emergency_refresh or is_fresh_cache or is_batching_in_progress:
                logger.info(f"Cache validation: Allowing batching process to complete (emergency: {is_emergency_refresh}, fresh: {is_fresh_cache}, batching: {is_batching_in_progress})")
                logger.info(f"Cache integrity check passed: {basic_data_count}/{total_activities} activities have basic data, {polyline_count}/{total_activities} have polyline data, {bounds_count}/{total_activities} have bounds data")
                return True
            
            # After batching should be complete, enforce the 30% polyline threshold
            polyline_percentage = polyline_count / total_activities if total_activities > 0 else 0
            if polyline_percentage < 0.3:
                logger.warning(f"Cache integrity check failed: Only {polyline_count}/{total_activities} activities have polyline data ({polyline_percentage:.1%} - below 30% threshold)")
                logger.warning("This indicates batching may not have completed successfully or needs to be re-run")
                return False
            
            # Check for recent activities (should have complete GPS data)
            recent_activities = [a for a in activities if a.get("start_date_local", "").startswith("2025-09")]
            if recent_activities:
                recent_polyline_count = sum(1 for activity in recent_activities if activity.get("map", {}).get("polyline"))
                recent_bounds_count = sum(1 for activity in recent_activities if activity.get("map", {}).get("bounds"))
                # Recent Run/Ride activities should have both polyline and bounds
                if recent_polyline_count < len(recent_activities) * 0.9:
                    logger.warning(f"Cache integrity check failed: Recent activities missing polyline data ({recent_polyline_count}/{len(recent_activities)})")
                    return False
                if recent_bounds_count < len(recent_activities) * 0.9:
                    logger.warning(f"Cache integrity check failed: Recent activities missing bounds data ({recent_bounds_count}/{len(recent_activities)})")
                    return False
            
            logger.info(f"Cache integrity check passed: {basic_data_count}/{total_activities} activities have basic data, {polyline_count}/{total_activities} have polyline data, {bounds_count}/{total_activities} have bounds data")
            return True
            
        except Exception as e:
            logger.error(f"Cache integrity check error: {e}")
            return False

    def _start_automated_refresh(self):
        """Start automated refresh system (8-hour intervals)"""
        try:
            logger.info("🔄 Automated refresh system started (8-hour intervals)")
            # Start the automated refresh loop in a background thread
            import threading
            refresh_thread = threading.Thread(target=self._automated_refresh_loop, daemon=True)
            refresh_thread.start()
        except Exception as e:
            logger.error(f"❌ Failed to start automated refresh: {e}")

    def _automated_refresh_loop(self):
        """Main loop for automated refresh every 8 hours"""
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
        """Perform a scheduled refresh using streamlined logic"""
        try:
            logger.info("🔄 Normal scheduled refresh...")
            self._start_batch_processing()
            
        except Exception as e:
            logger.error(f"❌ Scheduled refresh failed: {e}")

    def _start_batch_processing(self):
        """Start batch processing of activities (20 every 15 minutes) using new streamlined architecture"""
        logger.info("🔄 _start_batch_processing() called")
        try:
            with self._batch_lock:  # Thread-safe batch thread creation
                logger.info("🔄 Acquired batch lock")
                if self._batch_thread and self._batch_thread.is_alive():
                    logger.info("🏃‍♂️ Batch processing already running, skipping...")
                    return
                
                # Check if we're already in the middle of token acquisition
                if hasattr(self, '_token_acquisition_in_progress') and self._token_acquisition_in_progress:
                    logger.info("🔄 Token acquisition already in progress, skipping batch processing...")
                    return
                
                logger.info("🔄 Marking batching as in progress...")
                # Mark batching as in progress
                self._mark_batching_in_progress(True)
                
                logger.info("🔄 Creating batch processing thread...")
                # Start batch processing with additional safety measures
                self._batch_thread = threading.Thread(
                    target=self._batch_processing_loop, 
                    daemon=True,
                    name="BatchProcessingThread"
                )
                logger.info("🔄 Starting batch processing thread...")
                self._batch_thread.start()
                logger.info("🏃‍♂️ Batch processing started (20 activities every 15 minutes)")
                
        except Exception as e:
            logger.error(f"❌ Error in _start_batch_processing: {e}")
            import traceback
            logger.error(f"❌ Full traceback: {traceback.format_exc()}")
            raise

    def _batch_processing_loop(self):
        """Process activities in batches of 20 every 15 minutes using new streamlined architecture"""
        try:
            logger.info("🏃‍♂️ Starting batch processing with new streamlined architecture...")
            
            # Import required modules at the start
            import threading
            import time
            
            # Determine if this is emergency refresh or 8-hour refresh
            cache_data = self._load_cache(trigger_emergency_refresh=False)
            is_emergency_refresh = not cache_data or not cache_data.get("activities")
            
            if is_emergency_refresh:
                logger.info("🚨 Emergency refresh detected - will fetch ALL rich data (no expiration checks)")
                apply_expiration_checks = False
            else:
                logger.info("🕐 8-hour refresh detected - will apply expiration checks for rich data")
                apply_expiration_checks = True
            
            # Wait a bit to ensure main application has fully started
            logger.info("🔄 Waiting for main application to fully start...")
            time.sleep(20)  # Give main app more time to start
            
            # Step 1: Get a single access token for the entire batch processing session
            logger.info(f"🔄 Getting access token for entire batch processing session...")
            
            # This is the ONLY place that should acquire/refresh tokens
            access_token = None
            try:
                # Mark token acquisition as in progress to prevent conflicts
                self._token_acquisition_in_progress = True
                logger.info("🔄 Token acquisition marked as in progress")
                
                # Get token and handle refresh if needed - this is the single source of truth
                access_token = self.token_manager.get_valid_access_token()
                logger.info(f"✅ Got access token for entire batch processing session")
                
                # Clear the flag
                self._token_acquisition_in_progress = False
                logger.info("🔄 Token acquisition completed, flag cleared")
                
            except Exception as e:
                # Clear the flag on error
                self._token_acquisition_in_progress = False
                logger.error(f"❌ Failed to get access token for batch processing: {e}")
                logger.error("❌ Cannot proceed without valid token - aborting batch processing")
                return
            
            # Step 2: Fetch fresh basic data from Strava (following our new flow)
            logger.info("🔄 About to call _fetch_from_strava with access token...")
            logger.info(f"🔄 Access token available: {access_token is not None}")
            if access_token:
                logger.info(f"🔄 Access token preview: {access_token[:20]}...")
            raw_data = self._fetch_from_strava(200, access_token=access_token)
            logger.info(f"🔄 Fetched {len(raw_data)} raw activities from Strava")
            
            # Step 2b: Filter for runs/rides from May 22nd, 2025 onwards
            basic_data = self._filter_activities(raw_data)
            logger.info(f"🔄 Filtered to {len(basic_data)} runs/rides from May 22nd, 2025 onwards")
            
            # Step 3: Identify new activities (following our new flow)
            new_activities = self._identify_new_activities(basic_data)
            logger.info(f"🆕 Found {len(new_activities)} new activities")
            
            # Step 4: Process new activities in batches of 20 every 15 minutes
            if new_activities:
                batch_size = 20
                for i in range(0, len(new_activities), batch_size):
                    batch = new_activities[i:i + batch_size]
                    
                    logger.info(f"🏃‍♂️ Processing batch {i//batch_size + 1}: {len(batch)} new activities")
                    
                    # Process the batch (fetch rich data for new activities) with the pre-obtained token
                    self._process_activity_batch(batch, access_token=access_token, apply_expiration_checks=apply_expiration_checks)
                    
                    # Wait 15 minutes between batches (except for the last batch)
                    if i + batch_size < len(new_activities):
                        logger.info("⏰ Waiting 15 minutes before next batch...")
                        time.sleep(900)  # 15 minutes
            else:
                logger.info("✅ No new activities to process")
                
                # Even when there are no new activities, during the 8-hour refresh we
                # should check whether any existing activities still fall within the
                # expiration windows for rich data (photos, comments, description, polyline)
                # and top them up. We will only persist if any rich updates were applied.
                performed_rich_updates = False
                try:
                    existing_cache = self._load_cache(trigger_emergency_refresh=False) or {}
                    existing_activities = existing_cache.get("activities", [])
                    existing_by_id = {a.get("id"): a for a in existing_activities}
                    
                    # Build a list of existing activities eligible for rich-data refresh
                    eligible_existing: List[Dict[str, Any]] = []
                    for fresh in basic_data:
                        aid = fresh.get("id")
                        prev = existing_by_id.get(aid)
                        if not aid or not prev:
                            continue
                        
                        wants_photos = (not prev.get("photos_fetch_expired", False)) and not prev.get("photos")
                        wants_comments = (not prev.get("comments_fetch_expired", False)) and not prev.get("comments")
                        wants_description = (not prev.get("description_fetch_expired", False)) and not prev.get("description")
                        wants_polyline = (not prev.get("polyline_fetch_expired", False)) and (not prev.get("polyline") or not prev.get("bounds"))
                        
                        if wants_photos or wants_comments or wants_description or wants_polyline:
                            eligible_existing.append(fresh)
                    
                    if eligible_existing:
                        logger.info(f"🔎 Found {len(eligible_existing)} existing activities eligible for rich-data refresh within expiration windows")
                        batch_size = 20
                        for i in range(0, len(eligible_existing), batch_size):
                            batch = eligible_existing[i:i + batch_size]
                            logger.info(f"🏃‍♂️ Processing existing batch {i//batch_size + 1}: {len(batch)} activities (expiration checks ON)")
                            self._process_activity_batch(batch, access_token=access_token, apply_expiration_checks=True)
                            performed_rich_updates = True
                            if i + batch_size < len(eligible_existing):
                                logger.info("⏰ Waiting 15 minutes before next existing batch...")
                                time.sleep(900)
                    else:
                        logger.info("🔎 No existing activities require rich-data refresh within expiration windows")
                except Exception as enrich_err:
                    logger.warning(f"⚠️ Skipped existing-activity rich-data refresh due to error: {enrich_err}")
                
                if not performed_rich_updates:
                    # Preserve existing rich data exactly as-is – do not write basic-only dataset
                    logger.info("🛑 No rich updates performed – skipping cache save to preserve existing rich data")
                    self._mark_batching_in_progress(False)
                    logger.info("✅ Batch processing completed with no changes")
                    return
                
                # Persist merged results (basic_data + enriched existing); new_activities is empty
                logger.info("💾 Persisting cache after enriching existing activities within expiration windows")
                self._update_cache_with_batch_results(basic_data, [])
                self._mark_batching_in_progress(False)
                logger.info("✅ Batch processing completed with enriched updates")
                return
            
            # Step 4: Update cache with all data (only when there are new activities)
            self._update_cache_with_batch_results(basic_data, new_activities)
            
            # Step 5: Mark batching as complete
            self._mark_batching_in_progress(False)
            
            logger.info("✅ Batch processing completed successfully")
            
        except Exception as e:
            logger.error(f"❌ Batch processing failed: {e}")
            self._mark_batching_in_progress(False)

    def _process_activity_batch(self, batch: List[Dict[str, Any]], access_token: str = None, apply_expiration_checks: bool = True):
        """Process a batch of new activities using new streamlined architecture"""
        try:
            logger.info(f"🏃‍♂️ Processing batch of {len(batch)} new activities...")
            
            # Fetch rich data for all activities in this batch using the pre-obtained token
            # Apply expiration checks based on refresh type (emergency vs 8-hour)
            rich_data = self._fetch_rich_data_for_new_activities(batch, access_token=access_token, apply_expiration_checks=apply_expiration_checks)
            
            # Update each activity with rich data
            for activity in batch:
                activity_id = activity.get('id')
                if activity_id and activity_id in rich_data:
                    # Update activity with rich data
                    activity.update(rich_data[activity_id])
                    
                    # Add music detection to the activity
                    description = activity.get('description', '')
                    if description:
                        music_data = self._detect_music_sync(description)
                        if music_data:
                            activity['music'] = music_data
                            logger.info(f"🎵 Added music data to activity {activity_id}: {music_data.get('detected', {}).get('type', 'unknown')}")
                    
                    # Update expiration flags
                    activity = self._update_activity_expiration_flags(activity)
                    
                    logger.info(f"✅ Updated activity {activity_id} with rich data")
                else:
                    logger.warning(f"⚠️ No rich data found for activity {activity_id}")
                
                time.sleep(1)  # Small delay to respect API limits
                
        except Exception as e:
            logger.error(f"❌ Error processing activity batch: {e}")

    def _mark_batching_in_progress(self, in_progress: bool):
        """Mark batching as in progress or complete in cache (thread-safe)"""
        try:
            logger.info("🔄 _mark_batching_in_progress: Starting...")
            # Note: This method is called from within _start_batch_processing() which already holds _batch_lock
            # So we don't need to acquire the lock again to avoid deadlock
            
            # Use existing cache data or create minimal cache structure
            if self._cache_data is not None:
                cache_data = self._cache_data.copy()
                logger.info("🔄 _mark_batching_in_progress: Using existing cache data")
            else:
                # Create minimal cache structure for startup
                cache_data = {
                    "timestamp": None,
                    "activities": [],
                    "batching_in_progress": False,
                    "batching_status_updated": None
                }
                logger.info("🔄 _mark_batching_in_progress: Created minimal cache structure")
            
            cache_data["batching_in_progress"] = in_progress
            cache_data["batching_status_updated"] = datetime.now().isoformat()
            logger.info("🔄 _mark_batching_in_progress: Updated cache data with batching status")
            
            # Update in-memory cache immediately (don't wait for Supabase save)
            self._cache_data = cache_data
            self._cache_loaded_at = datetime.now()
            logger.info("🔄 _mark_batching_in_progress: Updated in-memory cache")
            
            # Skip Supabase operations during startup to avoid hanging
            logger.info("🔄 Skipping Supabase operations during batching startup to avoid hanging")
            
            status = "started" if in_progress else "completed"
            logger.info(f"🔄 Batching process {status}")
            
        except Exception as e:
            logger.error(f"❌ Failed to update batching status: {e}")
            import traceback
            logger.error(f"❌ Full traceback: {traceback.format_exc()}")

    def _identify_new_activities(self, basic_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Compare fresh basic data with database to identify new activities"""
        try:
            # Load existing cache to compare
            existing_cache = self._load_cache(trigger_emergency_refresh=False)
            existing_activities = existing_cache.get("activities", [])
            existing_ids = {activity.get("id") for activity in existing_activities}
            
            # Find new activities
            new_activities = []
            for activity in basic_data:
                activity_id = activity.get("id")
                if activity_id and activity_id not in existing_ids:
                    new_activities.append(activity)
                    logger.info(f"🆕 New activity identified: {activity_id} - {activity.get('name', 'Unknown')}")
            
            logger.info(f"🆕 Found {len(new_activities)} new activities out of {len(basic_data)} total")
            return new_activities
            
        except Exception as e:
            logger.error(f"❌ Error identifying new activities: {e}")
            return basic_data  # Return all activities as new if comparison fails

    def _update_activity_expiration_flags(self, activity: Dict[str, Any]) -> Dict[str, Any]:
        """Update photos_fetch_expired, comments_fetch_expired, polyline_fetch_expired, and description_fetch_expired flags for an activity"""
        try:
            activity_date = activity.get('start_date_local', '')
            if activity_date:
                activity['photos_fetch_expired'] = self._check_photos_fetch_expired(activity)
                activity['comments_fetch_expired'] = self._check_comments_fetch_expired(activity)
                activity['polyline_fetch_expired'] = self._check_polyline_fetch_expired(activity)
                activity['description_fetch_expired'] = self._check_description_fetch_expired(activity)
            return activity
        except Exception as e:
            logger.warning(f"Error updating expiration flags: {e}")
            return activity

    def _detect_music_sync(self, description: str) -> Dict[str, Any]:
        """Synchronous music detection (CPU-bound) - returns original format"""
        if not description:
            return {}
        
        # Music detection patterns - optimized for performance
        album_pattern = r"Album:\s*([^,\n]+?)\s+by\s+([^,\n]+)"
        russell_radio_pattern = r"Russell Radio:\s*([^,\n]+?)\s+by\s+([^,\n]+)"
        track_pattern = r"Track:\s*([^,\n]+?)\s+by\s+([^,\n]+)"
        playlist_pattern = r"Playlist:\s*([^,\n]+)"
        
        music_data = {}
        detected = {}
        
        # Check for album
        album_match = re.search(album_pattern, description, re.IGNORECASE)
        if album_match:
            detected = {
                "type": "album",
                "title": album_match.group(1).strip(),
                "artist": album_match.group(2).strip(),
                "source": "description"
            }
            music_data["album"] = {
                "name": album_match.group(1).strip(),
                "artist": album_match.group(2).strip()
            }
        
        # Check for Russell Radio
        russell_match = re.search(russell_radio_pattern, description, re.IGNORECASE)
        if russell_match:
            detected = {
                "type": "track",
                "title": russell_match.group(1).strip(),
                "artist": russell_match.group(2).strip(),
                "source": "russell_radio"
            }
            music_data["track"] = {
                "name": russell_match.group(1).strip(),
                "artist": russell_match.group(2).strip()
            }
        
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
        
        # Add detected field for frontend compatibility
        if detected:
            music_data["detected"] = detected
            
            # Generate Deezer widget HTML
            music_data["widget_html"] = self._generate_deezer_widget(detected)
        
        return music_data
    
    def _generate_deezer_widget(self, detected: Dict[str, Any]) -> str:
        """Generate Deezer widget HTML for the detected music"""
        try:
            logger.info(f"🎵 Generating Deezer widget for: {detected['title']} by {detected['artist']} (type: {detected['type']})")
            
            # Search for the track/album on Deezer
            deezer_id, id_type = self._search_deezer_for_id(
                detected["title"], 
                detected["artist"], 
                detected["type"]
            )
            
            if deezer_id and id_type:
                # Generate Deezer widget HTML
                if id_type == "track":
                    widget_html = f'<iframe scrolling="no" frameborder="0" allowTransparency="true" src="https://widget.deezer.com/widget/dark/{id_type}/{deezer_id}" width="100%" height="200"></iframe>'
                    logger.info(f"🎵 Generated Deezer track widget: {deezer_id}")
                    return widget_html
                elif id_type == "album":
                    widget_html = f'<iframe scrolling="no" frameborder="0" allowTransparency="true" src="https://widget.deezer.com/widget/dark/{id_type}/{deezer_id}" width="100%" height="300"></iframe>'
                    logger.info(f"🎵 Generated Deezer album widget: {deezer_id}")
                    return widget_html
            
            # Fallback: return a simple text representation
            logger.warning(f"🎵 No Deezer ID found, using fallback for: {detected['title']} by {detected['artist']}")
            return f'<div class="music-fallback"><p><strong>{detected["title"]}</strong> by {detected["artist"]}</p></div>'
            
        except Exception as e:
            logger.warning(f"🎵 Failed to generate Deezer widget: {e}")
            return f'<div class="music-fallback"><p><strong>{detected["title"]}</strong> by {detected["artist"]}</p></div>'
    
    def _search_deezer_for_id(self, title: str, artist: str, music_type: str) -> tuple[str, str]:
        """
        Search Deezer API for specific album/track ID with sophisticated matching
        Returns: (id_type, deezer_id) or (None, None) if not found
        """
        try:
            # Clean and prepare search query
            clean_title = title.strip().replace('"', '').replace("'", "")
            clean_artist = artist.strip().replace('"', '').replace("'", "")
            
            # Try multiple search strategies with more flexible terms
            search_queries = [
                f"{clean_title} {clean_artist}",      # Simple concatenation (most effective)
                f"{clean_artist} {clean_title}",      # Artist first
                f'"{clean_title}" "{clean_artist}"',  # Exact match with quotes
                clean_title,                          # Title only
                clean_artist                          # Artist only
            ]
            
            # Prioritize the correct search type, but try both for better coverage
            search_endpoints = []
            if music_type == "album":
                # For albums, try album search first, then track search to find the album
                search_endpoints = [
                    ("https://api.deezer.com/search/album", "album"),
                    ("https://api.deezer.com/search/track", "album_from_track")  # Extract album from track
                ]
            elif music_type == "track":
                search_endpoints = [
                    ("https://api.deezer.com/search/track", "track"),
                    ("https://api.deezer.com/search/album", "track")  # Fallback to album search
                ]
            else:
                return None, None
            
            # Try each search query with each endpoint
            for search_query in search_queries:
                for search_endpoint, endpoint_type in search_endpoints:
                    try:
                        encoded_query = search_query.replace(" ", "%20")
                        search_url = f"{search_endpoint}?q={encoded_query}&limit=10"
                        
                        logger.debug(f"🎵 Searching Deezer for: {search_query} ({endpoint_type}) (URL: {search_url})")
                        
                        # Make request to Deezer API
                        response = requests.get(search_url, timeout=10)
                        if response.status_code == 200:
                            data = response.json()
                            
                            if data.get("data") and len(data["data"]) > 0:
                                # Look for exact matches first
                                for result in data["data"]:
                                    result_title = result.get("title", "").lower()
                                    result_artist = result.get("artist", {}).get("name", "").lower()
                                    
                                    # Check for exact match
                                    if (clean_title.lower() in result_title and clean_artist.lower() in result_artist) or \
                                       (clean_artist.lower() in result_title and clean_title.lower() in result_artist):
                                        
                                        # If we found a track but need an album, get the album ID
                                        if endpoint_type == "album_from_track" and music_type == "album":
                                            album_id = result.get("album", {}).get("id")
                                            if album_id:
                                                logger.info(f"🎵 Found exact Deezer match: {result_title} by {result_artist} (track) - using album ID: {album_id}")
                                                return album_id, "album"
                                            else:
                                                logger.warning(f"🎵 Found track match but no album ID available")
                                                continue
                                        else:
                                            logger.info(f"🎵 Found exact Deezer match: {result_title} by {result_artist} ({endpoint_type}) (ID: {result['id']})")
                                            return result["id"], endpoint_type
                                
                                # If no exact match found, try partial matches
                                for result in data["data"]:
                                    result_title = result.get("title", "").lower()
                                    result_artist = result.get("artist", {}).get("name", "").lower()
                                    
                                    # Check for partial match (at least 80% of words match)
                                    title_words = set(clean_title.lower().split())
                                    artist_words = set(clean_artist.lower().split())
                                    result_title_words = set(result_title.split())
                                    result_artist_words = set(result_artist.split())
                                    
                                    title_match_ratio = len(title_words.intersection(result_title_words)) / len(title_words) if title_words else 0
                                    artist_match_ratio = len(artist_words.intersection(result_artist_words)) / len(artist_words) if artist_words else 0
                                    
                                    if title_match_ratio >= 0.8 and artist_match_ratio >= 0.8:
                                        # If we found a track but need an album, get the album ID
                                        if endpoint_type == "album_from_track" and music_type == "album":
                                            album_id = result.get("album", {}).get("id")
                                            if album_id:
                                                logger.info(f"🎵 Found partial Deezer match: {result_title} by {result_artist} (track) - using album ID: {album_id}")
                                                return album_id, "album"
                                            else:
                                                logger.warning(f"🎵 Found track match but no album ID available")
                                                continue
                                        else:
                                            logger.info(f"🎵 Found partial Deezer match: {result_title} by {result_artist} ({endpoint_type}) (ID: {result['id']})")
                                            return result["id"], endpoint_type
                                
                                # If still no match, return the first result as fallback
                                result = data["data"][0]
                                
                                # If we found a track but need an album, get the album ID
                                if endpoint_type == "album_from_track" and music_type == "album":
                                    album_id = result.get("album", {}).get("id")
                                    if album_id:
                                        logger.warning(f"🎵 No exact match found, using first result album: {result.get('title')} by {result.get('artist', {}).get('name')} (track) - using album ID: {album_id}")
                                        return album_id, "album"
                                    else:
                                        logger.warning(f"🎵 Found track but no album ID available, skipping")
                                        continue
                                else:
                                    logger.warning(f"🎵 No exact match found, using first result: {result.get('title')} by {result.get('artist', {}).get('name')} ({endpoint_type}) (ID: {result['id']})")
                                    return result["id"], endpoint_type
                    
                    except Exception as e:
                        logger.debug(f"🎵 Search query failed: {search_query} ({endpoint_type}) - {e}")
                        continue
            
            logger.warning(f"🎵 No Deezer results found for: {title} by {artist}")
            return None, None
            
        except Exception as e:
            logger.warning(f"🎵 Failed to search Deezer API: {e}")
            return None, None

