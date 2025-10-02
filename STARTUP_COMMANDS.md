# 🚀 API Web Service Startup Commands

This document provides simple commands to start the API web service for development and production.

## Quick Development Startup (Recommended)

For quick testing and development, use this one-liner command:

```bash
./start_dev.sh
```

Or run the command directly:
```bash
source .venv/bin/activate && export STRAVA_API_KEY=test-key-123 && export FUNDRAISING_API_KEY=test-fundraising-key-456 && uvicorn multi_project_api:app --host 0.0.0.0 --port 8000 --reload
```

## Full Development Startup

For development with all environment variables loaded from `.env`:

```bash
./start_server.sh
```

## Production Startup

For production deployment:

```bash
./start_production.sh
```

## What Each Command Does

### `./start_dev.sh`
- ✅ Activates virtual environment
- ✅ Sets test API keys
- ✅ Starts server with auto-reload
- ✅ Perfect for testing and development

### `./start_server.sh`
- ✅ Activates virtual environment
- ✅ Loads all environment variables from `.env`
- ✅ Maps `STRAVA_ACCESS_TOKEN` to `STRAVA_API_KEY`
- ✅ Starts server with auto-reload
- ✅ Good for development with real API keys

### `./start_production.sh`
- ✅ Activates virtual environment
- ✅ Loads all environment variables from `.env`
- ✅ Starts server with multiple workers
- ✅ Production logging and security settings
- ✅ No auto-reload (production mode)

## Access Points

Once the server is running, you can access:

- **API Documentation**: http://localhost:8000/docs
- **Demo Page**: http://localhost:8000/demo
- **Health Check**: http://localhost:8000/api/strava-integration/health
- **Main API**: http://localhost:8000/

## Troubleshooting

If you get environment variable errors:
1. Make sure `.venv` directory exists
2. Make sure `.env` file exists with your API keys
3. Use `./start_dev.sh` for quick testing with test keys

## Environment Variables Required

The server expects these environment variables:
- `STRAVA_API_KEY` (or `STRAVA_ACCESS_TOKEN` in .env)
- `FUNDRAISING_API_KEY`
- `JAWG_ACCESS_TOKEN` (for maps)
- `STRAVA_CLIENT_ID` and `STRAVA_CLIENT_SECRET` (for OAuth)
