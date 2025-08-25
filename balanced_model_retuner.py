#!/usr/bin/env python3
"""
Balanced Model Retuning - Find the sweet spot between biased and over-corrected
"""

import json
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BalancedModelRetuner:
    """Find balanced parameters between original bias and over-correction"""
    
    def __init__(self):
        self.config_file = 'data/balanced_tuned_config.json'
        
    def create_balanced_parameters(self):
        """Create balanced parameter adjustments between bias and over-correction"""
        
        logger.info("🔧 Creating balanced parameter adjustments...")
        
        # BALANCED corrections - aim for 48-52% home win rate
        balanced_config = {
            "version": "5.0_balanced",
            "description": "Balanced bias correction - target 50% home/away split",
            "generated_at": datetime.now().isoformat(),
            "parameters": {
                # Balanced field advantage
                "home_field_advantage": 0.06,  # Moderate home advantage
                "away_field_boost": 0.04,      # Moderate away team boost
                
                # Balanced scoring
                "base_runs_per_team": 3.9,     # Slightly reduced base scoring
                "base_lambda": 4.0,            # Moderate variance
                
                # Moderate pitcher impact
                "pitcher_era_weight": 0.78,    # Good pitcher weight
                "pitcher_whip_weight": 0.38,   # Good WHIP impact
                
                # Team parameters
                "team_strength_multiplier": 0.17,  # Moderate team strength impact
                "game_chaos_variance": 0.38,       # Moderate randomness
                
                # Bullpen (keep current)
                "bullpen_weight": 0.15,
                
                # BALANCED scoring bias corrections
                "total_scoring_adjustment": 0.90,  # Reduce total by 10%
                "home_scoring_boost": 0.92,       # Moderate home penalty
                "away_scoring_boost": 1.05,       # Moderate away boost
                
                # Simulation
                "simulation_count": 2000
            },
            "rationale": {
                "home_field_advantage": "Balanced at 0.06 - realistic home advantage without bias",
                "away_field_boost": "Moderate 4% away boost to counteract remaining bias",
                "scoring_adjustments": "Home teams get 92% scoring, away teams get 105% - gentle correction",
                "target": "Aim for 48-52% home win rate with realistic scoring"
            }
        }
        
        # Save configuration
        with open(self.config_file, 'w') as f:
            json.dump(balanced_config, f, indent=2)
        
        logger.info(f"✅ Balanced configuration saved to {self.config_file}")
        return balanced_config
    
    def apply_balanced_parameters_to_betting_engine(self):
        """Apply balanced parameters to the betting engine"""
        
        logger.info("🔧 Applying balanced parameter corrections to betting engine...")
        
        config = self.create_balanced_parameters()
        params = config['parameters']
        
        # Read current betting engine
        with open('betting_recommendations_engine.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Create backup
        backup_name = f'betting_recommendations_engine.py.backup_balanced_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
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
        # BALANCED MODEL PARAMETERS (v5.0)
        # Applied: {datetime.now().strftime('%Y-%m-%d')} - Balanced bias correction
        # Target: 48-52% home win rate with realistic scoring
        # ==========================================
        
        # Core prediction parameters (BALANCED corrections)
        self.home_field_advantage = {params['home_field_advantage']}  # Moderate home advantage
        self.away_field_boost = {params['away_field_boost']}        # Moderate away team boost
        self.base_runs_per_team = {params['base_runs_per_team']}     # Balanced base scoring
        self.base_lambda = {params['base_lambda']}            # Moderate variance
        
        # Pitcher impact parameters (balanced for accuracy)
        self.pitcher_era_weight = {params['pitcher_era_weight']}    # Good ERA impact
        self.pitcher_whip_weight = {params['pitcher_whip_weight']}   # Good WHIP impact
        
        # Team and game parameters
        self.team_strength_multiplier = {params['team_strength_multiplier']}  # Moderate team impact
        self.game_chaos_variance = {params['game_chaos_variance']}       # Moderate variance
        
        # Bullpen integration (maintained)
        self.bullpen_weight = {params['bullpen_weight']}
        
        # BALANCED scoring bias corrections
        self.total_scoring_adjustment = {params['total_scoring_adjustment']}  # Reduce total scoring by 10%
        self.home_scoring_boost = {params['home_scoring_boost']}       # Moderate home penalty
        self.away_scoring_boost = {params['away_scoring_boost']}       # Moderate away boost
        
        # Simulation parameters
        self.simulation_count = {params['simulation_count']}
        
        '''
        
        # Replace the section
        new_content = content[:start_index] + new_params + content[end_index:]
        
        # Write updated file
        with open('betting_recommendations_engine.py', 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        logger.info("✅ Balanced parameters applied to betting engine!")
        return True
    
    def apply_balanced_parameters_to_ultrafast_engine(self):
        """Apply balanced parameters to the UltraFast engine"""
        
        logger.info("🔧 Applying balanced parameters to UltraFast engine...")
        
        config = self.create_balanced_parameters()
        params = config['parameters']
        
        # Read current UltraFast engine
        with open('engines/ultra_fast_engine.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find and replace the config section
        start_marker = 'def _get_default_config(self):'
        end_marker = '"min_games_started": 5'
        
        start_index = content.find(start_marker)
        end_index = content.find(end_marker) + len(end_marker)
        
        if start_index == -1 or end_index == -1:
            logger.error("❌ Could not find config section in UltraFast engine")
            return False
        
        # Create new config section
        new_config = f'''def _get_default_config(self):
        """Get default configuration parameters - BALANCED BIAS CORRECTIONS"""
        return {{
            "engine_parameters": {{
                "home_field_advantage": {params['home_field_advantage']},    # Moderate home advantage
                "away_field_boost": {params['away_field_boost']},        # Moderate away boost  
                "base_lambda": {params['base_lambda']},              # Moderate variance
                "team_strength_multiplier": {params['team_strength_multiplier']}, # Moderate team impact
                "pitcher_era_weight": {params['pitcher_era_weight']},      # Good ERA impact
                "pitcher_whip_weight": {params['pitcher_whip_weight']},     # Good WHIP impact
                "game_chaos_variance": {params['game_chaos_variance']},     # Moderate randomness
                "total_scoring_adjustment": {params['total_scoring_adjustment']}, # Reduce total by 10%
                "home_scoring_boost": {params['home_scoring_boost']},      # Moderate home penalty
                "away_scoring_boost": {params['away_scoring_boost']},      # Moderate away boost
                "bullpen_weight": {params['bullpen_weight']}           # Bullpen integration
            }},
            "betting_parameters": {{
                "min_edge": 0.03,
                "kelly_fraction": 0.25,
                "high_confidence_ev": 0.10,
                "medium_confidence_ev": 0.05
            }},
            "simulation_parameters": {{
                "default_sim_count": 2000,
                "quick_sim_count": 1000,
                "detailed_sim_count": 5000,
                "max_sim_count": 10000
            }},
            "pitcher_quality_bounds": {{
                "min_quality_factor": 0.50,
                "max_quality_factor": 1.60,
                "ace_era_threshold": 2.75,
                "good_era_threshold": 3.50,
                "poor_era_threshold": 5.25,
                "min_games_started": 5'''
        
        # Replace the section
        new_content = content[:start_index] + new_config + content[end_index:]
        
        # Write updated file
        with open('engines/ultra_fast_engine.py', 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        # Also update the speed cache setup
        start_cache = '_setup_speed_cache(self):'
        end_cache = 'self.bullpen_weight = engine_params.get(\'bullpen_weight\', 0.15)'
        
        start_cache_index = new_content.find(start_cache)
        end_cache_index = new_content.find(end_cache) + len(end_cache)
        
        if start_cache_index != -1 and end_cache_index != -1:
            new_cache = f'''_setup_speed_cache(self):
        """Setup caching for maximum speed with balanced parameters"""
        engine_params = self.config.get('engine_parameters', {{}})
        self.home_field_advantage = engine_params.get('home_field_advantage', {params['home_field_advantage']})
        self.away_field_boost = engine_params.get('away_field_boost', {params['away_field_boost']})
        self.base_runs_per_team = {params['base_runs_per_team']}  # Balanced from config
        self.base_lambda = engine_params.get('base_lambda', {params['base_lambda']})
        self.team_strength_multiplier = engine_params.get('team_strength_multiplier', {params['team_strength_multiplier']})
        self.game_chaos_variance = engine_params.get('game_chaos_variance', {params['game_chaos_variance']})
        self.total_scoring_adjustment = engine_params.get('total_scoring_adjustment', {params['total_scoring_adjustment']})
        self.home_scoring_boost = engine_params.get('home_scoring_boost', {params['home_scoring_boost']})
        self.away_scoring_boost = engine_params.get('away_scoring_boost', {params['away_scoring_boost']})
        self.bullpen_weight = engine_params.get('bullpen_weight', {params['bullpen_weight']})'''
            
            new_content = new_content[:start_cache_index] + new_cache + new_content[end_cache_index:]
        
        # Write final updated file
        with open('engines/ultra_fast_engine.py', 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        logger.info("✅ Balanced parameters applied to UltraFast engine!")
        return True

def main():
    retuner = BalancedModelRetuner()
    
    logger.info("🎯 Starting balanced model retuning...")
    
    success1 = retuner.apply_balanced_parameters_to_betting_engine()
    success2 = retuner.apply_balanced_parameters_to_ultrafast_engine()
    
    if success1 and success2:
        logger.info("🎉 Balanced retuning completed successfully!")
        logger.info("🔄 Please clear cache and regenerate predictions to test")
        logger.info("🎯 Target: 48-52% home win rate with realistic 8-9 run totals")
    else:
        logger.error("❌ Balanced retuning failed")

if __name__ == "__main__":
    main()
