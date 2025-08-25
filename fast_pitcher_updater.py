#!/usr/bin/env python3
"""
Fast Pitcher Stats Updater
Lightweight script for frequent pitcher stats updates
"""

import requests
import json
import os
import logging
from datetime import datetime
from typing import Dict, Any, List

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FastPitcherUpdater:
    """Fast updater for pitcher statistics only"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.mlb_api_base = "https://statsapi.mlb.com/api/v1"
        self.current_season = 2025
        
        # File paths
        self.pitcher_stats_file = os.path.join(self.data_dir, "master_pitcher_stats.json")
        self.today_pitchers_file = os.path.join(self.data_dir, f"today_pitchers_{datetime.now().strftime('%Y_%m_%d')}.json")
        
        # Load existing pitcher data if available
        self.existing_pitchers = {}
        if os.path.exists(self.pitcher_stats_file):
            try:
                with open(self.pitcher_stats_file, 'r') as f:
                    self.existing_pitchers = json.load(f)
                logger.info(f"📊 Loaded {len(self.existing_pitchers)} existing pitchers")
            except Exception as e:
                logger.warning(f"⚠️ Could not load existing pitcher data: {e}")
    
    def get_todays_starting_pitchers(self) -> List[str]:
        """Get today's starting pitcher IDs"""
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            url = f"{self.mlb_api_base}/schedule?sportId=1&date={today}&hydrate=probablePitcher"
            
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            pitcher_ids = []
            
            for date_data in data.get('dates', []):
                for game in date_data.get('games', []):
                    # Get starting pitchers
                    if 'probablePitcher' in game:
                        away_pitcher = game.get('teams', {}).get('away', {}).get('probablePitcher')
                        home_pitcher = game.get('teams', {}).get('home', {}).get('probablePitcher')
                        
                        if away_pitcher:
                            pitcher_ids.append(str(away_pitcher.get('id', '')))
                        if home_pitcher:
                            pitcher_ids.append(str(home_pitcher.get('id', '')))
            
            logger.info(f"🎯 Found {len(pitcher_ids)} starting pitchers today")
            return pitcher_ids
            
        except Exception as e:
            logger.error(f"❌ Error getting today's pitchers: {e}")
            return []
    
    def update_pitcher_stats(self, pitcher_id: str) -> Dict[str, Any]:
        """Update stats for a specific pitcher"""
        try:
            # Get player info first
            player_url = f"{self.mlb_api_base}/people/{pitcher_id}"
            player_response = requests.get(player_url, timeout=10)
            player_response.raise_for_status()
            player_data = player_response.json()
            
            player_info = player_data.get('people', [{}])[0]
            player_name = player_info.get('fullName', '')
            
            # Get current season stats
            stats_url = f"{self.mlb_api_base}/people/{pitcher_id}/stats?stats=season&group=pitching&season={self.current_season}"
            stats_response = requests.get(stats_url, timeout=10)
            stats_response.raise_for_status()
            stats_data = stats_response.json()
            
            # Extract current stats
            for stat_group in stats_data.get('stats', []):
                for split in stat_group.get('splits', []):
                    stat = split.get('stat', {})
                    team_data = split.get('team', {})
                    team_name = team_data.get('name', '')
                    
                    era = float(stat.get('era', 999))
                    whip = float(stat.get('whip', 9.99))
                    innings_pitched = float(stat.get('inningsPitched', 0))
                    strikeouts = int(stat.get('strikeOuts', 0))
                    walks = int(stat.get('baseOnBalls', 0))
                    games_started = int(stat.get('gamesStarted', 0))
                    wins = int(stat.get('wins', 0))
                    losses = int(stat.get('losses', 0))
                    
                    return {
                        'name': player_name,
                        'team': team_name,
                        'era': era,
                        'whip': whip,
                        'strikeouts': strikeouts,
                        'walks': walks,
                        'innings_pitched': innings_pitched,
                        'games_started': games_started,
                        'wins': wins,
                        'losses': losses,
                        'last_updated': datetime.now().isoformat()
                    }
            
            logger.warning(f"⚠️ No stats found for pitcher {player_name}")
            return None
            
        except Exception as e:
            logger.error(f"❌ Error updating pitcher {pitcher_id}: {e}")
            return None
    
    def update_todays_pitchers(self) -> bool:
        """Update stats for today's starting pitchers"""
        logger.info("🔄 Updating today's starting pitcher stats...")
        
        try:
            # Get today's starting pitchers
            pitcher_ids = self.get_todays_starting_pitchers()
            
            if not pitcher_ids:
                logger.warning("⚠️ No starting pitchers found for today")
                return False
            
            updated_count = 0
            today_updates = {}
            
            # Update each pitcher
            for pitcher_id in pitcher_ids:
                updated_stats = self.update_pitcher_stats(pitcher_id)
                
                if updated_stats:
                    # Update existing pitcher data
                    self.existing_pitchers[pitcher_id] = updated_stats
                    today_updates[pitcher_id] = updated_stats
                    updated_count += 1
                    
                    logger.info(f"✅ Updated {updated_stats['name']} ({updated_stats['team']})")
            
            # Save updated master file
            if updated_count > 0:
                with open(self.pitcher_stats_file, 'w') as f:
                    json.dump(self.existing_pitchers, f, indent=2)
                
                # Save today's updates separately
                with open(self.today_pitchers_file, 'w') as f:
                    json.dump(today_updates, f, indent=2)
                
                logger.info(f"✅ Updated {updated_count}/{len(pitcher_ids)} pitchers")
                return True
            else:
                logger.warning("⚠️ No pitcher updates completed")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error updating today's pitchers: {e}")
            return False

def main():
    """Main execution for fast pitcher updates"""
    logger.info("⚡ Fast Pitcher Stats Updater Starting")
    logger.info(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    updater = FastPitcherUpdater()
    success = updater.update_todays_pitchers()
    
    if success:
        logger.info("🎉 Pitcher updates completed successfully!")
    else:
        logger.error("❌ Pitcher updates failed")
    
    return success

if __name__ == "__main__":
    main()
