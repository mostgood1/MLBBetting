#!/bin/bash

# Render startup script for MLB Betting System
echo "🚀 Starting MLB Betting System on Render..."

# Create data directory if it doesn't exist
mkdir -p data
mkdir -p logs
mkdir -p monitoring_data

# Set environment variables for Render
export FLASK_APP=app.py
export FLASK_ENV=production
export PORT=${PORT:-5000}

# Ensure Python path includes current directory
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Check if gunicorn is available
if ! command -v gunicorn &> /dev/null; then
    echo "❌ Gunicorn not found! Trying to install..."
    pip install gunicorn==21.2.0
fi

# Verify gunicorn is working
echo "🔍 Checking Gunicorn installation..."
gunicorn --version || exit 1

# Start the application with Gunicorn
echo "🌐 Starting Gunicorn server on port $PORT..."
exec gunicorn --bind 0.0.0.0:$PORT --workers 1 --timeout 120 --max-requests 1000 --preload app:app
