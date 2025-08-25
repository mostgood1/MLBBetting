# Render Deployment Configuration

## Overview
This document provides instructions for deploying the MLB Betting prediction system on Render.com with full feature parity to the local development environment.

## Required Environment Variables

To enable all features including weather/park integration, configure the following environment variables in your Render service:

### Essential Variables
```
FLASK_ENV=production
PORT=10000
PYTHONUNBUFFERED=1
```

### Weather Integration (Optional but Recommended)
```
WEATHER_API_KEY=your_openweathermap_api_key_here
```

**Note:** Weather integration enhances prediction accuracy by incorporating real-time weather conditions and ballpark factors. Without this key, the system will use default weather conditions but will still function fully.

## Getting a Weather API Key

1. Visit [OpenWeatherMap](https://openweathermap.org/api)
2. Sign up for a free account
3. Navigate to "API keys" in your account dashboard
4. Copy your API key and add it to Render environment variables

## Deployment Verification

After deployment, your Render site should:
1. **Load the main predictions interface** (not historical analysis)
2. **Display today's games with betting recommendations**
3. **Show comprehensive optimized predictions** including:
   - Moneyline recommendations
   - Spread predictions
   - Over/Under totals with weather/park factors
   - Confidence scores and expected values

## Features Enabled

✅ **Comprehensive Model**: Optimized configuration with actual game results analysis  
✅ **Weather Integration**: Real-time weather data for all 30 MLB ballparks  
✅ **Park Factors**: Ballpark-specific scoring adjustments  
✅ **Daily Automation**: Automated data refresh and prediction generation  
✅ **Performance Monitoring**: Enhanced tracking and metrics  
✅ **Responsive UI**: Mobile-friendly interface with team colors and logos

## Troubleshooting

### Site Shows Historical Analysis Instead of Main Predictions
- **Fixed**: Procfile has been corrected to serve `app:app` instead of `historical_analysis_app:app`

### Weather Data Not Loading
- Verify `WEATHER_API_KEY` is set in Render environment variables
- Check API key validity at OpenWeatherMap dashboard

### No Predictions Displaying
- Ensure the service has sufficient memory (recommend 512MB or higher)
- Check Render logs for any startup errors
- Verify all dependencies in requirements.txt are properly installed

## Support Files

- `Procfile`: Correctly configured to serve main application
- `requirements.txt`: All necessary dependencies included
- `app.py`: Properly configured with Render port handling
- Configuration files: Comprehensive optimized settings included

## Local vs Render Parity

The Render deployment is configured to provide identical functionality to local development:
- Same prediction model and configurations
- Same data sources and processing
- Same UI/UX experience
- Same performance optimizations

Both environments use the comprehensive optimized model with weather/park integration for maximum prediction accuracy.
