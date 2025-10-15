#!/usr/bin/env python3
"""
Secure Supabase Cache Manager
Handles persistent cache storage with comprehensive security measures
"""

import os
import json
import logging
import hashlib
import hmac
import time
import threading
import ipaddress
import re
import httpx
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

class SecureSupabaseCacheManager:
    """
    Secure Supabase Cache Manager with comprehensive security measures
    """
    
    def __init__(self):
        self.enabled = os.getenv("SUPABASE_ENABLED", "false").lower() == "true"
        self.base_url: Optional[str] = None
        self.headers: Optional[Dict[str, str]] = None
        self._lock = threading.Lock()
        
        # Security configurations
        self.max_data_size = 10 * 1024 * 1024  # 10MB
        self.allowed_cache_types = {'strava', 'fundraising'}
        self.rate_limit_window = 60  # seconds
        self.rate_limit_requests = 100  # per window
        self._request_counts = {}
        
        # API key validation
        self.api_key_hash = self._hash_api_key(os.getenv("SUPABASE_SERVICE_KEY", ""))
        
        # Pending saves for background retry
        self._pending_supabase_saves = []
        self._supabase_retry_thread = None
        self._shutdown_in_progress = False
        
        if self.enabled:
            self._initialize_supabase()
            self._start_background_retry_thread()
    
    def _hash_api_key(self, api_key: str) -> str:
        """Create hash of API key for validation"""
        return hashlib.sha256(api_key.encode()).hexdigest()
    
    def _validate_input(self, cache_type: str, data: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate input data for security"""
        # Validate cache type
        if cache_type not in self.allowed_cache_types:
            return False, f"Invalid cache type: {cache_type}"
        
        # Validate data structure
        if not isinstance(data, dict):
            return False, "Data must be a dictionary"
        
        # Check data size
        data_size = len(json.dumps(data))
        if data_size > self.max_data_size:
            return False, f"Data too large: {data_size} bytes (max: {self.max_data_size})"
        
        # Validate required fields
        if cache_type == 'strava':
            required_fields = ['activities', 'timestamp']
        elif cache_type == 'fundraising':
            required_fields = ['donations', 'total_raised', 'timestamp']
        
        for field in required_fields:
            if field not in data:
                return False, f"Missing required field: {field}"
        
        # Sanitize data (remove potential malicious content)
        sanitized_data = self._sanitize_data(data)
        
        return True, "Valid"
    
    def _sanitize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize ONLY user input data to prevent injection attacks - PROTECT API DATA"""
        def sanitize_value(value, key_path=""):
            if isinstance(value, str):
                # PROTECT API DATA: Don't sanitize encoded/calculated data
                protected_patterns = [
                    "polyline",      # Encoded route data
                    "bounds",        # Calculated map bounds  
                    "description",   # Strava activity descriptions (API data)
                    "name",          # Activity names (API data)
                    "type",          # Activity types (API data)
                    "start_date",    # Timestamps (API data)
                    "photos",        # Photo data (API data)
                    "music",         # Music detection data (calculated)
                    "urls",          # Photo URLs (API data)
                    "athlete",       # Athlete data (API data)
                    "distance",      # Numeric data
                    "moving_time",   # Numeric data
                    "elevation",     # Numeric data
                    "pace",          # Calculated data
                    "speed",         # Calculated data
                    "coordinates",   # GPS coordinates
                    "lat",           # Latitude
                    "lng",           # Longitude
                    "north",         # Bounds coordinates
                    "south",         # Bounds coordinates
                    "east",          # Bounds coordinates
                    "west"           # Bounds coordinates
                ]
                
                # Check if this is protected API data
                is_protected = any(pattern in key_path.lower() for pattern in protected_patterns)
                
                if is_protected:
                    # Only limit length for protected data
                    if len(value) > 50000:  # Larger limit for API data
                        value = value[:50000]
                    return value
                
                # SANITIZE USER INPUT: Only sanitize actual user input
                user_input_patterns = [
                    "comments",      # User comments on activities
                    "message",       # Donation messages
                    "donor_name"     # Donor names (user input)
                ]
                
                is_user_input = any(pattern in key_path.lower() for pattern in user_input_patterns)
                
                if is_user_input:
                    # Remove potential SQL injection patterns from user input
                    value = re.sub(r'[;\'"\\]', '', value)
                    # Limit string length for user input
                    if len(value) > 1000:  # Smaller limit for user input
                        value = value[:1000]
                else:
                    # For other data, just limit length
                    if len(value) > 10000:
                        value = value[:10000]
                        
            elif isinstance(value, dict):
                return {k: sanitize_value(v, f"{key_path}.{k}" if key_path else k) for k, v in value.items()}
            elif isinstance(value, list):
                return [sanitize_value(item, f"{key_path}[{i}]" if key_path else f"[{i}]") for i, item in enumerate(value)]
            return value
        
        return sanitize_value(data)
    
    def _check_rate_limit(self, client_ip: str) -> bool:
        """Implement rate limiting"""
        now = time.time()
        window_start = now - self.rate_limit_window
        
        # Clean old entries
        self._request_counts = {
            ip: count for ip, count in self._request_counts.items()
            if count['window_start'] > window_start
        }
        
        # Check current IP
        if client_ip not in self._request_counts:
            self._request_counts[client_ip] = {'count': 1, 'window_start': now}
            return True
        
        if self._request_counts[client_ip]['count'] >= self.rate_limit_requests:
            return False
        
        self._request_counts[client_ip]['count'] += 1
        return True
    
    def _log_operation(self, cache_type: str, operation: str, success: bool, 
                      client_ip: str = None, user_agent: str = None, data_size: int = 0):
        """Log all operations for audit trail"""
        try:
            if self.base_url:
                log_data = {
                    'cache_type': cache_type,
                    'operation': operation,
                    'user_role': 'service_role',
                    'ip_address': client_ip,
                    'user_agent': user_agent,
                    'data_size': data_size,
                    'success': success
                }
                
                with httpx.Client() as client:
                    response = client.post(
                        f"{self.base_url}cache_audit_log",
                        headers=self.headers,
                        json=log_data
                    )
                    response.raise_for_status()
        except Exception as e:
            logger.error(f"Failed to log operation: {e}")
    
    def _initialize_supabase(self):
        """Initialize Supabase HTTP client with security checks"""
        try:
            url = os.getenv("SUPABASE_URL")
            key = os.getenv("SUPABASE_SERVICE_KEY")
            
            if not url or not key:
                logger.warning("Supabase credentials not found, disabling Supabase cache")
                self.enabled = False
                return
            
            # Validate URL format
            if not url.startswith('https://'):
                raise ValueError("Supabase URL must use HTTPS")
            
            # Validate API key format (JWT tokens contain dots and other characters)
            if not key or len(key) < 10:
                raise ValueError("Invalid API key format")
            
            # Set up HTTP client configuration
            self.base_url = url + '/rest/v1/'
            self.headers = {
                'apikey': key,
                'Authorization': f'Bearer {key}',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            # Test connection with minimal query
            with httpx.Client() as client:
                response = client.get(
                    self.base_url + 'cache_storage?select=id&limit=1',
                    headers=self.headers
                )
                response.raise_for_status()
            
            logger.info("✅ Secure Supabase cache manager initialized")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Supabase: {e}")
            self.enabled = False
    
    def get_cache(self, cache_type: str, project_id: str = "fundraising-app", 
                  client_ip: str = None, user_agent: str = None) -> Optional[Dict[str, Any]]:
        """Get cache data with security validation"""
        if not self.enabled or not self.base_url:
            return None
        
        # Rate limiting
        if client_ip and not self._check_rate_limit(client_ip):
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            self._log_operation(cache_type, 'READ', False, client_ip, user_agent)
            return None
        
        try:
            with self._lock:
                project_id_num = self._get_project_id(project_id)
                
                # Build query URL
                query_url = f"{self.base_url}cache_storage?select=data,last_fetch,last_rich_fetch&cache_type=eq.{cache_type}&project_id=eq.{project_id_num}"
                
                with httpx.Client() as client:
                    response = client.get(query_url, headers=self.headers)
                    response.raise_for_status()
                    
                    result_data = response.json()
                    
                    if result_data:
                        cache_data = result_data[0]
                        data_size = len(json.dumps(cache_data['data']))
                        
                        self._log_operation(cache_type, 'READ', True, client_ip, user_agent, data_size)
                        logger.info(f"✅ Loaded {cache_type} cache from Supabase")
                        
                        return {
                            'data': cache_data['data'],
                            'last_fetch': cache_data['last_fetch'],
                            'last_rich_fetch': cache_data['last_rich_fetch']
                        }
                    
                    self._log_operation(cache_type, 'READ', True, client_ip, user_agent, 0)
                
        except Exception as e:
            logger.error(f"❌ Supabase read failed for {cache_type}: {e}")
            self._log_operation(cache_type, 'READ', False, client_ip, user_agent)
        
        return None
    
    def save_cache(self, cache_type: str, data: Dict[str, Any], 
                   last_fetch: Optional[datetime] = None,
                   last_rich_fetch: Optional[datetime] = None,
                   project_id: str = "fundraising-app",
                   client_ip: str = None, user_agent: str = None) -> bool:
        """Save cache data with security validation"""
        if not self.enabled or not self.base_url:
            return False
        
        # Validate input
        is_valid, error_msg = self._validate_input(cache_type, data)
        if not is_valid:
            logger.error(f"❌ Input validation failed: {error_msg}")
            self._log_operation(cache_type, 'WRITE', False, client_ip, user_agent)
            return False
        
        # Rate limiting
        if client_ip and not self._check_rate_limit(client_ip):
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            self._log_operation(cache_type, 'WRITE', False, client_ip, user_agent)
            return False
        
        try:
            with self._lock:
                # Sanitize data before saving
                sanitized_data = self._sanitize_data(data)
                
                # Calculate data size
                data_size = len(json.dumps(sanitized_data))
                
                # Prepare data for upsert
                upsert_data = {
                    'project_id': self._get_project_id(project_id),
                    'cache_type': cache_type,
                    'data': sanitized_data,
                    'last_fetch': last_fetch.isoformat() if last_fetch else None,
                    'last_rich_fetch': last_rich_fetch.isoformat() if last_rich_fetch else None,
                    'data_size': data_size,
                    'updated_at': datetime.now().isoformat()
                }
                
                with httpx.Client() as client:
                    # Use upsert with proper headers for conflict resolution
                    upsert_headers = self.headers.copy()
                    upsert_headers['Prefer'] = 'resolution=merge-duplicates'
                    
                    # Try POST first (for new records)
                    try:
                        response = client.post(
                            f"{self.base_url}cache_storage",
                            headers=upsert_headers,
                            json=upsert_data
                        )
                        response.raise_for_status()
                    except httpx.HTTPStatusError as e:
                        if e.response.status_code == 409:
                            # Conflict - record exists, try PATCH for update
                            logger.info(f"Record exists for {cache_type}, updating with PATCH")
                            patch_headers = self.headers.copy()
                            patch_headers['Prefer'] = 'resolution=merge-duplicates'
                            
                            # Use PATCH with the same data for upsert behavior
                            response = client.patch(
                                f"{self.base_url}cache_storage?cache_type=eq.{cache_type}&project_id=eq.{self._get_project_id(project_id)}",
                                headers=patch_headers,
                                json=upsert_data
                            )
                            response.raise_for_status()
                        else:
                            raise
                
                self._log_operation(cache_type, 'WRITE', True, client_ip, user_agent, data_size)
                logger.info(f"✅ Saved {cache_type} cache to Supabase")
                return True
                
        except Exception as e:
            logger.error(f"❌ Supabase write failed for {cache_type}: {e}")
            self._log_operation(cache_type, 'WRITE', False, client_ip, user_agent)
            return False
    
    def _get_project_id(self, project_name: str) -> int:
        """Get project ID from project name"""
        try:
            # Query for existing project
            query_url = f"{self.base_url}projects?select=id&project_name=eq.{project_name}"
            
            with httpx.Client() as client:
                response = client.get(query_url, headers=self.headers)
                response.raise_for_status()
                result_data = response.json()
            
            if result_data:
                return result_data[0]['id']
            else:
                # Create project if it doesn't exist
                project_data = {
                    'project_name': project_name,
                    'description': f'Cache project for {project_name}'
                }
                
                with httpx.Client() as client:
                    response = client.post(
                        f"{self.base_url}projects",
                        headers=self.headers,
                        json=project_data
                    )
                    response.raise_for_status()
                    result_data = response.json()
                    return result_data[0]['id']
                
        except Exception as e:
            logger.error(f"Failed to get project ID for {project_name}: {e}")
            return 1  # Default to first project
    
    def _queue_supabase_save(self, cache_type: str, data: Dict[str, Any], 
                           last_fetch: Optional[datetime] = None,
                           last_rich_fetch: Optional[datetime] = None,
                           project_id: str = "fundraising-app"):
        """Queue data for background Supabase save"""
        self._pending_supabase_saves.append({
            'cache_type': cache_type,
            'data': data,
            'last_fetch': last_fetch,
            'last_rich_fetch': last_rich_fetch,
            'project_id': project_id,
            'timestamp': datetime.now(),
            'retry_count': 0
        })
        
        logger.info(f"Queued {cache_type} cache for background save")
    
    def _start_background_retry_thread(self):
        """Start background thread to retry Supabase saves"""
        if self._supabase_retry_thread and self._supabase_retry_thread.is_alive():
            return
        
        self._supabase_retry_thread = threading.Thread(
            target=self._supabase_retry_loop, 
            daemon=True
        )
        self._supabase_retry_thread.start()
        logger.info("🔄 Background Supabase retry thread started")
    
    def _supabase_retry_loop(self):
        """Background loop to retry failed Supabase saves"""
        while not self._shutdown_in_progress:
            try:
                if self._pending_supabase_saves:
                    save_item = self._pending_supabase_saves[0]
                    
                    # Try to save
                    success = self.save_cache(
                        save_item['cache_type'],
                        save_item['data'],
                        save_item['last_fetch'],
                        save_item['last_rich_fetch'],
                        save_item['project_id']
                    )
                    
                    if success:
                        # Success - remove from queue
                        self._pending_supabase_saves.pop(0)
                        logger.info("✅ Background retry successful")
                    else:
                        # Still failing, increment retry count
                        save_item['retry_count'] += 1
                        
                        if save_item['retry_count'] > 10:  # Max 10 retries
                            logger.error("Max retries exceeded, removing from queue")
                            self._pending_supabase_saves.pop(0)
                        else:
                            # Wait longer before next retry
                            time.sleep(300)  # 5 minutes
                else:
                    # No pending saves, wait
                    time.sleep(60)  # Check every minute
                    
            except Exception as e:
                logger.error(f"Error in background retry loop: {e}")
                time.sleep(60)
    
    def graceful_shutdown(self):
        """Handle graceful shutdown - save all pending data to Supabase"""
        if self._shutdown_in_progress:
            return
        
        self._shutdown_in_progress = True
        logger.info("🔄 Graceful shutdown initiated, saving pending data...")
        
        # Save all pending Supabase data
        self._force_save_all_pending_data()
        
        # Wait for saves to complete (with timeout)
        self._wait_for_saves_completion(timeout=30)
        
        logger.info("✅ Graceful shutdown completed")
    
    def _force_save_all_pending_data(self):
        """Force save all pending data to Supabase"""
        for save_item in self._pending_supabase_saves:
            try:
                self.save_cache(
                    save_item['cache_type'],
                    save_item['data'],
                    save_item['last_fetch'],
                    save_item['last_rich_fetch'],
                    save_item['project_id']
                )
                logger.info("✅ Saved pending data to Supabase")
            except Exception as e:
                logger.error(f"Failed to save pending data: {e}")
    
    def _wait_for_saves_completion(self, timeout=30):
        """Wait for all saves to complete with timeout"""
        start_time = time.time()
        while self._pending_supabase_saves and (time.time() - start_time) < timeout:
            time.sleep(1)
        
        if self._pending_supabase_saves:
            logger.warning(f"Timeout: {len(self._pending_supabase_saves)} saves still pending")
