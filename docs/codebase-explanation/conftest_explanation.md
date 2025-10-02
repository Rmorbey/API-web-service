# 📚 conftest.py - Complete Code Explanation

## 🎯 **Overview**

This file is the **central pytest configuration file** that provides shared fixtures, test setup, and configuration for the entire test suite. It's the foundation that makes all other tests work by providing common test data, mock objects, and test clients.

## 📁 **File Structure Context**

```
conftest.py  ← YOU ARE HERE (Test Configuration)
├── tests/                          (Test directory)
│   ├── unit/                       (Unit tests)
│   ├── integration/                (Integration tests)
│   └── performance/                (Performance tests)
├── multi_project_api.py            (Main API)
└── projects/                       (Project modules)
```

## 🔍 **Key Components**

### **1. Environment Setup**

#### **Python Path Configuration**
```python
# Add project root to Python path for imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
```

**Purpose**: Ensures Python can find and import project modules during testing.

**How it works**:
- **`os.path.dirname(__file__)`**: Gets the directory containing conftest.py
- **`os.path.dirname()` again**: Goes up one level to project root
- **`sys.path.insert(0, ...)`**: Adds project root to Python path
- **Priority**: `0` index ensures project modules are found first

#### **Test Environment Variables**
```python
# Set test environment variables
os.environ["STRAVA_API_KEY"] = "test-strava-key-123"
os.environ["FUNDRAISING_API_KEY"] = "test-fundraising-key-456"
os.environ["STRAVA_ACCESS_TOKEN"] = "test-strava-token-789"
os.environ["JAWG_API_KEY"] = "test-jawg-key-abc"
os.environ["JUSTGIVING_URL"] = "https://test-justgiving.com/test-page"
```

**Purpose**: Sets up test environment variables that tests can rely on.

**Benefits**:
- **Consistent testing**: All tests use the same test values
- **No external dependencies**: Tests don't need real API keys
- **Isolation**: Tests are isolated from production environment
- **Predictability**: Tests behave consistently across environments

### **2. Core Fixtures**

#### **Environment Variables Fixture**
```python
@pytest.fixture(scope="session")
def test_env_vars() -> Dict[str, str]:
    """Provide test environment variables."""
    return {
        "STRAVA_API_KEY": "test-strava-key-123",
        "FUNDRAISING_API_KEY": "test-fundraising-key-456", 
        "STRAVA_ACCESS_TOKEN": "test-strava-token-789",
        "JAWG_API_KEY": "test-jawg-key-abc",
        "JUSTGIVING_URL": "https://test-justgiving.com/test-page"
    }
```

**Fixture Features**:
- **Session scope**: Created once per test session
- **Type hints**: `Dict[str, str]` for type safety
- **Documentation**: Clear docstring explaining purpose
- **Reusability**: Can be used by any test

#### **Temporary Directory Fixture**
```python
@pytest.fixture(scope="function")
def temp_dir() -> Generator[str, None, None]:
    """Create a temporary directory for test files."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)
```

**Fixture Features**:
- **Function scope**: Created fresh for each test
- **Generator pattern**: `yield` provides the directory, cleanup happens after
- **Automatic cleanup**: `shutil.rmtree()` removes directory after test
- **Isolation**: Each test gets its own clean directory

### **3. Mock Data Fixtures**

#### **Strava API Response Mock**
```python
@pytest.fixture(scope="function")
def mock_strava_api_response() -> Dict[str, Any]:
    """Mock Strava API response data."""
    return {
        "id": 123456789,
        "name": "Test Activity",
        "type": "Run",
        "distance": 5000.0,
        "moving_time": 1800,
        "elapsed_time": 1900,
        "start_date": "2025-01-01T10:00:00Z",
        "start_date_local": "2025-01-01T10:00:00Z",
        "description": "Test run description",
        "polyline": "test_polyline_data",
        "summary_polyline": "test_summary_polyline_data",
        "photos": {
            "primary": {
                "id": 123,
                "urls": {
                    "100": "https://example.com/photo.jpg"
                }
            }
        },
        "comments": [
            {
                "id": 1,
                "text": "Great run!",
                "athlete": {"id": 1, "firstname": "Test", "lastname": "User"}
            }
        ]
    }
```

**Mock Data Features**:
- **Realistic structure**: Matches actual Strava API response
- **Complete data**: Includes all necessary fields
- **Test values**: Safe, predictable test data
- **Reusability**: Can be used by multiple tests

#### **JustGiving HTML Mock**
```python
@pytest.fixture(scope="function")
def mock_justgiving_html() -> str:
    """Mock JustGiving HTML content."""
    return """
    <html>
        <body>
            <div class="total-raised">£150.00</div>
            <div class="donation">
                <span class="donor-name">Test Donor</span>
                <span class="amount">£25.00</span>
                <span class="message">Great cause!</span>
                <span class="date">2 days ago</span>
            </div>
        </body>
    </html>
    """
```

**HTML Mock Features**:
- **Realistic HTML**: Matches actual JustGiving page structure
- **Test data**: Predictable donation information
- **CSS selectors**: Matches scraper expectations
- **Complete structure**: Includes all necessary elements

