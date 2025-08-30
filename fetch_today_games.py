#!/usr/bin/env python3
"""
Real fetch_today_games script - fetches today's MLB games using enhanced_mlb_fetcher

This script fetches today's MLB games and saves them to data directory for the automation pipeline.
"""
import sys
import os
import json
from datetime import datetime
from pathlib import Path

# Add current directory to path for imports
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from enhanced_mlb_fetcher import fetch_todays_complete_games

def main():
    """Fetch today's games and save to data directory"""
    try:
        today = datetime.now().strftime('%Y-%m-%d')
        print(f"Fetching today's games for {today}")
        
        # Fetch games using our enhanced MLB fetcher
        games = fetch_todays_complete_games(today)
        
        # Ensure data directory exists
        data_dir = current_dir / "data"
        data_dir.mkdir(exist_ok=True)
        
        # Populate probable pitcher fields from enhanced fetcher output as a default
        # (These will be overwritten by real starting_pitchers file if present below)
        for game in games:
            try:
                if 'away_probable_pitcher' not in game or not game['away_probable_pitcher']:
                    if game.get('away_pitcher') and game.get('away_pitcher') != 'TBD':
                        game['away_probable_pitcher'] = game['away_pitcher']
                if 'home_probable_pitcher' not in game or not game['home_probable_pitcher']:
                    if game.get('home_pitcher') and game.get('home_pitcher') != 'TBD':
                        game['home_probable_pitcher'] = game['home_pitcher']
            except Exception:
                # Non-fatal; continue best-effort
                pass

        # Try to merge with real starting pitcher data
        pitcher_file = data_dir / f"starting_pitchers_{today.replace('-', '_')}.json"
        pitcher_data = {}
        
        if pitcher_file.exists():
            try:
                with open(pitcher_file, 'r') as f:
                    pitcher_info = json.load(f)
                    # Create lookup dictionary by team matchup
                    for game_info in pitcher_info.get('games', []):
                        key = f"{game_info['away_team']} @ {game_info['home_team']}"
                        pitcher_data[key] = {
                            'away_pitcher': game_info['away_pitcher'],
                            'home_pitcher': game_info['home_pitcher']
                        }
                print(f"Loaded real starting pitcher data for {len(pitcher_data)} matchups")
            except Exception as e:
                print(f"Warning: Could not load pitcher data: {e}")
        
        # Merge pitcher data with games
        for game in games:
            away_team = game.get('away_team', '')
            home_team = game.get('home_team', '')
            matchup_key = f"{away_team} @ {home_team}"
            
            if matchup_key in pitcher_data:
                game['away_probable_pitcher'] = pitcher_data[matchup_key]['away_pitcher']
                game['home_probable_pitcher'] = pitcher_data[matchup_key]['home_pitcher']
                print(f"Updated pitchers for {matchup_key}: {pitcher_data[matchup_key]['away_pitcher']} vs {pitcher_data[matchup_key]['home_pitcher']}")
        
        # Save games to data file
        games_file = data_dir / f"games_{today}.json"
        with open(games_file, 'w') as f:
            json.dump(games, f, indent=2)
        
        print(f"Successfully fetched and saved {len(games)} games to {games_file}")
        
        # Also print summary for logging
        for game in games:
            away_team = game.get('away_team', 'Unknown')
            home_team = game.get('home_team', 'Unknown')
            game_time = game.get('game_time', 'TBD')
            away_pitcher = game.get('away_probable_pitcher', 'TBD')
            home_pitcher = game.get('home_probable_pitcher', 'TBD')
            print(f"  {away_team} @ {home_team} at {game_time} (P: {away_pitcher} vs {home_pitcher})")
        
        return True
        
    except Exception as e:
        print(f"Error fetching today's games: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
