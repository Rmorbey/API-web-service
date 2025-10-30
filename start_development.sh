#!/bin/bash

# Development API Web Service Startup Script
# This script is for development with demo endpoints enabled

echo "🚀 Starting API Web Service (Development Mode)..."

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

# Force development environment
echo "🔧 Setting development environment..."
export ENVIRONMENT=development

# Install/update dependencies
echo "📋 Installing development dependencies..."
pip install -r requirements.txt --quiet

# Start the server in development mode (with reload, debug logging)
echo "🌐 Starting development server on http://0.0.0.0:8000"
echo "📊 API Documentation: http://0.0.0.0:8000/docs"
echo "💰 Fundraising Demo: http://0.0.0.0:8000/fundraising-demo (ENABLED)"
echo "🔧 Environment: DEVELOPMENT (Demo endpoints enabled)"
echo ""

# Development settings: single worker with reload for development
uvicorn multi_project_api:app --host 0.0.0.0 --port 8000 --workers 1 --reload --access-log --log-level debug
