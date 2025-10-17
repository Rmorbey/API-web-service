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
        
        
        # Start the automated refresh system
        self._start_automated_refresh()
        
        # Start the daily corruption check scheduler
        self._schedule_daily_corruption_check()
        
        # Initialize cache system on startup
        self.initialize_cache_system()
    
    def initialize_cache_system(self):
        """Initialize cache system on server startup"""
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
                supabase_result = self.supabase_cache.get_cache('strava', 'fundraising-app')
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
            # Don't call _start_batch_processing() here - let check_and_refresh() handle it
            # to avoid duplicate calls
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
                access_token = self.token_manager.get_valid_access_token()
                logger.info(f"✅ Got access token for batch processing")
            except Exception as e:
                logger.error(f"❌ Failed to get access token for batch: {e}")
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
            
            # Note: Removed signal-based timeout as it doesn't work in background threads
            # The _make_api_call_with_retry method already has built-in timeouts
            
            # Add detailed logging for token retrieval
            logger.info("🔄 Step 1: Getting access token...")
            try:
                # Add timeout to token retrieval to prevent hanging
                import threading
                import time
                
                access_token = None
                token_error = None
                
                def get_token():
                    nonlocal access_token, token_error
                    try:
                        access_token = self.token_manager.get_valid_access_token()
                    except Exception as e:
                        token_error = e
                
                # Start token retrieval in a separate thread with timeout
                token_thread = threading.Thread(target=get_token)
                token_thread.daemon = True
                token_thread.start()
                token_thread.join(timeout=30)  # 30 second timeout
                
                if token_thread.is_alive():
                    logger.error("❌ Token manager hanging - using fallback")
                    # Try to get fresh token using refresh token as fallback
                    import os
                    refresh_token = os.getenv("STRAVA_REFRESH_TOKEN")
                    if refresh_token:
                        logger.warning("🔄 Using refresh token to get fresh access token")
                        try:
                            # Use the token manager's refresh method directly with timeout
                            import threading
                            import time
                            
                            access_token = None
                            refresh_error = None
                            
                            def refresh_token_worker():
                                nonlocal access_token, refresh_error
                                try:
                                    access_token = self.token_manager._refresh_access_token(refresh_token)
                                except Exception as e:
                                    refresh_error = e
                            
                            # Start token refresh in a separate thread with timeout
                            refresh_thread = threading.Thread(target=refresh_token_worker)
                            refresh_thread.daemon = True
                            refresh_thread.start()
                            refresh_thread.join(timeout=30)  # 30 second timeout
                            
                            if refresh_thread.is_alive():
                                logger.error("❌ Fallback token refresh hanging - trying to get fresh token")
                                # Wait a moment for the token refresh to complete and save to environment
                                import time
                                time.sleep(3)
                                
                                # Try to get the fresh token from the token manager's internal state
                                try:
                                    # Check if the token manager has a cached token
                                    if hasattr(self.token_manager, '_cached_token') and self.token_manager._cached_token:
                                        access_token = self.token_manager._cached_token
                                        logger.warning(f"🔄 Using cached token from token manager: {access_token[:20]}...")
                                    else:
                                        # Try to get the fresh token from the token manager's tokens dict
                                        if hasattr(self.token_manager, 'tokens') and self.token_manager.tokens.get('access_token'):
                                            access_token = self.token_manager.tokens['access_token']
                                            logger.warning(f"🔄 Using fresh token from token manager: {access_token[:20]}...")
                                        else:
                                            # Fall back to environment token
                                            import os
                                            env_token = os.getenv("STRAVA_ACCESS_TOKEN")
                                            if env_token:
                                                access_token = env_token
                                                logger.warning(f"🔄 Using environment access token as last resort: {env_token[:20]}...")
                                            else:
                                                raise Exception("Fallback token refresh hanging and no token available")
                                except Exception as e:
                                    logger.error(f"❌ Failed to get token from token manager: {e}")
                                    raise Exception("Fallback token refresh hanging and no token available")
                            elif refresh_error:
                                logger.error(f"❌ Fallback token refresh failed: {refresh_error}")
                                raise Exception(f"Token manager hanging and fallback refresh failed: {refresh_error}")
                            else:
                                logger.info(f"🔄 Successfully got fresh access token via fallback: {access_token[:20] if access_token else 'None'}...")
                                
                        except Exception as e:
                            logger.error(f"❌ Fallback token refresh failed: {e}")
                            raise Exception(f"Token manager hanging and fallback refresh failed: {e}")
                    else:
                        raise Exception("Token manager hanging and no refresh token available")
                elif token_error:
                    logger.error(f"❌ Failed to get access token: {token_error}")
                    # Try to get token directly from environment as fallback
                    import os
                    fallback_token = os.getenv("STRAVA_ACCESS_TOKEN")
                    if fallback_token:
                        logger.warning("🔄 Using fallback token from environment variables")
                        access_token = fallback_token
                    else:
                        raise Exception(f"No access token available: {token_error}")
                else:
                    logger.info(f"🔄 Step 1 Complete: Access token received: {access_token[:20] if access_token else 'None'}...")
                    
            except Exception as e:
                logger.error(f"❌ Failed to get access token: {e}")
                # Try to get token directly from environment as fallback
                import os
                fallback_token = os.getenv("STRAVA_ACCESS_TOKEN")
                if fallback_token:
                    logger.warning("🔄 Using fallback token from environment variables")
                    access_token = fallback_token
                else:
                    raise Exception(f"No access token available: {e}")
            
            # Add detailed logging for headers
            logger.info("🔄 Step 2: Creating headers...")
            # Fix double Bearer issue - ensure token doesn't already have Bearer prefix
            clean_token = access_token.replace('Bearer ', '') if access_token else ''
            headers = {'Authorization': f'Bearer {clean_token}'}
            logger.info(f"🔄 Step 2 Complete: Headers created successfully")
            logger.info(f"🔄 Step 2b: Access token length: {len(clean_token) if clean_token else 0}")
            
            all_activities = []
            page = 1
            per_page = 200  # Strava's maximum per page
            max_pages = 50  # Safety limit to prevent infinite loops
            
            while len(all_activities) < limit and page <= max_pages:
                url = f"{self.base_url}/athlete/activities?per_page={per_page}&page={page}"
                logger.info(f"🔄 Step 3: Fetching page {page} from URL: {url}")
                
                # Use the new retry-enabled API call method
                logger.info(f"🔄 Step 3a: Making API call with retry...")
                response = self._make_api_call_with_retry(url, headers)
                logger.info(f"🔄 Step 3b: API call completed, status: {response.status_code}")
                
                logger.info(f"🔄 API response received for page {page}, parsing JSON...")
                page_activities = response.json()
                
                if not page_activities:
                    logger.info(f"🔄 No more activities on page {page}, stopping pagination")
                    break
                
                all_activities.extend(page_activities)
                logger.info(f"🔄 Page {page}: fetched {len(page_activities)} activities, total: {len(all_activities)}")
                
                # If we got fewer activities than requested, we've reached the end
                if len(page_activities) < per_page:
                    logger.info(f"🔄 Reached end of activities (got {len(page_activities)} < {per_page})")
                    break
                
                page += 1
                
                # Small delay to be respectful to Strava API
                import time
                time.sleep(0.1)
            
            logger.info(f"🔄 Successfully fetched {len(all_activities)} total activities from Strava across {page-1} pages")
            return all_activities[:limit]  # Return only the requested limit
            
        except Exception as e:
            logger.error(f"Failed to fetch activities from Strava: {str(e)}")
            raise Exception(f"Strava API error: {str(e)}")

    # COMMENTED OUT - REDUNDANT METHOD (Phase 1: Activity Selection Logic)
    # def _has_complete_data(self, activity: Dict[str, Any]) -> bool:
    #     """Check if activity has complete data - for Run/Ride activities, all should have polyline and bounds"""
    #     has_polyline = bool(activity.get("map") and activity.get("map").get("polyline"))
    #     has_bounds = bool(activity.get("map") and activity.get("map").get("bounds"))
    #     
    #     # For Run/Ride activities, both polyline and bounds should be present
    #     # (these are outdoor activities with GPS tracking)
    #     return has_polyline and has_bounds

    # COMMENTED OUT - REDUNDANT METHOD (Phase 1: Activity Selection Logic)
    # def _get_missing_rich_data(self, activity: Dict[str, Any]) -> Dict[str, bool]:
    #     """Check what specific rich data is missing from an activity"""
    #     return {
    #         "polyline": not bool(activity.get("map") and activity.get("map").get("polyline")),
    #         "bounds": not bool(activity.get("map") and activity.get("map").get("bounds")),
    #         "description": not bool(activity.get("description", "").strip()),
    #         "photos": not bool(activity.get("photos", {})),
    #         "comments": not bool(activity.get("comments", []))
    #     }

    # COMMENTED OUT - REDUNDANT METHOD (Phase 1: Activity Selection Logic)
    # def _has_essential_map_data(self, activity: Dict[str, Any]) -> bool:
    #     """Check if activity has essential map data (polyline AND bounds)"""
    #     has_polyline = bool(activity.get("map") and activity.get("map").get("polyline"))
    #     has_bounds = bool(activity.get("map") and activity.get("map").get("bounds"))
    #     return has_polyline and has_bounds

    # COMMENTED OUT - REDUNDANT METHOD (Phase 1: Activity Selection Logic)
    # def _has_optional_rich_data(self, activity: Dict[str, Any]) -> bool:
    #     """Check if activity has optional rich data (description, photos, comments)"""
    #     has_description = bool(activity.get("description", "").strip())
    #     has_photos = bool(activity.get("photos", {}))
    #     has_comments = bool(activity.get("comments", []))
    #     return has_description or has_photos or has_comments

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

    # COMMENTED OUT - REDUNDANT METHOD (Phase 2: Retry Logic)
    # def _get_rich_data_retry_count(self, activity: Dict[str, Any]) -> int:
    #     """Get the number of times we've tried to fetch rich data for this activity"""
    #     return activity.get('_rich_data_retry_count', 0)

    # COMMENTED OUT - REDUNDANT METHOD (Phase 2: Retry Logic)
    # def _get_last_retry_attempt(self, activity: Dict[str, Any]) -> Optional[str]:
    #     """Get the timestamp of the last retry attempt"""
    #     return activity.get('_last_retry_attempt')

    # COMMENTED OUT - REDUNDANT METHOD (Phase 2: Retry Logic)
    # def _increment_rich_data_retry_count(self, activity: Dict[str, Any]) -> Dict[str, Any]:
    #     """Increment the retry counter and update last attempt timestamp"""
    #     activity['_rich_data_retry_count'] = activity.get('_rich_data_retry_count', 0) + 1
    #     activity['_last_retry_attempt'] = datetime.now().isoformat()
    #     return activity

    # COMMENTED OUT - REDUNDANT METHOD (Phase 2: Retry Logic)
    # def _mark_rich_data_success(self, activity: Dict[str, Any]) -> Dict[str, Any]:
    #     """Mark that rich data was successfully fetched (don't reset counter)"""
    #     # Don't reset the counter - just ensure it exists
    #     if '_rich_data_retry_count' not in activity:
    #         activity['_rich_data_retry_count'] = 0
    #     return activity

    # COMMENTED OUT - REDUNDANT METHOD (Phase 2: Retry Logic)
    # def _can_retry_rich_data(self, activity: Dict[str, Any]) -> bool:
    #     """Check if enough time has passed since last retry attempt (24 hours)"""
    #     last_attempt = self._get_last_retry_attempt(activity)
    #     if not last_attempt:
    #         return True  # Never tried before
    #     
    #     try:
    #         last_attempt_dt = datetime.fromisoformat(last_attempt)
    #         time_since_last = datetime.now() - last_attempt_dt
    #         return time_since_last.total_seconds() >= 86400  # 24 hours
    #     except Exception:
    #         return True  # If parsing fails, allow retry

    # COMMENTED OUT - REDUNDANT METHOD (Phase 2: Retry Logic)
    # def _should_attempt_rich_data_update(self, activity: Dict[str, Any]) -> bool:
    #     """Check if we should attempt to update rich data for this activity"""
    #     # Check if activity is recent enough
    #     if not self._is_activity_recent_enough(activity):
    #         return False
    #     
    #     # Check if enough time has passed since last retry (24 hours)
    #     if not self._can_retry_rich_data(activity):
    #         return False
    #     
    #     # Get what data is missing
    #     missing_data = self._get_missing_rich_data(activity)
    #     retry_count = self._get_rich_data_retry_count(activity)
    #     
    #     # If we have essential map data (polyline + bounds), only try 5 times for optional data
    #     if self._has_essential_map_data(activity):
    #         if retry_count >= 5:
    #             # Already tried 5 times for optional data, don't try again
    #             return False
    #         # Try to get optional rich data (description, photos, comments)
    #         return missing_data["description"] or missing_data["photos"] or missing_data["comments"]
    #     
    #     # If we don't have essential map data, keep trying (unlimited attempts)
    #     return missing_data["polyline"] or missing_data["bounds"]

    # COMMENTED OUT - REDUNDANT METHOD (Phase 2: Retry Logic)
    # def _should_attempt_essential_map_data_update(self, activity: Dict[str, Any]) -> bool:
    #     """Check if we should attempt to fetch only essential map data (polyline + bounds)"""
    #     # Check if activity is recent enough
    #     if not self._is_activity_recent_enough(activity):
    #         return False
    #     
    #     # Only attempt if we've tried 5 times and still missing critical map data
    #     retry_count = self._get_rich_data_retry_count(activity)
    #     if retry_count < 5:
    #         return False
    #     
    #     # Check if we're missing critical map data
    #     has_polyline = bool(activity.get("map") and activity.get("map").get("polyline"))
    #     has_bounds = bool(activity.get("map") and activity.get("map").get("bounds"))
    #     return not (has_polyline and has_bounds)

    # COMMENTED OUT - REDUNDANT METHOD (Phase 2: Retry Logic)
    # def _fetch_essential_map_data_only(self, activity_id: int) -> Dict[str, Any]:
    #     """Fetch only essential map data (polyline + bounds) for activities that failed 5 times"""
    #     try:
    #         logger.info(f"🗺️ Fetching essential map data only for activity {activity_id}")
    #         
    #         # Fetch basic activity data to get map information
    #         activity_url = f"{self.base_url}/activities/{activity_id}"
    #         headers = {"Authorization": f"Bearer {self.token_manager.get_valid_access_token()}"}
    #         
    #         response = self._make_api_call_with_retry(activity_url, headers)
    #         activity_data = response.json()
    #         
    #         # Extract only essential map data
    #         map_data = activity_data.get("map", {})
    #         essential_map = {
    #             "polyline": map_data.get("polyline"),
    #             "bounds": map_data.get("bounds", {})
    #         }
    #         
    #         # Calculate bounds from polyline if not provided
    #         if not essential_map["bounds"] and essential_map["polyline"]:
    #             coordinates = self._decode_polyline(essential_map["polyline"])
    #             if coordinates:
    #                 essential_map["bounds"] = self._calculate_polyline_bounds(coordinates)
    #         
    #         logger.info(f"✅ Successfully fetched essential map data for activity {activity_id}")
    #         return essential_map
    #         
    #     except Exception as e:
    #         logger.error(f"❌ Failed to fetch essential map data for activity {activity_id}: {e}")
    #         return {}

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
        """Decode Google polyline string to lat/lng coordinates - FIXED with corruption detection"""
        if not polyline_str:
            return []
        
        try:
            # Use a more robust polyline decoder
            import polyline
            coordinates = polyline.decode(polyline_str)
            
            # Return raw coordinates from Strava API (trust the data)
            return [[lat, lng] for lat, lng in coordinates]
                
        except ImportError:
            # Fallback to manual decoder if polyline library not available
            logger.warning("polyline library not available, using fallback decoder")
            return self._decode_polyline_fallback(polyline_str)
        except Exception as e:
            logger.error(f"Error decoding polyline: {e}")
            return []
    
    def _calculate_polyline_bounds(self, coordinates: List[List[float]]) -> Dict[str, float]:
        """Calculate proper bounds for polyline coordinates (based on Towards Data Science article)"""
        if not coordinates:
            return {}
        
        try:
            lats = [coord[0] for coord in coordinates]  # latitude
            lngs = [coord[1] for coord in coordinates]  # longitude
            
            return {
                "south": min(lats),
                "west": min(lngs), 
                "north": max(lats),
                "east": max(lngs)
            }
        except Exception as e:
            logger.error(f"Error calculating polyline bounds: {e}")
            return {}
    
    def _calculate_polyline_centroid(self, coordinates: List[List[float]]) -> List[float]:
        """Calculate centroid for polyline coordinates (based on Towards Data Science article)"""
        if not coordinates:
            return []
        
        try:
            lats = [coord[0] for coord in coordinates]  # latitude
            lngs = [coord[1] for coord in coordinates]  # longitude
            
            # Calculate centroid as mean of min/max (as shown in the article)
            centroid_lat = (min(lats) + max(lats)) / 2
            centroid_lng = (min(lngs) + max(lngs)) / 2
            
            return [centroid_lat, centroid_lng]
        except Exception as e:
            logger.error(f"Error calculating polyline centroid: {e}")
            return []
    
    def _validate_coordinates(self, coordinates: List[tuple]) -> bool:
        """Validate that coordinates are reasonable and not corrupted"""
        if not coordinates:
            return False
        
        try:
            lats = [coord[0] for coord in coordinates]  # latitude
            lngs = [coord[1] for coord in coordinates]  # longitude
            
            # Check for valid coordinate ranges
            if (min(lats) < -90 or max(lats) > 90 or 
                min(lngs) < -180 or max(lngs) > 180):
                logger.warning(f"Invalid coordinate ranges detected: lat=[{min(lats):.6f}, {max(lats):.6f}], lng=[{min(lngs):.6f}, {max(lngs):.6f}]")
                return False
            
            # Check for extreme jumps between coordinates (likely corruption)
            # But be more lenient - allow up to 1 degree (111km) jumps for legitimate GPS issues
            if len(coordinates) > 1:
                max_lat_jump = max(abs(lats[i] - lats[i-1]) for i in range(1, len(lats)))
                max_lng_jump = max(abs(lngs[i] - lngs[i-1]) for i in range(1, len(lngs)))
                
                # 1 degree ≈ 111km, so jumps > 1 degree (111km) are suspicious
                if max_lat_jump > 1.0 or max_lng_jump > 1.0:
                    logger.warning(f"Extreme coordinate jumps detected: lat={max_lat_jump:.6f}, lng={max_lng_jump:.6f}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating coordinates: {e}")
            return False
    
    def _validate_polyline_string(self, polyline_str: str) -> bool:
        """Validate polyline string to detect corruption"""
        if not polyline_str or not isinstance(polyline_str, str):
            return False
        
        # Check for invalid characters that indicate corruption
        invalid_chars = ['^', '?', '[', '~', '}', '@', '`', '{', ']', '|']
        for char in invalid_chars:
            if char in polyline_str:
                logger.warning(f"Invalid character '{char}' detected in polyline string")
                return False
        
        # Check for reasonable length (polyline strings are typically 100-10000 chars)
        if len(polyline_str) < 10 or len(polyline_str) > 50000:
            logger.warning(f"Polyline string length {len(polyline_str)} is outside normal range")
            return False
        
        # Try to decode a small portion to test validity
        try:
            test_coords = self._decode_polyline(polyline_str[:100])  # Test first 100 chars
            if not test_coords or len(test_coords) == 0:
                logger.warning("Polyline string failed decoding test")
                return False
        except Exception as e:
            logger.warning(f"Polyline string validation failed: {e}")
            return False
        
        return True

    def _decode_polyline_fallback(self, polyline_str: str) -> List[List[float]]:
        """Fallback polyline decoder with better error handling"""
        if not polyline_str:
            return []
        
        try:
            index = 0
            lat = 0
            lng = 0
            coordinates = []
            
            while index < len(polyline_str):
                # Decode latitude
                shift = 0
                result = 0
                while index < len(polyline_str):
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
                while index < len(polyline_str):
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
            logger.error(f"Error in fallback polyline decoder: {e}")
            return []

    def _process_map_data(self, activity_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process map data - OPTIMIZED: Only essential fields for frontend"""
        map_data = activity_data.get("map", {})
        
        # Extract only essential map data
        polyline = map_data.get("polyline")
        bounds = map_data.get("bounds", {})
        
        # Use raw polyline data from Strava API (trust the data)
        # No validation needed - Strava API is reliable
        
        # Calculate bounds from polyline if not provided
        if not bounds and polyline:
            coordinates = self._decode_polyline(polyline)
            if coordinates:
                bounds = self._calculate_polyline_bounds(coordinates)
        
        # OPTIMIZED: Only return essential fields (frontend only needs polyline + bounds)
        return {
            "polyline": polyline,
            "bounds": bounds
        }

    def _clean_invalid_activities(self, activities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove invalid/unknown activities from the list"""
        cleaned = []
        removed_count = 0
        
        for activity in activities:
            # Check for invalid activities
            if (activity.get("name") == "Unknown Activity" or 
                activity.get("type") == "Unknown" or
                activity.get("distance", 0) == 0 and activity.get("moving_time", 0) == 0):
                
                logger.warning(f"Removing invalid activity: ID {activity.get('id')} - {activity.get('name')}")
                removed_count += 1
                continue
            
            cleaned.append(activity)
        
        if removed_count > 0:
            logger.info(f"Cleaned {removed_count} invalid activities from cache")
        
        return cleaned

    # COMMENTED OUT - REDUNDANT METHOD (Phase 3: Smart Merging)
    # def _smart_merge_activities(self, existing_activities: List[Dict[str, Any]], fresh_activities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    #     """
    #     Smart merge: Preserve ALL existing data, update only basic fields from fresh data
    #     FIXED: Never overwrite existing activities with fresh data to prevent data loss
    #     """
    #     # Clean existing activities first to remove any invalid entries
    #     existing_activities = self._clean_invalid_activities(existing_activities)
    #     
    #     # Create lookup maps
    #     existing_by_id = {activity.get("id"): activity for activity in existing_activities}
    #     fresh_by_id = {activity.get("id"): activity for activity in fresh_activities}
    #     
    #     merged_activities = []
    #     
    #     # Process fresh activities (maintains order from Strava)
    #     for fresh_activity in fresh_activities:
    #         activity_id = fresh_activity.get("id")
    #         existing_activity = existing_by_id.get(activity_id)
    #         
    #         if existing_activity:
    #             # PRESERVE: Always keep existing data, update only basic fields
    #             merged_activity = existing_activity.copy()
    #             
    #             # Update only basic fields that might have changed
    #             basic_fields = ["name", "type", "distance", "moving_time", "elapsed_time", 
    #                           "start_date", "start_date_local", "timezone", "total_elevation_gain"]
    #             
    #             for field in basic_fields:
    #                 if field in fresh_activity:
    #                     merged_activity[field] = fresh_activity[field]
    #             
    #             logger.info(f"Preserved existing data for activity {activity_id}: {fresh_activity.get('name', 'Unknown')}")
    #             
    #         else:
    #             # NEW ACTIVITY: Use fresh data and add timestamp tracking
    #             merged_activity = fresh_activity
    #             current_time = datetime.now().isoformat()
    #             merged_activity["_metadata"] = {
    #                 "basic_data_added": current_time,
    #                 "rich_data_added": None,
    #                 "last_updated": current_time
    #             }
    #             logger.info(f"New activity {activity_id}: {fresh_activity.get('name', 'Unknown')}")
    #         
    #         # Check if ANY activity (new or existing) needs rich data collection
    #         if self._should_attempt_rich_data_update(merged_activity):
    #             try:
    #                 retry_count = self._get_rich_data_retry_count(merged_activity)
    #                 logger.info(f"🔄 Fetching rich data for activity {activity_id} (attempt {retry_count + 1}/5)")
    #                 
    #                 complete_data = self._fetch_complete_activity_data(activity_id)
    #                 merged_activity = complete_data
    #                 
    #                 # Reset retry count on success
    #                 merged_activity['_rich_data_retry_count'] = 0
    #                 logger.info(f"✅ Successfully fetched rich data for activity {activity_id}")
    #                 
    #             except Exception as e:
    #                 # Increment retry count on failure
    #                 merged_activity = self._increment_rich_data_retry_count(merged_activity)
    #                 retry_count = self._get_rich_data_retry_count(merged_activity)
    #                 
    #                 if retry_count >= 5:
    #                     logger.warning(f"⚠️ Max retries reached for activity {activity_id} (5/5): {e}")
    #                 else:
    #                     logger.warning(f"⚠️ Failed to fetch rich data for activity {activity_id} (attempt {retry_count}/5): {e}")
    #         
    #         merged_activities.append(merged_activity)
    #     
    #     # Add any existing activities that weren't in fresh data (shouldn't happen with Strava)
    #     for activity_id, existing_activity in existing_by_id.items():
    #         if activity_id not in fresh_by_id:
    #             merged_activities.append(existing_activity)
    #             logger.info(f"Preserved existing activity not in fresh data: {activity_id}")
    #     
    #     return merged_activities

    def _check_and_update_all_activities_rich_data(self, activities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Check ALL activities within last 3 weeks and update rich data if needed"""
        updated_activities = []
        activities_updated = 0
        essential_map_updated = 0
        
        for activity in activities:
            activity_id = activity.get("id")
            
            # Check if this activity needs rich data updates
            if self._should_attempt_rich_data_update(activity):
                missing_data = self._get_missing_rich_data(activity)
                retry_count = self._get_rich_data_retry_count(activity)
                
                # Determine what type of data we're trying to fetch
                if self._has_essential_map_data(activity):
                    data_type = "optional rich data (description/photos/comments)"
                    max_attempts = 5
                else:
                    data_type = "essential map data (polyline/bounds)"
                    max_attempts = "unlimited"
                
                # Get last attempt info for logging
                last_attempt = self._get_last_retry_attempt(activity)
                if last_attempt:
                    try:
                        last_attempt_dt = datetime.fromisoformat(last_attempt)
                        hours_since = (datetime.now() - last_attempt_dt).total_seconds() / 3600
                        time_info = f" (last attempt: {hours_since:.1f}h ago)"
                    except:
                        time_info = ""
                else:
                    time_info = " (first attempt)"
                
                try:
                    logger.info(f"🔄 Updating {data_type} for activity {activity_id} (attempt {retry_count + 1}/{max_attempts}){time_info}")
                    
                    complete_data = self._fetch_complete_activity_data(activity_id)
                    activity = complete_data
                    
                    # Mark success (don't reset counter)
                    activity = self._mark_rich_data_success(activity)
                    activities_updated += 1
                    logger.info(f"✅ Successfully updated {data_type} for activity {activity_id}")
                    
                except Exception as e:
                    # Increment retry count on failure
                    activity = self._increment_rich_data_retry_count(activity)
                    retry_count = self._get_rich_data_retry_count(activity)
                    
                    if self._has_essential_map_data(activity) and retry_count >= 5:
                        logger.warning(f"⚠️ Max retries reached for optional data on activity {activity_id} (5/5): {e}")
                        logger.info(f"📋 Activity {activity_id} will preserve existing polyline/bounds data")
                    elif not self._has_essential_map_data(activity):
                        logger.warning(f"⚠️ Failed to fetch essential map data for activity {activity_id} (attempt {retry_count}): {e}")
                        logger.info(f"🔄 Will continue trying essential map data for activity {activity_id}")
                    else:
                        logger.warning(f"⚠️ Failed to update {data_type} for activity {activity_id} (attempt {retry_count}/5): {e}")
            
            updated_activities.append(activity)
        
        if activities_updated > 0:
            logger.info(f"📊 Updated rich data for {activities_updated} activities")
        if essential_map_updated > 0:
            logger.info(f"🗺️ Updated essential map data for {essential_map_updated} activities")
        
        return updated_activities

    def _update_activity_in_cache(self, activity_id: int, complete_data: Dict[str, Any]):
        """Update activity in cache with complete data and timestamp tracking"""
        cache_data = self._load_cache()
        current_time = datetime.now().isoformat()
        
        # Find and update the activity
        for i, activity in enumerate(cache_data.get("activities", [])):
            if activity.get("id") == activity_id:
                # Preserve existing timestamps if they exist
                existing_activity = cache_data["activities"][i]
                
                # Add timestamp tracking for data updates
                complete_data["_metadata"] = {
                    "basic_data_added": existing_activity.get("_metadata", {}).get("basic_data_added", current_time),
                    "rich_data_added": current_time,
                    "last_updated": current_time
                }
                
                # Log what data is being updated
                existing_polyline = existing_activity.get("map", {}).get("polyline")
                new_polyline = complete_data.get("map", {}).get("polyline")
                existing_bounds = existing_activity.get("map", {}).get("bounds")
                new_bounds = complete_data.get("map", {}).get("bounds")
                
                if existing_polyline and not new_polyline:
                    logger.warning(f"⚠️ Activity {activity_id}: LOST polyline data during update!")
                elif not existing_polyline and new_polyline:
                    logger.info(f"✅ Activity {activity_id}: GAINED polyline data")
                
                if existing_bounds and not new_bounds:
                    logger.warning(f"⚠️ Activity {activity_id}: LOST bounds data during update!")
                elif not existing_bounds and new_bounds:
                    logger.info(f"✅ Activity {activity_id}: GAINED bounds data")
                
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
    
    def _fetch_activity_photos(self, activity_id: int, access_token: str = None) -> Dict[str, Any]:
        """Fetch photos for a specific activity - OPTIMIZED: Only essential fields"""
        try:
            # Add size parameter to get actual photos instead of placeholders
            photos_url = f"{self.base_url}/activities/{activity_id}/photos?size=5000"
            
            # Use provided token or get a new one
            if access_token:
                token = access_token
            else:
                token = self.token_manager.get_valid_access_token()
            
            headers = {"Authorization": f"Bearer {token}"}
            
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
    
    def _fetch_activity_comments(self, activity_id: int, access_token: str = None) -> List[Dict[str, Any]]:
        """Fetch comments for a specific activity - OPTIMIZED: Only essential fields"""
        try:
            comments_url = f"{self.base_url}/activities/{activity_id}/comments"
            
            # Use provided token or get a new one
            if access_token:
                token = access_token
            else:
                token = self.token_manager.get_valid_access_token()
            
            headers = {"Authorization": f"Bearer {token}"}
            
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
        """Start the automated refresh system with 8-hour intervals"""
        if self._refresh_thread and self._refresh_thread.is_alive():
            return
        
        self._refresh_thread = threading.Thread(target=self._automated_refresh_loop, daemon=True)
        self._refresh_thread.start()
        logger.info("🔄 Automated refresh system started (8-hour intervals)")
    
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
    
    def _start_scheduled_refresh(self):
        """Start a normal scheduled refresh (not emergency)"""
        try:
            logger.info("🔄 Starting normal scheduled refresh...")
            # Run scheduled refresh in background thread to avoid blocking startup
            import threading
            refresh_thread = threading.Thread(target=self._perform_scheduled_refresh, daemon=True)
            refresh_thread.start()
            logger.info("🔄 Normal refresh started in background thread")
        except Exception as e:
            logger.error(f"❌ Failed to start scheduled refresh: {e}")
    
    def _perform_scheduled_refresh(self):
        """Perform a scheduled refresh using streamlined logic"""
        try:
            logger.info("🔄 Normal scheduled refresh...")
            self._start_batch_processing()
            
        except Exception as e:
            logger.error(f"❌ Scheduled refresh failed: {e}")
    
    # Backup operations removed - using Supabase-only storage
    
    def _start_batch_processing(self):
        """Start batch processing of activities (20 every 15 minutes) using new streamlined architecture"""
        if self._batch_thread and self._batch_thread.is_alive():
            logger.info("🏃‍♂️ Batch processing already running, skipping...")
            return
        
        # Mark batching as in progress
        self._mark_batching_in_progress(True)
        
        self._batch_thread = threading.Thread(target=self._batch_processing_loop, daemon=True)
        self._batch_thread.start()
        logger.info("🏃‍♂️ Batch processing started (20 activities every 15 minutes)")
    
    def _batch_processing_loop(self):
        """Process activities in batches of 20 every 15 minutes using new streamlined architecture"""
        try:
            logger.info("🏃‍♂️ Starting batch processing with new streamlined architecture...")
            
            # Step 1: Get a single access token for the entire batch processing session
            try:
                logger.info(f"🔄 Getting access token for entire batch processing session...")
                access_token = self.token_manager.get_valid_access_token()
                logger.info(f"✅ Got access token for entire batch processing session")
            except Exception as e:
                logger.error(f"❌ Failed to get access token for batch processing: {e}")
                logger.error(f"❌ Batch processing aborted - cannot proceed without valid token")
                return
            
            # Step 2: Fetch fresh basic data from Strava (following our new flow)
            raw_data = self._fetch_from_strava(200)
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
                    self._process_activity_batch(batch, access_token=access_token)
                    
                    # Wait 15 minutes between batches (except for the last batch)
                    if i + batch_size < len(new_activities):
                        logger.info("⏰ Waiting 15 minutes before next batch...")
                        time.sleep(900)  # 15 minutes
            else:
                logger.info("✅ No new activities to process")
            
            # Step 4: Update cache with all data
            self._update_cache_with_batch_results(basic_data, new_activities)
            
            # Step 5: Mark batching as complete
            self._mark_batching_in_progress(False)
            
            logger.info("✅ Batch processing completed successfully")
            
        except Exception as e:
            logger.error(f"❌ Batch processing failed: {e}")
            self._mark_batching_in_progress(False)
    #             
    #             # Wait 15 minutes before next batch (except for last batch)
    #             if i + batch_size < len(activities_to_process):
    #                 logger.info("⏳ Waiting 15 minutes before next batch...")
    #                 time.sleep(900)  # 15 minutes
    #         
    #         logger.info("🏃‍♂️ Batch processing complete")
    #         
    #         # Mark batching as complete and validate results
    #         self._mark_batching_in_progress(False)
    #         self._validate_post_batch_results()
    #         
    #         # Clear emergency refresh flags
    #         self._emergency_refresh_in_progress = False
    #         
    #         # Clear emergency refresh flag from cache data for future batch processing
    #         if self._cache_data and self._cache_data.get('emergency_refresh'):
    #             self._cache_data['emergency_refresh'] = False
    #             logger.info("🏃‍♂️ Cleared emergency refresh flag from cache data")
    #         
    #     except Exception as e:
    #         logger.error(f"❌ Batch processing failed: {e}")
    #         # Mark batching as complete even on failure
    #         self._mark_batching_in_progress(False)
    #         # Clear emergency refresh flags
    #         self._emergency_refresh_in_progress = False
    #         # Clear emergency refresh flag from cache data
    #         if self._cache_data and self._cache_data.get('emergency_refresh'):
    #             self._cache_data['emergency_refresh'] = False
    #             logger.info("🏃‍♂️ Cleared emergency refresh flag from cache data (after error)")
    
    def _mark_batching_in_progress(self, in_progress: bool):
        """Mark batching as in progress or complete in cache"""
        try:
            cache_data = self._load_cache(trigger_emergency_refresh=False)
            cache_data["batching_in_progress"] = in_progress
            cache_data["batching_status_updated"] = datetime.now().isoformat()
            
            # Save to file and Supabase
            self._save_cache(cache_data)
            
            status = "started" if in_progress else "completed"
            logger.info(f"🔄 Batching process {status}")
            
        except Exception as e:
            logger.error(f"❌ Failed to update batching status: {e}")
    
    def _validate_post_batch_results(self):
        """Validate results after batch processing completes"""
        try:
            cache_data = self._load_cache(trigger_emergency_refresh=False)
            activities = cache_data.get("activities", [])
            
            if not activities:
                logger.warning("No activities to validate after batch processing")
                return
            
            total_activities = len(activities)
            polyline_count = sum(1 for activity in activities if activity.get("map", {}).get("polyline"))
            bounds_count = sum(1 for activity in activities if activity.get("map", {}).get("bounds"))
            
            polyline_percentage = (polyline_count / total_activities) * 100
            bounds_percentage = (bounds_count / total_activities) * 100
            
            logger.info(f"📊 Post-batch validation: {polyline_count}/{total_activities} activities have polyline data ({polyline_percentage:.1f}%)")
            logger.info(f"📊 Post-batch validation: {bounds_count}/{total_activities} activities have bounds data ({bounds_percentage:.1f}%)")
            
            # If polyline data is still below 30%, trigger another batch process
            if polyline_percentage < 30.0:
                logger.warning(f"🏃‍♂️ Polyline data coverage is only {polyline_percentage:.1f}%, triggering retry")
                logger.info("🏃‍♂️ Starting batch processing retry to collect missing data")
                
                # Reset batching status and start again
                self._mark_batching_in_progress(True)
                self._start_batch_processing()
            else:
                logger.info(f"🏃‍♂️ Polyline data coverage is {polyline_percentage:.1f}%, batch processing successful")
                
        except Exception as e:
            logger.error(f"❌ Post-batch validation failed: {e}")
    
    # _get_activities_needing_update removed - redundant in streamlined logic
    
    # COMMENTED OUT - OLD BATCH PROCESSING LOGIC (Replaced with new simplified system)
    def _process_activity_batch(self, batch: List[Dict[str, Any]], access_token: str = None):
        """Process a batch of new activities using new streamlined architecture"""
        try:
            logger.info(f"🏃‍♂️ Processing batch of {len(batch)} new activities...")
            
            # Fetch rich data for all activities in this batch using the pre-obtained token
            rich_data = self._fetch_rich_data_for_new_activities(batch, access_token=access_token)
            
            # Update each activity with rich data
            for activity in batch:
                activity_id = activity.get('id')
                if activity_id and activity_id in rich_data:
                    # Update activity with rich data
                    activity.update(rich_data[activity_id])
                    
                    # Update expiration flags
                    activity = self._update_activity_expiration_flags(activity)
                    
                    logger.info(f"✅ Updated activity {activity_id} with rich data")
                else:
                    logger.warning(f"⚠️ No rich data found for activity {activity_id}")
                
                time.sleep(1)  # Small delay to respect API limits
                
        except Exception as e:
            logger.error(f"❌ Error processing activity batch: {e}")
    
    def _update_cache_with_batch_results(self, basic_data: List[Dict[str, Any]], new_activities: List[Dict[str, Any]]):
        """Update cache with batch processing results"""
        try:
            cache_data = self._load_cache(trigger_emergency_refresh=False)
            if not cache_data:
                cache_data = {"activities": [], "metadata": {}}
            
            existing_activities = cache_data.get("activities", [])
            existing_by_id = {activity.get("id"): activity for activity in existing_activities}
            
            # Update existing activities with fresh basic data
            for activity in basic_data:
                activity_id = activity.get("id")
                if activity_id in existing_by_id:
                    # Update existing activity with fresh basic data
                    existing_by_id[activity_id].update(activity)
                else:
                    # Add new activity
                    existing_activities.append(activity)
            
            # Save updated cache
            cache_data["activities"] = existing_activities
            
            # Update metadata
            current_time = datetime.now().isoformat()
            cache_data['last_fetch'] = current_time
            cache_data['last_basic_data_updated'] = current_time
            if new_activities:
                cache_data['last_rich_data_updated'] = current_time
            
            self._save_cache(cache_data)
            
            logger.info(f"✅ Updated cache with {len(basic_data)} activities ({len(new_activities)} new)")
            
        except Exception as e:
            logger.error(f"❌ Failed to update cache with batch results: {e}")
    
    # COMMENTED OUT - REDUNDANT METHOD (Phase 5: Diagnostic Methods)
    # def analyze_cache_data_loss(self) -> Dict[str, Any]:
    #     """Analyze cache to identify data loss and timestamp information"""
    #     try:
    #         cache_data = self._load_cache()
    #         activities = cache_data.get("activities", [])
    #         
    #         analysis = {
    #             "total_activities": len(activities),
    #             "activities_with_polyline": 0,
    #             "activities_with_bounds": 0,
    #             "activities_with_metadata": 0,
    #             "activities_with_corrupted_polyline": 0,
    #             "data_loss_analysis": [],
    #             "timestamp_analysis": [],
    #             "corrupted_activities": []
    #         }
    #         
    #         for activity in activities:
    #             activity_id = activity.get("id")
    #             activity_name = activity.get("name", "Unknown")
    #             
    #             # Check polyline data
    #             has_polyline = bool(activity.get("map", {}).get("polyline"))
    #             has_bounds = bool(activity.get("map", {}).get("bounds"))
    #             has_metadata = bool(activity.get("_metadata"))
    #             
    #             # Check for polyline corruption
    #             is_corrupted = False
    #             if has_polyline:
    #                 polyline_str = activity.get("map", {}).get("polyline", "")
    #                 try:
    #                     import polyline
    #                     coordinates = polyline.decode(polyline_str)
    #                     # Trust Strava API data - no validation needed
    #                     # If polyline decodes successfully, it's valid
    #                 except Exception:
    #                     is_corrupted = True
    #                     analysis["activities_with_corrupted_polyline"] += 1
    #             
    #             if has_polyline:
    #                 analysis["activities_with_polyline"] += 1
    #             if has_bounds:
    #                 analysis["activities_with_bounds"] += 1
    #             if has_metadata:
    #                 analysis["activities_with_metadata"] += 1
    #             
    #             # Analyze metadata if available
    #             metadata = activity.get("_metadata", {})
    #             if metadata:
    #                 analysis["timestamp_analysis"].append({
    #                     "activity_id": activity_id,
    #                     "activity_name": activity_name,
    #                     "basic_data_added": metadata.get("basic_data_added"),
    #                     "rich_data_added": metadata.get("rich_data_added"),
    #                     "last_updated": metadata.get("last_updated"),
    #                     "has_polyline": has_polyline,
    #                     "has_bounds": has_bounds,
    #                     "is_corrupted": is_corrupted
    #                 })
    #             else:
    #                 analysis["data_loss_analysis"].append({
    #                     "activity_id": activity_id,
    #                     "activity_name": activity_name,
    #                     "issue": "No metadata - cannot track when data was added",
    #                     "has_polyline": has_polyline,
    #                     "has_bounds": has_bounds,
    #                     "is_corrupted": is_corrupted
    #                 })
    #             
    #             # Add to corrupted activities list if corrupted
    #             if is_corrupted:
    #                 analysis["corrupted_activities"].append({
    #                     "activity_id": activity_id,
    #                     "activity_name": activity_name,
    #                     "issue": "Corrupted polyline data - causes weird route visualization"
    #                 })
    #         
    #         # Calculate percentages
    #         total = analysis["total_activities"]
    #         analysis["polyline_percentage"] = (analysis["activities_with_polyline"] / total * 100) if total > 0 else 0
    #         analysis["bounds_percentage"] = (analysis["activities_with_bounds"] / total * 100) if total > 0 else 0
    #         analysis["metadata_percentage"] = (analysis["activities_with_metadata"] / total * 100) if total > 0 else 0
    #         analysis["corruption_percentage"] = (analysis["activities_with_corrupted_polyline"] / total * 100) if total > 0 else 0
    #         
    #         return analysis
    #         
    #     except Exception as e:
    #         logger.error(f"Error analyzing cache data loss: {e}")
    #         return {"error": str(e)}
    

    # COMMENTED OUT - REDUNDANT METHOD (Phase 5: Diagnostic Methods)
    # def clean_invalid_activities(self) -> Dict[str, Any]:
    #     """Clean invalid activities from the cache"""
    #     try:
    #         # Load current cache
    #         cache_data = self._load_cache()
    #         if not cache_data:
    #             return {"success": False, "message": "No cache data found"}
    #         
    #         activities = cache_data.get("activities", [])
    #         original_count = len(activities)
    #         
    #         # Clean invalid activities
    #         cleaned_activities = self._clean_invalid_activities(activities)
    #         removed_count = original_count - len(cleaned_activities)
    #         
    #         if removed_count > 0:
    #             # Update cache with cleaned activities
    #             cache_data["activities"] = cleaned_activities
    #             cache_data["timestamp"] = datetime.now().isoformat()
    #             cache_data["cleaned_invalid_activities"] = True
    #             
    #             self._save_cache(cache_data)
    #             logger.info(f"Cleaned {removed_count} invalid activities from cache")
    #             
    #             return {
    #                 "success": True,
    #                 "message": f"Cleaned {removed_count} invalid activities from cache",
    #                 "activities_removed": removed_count,
    #                 "activities_remaining": len(cleaned_activities)
    #             }
    #         else:
    #             return {
    #                 "success": True,
    #                 "message": "No invalid activities found in cache",
    #                 "activities_removed": 0,
    #                 "activities_remaining": len(cleaned_activities)
    #             }
    #             
    #     except Exception as e:
    #         logger.error(f"Error cleaning invalid activities: {e}")
    #         return {"success": False, "message": f"Error cleaning invalid activities: {str(e)}"}
    
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
    
    
    # COMMENTED OUT - OLD EMERGENCY REFRESH LOGIC (Replaced with new simplified system)
    # def _trigger_emergency_refresh(self):
    #     """Emergency refresh - fetch fresh data from Strava when cache is empty"""
    #     if self._emergency_refresh_in_progress:
    #         logger.info("🏃‍♂️ Emergency refresh already in progress, skipping...")
    #         return
    #         
    #     self._emergency_refresh_in_progress = True
    #     logger.info("🏃‍♂️ Emergency refresh triggered - starting in background thread")
    #     
    #     # Start emergency refresh in background thread to avoid blocking startup
    #     def emergency_refresh_worker():
    #         try:
    #             logger.info("🏃‍♂️ Emergency refresh worker started - fetching fresh data from Strava")
    #             
    #             # When cache is empty, we need to fetch basic activity data from Strava first
    #             logger.info("🏃‍♂️ Fetching basic activity data from Strava API...")
    #             logger.info("🏃‍♂️ About to call _fetch_from_strava(200)...")
    #             
    #             try:
    #                 fresh_activities = self._fetch_from_strava(200)  # Fetch basic activity data
    #                 logger.info(f"🏃‍♂️ _fetch_from_strava completed, got {len(fresh_activities) if fresh_activities else 0} activities")
    #             except Exception as e:
    #                 logger.error(f"🏃‍♂️ _fetch_from_strava failed: {e}")
    #                 import traceback
    #                 logger.error(f"🏃‍♂️ Full traceback: {traceback.format_exc()}")
    #                 fresh_activities = None
    #             
    #             if fresh_activities:
    #                 logger.info(f"🏃‍♂️ Fetched {len(fresh_activities)} activities with basic data from Strava")
    #                 
    #                 # Create initial cache with basic activity data
    #                 initial_cache = {
    #                     "timestamp": datetime.now().isoformat(),
    #                     "activities": fresh_activities,
    #                     "emergency_refresh": True,
    #                     "last_updated": datetime.now().isoformat()
    #                 }
    #                 
    #                 # Save the initial cache
    #                 self._save_cache(initial_cache)
    #                 logger.info("🏃‍♂️ Initial cache created with basic activity data")
    #                 
    #                 # Now start batch processing to enrich with rich data
    #                 self._start_batch_processing()
    #             else:
    #                 logger.warning("🏃‍♂️ No activities fetched from Strava API")
    #                 self._emergency_refresh_in_progress = False
    #                 
    #         except Exception as e:
    #             logger.error(f"🏃‍♂️ Emergency refresh worker failed: {e}")
    #             self._emergency_refresh_in_progress = False
    #     
    #     # Start the worker in a background thread
    #     import threading
    #     worker_thread = threading.Thread(target=emergency_refresh_worker, daemon=True)
    #     worker_thread.start()
    #     logger.info("🏃‍♂️ Emergency refresh worker thread started")
    
    
