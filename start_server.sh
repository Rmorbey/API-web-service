#!/bin/bash

# API Web Service Startup Script
# This script activates the virtual environment, loads environment variables, and starts the server

echo "🚀 Starting API Web Service..."

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found. Please run: python -m venv .venv"
    exit 1
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found. Please create one with your API keys."
    exit 1
fi

# Load environment variables from .env file
echo "🔑 Loading environment variables..."
export $(cat .env | grep -v '^#' | xargs)

# Set required API keys (using the format that works)
export STRAVA_API_KEY="${STRAVA_ACCESS_TOKEN:-test-key-123}"
export FUNDRAISING_API_KEY="test-fundraising-key-456"

# Start the server using the exact command format that works
echo "🌐 Starting server on http://localhost:8000"
echo "📊 API Documentation: http://localhost:8000/docs"
echo "🎯 Demo Page: http://localhost:8000/demo"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

source .venv/bin/activate && uvicorn multi_project_api:app --host 0.0.0.0 --port 8000 --reload
