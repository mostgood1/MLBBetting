"""
UltraFast Engine Configuration Manager
Bridges the admin tuning system with the actual engine parameters
"""

import json
import os
from typing import Dict, Any

class EngineConfigManager:
    """Manages configuration for UltraFastEngine to make it actually tunable"""
    
    def __init__(self, config_file: str = 'data/optimized_config.json'):
        self.config_file = config_file
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file"""
        try:
            with open(self.config_file, 'r') as f:
                return json.load(f)
        except:
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Default configuration aligned with actual engine"""
        return {
            "version": "2.0_engine_aligned",
            "engine_parameters": {
                "home_field_advantage": 0.15,
                "base_runs_per_team": 4.3,
                "base_lambda": 4.2,
                "team_strength_multiplier": 0.20,
                "pitcher_era_weight": 0.70,
                "pitcher_whip_weight": 0.30,
                "game_chaos_variance": 0.42
            },
            "betting_parameters": {
                "min_edge": 0.03,
                "kelly_fraction": 0.25,
                "max_kelly_bet": 10.0,
                "high_confidence_ev": 0.10,
                "medium_confidence_ev": 0.05
            },
            "simulation_parameters": {
                "default_sim_count": 2000,
                "quick_sim_count": 1000,
                "detailed_sim_count": 5000,
                "max_sim_count": 10000,
                "random_seed_base": True
            },
            "pitcher_quality_bounds": {
                "min_quality_factor": 0.50,
                "max_quality_factor": 1.60,
                "ace_era_threshold": 2.75,
                "good_era_threshold": 3.50,
                "poor_era_threshold": 5.25,
                "min_games_started": 5
            }
        }
    
    def get_engine_config(self) -> Dict[str, Any]:
        """Get configuration for engine initialization"""
        return {
            'home_field_advantage': self.config.get('engine_parameters', {}).get('home_field_advantage', 0.15),
            'base_runs_per_team': self.config.get('engine_parameters', {}).get('base_runs_per_team', 4.3),
            'base_lambda': self.config.get('engine_parameters', {}).get('base_lambda', 4.2),
            'team_strength_multiplier': self.config.get('engine_parameters', {}).get('team_strength_multiplier', 0.20),
            'pitcher_era_weight': self.config.get('engine_parameters', {}).get('pitcher_era_weight', 0.70),
            'pitcher_whip_weight': self.config.get('engine_parameters', {}).get('pitcher_whip_weight', 0.30),
            'game_chaos_variance': self.config.get('engine_parameters', {}).get('game_chaos_variance', 0.42)
        }
    
    def get_betting_config(self) -> Dict[str, Any]:
        """Get configuration for betting analyzer"""
        return {
            'min_edge': self.config.get('betting_parameters', {}).get('min_edge', 0.03),
            'kelly_fraction': self.config.get('betting_parameters', {}).get('kelly_fraction', 0.25),
            'max_kelly_bet': self.config.get('betting_parameters', {}).get('max_kelly_bet', 10.0),
            'high_confidence_ev': self.config.get('betting_parameters', {}).get('high_confidence_ev', 0.10),
            'medium_confidence_ev': self.config.get('betting_parameters', {}).get('medium_confidence_ev', 0.05)
        }
    
    def get_simulation_config(self) -> Dict[str, Any]:
        """Get configuration for simulation parameters"""
        return {
            'default_sim_count': self.config.get('simulation_parameters', {}).get('default_sim_count', 2000),
            'quick_sim_count': self.config.get('simulation_parameters', {}).get('quick_sim_count', 1000),
            'detailed_sim_count': self.config.get('simulation_parameters', {}).get('detailed_sim_count', 5000),
            'max_sim_count': self.config.get('simulation_parameters', {}).get('max_sim_count', 10000),
            'random_seed_base': self.config.get('simulation_parameters', {}).get('random_seed_base', True)
        }
    
    def get_pitcher_config(self) -> Dict[str, Any]:
        """Get configuration for pitcher quality assessment"""
        return {
            'min_quality_factor': self.config.get('pitcher_quality_bounds', {}).get('min_quality_factor', 0.50),
            'max_quality_factor': self.config.get('pitcher_quality_bounds', {}).get('max_quality_factor', 1.60),
            'ace_era_threshold': self.config.get('pitcher_quality_bounds', {}).get('ace_era_threshold', 2.75),
            'good_era_threshold': self.config.get('pitcher_quality_bounds', {}).get('good_era_threshold', 3.50),
            'poor_era_threshold': self.config.get('pitcher_quality_bounds', {}).get('poor_era_threshold', 5.25),
            'min_games_started': self.config.get('pitcher_quality_bounds', {}).get('min_games_started', 5),
            'era_weight': self.config.get('engine_parameters', {}).get('pitcher_era_weight', 0.70),
            'whip_weight': self.config.get('engine_parameters', {}).get('pitcher_whip_weight', 0.30)
        }
    
    def update_config(self, new_config: Dict[str, Any]):
        """Update configuration and reload"""
        self.config.update(new_config)
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def reload_config(self):
        """Reload configuration from file"""
        self.config = self._load_config()

# Global config manager instance
config_manager = EngineConfigManager()