#### **Cache Data Mocks**
```python
@pytest.fixture(scope="function")
def mock_cache_data() -> Dict[str, Any]:
    """Mock cache data structure."""
    return {
        "timestamp": "2025-01-01T10:00:00Z",
        "last_updated": "2025-01-01T10:00:00Z",
        "version": "1.0",
        "activities": [
            {
                "id": 123456789,
                "name": "Test Activity",
                "type": "Run",
                "distance": 5000.0,
                "moving_time": 1800,
                "start_date_local": "2025-01-01T10:00:00Z",
                "description": "Test description",
                "polyline": "test_polyline",
                "bounds": {"northeast": {"lat": 51.5, "lng": -0.1}, "southwest": {"lat": 51.4, "lng": -0.2}},
                "photos": [],
                "comments": []
            }
        ],
        "total_activities": 1
    }
```

**Cache Mock Features**:
- **Complete structure**: Includes all cache fields
- **Nested data**: Activities array with full activity data
- **Metadata**: Timestamps, version, counts
- **Consistency**: Matches actual cache structure

### **4. HTTP Client Mocks**

#### **httpx Client Mock**
```python
@pytest.fixture(scope="function")
def mock_httpx_client():
    """Mock httpx client for external API calls."""
    with patch('httpx.AsyncClient') as mock_client:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}
        mock_response.text = "Mock response"
        
        mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
        mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
        
        yield mock_client
```

**HTTP Mock Features**:
- **Context manager**: `with patch()` for proper cleanup
- **Async support**: Mocks async HTTP client
- **Response mocking**: Mock response objects
- **Method mocking**: GET and POST methods

#### **Requests Library Mock**
```python
@pytest.fixture(scope="function")
def mock_requests():
    """Mock requests library for web scraping."""
    with patch('requests.get') as mock_get:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "<html>Mock HTML</html>"
        mock_response.content = b"<html>Mock HTML</html>"
        mock_get.return_value = mock_response
        yield mock_get
```

**Requests Mock Features**:
- **Synchronous mocking**: Mocks requests.get
- **HTML content**: Mock HTML responses
- **Binary content**: Mock binary responses
- **Status codes**: Mock HTTP status codes

### **5. FastAPI Test Clients**

#### **Main App Test Client**
```python
@pytest.fixture(scope="function")
def test_client():
    """Create a test client for the main FastAPI app."""
    from multi_project_api import app
    with TestClient(app) as client:
        yield client
```

**Test Client Features**:
- **FastAPI integration**: Uses FastAPI's TestClient
- **Context manager**: Proper cleanup with `with`
- **Function scope**: Fresh client for each test
- **Full app**: Tests the complete application

#### **Strava Integration Test Client**
```python
@pytest.fixture(scope="function")
def strava_test_client():
    """Create a test client for Strava integration endpoints."""
    from fastapi import FastAPI
    from fastapi.exceptions import RequestValidationError
    from projects.fundraising_tracking_app.strava_integration.strava_integration_api import router as strava_router
    from projects.fundraising_tracking_app.strava_integration.error_handlers import (
        api_exception_handler,
        validation_exception_handler,
        http_exception_handler,
        general_exception_handler
    )
    
    # Create a test app with the Strava router
    test_app = FastAPI()
    test_app.include_router(strava_router, prefix="/api/strava-integration")
    
    # Import APIException and add its handler first (more specific)
    from projects.fundraising_tracking_app.strava_integration.error_handlers import APIException
    test_app.add_exception_handler(APIException, api_exception_handler)
    
    # Add other error handlers (less specific)
    test_app.add_exception_handler(RequestValidationError, validation_exception_handler)
    test_app.add_exception_handler(Exception, general_exception_handler)
    
    with TestClient(test_app) as client:
        yield client
```

**Specialized Client Features**:
- **Module-specific**: Tests only Strava integration
- **Error handlers**: Includes all error handling
- **Router inclusion**: Adds specific router
- **Exception handling**: Proper error handling setup

#### **Fundraising Test Client**
```python
@pytest.fixture(scope="function")
def fundraising_test_client():
    """Create a test client for fundraising endpoints."""
    from fastapi import FastAPI
    from projects.fundraising_tracking_app.fundraising_scraper.fundraising_api import router as fundraising_router
    
    # Create a test app with the fundraising router
    test_app = FastAPI()
    test_app.include_router(fundraising_router, prefix="/api/fundraising")
    
    with TestClient(test_app) as client:
        yield client
```

**Fundraising Client Features**:
- **Module-specific**: Tests only fundraising functionality
- **Router inclusion**: Adds fundraising router
- **Prefix**: Uses `/api/fundraising` prefix
- **Isolation**: Tests fundraising in isolation

### **6. Authentication Fixtures**

#### **Valid API Headers**
```python
@pytest.fixture(scope="function")
def valid_api_headers() -> Dict[str, str]:
    """Provide valid API headers for testing."""
    return {
        "X-API-Key": "test-strava-key-123",
        "Content-Type": "application/json"
    }
```

