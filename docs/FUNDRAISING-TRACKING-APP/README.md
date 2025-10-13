# 🏃‍♂️ Fundraising Tracking App

This folder contains documentation for the **Ready & Raising - Fundraising Tracking App** and all the API endpoints that power it. This includes both the fundraising scraper functionality and the Strava integration that provides training data for the fundraising dashboard.

## 🎯 **App Overview**

**Ready & Raising** is a comprehensive fundraising tracking application that displays:
- **Training Activities**: Strava data showing preparation leading up to charity events
- **Fundraising Progress**: Real-time donation tracking and goal progress
- **Unified Dashboard**: All data in one convenient location

## 📚 **Implementation & Setup**

### **Deployment Guides**
- **[Option 3 Implementation Guide](OPTION_3_IMPLEMENTATION_GUIDE.md)** - Complete step-by-step implementation guide
- **[DigitalOcean Secrets Setup](DIGITALOCEAN_SECRETS_SETUP.md)** - Environment variables and secrets configuration
- **[Domain Setup Guide](DOMAIN_SETUP_GUIDE.md)** - Domain routing and reverse proxy setup
- **[Automated Token Refresh Setup](AUTOMATED_TOKEN_REFRESH_SETUP.md)** - Token management automation

### **Project Analysis**
- **[Repository File Analysis](REPOSITORY_FILE_ANALYSIS.md)** - File structure and optimization analysis

## 🔧 **API Endpoints Documentation**

### **Fundraising API**
- **[Fundraising API](codebase-explanation/fundraising_api_explanation.md)** - Fundraising data endpoints and functionality
- **[Fundraising Scraper](codebase-explanation/fundraising_scraper_explanation.md)** - JustGiving web scraping implementation
- **[Test Fundraising Scraper](codebase-explanation/test_fundraising_scraper_explanation.md)** - Fundraising scraper testing

### **Strava Integration API**
- **[Strava Integration API](codebase-explanation/strava_integration_api_explanation.md)** - Strava data endpoints and functionality
- **[Smart Strava Cache](codebase-explanation/smart_strava_cache_explanation.md)** - Strava data caching and management
- **[Strava Token Manager](codebase-explanation/strava_token_manager_explanation.md)** - Strava authentication and token management
- **[Test Strava Integration](codebase-explanation/test_strava_integration_explanation.md)** - Strava integration testing

## 🏗️ **Architecture**

The Ready & Raising app is powered by two main API systems:

### **1. Fundraising Scraper**
- Scrapes JustGiving pages for donation data
- Tracks fundraising progress and goals
- Provides real-time donation updates
- Manages individual donor information

### **2. Strava Integration**
- Fetches training activities and performance data
- Provides GPS routes and activity details
- Tracks preparation progress for charity events
- Enriches data with photos, comments, and music

## 🔗 **Data Flow**

```
JustGiving Page → Fundraising Scraper → API Endpoints → Frontend Dashboard
Strava API → Strava Integration → API Endpoints → Frontend Dashboard
```

## 🎯 **Key Features**

- **Hybrid Caching**: Supabase persistence with local JSON fallback
- **Real-time Updates**: 15-minute fundraising refresh, 6-hour Strava refresh
- **Smart Data Merging**: Preserves individual donations while updating totals
- **Security**: API key authentication and rate limiting
- **Monitoring**: Health checks and performance metrics

## 🔗 **Related Documentation**

- **[Multi-Project API Service](../MULTI-PROJECT-API-SERVICE/)** - Reusable infrastructure components
- **[Internal Documentation](../internal/)** - Security and internal notes
