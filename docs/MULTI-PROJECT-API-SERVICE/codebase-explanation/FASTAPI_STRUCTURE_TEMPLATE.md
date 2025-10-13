# 🚀 FastAPI Structure Template - Best Practices Guide

## 🎯 **Overview**

This document provides a comprehensive template for structuring FastAPI applications following industry best practices. Based on analysis of your current API structure and 2024 FastAPI best practices, this template will help you create maintainable, scalable, and production-ready APIs.

## 📁 **Recommended Project Structure**

```
my_fastapi_project/
├── app/
│   ├── __init__.py
│   ├── main.py                     # Main FastAPI application
│   ├── api/
│   │   ├── __init__.py
│   │   ├── v1/                     # API versioning
│   │   │   ├── __init__.py
│   │   │   ├── endpoints/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── auth.py         # Authentication endpoints
│   │   │   │   ├── users.py        # User management
│   │   │   │   ├── items.py        # Resource endpoints
│   │   │   │   └── health.py       # Health checks
│   │   │   ├── dependencies.py     # Shared dependencies
│   │   │   └── router.py           # Main router
│   │   └── middleware/
│   │       ├── __init__.py
│   │       ├── auth.py             # Authentication middleware
│   │       ├── rate_limit.py       # Rate limiting
│   │       ├── cors.py             # CORS configuration
│   │       └── security.py         # Security headers
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py               # Configuration management
│   │   ├── security.py             # Security utilities
│   │   ├── database.py             # Database configuration
│   │   └── logging.py              # Logging configuration
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py                 # Base model class
│   │   ├── user.py                 # User model
│   │   └── item.py                 # Item model
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── base.py                 # Base schema classes
│   │   ├── user.py                 # User schemas
│   │   ├── item.py                 # Item schemas
│   │   └── common.py               # Common schemas
│   ├── services/
│   │   ├── __init__.py
│   │   ├── auth_service.py         # Authentication logic
│   │   ├── user_service.py         # User business logic
│   │   └── item_service.py         # Item business logic
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── helpers.py              # Helper functions
│   │   ├── validators.py           # Custom validators
│   │   └── decorators.py           # Custom decorators
│   └── tests/
│       ├── __init__.py
│       ├── conftest.py             # Test configuration
│       ├── test_auth.py
│       ├── test_users.py
│       └── test_items.py
├── migrations/                     # Database migrations
├── static/                        # Static files
├── templates/                     # HTML templates
├── .env                          # Environment variables
├── .env.example                  # Environment template
├── .gitignore
├── requirements.txt
├── requirements-dev.txt           # Development dependencies
├── pyproject.toml                # Project configuration
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## 🔧 **Core Components**

### **1. Main Application (`app/main.py`)**

```python
#!/usr/bin/env python3
"""
Main FastAPI Application
Production-ready FastAPI application with comprehensive middleware and security
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import time
from typing import Dict, Any

from app.core.config import settings
from app.core.logging import setup_logging
from app.api.v1.router import api_router
from app.api.middleware.auth import AuthMiddleware
from app.api.middleware.rate_limit import RateLimitMiddleware
from app.api.middleware.security import SecurityMiddleware

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    logger.info("Starting up FastAPI application...")
    yield
    # Shutdown
    logger.info("Shutting down FastAPI application...")

# Create FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.PROJECT_DESCRIPTION,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    contact={
        "name": settings.CONTACT_NAME,
        "email": settings.CONTACT_EMAIL,
    },
    license_info={
        "name": settings.LICENSE_NAME,
        "url": settings.LICENSE_URL,
    },
)

# Add middleware (order matters!)
app.add_middleware(SecurityMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(AuthMiddleware)
app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=settings.ALLOWED_HOSTS
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)

# Root endpoint
@app.get("/", tags=["General"])
def root() -> Dict[str, Any]:
    """Root endpoint with API information"""
    return {
        "message": f"Welcome to {settings.PROJECT_NAME}",
        "version": settings.VERSION,
        "docs": "/docs",
        "health": "/health"
    }

# Health check endpoint
@app.get("/health", tags=["General"])
def health_check() -> Dict[str, Any]:
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "version": settings.VERSION
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
```

### **2. Configuration Management (`app/core/config.py`)**

```python
"""
Configuration Management
Centralized configuration using Pydantic Settings
"""

from pydantic import BaseSettings, validator
from typing import List, Optional
import os
from pathlib import Path

class Settings(BaseSettings):
    """Application settings"""
    
    # Project Information
    PROJECT_NAME: str = "My FastAPI Project"
    PROJECT_DESCRIPTION: str = "A production-ready FastAPI application"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Contact Information
    CONTACT_NAME: str = "Your Name"
    CONTACT_EMAIL: str = "your.email@example.com"
    LICENSE_NAME: str = "MIT"
    LICENSE_URL: str = "https://opensource.org/licenses/MIT"
    
    # Security
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ALGORITHM: str = "HS256"
    
    # Database
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 5
    DATABASE_MAX_OVERFLOW: int = 10
    
    # CORS
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "https://yourdomain.com"
    ]
    ALLOWED_HOSTS: List[str] = [
        "localhost",
        "127.0.0.1",
        "yourdomain.com"
    ]
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60  # seconds
    
    # Caching
    REDIS_URL: Optional[str] = None
    CACHE_TTL: int = 300  # 5 minutes
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Development
    DEBUG: bool = False
    TESTING: bool = False
    
    @validator("SECRET_KEY", pre=True)
    def validate_secret_key(cls, v):
        if not v or len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters")
        return v
    
    @validator("DATABASE_URL", pre=True)
    def validate_database_url(cls, v):
        if not v:
            raise ValueError("DATABASE_URL is required")
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Create settings instance
settings = Settings()
```

### **3. Security Utilities (`app/core/security.py`)**

```python
"""
Security Utilities
Authentication, authorization, and security helpers
"""

from datetime import datetime, timedelta
from typing import Optional, Union
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from app.core.config import settings

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT token scheme
security = HTTPBearer()

class TokenData(BaseModel):
    """Token data model"""
    username: Optional[str] = None
    scopes: list[str] = []

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)

def create_access_token(
    data: dict, 
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> TokenData:
    """Verify and decode a JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    
    return token_data

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> TokenData:
    """Get current authenticated user"""
    token = credentials.credentials
    return verify_token(token)

