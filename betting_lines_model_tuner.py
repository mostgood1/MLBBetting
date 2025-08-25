#!/usr/bin/env python3
"""
Betting Lines Integration Model Tuner
Incorporates real betting lines to improve model predictions and reduce bias
"""

import json
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import numpy as np
import statistics
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BettingLinesModelTuner:
    """Integrates betting lines into model tuning for improved accuracy"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.current_season = 2025
        
        # File paths
        self.predictions_file = self.data_dir / "master_predictions.json"
        self.betting_lines_pattern = "real_betting_lines_*.json"
        self.historical_pattern = "betting_recommendations_*.json"
        
        # Tuning parameters for betting lines integration
        self.betting_weight = 0.25  # How much to weight betting lines vs model
        self.line_confidence_threshold = 0.15  # Minimum difference to trigger adjustment
        
        # Data storage
        self.historical_data = []
        self.betting_lines_data = {}
        self.model_performance = {}
        
    def load_historical_betting_data(self, days_back: int = 14) -> List[Dict]:
        """Load historical betting data for analysis"""
        logger.info(f"📊 Loading historical betting data for last {days_back} days...")
        
        historical_data = []
        
        # Get date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        # Load historical betting recommendations files
        for i in range(days_back):
            check_date = start_date + timedelta(days=i)
            date_str = check_date.strftime('%Y_%m_%d')
            
            betting_file = self.data_dir / f"betting_recommendations_{date_str}.json"
            
            if betting_file.exists():
                try:
                    with open(betting_file, 'r') as f:
                        daily_data = json.load(f)
                        
                    if 'games' in daily_data:
                        for game_id, game_data in daily_data['games'].items():
                            if self._validate_game_data(game_data):
                                game_data['date'] = check_date.strftime('%Y-%m-%d')
                                game_data['game_id'] = game_id
                                historical_data.append(game_data)
                                
                except Exception as e:
                    logger.debug(f"Could not load {betting_file}: {e}")
        
        logger.info(f"✅ Loaded {len(historical_data)} games from historical data")
        return historical_data
    
    def _validate_game_data(self, game_data: Dict) -> bool:
        """Validate that game data has required fields"""
        # Handle nested structure where prediction data is nested
        if 'predictions' in game_data:
            # Check if it's double-nested
            predictions = game_data['predictions']
            if 'predictions' in predictions:
                prediction = predictions['predictions']
                betting_lines = predictions.get('betting_lines', {})
            else:
                prediction = predictions
                betting_lines = game_data.get('betting_lines', {})
        else:
            prediction = game_data.get('prediction', {})
            betting_lines = game_data.get('betting_lines', {})
        
        # Check prediction fields
        pred_required = ['home_win_prob', 'predicted_total_runs']
        for field in pred_required:
            if field not in prediction:
                return False
        
        # Check betting lines fields
        lines_required = ['home_ml', 'total_line']
        for field in lines_required:
            if field not in betting_lines or betting_lines[field] is None:
                return False
        
        return True
    
    def analyze_model_vs_betting_lines(self) -> Dict[str, Any]:
        """Analyze how our model predictions compare to betting lines"""
        logger.info("🔍 Analyzing model predictions vs betting lines...")
        
        historical_data = self.load_historical_betting_data()
        
        if not historical_data:
            logger.error("❌ No historical data available for analysis")
            return {}
        
        # Analysis metrics
        total_comparisons = 0
        moneyline_differences = []
        total_differences = []
        
        # Model vs Lines analysis
        model_favors_home_more = 0
        model_favors_away_more = 0
        model_higher_totals = 0
        model_lower_totals = 0
        
        for game in historical_data:
            try:
                # Handle nested structure
                if 'predictions' in game:
                    predictions = game['predictions']
                    if 'predictions' in predictions:
                        prediction = predictions['predictions']
                        betting_lines = predictions.get('betting_lines', {})
                    else:
                        prediction = predictions
                        betting_lines = game.get('betting_lines', {})
                else:
                    prediction = game.get('prediction', {})
                    betting_lines = game.get('betting_lines', {})
                
                # Extract data
                model_home_prob = prediction.get('home_win_prob', 0)
                model_total = prediction.get('predicted_total_runs', 0)
                
                lines_home_ml = betting_lines.get('home_ml')
                lines_total = betting_lines.get('total_line')
                
                if not all([model_home_prob, model_total, lines_home_ml, lines_total]):
                    continue
                
                # Convert moneyline to probability
                lines_home_prob = self._moneyline_to_probability(lines_home_ml)
                
                if lines_home_prob is not None:
                    # Moneyline comparison
                    ml_diff = model_home_prob - lines_home_prob
                    moneyline_differences.append(ml_diff)
                    
                    if ml_diff > 0.05:  # Model favors home more than lines
                        model_favors_home_more += 1
                    elif ml_diff < -0.05:  # Model favors away more than lines
                        model_favors_away_more += 1
                
                # Total comparison
                total_diff = model_total - lines_total
                total_differences.append(total_diff)
                
                if total_diff > 0.5:  # Model predicts higher scoring
                    model_higher_totals += 1
                elif total_diff < -0.5:  # Model predicts lower scoring
                    model_lower_totals += 1
                
                total_comparisons += 1
                
            except Exception as e:
                logger.debug(f"Error analyzing game {game.get('game_id', 'unknown')}: {e}")
                continue
        
        if total_comparisons == 0:
            logger.error("❌ No valid comparisons found")
            return {}
        
        # Calculate statistics
        analysis = {
            'total_games_analyzed': total_comparisons,
            'moneyline_analysis': {
                'avg_difference': statistics.mean(moneyline_differences) if moneyline_differences else 0,
                'std_difference': statistics.stdev(moneyline_differences) if len(moneyline_differences) > 1 else 0,
                'model_favors_home_more_pct': (model_favors_home_more / total_comparisons) * 100,
                'model_favors_away_more_pct': (model_favors_away_more / total_comparisons) * 100,
            },
            'total_analysis': {
                'avg_difference': statistics.mean(total_differences) if total_differences else 0,
                'std_difference': statistics.stdev(total_differences) if len(total_differences) > 1 else 0,
                'model_higher_totals_pct': (model_higher_totals / total_comparisons) * 100,
                'model_lower_totals_pct': (model_lower_totals / total_comparisons) * 100,
            },
            'bias_indicators': {
                'home_team_bias': statistics.mean(moneyline_differences) if moneyline_differences else 0,
                'scoring_bias': statistics.mean(total_differences) if total_differences else 0,
            }
        }
        
        logger.info(f"📊 Analysis complete:")
        logger.info(f"   Home team bias: {analysis['bias_indicators']['home_team_bias']:+.3f}")
        logger.info(f"   Scoring bias: {analysis['bias_indicators']['scoring_bias']:+.3f}")
        logger.info(f"   Model higher scoring: {analysis['total_analysis']['model_higher_totals_pct']:.1f}%")
        
        return analysis
    
    def _moneyline_to_probability(self, moneyline: int) -> Optional[float]:
        """Convert American moneyline odds to implied probability"""
        try:
            if moneyline > 0:
                # Positive odds: probability = 100 / (odds + 100)
                return 100 / (moneyline + 100)
            else:
                # Negative odds: probability = abs(odds) / (abs(odds) + 100)
                return abs(moneyline) / (abs(moneyline) + 100)
        except (TypeError, ZeroDivisionError):
            return None
    
    def generate_betting_adjusted_predictions(self, game_data: Dict) -> Dict:
        """Generate predictions adjusted by betting lines"""
        logger.info("🎯 Generating betting-lines-adjusted predictions...")
        
        # Get original prediction
        original_prediction = game_data.get('prediction', {})
        betting_lines = game_data.get('betting_lines', {})
        
        if not original_prediction or not betting_lines:
            logger.warning("⚠️ Missing prediction or betting lines data")
            return original_prediction
        
        # Extract original values
        orig_home_prob = original_prediction.get('home_win_prob', 0.5)
        orig_total = original_prediction.get('predicted_total_runs', 8.5)
        
        # Extract betting lines
        home_ml = betting_lines.get('home_ml')
        total_line = betting_lines.get('total_line')
        
        # Adjust moneyline prediction
        adjusted_home_prob = orig_home_prob
        if home_ml is not None:
            lines_home_prob = self._moneyline_to_probability(home_ml)
            if lines_home_prob is not None:
                # Blend model prediction with lines probability
                adjusted_home_prob = (
                    (1 - self.betting_weight) * orig_home_prob + 
                    self.betting_weight * lines_home_prob
                )
        
        # Adjust total prediction
        adjusted_total = orig_total
        if total_line is not None:
            total_diff = abs(orig_total - total_line)
            if total_diff > self.line_confidence_threshold:
                # Blend model total with lines total
                adjusted_total = (
                    (1 - self.betting_weight) * orig_total + 
                    self.betting_weight * total_line
                )
        
        # Create adjusted prediction
        adjusted_prediction = original_prediction.copy()
        adjusted_prediction['home_win_prob'] = round(adjusted_home_prob, 3)
        adjusted_prediction['away_win_prob'] = round(1 - adjusted_home_prob, 3)
        adjusted_prediction['predicted_total_runs'] = round(adjusted_total, 1)
        
        # Add metadata about adjustments
        adjusted_prediction['betting_adjustments'] = {
            'moneyline_adjusted': abs(adjusted_home_prob - orig_home_prob) > 0.01,
            'total_adjusted': abs(adjusted_total - orig_total) > 0.1,
            'betting_weight_used': self.betting_weight,
            'original_home_prob': orig_home_prob,
            'original_total': orig_total,
            'lines_home_prob': self._moneyline_to_probability(home_ml) if home_ml else None,
            'lines_total': total_line
        }
        
        return adjusted_prediction
    
    def create_betting_integrated_config(self) -> Dict:
        """Create configuration for betting-lines-integrated model"""
        logger.info("⚙️ Creating betting-lines-integrated configuration...")
        
        # Analyze current bias
        analysis = self.analyze_model_vs_betting_lines()
        
        if not analysis:
            logger.error("❌ Cannot create config without analysis data")
            return {}
        
        # Base configuration (start with balanced config)
        base_config = {
            'home_field_advantage': 0.06,
            'away_field_boost': 0.04,
            'bullpen_weight': 0.15,
            'pitcher_weight': 0.35,
            'team_strength_weight': 0.30,
            'run_environment': 0.85,
            'variance_factor': 0.88
        }
        
        # Adjust based on betting lines analysis
        bias_indicators = analysis.get('bias_indicators', {})
        home_bias = bias_indicators.get('home_team_bias', 0)
        scoring_bias = bias_indicators.get('scoring_bias', 0)
        
        # Adjust for home team bias
        if abs(home_bias) > 0.03:  # Significant bias
            if home_bias > 0:  # Model favors home too much
                base_config['home_field_advantage'] *= 0.9
                base_config['away_field_boost'] *= 1.1
            else:  # Model favors away too much
                base_config['home_field_advantage'] *= 1.1
                base_config['away_field_boost'] *= 0.9
        
        # Adjust for scoring bias
        if abs(scoring_bias) > 0.3:  # Significant scoring bias
            if scoring_bias > 0:  # Model predicts too high
                base_config['run_environment'] *= 0.95
            else:  # Model predicts too low
                base_config['run_environment'] *= 1.05
        
        # Add betting lines integration parameters
        betting_config = base_config.copy()
        betting_config.update({
            'betting_integration': {
                'enabled': True,
                'betting_weight': self.betting_weight,
                'line_confidence_threshold': self.line_confidence_threshold,
                'moneyline_bias_correction': -home_bias * 0.5,  # Partial correction
                'scoring_bias_correction': -scoring_bias * 0.3,  # Partial correction
            },
            'analysis_stats': analysis,
            'config_type': 'betting_integrated',
            'created_date': datetime.now().isoformat()
        })
        
        logger.info("✅ Betting-integrated configuration created")
        logger.info(f"   Home bias correction: {betting_config['betting_integration']['moneyline_bias_correction']:+.3f}")
        logger.info(f"   Scoring bias correction: {betting_config['betting_integration']['scoring_bias_correction']:+.3f}")
        
        return betting_config
    
    def save_betting_integrated_config(self, config: Dict) -> bool:
        """Save betting-integrated configuration"""
        try:
            config_file = self.data_dir / "betting_integrated_config.json"
            
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            logger.info(f"✅ Betting-integrated config saved to {config_file}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error saving config: {e}")
            return False
    
    def test_betting_integration(self, sample_games: List[Dict]) -> Dict:
        """Test betting integration on sample games"""
        logger.info("🧪 Testing betting integration on sample games...")
        
        if not sample_games:
            logger.error("❌ No sample games provided")
            return {}
        
        results = {
            'total_tested': len(sample_games),
            'adjustments_made': 0,
            'moneyline_adjustments': 0,
            'total_adjustments': 0,
            'avg_home_prob_change': 0,
            'avg_total_change': 0,
            'sample_comparisons': []
        }
        
        home_prob_changes = []
        total_changes = []
        
        for game in sample_games[:10]:  # Test first 10 games
            try:
                original_pred = game.get('prediction', {})
                adjusted_pred = self.generate_betting_adjusted_predictions(game)
                
                if 'betting_adjustments' in adjusted_pred:
                    adjustments = adjusted_pred['betting_adjustments']
                    
                    if adjustments['moneyline_adjusted'] or adjustments['total_adjusted']:
                        results['adjustments_made'] += 1
                    
                    if adjustments['moneyline_adjusted']:
                        results['moneyline_adjustments'] += 1
                        home_prob_change = adjusted_pred['home_win_prob'] - adjustments['original_home_prob']
                        home_prob_changes.append(home_prob_change)
                    
                    if adjustments['total_adjusted']:
                        results['total_adjustments'] += 1
                        total_change = adjusted_pred['predicted_total_runs'] - adjustments['original_total']
                        total_changes.append(total_change)
                    
                    # Sample comparison
                    comparison = {
                        'game_id': game.get('game_id', 'unknown'),
                        'original_home_prob': adjustments['original_home_prob'],
                        'adjusted_home_prob': adjusted_pred['home_win_prob'],
                        'original_total': adjustments['original_total'],
                        'adjusted_total': adjusted_pred['predicted_total_runs'],
                        'betting_lines': game.get('betting_lines', {})
                    }
                    results['sample_comparisons'].append(comparison)
                    
            except Exception as e:
                logger.debug(f"Error testing game {game.get('game_id', 'unknown')}: {e}")
                continue
        
        # Calculate averages
        if home_prob_changes:
            results['avg_home_prob_change'] = statistics.mean(home_prob_changes)
        
        if total_changes:
            results['avg_total_change'] = statistics.mean(total_changes)
        
        logger.info(f"🧪 Test results:")
        logger.info(f"   Games with adjustments: {results['adjustments_made']}/{results['total_tested']}")
        logger.info(f"   Avg home prob change: {results['avg_home_prob_change']:+.3f}")
        logger.info(f"   Avg total change: {results['avg_total_change']:+.2f}")
        
        return results

def main():
    """Main execution function"""
    logger.info("🎯 Betting Lines Model Tuner Starting")
    logger.info(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    tuner = BettingLinesModelTuner()
    
    # Step 1: Analyze model vs betting lines
    logger.info("\n📊 Step 1: Analyzing Model vs Betting Lines")
    analysis = tuner.analyze_model_vs_betting_lines()
    
    if not analysis:
        logger.error("❌ Analysis failed - cannot proceed")
        return False
    
    # Step 2: Create betting-integrated configuration
    logger.info("\n⚙️ Step 2: Creating Betting-Integrated Configuration")
    config = tuner.create_betting_integrated_config()
    
    if not config:
        logger.error("❌ Configuration creation failed")
        return False
    
    # Step 3: Save configuration
    logger.info("\n💾 Step 3: Saving Configuration")
    if not tuner.save_betting_integrated_config(config):
        logger.error("❌ Configuration save failed")
        return False
    
    # Step 4: Test on sample data
    logger.info("\n🧪 Step 4: Testing Betting Integration")
    historical_data = tuner.load_historical_betting_data(days_back=3)
    
    if historical_data:
        test_results = tuner.test_betting_integration(historical_data)
        
        if test_results:
            logger.info("✅ Testing completed successfully")
        else:
            logger.warning("⚠️ Testing had issues")
    else:
        logger.warning("⚠️ No data available for testing")
    
    logger.info("\n🎉 Betting Lines Model Tuning Complete!")
    logger.info("📋 Summary:")
    logger.info(f"   Home bias detected: {analysis['bias_indicators']['home_team_bias']:+.3f}")
    logger.info(f"   Scoring bias detected: {analysis['bias_indicators']['scoring_bias']:+.3f}")
    logger.info(f"   Configuration saved with bias corrections")
    
    return True

if __name__ == "__main__":
    main()
