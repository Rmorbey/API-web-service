#!/usr/bin/env python3
"""
Multi-Project API Service
A FastAPI application that can handle multiple different API projects
"""

from fastapi import FastAPI, APIRouter, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create main FastAPI app
app = FastAPI(
    title="Russell Morbey - Multi-Project API Service",
    description="API service for multiple projects including fundraising tracking and Strava integration",
    version="1.0.0"
)

# CORS middleware for React frontend and local HTML files
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*",  # Allow all origins for development
        "http://localhost:3000", 
        "http://localhost:5173",  # Common React dev ports
        "https://www.russellmorbey.co.uk",  # Production domain
        "https://russellmorbey.co.uk"  # Alternative domain
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Project configuration
PROJECTS = {
    "strava-integration": {
        "name": "Strava Integration Service", 
        "description": "Personal Strava data integration with smart caching",
        "version": "1.0.0",
        "enabled": True
    },
    "web-scraping": {
        "name": "Web Scraping Service",
        "description": "Web scraping utilities for data collection",
        "version": "1.0.0", 
        "enabled": False  # Not implemented yet
    }
}

# Import project modules
try:
    from projects.fundraising_tracking_app.strava_integration.strava_integration_api import router as strava_router
except ImportError:
    # Fallback if modules don't exist
    strava_router = None

# Root endpoint - shows all available projects
@app.get("/")
def root():
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
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "projects_loaded": len([p for p in PROJECTS.values() if p["enabled"]]),
        "total_projects": len(PROJECTS)
    }

@app.get("/projects")
def get_projects():
    """Get detailed information about all projects"""
    return {
        "projects": PROJECTS,
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/demo")
def serve_demo():
    """Serve the Strava React demo"""
    return FileResponse("examples/strava-react-demo-clean.html")

# Include project routers if they exist
if strava_router:
    app.include_router(
        strava_router, 
        prefix="/api/strava-integration", 
        tags=["strava-integration"]
    )

# All project routers are now included above

# All endpoints are now handled by the included routers

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
