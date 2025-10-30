#!/usr/bin/env python3
"""
Fixed Security Tests
Tests the actual security implementation in the security module
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from collections import deque
from fastapi import Request, Response
from fastapi.responses import JSONResponse

from projects.fundraising_tracking_app.activity_integration.security import (
    RateLimiter,
    SecurityHeaders,
    APIKeyValidator,
    RequestLogger,
    SecurityMiddleware,
    validate_api_key_format
)


class TestRateLimiter:
    """Test the RateLimiter class"""
    
    def test_rate_limiter_initialization(self):
        """Test RateLimiter initialization with default values."""
        limiter = RateLimiter()
        assert limiter.max_requests == 100
        assert limiter.window_seconds == 3600
        assert hasattr(limiter, 'requests')
    
    def test_rate_limiter_initialization_with_custom_values(self):
        """Test RateLimiter initialization with custom values."""
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
            assert "remaining" in info
            assert "reset_time" in info
    
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
        assert "remaining" in info
        assert "reset_time" in info


class TestSecurityHeaders:
    """Test the SecurityHeaders class"""
    
    def test_security_headers_initialization(self):
        """Test SecurityHeaders initialization."""
        headers = SecurityHeaders()
        assert hasattr(headers, 'get_headers')
    
    def test_security_headers_get_headers(self):
        """Test that get_headers returns security headers."""
        headers = SecurityHeaders()
        security_headers = headers.get_headers()
        
        assert isinstance(security_headers, dict)
        # Check for common security headers
        expected_headers = [
            'X-Content-Type-Options',
            'X-Frame-Options',
            'X-XSS-Protection',
            'Referrer-Policy',
            'Content-Security-Policy'
        ]
        
        for header in expected_headers:
            assert header in security_headers


class TestAPIKeyValidator:
    """Test the APIKeyValidator class"""
    
    def test_api_key_validator_initialization(self):
        """Test APIKeyValidator initialization with valid keys."""
        valid_keys = {
            "test-key-123": {"enabled": True, "permissions": ["read"]},
            "test-key-456": {"enabled": True, "permissions": ["read", "write"]}
        }
        validator = APIKeyValidator(valid_keys)
        assert validator.valid_keys == valid_keys
        assert hasattr(validator, 'key_usage')
        assert hasattr(validator, 'key_last_used')
    
    def test_validate_key_with_valid_key(self):
        """Test validation with a valid API key."""
        valid_keys = {
            "test-key-123": {"enabled": True, "permissions": ["read"]}
        }
        validator = APIKeyValidator(valid_keys)
        
        is_valid, message = validator.validate_key("test-key-123", "127.0.0.1")
        assert is_valid is True
        assert message is None
    
    def test_validate_key_with_invalid_key(self):
        """Test validation with an invalid API key."""
        valid_keys = {
            "test-key-123": {"enabled": True, "permissions": ["read"]}
        }
        validator = APIKeyValidator(valid_keys)
        
        is_valid, message = validator.validate_key("invalid-key", "127.0.0.1")
        assert is_valid is False
        assert "Invalid API key" in message
    
    def test_validate_key_with_empty_key(self):
        """Test validation with an empty API key."""
        valid_keys = {
            "test-key-123": {"enabled": True, "permissions": ["read"]}
        }
        validator = APIKeyValidator(valid_keys)
        
        is_valid, message = validator.validate_key("", "127.0.0.1")
        assert is_valid is False
        assert "API key required" in message
    
    def test_validate_key_with_disabled_key(self):
        """Test validation with a disabled API key."""
        valid_keys = {
            "test-key-123": {"disabled": True, "permissions": ["read"]}
        }
        validator = APIKeyValidator(valid_keys)
        
        is_valid, message = validator.validate_key("test-key-123", "127.0.0.1")
        assert is_valid is False
        assert "disabled" in message.lower()


class TestRequestLogger:
    """Test the RequestLogger class"""
    
    def test_request_logger_initialization(self):
        """Test RequestLogger initialization."""
        logger = RequestLogger()
        assert hasattr(logger, 'log_request')
    
    def test_log_request(self):
        """Test request logging functionality."""
        logger = RequestLogger()
        
        # Mock request with proper structure
        request = Mock()
        request.method = "GET"
        request.url = Mock()
        request.url.path = "/api/test"
        request.client = Mock()
        request.client.host = "127.0.0.1"
        request.headers = {"user-agent": "Mozilla/5.0"}
        
        # Mock response
        response = Mock()
        response.status_code = 200
        
        # Should not raise an exception
        try:
            logger.log_request(request, response, 0.1)
            assert True
        except Exception as e:
            pytest.fail(f"log_request raised an exception: {e}")


class TestSecurityMiddleware:
    """Test the SecurityMiddleware class"""
    
    def test_security_middleware_initialization(self):
        """Test SecurityMiddleware initialization."""
        middleware = SecurityMiddleware()
        assert hasattr(middleware, 'rate_limiter')
        assert hasattr(middleware, 'map_tile_limiter')
        assert hasattr(middleware, 'security_headers')
        assert hasattr(middleware, 'request_logger')
    
    @pytest.mark.asyncio
    async def test_security_middleware_basic_functionality(self):
        """Test basic security middleware functionality."""
        middleware = SecurityMiddleware()
        
        # Mock request
        request = Mock()
        request.method = "GET"
        request.url = Mock()
        request.url.path = "/api/test"
        request.client = Mock()
        request.client.host = "127.0.0.1"
        request.headers = {"user-agent": "Mozilla/5.0"}
        
        # Mock call_next function
        async def mock_call_next(req):
            return Response(content='{"status": "ok"}', status_code=200)
        
        # Test middleware execution
        response = await middleware(request, mock_call_next)
        
        assert response.status_code == 200
        assert isinstance(response, Response)
    
    @pytest.mark.asyncio
    async def test_security_middleware_rate_limiting(self):
        """Test rate limiting functionality."""
        middleware = SecurityMiddleware()
        
        # Mock request
        request = Mock()
        request.method = "GET"
        request.url = Mock()
        request.url.path = "/api/test"
        request.client = Mock()
        request.client.host = "127.0.0.1"
        request.headers = {"user-agent": "Mozilla/5.0"}
        
        # Mock call_next function
        async def mock_call_next(req):
            return Response(content='{"status": "ok"}', status_code=200)
        
        # Make multiple requests to test rate limiting
        responses = []
        for i in range(5):  # Should be within limit
            response = await middleware(request, mock_call_next)
            responses.append(response)
        
        # All requests should succeed
        assert all(r.status_code == 200 for r in responses)
    
    @pytest.mark.asyncio
    async def test_security_middleware_map_tile_rate_limiting(self):
        """Test map tile specific rate limiting."""
        middleware = SecurityMiddleware()
        
        # Mock map tile request
        request = Mock()
        request.method = "GET"
        request.url = Mock()
        request.url.path = "/api/activity-integration/map-tiles/10/512/384"
        request.client = Mock()
        request.client.host = "127.0.0.1"
        request.headers = {"user-agent": "Mozilla/5.0"}
        
        # Mock call_next function
        async def mock_call_next(req):
            return Response(content='{"status": "ok"}', status_code=200)
        
        # Make multiple map tile requests
        responses = []
        for i in range(10):  # Should be within map tile limit
            response = await middleware(request, mock_call_next)
            responses.append(response)
        
        # All requests should succeed
        assert all(r.status_code == 200 for r in responses)


class TestAPIKeyFormatValidation:
    """Test the validate_api_key_format function"""
    
    def test_validate_api_key_format_valid(self):
        """Test validation with valid API key format."""
        valid_key = "prod-api-key-abcdefghijklmnop"
        result = validate_api_key_format(valid_key)
        assert result is True
    
    def test_validate_api_key_format_invalid_short(self):
        """Test validation with invalid short API key."""
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
    
    def test_validate_api_key_format_with_special_chars(self):
        """Test validation with API key containing special characters."""
        # Valid format with hyphens and letters (no weak patterns)
        valid_key = "prod-key-abcdefghijklmnop-xyz"
        result = validate_api_key_format(valid_key)
        assert result is True
        
        # Invalid format with weak pattern
        invalid_key = "test-key-abcdefghijklmnop"
        result = validate_api_key_format(invalid_key)
        assert result is False


class TestSecurityIntegration:
    """Test security components integration"""
    
    def test_rate_limiter_with_api_validator(self):
        """Test rate limiter integration with API key validator."""
        # Create rate limiter
        limiter = RateLimiter(max_requests=3, window_seconds=60)
        
        # Create API key validator
        valid_keys = {
            "test-key-123": {"enabled": True, "permissions": ["read"]}
        }
        validator = APIKeyValidator(valid_keys)
        
        # Test both components work together
        client_id = "test_client"
        
        # Rate limiter should allow requests
        allowed, rate_info = limiter.is_allowed(client_id)
        assert allowed is True
        
        # API key validator should validate keys
        is_valid, message = validator.validate_key("test-key-123", "127.0.0.1")
        assert is_valid is True
    
    def test_security_components_initialization(self):
        """Test that all security components can be initialized together."""
        # Initialize all components
        rate_limiter = RateLimiter()
        map_tile_limiter = RateLimiter(max_requests=500, window_seconds=60)
        security_headers = SecurityHeaders()
        request_logger = RequestLogger()
        
        valid_keys = {
            "test-key-123": {"enabled": True, "permissions": ["read"]}
        }
        api_validator = APIKeyValidator(valid_keys)
        
        # Create middleware with all components
        middleware = SecurityMiddleware()
        
        # All components should be properly initialized
        assert middleware.rate_limiter is not None
        assert middleware.map_tile_limiter is not None
        assert middleware.security_headers is not None
        assert middleware.request_logger is not None
        
        # Individual components should work
        assert rate_limiter.max_requests == 100
        assert map_tile_limiter.max_requests == 500
        assert len(security_headers.get_headers()) > 0
        assert api_validator.valid_keys == valid_keys


class TestCoverageGaps:
    """Test cases to cover missing lines in security.py"""
    
    def test_rate_limiter_window_cleanup(self):
        """Test that old requests are removed from the window"""
        limiter = RateLimiter(max_requests=2, window_seconds=1)
        
        # Add requests at different times
        limiter.requests["test_client"] = deque([0, 0.5])  # Old requests
        
        # This should trigger cleanup of old requests
        allowed, _ = limiter.is_allowed("test_client")
        assert allowed is True
    
    def test_api_key_rate_limit_exceeded(self):
        """Test API key rate limit exceeded scenario"""
        validator = APIKeyValidator({"test_key": {"max_requests_per_hour": 1000}})
        validator.key_usage["test_key"] = 1000  # Set to max limit
        
        result, message = validator.validate_key("test_key", "127.0.0.1")
        
        assert result is False
        assert "rate limit exceeded" in message.lower()
    
    def test_suspicious_request_detection(self):
        """Test suspicious request detection and logging"""
        # Mock request and response
        request = Mock()
        request.method = "GET"
        request.url.path = "/api/test"
        request.client.host = "127.0.0.1"
        request.headers = {"user-agent": "sqlmap/1.0"}  # Suspicious user agent
        
        response = Mock()
        response.status_code = 200
        
        # Mock logger to capture warning calls
        with patch('projects.fundraising_tracking_app.activity_integration.security.logger') as mock_logger:
            # Call the static method
            RequestLogger.log_request(request, response, 0.1)
            
            # Check that warning was logged
            mock_logger.warning.assert_called_once()
            assert "Suspicious request detected" in str(mock_logger.warning.call_args)
    
    @pytest.mark.asyncio
    async def test_rate_limit_exceeded_warning(self):
        """Test rate limit exceeded warning in middleware"""
        middleware = SecurityMiddleware()
        
        # Mock request
        request = Mock()
        request.method = "GET"
        request.url = Mock()
        request.url.path = "/api/test"
        request.client = Mock()
        request.client.host = "127.0.0.1"
        request.headers = {"user-agent": "Mozilla/5.0"}
        
        # Mock rate limiter to return False (rate limited)
        with patch.object(middleware.rate_limiter, 'is_allowed', return_value=(False, {"reset_time": 60})):
            with patch('projects.fundraising_tracking_app.activity_integration.security.logger') as mock_logger:
                async def mock_call_next(req):
                    return Response(content='{"status": "ok"}', status_code=200)
                
                response = await middleware(request, mock_call_next)
                
                # Check that warning was logged
                mock_logger.warning.assert_called_once()
                assert "Rate limit exceeded" in str(mock_logger.warning.call_args)
                assert response.status_code == 429
    
    def test_create_api_key_generation(self):
        """Test API key generation"""
        from projects.fundraising_tracking_app.activity_integration.security import create_api_key
        
        # Generate multiple keys to ensure randomness
        key1 = create_api_key()
        key2 = create_api_key()
        
        # Keys should be different and valid
        assert key1 != key2
        assert len(key1) == 43  # 32 bytes base64 encoded
        assert len(key2) == 43
        assert isinstance(key1, str)
        assert isinstance(key2, str)
