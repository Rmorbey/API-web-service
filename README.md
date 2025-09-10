# My FastApi backend Web Service

This will provide my frontend projects with a REST API Web Service that will handle all of my API calls and data. I'm planning on using Cursor Ai to learn how to use Ai tools to my advantage while coding. This is a personal learning project.

## APIs in development
- Fundraising tracking app API.

## APIs that have been implemented
- Work in Progress

## Tickets for Fundraising tracking app API
- Use cursor to build the backend REST APIs using python and FastApi.
- Using a webscraper to collect specific data from my fundraising page.
- Using Strava Api to collect data, sanatize and deliver to my fundraising tracking app frontend.

---

# Strava API Service

A FastAPI backend service that collects, sanitizes, and serves Strava activity data to frontend applications.

## Features

- **Strava OAuth Integration**: Secure authentication with Strava API
- **Data Sanitization**: Clean and validate raw Strava data
- **Data Formatting**: Transform data for optimal frontend consumption
- **CORS Support**: Ready for React and other frontend frameworks
- **RESTful API**: Clean endpoints for activities and authentication
- **Error Handling**: Comprehensive error handling and validation

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Strava API Configuration

1. Go to [Strava API Settings](https://www.strava.com/settings/api)
2. Create a new application
3. Note your Client ID and Client Secret
4. Set the Authorization Callback Domain to `localhost` (for development)

### 3. Environment Variables

Copy `env.example` to `.env` and fill in your Strava credentials:

```bash
cp env.example .env
```

Edit `.env` with your actual values:
```env
STRAVA_CLIENT_ID=your_actual_client_id
STRAVA_CLIENT_SECRET=your_actual_client_secret
STRAVA_REDIRECT_URI=http://localhost:8000/auth/strava/callback
```

### 4. Run the Service

```bash
python main.py
```

Or with uvicorn:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The service will be available at `http://localhost:8000`

## API Endpoints

### Authentication

- `GET /auth/strava` - Get Strava OAuth authorization URL
- `POST /auth/strava/callback` - Exchange authorization code for access token

### Activities

- `GET /activities` - Get paginated list of activities
- `GET /activities/{activity_id}` - Get specific activity by ID

### Utility

- `GET /` - API information and available endpoints
- `GET /health` - Health check endpoint

## Frontend Integration

### 1. OAuth Flow

```javascript
// 1. Get authorization URL
const authResponse = await fetch('http://localhost:8000/auth/strava');
const { auth_url } = await authResponse.json();

// 2. Redirect user to Strava
window.location.href = auth_url;

// 3. Handle callback (in your React app)
// Strava will redirect back with a 'code' parameter
const urlParams = new URLSearchParams(window.location.search);
const code = urlParams.get('code');

// 4. Exchange code for token
const tokenResponse = await fetch('http://localhost:8000/auth/strava/callback', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ code })
});

const { access_token, refresh_token } = await tokenResponse.json();
```

### 2. Fetching Activities

```javascript
// Store the access token securely (e.g., in localStorage or state)
const accessToken = 'your_access_token_here';

// Fetch activities
const activitiesResponse = await fetch('http://localhost:8000/activities', {
  headers: {
    'Authorization': `Bearer ${accessToken}`
  }
});

const { activities } = await activitiesResponse.json();
console.log(activities);
```

### 3. React Component Example

```jsx
import React, { useState, useEffect } from 'react';

function StravaActivities() {
  const [activities, setActivities] = useState([]);
  const [loading, setLoading] = useState(false);

  const fetchActivities = async (accessToken) => {
    setLoading(true);
    try {
      const response = await fetch('http://localhost:8000/activities', {
        headers: {
          'Authorization': `Bearer ${accessToken}`
        }
      });
      const data = await response.json();
      setActivities(data.activities);
    } catch (error) {
      console.error('Error fetching activities:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h2>Strava Activities</h2>
      {loading ? (
        <p>Loading activities...</p>
      ) : (
        <div>
          {activities.map(activity => (
            <div key={activity.id} className="activity-card">
              <h3>{activity.name}</h3>
              <p>Distance: {activity.distance_km} km</p>
              <p>Duration: {activity.duration_minutes} minutes</p>
              <p>Pace: {activity.pace_min_per_km} min/km</p>
              <p>Date: {activity.date} at {activity.time}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default StravaActivities;
```

## Data Structure

### Formatted Activity Data

The API returns activities in a clean, frontend-friendly format:

```json
{
  "id": 123456789,
  "name": "Morning Run",
  "distance_km": 5.2,
  "duration_minutes": 32.5,
  "pace_min_per_km": 6.2,
  "elevation_gain_m": 45,
  "activity_type": "Run",
  "date": "2024-01-15",
  "time": "07:30",
  "heart_rate_avg": 145,
  "heart_rate_max": 165,
  "cadence_avg": 175,
  "power_avg": null,
  "calories": 320
}
```

## Error Handling

The API returns appropriate HTTP status codes and error messages:

- `400 Bad Request` - Invalid request parameters
- `401 Unauthorized` - Invalid or missing access token
- `404 Not Found` - Activity not found
- `500 Internal Server Error` - Server-side errors

## Development

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run tests
pytest
```

### API Documentation

Once running, visit `http://localhost:8000/docs` for interactive API documentation powered by Swagger UI.

## Security Notes

- Store access tokens securely in your frontend application
- Implement token refresh logic for expired tokens
- Use HTTPS in production
- Consider implementing rate limiting for production use

## Troubleshooting

### Common Issues

1. **CORS Errors**: Ensure your frontend origin is in the `allow_origins` list
2. **Authentication Failures**: Verify your Strava API credentials
3. **Token Expiry**: Implement token refresh logic
4. **Rate Limiting**: Strava has API rate limits; implement proper error handling

### Debug Mode

Enable debug logging by setting the log level:

```bash
uvicorn main:app --reload --log-level debug
```
