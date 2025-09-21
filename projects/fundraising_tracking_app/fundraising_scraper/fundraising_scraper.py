#!/usr/bin/env python3
"""
Smart JustGiving Fundraising Scraper
Scrapes fundraising data from JustGiving page every 15 minutes
Uses smart caching strategy similar to Strava cache
"""

import requests
import json
import time
import threading
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
import re
import os
import glob

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
        
        # Create directories if they don't exist
        os.makedirs(os.path.dirname(cache_file), exist_ok=True)
        os.makedirs(self.backup_dir, exist_ok=True)
        
        # Load existing cache
        self._load_cache()
        
        # Start the scraper
        self._start_scraper()
    
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
                        logger.error("All backups failed, creating fresh cache...")
                        self._cache_data = self._create_empty_cache()
                        return self._cache_data
                        
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.warning(f"Cache file error: {e}, attempting to restore from backup...")
            if self._restore_from_backup():
                return self._cache_data
            else:
                logger.error("All backups failed, creating fresh cache...")
                self._cache_data = self._create_empty_cache()
                self._cache_loaded_at = now
                return self._cache_data
    
    def _create_empty_cache(self) -> Dict[str, Any]:
        """Create an empty cache structure"""
        return {
            "timestamp": None,
            "total_raised": 0.0,
            "donations": [],
            "total_donations": 0,
            "last_updated": None,
            "version": "1.0"
        }
    
    def _validate_cache_integrity(self, cache_data: Dict[str, Any]) -> bool:
        """Validate cache integrity"""
        try:
            # Check required fields
            required_fields = ["total_raised", "donations", "total_donations"]
            for field in required_fields:
                if field not in cache_data:
                    logger.warning(f"Missing required field: {field}")
                    return False
            
            # Check donations structure
            donations = cache_data.get("donations", [])
            if not isinstance(donations, list):
                logger.warning("Donations field is not a list")
                return False
            
            # Check individual donation structure
            for i, donation in enumerate(donations):
                if not isinstance(donation, dict):
                    logger.warning(f"Donation {i} is not a dictionary")
                    return False
                
                required_donation_fields = ["donor_name", "amount", "date"]
                for field in required_donation_fields:
                    if field not in donation:
                        logger.warning(f"Donation {i} missing field: {field}")
                        return False
            
            logger.info("Cache integrity validation passed")
            return True
            
        except Exception as e:
            logger.error(f"Cache integrity validation failed: {e}")
            return False
    
    def _restore_from_backup(self) -> bool:
        """Restore cache from the most recent backup"""
        try:
            backup_files = glob.glob(os.path.join(self.backup_dir, "fundraising_cache_backup_*.json"))
            if not backup_files:
                logger.warning("No backup files found")
                return False
            
            # Sort by modification time, newest first
            backup_files.sort(key=os.path.getmtime, reverse=True)
            
            for backup_file in backup_files:
                try:
                    with open(backup_file, 'r') as f:
                        backup_data = json.load(f)
                    
                    if self._validate_cache_integrity(backup_data):
                        self._cache_data = backup_data
                        self._cache_loaded_at = datetime.now()
                        
                        # Save restored cache
                        self._save_cache(backup_data)
                        
                        logger.info(f"Successfully restored cache from backup: {os.path.basename(backup_file)}")
                        return True
                    else:
                        logger.warning(f"Backup file {backup_file} failed integrity check")
                        
                except Exception as e:
                    logger.warning(f"Failed to restore from backup {backup_file}: {e}")
                    continue
            
            logger.error("All backup files failed to restore")
            return False
            
        except Exception as e:
            logger.error(f"Failed to restore from backup: {e}")
            return False
    
    def _create_backup(self):
        """Create a backup of the current cache"""
        try:
            if self._cache_data is None:
                logger.warning("No cache data to backup")
                return
            
            # Clean up old backups first
            self._cleanup_old_backups()
            
            # Create new backup
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = os.path.join(self.backup_dir, f"fundraising_cache_backup_{timestamp}.json")
            
            with open(backup_file, 'w') as f:
                json.dump(self._cache_data, f, indent=2)
            
            logger.info(f"💾 Backup created: {os.path.basename(backup_file)}")
            
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
    
    def _cleanup_old_backups(self):
        """Keep only the most recent backup"""
        try:
            backup_files = glob.glob(os.path.join(self.backup_dir, "fundraising_cache_backup_*.json"))
            if len(backup_files) > 1:
                # Sort by modification time, keep newest
                backup_files.sort(key=os.path.getmtime, reverse=True)
                for old_backup in backup_files[1:]:
                    os.remove(old_backup)
                    logger.info(f"🗑️ Removed old backup: {os.path.basename(old_backup)}")
        except Exception as e:
            logger.error(f"Failed to cleanup old backups: {e}")
    
    def _perform_smart_refresh(self):
        """Perform a smart refresh that preserves existing donations"""
        try:
            # Create backup before refresh
            self._create_backup()
            
            # Scrape fresh data
            fresh_data = self._scrape_fundraising_data()
            
            # Get current cache data
            current_data = self._load_cache()
            
            # Smart merge: preserve donations, update total raised
            merged_data = self._smart_merge_fundraising_data(current_data, fresh_data)
            
            # Save merged data
            self._save_cache(merged_data)
            
            logger.info(f"✅ Smart refresh completed: £{merged_data['total_raised']} raised, {len(merged_data['donations'])} donations")
            
        except Exception as e:
            logger.error(f"Smart refresh failed: {e}")
            raise
    
    def _smart_merge_fundraising_data(self, existing_data: Dict[str, Any], fresh_data: Dict[str, Any]) -> Dict[str, Any]:
        """Smart merge: preserve all existing donations, update only total raised"""
        try:
            # Start with existing data
            merged_data = existing_data.copy()
            
            # Update basic fields from fresh data
            merged_data.update({
                "timestamp": fresh_data.get("timestamp", merged_data.get("timestamp")),
                "total_raised": fresh_data.get("total_raised", merged_data.get("total_raised", 0.0)),
                "last_updated": datetime.now().isoformat(),
                "version": "1.0"
            })
            
            # Smart merge donations: preserve existing, add new ones
            existing_donations = {self._get_donation_key(d): d for d in merged_data.get("donations", [])}
            fresh_donations = fresh_data.get("donations", [])
            
            # Add new donations that don't already exist
            new_donations = []
            for fresh_donation in fresh_donations:
                donation_key = self._get_donation_key(fresh_donation)
                if donation_key not in existing_donations:
                    new_donations.append(fresh_donation)
                    logger.info(f"New donation found: {fresh_donation.get('donor_name')} - £{fresh_donation.get('amount')}")
            
            # Combine existing and new donations
            all_donations = list(existing_donations.values()) + new_donations
            
            # Sort by date (most recent first)
            all_donations.sort(key=lambda x: x.get('scraped_at', ''), reverse=True)
            
            merged_data.update({
                "donations": all_donations,
                "total_donations": len(all_donations)
            })
            
            logger.info(f"Smart merge: {len(existing_donations)} existing + {len(new_donations)} new = {len(all_donations)} total donations")
            
            return merged_data
            
        except Exception as e:
            logger.error(f"Smart merge failed: {e}")
            # Fallback to fresh data if merge fails
            return fresh_data
    
    def _get_donation_key(self, donation: Dict[str, Any]) -> str:
        """Create a unique key for a donation to detect duplicates"""
        donor_name = donation.get("donor_name", "")
        amount = donation.get("amount", 0)
        date = donation.get("date", "")
        message = donation.get("message", "")
        
        # Create a key that combines the most identifying features
        return f"{donor_name}_{amount}_{date}_{message}"
    
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
            
            # Make request to JustGiving page
            response = requests.get(self.justgiving_url, headers=headers, timeout=30)
            response.raise_for_status()
            
            # Parse HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            
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
    
    def _save_cache(self, data: Dict[str, Any]):
        """Save data to cache file"""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            # Update in-memory cache
            self._cache_data = data
            self._cache_loaded_at = datetime.now()
            
            logger.info(f"💾 Fundraising data saved to cache")
        except Exception as e:
            logger.error(f"Failed to save fundraising cache: {e}")
    
    def get_fundraising_data(self) -> Dict[str, Any]:
        """Get current fundraising data from cache"""
        return self._load_cache()
    
    def force_refresh_now(self) -> bool:
        """Manually trigger a smart refresh"""
        try:
            logger.info("🔄 Manual fundraising refresh triggered")
            self._perform_smart_refresh()
            return True
        except Exception as e:
            logger.error(f"Manual refresh failed: {e}")
            return False
    
    def cleanup_backups(self) -> bool:
        """Manually trigger backup cleanup"""
        try:
            self._cleanup_old_backups()
            return True
        except Exception as e:
            logger.error(f"Backup cleanup failed: {e}")
            return False
    
    def stop_scraper(self):
        """Stop the scraper thread"""
        self.running = False
        if self.scraper_thread:
            self.scraper_thread.join(timeout=5)
        logger.info("🛑 Fundraising scraper stopped")
