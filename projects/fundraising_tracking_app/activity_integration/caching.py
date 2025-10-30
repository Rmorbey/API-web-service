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
    
    def _generate_etag(self, data: Any) -> str:
        """Generate ETag from data content"""
        if isinstance(data, dict):
            # Sort keys for consistent hashing
            data_str = json.dumps(data, sort_keys=True, default=str)
        else:
            data_str = str(data)
        
        return f'"{hashlib.md5(data_str.encode()).hexdigest()}"'
    
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
    
    def _add_cache_headers(self, response: Response, cached_data: Dict[str, Any]) -> None:
        """Add proper cache headers to response"""
        response.headers["ETag"] = cached_data["etag"]
        response.headers["Last-Modified"] = cached_data["last_modified"]
        response.headers["Cache-Control"] = f"max-age={cached_data['max_age']}, public"
        
        # Add Vary header for user-specific content
        if cached_data["cache_type"] == "user_data":
            response.headers["Vary"] = "Authorization"
    
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