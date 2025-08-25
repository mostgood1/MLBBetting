#!/usr/bin/env python3
"""
Aggressive Model Retuning - Address remaining home team bias
"""

import json
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AggressiveModelRetuner:
    """More aggressive model parameter adjustments"""
    
    def __init__(self):
        self.config_file = 'data/aggressive_tuned_config.json'
        
    def create_aggressive_parameters(self):
        """Create aggressive parameter adjustments to eliminate home bias"""
        
        logger.info("🔧 Creating aggressive parameter adjustments...")
        
        # VERY aggressive corrections
        aggressive_config = {
            "version": "4.0_aggressive",
            "description": "Aggressive bias correction - eliminate home team advantage",
            "generated_at": datetime.now().isoformat(),
            "parameters": {
                # Remove almost all home field advantage
                "home_field_advantage": 0.02,  # Minimal home advantage
                
                # Boost away teams significantly
                "away_field_boost": 0.08,      # Give away teams an advantage
                
                # Reduce scoring slightly more
                "base_runs_per_team": 3.8,     # Further reduce base scoring
                "base_lambda": 3.9,            # Reduce variance
                
                # Increase pitcher impact
                "pitcher_era_weight": 0.85,    # Even more pitcher weight
                "pitcher_whip_weight": 0.45,   # Higher WHIP impact
                
                # Team parameters
                "team_strength_multiplier": 0.15,  # Reduce team strength impact
                "game_chaos_variance": 0.35,       # Reduce randomness
                
                # Bullpen (keep current)
                "bullpen_weight": 0.15,
                
                # AGGRESSIVE scoring bias corrections
                "total_scoring_adjustment": 0.88,  # Reduce total by 12%
                "home_scoring_boost": 0.88,       # Significant home penalty
                "away_scoring_boost": 1.08,       # Significant away boost
                
                # Simulation
                "simulation_count": 2000
            },
            "rationale": {
                "home_field_advantage": "Reduced to 0.02 from 0.10 - almost eliminate home advantage",
                "away_field_boost": "New parameter - give away teams 8% boost to counteract bias",
                "scoring_adjustments": "Home teams get 88% scoring, away teams get 108% - reverse the bias",
                "pitcher_weights": "Increased to make individual matchups more important than venue"
            }
        }
        
        # Save configuration
        with open(self.config_file, 'w') as f:
            json.dump(aggressive_config, f, indent=2)
        
        logger.info(f"✅ Aggressive configuration saved to {self.config_file}")
        return aggressive_config
    
    def apply_aggressive_parameters(self):
        """Apply aggressive parameters to the betting engine"""
        
        logger.info("🔧 Applying aggressive parameter corrections...")
        
        config = self.create_aggressive_parameters()
        params = config['parameters']
        
        # Read current betting engine
        with open('betting_recommendations_engine.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Create backup
        backup_name = f'betting_recommendations_engine.py.backup_aggressive_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
        with open(backup_name, 'w', encoding='utf-8') as f:
            f.write(content)
        logger.info(f"📁 Backup created: {backup_name}")
        
        # Find and replace the optimized parameters section
        start_marker = "# =========================================="
        end_marker = "# Load bullpen data"
        
        start_index = content.find(start_marker)
        end_index = content.find(end_marker)
        
        if start_index == -1 or end_index == -1:
            logger.error("❌ Could not find parameter section to replace")
            return False
        
        # Create new parameter section
        new_params = f'''        # ==========================================
        # AGGRESSIVE MODEL PARAMETERS (v4.0)
        # Applied: {datetime.now().strftime('%Y-%m-%d')} - Aggressive bias elimination
        # ==========================================
        
        # Core prediction parameters (AGGRESSIVE corrections)
        self.home_field_advantage = {params['home_field_advantage']}  # Minimal home advantage
        self.away_field_boost = {params['away_field_boost']}        # NEW: Away team boost
        self.base_runs_per_team = {params['base_runs_per_team']}     # Further reduced scoring
        self.base_lambda = {params['base_lambda']}            # Reduced variance
        
        # Pitcher impact parameters (maximized for accuracy)
        self.pitcher_era_weight = {params['pitcher_era_weight']}    # Maximized ERA impact
        self.pitcher_whip_weight = {params['pitcher_whip_weight']}   # Maximized WHIP impact
        
        # Team and game parameters
        self.team_strength_multiplier = {params['team_strength_multiplier']}  # Minimized team impact
        self.game_chaos_variance = {params['game_chaos_variance']}       # Reduced variance
        
        # Bullpen integration (maintained)
        self.bullpen_weight = {params['bullpen_weight']}
        
        # AGGRESSIVE scoring bias corrections
        self.total_scoring_adjustment = {params['total_scoring_adjustment']}  # Reduce total scoring by 12%
        self.home_scoring_boost = {params['home_scoring_boost']}       # Significant home penalty
        self.away_scoring_boost = {params['away_scoring_boost']}       # Significant away boost
        
        # Simulation parameters
        self.simulation_count = {params['simulation_count']}
        
        '''
        
        # Replace the section
        new_content = content[:start_index] + new_params + content[end_index:]
        
        # Write updated file
        with open('betting_recommendations_engine.py', 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        logger.info("✅ Aggressive parameters applied successfully!")
        return True

def main():
    retuner = AggressiveModelRetuner()
    
    logger.info("🎯 Starting aggressive model retuning...")
    
    success = retuner.apply_aggressive_parameters()
    
    if success:
        logger.info("🎉 Aggressive retuning completed successfully!")
        logger.info("🔄 Please run the betting engine again to test the changes")
    else:
        logger.error("❌ Aggressive retuning failed")

if __name__ == "__main__":
    main()
