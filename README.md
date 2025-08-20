# MLB Betting Prediction System

A comprehensive MLB betting prediction system with real-time data integration, live game status updates, doubleheader detection, and comprehensive monitoring.

## 🚀 Features

- **Real-time MLB Data**: Live game status updates and pitcher information
- **Doubleheader Detection**: Automatically detects and displays multiple games for same teams
- **Unified Betting Engine**: Advanced betting recommendations with real market lines
- **System Monitoring**: Complete health monitoring with performance metrics
- **Auto-tuning**: Background optimization system
- **Clean UI**: Professional dashboard with team logos and live updates

## 🌐 Render Deployment

This system is configured for easy deployment on Render.com:

### Prerequisites
- Render.com account
- GitHub repository

### Deployment Steps
1. Push code to GitHub repository
2. Connect Render to your GitHub repo
3. Configure as Web Service with:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `bash start.sh`
   - **Environment**: Python 3.11+

### Environment Variables (Optional)
- `PORT`: Automatically set by Render
- `FLASK_ENV`: Set to "production" in start.sh

## 🔧 Local Development

## Directory Structure

```
MLB-Betting/
├── app.py                                    # Main Flask application
├── comprehensive_tuned_engine.py            # Core prediction engine
├── enhanced_master_predictions_service.py   # Master prediction service
├── enhanced_mlb_fetcher.py                  # Enhanced MLB data fetcher
├── integrated_closing_lines.py              # Betting lines integration
├── live_mlb_data.py                         # Live MLB data fetching
├── team_assets.json                         # Team information and assets
├── team_assets_utils.py                     # Team assets utilities
├── team_name_normalizer.py                  # Team name normalization
├── data/                                    # Data files
│   ├── master_predictions.json             # Cached predictions
│   ├── master_betting_lines.json           # Betting lines data
│   ├── todays_complete_games.json          # Today's enhanced game data
│   └── ...                                 # Other data files
├── templates/                               # HTML templates
│   ├── index.html                          # Main dashboard
│   └── historical.html                     # Historical analysis
├── engines/                                # Prediction engines
│   └── ultra_fast_engine.py               # Fast prediction engine
└── utils/                                  # Utility modules
    ├── automated_closing_lines_fetcher.py  # Automated betting lines
    ├── comprehensive_closing_lines.py      # Closing lines management
    └── ...                                 # Other utilities
```

## Key Features

- **Real-time MLB Data**: Live game data with enhanced pitcher information
- **Betting Lines Integration**: Real-time odds and closing lines
- **Comprehensive Predictions**: Win probabilities, total runs, and betting recommendations
- **Self-contained**: No external dependencies outside this directory
- **Enhanced Pitcher Data**: Real pitcher names instead of "TBD"
- **Live Dashboard**: Web interface for real-time betting analysis

## Usage

1. Start the Flask server:
   ```bash
   python app.py
   ```

2. Open browser to `http://localhost:5000`

3. View today's games with predictions and betting recommendations

## API Endpoints

- `/api/today-games` - Get today's games with enhanced data
- `/api/prediction/<away_team>/<home_team>` - Get prediction for specific game
- `/api/live-status` - Get live system status
- `/` - Main dashboard interface

## Data Sources

- **MLB API**: Official game data and pitcher information
- **OddsAPI**: Real-time betting lines and odds
- **Enhanced Data**: Processed and enriched game information
