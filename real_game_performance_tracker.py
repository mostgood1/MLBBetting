"""
Real Game Performance Tracker and Auto-Tuner
Integrates with daily betting accuracy analysis to optimize engine parameters based on actual MLB results
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any
import logging
from engines.ultra_fast_engine import UltraFastSimEngine
import statistics

logger = logging.getLogger(__name__)

class RealGamePerformanceTracker:
    """Tracks engine performance against real MLB game results and suggests parameter optimizations"""
    
    def __init__(self, data_dir: str = 'data'):
        self.data_dir = data_dir
        self.accuracy_file = os.path.join(data_dir, 'betting_accuracy_analysis.json')
        self.performance_file = os.path.join(data_dir, 'performance_history.json')
        self.config_file = os.path.join(data_dir, 'optimized_config.json')
        
    def load_latest_accuracy_data(self) -> Dict[str, Any]:
        """Load the latest betting accuracy analysis"""
        try:
            with open(self.accuracy_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Could not load accuracy data: {e}")
            return {}
    
    def analyze_recent_performance(self, days: int = 7) -> Dict[str, Any]:
        """Analyze performance over recent days to identify trends"""
        accuracy_data = self.load_latest_accuracy_data()
        
        if not accuracy_data or 'detailed_games' not in accuracy_data:
            return {}
        
        # Filter recent games
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        recent_games = [
            game for game in accuracy_data['detailed_games']
            if game.get('date', '') >= cutoff_date
        ]
        
        if not recent_games:
            return {}
        
        # Calculate detailed metrics
        analysis = self._calculate_performance_metrics(recent_games)
        analysis['games_analyzed'] = len(recent_games)
        analysis['date_range'] = f"{cutoff_date} to {datetime.now().strftime('%Y-%m-%d')}"
        
        return analysis
    
    def _calculate_performance_metrics(self, games: List[Dict]) -> Dict[str, Any]:
        """Calculate detailed performance metrics from game results"""
        if not games:
            return {}
        
        # Basic accuracy metrics
        winner_correct = sum(1 for g in games if g.get('winner_correct', False))
        total_correct = sum(1 for g in games if g.get('total_correct', False))
        perfect_games = sum(1 for g in games if g.get('perfect_game', False))
        
        # Score prediction errors
        score_errors = []
        total_errors = []
        home_advantage_actual = []
        
        for game in games:
            if 'predicted_score' in game and 'actual_score' in game:
                try:
                    pred_away, pred_home = map(float, game['predicted_score'].split('-'))
                    actual_away, actual_home = map(float, game['actual_score'].split('-'))
                    
                    # Score prediction errors
                    away_error = abs(pred_away - actual_away)
                    home_error = abs(pred_home - actual_home)
                    score_errors.extend([away_error, home_error])
                    
                    # Total prediction errors
                    if 'predicted_total' in game and 'actual_total' in game:
                        total_error = abs(game['predicted_total'] - game['actual_total'])
                        total_errors.append(total_error)
                    
                    # Home field advantage analysis
                    actual_home_advantage = actual_home - actual_away
                    home_advantage_actual.append(actual_home_advantage)
                    
                except (ValueError, AttributeError):
                    continue
        
        # Calculate performance metrics
        metrics = {
            'winner_accuracy': winner_correct / len(games) if games else 0,
            'total_accuracy': total_correct / len(games) if games else 0,
            'perfect_game_rate': perfect_games / len(games) if games else 0,
            'avg_score_error': statistics.mean(score_errors) if score_errors else 0,
            'avg_total_error': statistics.mean(total_errors) if total_errors else 0,
            'score_error_std': statistics.stdev(score_errors) if len(score_errors) > 1 else 0,
            'total_error_std': statistics.stdev(total_errors) if len(total_errors) > 1 else 0,
            'actual_home_advantage': statistics.mean(home_advantage_actual) if home_advantage_actual else 0,
        }
        
        # Performance trends
        metrics['performance_issues'] = self._identify_performance_issues(metrics)
        metrics['optimization_targets'] = self._identify_optimization_targets(metrics)
        
        return metrics
    
    def _identify_performance_issues(self, metrics: Dict[str, float]) -> List[str]:
        """Identify specific performance issues based on metrics"""
        issues = []
        
        if metrics['winner_accuracy'] < 0.52:
            issues.append("WINNER_ACCURACY_LOW")
        if metrics['total_accuracy'] < 0.45:
            issues.append("TOTAL_ACCURACY_LOW")
        if metrics['perfect_game_rate'] < 0.15:
            issues.append("PERFECT_GAME_RATE_LOW")
        if metrics['avg_score_error'] > 2.5:
            issues.append("SCORE_PREDICTION_HIGH_ERROR")
        if metrics['avg_total_error'] > 3.0:
            issues.append("TOTAL_PREDICTION_HIGH_ERROR")
        if metrics['score_error_std'] > 2.0:
            issues.append("SCORE_PREDICTION_INCONSISTENT")
        
        return issues
    
    def _identify_optimization_targets(self, metrics: Dict[str, float]) -> Dict[str, str]:
        """Identify which parameters to adjust based on performance issues"""
        targets = {}
        
        # Home field advantage adjustments
        actual_home_adv = metrics.get('actual_home_advantage', 0)
        if actual_home_adv > 0.5:
            targets['home_field_advantage'] = 'INCREASE'
        elif actual_home_adv < -0.2:
            targets['home_field_advantage'] = 'DECREASE'
        
        # Scoring parameter adjustments
        if metrics['avg_total_error'] > 3.0:
            if metrics['avg_score_error'] > 2.5:
                targets['base_lambda'] = 'ADJUST_SCORING_BASELINE'
        
        # Pitcher parameter adjustments
        if metrics['winner_accuracy'] < 0.52:
            targets['pitcher_era_weight'] = 'INCREASE_PITCHER_IMPACT'
        
        # Simulation count adjustments
        if metrics['score_error_std'] > 2.0:
            targets['default_sim_count'] = 'INCREASE_FOR_STABILITY'
        
        return targets
    
    def suggest_parameter_adjustments(self, days: int = 7) -> Dict[str, Any]:
        """Suggest specific parameter adjustments based on recent performance"""
        performance = self.analyze_recent_performance(days)
        
        if not performance:
            return {'error': 'No performance data available'}
        
        # Load current configuration
        try:
            with open(self.config_file, 'r') as f:
                current_config = json.load(f)
        except:
            return {'error': 'No configuration file found'}
        
        suggestions = {
            'current_performance': performance,
            'parameter_adjustments': {},
            'reasoning': [],
            'expected_impact': [],
            'confidence_level': 'MEDIUM'
        }
        
        # Generate specific suggestions based on performance issues
        issues = performance.get('performance_issues', [])
        targets = performance.get('optimization_targets', {})
        
        engine_params = current_config.get('engine_parameters', {})
        
        # Home field advantage adjustments
        if 'home_field_advantage' in targets:
            current_hfa = engine_params.get('home_field_advantage', 0.15)
            actual_hfa = performance.get('actual_home_advantage', 0)
            
            if targets['home_field_advantage'] == 'INCREASE' and current_hfa < 0.25:
                new_hfa = min(0.25, current_hfa + 0.02)
                suggestions['parameter_adjustments']['engine_parameters.home_field_advantage'] = new_hfa
                suggestions['reasoning'].append(f"Increase home field advantage from {current_hfa} to {new_hfa} (actual home advantage: {actual_hfa:.2f})")
                suggestions['expected_impact'].append("Should improve winner accuracy for home teams")
            
            elif targets['home_field_advantage'] == 'DECREASE' and current_hfa > 0.08:
                new_hfa = max(0.08, current_hfa - 0.02)
                suggestions['parameter_adjustments']['engine_parameters.home_field_advantage'] = new_hfa
                suggestions['reasoning'].append(f"Decrease home field advantage from {current_hfa} to {new_hfa} (actual showing less home advantage)")
        
        # Base lambda (scoring) adjustments
        if 'TOTAL_PREDICTION_HIGH_ERROR' in issues:
            current_lambda = engine_params.get('base_lambda', 4.2)
            avg_error = performance.get('avg_total_error', 0)
            
            # Adjust based on error direction (this would need more analysis)
            if avg_error > 3.5:  # Predicting too high or too low consistently
                adjustment = 0.1 if performance.get('winner_accuracy', 0) > 0.5 else -0.1
                new_lambda = max(3.5, min(5.5, current_lambda + adjustment))
                suggestions['parameter_adjustments']['engine_parameters.base_lambda'] = new_lambda
                suggestions['reasoning'].append(f"Adjust base lambda from {current_lambda} to {new_lambda} to reduce total prediction error")
                suggestions['expected_impact'].append("Should improve total run prediction accuracy")
        
        # Pitcher weight adjustments
        if 'WINNER_ACCURACY_LOW' in issues:
            current_era_weight = engine_params.get('pitcher_era_weight', 0.70)
            if current_era_weight < 0.85:
                new_era_weight = min(0.85, current_era_weight + 0.05)
                suggestions['parameter_adjustments']['engine_parameters.pitcher_era_weight'] = new_era_weight
                suggestions['reasoning'].append(f"Increase ERA weight from {current_era_weight} to {new_era_weight} to improve winner predictions")
                suggestions['expected_impact'].append("Should improve winner accuracy by emphasizing pitcher quality")
        
        # Simulation count adjustments
        if 'SCORE_PREDICTION_INCONSISTENT' in issues:
            sim_params = current_config.get('simulation_parameters', {})
            current_sim_count = sim_params.get('default_sim_count', 2000)
            if current_sim_count < 5000:
                new_sim_count = min(5000, current_sim_count + 1000)
                suggestions['parameter_adjustments']['simulation_parameters.default_sim_count'] = new_sim_count
                suggestions['reasoning'].append(f"Increase simulation count from {current_sim_count} to {new_sim_count} for more stable predictions")
                suggestions['expected_impact'].append("Should reduce prediction variability")
        
        # Set confidence level based on data quality
        games_analyzed = performance.get('games_analyzed', 0)
        if games_analyzed >= 20:
            suggestions['confidence_level'] = 'HIGH'
        elif games_analyzed >= 10:
            suggestions['confidence_level'] = 'MEDIUM'
        else:
            suggestions['confidence_level'] = 'LOW'
        
        return suggestions
    
    def apply_parameter_adjustments(self, adjustments: Dict[str, Any], test_first: bool = True) -> Dict[str, Any]:
        """Apply suggested parameter adjustments to the configuration"""
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
        except:
            return {'success': False, 'error': 'Could not load configuration'}
        
        # Apply adjustments
        for param_path, new_value in adjustments.items():
            parts = param_path.split('.')
            current = config
            
            # Navigate to the parameter
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            
            # Set the new value
            old_value = current.get(parts[-1], 'not set')
            current[parts[-1]] = new_value
            logger.info(f"Parameter {param_path}: {old_value} → {new_value}")
        
        # Test configuration if requested
        if test_first:
            test_result = self._test_configuration(config)
            if not test_result['success']:
                return {'success': False, 'error': f'Configuration test failed: {test_result["error"]}'}
        
        # Save configuration
        config['last_updated'] = datetime.now().isoformat()
        config['version'] = f"{config.get('version', '2.0')}_auto_optimized"
        
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        return {'success': True, 'config': config}
    
    def _test_configuration(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Test a configuration by running sample predictions"""
        try:
            engine = UltraFastSimEngine(config=config)
            
            # Test with a few quick predictions
            test_teams = [("Yankees", "Red Sox"), ("Dodgers", "Giants")]
            
            for away, home in test_teams:
                results, pitcher_info = engine.simulate_game_vectorized(away, home, 100)
                if not results or len(results) != 100:
                    return {'success': False, 'error': f'Failed simulation for {away} vs {home}'}
            
            return {'success': True}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def generate_performance_report(self, days: int = 7) -> str:
        """Generate a human-readable performance report with optimization suggestions"""
        performance = self.analyze_recent_performance(days)
        suggestions = self.suggest_parameter_adjustments(days)
        
        if not performance:
            return "❌ No performance data available for analysis"
        
        report = f"""
📊 MLB Prediction Engine Performance Report
==========================================
📅 Analysis Period: {performance.get('date_range', 'Unknown')}
🎯 Games Analyzed: {performance.get('games_analyzed', 0)}

🎲 Current Performance Metrics:
- Winner Accuracy: {performance.get('winner_accuracy', 0):.1%} (Target: >52%)
- Total Accuracy: {performance.get('total_accuracy', 0):.1%} (Target: >45%)
- Perfect Games: {performance.get('perfect_game_rate', 0):.1%} (Target: >15%)
- Avg Score Error: {performance.get('avg_score_error', 0):.1f} runs
- Avg Total Error: {performance.get('avg_total_error', 0):.1f} runs

🚨 Performance Issues Identified:
"""
        
        issues = performance.get('performance_issues', [])
        if issues:
            for issue in issues:
                report += f"- {issue.replace('_', ' ').title()}\n"
        else:
            report += "- No major issues identified ✅\n"
        
        if 'parameter_adjustments' in suggestions and suggestions['parameter_adjustments']:
            report += f"""
🔧 Recommended Parameter Adjustments:
"""
            for adjustment, reasoning in zip(suggestions['parameter_adjustments'].items(), suggestions['reasoning']):
                param, value = adjustment
                report += f"- {param}: {value}\n  └─ {reasoning}\n"
            
            report += f"""
📈 Expected Impact:
"""
            for impact in suggestions['expected_impact']:
                report += f"- {impact}\n"
            
            report += f"\n🎯 Confidence Level: {suggestions['confidence_level']}\n"
        else:
            report += "\n✅ No parameter adjustments recommended at this time\n"
        
        return report

# Global performance tracker instance
performance_tracker = RealGamePerformanceTracker()
