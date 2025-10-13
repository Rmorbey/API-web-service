# 📚 Multi Project API - Complete Code Explanation

## 🎯 **Overview**

This is the **main API file** that brings everything together. It creates the FastAPI application, registers all routes, applies middleware, and handles the overall API structure. Think of it as the **orchestrator** that coordinates all the different components of your API.

## 📁 **File Structure Context**

```
multi_project_api.py  ← YOU ARE HERE (Main API)
├── strava_integration_api.py  (Strava routes)
├── fundraising_api.py         (Fundraising routes)
├── compression_middleware.py  (Response compression)
├── simple_error_handlers.py   (Error handling)
└── FastAPI                    (Web framework)
```

## 🔍 **Line-by-Line Code Explanation**

### **1. Imports and Setup (Lines 1-20)**

```python
#!/usr/bin/env python3
"""
Multi-Project API
Main FastAPI application that combines all project APIs
"""

import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi

# Import project APIs
from projects.fundraising_tracking_app.strava_integration.strava_integration_api import router as strava_router
from projects.fundraising_tracking_app.fundraising_scraper.fundraising_api import router as fundraising_router

# Import middleware and error handlers
from compression_middleware import SmartCompressionMiddleware
from simple_error_handlers import register_error_handlers

logger = logging.getLogger(__name__)
```

**What this does:**
- **Main application**: Creates the primary FastAPI app
- **Project imports**: Imports all project-specific routers
- **Middleware imports**: Imports compression and error handling
- **CORS support**: Enables cross-origin requests
- **Documentation**: Sets up OpenAPI/Swagger documentation

