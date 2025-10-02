#!/bin/bash

# Quick Development Startup - One-liner command
# This is the exact command format that works from our chat history

echo "🚀 Quick Development Startup..."
echo "🌐 Starting server on http://localhost:8000"
echo "🎯 Demo Page: http://localhost:8000/demo"
echo "Press Ctrl+C to stop the server"
echo ""

source .venv/bin/activate && export STRAVA_API_KEY=test-key-123 && export FUNDRAISING_API_KEY=test-fundraising-key-456 && uvicorn multi_project_api:app --host 0.0.0.0 --port 8000 --reload
