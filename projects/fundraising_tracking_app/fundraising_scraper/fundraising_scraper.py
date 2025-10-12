#!/usr/bin/env python3
"""
Smart JustGiving Fundraising Scraper with Supabase Integration
Scrapes fundraising data from JustGiving page every 15 minutes
Uses hybrid caching strategy: In-Memory → JSON → Supabase → Emergency
"""

import httpx
import json
import time
import threading
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from bs4 import BeautifulSoup
import re
import os
import glob
from ..strava_integration.http_clients import get_http_client
from ..strava_integration.supabase_cache_manager import SecureSupabaseCacheManager

# Configure logging
logger = logging.getLogger(__name__)

class SmartFundraisingCache:
    def __init__(self, justgiving_url: str, cache_file: str = "projects/fundraising_tracking_app/fundraising_scraper/fundraising_cache.json"):
        self.justgiving_url = justgiving_url
        self.cache_file = cache_file
        self.backup_dir = os.path.join(os.path.dirname(cache_file), "backups")
        self.scraper_thread = None
        self.running = False
        
        # Cache management
        self._cache_data = None
        self._cache_loaded_at = None
        self._cache_ttl = 300  # 5 minutes in-memory cache TTL
        
        # Initialize Supabase cache manager for persistence
        self.supabase_cache = SecureSupabaseCacheManager()
        
        # Create directories if they don't exist
        os.makedirs(os.path.dirname(cache_file), exist_ok=True)
        os.makedirs(self.backup_dir, exist_ok=True)
        
        # Initialize cache system on startup
        self.initialize_cache_system()
        
        # Start the scraper
        self._start_scraper()
    
    def initialize_cache_system(self):
        """Initialize cache system on server startup"""
        logger.info("🔄 Initializing fundraising cache system on startup...")
        
        if self.supabase_cache.enabled:
            try:
                supabase_result = self.supabase_cache.get_cache('fundraising', 'fundraising-app')
                if supabase_result and supabase_result.get('data'):
                    cache_data = supabase_result['data']
                    
                    if self._validate_cache_integrity(cache_data):
                        self._save_cache_to_file(cache_data)
                        logger.info("✅ Fundraising cache system initialized from Supabase")
                        
                        should_refresh, reason = self._should_refresh_cache(cache_data)
                        if should_refresh:
                            logger.info(f"🔄 Fundraising cache needs refresh: {reason}")
                            self._trigger_emergency_refresh()
                        else:
                            logger.info("✅ Fundraising cache is fresh and valid")
                    else:
                        logger.warning("❌ Supabase fundraising data integrity check failed, triggering refresh...")
                        self._trigger_emergency_refresh()
                else:
                    logger.info("📭 No Supabase fundraising data found, will populate on first refresh")
            except Exception as e:
                logger.error(f"❌ Fundraising cache system initialization failed: {e}")
        else:
            logger.info("📝 Supabase disabled, using file-based fundraising cache only")
    
    def _start_scraper(self):
        """Start the automated scraper thread"""
        if self.scraper_thread and self.scraper_thread.is_alive():
            return
        
        self.running = True
        self.scraper_thread = threading.Thread(target=self._scraper_loop, daemon=True)
        self.scraper_thread.start()
        logger.info("🔄 Fundraising scraper started (15-minute intervals)")
    
    def _scraper_loop(self):
        """Main scraper loop - runs every 15 minutes"""
        while self.running:
            try:
                logger.info("🔍 Starting fundraising data scrape...")
                self._perform_smart_refresh()
                logger.info("✅ Fundraising scrape completed")
            except Exception as e:
                logger.error(f"❌ Fundraising scrape failed: {e}")
            
            # Wait 15 minutes (900 seconds)
            time.sleep(900)
    
    def _load_cache(self) -> Dict[str, Any]:
        """Load cache: In-Memory → JSON File → Supabase → Emergency Refresh"""
        now = datetime.now()
        
        # 1. Check in-memory cache first (fastest)
        if (self._cache_data is not None and 
            self._cache_loaded_at is not None and 
            (now - self._cache_loaded_at).total_seconds() < self._cache_ttl):
            logger.debug("✅ Using in-memory fundraising cache")
            return self._cache_data
        
        # 2. Try JSON file (populated from Supabase at startup)
        try:
            with open(self.cache_file, 'r') as f:
                self._cache_data = json.load(f)
                self._cache_loaded_at = now
                
                if self._validate_cache_integrity(self._cache_data):
                    logger.info("✅ Loaded fundraising cache from JSON file")
                    return self._cache_data
                else:
                    logger.warning("❌ JSON fundraising cache integrity check failed")
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.warning(f"❌ JSON fundraising cache file error: {e}")
        
        # 3. Fallback to Supabase (source of truth)
        if self.supabase_cache.enabled:
            try:
                supabase_result = self.supabase_cache.get_cache('fundraising', 'fundraising-app')
                if supabase_result and supabase_result.get('data'):
                    self._cache_data = supabase_result['data']
                    self._cache_loaded_at = now
                    
                    if self._validate_cache_integrity(self._cache_data):
                        logger.info("✅ Loaded fundraising cache from Supabase database")
                        self._save_cache_to_file(self._cache_data)
                        return self._cache_data
                    else:
                        logger.warning("❌ Supabase fundraising cache integrity check failed")
                else:
                    logger.info("📭 No fundraising cache data found in Supabase")
            except Exception as e:
                logger.error(f"❌ Supabase fundraising read failed: {e}")
        
        # 4. Emergency refresh (all sources failed)
        logger.warning("🚨 All fundraising cache sources failed, triggering emergency refresh...")
        self._cache_data = self._create_empty_cache()
        self._trigger_emergency_refresh()
        return self._cache_data
    
    def _save_cache_to_file(self, data: Dict[str, Any]):
        """Helper method to save cache to JSON file"""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.debug("✅ Saved fundraising cache to JSON file")
        except Exception as e:
            logger.error(f"❌ Failed to save fundraising cache to file: {e}")
    
    def _save_cache(self, data: Dict[str, Any]):
        """Save cache: Validate → File → Memory → Supabase (with retry)"""
        # 1. Validate data first
        if not self._validate_cache_integrity(data):
            logger.error("❌ Fundraising cache data validation failed, not saving")
            return
        
        # 2. Add timestamps to data
        data_with_timestamps = data.copy()
        data_with_timestamps['last_saved'] = datetime.now().isoformat()
        
        # 3. Save to JSON file (fast, reliable)
        self._save_cache_to_file(data_with_timestamps)
        
        # 4. Update in-memory cache
        self._cache_data = data_with_timestamps
        self._cache_loaded_at = datetime.now()
        
        # 5. Save to Supabase (with retry logic)
        if self.supabase_cache.enabled:
            try:
                last_fetch = None
                if data_with_timestamps.get('timestamp'):
                    last_fetch = datetime.fromisoformat(data_with_timestamps['timestamp'])
                
                success = self.supabase_cache.save_cache(
                    'fundraising',
                    data_with_timestamps,
                    last_fetch=last_fetch,
                    project_id='fundraising-app'
                )
                
                if success:
                    logger.info("✅ Fundraising cache saved to Supabase successfully")
                else:
                    logger.warning("⚠️ Failed to save fundraising cache to Supabase, will retry in background")
                    
            except Exception as e:
                logger.error(f"❌ Supabase fundraising save error: {e}")
                self._queue_supabase_save(data_with_timestamps, last_fetch)
    
    def _queue_supabase_save(self, data: Dict[str, Any], last_fetch: Optional[datetime] = None):
        """Queue data for background Supabase save"""
        if self.supabase_cache.enabled:
            self.supabase_cache._queue_supabase_save(
                'fundraising',
                data,
                last_fetch=last_fetch,
                project_id='fundraising-app'
            )
    
    def _should_refresh_cache(self, cache_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Determine if cache should be refreshed and why"""
        if not cache_data.get("timestamp"):
            return True, "No timestamp in cache"
        
        cache_time = datetime.fromisoformat(cache_data["timestamp"])
        expiry_time = cache_time + timedelta(minutes=15)  # 15-minute refresh for fundraising
        now = datetime.now()
        
        if now >= expiry_time:
            return True, f"Cache expired {now - expiry_time} ago"
        
        donations = cache_data.get("donations", [])
        if len(donations) < 1:
            return True, f"No donations found"
        
        if cache_data.get("emergency_refresh"):
            return True, "Emergency refresh flag set"
        
        return False, "Cache is valid"
    
    def get_cache_status(self) -> Dict[str, Any]:
        """Get comprehensive cache status for monitoring"""
        try:
            cache_data = self._load_cache()
            should_refresh, reason = self._should_refresh_cache(cache_data)
            
            status = {
                "cache_valid": not should_refresh,
                "should_refresh": should_refresh,
                "refresh_reason": reason,
                "donations_count": len(cache_data.get("donations", [])),
                "total_raised": cache_data.get("total_raised", 0),
                "last_fetch": cache_data.get("timestamp"),
                "last_saved": cache_data.get("last_saved"),
                "cache_duration_minutes": 15,
                "supabase_enabled": self.supabase_cache.enabled,
                "in_memory_cache_age": None,
                "emergency_refresh_flag": cache_data.get("emergency_refresh", False)
            }
            
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
    
    def _trigger_emergency_refresh(self):
        """Emergency refresh - rebuild from scraping when all sources fail"""
        try:
            logger.info("🚨 EMERGENCY REFRESH: Rebuilding fundraising cache from scraping...")
            
            import threading
            emergency_thread = threading.Thread(target=self._perform_emergency_refresh, daemon=True)
            emergency_thread.start()
            
            logger.info("🚨 Emergency fundraising refresh started in background thread")
            
        except Exception as e:
            logger.error(f"Failed to trigger emergency fundraising refresh: {e}")
    
    def _perform_emergency_refresh(self):
        """Emergency refresh - rebuild from scraping when all sources fail"""
        try:
            logger.info("🔄 Performing emergency fundraising refresh...")
            
            fresh_data = self._scrape_fundraising_data()
            
            logger.info(f"✅ Emergency refresh: Scraped fundraising data")
            
            emergency_cache = {
                "timestamp": datetime.now().isoformat(),
                "total_raised": fresh_data.get("total_raised", 0),
                "donations": fresh_data.get("donations", []),
                "total_donations": fresh_data.get("total_donations", 0),
                "emergency_refresh": False,  # Clear the flag after successful refresh
                "last_updated": datetime.now().isoformat()
            }
            
            self._save_cache(emergency_cache)
            
            self._cache_data = emergency_cache
            self._cache_loaded_at = datetime.now()
            
            logger.info(f"✅ Emergency fundraising refresh complete")
            
        except Exception as e:
            logger.error(f"❌ Emergency fundraising refresh failed: {e}")
    
    def _create_empty_cache(self) -> Dict[str, Any]:
        """Create an empty cache structure"""
        return {
            "timestamp": None,
            "total_raised": 0.0,
            "donations": [],
            "total_donations": 0,
            "last_updated": None,
            "emergency_refresh": False
        }
    
    def _validate_cache_integrity(self, cache_data: Dict[str, Any]) -> bool:
        """Validate cache data integrity"""
        if not isinstance(cache_data, dict):
            return False
        
        required_fields = ["timestamp", "total_raised", "donations"]
        for field in required_fields:
            if field not in cache_data:
                logger.warning(f"Missing required field: {field}")
                return False
        
        # Check donations structure
        donations = cache_data.get("donations", [])
        if not isinstance(donations, list):
            logger.warning("Donations field is not a list")
            return False
        
        # Check total_raised is numeric
        total_raised = cache_data.get("total_raised", 0)
        if not isinstance(total_raised, (int, float)):
            logger.warning("Total raised is not numeric")
            return False
        
        return True
    
    def _perform_smart_refresh(self):
        """Perform smart refresh based on cache status"""
        cache_data = self._load_cache()
        should_refresh, reason = self._should_refresh_cache(cache_data)
        
        if should_refresh:
            logger.info(f"🔄 Fundraising cache refresh needed: {reason}")
            self._refresh_cache()
        else:
            logger.info("✅ Fundraising cache is still valid, skipping refresh")
    
    def _refresh_cache(self):
        """Refresh the cache with new data"""
        try:
            logger.info("🔄 Refreshing fundraising cache...")
            fresh_data = self._scrape_fundraising_data()
            
            if fresh_data:
                self._save_cache(fresh_data)
                logger.info("✅ Fundraising cache refreshed successfully")
            else:
                logger.warning("⚠️ No fresh data received, keeping existing cache")
                
        except Exception as e:
            logger.error(f"❌ Failed to refresh fundraising cache: {e}")
    
    def _scrape_fundraising_data(self) -> Dict[str, Any]:
        """Scrape fundraising data from JustGiving"""
        try:
            logger.info(f"🔍 Scraping fundraising data from: {self.justgiving_url}")
            
            # Use httpx directly instead of the shared client to avoid reuse issues
            with httpx.Client(timeout=30.0) as client:
                response = client.get(self.justgiving_url)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Extract JSON data from script tags (modern JustGiving uses React/Next.js)
                total_raised = 0.0
                donations = []
                target_amount = 0.0
                
                # Look for JSON data in script tags using regex patterns
                script_tags = soup.find_all('script')
                for script in script_tags:
                    if script.string and 'donationSummary' in script.string and 'Gabriella Cook' in script.string:
                        script_content = script.string
                        logger.info("Found script with donation data")
                        
                # Extract total amount using regex - updated pattern
                total_match = re.search(r'"totalAmount":\{"value":(\d+),"currencyCode":"GBP"', script_content)
                if total_match:
                    total_raised = float(total_match.group(1)) / 100  # Convert from pence
                    logger.info(f"Found total amount: £{total_raised:.2f}")
                
                # Extract donation count
                count_match = re.search(r'"donationCount":(\d+)', script_content)
                if count_match:
                    donation_count = int(count_match.group(1))
                    logger.info(f"Found donation count: {donation_count}")
                
                # Extract target amount - updated pattern
                target_match = re.search(r'"targetWithCurrency":\{"value":(\d+),"currencyCode":"GBP"', script_content)
                if target_match:
                    target_amount = float(target_match.group(1)) / 100
                    logger.info(f"Found target amount: £{target_amount:.2f}")
                
                # Extract individual donations using regex - updated pattern
                donation_pattern = r'"displayName":"([^"]+)","avatar":"[^"]*","message":"([^"]*)"[^}]*"amount":\{"value":(\d+),"currencyCode":"GBP"'
                donation_matches = re.findall(donation_pattern, script_content)
                        
                        for name, message, amount_str in donation_matches:
                            try:
                                amount = float(amount_str) / 100
                                donation_data_item = {
                                    "amount": amount,
                                    "name": name,
                                    "message": message,
                                    "timestamp": datetime.now().isoformat()
                                }
                                donations.append(donation_data_item)
                                logger.info(f"Found donation: {name} - £{amount:.2f} - {message}")
                            except Exception as e:
                                logger.warning(f"Error parsing donation: {e}")
                                continue
                        
                        if total_raised > 0 or donations:
                            logger.info(f"✅ Successfully parsed fundraising data: £{total_raised:.2f} raised from {len(donations)} donations")
                            break
                
                # Fallback to old method if JSON parsing failed
                if total_raised == 0.0 and not donations:
                    logger.info("🔄 JSON parsing failed, trying fallback HTML parsing...")
                    
                    # Try to find total in HTML
                    total_elements = soup.find_all(text=re.compile(r'£\d+\.?\d*'))
                    for element in total_elements:
                        if 'total' in element.parent.get_text().lower() or 'raised' in element.parent.get_text().lower():
                            total_text = re.sub(r'[£$€,]', '', element.strip())
                            try:
                                total_raised = float(total_text)
                                break
                            except ValueError:
                                continue
                
                return {
                    "timestamp": datetime.now().isoformat(),
                    "total_raised": total_raised,
                    "target_amount": target_amount,
                    "donations": donations,
                    "total_donations": len(donations),
                    "last_updated": datetime.now().isoformat(),
                    "justgiving_url": self.justgiving_url
                }
                
        except Exception as e:
            logger.error(f"❌ Failed to scrape fundraising data: {e}")
            return None
    
    def get_fundraising_data(self) -> Dict[str, Any]:
        """Get current fundraising data"""
        return self._load_cache()
    
    def stop(self):
        """Stop the scraper"""
        self.running = False
        if self.scraper_thread and self.scraper_thread.is_alive():
            self.scraper_thread.join(timeout=5)
        logger.info("🛑 Fundraising scraper stopped")
