"""
Unit tests for error handling functionality.
Tests custom error handlers, exception classes, and error response structures.
"""

import pytest
from unittest.mock import Mock, patch
from fastapi import Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import json
from datetime import datetime

from projects.fundraising_tracking_app.strava_integration.simple_error_handlers import (
    http_exception_handler,
    validation_exception_handler,
    general_exception_handler
)
from projects.fundraising_tracking_app.strava_integration.error_handlers import (
    AuthenticationException,
    AuthorizationException,
    ValidationException,
    ExternalServiceException,
    APIException
)


class TestCustomExceptionClasses:
    """Test custom exception classes."""
    
    def test_authentication_exception(self):
        """Test AuthenticationException creation and properties."""
        message = "Invalid credentials"
        exc = AuthenticationException(message)
        
        assert str(exc) == message
        assert isinstance(exc, Exception)
    
    def test_authorization_exception(self):
        """Test AuthorizationException creation and properties."""
        message = "Access denied"
        exc = AuthorizationException(message)
        
        assert str(exc) == message
        assert isinstance(exc, Exception)
    
    def test_validation_exception(self):
        """Test ValidationException creation and properties."""
        message = "Invalid input data"
        exc = ValidationException(message)
        
        assert str(exc) == message
        assert isinstance(exc, Exception)
    
    def test_external_service_exception(self):
        """Test ExternalServiceException creation and properties."""
        message = "External service unavailable"
        exc = ExternalServiceException(message)
        
        assert str(exc) == message
        assert isinstance(exc, Exception)
    
    def test_api_exception(self):
        """Test APIException creation and properties."""
        message = "API error occurred"
        error_code = "API_ERROR"
        status_code = 500
        exc = APIException(message, error_code=error_code, status_code=status_code)
        
        assert str(exc) == message
        assert exc.error_code == error_code
        assert exc.status_code == status_code
        assert isinstance(exc, Exception)


class TestErrorHandlers:
    """Test custom error handlers."""
    
    @pytest.mark.asyncio
    async def test_http_exception_handler(self):
        """Test HTTP exception handler."""
        # Create a mock request
        request = Mock(spec=Request)
        request.url.path = "/test/path"
        request.method = "GET"
        
        # Create an HTTP exception
        exc = HTTPException(status_code=404, detail="Not found")
        
        # Call the handler
        response = await http_exception_handler(request, exc)
        
        # Verify response
        assert isinstance(response, JSONResponse)
        assert response.status_code == 404
        
        # Parse response content
        content = json.loads(response.body.decode())
        assert content["success"] is False
        assert content["error"] == "Not found"
        assert content["status_code"] == 404
        assert "timestamp" in content
        assert "request_id" in content
    
    @pytest.mark.asyncio
    async def test_validation_exception_handler(self):
        """Test validation exception handler."""
        # Create a mock request
        request = Mock(spec=Request)
        request.url.path = "/test/path"
        request.method = "POST"
        
        # Create validation errors
        errors = [
            {
                "type": "missing",
                "loc": ["body", "field1"],
                "msg": "Field required",
                "input": None
            },
            {
                "type": "type_error",
                "loc": ["body", "field2"],
                "msg": "Input should be a valid integer",
                "input": "not_a_number"
            }
        ]
        
        # Create a validation exception
        exc = RequestValidationError(errors, body={"field2": "not_a_number"})
        
        # Call the handler
        response = await validation_exception_handler(request, exc)
        
        # Verify response
        assert isinstance(response, JSONResponse)
        assert response.status_code == 422
        
        # Parse response content
        content = json.loads(response.body.decode())
        assert content["success"] is False
        assert content["error"] == "Validation error"
        assert content["status_code"] == 422
        assert "timestamp" in content
        assert "request_id" in content
        assert "details" in content
        assert "validation_errors" in content["details"]
        assert len(content["details"]["validation_errors"]) == 2
    
    @pytest.mark.asyncio
    async def test_general_exception_handler(self):
        """Test general exception handler."""
        # Create a mock request
        request = Mock(spec=Request)
        request.url.path = "/test/path"
        request.method = "GET"
        
        # Create a general exception
        exc = ValueError("Something went wrong")
        
        # Call the handler
        response = await general_exception_handler(request, exc)
        
        # Verify response
        assert isinstance(response, JSONResponse)
        assert response.status_code == 500
        
        # Parse response content
        content = json.loads(response.body.decode())
        assert content["success"] is False
        assert content["error"] == "Internal server error"
        assert content["status_code"] == 500
        assert "timestamp" in content
        assert "request_id" in content
        assert "details" in content
        assert content["details"]["exception_type"] == "ValueError"
        assert content["details"]["exception_message"] == "Something went wrong"


