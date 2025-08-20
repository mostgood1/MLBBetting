#!/usr/bin/env python3
"""
Fetch Today's Starting Pitchers
===============================

Get actual starting pitcher assignments for today's games from MLB API.
"""

import requests
import json
import logging
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
    
    if not pitcher_data:
        logger.error("No pitcher data to update predictions with")
        return False
    
    logger.info("🔄 Updating predictions with real starting pitchers...")
    
    try:
        # Load current predictions
        with open('unified_predictions_cache.json', 'r') as f:
            predictions_data = json.load(f)
        
        today = datetime.now().strftime('%Y-%m-%d')
        
        if today not in predictions_data['predictions_by_date']:
            logger.error(f"No predictions found for {today}")
            return False
        
        # Create a mapping of games to pitchers
        pitcher_mapping = {}
        for game in pitcher_data:
            key = f"{game['away_team']} @ {game['home_team']}"
            pitcher_mapping[key] = {
                'away_pitcher': game['away_pitcher'],
                'home_pitcher': game['home_pitcher']
            }
        
        # Update predictions with real pitchers
        updated_count = 0
        games = predictions_data['predictions_by_date'][today]['games']
        
        for game_key, game_data in games.items():
            # Try exact match first
            if game_key in pitcher_mapping:
                game_data['away_pitcher'] = pitcher_mapping[game_key]['away_pitcher']
                game_data['home_pitcher'] = pitcher_mapping[game_key]['home_pitcher']
                updated_count += 1
                logger.info(f"Updated {game_key} with pitchers: {pitcher_mapping[game_key]['away_pitcher']} vs {pitcher_mapping[game_key]['home_pitcher']}")
            else:
                # Try partial matching
                for pitcher_key, pitcher_info in pitcher_mapping.items():
                    # Extract team names for comparison
                    pred_away = game_data.get('away_team', '')
                    pred_home = game_data.get('home_team', '')
                    
                    pitcher_parts = pitcher_key.split(' @ ')
                    if len(pitcher_parts) == 2:
                        pitcher_away = pitcher_parts[0]
                        pitcher_home = pitcher_parts[1]
                        
                        # Check if teams match (accounting for variations)
                        if (pred_away.lower() in pitcher_away.lower() or pitcher_away.lower() in pred_away.lower()) and \
                           (pred_home.lower() in pitcher_home.lower() or pitcher_home.lower() in pred_home.lower()):
                            game_data['away_pitcher'] = pitcher_info['away_pitcher']
                            game_data['home_pitcher'] = pitcher_info['home_pitcher']
                            updated_count += 1
                            logger.info(f"Updated {game_key} (matched to {pitcher_key}) with pitchers: {pitcher_info['away_pitcher']} vs {pitcher_info['home_pitcher']}")
                            break
        
        # Update metadata
        predictions_data['metadata']['last_pitcher_update'] = datetime.now().isoformat()
        predictions_data['metadata']['pitcher_update_date'] = today
        predictions_data['metadata']['pitchers_updated_count'] = updated_count
        
        # Save updated predictions
        with open('unified_predictions_cache.json', 'w') as f:
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
