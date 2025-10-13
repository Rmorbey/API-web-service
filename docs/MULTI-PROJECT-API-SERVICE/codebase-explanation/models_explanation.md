# 📚 Models - Complete Code Explanation

## 🎯 **Overview**

This file defines **Pydantic models** for data validation and serialization. These models ensure that data is properly structured, validated, and documented. Think of them as **blueprints** that define what data should look like and how it should behave.

## 📁 **File Structure Context**

```
models.py  ← YOU ARE HERE (Data Structures)
├── strava_integration_api.py  (Uses these models)
├── smart_strava_cache.py      (Uses these models)
└── FastAPI                    (Uses these for validation)
```

## 🔍 **Line-by-Line Code Explanation**

### **1. Imports and Setup (Lines 1-10)**

```python
#!/usr/bin/env python3
"""
Pydantic models for Strava Integration API
Defines request and response models for type safety and validation
"""

from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime
```

**What this does:**
- **`BaseModel`**: Base class for all Pydantic models
- **`Field`**: For defining field properties and validation
- **`field_validator`**: For custom validation logic
- **`ConfigDict`**: For model configuration
- **`typing`**: For type hints
- **`datetime`**: For date/time handling

### **2. Activity Photo Models (Lines 12-22)**

```python
class ActivityPhoto(BaseModel):
    """Activity photo data"""
    url: str = Field(..., description="Photo URL")
    caption: Optional[str] = Field(None, description="Photo caption")


class ActivityPhotos(BaseModel):
    """Activity photos container"""
    primary: Optional[ActivityPhoto] = Field(None, description="Primary photo")
    count: int = Field(default=0, description="Total photo count")
```

**What this does:**
- **`ActivityPhoto`**: Represents a single photo
  - **`url`**: Required string field for photo URL
  - **`caption`**: Optional string field for photo caption
- **`ActivityPhotos`**: Container for multiple photos
  - **`primary`**: Optional primary photo
  - **`count`**: Total number of photos (defaults to 0)

**Field Properties:**
- **`...`**: Required field (cannot be None)
- **`None`**: Optional field (can be None)
- **`default=0`**: Default value if not provided
- **`description`**: Documentation for the field

### **3. Activity Comment Model (Lines 24-30)**

```python
class ActivityComment(BaseModel):
    """Activity comment data"""
    id: int = Field(..., description="Comment ID")
    text: str = Field(..., description="Comment text")
    created_at: str = Field(..., description="Comment creation date")
    athlete: Dict[str, Any] = Field(..., description="Commenter information")
```

**What this does:**
- **`id`**: Unique comment identifier
- **`text`**: Comment content
- **`created_at`**: When comment was created
- **`athlete`**: Information about who made the comment

### **4. Main Activity Model (Lines 32-53)**

```python
class Activity(BaseModel):
    """Strava activity data"""
    id: int = Field(..., description="Activity ID")
    name: str = Field(..., description="Activity name")
    type: str = Field(..., description="Activity type")
    distance: float = Field(..., description="Distance in meters")
    moving_time: int = Field(..., description="Moving time in seconds")
    elapsed_time: int = Field(..., description="Total elapsed time in seconds")
    start_date: str = Field(..., description="Activity start date")
    start_date_local: str = Field(..., description="Local start date")
    timezone: str = Field(..., description="Activity timezone")
    total_elevation_gain: float = Field(..., description="Total elevation gain in meters")
    description: Optional[str] = Field(None, description="Activity description")
    photos: Optional[ActivityPhotos] = Field(None, description="Activity photos")
    comments: Optional[List[ActivityComment]] = Field(None, description="Activity comments")
    polyline: Optional[str] = Field(None, description="GPS polyline data")
    bounds: Optional[List[float]] = Field(None, description="Activity bounds")
    has_media: bool = Field(default=False, description="Whether activity has media")
    media_type: str = Field(default="none", description="Type of media (photo/video/none)")
    photo_url: Optional[str] = Field(None, description="Primary photo URL")
    formatted_duration: str = Field(..., description="Formatted duration (HH:MM:SS)")
```

