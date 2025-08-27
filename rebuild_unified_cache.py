#!/usr/bin/env python3
"""
Rebuild the unified predictions cache from all available data sources
This will reconstruct the cache with data from 8/15 onwards
"""

import json
import os
import glob
from datetime import datetime, timedelta

def rebuild_unified_cache():
    """Rebuild the unified predictions cache from historical data and daily files"""
    
    print("🔄 Rebuilding unified predictions cache...")
    
    # Load existing historical cache data (8/7 to 8/16)
    historical_file = "data/historical_predictions_cache.json"
    historical_data = {}
    
    if os.path.exists(historical_file):
        with open(historical_file, 'r') as f:
            historical_data = json.load(f)
        print(f"📊 Loaded historical cache with {len(historical_data)} dates")
    
    # Initialize unified cache structure
    unified_cache = {
        "predictions_by_date": {},
        "last_updated": datetime.now().isoformat(),
        "rebuild_timestamp": datetime.now().isoformat(),
        "data_sources": {
            "historical_cache": list(historical_data.keys()),
            "individual_files": []
        }
    }
    
    # Add historical data from 8/15 onwards to unified cache
    for date_str, date_data in historical_data.items():
        if date_str >= "2025-08-15":
            print(f"📅 Adding historical data for {date_str}")
            
            # Convert historical format to unified format
            unified_games = {}
            cached_predictions = date_data.get('cached_predictions', {})
            
            for game_key, game_data in cached_predictions.items():
                # Create unified game key
                away_team = game_data.get('away_team', '')
                home_team = game_data.get('home_team', '')
                unified_key = f"{away_team}_vs_{home_team}".replace(' ', '_')
                
                unified_games[unified_key] = {
                    "away_team": away_team,
                    "home_team": home_team,
                    "game_date": date_str,
                    "predictions": {
                        "home_win_prob": 1.0 - game_data.get('away_win_prob', 0.5),
                        "away_win_prob": game_data.get('away_win_prob', 0.5),
                        "predicted_home_score": game_data.get('predicted_home_score', 0),
                        "predicted_away_score": game_data.get('predicted_away_score', 0),
                        "predicted_total_runs": game_data.get('predicted_total_runs', 0)
                    },
                    "actual_results": {
                        "actual_home_score": game_data.get('actual_home_score'),
                        "actual_away_score": game_data.get('actual_away_score'),
                        "actual_total_runs": game_data.get('actual_total_runs'),
                        "prediction_error": game_data.get('prediction_error'),
                        "winner_correct": game_data.get('winner_correct')
                    },
                    "betting_lines": game_data.get('betting_lines', {}),
                    "pitcher_info": game_data.get('pitcher_quality', {}),
                    "source": "historical_cache"
                }
            
            unified_cache["predictions_by_date"][date_str] = {
                "games": unified_games,
                "timestamp": date_data.get('timestamp', ''),
                "total_games": len(unified_games),
                "source": "historical_cache"
            }
    
    # Now add data from individual daily files (8/17 onwards)
    start_date = datetime(2025, 8, 17)
    end_date = datetime(2025, 8, 27)
    current_date = start_date
    
    while current_date <= end_date:
        date_str = current_date.strftime('%Y-%m-%d')
        date_underscore = current_date.strftime('%Y_%m_%d')
        
        print(f"🔍 Looking for data files for {date_str}")
        
        # Look for games file
        games_file = f"data/games_{date_str}.json"
        betting_file = f"data/betting_recommendations_{date_underscore}.json"
        
        if os.path.exists(games_file):
            print(f"📁 Found games file: {games_file}")
            
            with open(games_file, 'r') as f:
                games_data = json.load(f)
            
            # Load betting recommendations if available
            betting_data = {}
            if os.path.exists(betting_file):
                print(f"📁 Found betting file: {betting_file}")
                with open(betting_file, 'r') as f:
                    betting_file_data = json.load(f)
                    # Extract games from the betting recommendations structure
                    betting_data = betting_file_data.get('games', {})
            
            # Convert to unified format
            unified_games = {}
            
            for game in games_data:
                away_team = game.get('away_team', '')
                home_team = game.get('home_team', '')
                unified_key = f"{away_team}_vs_{home_team}".replace(' ', '_')
                
                # Find matching betting recommendation
                game_betting = {}
                for bet_game_key, bet_data in betting_data.items():
                    if isinstance(bet_data, dict):  # Ensure it's a dict
                        if (bet_data.get('away_team') == away_team and 
                            bet_data.get('home_team') == home_team):
                            game_betting = bet_data
                            break
                
                unified_games[unified_key] = {
                    "away_team": away_team,
                    "home_team": home_team,
                    "game_date": date_str,
                    "game_time": game.get('game_time', ''),
                    "away_pitcher": game.get('away_pitcher', 'TBD'),
                    "home_pitcher": game.get('home_pitcher', 'TBD'),
                    "predictions": game_betting.get('predictions', {}),
                    "betting_lines": game_betting.get('betting_lines', {}),
                    "recommendations": game_betting.get('recommendations', []) or game_betting.get('value_bets', []),
                    "pitcher_info": game_betting.get('pitcher_info', {}),
                    "meta": game_betting.get('meta', {}),
                    "source": "daily_files"
                }
            
            unified_cache["predictions_by_date"][date_str] = {
                "games": unified_games,
                "timestamp": datetime.now().isoformat(),
                "total_games": len(unified_games),
                "source": "daily_files",
                "games_file": games_file,
                "betting_file": betting_file if os.path.exists(betting_file) else None
            }
            
            unified_cache["data_sources"]["individual_files"].append(date_str)
        
        current_date += timedelta(days=1)
    
    # Write the rebuilt cache
    cache_file = "data/unified_predictions_cache.json"
    with open(cache_file, 'w') as f:
        json.dump(unified_cache, f, indent=2)
    
    total_dates = len(unified_cache["predictions_by_date"])
    total_games = sum(date_data["total_games"] for date_data in unified_cache["predictions_by_date"].values())
    
    print(f"✅ Rebuilt unified cache successfully!")
    print(f"📊 Total dates: {total_dates}")
    print(f"🎯 Total games: {total_games}")
    print(f"📅 Date range: {min(unified_cache['predictions_by_date'].keys())} to {max(unified_cache['predictions_by_date'].keys())}")
    print(f"💾 Cache size: {os.path.getsize(cache_file)} bytes")
    
    return unified_cache

if __name__ == "__main__":
    rebuilt_cache = rebuild_unified_cache()
