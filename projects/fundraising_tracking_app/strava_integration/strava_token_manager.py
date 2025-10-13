#!/usr/bin/env python3
"""
Minimal Strava Token Manager
Contains only essential methods for token refresh
"""

import os
import json
import asyncio
import httpx
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
        
        # In production, trigger automated update
        if os.getenv("ENVIRONMENT") == "production":
            self._trigger_automated_update(tokens)
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
                response = requests.get(url, headers=headers)
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
                    update_response = requests.put(url, headers=headers, json={"spec": app_spec})
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
            # Add a 1-minute buffer to avoid edge cases (reduced from 5 minutes)
            buffer_time = expiry_time - timedelta(minutes=1)
            
            is_expired = datetime.now() >= buffer_time
            
            if is_expired:
                print("🔄 Access token expired, refreshing...")
            
            return is_expired
        except (ValueError, TypeError):
            print("⚠️  Invalid expires_at format, assuming expired")
            return True
    
    def get_valid_access_token(self) -> str:
        """Get a valid access token, refreshing if necessary"""
        current_tokens = self._load_tokens_from_env()
        
        if not current_tokens.get("access_token"):
            raise ValueError("No access token available. Please run the setup script.")
        
        # Check if token needs refreshing
        if self._is_token_expired(current_tokens.get("expires_at")):
            if not current_tokens.get("refresh_token"):
                raise ValueError("No refresh token available. Please re-authenticate.")
            
            # Refresh the token
            new_access_token = self._refresh_access_token(current_tokens["refresh_token"])
            return new_access_token
        
        return current_tokens["access_token"]
    
    def _refresh_access_token(self, refresh_token: str) -> str:
        """Refresh the access token using the refresh token - FIXED to be synchronous"""
        
        try:
            # Use shared HTTP client with connection pooling
            http_client = get_http_client()
            response = http_client.post(
                "https://www.strava.com/oauth/token",
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token"
                }
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to refresh token: {response.status_code} - {response.text}")
            
            token_data = response.json()
            
            # Calculate expires_at timestamp
            expires_at = int(datetime.now().timestamp()) + token_data["expires_in"]
            
            # Update tokens
            new_tokens = {
                "access_token": token_data["access_token"],
                "refresh_token": token_data["refresh_token"],
                "expires_at": str(expires_at),
                "expires_in": str(token_data["expires_in"])
            }
            
            # Save to .env file
            self._save_tokens_to_env(new_tokens)
            
            # Update instance tokens
            self.tokens = new_tokens
            
            expires_datetime = datetime.fromtimestamp(expires_at)
            print(f"✅ Token refreshed successfully, expires at: {expires_datetime}")
            
            return token_data["access_token"]
            
        except Exception as e:
            raise Exception(f"Failed to refresh access token: {str(e)}")