**Authentication Features**:
- **Valid credentials**: Uses test API key
- **Content type**: Proper JSON content type
- **Reusability**: Can be used by any test
- **Type safety**: `Dict[str, str]` type hint

#### **Invalid API Headers**
```python
@pytest.fixture(scope="function")
def invalid_api_headers() -> Dict[str, str]:
    """Provide invalid API headers for testing."""
    return {
        "X-API-Key": "invalid-key",
        "Content-Type": "application/json"
    }
```

**Invalid Auth Features**:
- **Invalid credentials**: Tests authentication failure
- **Error testing**: Tests error handling
- **Security testing**: Tests security measures
- **Edge case testing**: Tests boundary conditions

### **7. Sample Data Fixtures**

#### **Sample Strava Activities**
```python
@pytest.fixture(scope="function")
def sample_strava_activities() -> List[Dict[str, Any]]:
    """Sample Strava activities for testing."""
    return [
        {
            "id": 15806551007,
            "name": "Morning Run",
            "type": "Run",
            "distance": 5000.0,
            "moving_time": 1800,
            "elapsed_time": 1900,
            "start_date": "2025-09-06T07:00:00Z",
            "start_date_local": "2025-09-06T08:00:00Z",
            "description": "Beautiful morning run",
            "polyline": "test_polyline_data_1",
            "summary_polyline": "test_summary_polyline_1",
            "bounds": {
                "northeast": {"lat": 51.5074, "lng": -0.1278},
                "southwest": {"lat": 51.5073, "lng": -0.1279}
            },
            "photos": [],
            "comments": []
        },
        # ... more activities
    ]
```

**Sample Data Features**:
- **Multiple activities**: Tests with multiple data points
- **Realistic data**: Matches actual Strava data structure
- **Variety**: Different activity types and data
- **Complete structure**: All necessary fields included

#### **Sample Donations Data**
```python
@pytest.fixture(scope="function")
def sample_donations_data() -> List[Dict[str, Any]]:
    """Sample donations data for testing."""
    return [
        {
            "donor_name": "John Doe",
            "amount": 25.0,
            "message": "Great cause!",
            "date": "2 days ago",
            "scraped_at": "2025-01-01T10:00:00Z"
        },
        {
            "donor_name": "Jane Smith", 
            "amount": 50.0,
            "message": "Keep up the good work!",
            "date": "1 week ago",
            "scraped_at": "2025-01-01T10:00:00Z"
        }
    ]
```

**Donations Data Features**:
- **Multiple donations**: Tests with multiple data points
- **Realistic data**: Matches actual donation structure
- **Variety**: Different donors and amounts
- **Complete structure**: All necessary fields included

## 🎯 **Key Learning Points**

### **1. Test Configuration**

#### **Fixture Design**
- **Scope management**: Session, function, module scopes
- **Resource management**: Proper setup and teardown
- **Reusability**: Shared fixtures across tests
- **Type safety**: Type hints for better IDE support

#### **Mock Data Strategy**
- **Realistic data**: Mock data that matches real data
- **Complete coverage**: All necessary fields included
- **Predictable values**: Consistent test data
- **Edge cases**: Different scenarios covered

### **2. Testing Best Practices**

#### **Isolation**
- **Test independence**: Tests don't depend on each other
- **Clean state**: Fresh state for each test
- **Resource cleanup**: Proper cleanup after tests
- **Environment isolation**: Test environment separate from production

#### **Mocking Strategy**
- **External dependencies**: Mock external APIs
- **HTTP clients**: Mock HTTP requests
- **File operations**: Mock file system operations
- **Database operations**: Mock database calls

### **3. FastAPI Testing**

#### **Test Client Usage**
- **FastAPI TestClient**: Built-in testing support
- **Router testing**: Test individual routers
- **Error handling**: Test error scenarios
- **Authentication**: Test with different auth states

#### **Integration Testing**
- **Full app testing**: Test complete application
- **Module testing**: Test individual modules
- **Error testing**: Test error handling
- **Performance testing**: Test performance characteristics

## 🚀 **How This Fits Into Your Learning**

### **1. Testing Fundamentals**
- **Test setup**: How to configure test environments
- **Fixture design**: How to create reusable test components
- **Mocking**: How to mock external dependencies
- **Test organization**: How to structure test code

### **2. Python Testing**
- **pytest**: How to use pytest effectively
- **Fixtures**: How to create and use fixtures
- **Mocking**: How to mock objects and functions
- **Type hints**: How to use type hints in tests

### **3. API Testing**
- **FastAPI testing**: How to test FastAPI applications
- **HTTP testing**: How to test HTTP endpoints
- **Authentication testing**: How to test auth scenarios
- **Error testing**: How to test error handling

## 📚 **Next Steps**

1. **Review fixtures**: Understand each fixture and its purpose
2. **Use in tests**: See how fixtures are used in actual tests
3. **Create new fixtures**: Add fixtures for new functionality
4. **Test patterns**: Learn common testing patterns

This conftest.py file is the foundation of your testing infrastructure and demonstrates advanced testing practices! 🎉
