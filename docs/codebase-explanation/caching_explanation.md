# 📚 Caching - Complete Code Explanation

## 🎯 **Overview**

This module provides **HTTP response caching** with proper cache headers like ETag, Last-Modified, and Cache-Control. It intelligently caches API responses to improve performance and reduce server load. Think of it as the **performance optimizer** that stores frequently requested data in memory for faster access.

## 📁 **File Structure Context**

```
caching.py  ← YOU ARE HERE (HTTP Response Caching)
├── strava_integration_api.py  (Uses this for caching)
├── fundraising_api.py         (Uses this for caching)
└── FastAPI                    (Uses this for middleware)
```

## 🔍 **Line-by-Line Code Explanation**

### **1. Imports and Setup (Lines 1-16)**

```python
#!/usr/bin/env python3
"""
HTTP Response Caching with Proper Cache Headers
Provides intelligent caching with ETag, Last-Modified, and Cache-Control headers
"""

import hashlib
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Union
from fastapi import Request, Response
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)
```

**What this does:**
- **`hashlib`**: For generating ETags (content hashes)
- **`json`**: For serializing data for hashing
- **`time`**: For cache expiration timestamps
- **`datetime`**: For Last-Modified headers
- **`typing`**: For type hints
- **FastAPI**: For request/response handling

### **2. CacheManager Class (Lines 18-33)**

```python
class CacheManager:
    """
    Manages HTTP response caching with proper cache headers
    """
    
    def __init__(self):
        # Cache storage (in production, this could be Redis or similar)
        self._cache: Dict[str, Dict[str, Any]] = {}
        
        # Default cache durations (in seconds)
        self.default_cache_durations = {
            "static": 3600,      # 1 hour for static data
            "dynamic": 300,      # 5 minutes for dynamic data
            "realtime": 60,      # 1 minute for real-time data
            "user_data": 1800,   # 30 minutes for user-specific data
        }
```

**What this does:**
- **Cache storage**: In-memory dictionary for storing cached responses
- **Cache types**: Different durations for different data types
- **Static data**: 1 hour (rarely changes)
- **Dynamic data**: 5 minutes (changes frequently)
- **Real-time data**: 1 minute (changes very frequently)
- **User data**: 30 minutes (user-specific content)

### **3. ETag Generation (Lines 35-43)**

```python
def _generate_etag(self, data: Any) -> str:
    """Generate ETag from data content"""
    if isinstance(data, dict):
        # Sort keys for consistent hashing
        data_str = json.dumps(data, sort_keys=True, default=str)
    else:
        data_str = str(data)
    
    return f'"{hashlib.md5(data_str.encode()).hexdigest()}"'
```

**What this does:**
- **Content hashing**: Creates unique identifier for data content
- **Consistent hashing**: Sorts keys for consistent results
- **MD5 hash**: Uses MD5 for fast hashing
- **ETag format**: Wraps hash in quotes (HTTP standard)
- **Change detection**: ETag changes when content changes

**ETag Explained:**
- **ETag**: Entity Tag - unique identifier for content
- **Change detection**: Client can check if content changed
- **304 Not Modified**: Server returns 304 if ETag matches
- **Bandwidth saving**: Avoids sending unchanged content

### **4. Cache Key Generation (Lines 45-58)**

```python
def _get_cache_key(self, request: Request, user_id: Optional[str] = None) -> str:
    """Generate cache key from request"""
    # Include path, query parameters, and user ID if provided
    key_parts = [request.url.path]
    
    if request.query_params:
        # Sort query params for consistent keys
        sorted_params = sorted(request.query_params.items())
        key_parts.append("&".join(f"{k}={v}" for k, v in sorted_params))
    
    if user_id:
        key_parts.append(f"user:{user_id}")
    
    return "|".join(key_parts)
```

**What this does:**
- **Unique keys**: Creates unique identifier for each request
- **Path inclusion**: Includes URL path in key
- **Query parameters**: Includes query parameters in key
- **User specificity**: Includes user ID for user-specific content
- **Consistent ordering**: Sorts parameters for consistent keys

**Cache Key Examples:**
- **`/api/activities`**: Basic endpoint
- **`/api/activities?limit=10&type=Run`**: With query parameters
- **`/api/activities?limit=10&type=Run|user:123`**: User-specific

### **5. Cache Eligibility Check (Lines 60-75)**

```python
def _should_cache(self, request: Request, cache_type: str = "dynamic") -> bool:
    """Determine if request should be cached"""
    # Don't cache POST, PUT, DELETE requests
    if request.method not in ["GET", "HEAD"]:
        return False
    
    # Don't cache requests with no-cache headers
    cache_control = request.headers.get("cache-control", "")
    if "no-cache" in cache_control or "no-store" in cache_control:
        return False
    
    # Don't cache authenticated requests unless specified
    if request.headers.get("authorization") and cache_type != "user_data":
        return False
    
    return True
```

