"""
Error handling utilities and exception classes
"""

import logging
import uuid
from typing import Optional, Dict, Any, List
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from .error_models import (
    ErrorResponse, 
    ErrorCode, 
    ErrorDetail, 
    ValidationErrorResponse,
    RateLimitErrorResponse,
    ExternalServiceErrorResponse
)

logger = logging.getLogger(__name__)


class APIException(Exception):
    """Base exception for API errors"""
    def __init__(
        self, 
        error_code: ErrorCode, 
        message: str, 
        details: Optional[Dict[str, Any]] = None,
        status_code: int = 500
    ):
        self.error_code = error_code
        self.message = message
        self.details = details
        self.status_code = status_code
        super().__init__(message)


class ValidationException(APIException):
    """Exception for validation errors"""
    def __init__(
        self, 
        message: str, 
        errors: Optional[List[ErrorDetail]] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            error_code=ErrorCode.VALIDATION_ERROR,
            message=message,
            details=details,
            status_code=422
        )
        self.errors = errors or []


class AuthenticationException(APIException):
    """Exception for authentication errors"""
    def __init__(self, message: str = "Authentication required"):
        super().__init__(
            error_code=ErrorCode.UNAUTHORIZED,
            message=message,
            status_code=401
        )


class AuthorizationException(APIException):
    """Exception for authorization errors"""
    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(
            error_code=ErrorCode.FORBIDDEN,
            message=message,
            status_code=403
        )


class ResourceNotFoundException(APIException):
    """Exception for resource not found errors"""
    def __init__(self, resource: str, identifier: str):
        super().__init__(
            error_code=ErrorCode.NOT_FOUND,
            message=f"{resource} with identifier '{identifier}' not found",
            details={"resource": resource, "identifier": identifier},
            status_code=404
        )


class RateLimitException(APIException):
    """Exception for rate limiting errors"""
    def __init__(
        self, 
        message: str, 
        retry_after: Optional[int] = None,
        limit: Optional[int] = None,
        remaining: Optional[int] = None
    ):
        super().__init__(
            error_code=ErrorCode.RATE_LIMIT_EXCEEDED,
            message=message,
            details={
                "retry_after": retry_after,
                "limit": limit,
                "remaining": remaining
            },
            status_code=429
        )
        self.retry_after = retry_after
        self.limit = limit
        self.remaining = remaining


class ExternalServiceException(APIException):
    """Exception for external service errors"""
    def __init__(
        self, 
        service: str, 
        message: str, 
        status_code: Optional[int] = None,
        retry_after: Optional[int] = None
    ):
        super().__init__(
            error_code=ErrorCode.EXTERNAL_SERVICE_UNAVAILABLE,
            message=message,
            details={
                "service": service,
                "status_code": status_code,
                "retry_after": retry_after
            },
            status_code=503
        )
        self.service = service
        self.status_code = status_code
        self.retry_after = retry_after


def create_error_response(
    error_code: ErrorCode,
    message: str,
    details: Optional[Dict[str, Any]] = None,
    errors: Optional[List[ErrorDetail]] = None,
    request_id: Optional[str] = None
) -> ErrorResponse:
    """Create a standardized error response"""
    return ErrorResponse(
        error=error_code,
        message=message,
        details=details,
        errors=errors,
        request_id=request_id or str(uuid.uuid4())
    )


def create_validation_error_response(
    message: str,
    errors: List[ErrorDetail],
    request_id: Optional[str] = None
) -> ValidationErrorResponse:
    """Create a validation error response"""
    return ValidationErrorResponse(
        message=message,
        errors=errors,
        request_id=request_id or str(uuid.uuid4())
    )


def create_rate_limit_error_response(
    message: str,
    retry_after: Optional[int] = None,
    limit: Optional[int] = None,
    remaining: Optional[int] = None,
    request_id: Optional[str] = None
) -> RateLimitErrorResponse:
    """Create a rate limit error response"""
    return RateLimitErrorResponse(
        message=message,
        retry_after=retry_after,
        limit=limit,
        remaining=remaining,
        request_id=request_id or str(uuid.uuid4())
    )


