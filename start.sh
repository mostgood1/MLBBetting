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

# Start the application with Gunicorn
echo "🌐 Starting Gunicorn server on port $PORT..."
exec gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 120 --preload app:app
