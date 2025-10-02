#!/usr/bin/env python3
"""
FastAPI Cache Middleware
Automatically handles HTTP caching for API responses
"""

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable, Optional
import logging
import time

from .caching import cache_manager

logger = logging.getLogger(__name__)

class CacheMiddleware(BaseHTTPMiddleware):
    """
    Middleware to automatically cache API responses with proper HTTP headers
    """
    
    def __init__(self, app, cache_routes: Optional[dict] = None):
        super().__init__(app)
        
        # Define cache rules for specific routes
        self.cache_rules = cache_routes or {
            # Static data - cache for 1 hour
            "/api/strava-integration/": {"type": "static", "max_age": 3600},
            "/api/fundraising/": {"type": "static", "max_age": 3600},
            
            # Dynamic data - cache for 5 minutes
            "/api/strava-integration/feed": {"type": "dynamic", "max_age": 300},
            "/api/strava-integration/activities": {"type": "dynamic", "max_age": 300},
            "/api/fundraising/data": {"type": "dynamic", "max_age": 300},
            "/api/fundraising/donations": {"type": "dynamic", "max_age": 300},
            
            # Real-time data - cache for 1 minute
            "/api/strava-integration/health": {"type": "realtime", "max_age": 60},
            "/api/fundraising/health": {"type": "realtime", "max_age": 60},
            "/api/strava-integration/metrics": {"type": "realtime", "max_age": 60},
            
            # User-specific data - cache for 30 minutes
            "/api/strava-integration/refresh-cache": {"type": "user_data", "max_age": 1800},
            "/api/fundraising/refresh": {"type": "user_data", "max_age": 1800},
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with caching logic"""
        
        # Only cache GET requests
        if request.method != "GET":
            return await call_next(request)
        
        # Check if route should be cached
        cache_rule = self._get_cache_rule(request.url.path)
        if not cache_rule:
            return await call_next(request)
        
        # Extract user ID if available (for user-specific caching)
        user_id = self._extract_user_id(request)
        
        # Check for cached response
        cached_response = cache_manager.get_cached_response(request, user_id)
        if cached_response:
            logger.debug(f"Cache hit for {request.url.path}")
            return cached_response
        
        # Process request
        start_time = time.time()
        response = await call_next(request)
        processing_time = time.time() - start_time
        
        # Only cache successful responses
        if response.status_code == 200 and hasattr(response, 'body'):
            try:
                # Try to parse JSON response
                import json
                response_data = json.loads(response.body.decode())
                
                # Cache the response
                cache_manager.cache_response(
                    request,
                    response_data,
                    cache_type=cache_rule["type"],
                    user_id=user_id,
                    custom_max_age=cache_rule.get("max_age")
                )
                
                # Add cache headers to response
                self._add_cache_headers(response, cache_rule)
                
                logger.debug(f"Cached response for {request.url.path} (took {processing_time:.3f}s)")
                
            except (json.JSONDecodeError, AttributeError):
                # Not a JSON response or can't parse, don't cache
                logger.debug(f"Skipping cache for non-JSON response: {request.url.path}")
        
        return response
    
    def _get_cache_rule(self, path: str) -> Optional[dict]:
        """Get cache rule for the given path"""
        # Exact match first
        if path in self.cache_rules:
            return self.cache_rules[path]
        
        # Pattern matching for dynamic routes
        for pattern, rule in self.cache_rules.items():
            if pattern.endswith("*") and path.startswith(pattern[:-1]):
                return rule
        
        return None
    
    def _extract_user_id(self, request: Request) -> Optional[str]:
        """Extract user ID from request for user-specific caching"""
        # Try to get user ID from various sources
        api_key = request.headers.get("x-api-key")
        if api_key:
            # Use API key as user identifier
            return f"api_key:{api_key[:8]}"  # Use first 8 chars for privacy
        
        # Could also extract from JWT token, session, etc.
        return None
    
    def _add_cache_headers(self, response: Response, cache_rule: dict) -> None:
        """Add cache headers to response"""
        max_age = cache_rule.get("max_age", 300)
        cache_type = cache_rule.get("type", "dynamic")
        
        # Set Cache-Control header
        if cache_type == "user_data":
            response.headers["Cache-Control"] = f"max-age={max_age}, private"
            response.headers["Vary"] = "Authorization, X-API-Key"
        else:
            response.headers["Cache-Control"] = f"max-age={max_age}, public"
        
        # Add ETag header
        if hasattr(response, 'body') and response.body:
            import hashlib
            etag = f'"{hashlib.md5(response.body).hexdigest()}"'
            response.headers["ETag"] = etag
        
        # Add Last-Modified header
        from datetime import datetime
        response.headers["Last-Modified"] = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")


def create_cache_middleware(cache_routes: Optional[dict] = None) -> CacheMiddleware:
    """Create cache middleware with custom cache rules"""
    return CacheMiddleware(None, cache_routes)
