#!/usr/bin/env python3
"""
Activity Caching Strategy
Manages activity data from GPX imports with music detection and rich data support
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
from .http_clients import get_http_client
from .supabase_cache_manager import SecureSupabaseCacheManager
import os

# Configure enhanced logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('activity_integration.log')
    ]
)
logger = logging.getLogger(__name__)

# Performance logging is handled by the main logger

load_dotenv()

class ActivityCache:
    def __init__(self, cache_duration_hours: int = None):
        # Using GPX import from Google Sheets as data source
        # JSON cache file removed - using Supabase-only storage
        
        # Initialize Supabase cache manager for persistence
        self.supabase_cache = SecureSupabaseCacheManager()
        
        # Allow custom cache duration, default to 8 hours
        self.cache_duration_hours = cache_duration_hours or int(os.getenv("ACTIVITY_CACHE_HOURS", "8"))
        
        # Filtering criteria
        self.allowed_activity_types = ["Run", "Ride"]  # Only runs and bike rides
        
        # Performance optimizations
        self._cache_data = None  # In-memory cache
        self._cache_loaded_at = None
        self._cache_ttl = 300  # 5 minutes in-memory cache TTL
        
        # Background services tracking
        self._background_services_started = False
        
        # Initialize cache system on startup (synchronous - no background operations)
        self.initialize_cache_system_sync()
    
    def start_background_services(self):
        """Start background services (Supabase retry + corruption check only)"""
        if self._background_services_started:
            logger.info("🔄 Background services already started")
            return
        
        logger.info("🔄 Starting background services...")
        
        try:
            # Start Supabase background retry service (for network retries)
            self.supabase_cache.start_background_services()
            
            # Start the daily corruption check scheduler (useful for data integrity)
            self._schedule_daily_corruption_check()
            
            self._background_services_started = True
            logger.info("✅ Background services started (Supabase retry + corruption check)")
            
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
                supabase_result = self.supabase_cache.get_cache('activities', 'fundraising-app')
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
                supabase_result = self.supabase_cache.get_cache('activities', 'fundraising-app')
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
                supabase_result = self.supabase_cache.get_cache('activities', 'fundraising-app')
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
        
        # 4. Emergency refresh disabled - activities are imported manually via GPX
        if trigger_emergency_refresh:
            logger.info("📥 Emergency refresh disabled - import activities via GPX: POST /api/activity-integration/gpx/import-from-sheets")
        else:
            # No cache data found - return empty cache
            logger.info("📥 No cache data found. Import activities via GPX: POST /api/activity-integration/gpx/import-from-sheets")
            self._cache_data = {"timestamp": None, "activities": []}
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
                    'activities',
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
                'activities',
                data,
                last_fetch=last_fetch,
                last_rich_fetch=last_rich_fetch,
                project_id='fundraising-app'
            )
    
    def add_gpx_activities(self, gpx_activities: List[Dict[str, Any]]) -> int:
        """Add GPX-imported activities to the cache, merging with existing activities"""
        try:
            logger.info(f"📥 Adding {len(gpx_activities)} GPX activities to cache")
            
            # Load existing cache
            cache_data = self._load_cache()
            existing_activities = cache_data.get("activities", []) if cache_data else []
            
            # Create lookup by ID
            existing_by_id = {str(act.get("id")): act for act in existing_activities}
            
            # Merge GPX activities with existing
            new_count = 0
            updated_count = 0
            
            for gpx_activity in gpx_activities:
                activity_id = str(gpx_activity.get("id"))
                
                # Format activity to match expected structure (activity format)
                formatted_activity = {
                    "id": gpx_activity.get("id"),
                    "name": gpx_activity.get("name"),
                    "type": gpx_activity.get("type"),
                    "distance": gpx_activity.get("distance", 0),
                    "moving_time": gpx_activity.get("moving_time", 0),
                    "elapsed_time": gpx_activity.get("elapsed_time", 0),
                    "total_elevation_gain": gpx_activity.get("total_elevation_gain", 0),
                    "start_date": gpx_activity.get("start_date"),
                    "start_date_local": gpx_activity.get("start_date_local") or gpx_activity.get("start_date"),
                    "description": gpx_activity.get("description", ""),
                    "map": {
                        "polyline": gpx_activity.get("polyline"),
                        "bounds": gpx_activity.get("bounds")
                    },
                    "photos": gpx_activity.get("photos", []),
                    "comments": gpx_activity.get("comments", []),
                    "music": gpx_activity.get("music", {}),  # Preserve music data (added during processing)
                    "source": "gpx_import"
                }
                
                if activity_id in existing_by_id:
                    # Merge with existing - preserve existing rich data
                    existing = existing_by_id[activity_id]
                    # Keep existing rich data
                    if existing.get("photos"):
                        formatted_activity["photos"] = existing.get("photos")
                    if existing.get("comments"):
                        formatted_activity["comments"] = existing.get("comments")
                    if existing.get("description") and not formatted_activity.get("description"):
                        formatted_activity["description"] = existing.get("description")
                    # Preserve existing music if new one is empty
                    if existing.get("music") and not formatted_activity.get("music"):
                        formatted_activity["music"] = existing.get("music")
                    
                    existing_by_id[activity_id] = formatted_activity
                    updated_count += 1
                else:
                    # New activity
                    existing_by_id[activity_id] = formatted_activity
                    new_count += 1
            
            # Convert back to list
            merged_activities = list(existing_by_id.values())
            
            # Create updated cache data
            updated_cache = {
                "timestamp": datetime.now().isoformat(),
                "activities": merged_activities,
                "last_gpx_import": datetime.now().isoformat()
            }
            
            # Save to cache
            self._save_cache(updated_cache)
            
            logger.info(f"✅ Added {new_count} new GPX activities, updated {updated_count} existing")
            return new_count
            
        except Exception as e:
            logger.error(f"❌ Failed to add GPX activities: {e}")
            return 0
    
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
        """Cache refresh check - disabled since activities are imported manually"""
        # Always return False - no automatic refresh needed
        return False, "Activities are imported manually via GPX import"
    
    def _should_trigger_8hour_refresh(self) -> bool:
        """8-hour refresh check - disabled since activities are imported manually"""
        # Always return False - no automatic refresh needed
        return False
    
    


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


    def _has_music_patterns(self, description: str) -> bool:
        """Check if description contains music detection patterns"""
        if not description:
            return False
        
        # Music detection patterns
        album_pattern = r"Album:\s*([^,\n]+?)\s+by\s+([^,\n]+)"
        russell_radio_pattern = r"Russell Radio:\s*([^,\n]+?)\s+by\s+([^,\n]+)"
        track_pattern = r"Track:\s*([^,\n]+?)\s+by\s+([^,\n]+)"
        playlist_pattern = r"Playlist:\s*([^,\n]+)"
        
        return (bool(re.search(album_pattern, description, re.IGNORECASE)) or
                bool(re.search(russell_radio_pattern, description, re.IGNORECASE)) or
                bool(re.search(track_pattern, description, re.IGNORECASE)) or
                bool(re.search(playlist_pattern, description, re.IGNORECASE)))


    
    
    
    
    def _validate_cache_integrity_for_corruption(self, activities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate cache data integrity - check for missing or invalid fields"""
        corrupted_activities = []
        
        for activity in activities:
            activity_id = activity.get("id")
            if not activity_id:
                continue
            
            corruption_reasons = []
            
            # Check for missing essential fields
            if not activity.get("name"):
                corruption_reasons.append("missing_name")
            
            if activity.get("distance") is None or activity.get("distance") == 0:
                corruption_reasons.append("missing_or_zero_distance")
            
            # Check for invalid map data
            map_data = activity.get("map", {})
            if map_data and not map_data.get("polyline") and not map_data.get("bounds"):
                corruption_reasons.append("invalid_map_data")
            
            if corruption_reasons:
                corrupted_activities.append({
                    "id": activity_id,
                    "name": activity.get("name", "Unknown"),
                    "reasons": corruption_reasons
                })
                logger.warning(f"🚨 Data integrity issue in activity {activity_id}: {corruption_reasons}")
        
        return {
            "corruption_detected": len(corrupted_activities) > 0,
            "corrupted_activities": corrupted_activities,
            "total_checked": len(activities),
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
        """Execute daily corruption check at 2am - fetch fresh data and detect corruption"""
        logger.info("🕐 Starting daily corruption check...")
        
        try:
            # Corruption check: Validate existing cache data for integrity
            # No API calls needed - activities come from GPX import
            logger.info("🔄 Starting corruption check on existing cache data...")
            cache_data = self._load_cache()
            if not cache_data or not cache_data.get("activities"):
                logger.info("📥 No cache data found - import activities via GPX import endpoint")
                return
            
            existing_activities = cache_data.get("activities", [])
            raw_data = existing_activities  # Use existing cache data for validation
            logger.info(f"🔄 Fetched {len(raw_data)} raw activities for corruption check")
            
            # Step 3: Filter for runs/rides from May 22nd, 2025 onwards
            basic_data = self._filter_activities(raw_data)
            logger.info(f"🔄 Filtered to {len(basic_data)} runs/rides for corruption check")
            
            # Step 4: Validate existing cache data integrity (no API fetch needed)
            logger.info("🔄 Validating cache data integrity...")
            # Compare existing activities against themselves to detect missing/invalid data
            corruption_analysis = self._validate_cache_integrity_for_corruption(raw_data)
            
            # Step 6: Handle corruption if detected
            if corruption_analysis["corruption_detected"]:
                corrupted_count = len(corruption_analysis["corrupted_activities"])
                logger.warning(f"🚨 Corruption detected in {corrupted_count} activities!")
                
                # Log details of corrupted activities
                for corrupted in corruption_analysis["corrupted_activities"]:
                    logger.warning(f"🚨 Activity {corrupted['id']} ({corrupted['name']}): {corrupted['reasons']}")
                
                # Note: Data repair requires re-importing via GPX import endpoint
                logger.info("💡 To repair: Re-import activities via GPX import endpoint")
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
        """Refresh check - no longer needed since activities are imported manually"""
        # This method is kept for API compatibility but does nothing
        # Activities are imported via GPX import endpoint, not auto-refreshed
        return {
            "status": "manual_import_required",
            "message": "Activities are imported manually via GPX. Use POST /api/activity-integration/gpx/import-from-sheets"
        }
    
    
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
        """Only sanitize user input fields"""
        user_input_fields = ['comments', 'donation_messages', 'donor_names']
        # Simplified for now - full implementation in supabase_cache_manager.py
        return data
    
    def get_activities_smart(self, limit: int = 1000, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        Get activities with smart caching strategy
        Uses cache from Supabase (populated via GPX import from Google Sheets)
        """
        start_time = time.time()
        cache_data = self._load_cache()
        
        # Handle None cache_data
        if cache_data is None:
            logger.warning("No cached data available. Import activities via GPX import endpoint.")
            return []
        
        # Use cache if valid and not forcing refresh
        if not force_refresh and self._is_cache_valid(cache_data):
            logger.info(f"Using cached data ({len(cache_data.get('activities', []))} activities)")
            logger.info(f"Cache hit - {time.time() - start_time:.3f}s")
            return cache_data.get("activities", [])[:limit]
        
        # Cache is invalid - return what we have or empty list
        # Activities are now imported via GPX, not fetched from API
        if cache_data.get("activities"):
            logger.warning("Cache expired, returning cached data. Refresh via GPX import if needed.")
            return cache_data["activities"][:limit]
        else:
            logger.warning("No cached data available. Import activities via GPX import endpoint.")
            return []
    

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

