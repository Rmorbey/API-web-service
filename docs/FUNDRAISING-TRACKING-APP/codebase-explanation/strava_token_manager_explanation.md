# 📚 StravaTokenManager - Complete Code Explanation

## 🎯 **Overview**

This class handles **Strava authentication** - it manages access tokens, refresh tokens, and automatically refreshes tokens when they expire. Think of it as the **security guard** that ensures your API always has valid credentials to access Strava's data.

## 📁 **File Structure Context**

```
strava_token_manager.py  ← YOU ARE HERE (Authentication)
├── smart_strava_cache.py  (Uses this class)
├── http_clients.py        (Uses this for HTTP requests)
└── .env                   (Stores tokens)
```

## 🔍 **Line-by-Line Code Explanation**

### **1. Imports and Setup (Lines 1-17)**

```python
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
```

**What this does:**
- **Standard library imports**: `os`, `json`, `datetime` for basic functionality
- **`httpx`**: HTTP client for making API requests to Strava
- **`asyncio`**: For asynchronous operations (though this class is synchronous)
- **`typing`**: For type hints
- **Custom imports**: Uses shared HTTP client for connection pooling
- **`load_dotenv()`**: Loads environment variables from `.env` file

### **2. Class Initialization (Lines 18-25)**

```python
class StravaTokenManager:
    def __init__(self):
        self.client_id = os.getenv("STRAVA_CLIENT_ID")
        self.client_secret = os.getenv("STRAVA_CLIENT_SECRET")
        
        # Load tokens from environment variables
        self.tokens = self._load_tokens_from_env()
```

**What this does:**
- **Client credentials**: Gets Strava app credentials from environment
- **Token loading**: Loads existing tokens from environment variables
- **Instance variables**: Stores credentials and tokens for use

**Learning Point**: This follows the **OAuth 2.0** pattern where you need:
- `client_id`: Your app's identifier
- `client_secret`: Your app's secret key
- `access_token`: Token to access user data
- `refresh_token`: Token to get new access tokens

### **3. Token Loading from Environment (Lines 26-33)**

```python
def _load_tokens_from_env(self) -> Dict[str, Any]:
    """Load tokens from environment variables"""
    return {
        "access_token": os.getenv("STRAVA_ACCESS_TOKEN"),
        "refresh_token": os.getenv("STRAVA_REFRESH_TOKEN"),
        "expires_at": os.getenv("STRAVA_EXPIRES_AT"),
        "expires_in": os.getenv("STRAVA_EXPIRES_IN")
    }
```

**What this does:**
- **Environment variable access**: Gets tokens from `.env` file
- **Token structure**: Returns dictionary with all token information
- **Type hint**: Returns `Dict[str, Any]` for type safety

**Token Types Explained:**
- **`access_token`**: Used to make API requests (expires in 6 hours)
- **`refresh_token`**: Used to get new access tokens (expires in 6 months)
- **`expires_at`**: Unix timestamp when access token expires
- **`expires_in`**: Seconds until access token expires

### **4. Token Saving to Environment (Lines 35-62)**

```python
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
```

**What this does:**
- **File reading**: Reads existing `.env` file
- **Token replacement**: Removes old token lines and adds new ones
- **File writing**: Writes updated tokens back to `.env` file
- **Environment reload**: Reloads environment variables to pick up changes

**Why this matters**: When tokens are refreshed, they need to be saved so the app can use them next time.

### **5. Token Expiration Check (Lines 64-83)**

```python
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
```

**What this does:**
- **Timestamp conversion**: Converts Unix timestamp to datetime
- **Buffer time**: Adds 5-minute buffer to avoid edge cases
- **Expiration check**: Compares current time with expiry time
- **Error handling**: Assumes expired if timestamp is invalid
- **Logging**: Prints status messages for debugging

**Learning Point**: The 5-minute buffer prevents using tokens that are about to expire, avoiding API errors.

### **6. Main Token Access Method (Lines 85-101)**

```python
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
```

**What this does:**
- **Token loading**: Gets current tokens from environment
- **Validation**: Checks if access token exists
- **Expiration check**: Determines if token needs refreshing
- **Refresh logic**: Refreshes token if expired
- **Return**: Returns valid access token

**This is the main method** that other classes call to get a valid token.

### **7. Token Refresh Logic (Lines 103-147)**

```python
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
```

**What this does:**
- **HTTP request**: Makes POST request to Strava's token endpoint
- **OAuth 2.0 flow**: Uses refresh token to get new access token
- **Response validation**: Checks if request was successful
- **Token calculation**: Calculates new expiry timestamp
- **Token saving**: Saves new tokens to `.env` file
- **Instance update**: Updates class instance with new tokens
- **Logging**: Confirms successful refresh

**OAuth 2.0 Refresh Flow:**
1. **Send refresh token** to Strava's token endpoint
2. **Receive new tokens** (access + refresh)
3. **Calculate expiry time** from `expires_in` seconds
4. **Save new tokens** for future use

## 🎯 **Key Learning Points**

### **1. OAuth 2.0 Authentication**
- **Client credentials**: App ID and secret
- **Access tokens**: Short-lived tokens for API access
- **Refresh tokens**: Long-lived tokens for getting new access tokens
- **Token expiry**: Automatic refresh when tokens expire

### **2. Environment Variable Management**
- **Secure storage**: Tokens stored in `.env` file
- **Dynamic updates**: Tokens updated when refreshed
- **Environment reload**: Variables reloaded after updates

### **3. Error Handling**
- **Validation**: Checks for missing tokens
- **Graceful failures**: Clear error messages
- **Edge cases**: Handles invalid timestamps

### **4. HTTP Client Usage**
- **Connection pooling**: Reuses HTTP connections
- **Shared client**: Uses centralized HTTP client
- **Error handling**: Proper HTTP status code checking

### **5. Token Lifecycle Management**
- **Automatic refresh**: Transparent token renewal
- **Expiry checking**: Proactive token validation
- **State persistence**: Tokens saved between app restarts

## 🚀 **How This Fits Into Your Learning**

This class demonstrates:
- **OAuth 2.0 implementation**: Complete authentication flow
- **Environment variable management**: Secure credential storage
- **HTTP client usage**: Making API requests
- **Error handling**: Comprehensive error management
- **State management**: Persisting and updating application state

**Next**: We'll explore the `http_clients.py` to understand HTTP connection pooling! 🎉