### **2. Application Lifespan Management (Lines 22-35)**

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events"""
    # Startup
    logger.info("🚀 Starting Multi-Project API...")
    logger.info("📊 Available projects:")
    logger.info("  - Strava Integration API")
    logger.info("  - Fundraising Scraper API")
    logger.info("✅ Multi-Project API started successfully!")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down Multi-Project API...")
    logger.info("✅ Multi-Project API shutdown complete!")
```

**What this does:**
- **Lifespan management**: Handles app startup and shutdown
- **Startup logging**: Records when API starts
- **Project listing**: Shows available projects
- **Shutdown logging**: Records when API stops
- **Resource management**: Ensures proper cleanup

### **3. FastAPI Application Creation (Lines 37-50)**

```python
# Create FastAPI application
app = FastAPI(
    title="Multi-Project API",
    description="API combining multiple projects: Strava Integration and Fundraising Scraper",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)
```

**What this does:**
- **App creation**: Creates the main FastAPI application
- **Metadata**: Sets title, description, and version
- **Documentation URLs**: Configures Swagger and ReDoc
- **OpenAPI spec**: Enables OpenAPI specification
- **Lifespan**: Connects lifespan management

**API Documentation URLs:**
- **`/docs`**: Swagger UI (interactive documentation)
- **`/redoc`**: ReDoc (alternative documentation)
- **`/openapi.json`**: OpenAPI specification (JSON)

### **4. CORS Middleware Configuration (Lines 52-65)**

```python
# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React development server
        "http://localhost:5173",  # Vite development server
        "http://localhost:8000",  # FastAPI development server
        "https://www.russellmorbey.co.uk",  # Production frontend
        "https://russellmorbey.co.uk"       # Production frontend (no www)
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)
```

**What this does:**
- **CORS support**: Enables cross-origin requests
- **Allowed origins**: Specifies which domains can access the API
- **Development support**: Includes localhost URLs for development
- **Production support**: Includes production domain URLs
- **Method support**: Allows all HTTP methods
- **Header support**: Allows all headers

**CORS (Cross-Origin Resource Sharing):**
- **Security feature**: Controls which domains can access your API
- **Browser protection**: Prevents malicious websites from accessing your API
- **Development friendly**: Allows localhost during development
- **Production ready**: Restricts to specific production domains

### **5. Compression Middleware (Lines 67-70)**

```python
# Add compression middleware
app.add_middleware(SmartCompressionMiddleware, 
                   json_min_size=512, 
                   text_min_size=1024, 
                   compression_level=6)
```

**What this does:**
- **Response compression**: Compresses large responses
- **Smart compression**: Different thresholds for different content types
- **JSON optimization**: Lower threshold for JSON (512 bytes)
- **Text optimization**: Higher threshold for text (1024 bytes)
- **Performance**: Reduces bandwidth usage

### **6. Error Handler Registration (Lines 72-75)**

```python
# Register error handlers
register_error_handlers(app)
```

**What this does:**
- **Error handling**: Registers all error handlers
- **Centralized handling**: All errors go through same system
- **Consistent responses**: Standardized error format
- **Logging**: Errors are logged for monitoring

### **7. Route Registration (Lines 77-85)**

```python
# Register project routers
app.include_router(strava_router, prefix="/api/strava-integration", tags=["Strava Integration"])
app.include_router(fundraising_router, prefix="/api/fundraising", tags=["Fundraising"])

# Add health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "message": "Multi-Project API is running"}
```

**What this does:**
- **Router inclusion**: Adds all project routers to main app
- **URL prefixes**: Organizes routes under specific paths
- **Tags**: Groups related endpoints in documentation
- **Health check**: Provides basic health monitoring

**API Structure:**
- **`/api/strava-integration/*`**: Strava-related endpoints
- **`/api/fundraising/*`**: Fundraising-related endpoints
- **`/health`**: Basic health check
- **`/docs`**: API documentation

### **8. Custom OpenAPI Schema (Lines 87-120)**

```python
def custom_openapi():
    """Generate custom OpenAPI schema with project information"""
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="Multi-Project API",
        version="1.0.0",
        description="""
        ## Multi-Project API
        
        This API combines multiple projects into a single service:
        
        ### 🏃‍♂️ Strava Integration
        - **Purpose**: Fetch and process Strava activity data
        - **Features**: Activity caching, rich data collection, map tiles
        - **Endpoints**: `/api/strava-integration/*`
        
        ### 💰 Fundraising Scraper
        - **Purpose**: Scrape and process fundraising data from JustGiving
        - **Features**: Donation tracking, goal monitoring, data caching
        - **Endpoints**: `/api/fundraising/*`
        
        ### 🔧 Technical Features
        - **Response Compression**: Automatic gzip compression for large responses
        - **Error Handling**: Centralized error handling with consistent responses
        - **CORS Support**: Cross-origin request support for web applications
        - **Health Monitoring**: Built-in health check endpoints
        
        ### 🚀 Getting Started
        1. Check the health endpoint: `GET /health`
        2. Explore the API documentation: `GET /docs`
        3. Use the appropriate project endpoints based on your needs
        """,
        routes=app.routes,
    )
    
    # Add custom information
    openapi_schema["info"]["x-logo"] = {
        "url": "https://fastapi.tiangolo.com/img/logo-margin/logo-teal.png"
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

# Set custom OpenAPI schema
app.openapi = custom_openapi
```

**What this does:**
- **Custom documentation**: Creates enhanced OpenAPI schema
- **Project descriptions**: Detailed information about each project
- **Feature overview**: Lists technical features
- **Getting started**: Instructions for API usage
- **Visual enhancement**: Adds logo and styling

### **9. Custom Swagger UI (Lines 122-140)**

```python
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui():
    """Custom Swagger UI with enhanced styling"""
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title="Multi-Project API Documentation",
        swagger_ui_parameters={
            "deepLinking": True,
            "displayRequestDuration": True,
            "filter": True,
            "showExtensions": True,
            "showCommonExtensions": True,
            "tryItOutEnabled": True,
            "requestSnippetsEnabled": True,
            "syntaxHighlight": {
                "activate": True,
                "theme": "agate"
            }
        }
    )
```

**What this does:**
- **Custom Swagger UI**: Enhanced documentation interface
- **Deep linking**: Direct links to specific endpoints
- **Request duration**: Shows response times
- **Filtering**: Search and filter endpoints
- **Syntax highlighting**: Code examples with highlighting
- **Try it out**: Interactive API testing

### **10. Root Endpoint (Lines 142-150)**

```python
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Welcome to the Multi-Project API!",
        "version": "1.0.0",
        "projects": [
            {
                "name": "Strava Integration",
                "description": "Fetch and process Strava activity data",
                "endpoints": "/api/strava-integration/*"
            },
            {
                "name": "Fundraising Scraper",
                "description": "Scrape and process fundraising data",
                "endpoints": "/api/fundraising/*"
            }
        ],
        "documentation": "/docs",
        "health": "/health"
    }
```

**What this does:**
- **Welcome message**: Friendly API introduction
- **Version information**: API version details
- **Project listing**: Available projects and their endpoints
- **Navigation**: Links to documentation and health check
- **User guidance**: Helps users understand the API

## 🎯 **Key Learning Points**

### **1. FastAPI Application Structure**
- **Main app**: Central application that coordinates everything
- **Router inclusion**: Adding project-specific routes
- **Middleware stack**: Order matters for middleware
- **Lifespan management**: Startup and shutdown handling

### **2. Middleware Configuration**
- **CORS**: Cross-origin request support
- **Compression**: Response size optimization
- **Error handling**: Centralized exception management
- **Order matters**: Middleware processes in order

### **3. API Organization**
- **Project separation**: Each project has its own router
- **URL prefixes**: Organized endpoint structure
- **Tags**: Documentation grouping
- **Health monitoring**: Basic health checks

### **4. Documentation Enhancement**
- **Custom OpenAPI**: Enhanced API specification
- **Swagger UI**: Interactive documentation
- **Project descriptions**: Clear project information
- **User guidance**: Getting started instructions

### **5. Production Readiness**
- **CORS configuration**: Production domain support
- **Error handling**: Robust error management
- **Health monitoring**: Basic health checks
- **Documentation**: Comprehensive API docs

## 🚀 **How This Fits Into Your Learning**

This module demonstrates:
- **FastAPI application structure**: Main app coordination
- **Middleware patterns**: Request/response processing
- **Router organization**: Project separation and inclusion
- **Documentation strategies**: Enhanced API documentation
- **Production configuration**: CORS, error handling, monitoring

**Next**: We'll explore the `main.py` to understand the application entry point! 🎉