**What this does:**
- **Method filtering**: Only caches GET and HEAD requests
- **Header checking**: Respects no-cache headers
- **Authentication handling**: Doesn't cache auth requests by default
- **User data exception**: Allows caching user-specific data
- **Cache control**: Respects client cache preferences

### **6. Cached Response Retrieval (Lines 77-113)**

```python
def get_cached_response(self, request: Request, user_id: Optional[str] = None) -> Optional[Response]:
    """Get cached response if available and valid"""
    if not self._should_cache(request):
        return None
    
    cache_key = self._get_cache_key(request, user_id)
    cached_data = self._cache.get(cache_key)
    
    if not cached_data:
        return None
    
    # Check if cache is still valid
    if time.time() > cached_data["expires_at"]:
        del self._cache[cache_key]
        return None
    
    # Check ETag match
    if_none_match = request.headers.get("if-none-match")
    if if_none_match and if_none_match == cached_data["etag"]:
        # Return 304 Not Modified
        return Response(status_code=304)
    
    # Check Last-Modified
    if_modified_since = request.headers.get("if-modified-since")
    if if_modified_since:
        try:
            if_modified_since_time = datetime.fromisoformat(if_modified_since.replace("Z", "+00:00"))
            cached_time = datetime.fromisoformat(cached_data["last_modified"].replace("Z", "+00:00"))
            if cached_time <= if_modified_since_time:
                return Response(status_code=304)
        except ValueError:
            pass  # Invalid date format, continue with normal response
    
    # Return cached response with proper headers
    response = JSONResponse(content=cached_data["data"])
    self._add_cache_headers(response, cached_data)
    return response
```

**What this does:**
- **Cache lookup**: Finds cached response by key
- **Expiration check**: Removes expired cache entries
- **ETag validation**: Checks if content changed
- **304 response**: Returns 304 Not Modified if content unchanged
- **Last-Modified check**: Alternative to ETag for change detection
- **Header addition**: Adds cache headers to response

### **7. Response Caching (Lines 115-142)**

```python
def cache_response(self, 
                  request: Request, 
                  data: Any, 
                  cache_type: str = "dynamic",
                  user_id: Optional[str] = None,
                  custom_max_age: Optional[int] = None) -> None:
    """Cache response data with proper headers"""
    if not self._should_cache(request, cache_type):
        return
    
    cache_key = self._get_cache_key(request, user_id)
    etag = self._generate_etag(data)
    now = datetime.utcnow()
    
    # Determine cache duration
    max_age = custom_max_age or self.default_cache_durations.get(cache_type, 300)
    
    cached_data = {
        "data": data,
        "etag": etag,
        "last_modified": now.isoformat() + "Z",
        "expires_at": time.time() + max_age,
        "max_age": max_age,
        "cache_type": cache_type
    }
    
    self._cache[cache_key] = cached_data
    logger.debug(f"Cached response for {cache_key} (type: {cache_type}, max_age: {max_age}s)")
```

**What this does:**
- **Cache eligibility**: Checks if request should be cached
- **Key generation**: Creates unique cache key
- **ETag creation**: Generates content hash
- **Duration calculation**: Determines cache lifetime
- **Data storage**: Stores response data with metadata
- **Logging**: Records cache operations

### **8. Cache Header Addition (Lines 144-152)**

```python
def _add_cache_headers(self, response: Response, cached_data: Dict[str, Any]) -> None:
    """Add proper cache headers to response"""
    response.headers["ETag"] = cached_data["etag"]
    response.headers["Last-Modified"] = cached_data["last_modified"]
    response.headers["Cache-Control"] = f"max-age={cached_data['max_age']}, public"
    
    # Add Vary header for user-specific content
    if cached_data["cache_type"] == "user_data":
        response.headers["Vary"] = "Authorization"
```

**What this does:**
- **ETag header**: Adds content hash for change detection
- **Last-Modified**: Adds timestamp for change detection
- **Cache-Control**: Tells client how long to cache
- **Public caching**: Allows shared caches to store response
- **Vary header**: Indicates content varies by Authorization header

### **9. Cache Invalidation (Lines 154-173)**

