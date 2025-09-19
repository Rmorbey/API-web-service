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
        """Save tokens to .env file"""
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
            # Add a 5-minute buffer to avoid edge cases
            buffer_time = expiry_time - timedelta(minutes=5)
            
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
            # Use synchronous httpx client instead of async
            with httpx.Client() as client:
                response = client.post(
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