# API Key authentication (for service-to-service)
def verify_api_key(api_key: str) -> bool:
    """Verify API key for service authentication"""
    return api_key == settings.SECRET_KEY  # In production, use a proper API key system
```

### **4. Database Models (`app/models/base.py`)**

```python
"""
Base Database Model
SQLAlchemy base model with common functionality
"""

from sqlalchemy import Column, Integer, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()

class BaseModel(Base):
    """Base model with common fields"""
    __abstract__ = True
    
    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_active = Column(Boolean, default=True)
    
    def to_dict(self):
        """Convert model to dictionary"""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }
```

### **5. Pydantic Schemas (`app/schemas/base.py`)**

```python
"""
Base Pydantic Schemas
Common schema patterns and base classes
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class BaseSchema(BaseModel):
    """Base schema with common configuration"""
    class Config:
        from_attributes = True
        validate_assignment = True
        use_enum_values = True

class TimestampMixin(BaseSchema):
    """Mixin for timestamp fields"""
    created_at: datetime
    updated_at: Optional[datetime] = None

class IDMixin(BaseSchema):
    """Mixin for ID field"""
    id: int = Field(..., description="Unique identifier")

class PaginationParams(BaseSchema):
    """Pagination parameters"""
    page: int = Field(1, ge=1, description="Page number")
    size: int = Field(10, ge=1, le=100, description="Page size")
    
    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size

class PaginatedResponse(BaseSchema):
    """Paginated response wrapper"""
    items: list
    total: int
    page: int
    size: int
    pages: int
    
    @classmethod
    def create(cls, items: list, total: int, page: int, size: int):
        return cls(
            items=items,
            total=total,
            page=page,
            size=size,
            pages=(total + size - 1) // size
        )
```

### **6. API Router (`app/api/v1/router.py`)**

```python
"""
Main API Router
Combines all endpoint routers
"""

from fastapi import APIRouter
from app.api.v1.endpoints import auth, users, items, health

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(items.router, prefix="/items", tags=["Items"])
api_router.include_router(health.router, prefix="/health", tags=["Health"])
```

### **7. Endpoint Example (`app/api/v1/endpoints/users.py`)**

```python
"""
User Endpoints
User management API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.schemas.user import User, UserCreate, UserUpdate
from app.services.user_service import UserService
from app.schemas.base import PaginationParams, PaginatedResponse

