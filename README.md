# Multi-Project API Service

A production-ready FastAPI service that provides multiple integrated services including Strava data integration and JustGiving fundraising tracking with smart caching, security, and monitoring features.

## 📚 Documentation

All comprehensive documentation is available in the [`docs/`](docs/) folder:

- **[Implementation Guide](docs/OPTION_3_IMPLEMENTATION_GUIDE.md)** - Complete step-by-step implementation guide
- **[DigitalOcean Setup](docs/DIGITALOCEAN_SECRETS_SETUP.md)** - Environment variables and secrets configuration
- **[Domain Configuration](docs/DOMAIN_SETUP_GUIDE.md)** - Domain routing and reverse proxy setup
- **[Production Deployment](docs/PRODUCTION_DEPLOYMENT.md)** - Production optimization and deployment
- **[Security Guide](docs/API_SECURITY.md)** - Security implementation and best practices
- **[Repository Analysis](docs/REPOSITORY_FILE_ANALYSIS.md)** - File structure and optimization analysis

## Features

### Strava Integration
- **Smart Caching**: Intelligent caching strategy with in-memory optimization
- **Music Integration**: Automatic music detection from activity descriptions with Deezer widgets
- **Interactive Maps**: GPS route visualization with Jawg Maps integration
- **Rate Limiting**: Built-in API rate limiting and retry logic

### Fundraising Tracking
- **Web Scraping**: Automated JustGiving page scraping every 15 minutes
- **Smart Data Merging**: Preserves individual donations while updating totals
- **Backup System**: Automatic backup creation and restoration
- **Real-time Updates**: Live fundraising progress tracking

### Security & Monitoring
- **API Key Protection**: Secure endpoints with API key authentication
- **Security Headers**: Comprehensive security headers and input validation
- **Health Checks**: System health monitoring and metrics
- **Production Ready**: Docker containerization and deployment configuration

## Quick Start

### Prerequisites

- Python 3.9+
- Strava API credentials
- Jawg Maps API token (optional)

### Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy environment configuration:
   ```bash
   cp env.example .env
   ```
4. Configure your API keys in `.env`
5. Run the service:
   ```bash
   python multi_project_api.py
   ```

### Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up -d

# Or build and run manually
docker build -t strava-api .
docker run -p 8000:8000 --env-file .env strava-api
```

## API Endpoints

### Core Endpoints
- `GET /api/strava-integration/` - Project information
- `GET /api/strava-integration/health` - Health check
- `GET /api/strava-integration/metrics` - System metrics
- `GET /api/strava-integration/feed` - Activity feed
- `GET /api/strava-integration/test-feed` - Test data feed

### Activity Endpoints
- `GET /api/strava-integration/activities/{id}/map` - GPS data for maps
- `GET /api/strava-integration/activities/{id}/comments` - Activity comments
- `GET /api/strava-integration/activities/{id}/music` - Music widget
- `GET /api/strava-integration/activities/{id}/complete` - Complete activity data

### Map Endpoints
- `GET /api/strava-integration/map-tiles/{z}/{x}/{y}` - Map tiles proxy
- `GET /api/strava-integration/jawg-token` - Jawg token status

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `STRAVA_ACCESS_TOKEN` | Strava API access token | Required |
| `STRAVA_REFRESH_TOKEN` | Strava API refresh token | Required |
| `STRAVA_CLIENT_ID` | Strava API client ID | Required |
| `STRAVA_CLIENT_SECRET` | Strava API client secret | Required |
| `JAWG_ACCESS_TOKEN` | Jawg Maps API token | Optional |
| `STRAVA_CACHE_HOURS` | Cache duration in hours | 6 |

### Cache Configuration

The service uses a multi-layer caching strategy:
- **File Cache**: Persistent JSON cache with configurable TTL
- **In-Memory Cache**: 5-minute TTL for fast access
- **API Rate Limiting**: 200 calls/15min, 2000/day

## Security Features

- **Security Headers**: X-Content-Type-Options, X-Frame-Options, X-XSS-Protection
- **CORS Protection**: Restricted to specific domains
- **Input Validation**: Parameter validation and sanitization
- **API Key Security**: Server-side proxy for third-party API keys

## Monitoring

### Health Checks
- `GET /api/strava-integration/health` - Basic health status
- `GET /api/strava-integration/metrics` - Detailed system metrics

### Logging
- Structured logging with timestamps
- Performance metrics tracking
- Error logging with context
- Log files: `strava_integration.log`

## Development

### Running Tests
```bash
# Test the API endpoints
curl http://localhost:8000/api/strava-integration/health

# Test with sample data
curl http://localhost:8000/api/strava-integration/test-feed?limit=5
```

### Frontend Integration
The service is designed to work with the included demo frontend:
- Access at `http://localhost:8000/demo`
- No direct Strava API calls from frontend
- All data served through backend cache

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

1. **401 Unauthorized**: Check Strava token configuration
2. **Rate Limited**: Wait for rate limit reset or check API usage
3. **Cache Issues**: Clear cache file or restart service
4. **Map Tiles Not Loading**: Check Jawg token configuration

### Logs
Check the application logs for detailed error information:
```bash
tail -f strava_integration.log
```

## License

This project is for personal use and educational purposes.