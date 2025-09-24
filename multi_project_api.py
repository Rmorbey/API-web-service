#!/usr/bin/env python3
"""
Multi-Project API Service
A FastAPI application that can handle multiple different API projects
"""

from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import os
import re
from datetime import datetime
from dotenv import load_dotenv

# Import security middleware
from projects.fundraising_tracking_app.strava_integration.security import SecurityMiddleware

# Import error handling
from projects.fundraising_tracking_app.strava_integration.simple_error_handlers import (
    http_exception_handler,
    validation_exception_handler,
    general_exception_handler
)
from fastapi.exceptions import RequestValidationError

# Load environment variables
load_dotenv()

# Create main FastAPI app
app = FastAPI(
    title="Russell Morbey - Multi-Project API Service",
    description="API service for multiple projects including fundraising tracking and Strava integration",
    version="1.0.0"
)

# Security middleware
app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=["localhost", "127.0.0.1", "*.russellmorbey.co.uk", "russellmorbey.co.uk"]
)

# CORS middleware for React frontend and local HTML files
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", 
        "http://localhost:5173",  # Common React dev ports
        "http://localhost:8000",  # Local development
        "https://www.russellmorbey.co.uk",  # Production domain
        "https://russellmorbey.co.uk"  # Alternative domain
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Input validation is handled by FastAPI's built-in validation

# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    
    # Add security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval' https://widget.deezer.com https://unpkg.com; style-src 'self' 'unsafe-inline' https://unpkg.com; img-src 'self' data: https:; connect-src 'self' https://api.strava.com https://api.deezer.com https://widget.deezer.com; frame-src https://widget.deezer.com;"
    
    return response

# Add security middleware
security_middleware = SecurityMiddleware()
app.middleware("http")(security_middleware)

# Register error handlers
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# Project configuration
PROJECTS = {
    "strava-integration": {
        "name": "Strava Integration Service", 
        "description": "Personal Strava data integration with smart caching",
        "version": "1.0.0",
        "enabled": True
    },
    "fundraising-scraper": {
        "name": "Fundraising Scraper Service",
        "description": "JustGiving fundraising data scraper and API",
        "version": "1.0.0", 
        "enabled": True
    }
}

# Import project modules
try:
    from projects.fundraising_tracking_app.strava_integration.strava_integration_api import router as strava_router
except ImportError:
    # Fallback if modules don't exist
    strava_router = None

try:
    from projects.fundraising_tracking_app.fundraising_scraper.fundraising_api import router as fundraising_router
except ImportError:
    # Fallback if modules don't exist
    fundraising_router = None

# Root endpoint - shows all available projects
@app.get("/")
def root() -> Dict[str, Any]:
    """Get information about all available projects"""
    return {
        "message": "Russell Morbey - Multi-Project API Service",
        "version": "1.0.0",
        "projects": {
            project_id: {
                "name": project["name"],
                "description": project["description"],
                "version": project["version"],
                "enabled": project["enabled"],
                "endpoints": f"/api/{project_id}/"
            }
            for project_id, project in PROJECTS.items()
        },
        "available_endpoints": {
            "health": "/health",
            "projects": "/projects",
            "strava_integration": "/api/strava-integration/"
        }
    }

@app.get("/health")
def health_check() -> Dict[str, Any]:
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "projects_loaded": len([p for p in PROJECTS.values() if p["enabled"]]),
        "total_projects": len(PROJECTS)
    }

@app.get("/projects")
def get_projects() -> Dict[str, Any]:
    """Get detailed information about all projects"""
    return {
        "projects": PROJECTS,
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/demo")
def serve_demo() -> FileResponse:
    """Serve the Strava React demo"""
    return FileResponse("examples/strava-react-demo-clean.html")

@app.get("/fundraising-demo")
def serve_fundraising_demo() -> FileResponse:
    """Serve the fundraising demo"""
    return FileResponse("examples/fundraising-demo.html")

# Include project routers if they exist
if strava_router:
    app.include_router(
        strava_router, 
        prefix="/api/strava-integration", 
        tags=["strava-integration"]
    )

if fundraising_router:
    app.include_router(
        fundraising_router, 
        prefix="/api/fundraising", 
        tags=["fundraising"]
    )

# Direct route for the demo HTML file
@app.get("/examples/strava-react-demo-clean.html")
async def get_demo_html() -> FileResponse:
    """Serve the Strava demo HTML file"""
    return FileResponse("examples/strava-react-demo-clean.html")

# All project routers are now included above

# All endpoints are now handled by the included routers

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
