"""
Security utilities and middleware for enhanced API protection
"""

import time
import logging
from typing import Dict, Optional, Tuple
from fastapi import Request, HTTPException
from fastapi.responses import Response
from collections import defaultdict, deque
import hashlib
import hmac
import secrets

logger = logging.getLogger(__name__)


class RateLimiter:
    """Rate limiting implementation with sliding window"""
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 3600):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = defaultdict(deque)
    
    def is_allowed(self, client_id: str) -> Tuple[bool, Dict[str, int]]:
        """Check if client is within rate limits"""
        now = time.time()
        client_requests = self.requests[client_id]
        
        # Remove old requests outside the window
        while client_requests and client_requests[0] <= now - self.window_seconds:
            client_requests.popleft()
        
        # Check if under limit
        if len(client_requests) >= self.max_requests:
            return False, {
                "limit": self.max_requests,
                "remaining": 0,
                "reset_time": int(client_requests[0] + self.window_seconds)
            }
        
        # Add current request
        client_requests.append(now)
        
        return True, {
            "limit": self.max_requests,
            "remaining": self.max_requests - len(client_requests),
            "reset_time": int(now + self.window_seconds)
        }


class SecurityHeaders:
    """Enhanced security headers for API responses"""
    
    @staticmethod
    def get_headers() -> Dict[str, str]:
        """Get comprehensive security headers"""
        return {
            # Prevent MIME type sniffing
            "X-Content-Type-Options": "nosniff",
            
            # Prevent clickjacking
            "X-Frame-Options": "DENY",
            
            # XSS protection
            "X-XSS-Protection": "1; mode=block",
            
            # Referrer policy
            "Referrer-Policy": "strict-origin-when-cross-origin",
            
            # Content Security Policy (very permissive for demo pages)
            "Content-Security-Policy": (
                "default-src 'self' 'unsafe-inline' 'unsafe-eval' data: blob: https:; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' https:; "
                "style-src 'self' 'unsafe-inline' https:; "
                "img-src 'self' data: blob: https:; "
                "connect-src 'self' https:; "
                "frame-src 'self' https:; "
                "object-src 'none'; "
                "base-uri 'self'; "
                "form-action 'self'"
            ),
            
            # Permissions Policy
            "Permissions-Policy": (
                "accelerometer=(), "
                "gyroscope=(), "
                "magnetometer=(), "
                "camera=(), "
                "microphone=(), "
                "payment=(), "
                "usb=(), "
                "serial=(), "
                "bluetooth=(), "
                "midi=(), "
                "sync-xhr=(), "
                "fullscreen=(self), "
                "picture-in-picture=()"
            ),
            
            # HSTS (if using HTTPS)
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
            
            # Cache control for sensitive endpoints
            "Cache-Control": "no-store, no-cache, must-revalidate, proxy-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
            
            # Server information hiding
            "Server": "API-Service",
            
            # Cross-Origin policies (disabled for demo pages)
            # "Cross-Origin-Embedder-Policy": "unsafe-none",  # Disabled - causes image loading issues
            "Cross-Origin-Opener-Policy": "same-origin-allow-popups",
            "Cross-Origin-Resource-Policy": "cross-origin"
        }


class APIKeyValidator:
    """Enhanced API key validation with additional security checks"""
    
    def __init__(self, valid_keys: Dict[str, Dict[str, any]]):
        self.valid_keys = valid_keys
        self.key_usage = defaultdict(int)
        self.key_last_used = {}
    
    def validate_key(self, api_key: str, client_ip: str) -> Tuple[bool, Optional[str]]:
        """Validate API key with additional security checks"""
        if not api_key:
            return False, "API key required"
        
        if api_key not in self.valid_keys:
            logger.warning(f"Invalid API key attempt from {client_ip}")
            return False, "Invalid API key"
        
        key_info = self.valid_keys[api_key]
        
        # Check if key is disabled
        if key_info.get("disabled", False):
            logger.warning(f"Disabled API key used from {client_ip}")
            return False, "API key disabled"
        
        # Check usage limits
        max_requests = key_info.get("max_requests_per_hour", 1000)
        if self.key_usage[api_key] >= max_requests:
            logger.warning(f"API key rate limit exceeded from {client_ip}")
            return False, "API key rate limit exceeded"
        
        # Update usage
        self.key_usage[api_key] += 1
        self.key_last_used[api_key] = time.time()
        
        return True, None


