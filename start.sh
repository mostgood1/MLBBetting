#!/bin/bash

# Render startup script for MLB Betting System
echo "🚀 Starting MLB Betting System on Render..."

# Create data directory if it doesn't exist
mkdir -p data
mkdir -p logs
mkdir -p monitoring_data

# Create essential data files if they don't exist
echo '{}' > data/unified_predictions_cache.json 2>/dev/null || true
echo '{}' > data/betting_accuracy_analysis.json 2>/dev/null || true
echo '{}' > data/daily_dashboard_stats.json 2>/dev/null || true

# Try to use any betting lines data that might be in the repository
# This allows the system to use actual betting lines instead of generating fake ones
for file in data/real_betting_lines_*.json; do
    if [ -f "$file" ]; then
        echo "Found betting lines data: $file"
        # Create a copy with today's format if none exists for today
        today_file="data/real_betting_lines_$(date +%Y_%m_%d).json"
        if [ ! -f "$today_file" ]; then
            cp "$file" "$today_file" 2>/dev/null || true
            echo "Copied betting lines to today's format: $today_file"
        fi
        break
    fi
done

# Try to use any games data that might be in the repository
# This allows the system to use actual games instead of requiring API calls
for file in data/games_*.json; do
    if [ -f "$file" ]; then
        echo "Found games data: $file"
        # Create a copy with today's format if none exists for today
        today_games_file="data/games_$(date +%Y-%m-%d).json"
        if [ ! -f "$today_games_file" ]; then
            cp "$file" "$today_games_file" 2>/dev/null || true
            echo "Copied games to today's format: $today_games_file"
        fi
        break
    fi
done

# Create historical betting lines cache if it doesn't exist
echo '{}' > data/historical_betting_lines_cache.json 2>/dev/null || true

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
echo "🌐 Starting Historical Analysis App on port $PORT..."
exec gunicorn --bind 0.0.0.0:$PORT --workers 1 --timeout 120 --max-requests 1000 --preload historical_analysis_app:app
