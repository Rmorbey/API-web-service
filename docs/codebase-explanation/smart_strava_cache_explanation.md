# 📚 SmartStravaCache - Complete Code Explanation

## 🎯 **Overview**

This is the **core data management class** of your Strava integration. It handles fetching data from Strava, caching it intelligently, and managing the complex logic of when to refresh data. Think of it as the **brain** that decides what data to fetch, when to fetch it, and how to store it efficiently.

## 📁 **File Structure Context**

```
smart_strava_cache.py  ← YOU ARE HERE (Core Data Management)
├── strava_integration_api.py  (Uses this class)
├── strava_token_manager.py    (Manages authentication)
├── http_clients.py            (HTTP connection pooling)
└── models.py                  (Data structures)
```

## 🔍 **Line-by-Line Code Explanation**

### **1. Imports and Setup (Lines 1-35)**

```python
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
```

**What this does:**
- **Standard library imports**: `os`, `json`, `time`, `logging`, `threading` for basic functionality
- **`httpx`**: Modern HTTP client for making API requests
- **`datetime`**: For handling timestamps and time-based logic
- **`typing`**: For type hints (makes code more readable and catchable)
- **Custom imports**: Your own modules for token management and HTTP clients

```python
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
```

**What this does:**
- **Logging configuration**: Sets up logging to both console and file
- **Log levels**: INFO level captures important events
- **Log format**: Timestamp, logger name, level, and message
- **File logging**: Saves logs to `strava_integration_new.log`

### **2. Class Initialization (Lines 36-70)**

```python
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
        self.max_calls_per_day = 1000
```

**What this does:**
- **Token manager**: Handles Strava authentication
- **Base URL**: Strava API endpoint
- **Cache file**: Local JSON fallback storage
- **Supabase integration**: Primary persistent cache storage
- **Cache duration**: How long to keep data (6 hours default)
- **Activity filtering**: Only fetch runs and bike rides
- **Rate limiting**: Track API calls to avoid hitting limits

```python
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
```

**What this does:**
- **In-memory cache**: Keeps data in RAM for faster access
- **TTL (Time To Live)**: 5 minutes for in-memory cache
- **Start date**: Only fetch activities from May 22, 2025 onwards
- **Automated refresh**: Background system that updates data automatically
- **Threading**: Uses threads for background processing

### **2.1. Hybrid Caching Strategy**

The system uses a **three-tier caching approach**:

1. **Supabase Database** (Primary): Persistent storage for production deployment
2. **Local JSON File** (Fallback): Development and resilience backup
3. **In-Memory Cache** (Performance): Fast access for active requests

This ensures data persistence across server restarts while maintaining high performance.

### **3. Cache Loading and Validation (Lines 71-131)**

```python
def _load_cache(self) -> Dict[str, Any]:
    """Load cache from file with in-memory optimization and corruption detection"""
    now = datetime.now()
    
    # Check if in-memory cache is still valid
    if (self._cache_data is not None and 
        self._cache_loaded_at is not None and 
        (now - self._cache_loaded_at).total_seconds() < self._cache_ttl):
        return self._cache_data
```

**What this does:**
- **In-memory optimization**: If data is already in memory and fresh, use it
- **TTL check**: Only use in-memory data if it's less than 5 minutes old
- **Performance**: Avoids reading from disk if data is already in memory

```python
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
```

**What this does:**
- **File loading**: Reads cache from JSON file
- **Integrity validation**: Checks if cache data is valid
- **Backup restoration**: If cache is corrupted, tries to restore from backup
- **Emergency refresh**: If all else fails, rebuilds cache from scratch
- **Error handling**: Graceful degradation when things go wrong

### **4. Cache Validation and Filtering (Lines 122-158)**

```python
def _is_cache_valid(self, cache_data: Dict[str, Any]) -> bool:
    """Check if cache is still valid"""
    if not cache_data.get("timestamp"):
        return False
    
    cache_time = datetime.fromisoformat(cache_data["timestamp"])
    expiry_time = cache_time + timedelta(hours=self.cache_duration_hours)
    
    return datetime.now() < expiry_time
```

**What this does:**
- **Timestamp check**: Ensures cache has a timestamp
- **Expiry calculation**: Adds cache duration to timestamp
- **Current time check**: Returns True if cache hasn't expired

```python
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
```

**What this does:**
- **Activity type filtering**: Only keeps runs and bike rides
- **Invalid activity filtering**: Removes activities with missing data
- **Date filtering**: Only keeps activities from May 22, 2025 onwards
- **Error handling**: Gracefully handles date parsing errors

### **5. Rate Limiting (Lines 160-182)**

```python
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
```

**What this does:**
- **15-minute reset**: Resets counter every 15 minutes
- **Rate limit checking**: Ensures we don't exceed Strava's limits
- **Daily limit**: Basic daily limit tracking
- **Returns tuple**: (can_make_call, message)

### **6. API Call with Retry Logic (Lines 184-236)**

```python
def _make_api_call_with_retry(self, url: str, headers: Dict[str, str], max_retries: int = 3) -> httpx.Response:
    """Make an API call with retry logic and error handling using optimized HTTP client"""
    for attempt in range(max_retries):
        try:
            # Check rate limits before making call
            can_call, message = self._check_api_limits()
            if not can_call:
                raise Exception(f"Rate limit exceeded: {message}")
            
            # Make the API call using shared HTTP client with connection pooling
            http_client = get_http_client()
            response = http_client.get(url, headers=headers)
            
            # Record the API call
            self._record_api_call()
```

