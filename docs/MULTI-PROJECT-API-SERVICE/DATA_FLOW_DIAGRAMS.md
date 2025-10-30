# 📊 Data Flow Diagrams

## 🔄 **Complete System Data Flow**

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Google Sheets  │    │  JustGiving     │    │   Deezer API    │
│   (GPX Files)   │    │   (External)    │    │   (External)    │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          ▼                      ▼                      ▼
┌─────────────────┐    ┌─────────────────┐              │
│ ActivityCache   │    │SmartFundraising │              │
│                 │    │     Cache       │              │
│ • GPX Import    │    │ • Web Scraping  │              │
│ • Data Parse    │    │ • Data Extract  │              │
│ • Supabase Store│    │ • Smart Merge   │              │
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
│ • Supabase Database (Persistence)                             │
│ • Activity Data (GPX Import)                                   │
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

## 🏃‍♂️ **Activity Data Import Flow (GPX)**

```
┌─────────────────┐
│  Google Sheets  │
│                 │
│ • GPX File IDs  │
│ • Activity Meta │
│ • Descriptions  │
└─────────┬───────┘
          │ Manual Import
          ▼
┌─────────────────┐
│  HTTP Client    │
│                 │
│ • Google Drive  │
│ • Google Sheets │
│ • File Fetching │
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│  GPX Parser     │
│                 │
│ • Parse GPX     │
│ • Extract GPS   │
│ • Calculate Data│
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│ ActivityCache   │
│                 │
│ • Store Data    │
│ • Music Detect  │
│ • Process Data  │
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
│  Supabase Store │
│                 │
│ • Database      │
│ • Persistence   │
│ • Fast Access   │
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
