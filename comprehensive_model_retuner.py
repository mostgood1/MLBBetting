"""
Advanced Model Retuner with Weather/Park/Betting Integration
Comprehensive retuning using actual game results to optimize all model parameters
"""

import json
import os
import numpy as np
from typing import Dict, List, Tuple, Optional
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass
import glob

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class GameResult:
    away_team: str
    home_team: str
    away_score: int
    home_score: int
    total_runs: int
    home_won: bool
    
@dataclass
class GamePrediction:
    away_team: str
    home_team: str
    predicted_away_score: float
    predicted_home_score: float
    predicted_total_runs: float
    home_win_prob: float
    park_weather_factor: float = 1.0
    betting_lines: Dict = None

@dataclass
class ModelPerformance:
    total_games: int
    home_team_accuracy: float
    total_runs_mae: float
    total_runs_rmse: float
    scoring_bias: float
    home_team_bias: float
    park_factor_impact: float
    weather_impact: float

class AdvancedModelRetuner:
    """Advanced model retuner with all new integrations"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.game_results = []
        self.game_predictions = []
        self.performance_metrics = {}
        
    def load_historical_data(self, days_back: int = 7) -> None:
        """Load historical results and predictions for analysis"""
        logger.info(f"📊 Loading {days_back} days of historical data...")
        print(f"📊 Loading {days_back} days of historical data...")
        
        end_date = datetime.now()
        
        for i in range(days_back):
            date = end_date - timedelta(days=i)
            date_str = date.strftime('%Y_%m_%d')
            
            # Load final scores (file or analyzer fallback)
            scores_file = os.path.join(self.data_dir, f'final_scores_{date_str}.json')
            if os.path.exists(scores_file):
                print(f"📄 Loading scores: {scores_file}")
                self._load_final_scores(scores_file, date_str)
            else:
                # Analyzer fallback to retrieve and use final scores if available
                try:
                    from comprehensive_historical_analysis import ComprehensiveHistoricalAnalyzer
                    analyzer = ComprehensiveHistoricalAnalyzer()
                    # Convert date_str back to YYYY-MM-DD
                    d_dash = date.strftime('%Y-%m-%d')
                    scores_obj = analyzer.load_final_scores_for_date(d_dash) or {}
                    if scores_obj:
                        # Normalize to list shape expected by _load_final_scores
                        games = scores_obj.get('games', scores_obj)
                        if isinstance(games, dict):
                            # Write a temporary in-memory list structure
                            scores_list = []
                            for gk, g in games.items():
                                scores_list.append({
                                    'away_team': g.get('away_team') or (gk.split(' vs ')[0] if ' vs ' in gk else None),
                                    'home_team': g.get('home_team') or (gk.split(' vs ')[1] if ' vs ' in gk else None),
                                    'away_score': g.get('away_score', 0),
                                    'home_score': g.get('home_score', 0),
                                })
                        elif isinstance(games, list):
                            scores_list = games
                        else:
                            scores_list = []
                        # Directly ingest the list
                        self._ingest_scores_list(scores_list)
                except Exception as e:
                    logger.debug(f"Analyzer fallback failed for scores {date_str}: {e}")
            
            # Load predictions
            predictions_file = os.path.join(self.data_dir, f'betting_recommendations_{date_str}.json')
            if os.path.exists(predictions_file):
                print(f"📄 Loading predictions: {predictions_file}")
                self._load_predictions(predictions_file, date_str)
        
        logger.info(f"✅ Loaded {len(self.game_results)} game results")
        logger.info(f"✅ Loaded {len(self.game_predictions)} game predictions")
        print(f"✅ Loaded {len(self.game_results)} game results")
        print(f"✅ Loaded {len(self.game_predictions)} game predictions")
    
    def _load_final_scores(self, scores_file: str, date_str: str) -> None:
        """Load final scores from file"""
        try:
            with open(scores_file, 'r') as f:
                scores_data = json.load(f)
            # Support dict or list formats
            if isinstance(scores_data, dict):
                games = scores_data.get('games', scores_data)
                if isinstance(games, dict):
                    scores_list = []
                    for gk, g in games.items():
                        scores_list.append({
                            'away_team': g.get('away_team') or (gk.split(' vs ')[0] if ' vs ' in gk else None),
                            'home_team': g.get('home_team') or (gk.split(' vs ')[1] if ' vs ' in gk else None),
                            'away_score': g.get('away_score', 0),
                            'home_score': g.get('home_score', 0),
                        })
                elif isinstance(games, list):
                    scores_list = games
                else:
                    scores_list = []
            else:
                scores_list = scores_data if isinstance(scores_data, list) else []

            self._ingest_scores_list(scores_list)
                
        except Exception as e:
            logger.warning(f"Could not load scores from {scores_file}: {e}")
            print(f"⚠️ Could not load scores from {scores_file}: {e}")

    def _ingest_scores_list(self, scores_list):
        """Ingest a list of score dicts into game_results"""
        for game in scores_list:
            if not game:
                continue
            try:
                result = GameResult(
                    away_team=game['away_team'],
                    home_team=game['home_team'],
                    away_score=int(game.get('away_score', 0)),
                    home_score=int(game.get('home_score', 0)),
                    total_runs=int(game.get('away_score', 0)) + int(game.get('home_score', 0)),
                    home_won=int(game.get('home_score', 0)) > int(game.get('away_score', 0))
                )
                self.game_results.append(result)
            except Exception:
                continue
    
    def _load_predictions(self, predictions_file: str, date_str: str) -> None:
        """Load predictions from betting recommendations file"""
        try:
            with open(predictions_file, 'r') as f:
                pred_data = json.load(f)
            games = pred_data.get('games', {})
            for game_id, game_data in games.items():
                predictions = game_data.get('predictions', {})
                if isinstance(predictions, dict) and 'predictions' in predictions:
                    pred = predictions['predictions']
                else:
                    pred = predictions
                # Fallback if top-level fields present but no nested predictions
                if (not pred) and ( 'predicted_total_runs' in game_data or 'predicted_score' in game_data or 'win_probabilities' in game_data ):
                    pred = {}
                    away_ps = home_ps = None
                    ps = game_data.get('predicted_score')
                    if isinstance(ps, str) and '-' in ps:
                        try:
                            parts = ps.split('-')
                            if len(parts) == 2:
                                away_ps = float(parts[0])
                                home_ps = float(parts[1])
                        except Exception:
                            pass
                    pred['predicted_away_score'] = away_ps if away_ps is not None else game_data.get('predicted_away_score') or 0
                    pred['predicted_home_score'] = home_ps if home_ps is not None else game_data.get('predicted_home_score') or 0
                    if (pred['predicted_away_score'] == 0 and pred['predicted_home_score'] == 0 and game_data.get('predicted_total_runs')):
                        try:
                            tot = float(game_data.get('predicted_total_runs'))
                            pred['predicted_away_score'] = round(tot / 2, 2)
                            pred['predicted_home_score'] = round(tot / 2, 2)
                        except Exception:
                            pass
                    pred['predicted_total_runs'] = game_data.get('predicted_total_runs', (pred['predicted_away_score'] + pred['predicted_home_score']))
                    win_probs = game_data.get('win_probabilities', {})
                    if isinstance(win_probs, dict):
                        pred['home_win_prob'] = win_probs.get('home_prob', 0.5)
                    predictions = {'betting_lines': game_data.get('betting_lines', {})}
                if not pred:
                    continue
                park_weather_factor = 1.0
                try:
                    date_formatted = date_str
                    park_file = os.path.join(self.data_dir, f'park_weather_factors_{date_formatted}.json')
                    if os.path.exists(park_file):
                        with open(park_file, 'r') as pf:
                            park_data = json.load(pf)
                            home_team = game_data.get('home_team')
                            if home_team in park_data.get('teams', {}):
                                park_weather_factor = park_data['teams'][home_team].get('total_factor', 1.0)
                except:
                    pass
                prediction = GamePrediction(
                    away_team=game_data.get('away_team'),
                    home_team=game_data.get('home_team'),
                    predicted_away_score=pred.get('predicted_away_score', 0),
                    predicted_home_score=pred.get('predicted_home_score', 0),
                    predicted_total_runs=pred.get('predicted_total_runs', 0),
                    home_win_prob=pred.get('home_win_prob', 0.5),
                    park_weather_factor=park_weather_factor,
                    betting_lines=predictions.get('betting_lines', {})
                )
                self.game_predictions.append(prediction)
        except Exception as e:
            logger.warning(f"Could not load predictions from {predictions_file}: {e}")
            print(f"⚠️ Could not load predictions from {predictions_file}: {e}")
    
    def analyze_model_performance(self) -> ModelPerformance:
        """Analyze current model performance against actual results"""
        logger.info("🔍 Analyzing model performance...")
        print("🔍 Analyzing model performance...")
        
        matched_games = self._match_predictions_to_results()
        
        if not matched_games:
            logger.error("❌ No matched games found for analysis")
            print("❌ No matched games found for analysis")
            return None
        
        total_games = len(matched_games)
        
        # Home team accuracy
        home_correct = sum(1 for pred, result in matched_games 
                          if (pred.home_win_prob > 0.5) == result.home_won)
        home_accuracy = home_correct / total_games
        
        # Total runs analysis
        total_errors = [abs(pred.predicted_total_runs - result.total_runs) 
                       for pred, result in matched_games]
        total_mae = np.mean(total_errors)
        total_rmse = np.sqrt(np.mean([e**2 for e in total_errors]))
        
        # Scoring bias analysis
        predicted_totals = [pred.predicted_total_runs for pred, result in matched_games]
        actual_totals = [result.total_runs for pred, result in matched_games]
        scoring_bias = np.mean(predicted_totals) - np.mean(actual_totals)
        
        # Home team bias analysis
        home_predictions = [pred.home_win_prob for pred, result in matched_games]
        actual_home_wins = [1.0 if result.home_won else 0.0 for pred, result in matched_games]
        home_bias = np.mean(home_predictions) - np.mean(actual_home_wins)
        
        # Park factor impact analysis
        park_factors = [pred.park_weather_factor for pred, result in matched_games]
        park_impact = np.std(park_factors) if park_factors else 0.0
        
        performance = ModelPerformance(
            total_games=total_games,
            home_team_accuracy=home_accuracy,
            total_runs_mae=total_mae,
            total_runs_rmse=total_rmse,
            scoring_bias=scoring_bias,
            home_team_bias=home_bias,
            park_factor_impact=park_impact,
            weather_impact=0.0  # Calculate if needed
        )
        
        logger.info(f"📈 Performance Analysis Results:")
        logger.info(f"   Games Analyzed: {total_games}")
        logger.info(f"   Home Team Accuracy: {home_accuracy:.1%}")
        logger.info(f"   Total Runs MAE: {total_mae:.2f}")
        logger.info(f"   Total Runs RMSE: {total_rmse:.2f}")
        logger.info(f"   Scoring Bias: {scoring_bias:+.2f} runs")
        logger.info(f"   Home Team Bias: {home_bias:+.3f}")
        logger.info(f"   Park Factor Variance: {park_impact:.3f}")
        
        print(f"📈 Performance Analysis Results:")
        print(f"   Games Analyzed: {total_games}")
        print(f"   Home Team Accuracy: {home_accuracy:.1%}")
        print(f"   Total Runs MAE: {total_mae:.2f}")
        print(f"   Total Runs RMSE: {total_rmse:.2f}")
        print(f"   Scoring Bias: {scoring_bias:+.2f} runs")
        print(f"   Home Team Bias: {home_bias:+.3f}")
        print(f"   Park Factor Variance: {park_impact:.3f}")
        
        return performance
    
    def _match_predictions_to_results(self) -> List[Tuple[GamePrediction, GameResult]]:
        """Match predictions to actual results"""
        matched = []
        
        for pred in self.game_predictions:
            for result in self.game_results:
                if (pred.away_team == result.away_team and 
                    pred.home_team == result.home_team):
                    matched.append((pred, result))
                    break
        
        return matched
    
    def optimize_parameters(self, performance: ModelPerformance) -> Dict:
        """Generate optimized parameters based on performance analysis"""
        logger.info("⚙️ Optimizing model parameters...")
        print("⚙️ Optimizing model parameters...")
        
        # Load current configuration
        current_config = self._load_current_config()
        
        # Create optimized configuration
        optimized_config = current_config.copy()
        
        # Adjust based on performance metrics
        engine_params = optimized_config.get('engine_parameters', {})
        
        # Scoring bias adjustment
        if abs(performance.scoring_bias) > 0.2:
            current_lambda = engine_params.get('base_lambda', 4.2)
            if performance.scoring_bias > 0:
                # Model predicting too high
                new_lambda = current_lambda * (1 - min(0.1, abs(performance.scoring_bias) / 10))
            else:
                # Model predicting too low
                new_lambda = current_lambda * (1 + min(0.1, abs(performance.scoring_bias) / 10))
            
            engine_params['base_lambda'] = round(new_lambda, 3)
            logger.info(f"🎯 Adjusted base_lambda: {current_lambda:.3f} → {new_lambda:.3f}")
            print(f"🎯 Adjusted base_lambda: {current_lambda:.3f} → {new_lambda:.3f}")
        
        # Home field advantage adjustment
        if abs(performance.home_team_bias) > 0.03:
            current_hfa = engine_params.get('home_field_advantage', 0.15)
            if performance.home_team_bias > 0:
                # Model favoring home teams too much
                new_hfa = current_hfa * (1 - min(0.2, abs(performance.home_team_bias) * 2))
            else:
                # Model not favoring home teams enough
                new_hfa = current_hfa * (1 + min(0.2, abs(performance.home_team_bias) * 2))
            
            engine_params['home_field_advantage'] = round(new_hfa, 3)
            logger.info(f"🏠 Adjusted home_field_advantage: {current_hfa:.3f} → {new_hfa:.3f}")
            print(f"🏠 Adjusted home_field_advantage: {current_hfa:.3f} → {new_hfa:.3f}")
        
        # Total scoring environment adjustment
        current_total_adj = engine_params.get('total_scoring_adjustment', 1.0)
        if abs(performance.scoring_bias) > 0.15:
            if performance.scoring_bias > 0:
                new_total_adj = current_total_adj * (1 - min(0.05, abs(performance.scoring_bias) / 20))
            else:
                new_total_adj = current_total_adj * (1 + min(0.05, abs(performance.scoring_bias) / 20))
            
            engine_params['total_scoring_adjustment'] = round(new_total_adj, 4)
            logger.info(f"📊 Adjusted total_scoring_adjustment: {current_total_adj:.4f} → {new_total_adj:.4f}")
            print(f"📊 Adjusted total_scoring_adjustment: {current_total_adj:.4f} → {new_total_adj:.4f}")
        
        # Enhance park/weather integration if variance is low
        if performance.park_factor_impact < 0.05:
            park_params = optimized_config.get('park_weather_parameters', {})
            park_params['enabled'] = True
            park_params['impact_multiplier'] = park_params.get('impact_multiplier', 1.0) * 1.1
            logger.info("🌤️ Enhanced park/weather impact due to low variance")
            print("🌤️ Enhanced park/weather impact due to low variance")
        
        # Adjust betting integration based on accuracy
        if performance.home_team_accuracy < 0.52:
            betting_params = optimized_config.get('betting_integration', {})
            if betting_params.get('enabled', False):
                current_weight = betting_params.get('betting_weight', 0.25)
                new_weight = min(0.35, current_weight * 1.2)
                betting_params['betting_weight'] = round(new_weight, 3)
                logger.info(f"💰 Increased betting integration weight: {current_weight:.3f} → {new_weight:.3f}")
                print(f"💰 Increased betting integration weight: {current_weight:.3f} → {new_weight:.3f}")
        
        # Update run environment for park factors
        run_env = engine_params.get('run_environment', 0.85)
        if performance.scoring_bias != 0:
            bias_adjustment = -performance.scoring_bias * 0.02
            new_run_env = max(0.75, min(0.95, run_env + bias_adjustment))
            engine_params['run_environment'] = round(new_run_env, 4)
            logger.info(f"🏟️ Adjusted run_environment: {run_env:.4f} → {new_run_env:.4f}")
            print(f"🏟️ Adjusted run_environment: {run_env:.4f} → {new_run_env:.4f}")
        
        # Add metadata
        optimized_config['optimization_metadata'] = {
            'optimization_date': datetime.now().isoformat(),
            'games_analyzed': performance.total_games,
            'performance_metrics': {
                'home_accuracy': performance.home_team_accuracy,
                'total_runs_mae': performance.total_runs_mae,
                'scoring_bias': performance.scoring_bias,
                'home_bias': performance.home_team_bias
            },
            'optimization_version': '3.0_comprehensive_with_integrations'
        }
        
        return optimized_config
    
    def _load_current_config(self) -> Dict:
        """Load current model configuration"""
        config_files = [
            'betting_integrated_config.json',
            'balanced_tuned_config.json',
            'optimized_config.json'
        ]
        
        for config_file in config_files:
            config_path = os.path.join(self.data_dir, config_file)
            if os.path.exists(config_path):
                try:
                    with open(config_path, 'r') as f:
                        print(f"📖 Loading config from: {config_file}")
                        return json.load(f)
                except:
                    continue
        
        # Default configuration
        print("📖 Using default configuration")
        return {
            "version": "3.0_default",
            "engine_parameters": {
                "home_field_advantage": 0.15,
                "base_lambda": 4.2,
                "team_strength_multiplier": 0.20,
                "pitcher_era_weight": 0.70,
                "pitcher_whip_weight": 0.30,
                "game_chaos_variance": 0.42,
                "total_scoring_adjustment": 1.0,
                "run_environment": 0.85
            },
            "betting_integration": {
                "enabled": True,
                "betting_weight": 0.25,
                "line_confidence_threshold": 0.15
            },
            "park_weather_parameters": {
                "enabled": True,
                "impact_multiplier": 1.0
            }
        }
    
    def save_optimized_config(self, config: Dict, filename: str = None) -> str:
        """Save optimized configuration"""
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'comprehensive_optimized_config_{timestamp}.json'
        
        filepath = os.path.join(self.data_dir, filename)
        
        with open(filepath, 'w') as f:
            json.dump(config, f, indent=2)
        
        # Also save as the current optimized config
        current_path = os.path.join(self.data_dir, 'comprehensive_optimized_config.json')
        with open(current_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        logger.info(f"💾 Optimized configuration saved to: {filepath}")
        print(f"💾 Optimized configuration saved to: {filepath}")
        return filepath
    
    def run_comprehensive_optimization(self, days_back: int = 7) -> str:
        """Run complete optimization process"""
        logger.info("🚀 Starting Comprehensive Model Optimization")
        logger.info("=" * 60)
        print("🚀 Starting Comprehensive Model Optimization")
        print("=" * 60)
        
        # Load historical data
        self.load_historical_data(days_back)
        
        if len(self.game_results) == 0 or len(self.game_predictions) == 0:
            logger.error("❌ No historical data available for optimization")
            print("❌ No historical data available for optimization")
            return None
        
        # Analyze performance
        performance = self.analyze_model_performance()
        if not performance:
            return None
        
        # Optimize parameters
        optimized_config = self.optimize_parameters(performance)
        
        # Save configuration
        config_path = self.save_optimized_config(optimized_config)
        
        logger.info("=" * 60)
        logger.info("✅ Comprehensive Model Optimization Complete!")
        logger.info(f"📁 Configuration saved: {config_path}")
        print("=" * 60)
        print("✅ Comprehensive Model Optimization Complete!")
        print(f"📁 Configuration saved: {config_path}")
        
        return config_path

def main():
    """Run the comprehensive model retuning"""
    print("🎯 MLB Model Comprehensive Retuning")
    print("With Weather/Park Factors + Betting Integration")
    print("=" * 70)
    
    try:
        retuner = AdvancedModelRetuner()
        print(f"📂 Using data directory: {retuner.data_dir}")
        config_path = retuner.run_comprehensive_optimization(days_back=10)
    
        if config_path:
            print(f"\n🎉 Retuning Complete!")
            print(f"📁 New configuration: {config_path}")
            print(f"🔄 Restart prediction engine to use new parameters")
        else:
            print(f"\n❌ Retuning failed - insufficient data")
    except Exception as e:
        print(f"❌ Error during optimization: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
