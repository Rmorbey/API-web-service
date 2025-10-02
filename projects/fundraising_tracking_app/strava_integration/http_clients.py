#!/usr/bin/env python3
"""
HTTP Client Configuration for FastAPI
Provides optimized HTTP clients with proper FastAPI integration
"""

import httpx
import logging
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

# Global HTTP client instances
_http_client: Optional[httpx.Client] = None
_async_http_client: Optional[httpx.AsyncClient] = None

@asynccontextmanager
async def lifespan_http_clients(app):
    """
    FastAPI lifespan context manager for HTTP clients
    Properly manages client lifecycle with connection pooling
    
    Args:
        app: FastAPI application instance
    """
    global _http_client, _async_http_client
    
    # Create sync HTTP client with optimized settings
    _http_client = httpx.Client(
        timeout=30.0,
        limits=httpx.Limits(
            max_connections=20,
            max_keepalive_connections=10,
            keepalive_expiry=30.0
        ),
        # Enable HTTP/2 for better performance
        http2=True,
        # Enable compression
        headers={"Accept-Encoding": "gzip, deflate, br"}
    )
    
    # Create async HTTP client with optimized settings
    _async_http_client = httpx.AsyncClient(
        timeout=30.0,
        limits=httpx.Limits(
            max_connections=20,
            max_keepalive_connections=10,
            keepalive_expiry=30.0
        ),
        # Enable HTTP/2 for better performance
        http2=True,
        # Enable compression
        headers={"Accept-Encoding": "gzip, deflate, br"}
    )
    
    logger.info("HTTP clients initialized with connection pooling")
    
    try:
        yield
    finally:
        # Cleanup clients
        if _http_client:
            _http_client.close()
            logger.info("Sync HTTP client closed")
        
        if _async_http_client:
            await _async_http_client.aclose()
            logger.info("Async HTTP client closed")

def get_http_client() -> httpx.Client:
    """
    Get the global sync HTTP client instance
    Used for dependency injection in FastAPI endpoints
    """
    if _http_client is None:
        raise RuntimeError("HTTP client not initialized. Make sure lifespan is configured.")
    return _http_client

def get_async_http_client() -> httpx.AsyncClient:
    """
    Get the global async HTTP client instance
    Used for dependency injection in FastAPI endpoints
    """
    if _async_http_client is None:
        raise RuntimeError("Async HTTP client not initialized. Make sure lifespan is configured.")
    return _async_http_client

# FastAPI dependency functions
def get_sync_client() -> httpx.Client:
    """FastAPI dependency for sync HTTP client"""
    return get_http_client()

def get_async_client() -> httpx.AsyncClient:
    """FastAPI dependency for async HTTP client"""
    return get_async_http_client()
