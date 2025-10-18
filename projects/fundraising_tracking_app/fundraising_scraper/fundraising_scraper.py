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
        self._scraper_lock = threading.Lock()  # Thread safety for scraper state
        
        # Cache management
        self._cache_data = None
        self._cache_loaded_at = None
        self._cache_ttl = 300  # 5 minutes in-memory cache TTL
        
        # Initialize Supabase cache manager for persistence
        self.supabase_cache = SecureSupabaseCacheManager()
        
        # Create directories if they don't exist
        os.makedirs(os.path.dirname(cache_file), exist_ok=True)
        os.makedirs(self.backup_dir, exist_ok=True)
        
        # Startup phase tracking
        self._startup_phase = "initialized"
        self._background_services_started = False
        
        # Initialize cache system on startup (synchronous - no background operations)
        self.initialize_cache_system_sync()
    
    def start_background_services(self):
        """Start background services after main startup is complete (Phase 3)"""
        if self._background_services_started:
            logger.info("🔄 Fundraising background services already started")
            return
        
        logger.info("🔄 Starting fundraising background services...")
        
        try:
            # Start Supabase background services first
            self.supabase_cache.start_background_services()
            
            # Check if we need to trigger emergency refresh (no cache data found during sync init)
            if not self._cache_data:
                logger.info("🔄 No fundraising cache data found during sync init - scheduling emergency refresh for after startup")
                # Defer emergency refresh to avoid blocking startup
                def deferred_emergency_refresh():
                    time.sleep(15)  # Wait 15 seconds for main app to fully start
                    logger.info("🔄 Starting deferred fundraising emergency refresh...")
                    try:
                        self.initialize_cache_system()  # This will trigger emergency refresh
                        logger.info("✅ Fundraising emergency refresh completed successfully")
                    except Exception as e:
                        logger.error(f"❌ Deferred fundraising emergency refresh failed: {e}")
                        import traceback
                        logger.error(f"❌ Full traceback: {traceback.format_exc()}")
                
                emergency_thread = threading.Thread(target=deferred_emergency_refresh, daemon=True)
                emergency_thread.start()
                logger.info("🔄 Fundraising emergency refresh scheduled for 15 seconds after startup")
            
            # Start the scraper
            self._start_scraper()
            
            self._background_services_started = True
            self._startup_phase = "background_services_started"
            logger.info("✅ Fundraising background services started successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to start fundraising background services: {e}")
            self._startup_phase = "background_services_failed"
    
    def initialize_cache_system_sync(self):
        """Initialize cache system synchronously (Phase 2) - no background operations"""
        logger.info("🔄 Initializing fundraising cache system synchronously...")
        
        # Only load existing cache data, don't trigger any background operations
        try:
            # Try to load existing cache data
            cache_data = self._load_cache_sync()
            if cache_data:
                logger.info("✅ Fundraising cache system initialized with existing data")
            else:
                logger.info("📭 No existing fundraising cache data found - will populate in background")
        except Exception as e:
            logger.error(f"❌ Failed to initialize fundraising cache system: {e}")
    
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
                supabase_result = self.supabase_cache.get_cache('fundraising', 'fundraising-app')
                if supabase_result and supabase_result.get('data'):
                    cache_data = supabase_result['data']
                    
                    # Validate data integrity
                    if self._validate_cache_integrity(cache_data):
                        self._cache_data = cache_data
                        self._cache_loaded_at = now
                        return cache_data
            except Exception as e:
                logger.error(f"❌ Failed to load fundraising data from Supabase: {e}")
        
        return None
    
    def initialize_cache_system(self):
        """Initialize cache system on server startup (legacy method for background operations)"""
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
        
        with self._scraper_lock:  # Thread-safe scraper start
            self.running = True
            self.scraper_thread = threading.Thread(target=self._scraper_loop, daemon=True)
            self.scraper_thread.start()
            logger.info("🔄 Fundraising scraper started (15-minute intervals)")
    
    def stop_scraper(self):
        """Stop the fundraising scraper (thread-safe)"""
        with self._scraper_lock:
            self.running = False
            logger.info("🛑 Fundraising scraper stopped")
    
    def _scraper_loop(self):
        """Main scraper loop - runs every 15 minutes (thread-safe)"""
        while True:
            with self._scraper_lock:  # Thread-safe check of running state
                if not self.running:
                    break
            
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
        now = datetime.now()  # Use server timezone (will be Europe/London)
        
        # Debug logging to understand time comparison (only log when cache is about to expire)
        time_until_expiry = expiry_time - now
        if time_until_expiry.total_seconds() < 300:  # Less than 5 minutes
            logger.info(f"⏰ Cache expiring soon: {time_until_expiry} remaining")
            logger.info(f"🕐 Cache time: {cache_time}")
            logger.info(f"🕐 Current time: {now}")
            logger.info(f"🕐 Expiry time: {expiry_time}")
            logger.info(f"🕐 Cache age: {now - cache_time}")
        
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
                "emergency_refresh": True,
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
        """Scrape fundraising data from JustGiving page"""
        try:
            # Set headers to mimic a real browser
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }

            # Make request to JustGiving page using shared HTTP client
            http_client = get_http_client()
            response = http_client.get(self.justgiving_url, headers=headers)
            response.raise_for_status()
            
            # Parse HTML
            soup = BeautifulSoup(response.content, 'lxml')
            
            # Extract total amount raised
            total_raised = self._extract_total_raised(soup)

            # Extract donations
            donations = self._extract_donations(soup)

            # Create fresh data (will be merged with existing)
            fresh_data = {
                "timestamp": datetime.now().isoformat(),
                "total_raised": total_raised,
                "donations": donations,
                "total_donations": len(donations),
                "last_updated": datetime.now().isoformat()
            }

            logger.info(f"💰 Scraped: £{total_raised} raised, {len(donations)} donations")
            return fresh_data

        except Exception as e:
            logger.error(f"Failed to scrape fundraising data: {e}")
            raise
    
    def _extract_total_raised(self, soup: BeautifulSoup) -> float:
        """Extract total amount raised from the page"""
        try:
            # Try multiple selectors for the total raised amount
            selectors = [
                # Main total display
                'p.branded-text.cp-heading-medium.m-0',
                # Alternative total display
                'div.cp-body-large',
                # Fallback to any branded-text with amount
                'p.branded-text',
                'div.branded-text'
            ]
            
            for selector in selectors:
                elements = soup.select(selector)
                for element in elements:
                    amount_text = element.get_text(strip=True)
                    # Look for amount pattern like "£15" or "£15.00" or "£1,234"
                    amount_match = re.search(r'£([\d,]+\.?\d*)', amount_text)
                    if amount_match:
                        # Remove commas and convert to float
                        amount_str = amount_match.group(1).replace(',', '')
                        amount = float(amount_str)
                        logger.info(f"Found total raised: £{amount}")
                        return amount
            
            # If no branded text found, look for any element containing £ symbol
            all_elements = soup.find_all(text=re.compile(r'£[\d,]+\.?\d*'))
            for element in all_elements:
                amount_match = re.search(r'£([\d,]+\.?\d*)', element.strip())
                if amount_match:
                    amount_str = amount_match.group(1).replace(',', '')
                    amount = float(amount_str)
                    logger.info(f"Found total raised in text: £{amount}")
                    return amount

            logger.warning("Could not find total raised amount")
            return 0.0

        except Exception as e:
            logger.error(f"Error extracting total raised: {e}")
            return 0.0

    def _extract_donations(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract individual donations from the page"""
        donations = []

        try:
            # Find all supporter detail sections
            supporter_sections = soup.find_all('header', class_='SupporterDetails_header__3czW_')
            
            for section in supporter_sections:
                try:
                    donation = self._extract_single_donation(section)
                    if donation:
                        donations.append(donation)
                except Exception as e:
                    logger.warning(f"Error extracting single donation: {e}")
                    continue
            
            logger.info(f"Extracted {len(donations)} donations")
            return donations
            
        except Exception as e:
            logger.error(f"Error extracting donations: {e}")
            return []

    def _extract_single_donation(self, header_section) -> Optional[Dict[str, Any]]:
        """Extract data from a single donation section"""
        try:
            # Find the parent container
            supporter_container = header_section.find_parent()
            if not supporter_container:
                return None
            
            # Extract donor name
            name_element = header_section.find('h2', class_='SupporterDetails_donorName__f_tha')
            donor_name = name_element.get_text(strip=True) if name_element else "Anonymous"
            
            # Extract donation date
            date_element = header_section.find('span', class_='SupporterDetails_date__zEBmC')
            donation_date = date_element.get_text(strip=True) if date_element else "Unknown"
            
            # Extract donation amount
            amount_element = supporter_container.find('div', class_='SupporterDetails_amount__LzYvS')
            amount_text = amount_element.get_text(strip=True) if amount_element else "£0"
            amount_match = re.search(r'£([\d,]+\.?\d*)', amount_text)
            amount = float(amount_match.group(1).replace(',', '')) if amount_match else 0.0
            
            # Extract donation message (optional)
            message_element = supporter_container.find('span', class_='SupporterDetails_donationMessage__IPPow')
            message = message_element.get_text(strip=True) if message_element else ""
            
            return {
                "donor_name": donor_name,
                "amount": amount,
                "message": message,
                "date": donation_date,
                "scraped_at": datetime.now().isoformat()
            }

        except Exception as e:
            logger.warning(f"Error extracting single donation: {e}")
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