router = APIRouter()

@router.get("/", response_model=PaginatedResponse)
def get_users(
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get paginated list of users"""
    service = UserService(db)
    users, total = service.get_users_paginated(
        skip=pagination.offset,
        limit=pagination.size
    )
    return PaginatedResponse.create(users, total, pagination.page, pagination.size)

@router.get("/{user_id}", response_model=User)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get user by ID"""
    service = UserService(db)
    user = service.get_user(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user

@router.post("/", response_model=User, status_code=status.HTTP_201_CREATED)
def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """Create a new user"""
    service = UserService(db)
    user = service.create_user(user_data)
    return user

@router.put("/{user_id}", response_model=User)
def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update user"""
    service = UserService(db)
    user = service.update_user(user_id, user_data)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Delete user"""
    service = UserService(db)
    success = service.delete_user(user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
```

### **8. Service Layer (`app/services/user_service.py`)**

```python
"""
User Service
Business logic for user operations
"""

from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.core.security import get_password_hash

class UserService:
    """User service for business logic"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_user(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        return self.db.query(User).filter(User.id == user_id).first()
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        return self.db.query(User).filter(User.email == email).first()
    
    def get_users_paginated(self, skip: int = 0, limit: int = 100) -> Tuple[List[User], int]:
        """Get paginated users"""
        users = self.db.query(User).offset(skip).limit(limit).all()
        total = self.db.query(User).count()
        return users, total
    
    def create_user(self, user_data: UserCreate) -> User:
        """Create new user"""
        hashed_password = get_password_hash(user_data.password)
        user = User(
            email=user_data.email,
            hashed_password=hashed_password,
            full_name=user_data.full_name,
            is_active=user_data.is_active
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user
    
    def update_user(self, user_id: int, user_data: UserUpdate) -> Optional[User]:
        """Update user"""
        user = self.get_user(user_id)
        if not user:
            return None
        
        update_data = user_data.dict(exclude_unset=True)
        if "password" in update_data:
            update_data["hashed_password"] = get_password_hash(update_data.pop("password"))
        
        for field, value in update_data.items():
            setattr(user, field, value)
        
        self.db.commit()
        self.db.refresh(user)
        return user
    
    def delete_user(self, user_id: int) -> bool:
        """Delete user (soft delete)"""
        user = self.get_user(user_id)
        if not user:
            return False
        
        user.is_active = False
        self.db.commit()
        return True
```

### **9. Middleware Example (`app/api/middleware/rate_limit.py`)**

```python
"""
Rate Limiting Middleware
Implements rate limiting for API endpoints
"""

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import time
from collections import defaultdict, deque
from typing import Dict, Deque

from app.core.config import settings

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware"""
    
    def __init__(self, app, requests_per_minute: int = None):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute or settings.RATE_LIMIT_REQUESTS
        self.requests: Dict[str, Deque[float]] = defaultdict(lambda: deque())
    
    async def dispatch(self, request: Request, call_next):
        """Process request with rate limiting"""
        client_ip = request.client.host
        current_time = time.time()
        
        # Clean old requests (older than 1 minute)
        minute_ago = current_time - 60
        while self.requests[client_ip] and self.requests[client_ip][0] < minute_ago:
            self.requests[client_ip].popleft()
        
        # Check rate limit
        if len(self.requests[client_ip]) >= self.requests_per_minute:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Please try again later."
            )
        
        # Add current request
        self.requests[client_ip].append(current_time)
        
        # Process request
        response = await call_next(request)
        return response
```

### **10. Test Configuration (`app/tests/conftest.py`)**

```python
"""
Test Configuration
Pytest configuration and fixtures
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import get_db, Base
from app.core.config import settings

# Test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session")
def db_engine():
    """Create test database engine"""
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def db_session(db_engine):
    """Create test database session"""
    connection = db_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture(scope="function")
def client(db_session):
    """Create test client"""
    def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture
def test_user_data():
    """Test user data"""
    return {
        "email": "test@example.com",
        "password": "testpassword123",
        "full_name": "Test User"
    }
```

## 🎯 **Key Best Practices Implemented**

### **1. Project Organization**
- **Modular Structure**: Clear separation of concerns
- **Versioning**: API versioning for backward compatibility
- **Layered Architecture**: Models, schemas, services, endpoints

### **2. Security**
- **JWT Authentication**: Secure token-based authentication
- **Password Hashing**: Bcrypt for password security
- **Rate Limiting**: Protection against abuse
- **CORS Configuration**: Controlled cross-origin access
- **Security Headers**: Comprehensive security headers

### **3. Database Management**
- **SQLAlchemy ORM**: Robust database abstraction
- **Migration Support**: Database schema versioning
- **Connection Pooling**: Efficient database connections
- **Transaction Management**: Proper transaction handling

### **4. Error Handling**
- **Centralized Error Handling**: Consistent error responses
- **HTTP Status Codes**: Proper status code usage
- **Validation Errors**: Pydantic validation integration
- **Custom Exceptions**: Business logic exceptions

### **5. Performance**
- **Async Support**: Asynchronous request handling
- **Caching**: Redis integration for caching
- **Pagination**: Efficient data pagination
- **Database Optimization**: Query optimization

### **6. Testing**
- **Comprehensive Testing**: Unit and integration tests
- **Test Database**: Isolated test environment
- **Fixtures**: Reusable test components
- **Coverage**: High test coverage

### **7. Documentation**
- **Auto-generated Docs**: FastAPI automatic documentation
- **OpenAPI Integration**: Standard API specification
- **Type Hints**: Comprehensive type annotations
- **Docstrings**: Detailed function documentation

## 🚀 **Usage Instructions**

### **1. Project Setup**
```bash
# Create project directory
mkdir my_fastapi_project
cd my_fastapi_project

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### **2. Environment Configuration**
```bash
# Copy environment template
cp .env.example .env

# Edit environment variables
nano .env
```

### **3. Database Setup**
```bash
# Run migrations
alembic upgrade head

# Or create tables directly
python -c "from app.core.database import engine; from app.models import Base; Base.metadata.create_all(bind=engine)"
```

### **4. Running the Application**
```bash
# Development
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### **5. Testing**
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest app/tests/test_users.py
```

## 📚 **Additional Resources**

### **Dependencies (`requirements.txt`)**
```
fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
alembic==1.12.1
pydantic==2.5.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6
redis==5.0.1
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0
httpx==0.25.2
```

### **Development Dependencies (`requirements-dev.txt`)**
```
black==23.11.0
isort==5.12.0
flake8==6.1.0
mypy==1.7.1
pre-commit==3.6.0
```

## 🎯 **Conclusion**

This template provides a solid foundation for building production-ready FastAPI applications. It incorporates industry best practices for security, performance, maintainability, and scalability. Use this structure as a starting point and adapt it to your specific project requirements.

The modular design allows for easy extension and modification, while the comprehensive testing and documentation ensure long-term maintainability. Follow the patterns established in this template to create consistent, high-quality APIs across all your projects.
