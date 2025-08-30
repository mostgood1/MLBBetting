#!/usr/bin/env python3
"""
Fetch Today's Starting Pitchers
===============================

Get actual starting pitcher assignments for today's games from MLB API.
"""

import requests
import json
import logging
import os
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fetch_todays_starting_pitchers():
    """Fetch starting pitchers for today's MLB games"""
    
    today = datetime.now().strftime('%Y-%m-%d')
    logger.info(f"🎯 Fetching starting pitchers for {today}")
    
    # MLB Stats API endpoint for today's games
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={today}&hydrate=probablePitcher,team"
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        games_with_pitchers = []
        
        if 'dates' in data and len(data['dates']) > 0:
            for date_data in data['dates']:
                if 'games' in date_data:
                    for game in date_data['games']:
                        # Extract team names
                        away_team = game['teams']['away']['team']['name']
                        home_team = game['teams']['home']['team']['name']
                        
                        # Extract probable pitchers
                        away_pitcher = "TBD"
                        home_pitcher = "TBD"
                        
                        if 'probablePitcher' in game['teams']['away']:
                            if game['teams']['away']['probablePitcher']:
                                away_pitcher = game['teams']['away']['probablePitcher']['fullName']
                        
                        if 'probablePitcher' in game['teams']['home']:
                            if game['teams']['home']['probablePitcher']:
                                home_pitcher = game['teams']['home']['probablePitcher']['fullName']
                        
                        game_info = {
                            'away_team': away_team,
                            'home_team': home_team,
                            'away_pitcher': away_pitcher,
                            'home_pitcher': home_pitcher,
                            'game_key': f"{away_team} @ {home_team}"
                        }
                        
                        games_with_pitchers.append(game_info)
                        
                        logger.info(f"{away_team} @ {home_team}: {away_pitcher} vs {home_pitcher}")
        
        logger.info(f"✅ Found {len(games_with_pitchers)} games with pitcher assignments")
        
        # Save the pitcher data
        pitcher_data = {
            'date': today,
            'fetched_at': datetime.now().isoformat(),
            'games': games_with_pitchers
        }
        
        with open(f'data/starting_pitchers_{today.replace("-", "_")}.json', 'w') as f:
            json.dump(pitcher_data, f, indent=2)
        
        logger.info(f"💾 Saved pitcher data to data/starting_pitchers_{today.replace('-', '_')}.json")
        
        return games_with_pitchers
        
    except Exception as e:
        logger.error(f"❌ Error fetching starting pitchers: {e}")
        return []

def update_predictions_with_real_pitchers(pitcher_data):
    """Update today's predictions with real starting pitcher data"""
    try:
        # Load current predictions cache (append by date)
        cache_path_candidates = [
            'data/unified_predictions_cache.json',  # preferred
            'unified_predictions_cache.json'        # fallback
        ]
        cache_path = None
        predictions_data = {}
        for p in cache_path_candidates:
            if os.path.exists(p):
                cache_path = p
                try:
                    with open(p, 'r') as f:
                        predictions_data = json.load(f)
                except Exception:
                    predictions_data = {}
                break
        if cache_path is None:
            cache_path = cache_path_candidates[0]
        today = datetime.now().strftime('%Y-%m-%d')
        # Ensure structure
        if 'predictions_by_date' not in predictions_data:
            predictions_data['predictions_by_date'] = {}
        if today not in predictions_data['predictions_by_date']:
            logger.warning(f"No predictions found for {today} in cache. Skipping update.")
            # Still write out a metadata note so we can track the attempt
            predictions_data['predictions_by_date'][today] = {
                'games': {},
                'metadata': {
                    'last_pitcher_update': datetime.now().isoformat(),
                    'pitcher_update_date': today,
                    'pitchers_updated_count': 0
                }
            }
            with open(cache_path, 'w') as f:
                json.dump(predictions_data, f, indent=2)
            return False

        # Create a mapping of "Away Team @ Home Team" to pitchers
        def norm(name: str) -> str:
            return (name or '').lower()

        pitcher_mapping = {}
        for game in pitcher_data:
            key = f"{game['away_team']} @ {game['home_team']}"
            pitcher_mapping[norm(key)] = {
                'away_pitcher': game.get('away_pitcher', 'TBD') or 'TBD',
                'home_pitcher': game.get('home_pitcher', 'TBD') or 'TBD'
            }

        # Update predictions with real pitchers
        updated_count = 0
        day_data = predictions_data['predictions_by_date'][today]
        games = day_data.get('games', {})

        for game_key, game_data in games.items():
            # Try to build a flexible key from stored game data
            pred_away = game_data.get('away_team') or game_key.split('_vs_')[0].replace('_', ' ')
            pred_home = game_data.get('home_team') or game_key.split('_vs_')[-1].replace('_', ' ')
            lookup_keys = [
                f"{pred_away} @ {pred_home}",
                f"{pred_away} vs {pred_home}",
                game_key.replace('_vs_', ' @ ')
            ]
            found = False
            for lk in lookup_keys:
                pm = pitcher_mapping.get(norm(lk))
                if pm:
                    # Persist under pitcher_info for downstream consumers
                    pi = game_data.get('pitcher_info', {})
                    pi['away_pitcher_name'] = pm['away_pitcher']
                    pi['home_pitcher_name'] = pm['home_pitcher']
                    game_data['pitcher_info'] = pi
                    # Also mirror to flat fields for backward compatibility
                    game_data['away_pitcher'] = pm['away_pitcher']
                    game_data['home_pitcher'] = pm['home_pitcher']
                    updated_count += 1
                    found = True
                    logger.info(f"Updated pitchers for {pred_away} @ {pred_home}: {pm['away_pitcher']} vs {pm['home_pitcher']}")
                    break
            if not found:
                # leave as-is
                continue

        # Update metadata
        md = day_data.get('metadata', {})
        md['last_pitcher_update'] = datetime.now().isoformat()
        md['pitcher_update_date'] = today
        md['pitchers_updated_count'] = updated_count
        day_data['metadata'] = md

        # Save merged cache
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        with open(cache_path, 'w') as f:
            json.dump(predictions_data, f, indent=2)
        logger.info(f"✅ Updated {updated_count} games with real starting pitchers")
        return True

    except Exception as e:
        logger.error(f"❌ Error updating predictions with pitchers: {e}")
        return False

def main():
    """Main function"""
    logger.info("🎯 Starting Pitcher Update Process")
    
    # Step 1: Fetch today's starting pitchers
    pitcher_data = fetch_todays_starting_pitchers()
    
    if pitcher_data:
        # Step 2: Update predictions with real pitchers
        if update_predictions_with_real_pitchers(pitcher_data):
            logger.info("✅ Starting pitcher update complete!")
            logger.info("🔄 Ready to regenerate predictions with real pitcher data")
        else:
            logger.error("❌ Failed to update predictions with pitcher data")
    else:
        logger.error("❌ Failed to fetch starting pitcher data")

if __name__ == "__main__":
    main()
