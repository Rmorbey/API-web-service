"""
Standardized error response models for consistent API error handling
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum


class ErrorCode(str, Enum):
    """Standardized error codes for consistent error handling"""
    # Authentication & Authorization
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    INVALID_API_KEY = "INVALID_API_KEY"
    
    # Validation Errors
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_INPUT = "INVALID_INPUT"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    
    # Resource Errors
    NOT_FOUND = "NOT_FOUND"
    RESOURCE_CONFLICT = "RESOURCE_CONFLICT"
    
    # External Service Errors
    STRAVA_API_ERROR = "STRAVA_API_ERROR"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    EXTERNAL_SERVICE_UNAVAILABLE = "EXTERNAL_SERVICE_UNAVAILABLE"
    
    # Internal Errors
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    CACHE_ERROR = "CACHE_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"
    
    # Business Logic Errors
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    OPERATION_FAILED = "OPERATION_FAILED"


class ErrorDetail(BaseModel):
    """Detailed error information"""
    field: Optional[str] = Field(None, description="Field that caused the error")
    message: str = Field(..., description="Specific error message")
    value: Optional[Any] = Field(None, description="Value that caused the error")


class ErrorResponse(BaseModel):
    """Standardized error response format"""
    success: bool = Field(False, description="Always false for error responses")
    error: ErrorCode = Field(..., description="Standardized error code")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    errors: Optional[list[ErrorDetail]] = Field(None, description="Field-specific validation errors")
    timestamp: datetime = Field(default_factory=datetime.now, description="Error timestamp")
    request_id: Optional[str] = Field(None, description="Unique request identifier for debugging")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        json_serialize_default_exclude_none = True


class ValidationErrorResponse(ErrorResponse):
    """Specialized error response for validation errors"""
    error: ErrorCode = Field(ErrorCode.VALIDATION_ERROR, description="Validation error code")
    errors: list[ErrorDetail] = Field(..., description="List of validation errors")


class RateLimitErrorResponse(ErrorResponse):
    """Specialized error response for rate limiting"""
    error: ErrorCode = Field(ErrorCode.RATE_LIMIT_EXCEEDED, description="Rate limit error code")
    retry_after: Optional[int] = Field(None, description="Seconds to wait before retrying")
    limit: Optional[int] = Field(None, description="Rate limit threshold")
    remaining: Optional[int] = Field(None, description="Remaining requests in current window")


class ExternalServiceErrorResponse(ErrorResponse):
    """Specialized error response for external service failures"""
    service: str = Field(..., description="Name of the external service that failed")
    status_code: Optional[int] = Field(None, description="HTTP status code from external service")
    retry_after: Optional[int] = Field(None, description="Seconds to wait before retrying")
