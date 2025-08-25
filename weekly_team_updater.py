#!/usr/bin/env python3
"""
Weekly Team Strength Updater
Updates team strength ratings weekly based on recent performance
"""

import requests
import json
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Any

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class WeeklyTeamStrengthUpdater:
    """Updates team strength ratings weekly"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.mlb_api_base = "https://statsapi.mlb.com/api/v1"
        self.current_season = 2025
        
        # File paths
        self.team_strength_file = os.path.join(self.data_dir, "master_team_strength.json")
        
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
    
    def get_recent_team_performance(self, days_back: int = 14) -> Dict[str, Dict[str, Any]]:
        """Get recent team performance for strength calculation"""
        logger.info(f"📊 Analyzing team performance over last {days_back} days...")
        
        try:
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            start_str = start_date.strftime('%Y-%m-%d')
            end_str = end_date.strftime('%Y-%m-%d')
            
            # Get games for the period
            url = f"{self.mlb_api_base}/schedule?sportId=1&startDate={start_str}&endDate={end_str}&hydrate=team,linescore"
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            team_performance = {}
            
            # Process each game
            for date_data in data.get('dates', []):
                for game in date_data.get('games', []):
                    # Skip if game not finished
                    if game.get('status', {}).get('statusCode', '') != 'F':
                        continue
                    
                    teams = game.get('teams', {})
                    away_team = teams.get('away', {})
                    home_team = teams.get('home', {})
                    
                    away_name = self.normalize_team_name(away_team.get('team', {}).get('name', ''))
                    home_name = self.normalize_team_name(home_team.get('team', {}).get('name', ''))
                    
                    away_score = away_team.get('score', 0)
                    home_score = home_team.get('score', 0)
                    
                    # Initialize team stats if needed
                    for team_name in [away_name, home_name]:
                        if team_name not in team_performance:
                            team_performance[team_name] = {
                                'wins': 0,
                                'losses': 0,
                                'runs_scored': 0,
                                'runs_allowed': 0,
                                'games': 0
                            }
                    
                    # Update stats
                    if away_score > home_score:  # Away team wins
                        team_performance[away_name]['wins'] += 1
                        team_performance[home_name]['losses'] += 1
                    else:  # Home team wins
                        team_performance[home_name]['wins'] += 1
                        team_performance[away_name]['losses'] += 1
                    
                    # Update run stats
                    team_performance[away_name]['runs_scored'] += away_score
                    team_performance[away_name]['runs_allowed'] += home_score
                    team_performance[away_name]['games'] += 1
                    
                    team_performance[home_name]['runs_scored'] += home_score
                    team_performance[home_name]['runs_allowed'] += away_score
                    team_performance[home_name]['games'] += 1
            
            logger.info(f"✅ Analyzed performance for {len(team_performance)} teams")
            return team_performance
            
        except Exception as e:
            logger.error(f"❌ Error getting recent performance: {e}")
            return {}
    
    def calculate_team_strengths(self, recent_performance: Dict[str, Dict[str, Any]]) -> Dict[str, float]:
        """Calculate team strength based on recent performance"""
        logger.info("🎯 Calculating team strength ratings...")
        
        team_strengths = {}
        
        for team_name, stats in recent_performance.items():
            games = stats.get('games', 0)
            
            if games < 3:  # Need minimum games for meaningful calculation
                continue
            
            wins = stats.get('wins', 0)
            runs_scored = stats.get('runs_scored', 0)
            runs_allowed = stats.get('runs_allowed', 0)
            
            # Calculate metrics
            win_pct = wins / games
            runs_per_game = runs_scored / games
            runs_allowed_per_game = runs_allowed / games
            run_differential = runs_per_game - runs_allowed_per_game
            
            # Combine win percentage and run differential
            # Weight: 60% win percentage, 40% run differential
            strength = (win_pct - 0.5) * 0.6 + (run_differential / 10) * 0.4
            
            # Normalize to reasonable range (-0.15 to +0.15)
            strength = max(-0.15, min(0.15, strength))
            
            team_strengths[team_name] = round(strength, 3)
        
        logger.info(f"✅ Calculated strengths for {len(team_strengths)} teams")
        return team_strengths
    
    def blend_with_existing(self, new_strengths: Dict[str, float], blend_ratio: float = 0.3) -> Dict[str, float]:
        """Blend new strengths with existing ones for stability"""
        logger.info(f"🔄 Blending new strengths with existing (ratio: {blend_ratio})")
        
        try:
            # Load existing strengths
            existing_strengths = {}
            if os.path.exists(self.team_strength_file):
                with open(self.team_strength_file, 'r') as f:
                    existing_strengths = json.load(f)
            
            blended_strengths = {}
            
            # Process all teams
            all_teams = set(new_strengths.keys()) | set(existing_strengths.keys())
            
            for team in all_teams:
                new_strength = new_strengths.get(team, 0.0)
                existing_strength = existing_strengths.get(team, 0.0)
                
                # Blend: new_ratio * new + (1 - new_ratio) * existing
                blended_strength = blend_ratio * new_strength + (1 - blend_ratio) * existing_strength
                blended_strengths[team] = round(blended_strength, 3)
            
            logger.info(f"✅ Blended strengths for {len(blended_strengths)} teams")
            return blended_strengths
            
        except Exception as e:
            logger.error(f"❌ Error blending strengths: {e}")
            return new_strengths  # Return new strengths if blending fails
    
    def update_team_strengths(self, days_back: int = 14, blend_ratio: float = 0.3) -> bool:
        """Update team strength ratings"""
        logger.info("🔄 Starting weekly team strength update...")
        
        try:
            # Get recent performance
            recent_performance = self.get_recent_team_performance(days_back)
            
            if not recent_performance:
                logger.error("❌ No recent performance data available")
                return False
            
            # Calculate new strengths
            new_strengths = self.calculate_team_strengths(recent_performance)
            
            if not new_strengths:
                logger.error("❌ Could not calculate new team strengths")
                return False
            
            # Blend with existing data for stability
            final_strengths = self.blend_with_existing(new_strengths, blend_ratio)
            
            # Create backup
            if os.path.exists(self.team_strength_file):
                backup_file = f"{self.team_strength_file}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                os.rename(self.team_strength_file, backup_file)
                logger.info(f"📁 Backup created: {backup_file}")
            
            # Save updated strengths
            with open(self.team_strength_file, 'w') as f:
                json.dump(final_strengths, f, indent=2)
            
            logger.info("✅ Team strength update completed successfully")
            
            # Log top and bottom teams
            sorted_teams = sorted(final_strengths.items(), key=lambda x: x[1], reverse=True)
            logger.info("🏆 Top 5 teams:")
            for i, (team, strength) in enumerate(sorted_teams[:5]):
                logger.info(f"   {i+1}. {team}: {strength:+.3f}")
            
            logger.info("📉 Bottom 5 teams:")
            for i, (team, strength) in enumerate(sorted_teams[-5:]):
                logger.info(f"   {30-4+i}. {team}: {strength:+.3f}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error updating team strengths: {e}")
            return False

def main():
    """Main execution for weekly team strength update"""
    logger.info("📈 Weekly Team Strength Updater Starting")
    logger.info(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    updater = WeeklyTeamStrengthUpdater()
    
    # Use last 14 days with 30% new data blend
    success = updater.update_team_strengths(days_back=14, blend_ratio=0.3)
    
    if success:
        logger.info("🎉 Weekly team strength update completed successfully!")
    else:
        logger.error("❌ Weekly team strength update failed")
    
    return success

if __name__ == "__main__":
    main()
