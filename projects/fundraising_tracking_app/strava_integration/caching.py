"""
Advanced response caching system for improved performance
"""

import time
import json
import hashlib
import logging
from typing import Any, Dict, Optional, Callable
from datetime import datetime, timedelta
from functools import wraps
import threading
from collections import OrderedDict

logger = logging.getLogger(__name__)


class ResponseCache:
    """High-performance response cache with TTL and LRU eviction"""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache = OrderedDict()
        self.access_times = {}
        self.lock = threading.RLock()
    
    def _generate_key(self, endpoint: str, params: Dict[str, Any]) -> str:
        """Generate cache key from endpoint and parameters"""
        key_data = {
            "endpoint": endpoint,
            "params": sorted(params.items()) if params else []
        }
        key_string = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_string.encode()).hexdigest()[:16]
    
    def get(self, endpoint: str, params: Dict[str, Any]) -> Optional[Any]:
        """Get cached response if valid"""
        with self.lock:
            key = self._generate_key(endpoint, params)
            
            if key not in self.cache:
                return None
            
            # Check TTL
            cache_entry = self.cache[key]
            if time.time() > cache_entry["expires_at"]:
                del self.cache[key]
                if key in self.access_times:
                    del self.access_times[key]
                return None
            
            # Update access time for LRU
            self.access_times[key] = time.time()
            
            # Move to end (most recently used)
            self.cache.move_to_end(key)
            
            logger.debug(f"Cache hit for {endpoint}")
            return cache_entry["data"]
    
    def set(self, endpoint: str, params: Dict[str, Any], data: Any, ttl: Optional[int] = None) -> None:
        """Cache response data"""
        with self.lock:
            key = self._generate_key(endpoint, params)
            ttl = ttl or self.default_ttl
            
            # Evict if at capacity
            if len(self.cache) >= self.max_size:
                self._evict_lru()
            
            self.cache[key] = {
                "data": data,
                "expires_at": time.time() + ttl,
                "created_at": time.time(),
                "endpoint": endpoint
            }
            self.access_times[key] = time.time()
            
            logger.debug(f"Cached response for {endpoint} (TTL: {ttl}s)")
    
    def _evict_lru(self) -> None:
        """Evict least recently used item"""
        if not self.cache:
            return
        
        # Find LRU item
        lru_key = min(self.access_times.keys(), key=lambda k: self.access_times[k])
        
        # Remove from cache
        if lru_key in self.cache:
            del self.cache[lru_key]
        if lru_key in self.access_times:
            del self.access_times[lru_key]
        
        logger.debug(f"Evicted LRU cache entry: {lru_key}")
    
    def invalidate(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> int:
        """Invalidate cache entries for endpoint"""
        with self.lock:
            if params is None:
                # Invalidate all entries for endpoint
                keys_to_remove = [
                    key for key, entry in self.cache.items()
                    if entry["endpoint"] == endpoint
                ]
            else:
                # Invalidate specific entry
                key = self._generate_key(endpoint, params)
                keys_to_remove = [key] if key in self.cache else []
            
            for key in keys_to_remove:
                if key in self.cache:
                    del self.cache[key]
                if key in self.access_times:
                    del self.access_times[key]
            
            logger.debug(f"Invalidated {len(keys_to_remove)} cache entries for {endpoint}")
            return len(keys_to_remove)
    
    def clear(self) -> None:
        """Clear all cache entries"""
        with self.lock:
            self.cache.clear()
            self.access_times.clear()
            logger.info("Cache cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self.lock:
            now = time.time()
            valid_entries = sum(1 for entry in self.cache.values() if entry["expires_at"] > now)
            
            return {
                "total_entries": len(self.cache),
                "valid_entries": valid_entries,
                "max_size": self.max_size,
                "hit_ratio": getattr(self, "_hit_ratio", 0.0),
                "memory_usage_mb": self._estimate_memory_usage()
            }
    
    def _estimate_memory_usage(self) -> float:
        """Estimate cache memory usage in MB"""
        try:
            total_size = 0
            for entry in self.cache.values():
                total_size += len(json.dumps(entry["data"]).encode())
            return round(total_size / (1024 * 1024), 2)
        except:
            return 0.0


class CacheDecorator:
    """Decorator for caching function responses"""
    
    def __init__(self, cache: ResponseCache, ttl: int = 300, key_func: Optional[Callable] = None):
        self.cache = cache
        self.ttl = ttl
        self.key_func = key_func or (lambda *args, **kwargs: str(args) + str(kwargs))
    
    def __call__(self, func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = self.key_func(*args, **kwargs)
            
            # Try to get from cache
            cached_result = self.cache.get(func.__name__, {"key": cache_key})
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            self.cache.set(func.__name__, {"key": cache_key}, result, self.ttl)
            
            return result
        
        return wrapper


class CacheManager:
    """Centralized cache management"""
    
    def __init__(self):
        self.caches = {}
        self.default_cache = ResponseCache(max_size=1000, default_ttl=300)
    
    def get_cache(self, name: str = "default") -> ResponseCache:
        """Get or create named cache"""
        if name not in self.caches:
            self.caches[name] = ResponseCache(max_size=1000, default_ttl=300)
        return self.caches[name]
    
    def clear_all(self) -> None:
        """Clear all caches"""
        for cache in self.caches.values():
            cache.clear()
        self.default_cache.clear()
        logger.info("All caches cleared")
    
    def get_all_stats(self) -> Dict[str, Any]:
        """Get statistics for all caches"""
        stats = {"default": self.default_cache.get_stats()}
        for name, cache in self.caches.items():
            stats[name] = cache.get_stats()
        return stats


# Global cache manager instance
cache_manager = CacheManager()


def cached(ttl: int = 300, cache_name: str = "default"):
    """Decorator for caching function responses"""
    cache = cache_manager.get_cache(cache_name)
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            key_data = {
                "func": func.__name__,
                "args": args,
                "kwargs": kwargs
            }
            cache_key = hashlib.sha256(json.dumps(key_data, default=str).encode()).hexdigest()[:16]
            
            # Try to get from cache
            cached_result = cache.get(func.__name__, {"key": cache_key})
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache.set(func.__name__, {"key": cache_key}, result, ttl)
            
            return result
        
        return wrapper
    
    return decorator


def invalidate_cache(cache_name: str = "default", endpoint: Optional[str] = None):
    """Invalidate cache entries"""
    cache = cache_manager.get_cache(cache_name)
    if endpoint:
        return cache.invalidate(endpoint)
    else:
        cache.clear()
        return 0