**What this does:**
- **Core activity data**: ID, name, type, distance, time
- **Date/time fields**: Start dates and timezone
- **Optional rich data**: Description, photos, comments
- **Map data**: Polyline and bounds for GPS routes
- **Media fields**: Photo and video information
- **Formatted fields**: Human-readable duration

**Field Types:**
- **`int`**: Integer numbers
- **`str`**: Text strings
- **`float`**: Decimal numbers
- **`bool`**: True/false values
- **`Optional[...]`**: Can be None
- **`List[...]`**: List of items

### **5. Response Models (Lines 55-113)**

```python
class ActivityFeedResponse(BaseModel):
    """Response model for activity feed endpoint"""
    activities: List[Activity] = Field(..., description="List of activities")
    total: int = Field(..., description="Total number of activities")
    timestamp: datetime = Field(..., description="Response timestamp")


class HealthResponse(BaseModel):
    """Response model for health check endpoint"""
    project: str = Field(..., description="Project name")
    status: str = Field(..., description="Health status")
    timestamp: datetime = Field(..., description="Health check timestamp")
    strava_configured: bool = Field(..., description="Whether Strava is configured")
    jawg_configured: bool = Field(..., description="Whether Jawg Maps is configured")
    cache_status: str = Field(..., description="Cache status")


class MetricsResponse(BaseModel):
    """Response model for metrics endpoint"""
    project: str = Field(..., description="Project name")
    cache_hits: int = Field(..., description="Number of cache hits")
    cache_misses: int = Field(..., description="Number of cache misses")
    api_calls_made: int = Field(..., description="Number of API calls made")
    last_refresh: Optional[datetime] = Field(None, description="Last refresh timestamp")
    activities_cached: int = Field(..., description="Number of activities in cache")
    cache_size_mb: float = Field(..., description="Cache size in MB")
```

**What this does:**
- **`ActivityFeedResponse`**: Response for activity feed endpoint
- **`HealthResponse`**: Response for health check endpoint
- **`MetricsResponse`**: Response for metrics endpoint
- **Consistent structure**: All responses have timestamp and relevant data

### **6. Request Models (Lines 120-253)**

```python
class FeedRequest(BaseModel):
    """Request model for activity feed endpoint with filtering options"""
    limit: int = Field(
        default=20, 
        ge=1, 
        le=200, 
        description="Number of activities to return",
    )
    activity_type: Optional[Literal["Run", "Ride"]] = Field(
        default=None, 
        description="Filter by activity type (Run or Ride)",
    )
    date_from: Optional[datetime] = Field(
        default=None, 
        description="Filter activities from this date onwards (ISO format)",
    )
    date_to: Optional[datetime] = Field(
        default=None, 
        description="Filter activities up to this date (ISO format)",
    )
    has_photos: Optional[bool] = Field(
        default=None, 
        description="Filter activities that have photos (true) or don't have photos (false)",
    )
    has_description: Optional[bool] = Field(
        default=None, 
        description="Filter activities that have descriptions (true) or don't have descriptions (false)",
    )
    min_distance: Optional[float] = Field(
        default=None, 
        ge=0, 
        description="Minimum distance in meters",
    )
    max_distance: Optional[float] = Field(
        default=None, 
        ge=0, 
        description="Maximum distance in meters",
    )
```

**What this does:**
- **`limit`**: Number of activities to return (1-200)
- **`activity_type`**: Filter by Run or Ride only
- **`date_from/date_to`**: Date range filtering
- **`has_photos/description`**: Boolean filtering
- **`min/max_distance`**: Distance range filtering

**Field Validation:**
- **`ge=1`**: Greater than or equal to 1
- **`le=200`**: Less than or equal to 200
- **`Literal["Run", "Ride"]`**: Only allows these specific values

### **7. Custom Validators (Lines 159-175)**

```python
@field_validator('date_to')
@classmethod
def validate_date_range(cls, v, info):
    """Validate that date_to is after date_from"""
    if v and hasattr(info, 'data') and 'date_from' in info.data and info.data['date_from']:
        if v <= info.data['date_from']:
            raise ValueError('date_to must be after date_from')
    return v

@field_validator('max_distance')
@classmethod
def validate_distance_range(cls, v, info):
    """Validate that max_distance is greater than min_distance"""
    if v and hasattr(info, 'data') and 'min_distance' in info.data and info.data['min_distance']:
        if v <= info.data['min_distance']:
            raise ValueError('max_distance must be greater than min_distance')
    return v
```

