# 🏗️ System Architecture & Data Flow Overview

## 📊 **Core System Components**

### **1. Data Collection Layer**
- **Activity Integration** (`activity_cache.py`) - GPX import from Google Sheets
- **Fundraising Scraper** (`fundraising_scraper.py`)
- **HTTP Clients** (`http_clients.py`)
- **Supabase Cache Manager** (`supabase_cache_manager.py`)

### **2. Data Processing Layer**
- **Async Processor** (`async_processor.py`)
- **Smart Cache Management** (Activity & Fundraising)
- **GPX Parser** (parses GPS data from GPX files)
- **Data Validation & Formatting**
- **Hybrid Caching Strategy** (Supabase for activities, Local JSON for fundraising)

### **3. API Layer**
- **FastAPI Application** (`multi_project_api.py`)
- **Multi-Layer Security** (`security.py`)
- **Error Handling** (`simple_error_handlers.py`)
- **Compression Middleware** (`compression_middleware.py`)
- **Cache Middleware** (`cache_middleware.py`)

### **4. Security Layer**
- **API Key Authentication** - All production endpoints protected
- **Frontend Access Verification** - Referer header validation
- **Rate Limiting** - 1000 requests per hour
- **Security Headers** - XSS, clickjacking protection
- **Trusted Host Middleware** - Domain validation

### **5. Frontend Layer**
- **Demo Pages** (`examples/`) - No API keys required
- **Static File Serving**
- **Public Access Endpoints** - `/demo/*` routes

---

## 🛡️ **Enhanced Security Flow**

### **Multi-Layer Security Architecture:**
```
Request → Trusted Host Check → Referer Validation → API Key Auth → Rate Limiting → Security Headers → Endpoint
```

### **Security Layers Explained:**
1. **Trusted Host Check** - Validates request domain against allowed hosts
2. **Referer Validation** - Ensures request comes from authorized frontend domains
3. **API Key Authentication** - Validates API key for protected endpoints
4. **Rate Limiting** - Enforces 1000 requests per hour limit
5. **Security Headers** - Adds protection headers (XSS, clickjacking, etc.)
6. **Endpoint Access** - Grants access to protected resources

### **Demo vs Production Access:**
- **Demo Endpoints** (`/demo/*`) - No authentication required, public access
- **Production Endpoints** (`/api/*`) - Full multi-layer security required

---

## 🔄 **Complete Data Flow Process**

### **Phase 1: Data Collection & Caching**

#### **Activity Data Import (GPX):**
```
1. POST /api/activity-integration/gpx/import-from-sheets
   ↓
2. HTTP Client → Google Sheets API → Google Drive API
   ↓
3. Fetch GPX File Content
   ↓
4. Parse GPX File (GPS coordinates, timestamps, metadata)
   ↓
5. Calculate Activity Metrics (distance, duration, elevation)
   ↓
6. Store in Supabase + Music Detection
   ↓
7. Cache Storage (Supabase database + in-memory)
```

#### **Fundraising Data Collection:**
```
1. FundraisingScraper.force_refresh_now()
   ↓
2. HTTP Client → JustGiving Website
   ↓
3. HTML Scraping (BeautifulSoup with CSS selectors)
   ↓
4. Data Extraction (amount, donations, messages)
   ↓
5. Smart Merge with Existing Cache
   ↓
6. Hybrid Cache Storage (Supabase + JSON file + in-memory)
```

### **Phase 2: Data Processing & Enhancement**

#### **Async Processing Pipeline:**
```
Raw Data → AsyncProcessor → Enhanced Data
    ↓
1. Music Detection (Deezer API)
2. Photo Processing & Optimization
3. Date/Time Formatting
4. Distance/Duration Formatting
5. Comment Cleaning
6. Map Data Optimization
```

### **Phase 3: API Endpoint Processing**

#### **Request Flow:**
```
Frontend Request → Security Middleware → API Endpoint → Data Processing → Response
    ↓
1. API Key Verification
2. Rate Limiting
3. Domain Validation
4. Cache Retrieval
5. Async Processing
6. Response Formatting
7. Caching Headers
```

### **Phase 4: Frontend Delivery**

#### **Demo Page Flow:**
```
Browser → Static File Server → Demo Page → API Calls → Data Display
    ↓
1. HTML/CSS/JS Loading
2. API Endpoint Calls (/demo/*)
3. Data Processing & Display
4. Interactive Features
```

---

## 🔗 **Component Interconnections**

### **Core Dependencies:**

#### **SmartStravaCache Dependencies:**
- `http_clients.py` → HTTP requests to Strava API
- `async_processor.py` → Data processing & enhancement
- `security.py` → Rate limiting & API key validation
- File system → Cache persistence

#### **SmartFundraisingCache Dependencies:**
- `http_clients.py` → HTTP requests to JustGiving
- `async_processor.py` → Donation data processing
- BeautifulSoup → HTML parsing
- File system → Cache persistence

#### **AsyncProcessor Dependencies:**
- `http_clients.py` → Deezer API for music detection
- ThreadPoolExecutor → Parallel processing
- Both caches → Data enhancement

#### **API Layer Dependencies:**
- Both caches → Data retrieval
- `async_processor.py` → Data processing
- `security.py` → Authentication & rate limiting
- `simple_error_handlers.py` → Error management

---

## 📈 **Data Processing Pipeline**