```python
def invalidate_cache(self, pattern: Optional[str] = None, user_id: Optional[str] = None) -> int:
    """Invalidate cache entries matching pattern or user"""
    if not pattern and not user_id:
        # Clear all cache
        count = len(self._cache)
        self._cache.clear()
        return count
    
    keys_to_remove = []
    for key in self._cache.keys():
        if pattern and pattern in key:
            keys_to_remove.append(key)
        elif user_id and f"user:{user_id}" in key:
            keys_to_remove.append(key)
    
    for key in keys_to_remove:
        del self._cache[key]
    
    logger.info(f"Invalidated {len(keys_to_remove)} cache entries")
    return len(keys_to_remove)
```

**What this does:**
- **Pattern matching**: Removes cache entries matching pattern
- **User-specific**: Removes cache entries for specific user
- **Full clear**: Clears all cache if no pattern/user specified
- **Count return**: Returns number of entries removed
- **Logging**: Records invalidation operations

### **10. Cache Statistics (Lines 175-191)**

```python
def get_cache_stats(self) -> Dict[str, Any]:
    """Get cache statistics"""
    total_entries = len(self._cache)
    expired_entries = sum(1 for data in self._cache.values() if time.time() > data["expires_at"])
    
    cache_types = {}
    for data in self._cache.values():
        cache_type = data["cache_type"]
        cache_types[cache_type] = cache_types.get(cache_type, 0) + 1
    
    return {
        "total_entries": total_entries,
        "expired_entries": expired_entries,
        "active_entries": total_entries - expired_entries,
        "cache_types": cache_types,
        "memory_usage_estimate": sum(len(str(data["data"])) for data in self._cache.values())
    }
```

**What this does:**
- **Entry counting**: Counts total and expired entries
- **Type breakdown**: Shows distribution by cache type
- **Memory estimation**: Estimates memory usage
- **Performance metrics**: Helps monitor cache performance

### **11. Global Instance and Decorator (Lines 194-245)**

```python
# Global cache manager instance
cache_manager = CacheManager()

def get_cache_manager() -> CacheManager:
    """Get the global cache manager instance"""
    return cache_manager

def cache_response_decorator(cache_type: str = "dynamic", 
                           max_age: Optional[int] = None,
                           user_specific: bool = False):
    """
    Decorator to automatically cache API responses
    
    Args:
        cache_type: Type of cache (static, dynamic, realtime, user_data)
        max_age: Custom cache duration in seconds
        user_specific: Whether cache should be user-specific
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Extract request from arguments
            request = None
            user_id = None
            
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            # Check for cached response
            if request:
                cached_response = cache_manager.get_cached_response(request, user_id)
                if cached_response:
                    return cached_response
            
            # Execute the original function
            result = await func(*args, **kwargs) if hasattr(func, '__call__') and hasattr(func, '__code__') and func.__code__.co_flags & 0x80 else func(*args, **kwargs)
            
            # Cache the response
            if request and isinstance(result, (dict, list)):
                cache_manager.cache_response(
                    request, 
                    result, 
                    cache_type=cache_type,
                    user_id=user_id,
                    custom_max_age=max_age
                )
            
            return result
        return wrapper
    return decorator
```

**What this does:**
- **Global instance**: Single cache manager for entire app
- **Decorator**: Easy way to add caching to endpoints
- **Request extraction**: Finds request object in function arguments
- **Cache check**: Returns cached response if available
- **Function execution**: Runs original function if not cached
- **Response caching**: Caches function result

## 🎯 **Key Learning Points**

### **1. HTTP Caching Standards**
- **ETag**: Content hash for change detection
- **Last-Modified**: Timestamp for change detection
- **Cache-Control**: Tells client how long to cache
- **304 Not Modified**: Avoids sending unchanged content

### **2. Cache Management**
- **Key generation**: Unique keys for each request
- **Expiration**: Automatic removal of expired entries
- **Invalidation**: Manual cache clearing
- **Statistics**: Performance monitoring

### **3. Performance Optimization**
- **Memory storage**: Fast in-memory access
- **Content hashing**: Efficient change detection
- **Header optimization**: Proper HTTP headers
- **Bandwidth saving**: Reduces data transfer

### **4. Cache Types**
- **Static**: Long-lived data (1 hour)
- **Dynamic**: Frequently changing data (5 minutes)
- **Real-time**: Very frequent changes (1 minute)
- **User data**: User-specific content (30 minutes)

### **5. Error Handling**
- **Graceful degradation**: Continues without cache on errors
- **Validation**: Checks cache integrity
- **Logging**: Records cache operations
- **Fallback**: Handles invalid cache data

## 🚀 **How This Fits Into Your Learning**

This module demonstrates:
- **HTTP caching**: Standard web caching techniques
- **Performance optimization**: Reducing server load
- **Cache management**: Intelligent cache handling
- **HTTP headers**: Proper cache header usage
- **Decorator pattern**: Easy caching integration

**Next**: We'll explore the `compression_middleware.py` to understand response compression! 🎉
