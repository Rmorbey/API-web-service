# Multi-Project API Service

A production-ready FastAPI service that provides multiple integrated services including activity data integration (via GPX import from Google Sheets) and JustGiving fundraising tracking with smart caching, security, and monitoring features.

## 📚 Documentation

### **Project-Specific Documentation**
- **[🏃‍♂️ Fundraising Tracking App](docs/FUNDRAISING-TRACKING-APP/README.md)** - Complete project overview, timeline, and implementation guide
- **[🏗️ Multi-Project API Service](docs/MULTI-PROJECT-API-SERVICE/)** - Reusable infrastructure components and architecture

### **Quick Navigation**
- **[📊 Documentation Index](docs/README.md)** - Complete documentation navigation
- **[🚀 Implementation Guide](docs/FUNDRAISING-TRACKING-APP/OPTION_3_IMPLEMENTATION_GUIDE.md)** - Step-by-step deployment guide
- **[🔐 DigitalOcean Setup](docs/FUNDRAISING-TRACKING-APP/DIGITALOCEAN_SECRETS_SETUP.md)** - Environment variables and secrets configuration
- **[📚 API Documentation](docs/FUNDRAISING-TRACKING-APP/API_DOCUMENTATION.md)** - Complete endpoint reference
- **[📥 GPX Import Guide](docs/GPX_IMPORT_GUIDE.md)** - How to import activity data from Google Sheets

### **Project-Specific READMEs**
- **[🏃‍♂️ Fundraising Tracking App README](docs/FUNDRAISING-TRACKING-APP/README.md)** - Main project documentation
- **[🏗️ Multi-Project API Service README](docs/MULTI-PROJECT-API-SERVICE/)** - Infrastructure documentation
- **[📁 Codebase Explanations](docs/FUNDRAISING-TRACKING-APP/codebase-explanation/)** - Detailed code walkthroughs
- **[🏗️ System Architecture](docs/MULTI-PROJECT-API-SERVICE/codebase-explanation/)** - Technical architecture details

## Features

### Activity Data Integration
- **GPX Import**: Import activity data from Google Sheets containing GPX file references
- **Smart Caching**: Intelligent caching strategy with in-memory optimization
- **Music Integration**: Automatic music detection from activity descriptions with Deezer widgets
- **Interactive Maps**: GPS route visualization with Jawg Maps integration
- **Manual Import**: Import activities on-demand via API endpoint

### Fundraising Tracking
- **Web Scraping**: Automated JustGiving page scraping every 15 minutes
- **Hybrid Caching**: Supabase persistence with local JSON fallback
- **Smart Data Merging**: Preserves individual donations while updating totals
- **Real-time Updates**: Live fundraising progress tracking

### Security & Monitoring
- **API Key Protection**: Secure endpoints with API key authentication
- **Security Headers**: Comprehensive security headers and input validation
- **Health Checks**: System health monitoring and metrics
- **Production Ready**: Docker containerization and deployment configuration

## Quick Start

### Prerequisites

- Python 3.9+
- Google Sheets API credentials (for GPX import)
- Google Drive API access (for fetching GPX files)
- Jawg Maps API token (optional, for map visualization)

### Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy environment configuration:
   ```bash
   cp projects/fundraising_tracking_app/env.example projects/fundraising_tracking_app/.env
   ```
4. Configure your API keys in `.env`:
   - `GOOGLE_SHEETS_SPREADSHEET_ID` - Your Google Sheets ID
   - `GOOGLE_SHEETS_CREDENTIALS_FILE` - Path to Google API credentials
   - `ACTIVITY_API_KEY` - API key for activity endpoints
   - `JAWG_ACCESS_TOKEN` - Jawg Maps token (optional)
5. Run the service:
   ```bash
   python multi_project_api.py
   ```

### Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up -d