### **Strava Activity Processing:**

```python
# 1. Raw Data Collection
raw_activities = strava_api.get_activities()

# 2. Smart Cache Merge
merged_activities = cache._smart_merge_activities(existing, raw)

# 3. Rich Data Collection
for activity in merged_activities:
    if needs_rich_data(activity):
        rich_data = fetch_activity_details(activity.id)
        activity.update(rich_data)

# 4. Async Processing
processed_activities = await async_processor.process_activities_parallel(activities)

# 5. Response Formatting
feed_items = []
for activity in processed_activities:
    feed_item = {
        "id": activity["id"],
        "name": activity["name"],
        "distance_km": activity["distance"] / 1000,
        "duration_minutes": activity["moving_time"] / 60,
        "date": activity["date_formatted"],
        "time": activity["formatted_duration"],
        "photos": activity["photos"],
        "map": activity["map"],
        "music": activity["music"]
    }
    feed_items.append(feed_item)
```

### **Fundraising Data Processing:**

```python
# 1. Web Scraping
html = http_client.get(justgiving_url)
soup = BeautifulSoup(html, 'html.parser')

# 2. Data Extraction
total_raised = extract_total_raised(soup)
donations = extract_donations(soup)

# 3. Smart Cache Merge
merged_data = cache._smart_merge_fundraising_data(existing, new)

# 4. Async Processing
processed_donations = await async_processor.process_donations_parallel(donations)

# 5. Response Formatting
response_data = {
    "total_raised": total_raised,
    "target_amount": 300,
    "progress_percentage": (total_raised / 300) * 100,
    "donations": processed_donations
}
```

---

## 🚀 **Performance Optimizations**

### **Caching Strategy:**
- **In-Memory Cache**: Fast access for recent data
- **File Cache**: Persistence across restarts
- **HTTP Caching**: Browser-level caching with ETags
- **Smart Merging**: Preserves rich data while updating basic info

### **Async Processing:**
- **Parallel Activity Processing**: Multiple activities processed simultaneously
- **Thread Pool**: CPU-bound tasks (formatting, parsing)
- **Async I/O**: Network requests (music detection, API calls)

### **Rate Limiting:**
- **Strava API**: 1000 calls/day, 15 calls/15min
- **Deezer API**: Reasonable limits for music detection
- **JustGiving**: Respectful scraping intervals

---

## 🔐 **Security Architecture**

### **Multi-Layer Security:**
```
1. API Key Authentication (X-API-Key header)
2. Domain Validation (Referer header check)
3. Rate Limiting (per-IP and global)
4. Input Validation (Pydantic models)
5. Error Handling (no sensitive data exposure)
```

### **Demo vs Production:**
- **Demo Endpoints**: No authentication required (`/demo/*`)
- **Production Endpoints**: Full authentication required
- **Secure Token Handling**: Server-side only, never exposed to client

---

## 📊 **Data Storage & Persistence**

### **Cache Files:**
- `strava_cache.json` → Strava activities
- `fundraising_cache.json` → Fundraising data
- `*_backup_*.json` → Automatic backups

### **Cache Structure:**
```json
{
  "timestamp": "2025-10-02T20:47:30.955923",
  "activities": [...],
  "last_updated": "2025-10-02T20:47:30.956991",
  "cache_status": "active"
}
```

---

## 🔄 **Real-Time Updates**

### **Automatic Refresh:**
- **Strava**: Every 6 hours (configurable)
- **Fundraising**: Every 15 minutes
- **Smart Merging**: Preserves existing rich data

### **Manual Refresh:**
- **API Endpoints**: `/refresh-cache`, `/refresh`
- **Requires Authentication**: API key validation
- **Immediate Processing**: Bypasses cache TTL

---

## 🎯 **Frontend Integration**

### **Demo Pages:**
- **Strava Demo**: `http://localhost:8000/demo`
- **Fundraising Demo**: `http://localhost:8000/fundraising-demo`

### **API Endpoints:**
- **Strava**: `/api/strava-integration/demo/feed`
- **Fundraising**: `/api/fundraising/demo/data`
- **Map Tiles**: `/api/strava-integration/demo/map-tiles/{z}/{x}/{y}`

### **Data Flow to Frontend:**
```
1. Browser loads demo page
2. JavaScript makes API calls to demo endpoints
3. API retrieves data from cache
4. Async processing enhances data
5. Formatted JSON response sent to browser
6. JavaScript renders data in UI
7. Interactive features (maps, music) activated
```

---

## 🏆 **System Strengths**

### **Scalability:**
- **Async Processing**: Handles multiple requests efficiently
- **Smart Caching**: Reduces API calls and improves performance
- **Modular Design**: Easy to extend and maintain

### **Reliability:**
- **Error Handling**: Graceful degradation on failures
- **Backup System**: Automatic cache backups
- **Rate Limiting**: Prevents API abuse

### **Security:**
- **Multi-layer Authentication**: API keys, domain validation
- **No Secret Exposure**: Demo endpoints for public access
- **Input Validation**: Pydantic models ensure data integrity

### **User Experience:**
- **Fast Response Times**: Cached data with smart processing
- **Rich Data**: Maps, photos, music, comments
- **Real-time Updates**: Automatic refresh with manual override

---

This architecture provides a robust, scalable, and secure system for collecting, processing, and delivering fitness and fundraising data to frontend applications.