**What this does:**
- **Custom validation**: Additional validation beyond basic field validation
- **`@field_validator`**: Decorator for custom validation
- **`@classmethod`**: Method that can access class data
- **Cross-field validation**: Validates relationships between fields
- **Error raising**: Raises `ValueError` with clear message

### **8. Model Configuration (Lines 177-190)**

```python
model_config = ConfigDict(
    json_schema_extra={
        "example": {
            "limit": 20,
            "activity_type": "Run",
            "date_from": "2025-05-22T00:00:00",
            "date_to": "2025-09-24T23:59:59",
            "has_photos": True,
            "has_description": True,
            "min_distance": 1000.0,
            "max_distance": 10000.0
        }
    }
)
```

**What this does:**
- **`ConfigDict`**: Pydantic V2 configuration
- **`json_schema_extra`**: Additional information for OpenAPI schema
- **`example`**: Example data for API documentation
- **API documentation**: Shows users how to use the endpoint

### **9. Additional Request Models (Lines 193-253)**

```python
class RefreshRequest(BaseModel):
    """Request model for manual refresh endpoint"""
    force_full_refresh: bool = Field(
        default=False, 
        description="Force a full refresh instead of smart merge",
    )
    include_old_activities: bool = Field(
        default=False, 
        description="Include activities older than 3 weeks in refresh",
    )
    batch_size: int = Field(
        default=20, 
        ge=1, 
        le=50, 
        description="Number of activities to process in each batch",
    )


class CleanupRequest(BaseModel):
    """Request model for cleanup endpoints"""
    keep_backups: int = Field(
        default=1, 
        ge=0, 
        le=10, 
        description="Number of recent backups to keep",
    )
    force_cleanup: bool = Field(
        default=False, 
        description="Force cleanup even if cache is recent",
    )


class MapTilesRequest(BaseModel):
    """Request model for map tiles endpoint"""
    z: int = Field(..., ge=0, le=18, description="Zoom level")
    x: int = Field(..., ge=0, description="Tile X coordinate")
    y: int = Field(..., ge=0, description="Tile Y coordinate")
    style: Optional[Literal["streets", "terrain", "satellite", "dark"]] = Field(
        default="streets", 
        description="Map style"
    )
```

**What this does:**
- **`RefreshRequest`**: For manual cache refresh
- **`CleanupRequest`**: For cache cleanup operations
- **`MapTilesRequest`**: For map tile requests
- **Different validation rules**: Each model has appropriate constraints

## 🎯 **Key Learning Points**

### **1. Pydantic Models**
- **Data validation**: Automatic validation of input data
- **Type safety**: Ensures data types are correct
- **Documentation**: Self-documenting with field descriptions
- **Serialization**: Automatic JSON conversion

### **2. Field Validation**
- **Basic validation**: `ge`, `le`, `default` values
- **Custom validation**: `@field_validator` decorator
- **Cross-field validation**: Validates relationships between fields
- **Error handling**: Clear error messages for validation failures

### **3. Type Hints**
- **`Optional[...]`**: Fields that can be None
- **`List[...]`**: Lists of specific types
- **`Literal[...]`**: Only specific values allowed
- **`Dict[str, Any]`**: Dictionary with string keys

### **4. API Documentation**
- **Field descriptions**: Help users understand each field
- **Examples**: Show users how to use the API
- **OpenAPI integration**: Automatic API documentation generation

### **5. Model Organization**
- **Response models**: Define what the API returns
- **Request models**: Define what the API accepts
- **Nested models**: Complex data structures
- **Reusable models**: Models that can be used in multiple places

## 🚀 **How This Fits Into Your Learning**

This file demonstrates:
- **Pydantic V2**: Modern data validation library
- **Type safety**: Ensuring data integrity
- **API design**: Well-structured request/response models
- **Validation patterns**: Different types of validation
- **Documentation**: Self-documenting code

**Next**: We'll explore the `security.py` to understand authentication and security! 🎉