def create_external_service_error_response(
    service: str,
    message: str,
    status_code: Optional[int] = None,
    retry_after: Optional[int] = None,
    request_id: Optional[str] = None
) -> ExternalServiceErrorResponse:
    """Create an external service error response"""
    return ExternalServiceErrorResponse(
        service=service,
        message=message,
        status_code=status_code,
        retry_after=retry_after,
        request_id=request_id or str(uuid.uuid4())
    )


async def api_exception_handler(request: Request, exc: APIException) -> JSONResponse:
    """Handle custom API exceptions"""
    logger.error(f"API Exception: {exc.error_code} - {exc.message}", extra={
        "error_code": exc.error_code,
        "message": exc.message,
        "details": exc.details,
        "path": request.url.path,
        "method": request.method
    })
    
    error_response = create_error_response(
        error_code=exc.error_code,
        message=exc.message,
        details=exc.details,
        request_id=str(uuid.uuid4())
    )
    
    # Create a simple dict to avoid JSON serialization issues
    response_content = {
        "success": False,
        "error": exc.error_code.value,
        "message": exc.message,
        "timestamp": datetime.now().isoformat(),
        "request_id": exc.request_id
    }
    
    if exc.details:
        response_content["details"] = exc.details
    
    return JSONResponse(
        status_code=exc.status_code,
        content=response_content
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle FastAPI validation exceptions"""
    logger.warning(f"Validation Error: {exc.errors()}", extra={
        "path": request.url.path,
        "method": request.method
    })
    
    # Convert FastAPI validation errors to our format
    error_details = []
    for error in exc.errors():
        error_details.append(ErrorDetail(
            field=".".join(str(loc) for loc in error["loc"]),
            message=error["msg"],
            value=error.get("input")
        ))
    
    error_response = create_validation_error_response(
        message="Request validation failed",
        errors=error_details,
        request_id=str(uuid.uuid4())
    )
    
    return JSONResponse(
        status_code=422,
        content=error_response.dict()
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle FastAPI HTTP exceptions"""
    logger.warning(f"HTTP Exception: {exc.status_code} - {exc.detail}", extra={
        "status_code": exc.status_code,
        "detail": exc.detail,
        "path": request.url.path,
        "method": request.method
    })
    
    # Map common HTTP status codes to our error codes
    error_code_mapping = {
        400: ErrorCode.INVALID_INPUT,
        401: ErrorCode.UNAUTHORIZED,
        403: ErrorCode.FORBIDDEN,
        404: ErrorCode.NOT_FOUND,
        409: ErrorCode.RESOURCE_CONFLICT,
        422: ErrorCode.VALIDATION_ERROR,
        429: ErrorCode.RATE_LIMIT_EXCEEDED,
        500: ErrorCode.INTERNAL_SERVER_ERROR,
        502: ErrorCode.EXTERNAL_SERVICE_UNAVAILABLE,
        503: ErrorCode.EXTERNAL_SERVICE_UNAVAILABLE,
        504: ErrorCode.EXTERNAL_SERVICE_UNAVAILABLE,
    }
    
    error_code = error_code_mapping.get(exc.status_code, ErrorCode.INTERNAL_SERVER_ERROR)
    
    error_response = create_error_response(
        error_code=error_code,
        message=str(exc.detail),
        request_id=str(uuid.uuid4())
    )
    
    # Create a simple dict to avoid JSON serialization issues
    response_content = {
        "success": False,
        "error": exc.error_code.value,
        "message": exc.message,
        "timestamp": datetime.now().isoformat(),
        "request_id": exc.request_id
    }
    
    if exc.details:
        response_content["details"] = exc.details
    
    return JSONResponse(
        status_code=exc.status_code,
        content=response_content
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions"""
    logger.error(f"Unexpected Exception: {type(exc).__name__} - {str(exc)}", extra={
        "exception_type": type(exc).__name__,
        "exception_message": str(exc),
        "path": request.url.path,
        "method": request.method
    }, exc_info=True)
    
    # Create a simple dict to avoid JSON serialization issues
    response_content = {
        "success": False,
        "error": "INTERNAL_SERVER_ERROR",
        "message": "An unexpected error occurred",
        "timestamp": datetime.now().isoformat(),
        "request_id": str(uuid.uuid4())
    }
    
    if exc:
        response_content["details"] = {
            "exception_type": type(exc).__name__,
            "exception_message": str(exc)
        }
    
    return JSONResponse(
        status_code=500,
        content=response_content
    )