class TestErrorResponseStructure:
    """Test error response structure and consistency."""
    
    @pytest.mark.asyncio
    async def test_error_response_consistency(self):
        """Test that all error responses have consistent structure."""
        request = Mock(spec=Request)
        request.url.path = "/test/path"
        request.method = "GET"
        
        # Test different exception types
        exceptions = [
            HTTPException(status_code=400, detail="Bad request"),
            HTTPException(status_code=401, detail="Unauthorized"),
            HTTPException(status_code=403, detail="Forbidden"),
            HTTPException(status_code=404, detail="Not found"),
            HTTPException(status_code=500, detail="Internal server error")
        ]
        
        for exc in exceptions:
            response = await http_exception_handler(request, exc)
            content = json.loads(response.body.decode())
            
            # Check required fields
            assert "success" in content
            assert "error" in content
            assert "status_code" in content
            assert "timestamp" in content
            assert "request_id" in content
            
            # Check field types
            assert isinstance(content["success"], bool)
            assert isinstance(content["error"], str)
            assert isinstance(content["status_code"], int)
            assert isinstance(content["timestamp"], str)
            assert isinstance(content["request_id"], str)
            
            # Check success is always False for errors
            assert content["success"] is False
    
    @pytest.mark.asyncio
    async def test_request_id_uniqueness(self):
        """Test that request IDs are unique across different requests."""
        request = Mock(spec=Request)
        request.url.path = "/test/path"
        request.method = "GET"
        
        exc = HTTPException(status_code=400, detail="Bad request")
        
        # Generate multiple responses
        responses = []
        for _ in range(5):
            response = await http_exception_handler(request, exc)
            content = json.loads(response.body.decode())
            responses.append(content["request_id"])
        
        # Check that all request IDs are unique
        assert len(set(responses)) == 5
    
    @pytest.mark.asyncio
    async def test_timestamp_format(self):
        """Test that timestamps are in ISO format."""
        request = Mock(spec=Request)
        request.url.path = "/test/path"
        request.method = "GET"
        
        exc = HTTPException(status_code=400, detail="Bad request")
        response = await http_exception_handler(request, exc)
        content = json.loads(response.body.decode())
        
        # Try to parse the timestamp
        timestamp = content["timestamp"]
        parsed_timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        
        # Check that it's a valid datetime
        assert isinstance(parsed_timestamp, datetime)


class TestSecurityErrorHandling:
    """Test security-related error handling."""
    
    @pytest.mark.asyncio
    async def test_authentication_error_handling(self):
        """Test handling of authentication errors."""
        request = Mock(spec=Request)
        request.url.path = "/api/protected"
        request.method = "GET"
        
        # Test 401 Unauthorized
        exc = HTTPException(status_code=401, detail="API key required")
        response = await http_exception_handler(request, exc)
        
        content = json.loads(response.body.decode())
        assert response.status_code == 401
        assert content["error"] == "API key required"
        assert "request_id" in content
    
    @pytest.mark.asyncio
    async def test_authorization_error_handling(self):
        """Test handling of authorization errors."""
        request = Mock(spec=Request)
        request.url.path = "/api/admin"
        request.method = "POST"
        
        # Test 403 Forbidden
        exc = HTTPException(status_code=403, detail="Insufficient permissions")
        response = await http_exception_handler(request, exc)
        
        content = json.loads(response.body.decode())
        assert response.status_code == 403
        assert content["error"] == "Insufficient permissions"
        assert "request_id" in content
    
    @pytest.mark.asyncio
    async def test_rate_limiting_error_handling(self):
        """Test handling of rate limiting errors."""
        request = Mock(spec=Request)
        request.url.path = "/api/endpoint"
        request.method = "GET"
        
        # Test 429 Too Many Requests
        exc = HTTPException(status_code=429, detail="Rate limit exceeded")
        response = await http_exception_handler(request, exc)
        
        content = json.loads(response.body.decode())
        assert response.status_code == 429
        assert content["error"] == "Rate limit exceeded"
        assert "request_id" in content


class TestErrorLogging:
    """Test error logging functionality."""
    
    @pytest.mark.asyncio
    async def test_error_logging_with_mock_logger(self):
        """Test that errors are properly logged."""
        request = Mock(spec=Request)
        request.url.path = "/test/path"
        request.method = "GET"
        
        exc = HTTPException(status_code=500, detail="Internal error")
        
        # Mock the logger
        with patch('projects.fundraising_tracking_app.strava_integration.simple_error_handlers.logger') as mock_logger:
            await http_exception_handler(request, exc)
            
            # Verify that warning was logged
            mock_logger.warning.assert_called_once()
            call_args = mock_logger.warning.call_args
            
            # Check log message contains expected information
            log_message = call_args[0][0]
            assert "HTTP Exception" in log_message
            assert "500" in log_message
            assert "Internal error" in log_message
    
    @pytest.mark.asyncio
    async def test_validation_error_logging(self):
        """Test that validation errors are properly logged."""
        request = Mock(spec=Request)
        request.url.path = "/test/path"
        request.method = "POST"
        
        errors = [{"type": "missing", "loc": ["body", "field"], "msg": "Field required", "input": None}]
        exc = RequestValidationError(errors, body={})
        
        # Mock the logger
        with patch('projects.fundraising_tracking_app.strava_integration.simple_error_handlers.logger') as mock_logger:
            await validation_exception_handler(request, exc)
            
            # Verify that warning was logged
            mock_logger.warning.assert_called_once()
            call_args = mock_logger.warning.call_args
            
            # Check log message contains expected information
            log_message = call_args[0][0]
            assert "Validation Error" in log_message
            assert "422" in log_message
    
    @pytest.mark.asyncio
    async def test_general_exception_logging(self):
        """Test that general exceptions are properly logged."""
        request = Mock(spec=Request)
        request.url.path = "/test/path"
        request.method = "GET"
        
        exc = RuntimeError("Unexpected error")
        
        # Mock the logger
        with patch('projects.fundraising_tracking_app.strava_integration.simple_error_handlers.logger') as mock_logger:
            await general_exception_handler(request, exc)
            
            # Verify that error was logged
            mock_logger.error.assert_called_once()
            call_args = mock_logger.error.call_args
            
            # Check log message contains expected information
            log_message = call_args[0][0]
            assert "Unhandled Exception" in log_message
            assert "RuntimeError" in log_message
            assert "Unexpected error" in log_message