**What this does:**
- **Retry loop**: Tries up to 3 times if call fails
- **Rate limit check**: Ensures we don't exceed limits
- **HTTP client**: Uses shared client with connection pooling
- **Call recording**: Tracks API usage

```python
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
```

**What this does:**
- **200 OK**: Success, return response
- **401 Unauthorized**: Token expired, try to refresh
- **429 Too Many Requests**: Rate limited, wait and retry
- **Error handling**: Proper error messages for different scenarios

### **7. Main Data Fetching Method (Lines 238-298)**

```python
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
```

**What this does:**
- **Main entry point**: This is what the API calls
- **Cache check**: Uses cached data if it's still valid
- **Performance logging**: Tracks how long operations take
- **Limit application**: Only returns requested number of activities

```python
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
```

**What this does:**
- **Smart refresh**: When cache expires, fetch new data
- **Fresh data**: Get latest activities from Strava
- **Filtering**: Remove unwanted activities
- **Smart merge**: Combine new data with existing rich data
- **Rich data update**: Check all activities for missing data

### **8. Smart Merge Logic (Lines 669-738)**

```python
def _smart_merge_activities(self, existing_activities: List[Dict[str, Any]], fresh_activities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Smart merge: Preserve ALL existing data, update only basic fields from fresh data
    FIXED: Never overwrite existing activities with fresh data to prevent data loss
    """
    # Clean existing activities first to remove any invalid entries
    existing_activities = self._clean_invalid_activities(existing_activities)
    
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
            # NEW ACTIVITY: Use fresh data
            merged_activity = fresh_activity
            logger.info(f"New activity {activity_id}: {fresh_activity.get('name', 'Unknown')}")
```

**What this does:**
- **Data preservation**: Never overwrites existing rich data
- **Lookup maps**: Fast lookup by activity ID
- **Basic field updates**: Only updates fields that might change
- **New activity handling**: Uses fresh data for new activities
- **Order preservation**: Maintains Strava's activity order

### **9. Rich Data Collection Logic (Lines 740-850)**

```python
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
```

**What this does:**
- **Comprehensive check**: Looks at ALL activities within 3 weeks
- **Data type determination**: Different logic for essential vs optional data
- **Retry tracking**: Keeps track of how many times we've tried
- **Smart retry logic**: Different limits for different data types

### **10. Retry Logic and Data Types (Lines 407-431)**

```python
def _should_attempt_rich_data_update(self, activity: Dict[str, Any]) -> bool:
    """Check if we should attempt to update rich data for this activity"""
    # Check if activity is recent enough
    if not self._is_activity_recent_enough(activity):
        return False
    
    # Check if enough time has passed since last retry (24 hours)
    if not self._can_retry_rich_data(activity):
        return False
    
    # Get what data is missing
    missing_data = self._get_missing_rich_data(activity)
    retry_count = self._get_rich_data_retry_count(activity)
    
    # If we have essential map data (polyline + bounds), only try 5 times for optional data
    if self._has_essential_map_data(activity):
        if retry_count >= 5:
            # Already tried 5 times for optional data, don't try again
            return False
        # Try to get optional rich data (description, photos, comments)
        return missing_data["description"] or missing_data["photos"] or missing_data["comments"]
    
    # If we don't have essential map data, keep trying (unlimited attempts)
    return missing_data["polyline"] or missing_data["bounds"]
```

**What this does:**
- **Age check**: Only tries for activities less than 3 weeks old
- **Time check**: Only tries if 24 hours have passed since last attempt
- **Data type logic**: Different retry limits for different data types
- **Essential data**: Unlimited retries for polyline and bounds
- **Optional data**: Only 5 retries for description, photos, comments

## 🎯 **Key Learning Points**

### **1. Caching Strategy**
- **Multi-level caching**: In-memory + file-based caching
- **Smart invalidation**: Only refreshes when necessary
- **Data preservation**: Never loses existing rich data

### **2. Rate Limiting**
- **Proactive checking**: Checks limits before making calls
- **Retry logic**: Handles rate limits gracefully
- **Exponential backoff**: Waits longer between retries

### **3. Error Handling**
- **Graceful degradation**: Falls back to cached data on errors
- **Backup restoration**: Tries to restore from backups
- **Comprehensive logging**: Tracks all operations

### **4. Data Management**
- **Smart merging**: Preserves existing data while updating basic fields
- **Rich data collection**: Intelligently fetches missing data
- **Retry logic**: Different strategies for different data types

### **5. Performance Optimization**
- **In-memory caching**: Fast access to frequently used data
- **Connection pooling**: Reuses HTTP connections
- **Batch processing**: Processes multiple activities efficiently

## 🚀 **How This Fits Into Your Learning**

This class demonstrates:
- **Advanced caching patterns**: Multi-level, smart invalidation
- **Rate limiting**: Proactive and reactive rate limit handling
- **Error handling**: Comprehensive error management and recovery
- **Data management**: Smart merging and preservation strategies
- **Performance optimization**: Multiple techniques for speed and efficiency

**Next**: We'll explore the `StravaTokenManager` to understand how authentication works! 🎉
