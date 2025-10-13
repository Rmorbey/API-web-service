# 📚 Security - Complete Code Explanation

## 🎯 **Overview**

This module provides **comprehensive security features** for your API, including rate limiting, security headers, API key validation, and request logging. Think of it as the **security guard** that protects your API from abuse, attacks, and unauthorized access.

## 📁 **File Structure Context**

```
security.py  ← YOU ARE HERE (Security & Protection)
├── multi_project_api.py  (Uses this middleware)
├── strava_integration_api.py (Uses this for authentication)
└── FastAPI              (Uses this for security)
```

## 🔍 **Line-by-Line Code Explanation**

### **1. Imports and Setup (Lines 1-15)**

```python
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
```

**What this does:**
- **`time`**: For timestamp tracking and rate limiting
- **`logging`**: For security event logging
- **`typing`**: For type hints
- **`fastapi`**: For request/response handling
- **`collections`**: For efficient data structures
- **`hashlib`**: For creating secure hashes
- **`secrets`**: For generating secure random values

### **2. Rate Limiter Class (Lines 18-50)**

```python
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
```

**What this does:**
- **Sliding window**: Tracks requests over a moving time window
- **`defaultdict(deque)`**: Efficient storage for client request timestamps
- **Old request removal**: Removes requests outside the time window
- **Limit checking**: Ensures clients don't exceed rate limits
- **Request tracking**: Records each request timestamp
- **Rate limit info**: Returns limit, remaining, and reset time

**Rate Limiting Explained:**
- **Sliding window**: More accurate than fixed windows
- **Per-client tracking**: Each client has their own limit
- **Automatic cleanup**: Old requests are automatically removed
- **Real-time limits**: Limits are enforced in real-time

### **3. Security Headers Class (Lines 53-117)**

```python
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
            "Cross-Origin-Opener-Policy": "same-origin-allow-popups",
            "Cross-Origin-Resource-Policy": "cross-origin"
        }
```

**What this does:**
- **Security headers**: Comprehensive set of security headers
- **MIME type protection**: Prevents MIME type sniffing attacks
- **Clickjacking protection**: Prevents iframe embedding
- **XSS protection**: Blocks cross-site scripting attacks
- **CSP**: Content Security Policy for resource control
- **Permissions Policy**: Controls browser feature access
- **HSTS**: Forces HTTPS connections
- **Cache control**: Prevents sensitive data caching

**Security Headers Explained:**
- **`X-Content-Type-Options: nosniff`**: Prevents browsers from guessing content types
- **`X-Frame-Options: DENY`**: Prevents clickjacking attacks
- **`X-XSS-Protection: 1; mode=block`**: Enables XSS filtering
- **`Content-Security-Policy`**: Controls what resources can be loaded
- **`Permissions-Policy`**: Controls browser features like camera, microphone

### **4. API Key Validator Class (Lines 120-154)**

```python
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
```

**What this does:**
- **Key validation**: Checks if API key is valid
- **Usage tracking**: Tracks how many times each key is used
- **Rate limiting**: Enforces per-key rate limits
- **Security logging**: Logs suspicious activity
- **Key management**: Supports enabling/disabling keys

**API Key Security Features:**
- **Key validation**: Ensures key exists and is valid
- **Usage limits**: Prevents key abuse
- **Disable capability**: Can disable compromised keys
- **Audit logging**: Tracks all key usage

### **5. Request Logger Class (Lines 157-187)**

```python
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
            logger.warning(f"Suspicious request detected: {log_data}")
        else:
            logger.info(f"Request processed: {log_data}")
```

**What this does:**
- **Request logging**: Logs all API requests
- **Suspicious detection**: Identifies potential attacks
- **Performance tracking**: Records processing time
- **Security monitoring**: Helps identify threats

**Suspicious Patterns Detected:**
- **`sqlmap`**: SQL injection testing tool
- **`nmap`**: Network scanning tool
- **`nikto`**: Web vulnerability scanner
- **`burp`**: Web application security testing
- **`zap`**: OWASP ZAP security scanner

### **6. Security Middleware Class (Lines 190-245)**

```python
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
```

**What this does:**
- **Middleware function**: Processes every request
- **Rate limiting**: Different limits for different endpoints
- **Security headers**: Adds security headers to responses
- **Request logging**: Logs all requests for monitoring
- **Client identification**: Uses IP + User-Agent for unique identification

**Rate Limiting Strategy:**
- **General API**: 1000 requests per hour
- **Map tiles**: 500 requests per minute (more generous)
- **Per-client limits**: Each client has their own limit
- **Automatic reset**: Limits reset automatically

### **7. Utility Functions (Lines 248-263)**

```python
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
```

**What this does:**
- **`create_api_key()`**: Generates secure random API keys
- **`validate_api_key_format()`**: Validates API key strength
- **Weak pattern detection**: Rejects common weak patterns
- **Length validation**: Ensures minimum key length

## 🎯 **Key Learning Points**

### **1. Rate Limiting**
- **Sliding window**: More accurate than fixed windows
- **Per-client limits**: Each client has their own limit
- **Different limits**: Different endpoints can have different limits
- **Automatic cleanup**: Old requests are automatically removed

### **2. Security Headers**
- **Comprehensive protection**: Multiple layers of security
- **Browser security**: Protects against common attacks
- **Content Security Policy**: Controls resource loading
- **Permissions Policy**: Controls browser features

### **3. API Key Management**
- **Secure generation**: Uses cryptographically secure random
- **Usage tracking**: Monitors key usage patterns
- **Rate limiting**: Prevents key abuse
- **Audit logging**: Tracks all key usage

### **4. Request Monitoring**
- **Comprehensive logging**: Logs all requests
- **Suspicious detection**: Identifies potential attacks
- **Performance tracking**: Monitors response times
- **Security analysis**: Helps identify threats

### **5. Middleware Pattern**
- **Request processing**: Processes every request
- **Response enhancement**: Adds security headers
- **Error handling**: Graceful handling of security violations
- **Performance impact**: Minimal impact on response times

## 🚀 **How This Fits Into Your Learning**

This module demonstrates:
- **Security best practices**: Multiple layers of protection
- **Rate limiting**: Preventing API abuse
- **Security headers**: Browser security features
- **API key management**: Secure authentication
- **Request monitoring**: Security analysis and logging

**Next**: We'll explore the `async_processor.py` to understand background processing! 🎉
