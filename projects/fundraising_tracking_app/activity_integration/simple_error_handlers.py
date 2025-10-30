"""
Simple error handlers for FastAPI following best practices
Based on research findings from FastAPI documentation and community examples
"""

import uuid
import logging
from datetime import datetime
from typing import Any, Dict
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

logger = logging.getLogger(__name__)

def create_error_response(
    status_code: int,
    message: str,
    details: Dict[str, Any] = None,
    request_id: str = None
) -> Dict[str, Any]:
    """Create a standardized error response"""
    if request_id is None:
        request_id = str(uuid.uuid4())
    
    response = {
        "success": False,
        "error": message,
        "status_code": status_code,
        "timestamp": datetime.now().isoformat(),
        "request_id": request_id
    }
    
    if details:
        response["details"] = details
    
    return response

async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle HTTP exceptions with standardized format"""
    logger.warning(f"HTTP Exception: {exc.status_code} - {exc.detail}")
    
    response_content = create_error_response(
        status_code=exc.status_code,
        message=exc.detail,
        request_id=str(uuid.uuid4())
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=response_content
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle validation errors with detailed information"""
    logger.warning(f"Validation Error: {exc.errors()}")
    
    response_content = create_error_response(
        status_code=422,
        message="Validation error",
        details={
            "validation_errors": exc.errors(),
            "body": exc.body
        },
        request_id=str(uuid.uuid4())
    )
    
    return JSONResponse(
        status_code=422,
        content=response_content
    )

async def api_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle API-specific exceptions"""
    logger.error(f"API Exception: {type(exc).__name__}: {str(exc)}")
    
    response_content = create_error_response(
        status_code=500,
        message="API error",
        details={
            "exception_type": type(exc).__name__,
            "exception_message": str(exc)
        },
        request_id=str(uuid.uuid4())
    )
    
    return JSONResponse(
        status_code=500,
        content=response_content
    )

async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions"""
    logger.error(f"Unexpected error: {type(exc).__name__}: {str(exc)}", exc_info=True)
    
    response_content = create_error_response(
        status_code=500,
        message="Internal server error",
        details={
            "exception_type": type(exc).__name__,
            "exception_message": str(exc)
        },
        request_id=str(uuid.uuid4())
    )
    
    return JSONResponse(
        status_code=500,
        content=response_content
    )
