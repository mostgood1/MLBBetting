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

# Get today's date in various formats
TODAY_HYPHEN=$(date +%Y-%m-%d)      # 2025-08-27
TODAY_UNDERSCORE=$(date +%Y_%m_%d)  # 2025_08_27

echo "📅 Today's date: $TODAY_HYPHEN (underscore: $TODAY_UNDERSCORE)"

# Try to use any betting lines data that might be in the repository
# This allows the system to use actual betting lines instead of generating fake ones
for file in data/real_betting_lines_*.json; do
    if [ -f "$file" ]; then
        echo "Found betting lines data: $file"
        # Create a copy with today's format if none exists for today
        today_file="data/real_betting_lines_${TODAY_UNDERSCORE}.json"
        if [ ! -f "$today_file" ]; then
            cp "$file" "$today_file" 2>/dev/null || true
            echo "Copied betting lines to today's format: $today_file"
        fi
        break
    fi
done

# Try to use any games data that might be in the repository
# This allows the system to use actual games instead of requiring API calls
GAMES_FOUND=false
for file in data/games_*.json; do
    if [ -f "$file" ]; then
        echo "Found games data: $file"
        # Create a copy with today's format if none exists for today
        today_games_file="data/games_${TODAY_HYPHEN}.json"
        if [ ! -f "$today_games_file" ]; then
            cp "$file" "$today_games_file" 2>/dev/null || true
            echo "Copied games to today's format: $today_games_file"
            GAMES_FOUND=true
        else
            echo "Today's games file already exists: $today_games_file"
            GAMES_FOUND=true
        fi
        break
    fi
done

# If no games were found, create a minimal structure to prevent errors
if [ "$GAMES_FOUND" = false ]; then
    echo "⚠️ No games data found - creating fallback structure"
    echo '[]' > "data/games_${TODAY_HYPHEN}.json"
fi

# Also try starting pitchers
for file in data/starting_pitchers_*.json; do
    if [ -f "$file" ]; then
        echo "Found pitchers data: $file"
        today_pitchers_file="data/starting_pitchers_${TODAY_UNDERSCORE}.json"
        if [ ! -f "$today_pitchers_file" ]; then
            cp "$file" "$today_pitchers_file" 2>/dev/null || true
            echo "Copied pitchers to today's format: $today_pitchers_file"
        fi
        break
    fi
done

# List what data files we have for debugging
echo "📂 Available data files for today:"
ls -la data/*${TODAY_HYPHEN}* 2>/dev/null || echo "No hyphen format files"
ls -la data/*${TODAY_UNDERSCORE}* 2>/dev/null || echo "No underscore format files"

# Create historical betting lines cache if it doesn't exist
echo '{}' > data/historical_betting_lines_cache.json 2>/dev/null || true

# Force initial data population if needed
echo "🔄 Ensuring data is populated for startup..."
if [ -f "data/games_${TODAY_HYPHEN}.json" ]; then
    echo "✅ Games data available"
else
    echo "❌ No games data - app may show no games until data is loaded"
fi

# Set environment variables for Render
export FLASK_APP=app.py
export FLASK_ENV=production
export PORT=${PORT:-5000}
export FORCE_DATA_REFRESH=true

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
echo "🌐 Starting MLB Betting System on port $PORT..."
exec gunicorn --bind 0.0.0.0:$PORT --workers 1 --timeout 120 --max-requests 1000 --preload app:app
