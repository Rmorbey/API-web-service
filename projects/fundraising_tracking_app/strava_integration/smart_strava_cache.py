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
            return True  # No cache data, trigger refresh
        
        last_fetch = cache_data.get('last_fetch')
        if not last_fetch:
            return True  # No last_fetch timestamp, trigger refresh
        
        try:
            last_fetch_time = datetime.fromisoformat(last_fetch)
            time_since_fetch = datetime.now() - last_fetch_time
            return time_since_fetch >= timedelta(hours=8)
        except Exception as e:
            logger.warning(f"Error parsing last_fetch timestamp: {e}")
            return True  # If parsing fails, trigger refresh
    
    def _identify_new_activities(self, basic_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Compare fresh basic data with database to identify new activities"""
        cache_data = self._load_cache(trigger_emergency_refresh=False)
        if not cache_data:
            return basic_data  # No existing data, all activities are new
        
        existing_activities = cache_data.get("activities", [])
        existing_ids = {activity.get("id") for activity in existing_activities}
        
        new_activities = []
        for activity in basic_data:
            activity_id = activity.get("id")
            if activity_id not in existing_ids:
                new_activities.append(activity)
                logger.info(f"🆕 New activity identified: {activity_id} - {activity.get('name', 'Unknown')}")
        
        logger.info(f"🆕 Found {len(new_activities)} new activities out of {len(basic_data)} total")
        return new_activities
    
    def _fetch_rich_data_for_new_activities(self, new_activities: List[Dict[str, Any]], access_token: str = None) -> Dict[int, Dict[str, Any]]:
        """Fetch rich data (photos + comments) only for new activities"""
        rich_data = {}
        
        # Use provided token or get a new one (fallback for backward compatibility)
        if not access_token:
            try:
                logger.info(f"🔄 Getting access token for batch of {len(new_activities)} activities...")
                # Use a more reliable token acquisition approach
                access_token = self.token_manager.get_valid_access_token()
                logger.info(f"✅ Got access token for batch processing")
            except Exception as e:
                logger.error(f"❌ Failed to get access token for batch: {e}")
                logger.warning("⚠️ Continuing without rich data - will use fallback token from environment")
                # Try to use fallback token from environment
                try:
                    import os
                    fallback_token = os.getenv("STRAVA_ACCESS_TOKEN")
                    if fallback_token:
                        access_token = fallback_token
                        logger.info("🔄 Using fallback token from environment variables")
                    else:
                        logger.error("❌ No fallback token available")
                        # Return empty rich data for all activities
                        for activity in new_activities:
                            activity_id = activity.get("id")
                            if activity_id:
                                rich_data[activity_id] = {"photos": {}, "comments": []}
                        return rich_data
                except Exception as fallback_error:
                    logger.error(f"❌ Fallback token acquisition failed: {fallback_error}")
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
                
                # Fetch photos and comments using the pre-obtained token
                photos_data = self._fetch_activity_photos(activity_id, access_token=access_token)
                comments_data = self._fetch_activity_comments(activity_id, access_token=access_token)
                
                rich_data[activity_id] = {
                    "photos": photos_data,
                    "comments": comments_data
                }
                
                logger.info(f"✅ Successfully fetched rich data for activity {activity_id}")
                
            except Exception as e:
                logger.warning(f"⚠️ Failed to fetch rich data for activity {activity_id}: {e}")
                rich_data[activity_id] = {
                    "photos": {},
                    "comments": []
                }
        
        return rich_data
    
    def _fetch_rich_data_for_all_activities(self) -> Dict[int, Dict[str, Any]]:
        """Fetch rich data for ALL activities (used in daily corruption check)"""
        cache_data = self._load_cache(trigger_emergency_refresh=False)
        if not cache_data:
            return {}
        
        activities = cache_data.get("activities", [])
        rich_data = {}
        
        # Get a single token for the entire batch to avoid deadlocks
        try:
            logger.info(f"🔄 Getting access token for corruption check of {len(activities)} activities...")
            access_token = self.token_manager.get_valid_access_token()
            logger.info(f"✅ Got access token for corruption check")
        except Exception as e:
            logger.error(f"❌ Failed to get access token for corruption check: {e}")
            # Return empty rich data for all activities
            for activity in activities:
                activity_id = activity.get("id")
                if activity_id:
                    rich_data[activity_id] = {"photos": {}, "comments": []}
            return rich_data
        
        for activity in activities:
            activity_id = activity.get("id")
            if not activity_id:
                continue
            
            try:
                logger.info(f"🔄 Fetching rich data for activity {activity_id} (corruption check)")
                
                # Fetch photos and comments using the pre-obtained token
                photos_data = self._fetch_activity_photos(activity_id, access_token=access_token)
                comments_data = self._fetch_activity_comments(activity_id, access_token=access_token)
                
                rich_data[activity_id] = {
                    "photos": photos_data,
                    "comments": comments_data
                }
                
            except Exception as e:
                logger.warning(f"⚠️ Failed to fetch rich data for activity {activity_id}: {e}")
                rich_data[activity_id] = {
                    "photos": {},
                    "comments": []
                }
        
        return rich_data
    
    def _fetch_rich_data_for_all_activities_with_batching(self, basic_data: List[Dict[str, Any]]) -> Dict[int, Dict[str, Any]]:
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
            batch_rich_data = self._fetch_rich_data_for_new_activities(batch)
            rich_data.update(batch_rich_data)
            
            logger.info(f"✅ Completed batch {batch_num}/{total_batches}: {len(batch_rich_data)} activities with rich data")
            
            # Wait 15 minutes between batches (except for the last batch)
            if i + batch_size < len(basic_data):
                logger.info("⏰ Waiting 15 minutes before next batch...")
                time.sleep(900)  # 15 minutes
        
        logger.info(f"✅ Batch processing completed: {len(rich_data)} activities with rich data")
        return rich_data
    
    def _check_photo_fetch_expired(self, activity_date: str) -> bool:
        """Check if photo fetching should be skipped (24+ hours after activity date)"""
        try:
            activity_dt = datetime.fromisoformat(activity_date.replace('Z', '+00:00'))
            time_since_activity = datetime.now(timezone.utc) - activity_dt
            return time_since_activity >= timedelta(hours=24)
        except Exception as e:
            logger.warning(f"Error parsing activity date {activity_date}: {e}")
            return False  # If parsing fails, don't skip
    
    def _check_comments_fetch_expired(self, activity_date: str) -> bool:
        """Check if comments fetching should be skipped (168+ hours after activity date)"""
        try:
            activity_dt = datetime.fromisoformat(activity_date.replace('Z', '+00:00'))
            time_since_activity = datetime.now(timezone.utc) - activity_dt
            return time_since_activity >= timedelta(hours=168)  # 1 week
        except Exception as e:
            logger.warning(f"Error parsing activity date {activity_date}: {e}")
            return False  # If parsing fails, don't skip
    
    def _update_activity_expiration_flags(self, activity: Dict[str, Any]) -> Dict[str, Any]:
        """Update photos_fetch_expired and comments_fetch_expired flags for an activity"""
        activity_date = activity.get('start_date', '')
        if not activity_date:
            return activity
        
        activity['photos_fetch_expired'] = self._check_photo_fetch_expired(activity_date)
        activity['comments_fetch_expired'] = self._check_comments_fetch_expired(activity_date)
        activity['strava_activity_date'] = activity_date
        
        return activity
    
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
        """Execute daily corruption check at 2am using batch processing"""
        logger.info("🕐 Starting daily corruption check...")
        
        try:
            # Ensure fresh tokens
            self.token_manager.get_valid_access_token()
            
            # Step 1: Fetch fresh basic data (1 API call - fine to do all at once)
            raw_data = self._fetch_from_strava(200)
            logger.info(f"🔄 Fetched {len(raw_data)} raw activities for corruption check")
            
            # Step 1b: Filter for runs/rides from May 22nd, 2025 onwards
            basic_data = self._filter_activities(raw_data)
            logger.info(f"🔄 Filtered to {len(basic_data)} runs/rides from May 22nd, 2025 onwards")
            
            # Step 2: Fetch rich data for ALL activities using batch processing
            rich_data = self._fetch_rich_data_for_all_activities_with_batching(basic_data)
            logger.info(f"🔄 Fetched rich data for {len(rich_data)} activities using batch processing")
            
            # Step 3: Compare fresh vs database data
            corruption_analysis = self._compare_fresh_vs_database_data(basic_data, rich_data)
            
            if corruption_analysis["corruption_detected"]:
                logger.warning(f"🚨 Corruption detected in {corruption_analysis['corrupted_count']} activities")
                # TODO: Implement data overwrite with fresh data
            else:
                logger.info("✅ No corruption detected in daily check")
            
            # Step 4: Update metadata
            current_time = datetime.now().isoformat()
            cache_data = self._load_cache(trigger_emergency_refresh=False)
            if cache_data:
                cache_data['last_fetch'] = current_time
                cache_data['last_basic_data_updated'] = current_time
                cache_data['last_rich_data_updated'] = current_time
                self._save_cache(cache_data)
            
            logger.info("✅ Daily corruption check completed")
            
        except Exception as e:
            logger.error(f"❌ Daily corruption check failed: {e}")
    
    def check_and_refresh(self):
        """Main entry point - single condition check for all refresh scenarios"""
        cache_data = self._load_cache()
        
        # SINGLE CONDITION: Empty database OR 8+ hours old
        if (not cache_data or 
            not cache_data.get("activities") or 
            self._should_trigger_8hour_refresh()):
            
            logger.info("🏃‍♂️ Starting batch processing")
            self._start_batch_processing()
            return
        
        logger.info("🏃‍♂️ Cache is valid - no refresh needed")
    
    
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
    
    def _filter_activities(self, activities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter activities based on type and date"""
        filtered = []
        
        for activity in activities:
            # Filter by activity type
            if activity.get("type") not in self.allowed_activity_types:
                continue
            
            # Filter out invalid/unknown activities
            if activity.get("name") == "Unknown Activity" or activity.get("type") == "Unknown":
                logger.warning(f"Filtering out invalid activity: {activity.get('id')} - {activity.get('name')}")
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
    
    def _make_api_call_with_retry(self, url: str, headers: Dict[str, str], max_retries: int = 3) -> httpx.Response:
        """Make an API call with retry logic and error handling using optimized HTTP client"""
        for attempt in range(max_retries):
            try:
                # Check rate limits before making call
                can_call, message = self._check_api_limits()
                if not can_call:
                    raise Exception(f"Rate limit exceeded: {message}")
                
                # Make the API call using shared HTTP client with connection pooling
                # CRITICAL: Add timeout to prevent hanging
                logger.info(f"🔄 Step 3a1: Getting HTTP client...")
                http_client = get_http_client()
                logger.info(f"🔄 Step 3a2: HTTP client obtained, making API call to: {url}")
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
                                    new_token = self.token_manager.get_valid_access_token()
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
            
            # Check and update rich data for ALL activities within last 3 weeks
            logger.info("🔍 Checking all activities for missing rich data...")
            updated_activities = self._check_and_update_all_activities_rich_data(merged_activities)
            
            # Update cache with merged and updated data
            cache_data = {
                "timestamp": datetime.now().isoformat(),
                "activities": updated_activities,
                "total_fetched": len(fresh_activities),
                "total_filtered": len(filtered_activities),
                "smart_merge": True,  # Flag to indicate smart merge was used
                "rich_data_updated": True  # Flag to indicate rich data was checked
            }
            
            self._save_cache(cache_data)
            
            execution_time = time.time() - start_time
            logger.info(f"Smart merged {len(merged_activities)} activities and updated rich data")
            logger.info(f"Smart merge complete - {execution_time:.3f}s")
            return updated_activities[:limit]
            
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
        """Fetch activities from Strava API with pagination to get ALL activities"""
        try:
            logger.info(f"🔄 Starting Strava API fetch for {limit} activities...")
            
            # Step 1: Get access token
            logger.info("🔄 Step 1: Getting access token...")
            try:
                access_token = self.token_manager.get_valid_access_token()
                logger.info("✅ Got access token for Strava API fetch")
            except Exception as e:
                logger.error(f"❌ Failed to get access token: {e}")
                logger.warning("🔄 Using fallback token from environment variables")
                import os
                fallback_token = os.getenv("STRAVA_ACCESS_TOKEN")
                if fallback_token:
                    access_token = fallback_token
                    logger.info("🔄 Using fallback token from environment variables")
                else:
                    logger.error("❌ No fallback token available")
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
            
            response = self._make_api_call_with_retry(
                "https://www.strava.com/api/v3/athlete/activities?per_page=200&page=1", 
                headers
            )
            
            logger.info(f"🔄 Step 3a4: API call completed: {response.status_code}")
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
        """Update cache with batch processing results"""
        try:
            logger.info(f"🔄 Updating cache with {len(basic_data)} activities ({len(new_activities)} new)")
            
            # Create cache data structure
            cache_data = {
                "timestamp": datetime.now().isoformat(),
                "activities": basic_data,
                "batching_in_progress": False,
                "batching_status_updated": datetime.now().isoformat()
            }
            
            # Update in-memory cache
            self._cache_data = cache_data
            self._cache_loaded_at = datetime.now()
            
            # Save to Supabase
            self._save_cache(cache_data)
            
            logger.info(f"✅ Updated cache with {len(basic_data)} activities ({len(new_activities)} new)")
            
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
