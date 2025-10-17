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
        self._last_digitalocean_update = None
    
        
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
        
        # Clear cached token to force reload from environment (no lock needed - already in locked context)
        self._cached_token = None
        self._cached_token_expires_at = None
        
        # Log token refresh (without exposing actual tokens)
        print("🔄 NEW STRAVA TOKENS - TRIGGERING AUTOMATED UPDATE:")
        print(f"STRAVA_ACCESS_TOKEN={'*' * 20}...{tokens['access_token'][-4:]}")
        print(f"STRAVA_REFRESH_TOKEN={'*' * 20}...{tokens['refresh_token'][-4:]}")
        print(f"STRAVA_EXPIRES_AT={tokens['expires_at']}")
        print(f"STRAVA_EXPIRES_IN={tokens['expires_in']}")
        
        # Log token refresh (without exposing actual tokens)
        print(f"🔄 Token refresh logged: access_token={'*' * 20}...{tokens['access_token'][-4:]}")
        print(f"🔄 Token refresh logged: refresh_token={'*' * 20}...{tokens['refresh_token'][-4:]}")
        print(f"🔄 Token refresh logged: expires_at={tokens['expires_at']}")
        print(f"🔄 Token refresh logged: expires_in={tokens['expires_in']}")
        
        # Always use local .env file storage - much more reliable than DigitalOcean API
        print("🔄 Using local .env file storage for token persistence (reliable approach)")
        self._update_env_file(tokens)
    
    # DigitalOcean API integration removed - using local .env file storage instead
    
    def _update_env_file(self, tokens: Dict[str, Any]):
        """Update .env file (development only)"""
        print("🔄 Starting _update_env_file...")
        env_file = ".env"
        
        try:
            print("🔄 Reading existing .env file...")
            # Read existing .env file
            env_lines = []
            if os.path.exists(env_file):
                with open(env_file, 'r') as f:
                    env_lines = f.readlines()
                print(f"🔄 Read {len(env_lines)} lines from .env file")
            else:
                print("🔄 .env file does not exist, creating new one")
            
            print("🔄 Processing token updates...")
            # Update or add token lines
            token_keys = ["STRAVA_ACCESS_TOKEN", "STRAVA_REFRESH_TOKEN", "STRAVA_EXPIRES_AT", "STRAVA_EXPIRES_IN"]
            token_values = [tokens.get("access_token"), tokens.get("refresh_token"), tokens.get("expires_at"), tokens.get("expires_in")]
            
            # Remove existing token lines
            env_lines = [line for line in env_lines if not any(line.startswith(key + "=") for key in token_keys)]
            print(f"🔄 Removed existing token lines, {len(env_lines)} lines remaining")
            
            # Add updated token lines
            for key, value in zip(token_keys, token_values):
                if value is not None:
                    env_lines.append(f"{key}={value}\n")
            print(f"🔄 Added new token lines, {len(env_lines)} lines total")
            
            print("🔄 Writing to .env file...")
            # Write back to .env file
            with open(env_file, 'w') as f:
                f.writelines(env_lines)
            print("🔄 Successfully wrote to .env file")
            
            print("🔄 Reloading environment variables...")
            # Reload environment variables (with error handling)
            try:
                load_dotenv(override=True)
                print("🔄 Successfully reloaded environment variables")
            except Exception as reload_error:
                print(f"⚠️ Warning: Failed to reload environment variables: {reload_error}")
                print("🔄 Continuing without reload - tokens are saved to file")
            
        except Exception as e:
            print(f"❌ Error in _update_env_file: {e}")
            import traceback
            print(f"❌ Full traceback: {traceback.format_exc()}")
            raise
    
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
        if not self._token_lock.acquire(timeout=10):
            print(f"❌ Failed to acquire token lock within 10 seconds - possible deadlock")
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
            # Save to .env file (local storage - fast and reliable)
            try:
                self._save_tokens_to_env(new_tokens)
                print("✅ Tokens saved successfully to local .env file")
            except Exception as e:
                print(f"⚠️ Token save error: {e}")
                print("🔄 Continuing with token refresh despite save error...")
            
            # Update instance tokens (always do this regardless of save status)
            self.tokens = new_tokens
            
            # Update cached token to prevent using old token
            with self._token_lock:
                self._cached_token = token_data["access_token"]
                self._cached_token_expires_at = expires_at
            
            expires_datetime = datetime.fromtimestamp(expires_at)
            print(f"✅ Token refreshed successfully, expires at: {expires_datetime}")
            print(f"🔄 Updated cached token: {token_data['access_token'][:20]}...")
            
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
