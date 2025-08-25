#!/usr/bin/env python3
"""
Manual Model Parameter Adjustment Tool
=====================================
Addresses specific model bias issues observed in the predictions:
- Home team bias (home teams winning almost every game in predictions)
- Scoring accuracy improvements
- Bullpen factor integration
- Parameter rebalancing based on observed patterns
"""

import json
import os
import logging
from datetime import datetime
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ManualModelAdjuster:
    """Tool for manually adjusting model parameters based on observed biases"""
    
    def __init__(self, data_dir: str = 'data'):
        self.data_dir = data_dir
        self.config_file = os.path.join(data_dir, 'manual_tuned_config.json')
        
        # Current observed issues from the prediction data:
        # 1. Home teams have win probabilities often 52-58% (too high)
        # 2. Total scores often predicted around 11+ runs (seems high)
        # 3. No bullpen factor currently integrated
        # 4. Score predictions need better calibration
        
        self.current_issues = {
            'home_team_bias': 'Excessive - home teams predicted to win ~60% of games',
            'total_scoring': 'Often 11+ runs predicted, may be too high',
            'bullpen_factor': 'Not currently integrated',
            'score_differential': 'Home teams often predicted +0.5-1.0 run advantage'
        }

    def analyze_prediction_patterns(self) -> Dict[str, Any]:
        """Analyze patterns from recent predictions"""
        analysis = {
            'timestamp': datetime.now().isoformat(),
            'observed_patterns': {},
            'recommended_adjustments': {}
        }
        
        # Check recent betting recommendations for patterns
        betting_files = [f for f in os.listdir(self.data_dir) if f.startswith('betting_recommendations_2025')]
        
        if not betting_files:
            logger.warning("No recent betting recommendations found for analysis")
            return analysis
        
        # Analyze the most recent file
        latest_file = max(betting_files)
        file_path = os.path.join(self.data_dir, latest_file)
        
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            games = data.get('games', {})
            if not games:
                logger.warning("No games found in betting recommendations")
                return analysis
            
            # Analyze patterns
            home_win_probs = []
            away_win_probs = []
            total_scores = []
            score_diffs = []
            
            for game_key, game_data in games.items():
                predictions = game_data.get('predictions', {})
                
                home_prob = predictions.get('home_win_prob', 0.5)
                away_prob = predictions.get('away_win_prob', 0.5)
                total_score = predictions.get('predicted_total_runs', 0)
                home_score = predictions.get('predicted_home_score', 0)
                away_score = predictions.get('predicted_away_score', 0)
                
                home_win_probs.append(home_prob)
                away_win_probs.append(away_prob)
                total_scores.append(total_score)
                score_diffs.append(home_score - away_score)
            
            # Calculate statistics
            analysis['observed_patterns'] = {
                'average_home_win_prob': sum(home_win_probs) / len(home_win_probs) if home_win_probs else 0,
                'average_away_win_prob': sum(away_win_probs) / len(away_win_probs) if away_win_probs else 0,
                'average_total_score': sum(total_scores) / len(total_scores) if total_scores else 0,
                'average_score_differential': sum(score_diffs) / len(score_diffs) if score_diffs else 0,
                'home_team_favored_rate': sum(1 for p in home_win_probs if p > 0.52) / len(home_win_probs) if home_win_probs else 0,
                'games_analyzed': len(games)
            }
            
            # Generate recommendations based on patterns
            patterns = analysis['observed_patterns']
            recommendations = {}
            
            # Home field advantage adjustment
            if patterns['average_home_win_prob'] > 0.55:
                hfa_reduction = (patterns['average_home_win_prob'] - 0.52) * 0.5
                recommendations['home_field_advantage'] = {
                    'current_estimated': 0.15,
                    'recommended': max(0.08, 0.15 - hfa_reduction),
                    'reason': f"Reduce excessive home bias (avg home win prob: {patterns['average_home_win_prob']:.3f})"
                }
            
            # Total scoring adjustment
            if patterns['average_total_score'] > 9.5:
                scoring_reduction = (patterns['average_total_score'] - 9.0) / 10.0
                recommendations['scoring_adjustment'] = {
                    'current_estimated': 1.0,
                    'recommended': max(0.85, 1.0 - scoring_reduction),
                    'reason': f"Reduce high total scoring (avg: {patterns['average_total_score']:.1f} runs)"
                }
            
            # Score differential adjustment
            if abs(patterns['average_score_differential']) > 0.3:
                recommendations['score_balance'] = {
                    'home_advantage_excessive': patterns['average_score_differential'] > 0.3,
                    'recommended_balance_adjustment': -patterns['average_score_differential'] * 0.3,
                    'reason': f"Rebalance score differential (avg: {patterns['average_score_differential']:+.2f})"
                }
            
            # Bullpen factor integration
            recommendations['bullpen_integration'] = {
                'current': 0.0,
                'recommended': 0.15,
                'reason': "Integrate bullpen factors for improved late-game accuracy"
            }
            
            analysis['recommended_adjustments'] = recommendations
            
        except Exception as e:
            logger.error(f"Error analyzing prediction patterns: {e}")
            analysis['error'] = str(e)
        
        return analysis

    def create_optimized_config(self) -> Dict[str, Any]:
        """Create optimized configuration based on observed issues"""
        
        # Base configuration addressing observed issues
        optimized_config = {
            'version': '3.0_manual_tuned',
            'timestamp': datetime.now().isoformat(),
            'tuning_source': 'manual_bias_correction',
            'issues_addressed': list(self.current_issues.keys()),
            
            'engine_parameters': {
                # Reduce home field advantage to address home team bias
                'home_field_advantage': 0.10,  # Reduced from typical 0.15
                
                # Adjust base scoring parameters
                'base_runs_per_team': 4.0,     # Slightly reduced from 4.3
                'base_lambda': 4.0,            # Reduced from 4.2 to lower variance
                
                # Rebalance pitcher impact
                'pitcher_era_weight': 0.75,    # Increased from 0.70
                'pitcher_whip_weight': 0.35,   # Increased from 0.30
                
                # Team strength adjustments
                'team_strength_multiplier': 0.18,  # Reduced from 0.20
                
                # Add bullpen factor
                'bullpen_weight': 0.15,        # NEW: 15% bullpen impact
                
                # Scoring bias corrections
                'total_scoring_adjustment': 0.92,  # Reduce total scoring by 8%
                'home_scoring_boost': 0.96,       # Reduce home team scoring advantage
                'away_scoring_boost': 1.02,       # Slight boost to away team scoring
                
                # Variance and chaos adjustments
                'game_chaos_variance': 0.38,   # Reduced from 0.42
                
                # Simulation parameters
                'simulation_count': 2000,      # Standard simulation count
            },
            
            'adjustments_rationale': {
                'home_field_advantage': 'Reduced from 0.15 to 0.10 to address excessive home team bias',
                'base_runs_per_team': 'Reduced from 4.3 to 4.0 to lower total scoring predictions',
                'base_lambda': 'Reduced from 4.2 to 4.0 to decrease scoring variance',
                'pitcher_weights': 'Increased ERA/WHIP weights to improve winner prediction accuracy',
                'bullpen_weight': 'Added 15% bullpen factor to improve late-game accuracy',
                'scoring_adjustments': 'Applied differential adjustments to balance home/away scoring',
                'team_strength_multiplier': 'Reduced to prevent over-amplification of team differences'
            },
            
            'expected_improvements': [
                'More balanced home/away win predictions (target: ~52% home advantage)',
                'Lower total run predictions (target: 8.5-9.5 avg instead of 11+)',
                'Better individual team score accuracy',
                'Improved prediction accuracy in close games via bullpen factors',
                'More realistic score differentials'
            ]
        }
        
        return optimized_config

    def apply_manual_adjustments(self) -> Dict[str, Any]:
        """Apply manual adjustments and save configuration"""
        
        logger.info("🔧 Creating manually optimized model configuration...")
        
        # Analyze current patterns
        analysis = self.analyze_prediction_patterns()
        
        # Create optimized configuration
        config = self.create_optimized_config()
        
        # Save configuration
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
            logger.info(f"✅ Saved optimized configuration to {self.config_file}")
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            return {'error': str(e)}
        
        return {
            'success': True,
            'config_file': self.config_file,
            'analysis': analysis,
            'configuration': config
        }

    def generate_adjustment_report(self, results: Dict[str, Any]) -> str:
        """Generate detailed adjustment report"""
        
        if 'error' in results:
            return f"❌ Error generating adjustments: {results['error']}"
        
        config = results.get('configuration', {})
        analysis = results.get('analysis', {})
        patterns = analysis.get('observed_patterns', {})
        
        report = f"""
🔧 Manual Model Adjustment Report
================================
📅 Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🎯 Issues Identified & Addressed:
"""
        
        for issue, description in self.current_issues.items():
            report += f"  • {issue.replace('_', ' ').title()}: {description}\n"
        
        if patterns:
            report += f"""
📊 Current Model Patterns (from {patterns.get('games_analyzed', 0)} games):
  • Average Home Win Probability: {patterns.get('average_home_win_prob', 0):.1%}
  • Average Total Runs Predicted: {patterns.get('average_total_score', 0):.1f}
  • Home Team Favored Rate: {patterns.get('home_team_favored_rate', 0):.1%}
  • Average Score Differential: {patterns.get('average_score_differential', 0):+.2f} (home advantage)
"""
        
        params = config.get('engine_parameters', {})
        report += f"""
⚙️ Parameter Adjustments Applied:
  • Home Field Advantage: {params.get('home_field_advantage', 0):.2f} (reduced for bias correction)
  • Base Runs Per Team: {params.get('base_runs_per_team', 0):.1f} (lowered total scoring)
  • Base Lambda: {params.get('base_lambda', 0):.1f} (reduced variance)
  • Pitcher ERA Weight: {params.get('pitcher_era_weight', 0):.2f} (increased impact)
  • Bullpen Weight: {params.get('bullpen_weight', 0):.2f} (newly integrated)
  • Total Scoring Adjustment: {params.get('total_scoring_adjustment', 1.0):.2f} (reduced by {(1-params.get('total_scoring_adjustment', 1.0))*100:.0f}%)
  • Home Scoring Boost: {params.get('home_scoring_boost', 1.0):.2f}
  • Away Scoring Boost: {params.get('away_scoring_boost', 1.0):.2f}

🎯 Expected Improvements:
"""
        
        for improvement in config.get('expected_improvements', []):
            report += f"  • {improvement}\n"
        
        report += f"""
📈 Implementation:
  • Configuration saved to: {self.config_file}
  • Ready for integration into prediction engine
  • Recommend testing on next prediction cycle
  • Monitor performance over 7-14 days for effectiveness

🔄 Next Steps:
  1. Update prediction engine to use new parameters
  2. Run predictions with adjusted configuration
  3. Monitor home/away win rate balance
  4. Track total scoring accuracy improvements
  5. Verify bullpen factor integration effectiveness
"""
        
        return report

def main():
    """Run manual model adjustment process"""
    print("🔧 Manual Model Parameter Adjustment Tool")
    print("=" * 50)
    
    adjuster = ManualModelAdjuster()
    
    # Apply manual adjustments
    results = adjuster.apply_manual_adjustments()
    
    # Generate and display report
    report = adjuster.generate_adjustment_report(results)
    print(report)
    
    if results.get('success'):
        print(f"\n✅ Manual adjustments completed successfully!")
        print(f"📁 Configuration file: {results['config_file']}")
    else:
        print(f"\n❌ Adjustment process failed")

if __name__ == "__main__":
    main()