class RequestLogger:
    """Enhanced request logging for security monitoring"""
    
    @staticmethod
    def log_request(request: Request, response: Response, processing_time: float):
        """Log request details for security monitoring"""
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        
        # Log suspicious patterns
        suspicious_patterns = [
            "sqlmap", "nmap", "nikto", "dirb", "gobuster", "wfuzz",
            "burp", "zap", "w3af", "acunetix", "nessus"
        ]
        
        is_suspicious = any(pattern in user_agent.lower() for pattern in suspicious_patterns)
        
        log_data = {
            "method": request.method,
            "path": request.url.path,
            "client_ip": client_ip,
            "user_agent": user_agent,
            "status_code": response.status_code,
            "processing_time": processing_time,
            "is_suspicious": is_suspicious
        }
        
        if is_suspicious:
            logger.warning(f"🚨 Suspicious request detected: {log_data}")
        elif request.url.path in ["/api/health", "/health"]:
            # Reduce health check logging to debug level to avoid log spam
            logger.debug(f"💚 Health check: {log_data}")
        else:
            logger.info(f"📝 Request processed: {log_data}")


class SecurityMiddleware:
    """Comprehensive security middleware"""
    
    def __init__(self):
        # Different rate limits for different endpoints
        self.rate_limiter = RateLimiter(max_requests=1000, window_seconds=3600)  # General API (1000/hour)
        # Jawg Maps API allows 100 requests per second, so we'll be more generous
        self.map_tile_limiter = RateLimiter(max_requests=500, window_seconds=60)  # Map tiles (500/minute)
        self.security_headers = SecurityHeaders()
        self.request_logger = RequestLogger()
    
    async def __call__(self, request: Request, call_next):
        """Process request through security middleware"""
        start_time = time.time()
        
        # Get client identifier
        client_ip = request.client.host if request.client else "unknown"
        client_id = self._get_client_id(request, client_ip)
        
        # Rate limiting - use different limits for map tiles
        if "/map-tiles/" in str(request.url):
            allowed, rate_info = self.map_tile_limiter.is_allowed(client_id)
        else:
            allowed, rate_info = self.rate_limiter.is_allowed(client_id)
            
        if not allowed:
            logger.warning(f"Rate limit exceeded for {client_ip}")
            return Response(
                content='{"error": "Rate limit exceeded", "retry_after": ' + str(rate_info["reset_time"]) + '}',
                status_code=429,
                headers={"Retry-After": str(rate_info["reset_time"])}
            )
        
        # Process request
        response = await call_next(request)
        
        # Add security headers
        for header, value in self.security_headers.get_headers().items():
            response.headers[header] = value
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(rate_info["limit"])
        response.headers["X-RateLimit-Remaining"] = str(rate_info["remaining"])
        response.headers["X-RateLimit-Reset"] = str(rate_info["reset_time"])
        
        # Log request
        processing_time = time.time() - start_time
        self.request_logger.log_request(request, response, processing_time)
        
        return response
    
    def _get_client_id(self, request: Request, client_ip: str) -> str:
        """Get unique client identifier"""
        # Use IP + User-Agent for more granular rate limiting
        user_agent = request.headers.get("user-agent", "")
        return hashlib.sha256(f"{client_ip}:{user_agent}".encode()).hexdigest()[:16]


def create_api_key() -> str:
    """Generate a secure API key"""
    return secrets.token_urlsafe(32)


def validate_api_key_format(api_key: str) -> bool:
    """Validate API key format"""
    if not api_key or len(api_key) < 16:
        return False
    
    # Check for common weak patterns
    weak_patterns = ["test", "demo", "example", "123", "password", "admin"]
    if any(pattern in api_key.lower() for pattern in weak_patterns):
        return False
    
    return True