# Or build and run manually
docker build -t activity-api .
docker run -p 8000:8000 --env-file .env activity-api
```

## API Endpoints

### Core Endpoints
- `GET /api/activity-integration/` - Project information
- `GET /api/activity-integration/health` - Health check
- `GET /api/activity-integration/metrics` - System metrics
- `GET /api/activity-integration/feed` - Activity feed (up to 500 activities)

### Activity Data Endpoints
- `GET /api/activity-integration/activities/{id}/map` - GPS data for maps
- `GET /api/activity-integration/activities/{id}/comments` - Activity comments
- `GET /api/activity-integration/activities/{id}/music` - Music widget
- `GET /api/activity-integration/activities/{id}/complete` - Complete activity data

### GPX Import Endpoints
- `POST /api/activity-integration/gpx/import-from-sheets` - Import activities from Google Sheets
- `POST /api/activity-integration/gpx/upload` - Upload GPX file directly
- `POST /api/activity-integration/gpx/refresh` - Refresh activities from sheets

### Map Endpoints
- `GET /api/activity-integration/map-tiles/{z}/{x}/{y}` - Map tiles proxy
- `GET /api/activity-integration/jawg-token` - Jawg token status

### Fundraising Endpoints
- `GET /api/fundraising/data` - Fundraising data and progress
- `GET /api/fundraising/donations` - Individual donations list
- `GET /api/fundraising/health` - Fundraising service health

### Demo Endpoints (Development Only)
- `GET /fundraising-demo` - Fundraising progress demo page

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ACTIVITY_API_KEY` | Activity API authentication key | Required |
| `GOOGLE_SHEETS_SPREADSHEET_ID` | Google Sheets spreadsheet ID | Required |
| `GOOGLE_SHEETS_CREDENTIALS_FILE` | Path to Google API credentials JSON | Required |
| `GOOGLE_SHEETS_TOKEN_FILE` | Path to Google API token file | Required |
| `JAWG_ACCESS_TOKEN` | Jawg Maps API token | Optional |
| `ACTIVITY_CACHE_HOURS` | Cache duration in hours | 8 |
| `SUPABASE_URL` | Supabase project URL | Required |
| `SUPABASE_ANON_KEY` | Supabase anonymous key | Required |
| `SUPABASE_SERVICE_KEY` | Supabase service role key | Required |
| `FUNDRAISING_API_KEY` | Fundraising API authentication key | Required |
| `TZ` | Server timezone | Europe/London |

### Cache Configuration

The service uses a hybrid caching strategy:
- **Supabase Cache**: Persistent database storage for production
- **Local JSON Cache**: Fallback for development and resilience
- **In-Memory Cache**: 5-minute TTL for fast access
- **Manual Import**: Activities are imported manually via GPX import endpoint

## Data Flow

### Activity Data Import Process

1. **GPX Files**: Activity data is stored as GPX files (in Google Drive or server)
2. **Google Sheets**: Reference GPX files in a Google Sheet with activity metadata
3. **API Import**: Call `POST /api/activity-integration/gpx/import-from-sheets`
4. **Processing**: System fetches GPX files, parses GPS data, calculates metrics
5. **Storage**: Activities stored in Supabase cache with music detection and map generation
6. **API Access**: Frontend consumes data via `/api/activity-integration/feed`

See [GPX Import Guide](docs/GPX_IMPORT_GUIDE.md) for detailed instructions.

## Security Features

- **Security Headers**: X-Content-Type-Options, X-Frame-Options, X-XSS-Protection
- **CORS Protection**: Restricted to specific domains
- **Input Validation**: Parameter validation and sanitization
- **API Key Security**: Server-side proxy for third-party API keys

## Monitoring

### Health Checks
- `GET /api/activity-integration/health` - Basic health status
- `GET /api/activity-integration/metrics` - Detailed system metrics

### Logging
- Structured logging with timestamps
- Performance metrics tracking
- Error logging with context
- Log files: `activity_integration.log`

## Development

### Running Tests
```bash
# Test the API endpoints
curl http://localhost:8000/api/activity-integration/health

# Test activity feed
curl http://localhost:8000/api/activity-integration/feed?limit=5
```

### Frontend Integration
The service includes demo pages for testing:
- **Fundraising Demo**: `http://localhost:8000/fundraising-demo` - Progress tracker
- No direct API calls from frontend - all data served through backend cache

## Production Deployment

### Docker
```bash
docker-compose up -d
```

### Manual Deployment
1. Set up reverse proxy (nginx)
2. Configure SSL certificates
3. Set up monitoring and logging
4. Configure backup for cache files

## Troubleshooting

### Common Issues

1. **401 Unauthorized**: Check API key configuration
2. **GPX Import Fails**: Verify Google Sheets API credentials and permissions
3. **Cache Issues**: Clear cache or restart service
4. **Map Tiles Not Loading**: Check Jawg token configuration

### Logs
Check the application logs for detailed error information:
```bash
tail -f activity_integration.log
```

## License

This project is for personal use and educational purposes.
