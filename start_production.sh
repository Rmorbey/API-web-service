#!/bin/bash

# Production API Web Service Startup Script
# This script is for production deployment with proper security settings

echo "🚀 Starting API Web Service (Production Mode)..."

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found. Please run: python -m venv .venv"
    exit 1
fi

# Activate virtual environment
echo "📦 Activating virtual environment..."
source .venv/bin/activate

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found. Please create one with your API keys."
    exit 1
fi

# Load environment variables
echo "🔑 Loading environment variables..."
export $(cat .env | grep -v '^#' | xargs)

# Force production environment
echo "🔧 Setting production environment..."
export ENVIRONMENT=production

# Install/update dependencies
echo "📋 Installing production dependencies..."
pip install -r requirements.txt --quiet

# Start the server in production mode (no reload, proper logging)
echo "🌐 Starting production server on http://0.0.0.0:8000"
echo "📊 API Documentation: http://0.0.0.0:8000/docs"
echo "🚫 Demo Page: http://0.0.0.0:8000/demo (DISABLED)"
echo "🚫 Fundraising Demo: http://0.0.0.0:8000/fundraising-demo (DISABLED)"
echo "🔧 Environment: PRODUCTION (Demo endpoints disabled)"
echo ""

# Production settings: single worker for rate-limited APIs, proper logging
# Single worker prevents duplicate API calls to Strava (1000 calls/day limit)
uvicorn multi_project_api:app --host 0.0.0.0 --port 8000 --workers 1 --access-log --log-level info
