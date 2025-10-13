# 📊 Data Flow Diagrams

## 🔄 **Complete System Data Flow**

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Strava API    │    │  JustGiving     │    │   Deezer API    │
│   (External)    │    │   (External)    │    │   (External)    │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          ▼                      ▼                      ▼
┌─────────────────┐    ┌─────────────────┐              │
│ SmartStravaCache│    │SmartFundraising │              │
│                 │    │     Cache       │              │
│ • Rate Limiting │    │ • Web Scraping  │              │
│ • Smart Merge   │    │ • Data Extract  │              │
│ • Rich Data     │    │ • Smart Merge   │              │
└─────────┬───────┘    └─────────┬───────┘              │
          │                      │                      │
          ▼                      ▼                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                    AsyncProcessor                               │
│                                                                 │
│ • Music Detection (Deezer)                                     │
│ • Photo Processing                                             │
│ • Date/Time Formatting                                         │
│ • Distance/Duration Formatting                                 │
│ • Comment Cleaning                                             │
│ • Map Data Optimization                                        │
└─────────────────┬───────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Cache Storage                                │
│                                                                 │
│ • In-Memory Cache (Fast Access)                                │
│ • File Cache (Persistence)                                     │
│ • Backup System (Automatic)                                    │
└─────────────────┬───────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                    API Layer                                    │
│                                                                 │
│ • Security Middleware (API Keys, Rate Limiting)                │
│ • Demo Endpoints (No Auth Required)                            │
│ • Production Endpoints (Full Auth)                             │
│ • Error Handling & Validation                                  │
└─────────────────┬───────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Frontend Delivery                            │
│                                                                 │
│ • Demo Pages (HTML/CSS/JS)                                     │
│ • API Calls to Demo Endpoints                                  │
│ • Data Rendering & Visualization                               │
│ • Interactive Features (Maps, Music)                           │
└─────────────────────────────────────────────────────────────────┘
```

## 🏃‍♂️ **Strava Data Collection Flow**

```
┌─────────────────┐
│   Strava API    │
│                 │
│ • Activities    │
│ • Photos        │
│ • Comments      │
│ • Polylines     │
└─────────┬───────┘
          │ HTTP Requests
          ▼
┌─────────────────┐
│  HTTP Client    │
│                 │
│ • Rate Limiting │
│ • Error Handling│
│ • Retry Logic   │
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│SmartStravaCache │
│                 │
│ • Smart Merge   │
│ • Rich Data     │
│ • Cache TTL     │
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│ AsyncProcessor  │
│                 │
│ • Music Detect  │
│ • Photo Process │
│ • Format Data   │
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│   Cache Store   │
│                 │
│ • JSON Files    │
│ • In-Memory     │
│ • Backups       │
└─────────────────┘
```

## 💰 **Fundraising Data Collection Flow**

```
┌─────────────────┐
│  JustGiving     │
│   Website       │
│                 │
│ • HTML Content  │
│ • Donation Data │
│ • Progress Info │
└─────────┬───────┘
          │ HTTP GET
          ▼
┌─────────────────┐
│  HTTP Client    │
│                 │
│ • Respectful    │
│   Scraping      │
│ • Error Handling│
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│SmartFundraising │
│     Cache       │
│                 │
│ • HTML Parsing  │
│ • Data Extract  │
│ • Smart Merge   │
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│ AsyncProcessor  │
│                 │
│ • Format Dates  │
│ • Clean Data    │
│ • Anonymize     │
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│   Cache Store   │
│                 │
│ • JSON Files    │
│ • In-Memory     │
│ • Backups       │
└─────────────────┘
```

## 🎵 **Music Detection Flow**

```
┌─────────────────┐
│  Activity Data  │
│                 │
│ • Description   │
│ • Comments      │
│ • Name          │
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│ AsyncProcessor  │
│                 │
│ • Extract Text  │
│ • Search Terms  │
│ • Clean Data    │
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│   Deezer API    │
│                 │
│ • Track Search  │
│ • Artist Match  │
│ • Widget HTML   │
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│ Enhanced Data   │
│                 │
│ • Music Info    │
│ • Widget HTML   │
│ • Detection     │
└─────────────────┘
```

## 🌐 **API Request Flow**

```
┌─────────────────┐
│   Frontend      │
│   (Browser)     │
│                 │
│ • Demo Page     │
│ • API Calls     │
│ • Data Display  │
└─────────┬───────┘
          │ HTTP Request
          ▼
┌─────────────────┐
│ Security        │
│ Middleware      │
│                 │
│ • API Key Check │
│ • Rate Limiting │
│ • Domain Valid  │
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│  API Endpoint   │
│                 │
│ • Route Handler │
│ • Data Retrieval│
│ • Processing    │
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│   Cache Layer   │
│                 │
│ • Data Lookup   │
│ • TTL Check     │
│ • Smart Merge   │
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│ AsyncProcessor  │
│                 │
│ • Enhance Data  │
│ • Format Output │
│ • Parallel Proc │
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│   JSON Response │
│                 │
│ • Formatted     │
│ • Cached        │
│ • Optimized     │
└─────────────────┘
```

## 🔄 **Cache Management Flow**

```
┌─────────────────┐
│   New Data      │
│   Available     │
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│ Smart Merge     │
│                 │
│ • Compare Data  │
│ • Preserve Rich │
│ • Update Basic  │
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│ Cache Update    │
│                 │
│ • In-Memory     │
│ • File System   │
│ • Backup Create │
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│ Cache Validation│
│                 │
│ • Integrity     │
│ • TTL Check     │
│ • Cleanup       │
└─────────────────┘
```

## 🚀 **Performance Optimization Flow**

```
┌─────────────────┐
│   Request       │
│   Arrives       │
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│ Cache Check     │
│                 │
│ • In-Memory     │
│ • TTL Valid?    │
│ • Hit/Miss      │
└─────────┬───────┘
          │
    ┌─────┴─────┐
    │           │
    ▼           ▼
┌─────────┐ ┌─────────┐
│Cache Hit│ │Cache Miss│
│         │ │         │
│• Fast   │ │• Process│
│• Return │ │• Update │
└─────────┘ └─────────┘
```

## 🔐 **Security Flow**

```
┌─────────────────┐
│   API Request   │
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│ API Key Check   │
│                 │
│ • Header Valid? │
│ • Key Correct?  │
└─────────┬───────┘
          │
    ┌─────┴─────┐
    │           │
    ▼           ▼
┌─────────┐ ┌─────────┐
│ Valid   │ │Invalid  │
│         │ │         │
│• Continue│ │• 401    │
│• Process │ │• Reject │
└─────────┘ └─────────┘
```

This comprehensive overview shows how all components work together to create a robust, scalable system for collecting, processing, and delivering fitness and fundraising data.
