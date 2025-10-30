#!/usr/bin/env python3
"""
Environment utilities for controlling access based on environment settings.
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

def get_environment() -> str:
    """Get the current environment setting."""
    return os.getenv("ENVIRONMENT", "production").lower()

def is_development() -> bool:
    """Check if the current environment is development."""
    return get_environment() == "development"

def is_production() -> bool:
    """Check if the current environment is production."""
    return get_environment() == "production"

def verify_development_access() -> bool:
    """
    Verify that the current environment allows development-only features.
    Raises HTTPException if not in development mode.
    """
    if not is_development():
        from fastapi import HTTPException
        logger.warning(f"Development endpoint accessed in {get_environment()} environment")
        raise HTTPException(
            status_code=403,
            detail=f"Development endpoints are only available in development environment. Current environment: {get_environment()}"
        )
    return True

def get_environment_info() -> dict:
    """Get environment information for debugging/logging."""
    return {
        "environment": get_environment(),
        "is_development": is_development(),
        "is_production": is_production()
    }
