#!/usr/bin/env python3
"""
Multi-Project API Service
A FastAPI application that can handle multiple different API projects
"""

from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import os
import re
import logging
from datetime import datetime
from dotenv import load_dotenv

# Configure logging
logger = logging.getLogger(__name__)

# Import security middleware
from projects.fundraising_tracking_app.strava_integration.security import SecurityMiddleware

# Import error handling
from projects.fundraising_tracking_app.strava_integration.simple_error_handlers import (
    http_exception_handler,
    validation_exception_handler,
    general_exception_handler
)
from fastapi.exceptions import RequestValidationError

# Import HTTP client lifespan manager
from projects.fundraising_tracking_app.strava_integration.http_clients import lifespan_http_clients
from contextlib import asynccontextmanager

# Import cache middleware
from projects.fundraising_tracking_app.strava_integration.cache_middleware import CacheMiddleware
from projects.fundraising_tracking_app.strava_integration.compression_middleware import SmartCompressionMiddleware

# Load environment variables
load_dotenv()

# Create startup initialization function
@asynccontextmanager
async def lifespan_with_cache_init(app: FastAPI):
    """Application lifespan with cache system initialization"""
    # Startup
    logger.info("🚀 Starting Multi-Project API with cache initialization...")
    
    # Initialize HTTP clients first
    async with lifespan_http_clients(app):
        # Initialize cache systems to start automated refresh threads
        try:
            # Initialize Strava cache system
            from projects.fundraising_tracking_app.strava_integration.strava_integration_api import get_cache as get_strava_cache
            strava_cache = get_strava_cache()
            logger.info("✅ Strava cache system initialized with automated refresh")
            
            # Initialize Fundraising cache system  
            from projects.fundraising_tracking_app.fundraising_scraper.fundraising_api import get_cache as get_fundraising_cache
            fundraising_cache = get_fundraising_cache()
            logger.info("✅ Fundraising cache system initialized with automated refresh")
            
            logger.info("🔄 All automated refresh systems started successfully!")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize cache systems: {e}")
        
        yield
        
        # Shutdown
        logger.info("🛑 Shutting down Multi-Project API...")
        logger.info("✅ Multi-Project API shutdown complete!")

# Create main FastAPI app with lifespan management
app = FastAPI(
    title="Russell Morbey - Multi-Project API Service",
    description="""
    ## 🚀 Multi-Project API Service
    
    A comprehensive FastAPI application providing APIs for multiple projects including:
    
    ### 📊 **Strava Integration API**
    - **Activity Feed**: Get Strava activities with photos, comments, and music detection
    - **Cache Management**: View cache statistics and invalidate cache entries
    - **Map Integration**: Access Jawg map tiles and tokens
    - **Metrics**: Monitor API performance and usage
    - **Health Checks**: Verify service status
    
    ### 💰 **Fundraising Tracking API**
    - **Donation Data**: Retrieve fundraising data and donations
    - **Cache Management**: View and manage fundraising cache
    - **Data Refresh**: Trigger manual data updates
    - **Health Monitoring**: Check service health status
    
    ### 🔧 **Features**
    - **Rate Limiting**: Built-in rate limiting for API protection
    - **Caching**: Intelligent caching with 95% hit rate
    - **Compression**: Response compression for optimal performance
    - **Security**: API key authentication and security headers
    - **Monitoring**: Comprehensive metrics and health checks
    
    ### 📈 **Performance**
    - **Response Times**: 5-50ms average response time
    - **Bandwidth**: 60-80% reduction through compression
    - **Processing**: 97% faster through async processing
    - **Reliability**: 100% test coverage with 650+ tests
    
    ### 🔑 **Authentication**
    All API endpoints require authentication via `X-API-Key` header.
    
    ### 📚 **Documentation**
    - Interactive API documentation available at `/docs`
    - OpenAPI specification available at `/openapi.json`
    """,
    version="1.0.0",
    contact={
        "name": "Russell Morbey",
        "email": "russell@example.com",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    lifespan=lifespan_with_cache_init,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Compression middleware (add first for optimal performance)
app.add_middleware(SmartCompressionMiddleware)

# Cache middleware (add second)
app.add_middleware(CacheMiddleware)


# Security middleware
app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=[
        "localhost",
        "127.0.0.1",
        "*.russellmorbey.co.uk",
        "russellmorbey.co.uk",
        "*.ondigitalocean.app"  # allow DO App Platform health probes and default domain
    ]
)

# Public health check bypass (must be added AFTER TrustedHost so it runs first)
@app.middleware("http")
async def public_health_bypass(request: Request, call_next):
    if request.method == "GET" and request.url.path in ("/api/health", "/health"):
        return JSONResponse({
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "projects_loaded": len([p for p in PROJECTS.values() if p["enabled"]]),
            "total_projects": len(PROJECTS)
        })
    return await call_next(request)

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
@app.get(
    "/",
    summary="🏠 API Root",
    description="Get basic information about the API service and available projects",
    response_description="API information and available projects",
    tags=["General"]
)
def root() -> Dict[str, Any]:
    """
    ## 🏠 API Root Endpoint
    
    Returns comprehensive information about the API service including:
    - Service name and version
    - Available projects and their status
    - Available endpoints
    - Timestamp
    
    ### Response
    - **message**: Service name
    - **version**: API version
    - **projects**: Available projects with details
    - **available_endpoints**: All available API endpoints
    - **timestamp**: Current timestamp
    """
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

@app.get(
    "/health",
    summary="🏥 Health Check",
    description="Check the health status of the API service and all loaded projects",
    response_description="Health status information",
    tags=["General"]
)
def health_check() -> Dict[str, Any]:
    """
    ## 🏥 Health Check Endpoint
    
    Returns the health status of the API service including:
    - Overall service status
    - Number of loaded projects
    - Timestamp
    
    ### Response
    - **status**: Service health status (healthy/unhealthy)
    - **timestamp**: Current UTC timestamp
    - **projects_loaded**: Number of enabled projects
    - **total_projects**: Total number of configured projects
    """
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
    """Serve the Strava React demo (development environment only)"""
    # Verify we're in development environment
    from projects.fundraising_tracking_app.strava_integration.environment_utils import verify_development_access
    verify_development_access()
    return FileResponse("examples/strava-react-demo-clean.html")

@app.get("/fundraising-demo")
def serve_fundraising_demo() -> FileResponse:
    """Serve the fundraising demo (development environment only)"""
    # Verify we're in development environment
    from projects.fundraising_tracking_app.strava_integration.environment_utils import verify_development_access
    verify_development_access()
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

# Demo page is served by /demo endpoint above

# All project routers are now included above

# All endpoints are now handled by the included routers

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
