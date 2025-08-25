#!/usr/bin/env python3
"""
Daily MLB Data Updater
Comprehensive script to update team strength, pitcher stats, and bullpen data daily
"""

import requests
import json
import os
import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Any
import statistics

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DailyMLBDataUpdater:
    """Updates core MLB data files daily"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.mlb_api_base = "https://statsapi.mlb.com/api/v1"
        self.current_season = 2025
        
        # Ensure data directory exists
        os.makedirs(self.data_dir, exist_ok=True)
        
        # File paths
        self.team_strength_file = os.path.join(self.data_dir, "master_team_strength.json")
        self.pitcher_stats_file = os.path.join(self.data_dir, "master_pitcher_stats.json")
        self.bullpen_stats_file = os.path.join(self.data_dir, "bullpen_stats.json")
        
        # Team name mappings for consistency
        self.team_name_map = {
            "Arizona D-backs": "Arizona Diamondbacks",
            "Chi White Sox": "Chicago White Sox", 
            "Chi Cubs": "Chicago Cubs",
            "LA Angels": "Los Angeles Angels",
            "LA Dodgers": "Los Angeles Dodgers",
            "NY Yankees": "New York Yankees",
            "NY Mets": "New York Mets",
            "SD Padres": "San Diego Padres",
            "SF Giants": "San Francisco Giants",
            "TB Rays": "Tampa Bay Rays",
            "WSH Nationals": "Washington Nationals"
        }
    
    def normalize_team_name(self, name: str) -> str:
        """Normalize team names for consistency"""
        return self.team_name_map.get(name, name)
    
    def fetch_team_standings(self) -> Dict[str, float]:
        """Fetch current team standings and calculate strength ratings"""
        logger.info("🏆 Fetching team standings for strength calculations...")
        
        try:
            # Get standings
            url = f"{self.mlb_api_base}/standings?leagueId=103,104&season={self.current_season}"
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            team_stats = {}
            
            # Process all divisions
            for record in data.get('records', []):
                for team_record in record.get('teamRecords', []):
                    team_name = team_record.get('team', {}).get('name', '')
                    team_name = self.normalize_team_name(team_name)
                    
                    wins = team_record.get('wins', 0)
                    losses = team_record.get('losses', 0)
                    runs_scored = team_record.get('runsScored', 0)
                    runs_allowed = team_record.get('runsAllowed', 0)
                    
                    # Calculate strength based on run differential and win percentage
                    total_games = wins + losses
                    if total_games > 0:
                        win_pct = wins / total_games
                        run_diff_per_game = (runs_scored - runs_allowed) / total_games if total_games > 0 else 0
                        
                        # Combine win percentage and run differential for strength
                        # Normalize to roughly -0.1 to +0.1 range
                        strength = (win_pct - 0.5) * 0.4 + (run_diff_per_game / 10)
                        team_stats[team_name] = round(strength, 3)
            
            logger.info(f"✅ Calculated strength for {len(team_stats)} teams")
            return team_stats
            
        except Exception as e:
            logger.error(f"❌ Error fetching team standings: {e}")
            # Return empty dict to use existing data
            return {}
    
    def fetch_pitcher_stats(self) -> Dict[str, Dict[str, Any]]:
        """Fetch current pitcher statistics"""
        logger.info("⚾ Fetching pitcher statistics...")
        
        try:
            # Get all active players
            url = f"{self.mlb_api_base}/sports/1/players?season={self.current_season}"
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            pitcher_stats = {}
            pitcher_count = 0
            
            # Get all players who are pitchers
            for player in data.get('people', []):
                player_id = str(player.get('id', ''))
                player_name = player.get('fullName', '')
                
                # Check if this is a pitcher
                position = player.get('primaryPosition', {}).get('abbreviation', '')
                if position not in ['P', 'SP', 'RP', 'CP']:
                    continue
                
                try:
                    # Get detailed stats for this pitcher
                    stats_url = f"{self.mlb_api_base}/people/{player_id}/stats?stats=season&group=pitching&season={self.current_season}"
                    stats_response = requests.get(stats_url, timeout=10)
                    stats_response.raise_for_status()
                    stats_data = stats_response.json()
                    
                    # Extract pitching stats
                    for stat_group in stats_data.get('stats', []):
                        for split in stat_group.get('splits', []):
                            stat = split.get('stat', {})
                            team_data = split.get('team', {})
                            team_name = self.normalize_team_name(team_data.get('name', ''))
                            
                            era = float(stat.get('era', 999))
                            whip = float(stat.get('whip', 9.99))
                            innings_pitched = float(stat.get('inningsPitched', 0))
                            strikeouts = int(stat.get('strikeOuts', 0))
                            walks = int(stat.get('baseOnBalls', 0))
                            games_started = int(stat.get('gamesStarted', 0))
                            wins = int(stat.get('wins', 0))
                            losses = int(stat.get('losses', 0))
                            
                            # Only include pitchers with meaningful innings
                            if innings_pitched > 1.0:
                                pitcher_stats[player_id] = {
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
                                pitcher_count += 1
                                
                                if pitcher_count % 50 == 0:
                                    logger.info(f"📊 Processed {pitcher_count} pitchers...")
                
                except Exception as e:
                    logger.debug(f"Could not get stats for pitcher {player_name}: {e}")
                    continue
            
            logger.info(f"✅ Fetched stats for {len(pitcher_stats)} pitchers")
            return pitcher_stats
            
        except Exception as e:
            logger.error(f"❌ Error fetching pitcher stats: {e}")
            return {}
    
    def calculate_bullpen_stats(self, pitcher_stats: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Calculate bullpen quality stats for all teams"""
        logger.info("🎯 Calculating bullpen statistics...")
        
        # Group relievers by team
        team_relievers = {}
        
        for pitcher_id, stats in pitcher_stats.items():
            team = stats.get('team', '')
            games_started = stats.get('games_started', 0)
            innings_pitched = stats.get('innings_pitched', 0)
            
            # Consider as reliever if few starts and meaningful innings
            if games_started < 5 and innings_pitched > 5:
                if team not in team_relievers:
                    team_relievers[team] = []
                
                era = stats.get('era', 999)
                whip = stats.get('whip', 9.99)
                
                # Cap extreme values
                era = min(era, 15.0)
                whip = min(whip, 5.0)
                
                team_relievers[team].append({
                    'name': stats.get('name', ''),
                    'era': era,
                    'whip': whip,
                    'innings_pitched': innings_pitched
                })
        
        # Calculate team bullpen quality factors
        bullpen_stats = {}
        
        for team, relievers in team_relievers.items():
            if not relievers:
                continue
            
            # Weight by innings pitched
            total_weighted_innings = sum(r['innings_pitched'] for r in relievers)
            
            if total_weighted_innings > 0:
                # Calculate weighted averages
                weighted_era = sum(r['era'] * r['innings_pitched'] for r in relievers) / total_weighted_innings
                weighted_whip = sum(r['whip'] * r['innings_pitched'] for r in relievers) / total_weighted_innings
                
                # Convert to quality factor (lower ERA/WHIP = higher quality)
                # League average ERA ~4.00, WHIP ~1.30
                era_factor = 4.0 / max(weighted_era, 1.0)  # Avoid division by zero
                whip_factor = 1.3 / max(weighted_whip, 0.5)
                
                # Combine factors (ERA weighted more heavily)
                quality_factor = (era_factor * 0.7 + whip_factor * 0.3)
                
                # Normalize to reasonable range (0.8 to 1.5)
                quality_factor = max(0.8, min(1.5, quality_factor))
                
                bullpen_stats[team] = {
                    'quality_factor': round(quality_factor, 3),
                    'weighted_era': round(weighted_era, 2),
                    'weighted_whip': round(weighted_whip, 3),
                    'reliever_count': len(relievers),
                    'total_innings': round(total_weighted_innings, 1),
                    'last_updated': datetime.now().isoformat()
                }
        
        logger.info(f"✅ Calculated bullpen stats for {len(bullpen_stats)} teams")
        return bullpen_stats
    
    def update_team_strength(self) -> bool:
        """Update team strength data"""
        logger.info("🔄 Updating team strength data...")
        
        try:
            new_strength = self.fetch_team_standings()
            
            if new_strength:
                # Create backup of existing data
                if os.path.exists(self.team_strength_file):
                    backup_file = f"{self.team_strength_file}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    os.rename(self.team_strength_file, backup_file)
                    logger.info(f"📁 Backup created: {backup_file}")
                
                # Save new data
                with open(self.team_strength_file, 'w') as f:
                    json.dump(new_strength, f, indent=2)
                
                logger.info(f"✅ Team strength data updated successfully")
                return True
            else:
                logger.warning("⚠️ No new team strength data available - keeping existing")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error updating team strength: {e}")
            return False
    
    def update_pitcher_stats(self) -> bool:
        """Update pitcher statistics data"""
        logger.info("🔄 Updating pitcher statistics...")
        
        try:
            new_stats = self.fetch_pitcher_stats()
            
            if new_stats:
                # Create backup of existing data
                if os.path.exists(self.pitcher_stats_file):
                    backup_file = f"{self.pitcher_stats_file}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    os.rename(self.pitcher_stats_file, backup_file)
                    logger.info(f"📁 Backup created: {backup_file}")
                
                # Save new data
                with open(self.pitcher_stats_file, 'w') as f:
                    json.dump(new_stats, f, indent=2)
                
                logger.info(f"✅ Pitcher stats updated successfully")
                return True
            else:
                logger.warning("⚠️ No new pitcher stats available - keeping existing")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error updating pitcher stats: {e}")
            return False
    
    def update_bullpen_stats(self) -> bool:
        """Update bullpen statistics data"""
        logger.info("🔄 Updating bullpen statistics...")
        
        try:
            # Load current pitcher stats (updated or existing)
            if os.path.exists(self.pitcher_stats_file):
                with open(self.pitcher_stats_file, 'r') as f:
                    pitcher_stats = json.load(f)
            else:
                logger.error("❌ No pitcher stats available for bullpen calculation")
                return False
            
            # Calculate new bullpen stats
            new_bullpen = self.calculate_bullpen_stats(pitcher_stats)
            
            if new_bullpen:
                # Create backup of existing data
                if os.path.exists(self.bullpen_stats_file):
                    backup_file = f"{self.bullpen_stats_file}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    os.rename(self.bullpen_stats_file, backup_file)
                    logger.info(f"📁 Backup created: {backup_file}")
                
                # Save new data
                with open(self.bullpen_stats_file, 'w') as f:
                    json.dump(new_bullpen, f, indent=2)
                
                logger.info(f"✅ Bullpen stats updated successfully")
                return True
            else:
                logger.warning("⚠️ No bullpen stats calculated - keeping existing")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error updating bullpen stats: {e}")
            return False
    
    def update_all_data(self) -> Dict[str, bool]:
        """Update all data files and return success status"""
        logger.info("🚀 Starting comprehensive MLB data update...")
        
        results = {
            'team_strength': False,
            'pitcher_stats': False,
            'bullpen_stats': False
        }
        
        # Update in order of dependency
        results['team_strength'] = self.update_team_strength()
        results['pitcher_stats'] = self.update_pitcher_stats()
        results['bullpen_stats'] = self.update_bullpen_stats()
        
        # Summary
        successful_updates = sum(results.values())
        logger.info(f"📊 Update Summary: {successful_updates}/3 successful")
        
        for update_type, success in results.items():
            status = "✅" if success else "❌"
            logger.info(f"   {status} {update_type}")
        
        return results

def main():
    """Main execution function"""
    logger.info("🎯 Daily MLB Data Updater Starting")
    logger.info(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    updater = DailyMLBDataUpdater()
    results = updater.update_all_data()
    
    if all(results.values()):
        logger.info("🎉 All data updates completed successfully!")
    elif any(results.values()):
        logger.info("⚠️ Partial data update completed")
    else:
        logger.error("❌ All data updates failed")
    
    return results

if __name__ == "__main__":
    main()
