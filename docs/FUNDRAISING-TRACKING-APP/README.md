# 🏃‍♂️ Ready & Raising - Fundraising Tracking App

## 🎯 **Project Overview**

**Ready & Raising** is a comprehensive fundraising tracking application that combines training data from Strava with real-time fundraising progress from JustGiving. The app provides a unified dashboard showing both preparation activities and donation progress for charity events.

### **What It Does**
- **Training Activities**: Displays Strava data showing preparation leading up to charity events
- **Fundraising Progress**: Real-time donation tracking and goal progress from JustGiving
- **Unified Dashboard**: All data in one convenient location for supporters to see progress

### **Technical Architecture**
- **Backend**: FastAPI with hybrid caching (Supabase + local JSON)
- **Data Sources**: Strava API + JustGiving web scraping
- **Deployment**: DigitalOcean App Platform with Cloudflare routing
- **Security**: API key authentication, rate limiting, and multi-layer security

---

## 📅 **Project Timeline & Development Journey**

### **Phase 1: Initial Setup & Architecture (Early Development)**
- **Multi-project API structure** established
- **FastAPI application** with project-based routing
- **Basic Strava integration** with token management
- **Initial fundraising scraper** for JustGiving data

### **Phase 2: Advanced Caching & Data Management**
- **Smart caching system** implemented for Strava data
- **Hybrid caching strategy** (in-memory + file + Supabase)
- **Rate limiting** and API call optimization
- **Background processing** for data enrichment

### **Phase 3: Production Deployment & Optimization**
- **DigitalOcean App Platform** deployment configuration
- **Environment variable management** and secrets setup
- **Health checks** and monitoring implementation
- **Performance optimization** and error handling

### **Phase 4: Advanced Features & Reliability**
- **Automated token refresh** for Strava API
- **Smart data merging** to preserve existing data
- **Emergency refresh logic** for data integrity
- **Comprehensive error handling** and fallback systems

### **Phase 5: Production Issues & Resolutions**
- **Token refresh loop** issues resolved
- **Timezone configuration** (UTC → Europe/London)
- **Supabase integration** for data persistence
- **Cache validation** and integrity checks

### **Phase 6: Final Optimization & Documentation**
- **Log optimization** with emoji indicators
- **Demo endpoints** for development testing
- **Comprehensive documentation** and code explanations
- **Security review** and sanitization

---

## 🏗️ **System Architecture**

### **Data Collection Layer**
- **Strava Integration**: Fetches training activities, GPS routes, photos, comments
- **Fundraising Scraper**: Scrapes JustGiving pages for donation data
- **Hybrid Caching**: Supabase persistence with local JSON fallback

### **Data Processing Layer**
- **Async Processing**: Background data enrichment and formatting
- **Smart Merging**: Preserves existing data while updating new information
- **Rate Limiting**: Respects API limits and implements backoff strategies

### **API Layer**
- **FastAPI Application**: RESTful API with comprehensive endpoints
- **Security Middleware**: API key authentication and request validation
- **Error Handling**: Graceful degradation and comprehensive logging

### **Frontend Integration**
- **Demo Pages**: Development testing interfaces
- **API Endpoints**: Production-ready data access
- **Real-time Updates**: 15-minute fundraising, 6-hour Strava refresh

---

## 📚 **Documentation Structure**

### **Implementation Guides**
- **[Option 3 Implementation Guide](OPTION_3_IMPLEMENTATION_GUIDE.md)** - Complete deployment guide
- **[DigitalOcean Secrets Setup](DIGITALOCEAN_SECRETS_SETUP.md)** - Environment configuration
- **[Startup Scripts Guide](../MULTI-PROJECT-API-SERVICE/STARTUP_SCRIPTS_GUIDE.md)** - Development workflow

### **API Documentation**
- **[API Documentation](API_DOCUMENTATION.md)** - Complete endpoint reference
- **[System Architecture](../MULTI-PROJECT-API-SERVICE/SYSTEM_ARCHITECTURE_OVERVIEW.md)** - Technical overview

### **Code Explanations**
- **[Smart Strava Cache](codebase-explanation/smart_strava_cache_explanation.md)** - Caching strategy
- **[Fundraising Scraper](codebase-explanation/fundraising_scraper_explanation.md)** - Web scraping implementation
- **[Strava Integration](codebase-explanation/strava_integration_api_explanation.md)** - API integration
- **[Token Manager](codebase-explanation/strava_token_manager_explanation.md)** - Authentication

---

## 💻 **Code Organization**

The fundraising tracking app code is located in `projects/fundraising_tracking_app/`:

```
projects/fundraising_tracking_app/
├── examples/                           # Demo pages and usage examples
├── env.example                         # Environment variable template
├── env.production                      # Production environment template  
├── supabase_security_setup_template.sql # Database schema template
├── fundraising_scraper/                # Fundraising API and scraper
│   ├── fundraising_api.py             # API endpoints
│   ├── fundraising_scraper.py         # Web scraping logic
│   └── models.py                      # Data models
└── strava_integration/                 # Strava API integration
    ├── smart_strava_cache.py          # Caching system
    ├── strava_integration_api.py      # API endpoints
    ├── strava_token_manager.py        # Authentication
    └── supabase_cache_manager.py      # Database integration
```

---

## 🎯 **Key Features & Capabilities**

### **Data Management**
- **Hybrid Caching**: Supabase persistence with local JSON fallback
- **Smart Merging**: Preserves existing data while updating new information
- **Data Validation**: Integrity checks and corruption recovery
- **Backup System**: Automatic backups and restoration

### **API Integration**
- **Strava API**: Training activities, GPS routes, photos, comments
- **JustGiving Scraping**: Donation data, donor information, progress tracking
- **Rate Limiting**: Respects API limits with exponential backoff
- **Error Handling**: Comprehensive error management and recovery

### **Security & Performance**
- **API Key Authentication**: Secure endpoint access
- **Rate Limiting**: 1000 requests per hour protection
- **Security Headers**: XSS, clickjacking protection
- **Health Monitoring**: Continuous health checks and logging

### **Development & Testing**
- **Demo Endpoints**: Development testing interfaces
- **Environment Management**: Development vs production configurations
- **Comprehensive Logging**: Debug and production logging levels
- **Automated Testing**: Unit and integration test coverage

---

## 🚀 **Deployment & Production**

### **Current Status**
- **Production Deployed**: DigitalOcean App Platform
- **Domain**: `https://api.russellmorbey.co.uk/`
- **Environment**: Production with automated token refresh
- **Monitoring**: Health checks and performance metrics

### **Key Achievements**
- **Zero-downtime deployment** with automated token refresh
- **Hybrid caching** ensuring data persistence across restarts
- **Comprehensive error handling** with graceful degradation
- **Production-ready security** with multi-layer authentication

---

## 🔗 **Related Documentation**

- **[Multi-Project API Service](../MULTI-PROJECT-API-SERVICE/)** - Reusable infrastructure components
- **[Internal Documentation](../internal/)** - Security and internal notes
- **[Main Documentation Index](../README.md)** - Complete documentation navigation