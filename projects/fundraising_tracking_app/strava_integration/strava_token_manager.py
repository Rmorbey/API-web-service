#!/usr/bin/env python3
"""
Minimal Strava Token Manager
Contains only essential methods for token refresh
"""

import os
import json
import asyncio
import httpx
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from .http_clients import get_http_client
from dotenv import load_dotenv

load_dotenv()

class StravaTokenManager:
    def __init__(self):
        self.client_id = os.getenv("STRAVA_CLIENT_ID")
        self.client_secret = os.getenv("STRAVA_CLIENT_SECRET")
        
        # Load tokens from environment variables
        self.tokens = self._load_tokens_from_env()
        
        # Add thread-safe token caching and refresh locking
        self._token_lock = threading.Lock()
        self._cached_token = None
        self._cached_token_expires_at = None
        self._last_refresh_time = None
        self._in_emergency_refresh = False  # Flag to track emergency refresh mode
        self._last_digitalocean_update = None
    
    def set_emergency_refresh_mode(self, enabled: bool):
        """Set emergency refresh mode to skip DigitalOcean updates"""
        self._in_emergency_refresh = enabled
        
    def _load_tokens_from_env(self) -> Dict[str, Any]:
        """Load tokens from environment variables"""
        return {
            "access_token": os.getenv("STRAVA_ACCESS_TOKEN"),
            "refresh_token": os.getenv("STRAVA_REFRESH_TOKEN"),
            "expires_at": os.getenv("STRAVA_EXPIRES_AT"),
            "expires_in": os.getenv("STRAVA_EXPIRES_IN")
        }
    
    def _save_tokens_to_env(self, tokens: Dict[str, Any]):
        """Save tokens in memory and trigger automated update (production-safe)"""
        # Update in-memory tokens
        self.tokens = tokens
        
        # Clear cached token to force reload from environment
        with self._token_lock:
            self._cached_token = None
            self._cached_token_expires_at = None
        
        # Log the new tokens
        print("🔄 NEW STRAVA TOKENS - TRIGGERING AUTOMATED UPDATE:")
        print(f"STRAVA_ACCESS_TOKEN={tokens['access_token']}")
        print(f"STRAVA_REFRESH_TOKEN={tokens['refresh_token']}")
        print(f"STRAVA_EXPIRES_AT={tokens['expires_at']}")
        print(f"STRAVA_EXPIRES_IN={tokens['expires_in']}")
        
        # Also log to file for easier access
        with open("strava_token_refresh.log", "a") as f:
            f.write(f"\n=== TOKEN REFRESH - {datetime.now().isoformat()} ===\n")
            f.write(f"STRAVA_ACCESS_TOKEN={tokens['access_token']}\n")
            f.write(f"STRAVA_REFRESH_TOKEN={tokens['refresh_token']}\n")
            f.write(f"STRAVA_EXPIRES_AT={tokens['expires_at']}\n")
            f.write(f"STRAVA_EXPIRES_IN={tokens['expires_in']}\n")
            f.write("==========================================\n")
        
        # In production, only trigger automated update if tokens have actually changed
        if os.getenv("ENVIRONMENT") == "production":
            # Check if tokens have actually changed to avoid unnecessary restarts
            current_tokens = self._load_tokens_from_env()
            tokens_changed = (current_tokens.get("access_token") != tokens["access_token"] or 
                            current_tokens.get("refresh_token") != tokens["refresh_token"])
            
            # Also check if we've updated DigitalOcean recently (within last 30 minutes)
            recent_update = (self._last_digitalocean_update and 
                           time.time() - self._last_digitalocean_update < 1800)  # 30 minutes
            
            # CRITICAL: Skip DigitalOcean update during emergency refresh to prevent hanging
            if self._in_emergency_refresh:
                print("🔄 Emergency refresh mode - skipping DigitalOcean update to prevent hanging")
            elif tokens_changed and not recent_update:
                print("🔄 Triggering DigitalOcean automated update...")
                self._trigger_automated_update(tokens)
                print("🔄 DigitalOcean automated update completed")
                self._last_digitalocean_update = time.time()
            elif tokens_changed and recent_update:
                print("🔄 Tokens changed but DigitalOcean update too recent, skipping to prevent restart loop")
            else:
                print("🔄 Tokens unchanged, skipping DigitalOcean update to prevent restart")
        else:
            # In development, still update .env file
            self._update_env_file(tokens)
    
    def _trigger_automated_update(self, tokens: Dict[str, Any]):
        """Trigger automated token update via DigitalOcean API"""
        try:
            import requests
            
            # DigitalOcean API direct update
            do_token = os.getenv("DIGITALOCEAN_API_TOKEN")
            app_id = os.getenv("DIGITALOCEAN_APP_ID")
            
            if do_token and app_id:
                # Update DigitalOcean App secrets directly
                url = f"https://api.digitalocean.com/v2/apps/{app_id}"
                headers = {
                    "Authorization": f"Bearer {do_token}",
                    "Content-Type": "application/json"
                }
                
                # Get current app spec
                print(f"🔄 Making DigitalOcean API call to: {url}")
                response = requests.get(url, headers=headers, timeout=30)
                print(f"🔄 DigitalOcean API response: {response.status_code}")
                if response.status_code == 200:
                    app_spec = response.json()["app"]["spec"]
                    
                    # Update environment variables
                    for service in app_spec.get("services", []):
                        if service.get("name") == "api":
                            env_vars = service.get("envs", [])
                            
                            # Update Strava token environment variables
                            token_updates = {
                                "STRAVA_ACCESS_TOKEN": tokens['access_token'],
                                "STRAVA_REFRESH_TOKEN": tokens['refresh_token'],
                                "STRAVA_EXPIRES_AT": tokens['expires_at'],
                                "STRAVA_EXPIRES_IN": tokens['expires_in']
                            }
                            
                            # Update existing env vars or add new ones
                            for key, value in token_updates.items():
                                found = False
                                for env_var in env_vars:
                                    if env_var.get("key") == key:
                                        env_var["value"] = value
                                        found = True
                                        break
                                
                                if not found:
                                    env_vars.append({
                                        "key": key,
                                        "value": value,
                                        "scope": "RUN_TIME",
                                        "type": "SECRET"
                                    })
                            
                            service["envs"] = env_vars
                            break
                    
                    # Update the app
                    update_response = requests.put(url, headers=headers, json={"spec": app_spec}, timeout=30)
                    if update_response.status_code == 200:
                        print("✅ DigitalOcean secrets updated successfully")
                        print("🔄 App will restart automatically with new tokens")
                    else:
                        print(f"⚠️ Failed to update DigitalOcean secrets: {update_response.status_code}")
                        print(f"Response: {update_response.text}")
                else:
                    print(f"⚠️ Failed to get app spec: {response.status_code}")
            else:
                print("⚠️ DIGITALOCEAN_API_TOKEN or DIGITALOCEAN_APP_ID not set")
                print("📝 Please update DigitalOcean secrets manually")
                
        except Exception as e:
            print(f"⚠️ Failed to trigger automated update: {e}")
            print("📝 Please update DigitalOcean secrets manually")
    
    def _update_env_file(self, tokens: Dict[str, Any]):
        """Update .env file (development only)"""
        env_file = ".env"
        
        # Read existing .env file
        env_lines = []
        if os.path.exists(env_file):
            with open(env_file, 'r') as f:
                env_lines = f.readlines()
        
        # Update or add token lines
        token_keys = ["STRAVA_ACCESS_TOKEN", "STRAVA_REFRESH_TOKEN", "STRAVA_EXPIRES_AT", "STRAVA_EXPIRES_IN"]
        token_values = [tokens.get("access_token"), tokens.get("refresh_token"), tokens.get("expires_at"), tokens.get("expires_in")]
        
        # Remove existing token lines
        env_lines = [line for line in env_lines if not any(line.startswith(key + "=") for key in token_keys)]
        
        # Add updated token lines
        for key, value in zip(token_keys, token_values):
            if value is not None:
                env_lines.append(f"{key}={value}\n")
        
        # Write back to .env file
        with open(env_file, 'w') as f:
            f.writelines(env_lines)
        
        # Reload environment variables
        load_dotenv(override=True)
    
    def _is_token_expired(self, expires_at) -> bool:
        """Check if token is expired"""
        if not expires_at:
            return True
        
        try:
            # expires_at is a Unix timestamp
            expiry_time = datetime.fromtimestamp(int(expires_at))
            # Use 2-minute buffer to prevent premature refreshes but avoid race conditions
            buffer_time = expiry_time - timedelta(minutes=2)
            
            is_expired = datetime.now() >= buffer_time
            
            if is_expired:
                print("🔄 Access token expired, refreshing...")
            
            return is_expired
        except (ValueError, TypeError):
            print("⚠️  Invalid expires_at format, assuming expired")
            return True
    
    def get_valid_access_token(self) -> str:
        """Get a valid access token, refreshing if necessary - THREAD-SAFE"""
        print(f"🔄 get_valid_access_token called, acquiring lock...")
        
        # Add timeout to prevent deadlock
        if not self._token_lock.acquire(timeout=30):
            print(f"❌ Failed to acquire token lock within 30 seconds - possible deadlock")
            raise Exception("Token lock timeout - possible deadlock detected")
        
        try:
            print(f"🔄 Lock acquired, checking cached token...")
            # Check if we have a cached token that's still valid
            print(f"🔄 Checking cached token: {self._cached_token is not None}")
            if (self._cached_token and 
                self._cached_token_expires_at and 
                not self._is_token_expired(self._cached_token_expires_at)):
                print(f"🔄 Using cached token")
                return self._cached_token
            
            # Load current tokens from environment
            current_tokens = self._load_tokens_from_env()
            
            print(f"🔄 Loaded tokens from environment:")
            print(f"🔄 Access token: {'Present' if current_tokens.get('access_token') else 'Missing'}")
            print(f"🔄 Refresh token: {'Present' if current_tokens.get('refresh_token') else 'Missing'}")
            print(f"🔄 Expires at: {current_tokens.get('expires_at', 'Missing')}")
            
            if not current_tokens.get("access_token"):
                raise ValueError("No access token available. Please run the setup script.")
            
            # Check if token needs refreshing
            if self._is_token_expired(current_tokens.get("expires_at")):
                print(f"🔄 Token is expired, checking refresh token...")
                if not current_tokens.get("refresh_token"):
                    raise ValueError("No refresh token available. Please re-authenticate.")
                
                # Check if we recently refreshed (within last 10 minutes) to prevent rapid refreshes
                if (self._last_refresh_time and 
                    time.time() - self._last_refresh_time < 600):  # 10 minutes
                    print("🔄 Token refresh recently completed, using cached token")
                    return self._cached_token or current_tokens["access_token"]
                
                print(f"🔄 Token expired, starting refresh process...")
                # Refresh the token
                new_access_token = self._refresh_access_token(current_tokens["refresh_token"])
                
                # Cache the new token
                self._cached_token = new_access_token
                self._cached_token_expires_at = current_tokens.get("expires_at")
                self._last_refresh_time = time.time()
                
                return new_access_token
            
            # Token is still valid, cache it and return
            self._cached_token = current_tokens["access_token"]
            self._cached_token_expires_at = current_tokens.get("expires_at")
            return current_tokens["access_token"]
        
        finally:
            self._token_lock.release()
            print(f"🔄 Token lock released")
    
    def _refresh_access_token(self, refresh_token: str) -> str:
        """Refresh the access token using the refresh token - FIXED to be synchronous"""
        
        try:
            print(f"🔄 Starting token refresh...")
            print(f"🔄 Client ID: {self.client_id[:8]}..." if self.client_id else "❌ No client ID")
            print(f"🔄 Refresh token: {refresh_token[:8]}..." if refresh_token else "❌ No refresh token")
            
            # Use synchronous requests for token refresh to avoid async/sync issues
            import requests
            print(f"🔄 Making request to Strava OAuth endpoint...")
            
            response = requests.post(
                "https://www.strava.com/oauth/token",
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token"
                },
                timeout=60  # Increased timeout for token refresh
            )
            
            print(f"🔄 Token refresh response received: {response.status_code}")
            
            if response.status_code != 200:
                print(f"❌ Token refresh failed: {response.status_code} - {response.text}")
                raise Exception(f"Failed to refresh token: {response.status_code} - {response.text}")
            
            token_data = response.json()
            print(f"🔄 Token refresh response received: {response.status_code}")
            
            # Calculate expires_at timestamp
            expires_at = int(datetime.now().timestamp()) + token_data["expires_in"]
            
            # Update tokens
            new_tokens = {
                "access_token": token_data["access_token"],
                "refresh_token": token_data["refresh_token"],
                "expires_at": str(expires_at),
                "expires_in": str(token_data["expires_in"])
            }
            
            print(f"🔄 Saving new tokens to environment...")
            # Save to .env file
            self._save_tokens_to_env(new_tokens)
            
            # Update instance tokens
            self.tokens = new_tokens
            
            expires_datetime = datetime.fromtimestamp(expires_at)
            print(f"✅ Token refreshed successfully, expires at: {expires_datetime}")
            
            return token_data["access_token"]
            
        except Exception as e:
            raise Exception(f"Failed to refresh access token: {str(e)}")
    
    def get_token_status(self) -> Dict[str, Any]:
        """Get current token status for debugging"""
        with self._token_lock:
            current_tokens = self._load_tokens_from_env()
            return {
                "has_access_token": bool(current_tokens.get("access_token")),
                "has_refresh_token": bool(current_tokens.get("refresh_token")),
                "expires_at": current_tokens.get("expires_at"),
                "is_expired": self._is_token_expired(current_tokens.get("expires_at")),
                "cached_token": bool(self._cached_token),
                "last_refresh_time": self._last_refresh_time,
                "time_since_last_refresh": time.time() - self._last_refresh_time if self._last_refresh_time else None
            }
