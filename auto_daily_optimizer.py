#!/usr/bin/env python3
"""
Automated Daily Prediction Engine Optimization
Analyzes recent performance and optimizes parameters automatically
"""

import json
import os
import logging
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import subprocess
import sys

class AutoOptimizer:
    """Automated optimization system for daily tuning"""
    
    def __init__(self):
        self.config_file = Path('data/optimized_config.json')
        self.performance_file = Path('data/performance_history.json')
        self.betting_accuracy_file = Path('data/betting_accuracy_analysis.json')
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('data/auto_optimization.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def analyze_recent_performance(self, days=7):
        """Analyze performance over recent days"""
        try:
            # Load betting accuracy data
            with open(self.betting_accuracy_file, 'r') as f:
                betting_data = json.load(f)
            
            performance_metrics = {
                'total_games': betting_data['total_predictions_analyzed'],
                'winner_accuracy': betting_data['betting_performance']['winner_accuracy_pct'] / 100,
                'total_accuracy': betting_data['betting_performance']['total_accuracy_pct'] / 100,
                'perfect_games_pct': betting_data['betting_performance']['perfect_games_pct'] / 100,
                'recent_trend': self._calculate_recent_trend(betting_data)
            }
            
            self.logger.info(f"📊 Recent Performance Analysis:")
            self.logger.info(f"   Winner Accuracy: {performance_metrics['winner_accuracy']:.1%}")
            self.logger.info(f"   Total Accuracy: {performance_metrics['total_accuracy']:.1%}")
            self.logger.info(f"   Perfect Games: {performance_metrics['perfect_games_pct']:.1%}")
            
            return performance_metrics
            
        except Exception as e:
            self.logger.error(f"Performance analysis failed: {e}")
            return None
    
    def _calculate_recent_trend(self, betting_data):
        """Calculate performance trend from recent games"""
        detailed_games = betting_data.get('detailed_games', [])
        if len(detailed_games) < 10:
            return 0.0
        
        # Take last 20 games for trend analysis
        recent_games = detailed_games[-20:]
        accuracy_scores = []
        
        for game in recent_games:
            score = 0
            if game.get('winner_correct'):
                score += 0.5
            if game.get('total_correct'):
                score += 0.3
            if game.get('bet_grade') == 'A+':
                score += 0.2
            accuracy_scores.append(score)
        
        # Calculate trend (positive = improving, negative = declining)
        if len(accuracy_scores) >= 10:
            first_half = np.mean(accuracy_scores[:10])
            second_half = np.mean(accuracy_scores[10:])
            return second_half - first_half
        
        return 0.0
    
    def suggest_optimizations(self, performance_metrics):
        """Suggest parameter optimizations based on performance"""
        suggestions = {}
        current_config = self.load_current_config()
        
        # Analyze winner accuracy
        if performance_metrics['winner_accuracy'] < 0.55:
            self.logger.info("🔧 Winner accuracy below target - adjusting team parameters")
            suggestions['team_parameters'] = {
                'offensive_runs_weight': min(0.55, current_config['team_parameters']['offensive_runs_weight'] + 0.05),
                'recent_form_weight': min(0.4, current_config['team_parameters']['recent_form_weight'] + 0.05)
            }
        
        # Analyze total accuracy  
        if performance_metrics['total_accuracy'] < 0.45:
            self.logger.info("🔧 Total accuracy below target - adjusting pitcher parameters")
            suggestions['pitcher_parameters'] = {
                'era_weight': min(0.5, current_config['pitcher_parameters']['era_weight'] + 0.05),
                'recent_form_weight': min(0.4, current_config['pitcher_parameters']['recent_form_weight'] + 0.05)
            }
        
        # Analyze perfect games percentage
        if performance_metrics['perfect_games_pct'] < 0.15:
            self.logger.info("🔧 Perfect games below target - tightening betting parameters")
            suggestions['betting_parameters'] = {
                'high_confidence_threshold': min(0.75, current_config['betting_parameters']['high_confidence_threshold'] + 0.02),
                'value_bet_threshold': min(0.08, current_config['betting_parameters']['value_bet_threshold'] + 0.01)
            }
        
        # Adjust based on trend
        if performance_metrics['recent_trend'] < -0.1:
            self.logger.info("📉 Declining trend detected - applying conservative adjustments")
            if 'simulation_parameters' not in suggestions:
                suggestions['simulation_parameters'] = {}
            suggestions['simulation_parameters']['default_sim_count'] = min(7000, current_config['simulation_parameters']['default_sim_count'] + 1000)
        
        return suggestions
    
    def apply_optimizations(self, suggestions):
        """Apply optimization suggestions to configuration"""
        current_config = self.load_current_config()
        
        # Apply suggested changes
        for category, params in suggestions.items():
            if category in current_config:
                for param, value in params.items():
                    current_config[category][param] = value
                    self.logger.info(f"✅ Updated {category}.{param} = {value}")
        
        # Update metadata
        current_config['last_updated'] = datetime.now().isoformat()
        current_config['version'] = f"auto_optimized_{datetime.now().strftime('%Y%m%d_%H%M')}"
        current_config['performance_grade'] = "AUTO_OPTIMIZED"
        current_config['optimization_history'] = current_config.get('optimization_history', [])
        current_config['optimization_history'].append({
            'timestamp': datetime.now().isoformat(),
            'changes': suggestions,
            'trigger': 'automated_daily_optimization'
        })
        
        # Save optimized configuration
        with open(self.config_file, 'w') as f:
            json.dump(current_config, f, indent=2)
        
        self.logger.info("💾 Optimized configuration saved")
        return current_config
    
    def load_current_config(self):
        """Load current configuration or create default"""
        try:
            with open(self.config_file, 'r') as f:
                return json.load(f)
        except:
            return self.get_default_config()
    
    def get_default_config(self):
        """Get default configuration"""
        return {
            "version": "1.0_default",
            "performance_grade": "DEFAULT",
            "pitcher_parameters": {
                "era_weight": 0.45,
                "whip_weight": 0.3,
                "recent_form_weight": 0.35,
                "career_vs_team_weight": 0.3,
                "ace_run_impact": -1.0,
                "good_run_impact": -0.6
            },
            "team_parameters": {
                "offensive_runs_weight": 0.45,
                "recent_form_weight": 0.35,
                "home_field_advantage": 0.2,
                "h2h_weight": 0.25
            },
            "betting_parameters": {
                "high_confidence_threshold": 0.7,
                "medium_confidence_threshold": 0.55,
                "value_bet_threshold": 0.05,
                "kelly_multiplier": 0.25
            },
            "simulation_parameters": {
                "default_sim_count": 5000,
                "fast_sim_count": 2000,
                "accuracy_sim_count": 10000
            }
        }
    
    def run_daily_optimization(self):
        """Run the full daily optimization process"""
        self.logger.info("🚀 Starting automated daily optimization")
        
        try:
            # 1. Analyze recent performance
            performance = self.analyze_recent_performance()
            if not performance:
                self.logger.error("❌ Performance analysis failed - aborting optimization")
                return False
            
            # 2. Generate optimization suggestions
            suggestions = self.suggest_optimizations(performance)
            
            if not suggestions:
                self.logger.info("✅ No optimizations needed - performance is satisfactory")
                return True
            
            # 3. Apply optimizations
            optimized_config = self.apply_optimizations(suggestions)
            
            # 4. Log optimization summary
            self.logger.info("🎯 Daily optimization completed successfully")
            self.logger.info(f"   Applied {len(suggestions)} category optimizations")
            self.logger.info(f"   New version: {optimized_config['version']}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Daily optimization failed: {e}")
            return False
    
    def validate_optimization(self):
        """Validate that optimization improved performance"""
        # This would ideally run some validation tests
        # For now, just log that validation should be run
        self.logger.info("🧪 Optimization validation recommended - monitor next day's performance")

def main():
    """Main function for automated optimization"""
    optimizer = AutoOptimizer()
    
    if len(sys.argv) > 1 and sys.argv[1] == '--validate':
        optimizer.validate_optimization()
    else:
        success = optimizer.run_daily_optimization()
        if success:
            print("✅ Daily optimization completed successfully")
            sys.exit(0)
        else:
            print("❌ Daily optimization failed")
            sys.exit(1)

if __name__ == "__main__":
    main()
