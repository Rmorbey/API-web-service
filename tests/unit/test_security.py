"""
Unit tests for security functionality.
Tests API key validation, rate limiting, and security middleware.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi import Request, HTTPException
from fastapi.responses import Response
import time
from datetime import datetime, timedelta

from projects.fundraising_tracking_app.strava_integration.security import (
    RateLimiter,
    SecurityMiddleware,
    APIKeyValidator,
    validate_api_key_format
)


class TestRateLimiter:
    """Test rate limiting functionality."""
    
    def test_rate_limiter_initialization(self):
        """Test rate limiter initialization with default values."""
        limiter = RateLimiter()
        
        assert limiter.max_requests == 100
        assert limiter.window_seconds == 3600
        assert len(limiter.requests) == 0
    
    def test_rate_limiter_custom_limits(self):
        """Test rate limiter with custom limits."""
        limiter = RateLimiter(max_requests=50, window_seconds=1800)
        
        assert limiter.max_requests == 50
        assert limiter.window_seconds == 1800
    
    def test_rate_limiter_allows_requests_within_limit(self):
        """Test that rate limiter allows requests within the limit."""
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        client_id = "test_client"
        
        # Make 5 requests (within limit)
        for i in range(5):
            allowed, info = limiter.is_allowed(client_id)
            assert allowed is True
            assert info["remaining"] == 5 - (i + 1)
            assert info["limit"] == 5
    
    def test_rate_limiter_blocks_requests_over_limit(self):
        """Test that rate limiter blocks requests over the limit."""
        limiter = RateLimiter(max_requests=3, window_seconds=60)
        client_id = "test_client"
        
        # Make 3 requests (at limit)
        for i in range(3):
            allowed, info = limiter.is_allowed(client_id)
            assert allowed is True
        
        # 4th request should be blocked
        allowed, info = limiter.is_allowed(client_id)
        assert allowed is False
        assert info["remaining"] == 0
        assert info["limit"] == 3
    
    def test_rate_limiter_resets_after_window(self):
        """Test that rate limiter resets after the time window."""
        limiter = RateLimiter(max_requests=2, window_seconds=1)  # 1 second window
        client_id = "test_client"
        
        # Make 2 requests (at limit)
        allowed, info = limiter.is_allowed(client_id)
        assert allowed is True
        allowed, info = limiter.is_allowed(client_id)
        assert allowed is True
        
        # 3rd request should be blocked
        allowed, info = limiter.is_allowed(client_id)
        assert allowed is False
        
        # Wait for window to reset
        time.sleep(1.1)
        
        # Should be allowed again
        allowed, info = limiter.is_allowed(client_id)
        assert allowed is True
    
    def test_rate_limiter_different_clients(self):
        """Test that rate limiter tracks different clients separately."""
        limiter = RateLimiter(max_requests=2, window_seconds=60)
        client1 = "client1"
        client2 = "client2"
        
        # Client 1 makes 2 requests
        allowed, _ = limiter.is_allowed(client1)
        assert allowed is True
        allowed, _ = limiter.is_allowed(client1)
        assert allowed is True
        
        # Client 1 should be blocked
        allowed, _ = limiter.is_allowed(client1)
        assert allowed is False
        
        # Client 2 should still be allowed
        allowed, _ = limiter.is_allowed(client2)
        assert allowed is True
        allowed, _ = limiter.is_allowed(client2)
        assert allowed is True
        
        # Client 2 should now be blocked
        allowed, _ = limiter.is_allowed(client2)
        assert allowed is False


class TestAPIKeyValidation:
    """Test API key validation functionality."""
    
    def test_api_key_validator_initialization(self):
        """Test APIKeyValidator initialization."""
        validator = APIKeyValidator()
        assert hasattr(validator, 'valid_keys')
    
    def test_validate_api_key_format_valid(self):
        """Test validation with valid API key format."""
        valid_key = "test-api-key-123"
        result = validate_api_key_format(valid_key)
        assert result is True
    
    def test_validate_api_key_format_invalid(self):
        """Test validation with invalid API key format."""
        invalid_key = "short"
        result = validate_api_key_format(invalid_key)
        assert result is False
    
    def test_validate_api_key_format_none(self):
        """Test validation with None API key."""
        result = validate_api_key_format(None)
        assert result is False
    
    def test_validate_api_key_format_empty(self):
        """Test validation with empty API key."""
        result = validate_api_key_format("")
        assert result is False
    
    def test_api_key_validator_with_valid_key(self):
        """Test APIKeyValidator with valid key."""
        validator = APIKeyValidator()
        valid_key = "test-api-key-123"
        
        # Add valid key
        validator.valid_keys.add(valid_key)
        
        # Should validate successfully
        result = validator.validate(valid_key)
        assert result is True
    
    def test_api_key_validator_with_invalid_key(self):
        """Test APIKeyValidator with invalid key."""
        validator = APIKeyValidator()
        valid_key = "test-api-key-123"
        invalid_key = "wrong-key"
        
        # Add valid key
        validator.valid_keys.add(valid_key)
        
        # Should fail validation
        result = validator.validate(invalid_key)
        assert result is False


class TestSecurityHeaders:
    """Test security headers functionality."""
    
    def test_security_headers_class_initialization(self):
        """Test SecurityHeaders class initialization."""
        from projects.fundraising_tracking_app.strava_integration.security import SecurityHeaders
        
        headers = SecurityHeaders()
        assert hasattr(headers, 'get_headers')
    
    def test_security_headers_content(self):
        """Test that security headers contain expected values."""
        from projects.fundraising_tracking_app.strava_integration.security import SecurityHeaders
        
        headers = SecurityHeaders()
        header_dict = headers.get_headers()
        
        # Check that security headers are present
        expected_headers = [
            "X-Content-Type-Options",
            "X-Frame-Options",
            "X-XSS-Protection"
        ]
        
        for header in expected_headers:
            assert header in header_dict
            assert header_dict[header] is not None


class TestSecurityMiddleware:
    """Test security middleware functionality."""
    
    def test_security_middleware_initialization(self):
        """Test security middleware initialization."""
        middleware = SecurityMiddleware()
        
        assert hasattr(middleware, 'rate_limiter')
        assert hasattr(middleware, 'api_key_validator')
        assert isinstance(middleware.rate_limiter, RateLimiter)
        assert isinstance(middleware.api_key_validator, APIKeyValidator)
    
    @pytest.mark.asyncio
    async def test_security_middleware_basic_functionality(self):
        """Test basic security middleware functionality."""
        middleware = SecurityMiddleware()
        
        # Create a mock request
        request = Mock(spec=Request)
        request.method = "GET"
        request.url.path = "/api/health"
        request.client.host = "127.0.0.1"
        request.headers = {"user-agent": "Mozilla/5.0 (compatible)"}
        
        # Create a mock call_next function
        call_next = Mock()
        call_next.return_value = Response(status_code=200)
        
        # Process the request
        response = await middleware(request, call_next)
        
        # Should process the request (exact behavior depends on implementation)
        assert response is not None
        call_next.assert_called_once_with(request)


class TestSecurityIntegration:
    """Test security features working together."""
    
    def test_rate_limiter_with_api_validator(self):
        """Test rate limiter working with API key validator."""
        limiter = RateLimiter(max_requests=2, window_seconds=60)
        validator = APIKeyValidator()
        
        # Add a valid API key
        valid_key = "test-api-key-123"
        validator.valid_keys.add(valid_key)
        
        # Test that both systems work together
        client_id = "test_client"
        
        # Rate limiter should allow requests
        allowed, info = limiter.is_allowed(client_id)
        assert allowed is True
        
        # API validator should validate keys
        result = validator.validate(valid_key)
        assert result is True
    
    def test_security_components_initialization(self):
        """Test that all security components can be initialized together."""
        from projects.fundraising_tracking_app.strava_integration.security import (
            RateLimiter, SecurityHeaders, APIKeyValidator, SecurityMiddleware
        )
        
        # Test that all components can be created
        limiter = RateLimiter()
        headers = SecurityHeaders()
        validator = APIKeyValidator()
        middleware = SecurityMiddleware()
        
        # All should be properly initialized
        assert limiter is not None
        assert headers is not None
        assert validator is not None
        assert middleware is not None
