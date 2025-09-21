# API Security Documentation

## Protected Endpoints

Both the Strava Integration and Fundraising Scraper APIs now have API key protection on sensitive endpoints to prevent unauthorized access.

### Protected Endpoints

#### Strava Integration API
- `POST /api/strava-integration/refresh-cache` - Manual cache refresh
- `POST /api/strava-integration/cleanup-backups` - Backup cleanup

#### Fundraising Scraper API  
- `POST /api/fundraising/refresh` - Manual data refresh
- `POST /api/fundraising/cleanup-backups` - Backup cleanup

### Public Endpoints (No API Key Required)

#### Strava Integration API
- `GET /api/strava-integration/` - Project info
- `GET /api/strava-integration/health` - Health check
- `GET /api/strava-integration/activities` - Get activities data
- `GET /api/strava-integration/demo` - Demo page

#### Fundraising Scraper API
- `GET /api/fundraising/` - Project info
- `GET /api/fundraising/health` - Health check
- `GET /api/fundraising/data` - Get fundraising data
- `GET /api/fundraising/donations` - Get donations for scrolling

## Using Protected Endpoints

### API Key Configuration

The API keys are configured via environment variables:

```bash
# Strava API Key
export STRAVA_API_KEY="your-secure-strava-key"

# Fundraising API Key  
export FUNDRAISING_API_KEY="your-secure-fundraising-key"
```

**Default Keys (for development only):**
- Strava: `demo-key-2024`
- Fundraising: `demo-key-2024`

⚠️ **Important:** Change these default keys in production!

### Making Authenticated Requests

Include the API key in the `X-API-Key` header:

```bash
# Strava API
curl -X POST "http://localhost:8000/api/strava-integration/refresh-cache" \
  -H "X-API-Key: your-strava-api-key"

# Fundraising API
curl -X POST "http://localhost:8000/api/fundraising/refresh" \
  -H "X-API-Key: your-fundraising-api-key"
```

### JavaScript Example

```javascript
// Refresh Strava cache
fetch('/api/strava-integration/refresh-cache', {
  method: 'POST',
  headers: {
    'X-API-Key': 'your-strava-api-key',
    'Content-Type': 'application/json'
  }
})
.then(response => response.json())
.then(data => console.log(data));

// Refresh fundraising data
fetch('/api/fundraising/refresh', {
  method: 'POST', 
  headers: {
    'X-API-Key': 'your-fundraising-api-key',
    'Content-Type': 'application/json'
  }
})
.then(response => response.json())
.then(data => console.log(data));
```

## Error Responses

### Missing API Key
```json
{
  "detail": "API key required"
}
```
**Status:** 401 Unauthorized

### Invalid API Key
```json
{
  "detail": "Invalid API key"
}
```
**Status:** 403 Forbidden

## Security Benefits

1. **Prevents Abuse:** Unauthorized users cannot trigger expensive operations
2. **Rate Limiting Protection:** Prevents overwhelming the APIs with requests
3. **Data Safety:** Protects backup cleanup operations from accidental deletion
4. **Resource Management:** Prevents unnecessary server load

## Production Recommendations

1. **Use Strong API Keys:** Generate cryptographically secure random keys
2. **Environment Variables:** Store keys in environment variables, not code
3. **Key Rotation:** Regularly rotate API keys
4. **Monitoring:** Log and monitor API key usage
5. **HTTPS Only:** Always use HTTPS in production
6. **Rate Limiting:** Consider additional rate limiting per API key

## Example Production Setup

```bash
# Generate secure API keys
export STRAVA_API_KEY=$(openssl rand -hex 32)
export FUNDRAISING_API_KEY=$(openssl rand -hex 32)

# Start the server
uvicorn multi_project_api:app --host 0.0.0.0 --port 8000
```

