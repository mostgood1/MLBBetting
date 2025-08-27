#!/usr/bin/env python3
"""
Advanced MLB Prediction Model Retuning System
============================================
Analyzes real game results vs predictions to automatically retune the model for:
- Total score accuracy
- Individual team score accuracy  
- Winning team prediction (addressing home team bias)
- Score differential accuracy
- Integration of bullpen factors

Features:
- Performance-based parameter optimization
- Bullpen factor integration
- Home field advantage recalibration
- Pitcher impact rebalancing
- Real-time model adjustment based on actual results
"""

import json
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any, Optional
import statistics
import math
from dataclasses import dataclass

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class GameResult:
    """Structured game result for analysis"""
    date: str
    away_team: str
    home_team: str
    predicted_away_score: float
    predicted_home_score: float
    predicted_total: float
    predicted_winner: str
    predicted_away_prob: float
    predicted_home_prob: float
    actual_away_score: int
    actual_home_score: int
    actual_total: int
    actual_winner: str
    away_pitcher: str = "Unknown"
    home_pitcher: str = "Unknown"

@dataclass 
class BullpenStats:
    """Bullpen statistics for a team"""
    era: float
    whip: float
    saves: int
    blown_saves: int
    innings_pitched: float
    quality_factor: float  # Calculated composite score

class AdvancedModelRetuner:
    """Advanced retuning system for MLB prediction model"""
    
    def __init__(self, data_dir: str = 'data'):
        self.data_dir = data_dir
        self.results_file = os.path.join(data_dir, 'retuning_analysis.json')
        self.config_file = os.path.join(data_dir, 'optimized_model_config.json')
        self.bullpen_file = os.path.join(data_dir, 'bullpen_stats.json')
        
        # Current model parameters (baseline)
        self.current_params = {
            'home_field_advantage': 0.15,
            'base_lambda': 4.2,
            'pitcher_era_weight': 0.70,
            'pitcher_whip_weight': 0.30,
            'team_strength_multiplier': 0.20,
            'game_chaos_variance': 0.42,
            'bullpen_weight': 0.0,  # NEW: Currently not used
            'scoring_adjustment': 1.0,  # NEW: Total scoring calibration
            'home_scoring_boost': 1.0,  # NEW: Home team specific adjustment
            'away_scoring_boost': 1.0,  # NEW: Away team specific adjustment
        }
        
        # Performance targets
        self.targets = {
            'winner_accuracy': 0.54,  # Target 54% winner accuracy
            'total_accuracy_within_1': 0.35,  # 35% within 1 run of total
            'total_accuracy_within_2': 0.60,  # 60% within 2 runs of total
            'avg_score_error': 1.8,  # Average per-team score error < 1.8
            'home_bias_max': 0.58,  # Max home win rate should be ~58%
            'score_differential_accuracy': 0.45,  # Within 2 runs of actual differential
        }

    def collect_game_results(self, days_back: int = 14) -> List[GameResult]:
        """Collect recent game results for analysis"""
        results = []
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        # Scan betting recommendations files for recent dates
        for i in range(days_back):
            date = start_date + timedelta(days=i)
            date_str = date.strftime('%Y_%m_%d')
            
            # Check betting recommendations file
            betting_file = os.path.join(self.data_dir, f'betting_recommendations_{date_str}.json')
            if os.path.exists(betting_file):
                try:
                    with open(betting_file, 'r') as f:
                        betting_data = json.load(f)
                    
                    # Extract games with actual results
                    for game_key, game_data in betting_data.get('games', {}).items():
                        if self._has_final_results(game_data):
                            result = self._extract_game_result(game_data, date.strftime('%Y-%m-%d'))
                            if result:
                                results.append(result)
                                
                except Exception as e:
                    logger.warning(f"Could not process {betting_file}: {e}")
                    continue
        
        logger.info(f"📊 Collected {len(results)} completed games for analysis")
        return results

    def _has_final_results(self, game_data: Dict) -> bool:
        """Check if game has final results available"""
        # Look for actual scores in various possible locations
        if 'actual_away_score' in game_data and 'actual_home_score' in game_data:
            return True
        if 'final_score' in game_data:
            return True
        if 'result' in game_data and game_data['result'].get('status') == 'Final':
            return True
        return False

    def _extract_game_result(self, game_data: Dict, date: str) -> Optional[GameResult]:
        """Extract structured game result from betting data"""
        try:
            # Basic game info
            away_team = game_data.get('away_team', '')
            home_team = game_data.get('home_team', '')
            
            # Predictions
            predictions = game_data.get('predictions', {})
            pred_away = predictions.get('predicted_away_score', 0)
            pred_home = predictions.get('predicted_home_score', 0)
            pred_total = predictions.get('predicted_total_runs', 0)
            pred_away_prob = predictions.get('away_win_prob', 0.5)
            pred_home_prob = predictions.get('home_win_prob', 0.5)
            pred_winner = home_team if pred_home_prob > pred_away_prob else away_team
            
            # Actual results (try multiple sources)
            actual_away = actual_home = actual_total = None
            
            # Method 1: Direct fields
            if 'actual_away_score' in game_data:
                actual_away = game_data['actual_away_score']
                actual_home = game_data['actual_home_score']
                actual_total = actual_away + actual_home
            
            # Method 2: Final score object
            elif 'final_score' in game_data:
                final = game_data['final_score']
                actual_away = final.get('away_score', 0)
                actual_home = final.get('home_score', 0)
                actual_total = actual_away + actual_home
                
            # Method 3: Result object
            elif 'result' in game_data:
                result = game_data['result']
                actual_away = result.get('away_score', 0)
                actual_home = result.get('home_score', 0)
                actual_total = actual_away + actual_home
            
            if actual_away is None or actual_home is None:
                return None
                
            actual_winner = home_team if actual_home > actual_away else away_team
            
            # Pitcher info
            pitcher_info = game_data.get('pitcher_info', {})
            away_pitcher = pitcher_info.get('away_pitcher_name', game_data.get('away_pitcher', 'Unknown'))
            home_pitcher = pitcher_info.get('home_pitcher_name', game_data.get('home_pitcher', 'Unknown'))
            
            return GameResult(
                date=date,
                away_team=away_team,
                home_team=home_team,
                predicted_away_score=float(pred_away),
                predicted_home_score=float(pred_home),
                predicted_total=float(pred_total),
                predicted_winner=pred_winner,
                predicted_away_prob=float(pred_away_prob),
                predicted_home_prob=float(pred_home_prob),
                actual_away_score=int(actual_away),
                actual_home_score=int(actual_home),
                actual_total=int(actual_total),
                actual_winner=actual_winner,
                away_pitcher=away_pitcher,
                home_pitcher=home_pitcher
            )
            
        except Exception as e:
            logger.error(f"Error extracting game result: {e}")
            return None

    def analyze_current_performance(self, results: List[GameResult]) -> Dict[str, Any]:
        """Analyze current model performance against targets"""
        if not results:
            return {}
            
        analysis = {
            'total_games': len(results),
            'date_range': f"{min(r.date for r in results)} to {max(r.date for r in results)}",
            'timestamp': datetime.now().isoformat()
        }
        
        # Winner prediction accuracy
        winner_correct = sum(1 for r in results if r.predicted_winner == r.actual_winner)
        analysis['winner_accuracy'] = winner_correct / len(results)
        
        # Home team bias analysis
        home_wins_predicted = sum(1 for r in results if r.predicted_home_prob > r.predicted_away_prob)
        home_wins_actual = sum(1 for r in results if r.actual_winner == r.home_team)
        analysis['predicted_home_win_rate'] = home_wins_predicted / len(results)
        analysis['actual_home_win_rate'] = home_wins_actual / len(results)
        analysis['home_bias'] = analysis['predicted_home_win_rate'] - analysis['actual_home_win_rate']
        
        # Score prediction accuracy
        away_errors = [abs(r.predicted_away_score - r.actual_away_score) for r in results]
        home_errors = [abs(r.predicted_home_score - r.actual_home_score) for r in results]
        total_errors = [abs(r.predicted_total - r.actual_total) for r in results]
        
        analysis['avg_away_score_error'] = statistics.mean(away_errors)
        analysis['avg_home_score_error'] = statistics.mean(home_errors)
        analysis['avg_total_error'] = statistics.mean(total_errors)
        analysis['avg_score_error'] = (analysis['avg_away_score_error'] + analysis['avg_home_score_error']) / 2
        
        # Total prediction accuracy within thresholds
        analysis['total_within_1'] = sum(1 for err in total_errors if err <= 1) / len(results)
        analysis['total_within_2'] = sum(1 for err in total_errors if err <= 2) / len(results)
        
        # Score differential accuracy
        pred_diffs = [r.predicted_home_score - r.predicted_away_score for r in results]
        actual_diffs = [r.actual_home_score - r.actual_away_score for r in results]
        diff_errors = [abs(pred_diffs[i] - actual_diffs[i]) for i in range(len(results))]
        analysis['avg_differential_error'] = statistics.mean(diff_errors)
        analysis['differential_within_2'] = sum(1 for err in diff_errors if err <= 2) / len(results)
        
        # Scoring bias analysis
        analysis['total_scoring_bias'] = statistics.mean([r.predicted_total - r.actual_total for r in results])
        analysis['home_scoring_bias'] = statistics.mean([r.predicted_home_score - r.actual_home_score for r in results])
        analysis['away_scoring_bias'] = statistics.mean([r.predicted_away_score - r.actual_away_score for r in results])
        
        # Performance issues identification
        issues = []
        if analysis['winner_accuracy'] < self.targets['winner_accuracy']:
            issues.append(f"Winner accuracy {analysis['winner_accuracy']:.3f} below target {self.targets['winner_accuracy']}")
        
        if abs(analysis['home_bias']) > 0.05:
            bias_direction = "favoring home" if analysis['home_bias'] > 0 else "favoring away"
            issues.append(f"Home team bias {analysis['home_bias']:.3f} ({bias_direction})")
            
        if analysis['avg_score_error'] > self.targets['avg_score_error']:
            issues.append(f"Average score error {analysis['avg_score_error']:.2f} above target {self.targets['avg_score_error']}")
            
        if analysis['total_within_2'] < self.targets['total_accuracy_within_2']:
            issues.append(f"Total accuracy within 2 runs {analysis['total_within_2']:.3f} below target {self.targets['total_accuracy_within_2']}")
        
        analysis['performance_issues'] = issues
        
        return analysis

    def load_bullpen_data(self) -> Dict[str, BullpenStats]:
        """Load or generate bullpen statistics for teams"""
        try:
            if os.path.exists(self.bullpen_file):
                with open(self.bullpen_file, 'r') as f:
                    data = json.load(f)
                    
                bullpen_stats = {}
                for team, stats in data.items():
                    bullpen_stats[team] = BullpenStats(**stats)
                return bullpen_stats
        except Exception as e:
            logger.warning(f"Could not load bullpen data: {e}")
        
        # Generate estimated bullpen data based on team strength
        return self._generate_estimated_bullpen_data()

    def _generate_estimated_bullpen_data(self) -> Dict[str, BullpenStats]:
        """Generate estimated bullpen statistics"""
        # MLB team bullpen estimates (simplified)
        teams = [
            "Baltimore Orioles", "Boston Red Sox", "New York Yankees", "Tampa Bay Rays", "Toronto Blue Jays",
            "Chicago White Sox", "Cleveland Guardians", "Detroit Tigers", "Kansas City Royals", "Minnesota Twins",
            "Houston Astros", "Los Angeles Angels", "Athletics", "Seattle Mariners", "Texas Rangers",
            "Atlanta Braves", "Miami Marlins", "New York Mets", "Philadelphia Phillies", "Washington Nationals",
            "Chicago Cubs", "Cincinnati Reds", "Milwaukee Brewers", "Pittsburgh Pirates", "St. Louis Cardinals",
            "Arizona Diamondbacks", "Colorado Rockies", "Los Angeles Dodgers", "San Diego Padres", "San Francisco Giants"
        ]
        
        bullpen_data = {}
        for team in teams:
            # Generate realistic bullpen stats (would be replaced with real data)
            era = 3.5 + (hash(team) % 200) / 100.0  # ERA between 3.5-5.5
            whip = 1.2 + (hash(team) % 60) / 100.0   # WHIP between 1.2-1.8
            saves = 15 + (hash(team) % 30)           # Saves between 15-45
            blown_saves = 3 + (hash(team) % 15)      # Blown saves 3-18
            innings = 450 + (hash(team) % 100)       # IP between 450-550
            
            # Calculate quality factor (lower ERA/WHIP = higher quality)
            quality_factor = max(0.5, min(1.5, 2.0 - ((era - 3.0) / 3.0 + (whip - 1.0) / 1.0) / 2))
            
            bullpen_data[team] = BullpenStats(
                era=era,
                whip=whip,
                saves=saves,
                blown_saves=blown_saves,
                innings_pitched=innings,
                quality_factor=quality_factor
            )
        
        return bullpen_data

    def calculate_optimal_parameters(self, results: List[GameResult], analysis: Dict[str, Any]) -> Dict[str, float]:
        """Calculate optimal model parameters based on performance analysis"""
        new_params = self.current_params.copy()
        adjustments = {}
        
        # 1. Home Field Advantage Adjustment
        home_bias = analysis.get('home_bias', 0)
        if abs(home_bias) > 0.03:  # Significant bias
            hfa_adjustment = -home_bias * 0.5  # Reduce bias by 50%
            new_params['home_field_advantage'] = max(0.05, min(0.25, 
                self.current_params['home_field_advantage'] + hfa_adjustment))
            adjustments['home_field_advantage'] = hfa_adjustment
        
        # 2. Total Scoring Adjustment  
        total_bias = analysis.get('total_scoring_bias', 0)
        if abs(total_bias) > 0.5:  # Consistent over/under prediction
            scoring_adjustment = 1.0 - (total_bias / 10.0)  # Adjust by 10% per run of bias
            new_params['scoring_adjustment'] = max(0.8, min(1.2, scoring_adjustment))
            adjustments['scoring_adjustment'] = scoring_adjustment - 1.0
        
        # 3. Home/Away Scoring Balance
        home_bias_score = analysis.get('home_scoring_bias', 0)
        away_bias_score = analysis.get('away_scoring_bias', 0)
        
        if abs(home_bias_score) > 0.3:
            home_adjustment = 1.0 - (home_bias_score / 8.0)
            new_params['home_scoring_boost'] = max(0.85, min(1.15, home_adjustment))
            adjustments['home_scoring_boost'] = home_adjustment - 1.0
            
        if abs(away_bias_score) > 0.3:
            away_adjustment = 1.0 - (away_bias_score / 8.0)
            new_params['away_scoring_boost'] = max(0.85, min(1.15, away_adjustment))
            adjustments['away_scoring_boost'] = away_adjustment - 1.0
        
        # 4. Pitcher Weight Adjustments (if winner accuracy is low)
        winner_accuracy = analysis.get('winner_accuracy', 0.5)
        if winner_accuracy < self.targets['winner_accuracy']:
            # Increase pitcher impact
            era_weight_adj = min(0.05, (self.targets['winner_accuracy'] - winner_accuracy) * 0.2)
            new_params['pitcher_era_weight'] = min(0.9, self.current_params['pitcher_era_weight'] + era_weight_adj)
            adjustments['pitcher_era_weight'] = era_weight_adj
        
        # 5. Bullpen Factor Introduction
        # Start with modest bullpen weight if not currently used
        if self.current_params['bullpen_weight'] == 0:
            new_params['bullpen_weight'] = 0.15  # Start with 15% bullpen impact
            adjustments['bullpen_weight'] = 0.15
        
        # 6. Base Lambda Adjustment (affects total scoring variance)
        avg_total_error = analysis.get('avg_total_error', 2.0)
        if avg_total_error > 2.5:
            # Reduce variance in scoring
            lambda_adj = -0.1
            new_params['base_lambda'] = max(3.5, min(5.0, self.current_params['base_lambda'] + lambda_adj))
            adjustments['base_lambda'] = lambda_adj
        elif avg_total_error < 1.5:
            # Increase variance
            lambda_adj = 0.1
            new_params['base_lambda'] = max(3.5, min(5.0, self.current_params['base_lambda'] + lambda_adj))
            adjustments['base_lambda'] = lambda_adj
        
        return {
            'new_parameters': new_params,
            'adjustments_made': adjustments,
            'optimization_rationale': self._generate_rationale(analysis, adjustments)
        }

    def _generate_rationale(self, analysis: Dict[str, Any], adjustments: Dict[str, float]) -> List[str]:
        """Generate human-readable rationale for parameter adjustments"""
        rationale = []
        
        if 'home_field_advantage' in adjustments:
            bias = analysis.get('home_bias', 0)
            direction = "reducing" if bias > 0 else "increasing"
            rationale.append(f"Adjusted home field advantage by {adjustments['home_field_advantage']:.3f} ({direction} home team bias of {bias:.3f})")
        
        if 'scoring_adjustment' in adjustments:
            bias = analysis.get('total_scoring_bias', 0)
            direction = "reducing" if bias > 0 else "increasing"
            rationale.append(f"Applied {adjustments['scoring_adjustment']:.3f} total scoring adjustment ({direction} {abs(bias):.2f} run bias)")
        
        if 'home_scoring_boost' in adjustments:
            rationale.append(f"Adjusted home team scoring by {adjustments['home_scoring_boost']:.3f} to correct home scoring bias")
        
        if 'away_scoring_boost' in adjustments:
            rationale.append(f"Adjusted away team scoring by {adjustments['away_scoring_boost']:.3f} to correct away scoring bias")
        
        if 'pitcher_era_weight' in adjustments:
            rationale.append(f"Increased pitcher ERA weight by {adjustments['pitcher_era_weight']:.3f} to improve winner accuracy")
        
        if 'bullpen_weight' in adjustments:
            rationale.append(f"Introduced bullpen factor with {adjustments['bullpen_weight']:.3f} weight to improve late-game prediction accuracy")
        
        if 'base_lambda' in adjustments:
            error = analysis.get('avg_total_error', 2.0)
            direction = "reducing" if adjustments['base_lambda'] < 0 else "increasing"
            rationale.append(f"Adjusted base lambda by {adjustments['base_lambda']:.2f} ({direction} scoring variance, current avg error: {error:.2f})")
        
        return rationale

    def save_retuning_results(self, analysis: Dict[str, Any], optimization: Dict[str, Any]) -> None:
        """Save retuning analysis and results"""
        results = {
            'timestamp': datetime.now().isoformat(),
            'performance_analysis': analysis,
            'optimization_results': optimization,
            'previous_parameters': self.current_params,
            'recommended_parameters': optimization['new_parameters'],
            'performance_targets': self.targets
        }
        
        try:
            with open(self.results_file, 'w') as f:
                json.dump(results, f, indent=2)
            logger.info(f"💾 Saved retuning results to {self.results_file}")
        except Exception as e:
            logger.error(f"Failed to save retuning results: {e}")

    def apply_optimized_parameters(self, new_params: Dict[str, float]) -> None:
        """Apply optimized parameters to the model configuration"""
        config = {
            'version': '3.0_retuned',
            'timestamp': datetime.now().isoformat(),
            'retuning_source': 'advanced_model_retuner',
            'engine_parameters': new_params,
            'bullpen_integration': True,
            'performance_optimized': True
        }
        
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
            logger.info(f"✅ Applied optimized parameters to {self.config_file}")
        except Exception as e:
            logger.error(f"Failed to apply optimized parameters: {e}")

    def run_full_retuning_analysis(self, days_back: int = 14) -> Dict[str, Any]:
        """Run complete retuning analysis and optimization"""
        logger.info("🚀 Starting Advanced MLB Model Retuning Analysis")
        
        # Step 1: Collect recent game results
        logger.info(f"📊 Collecting game results from last {days_back} days...")
        results = self.collect_game_results(days_back)
        
        if len(results) < 10:
            logger.warning(f"Only {len(results)} games found - need at least 10 for reliable analysis")
            return {'error': 'Insufficient data for retuning analysis'}
        
        # Step 2: Analyze current performance
        logger.info("🔍 Analyzing current model performance...")
        analysis = self.analyze_current_performance(results)
        
        # Step 3: Calculate optimal parameters
        logger.info("⚙️ Calculating optimal parameters...")
        optimization = self.calculate_optimal_parameters(results, analysis)
        
        # Step 4: Load bullpen data for integration
        logger.info("🏟️ Loading bullpen data...")
        bullpen_data = self.load_bullpen_data()
        
        # Step 5: Save results
        logger.info("💾 Saving retuning results...")
        self.save_retuning_results(analysis, optimization)
        
        # Step 6: Apply optimized parameters
        logger.info("✅ Applying optimized parameters...")
        self.apply_optimized_parameters(optimization['new_parameters'])
        
        # Generate summary report
        summary = self._generate_summary_report(analysis, optimization, len(results))
        
        logger.info("🎯 Retuning analysis complete!")
        return {
            'success': True,
            'games_analyzed': len(results),
            'analysis': analysis,
            'optimization': optimization,
            'summary': summary,
            'bullpen_teams_loaded': len(bullpen_data)
        }

    def _generate_summary_report(self, analysis: Dict[str, Any], optimization: Dict[str, Any], games_count: int) -> str:
        """Generate human-readable summary report"""
        adjustments = optimization.get('adjustments_made', {})
        rationale = optimization.get('optimization_rationale', [])
        
        report = f"""
🎯 MLB Model Retuning Summary Report
===================================
📊 Analysis: {games_count} games from {analysis.get('date_range', 'unknown period')}

🏆 Current Performance:
  • Winner Accuracy: {analysis.get('winner_accuracy', 0):.1%} (Target: 54%)
  • Total Runs Within 2: {analysis.get('total_within_2', 0):.1%} (Target: 60%)
  • Average Score Error: {analysis.get('avg_score_error', 0):.2f} runs (Target: <1.8)
  • Home Team Bias: {analysis.get('home_bias', 0):.3f} (Target: <0.05)

⚙️ Parameter Adjustments Made: {len(adjustments)}
"""
        
        for reason in rationale:
            report += f"  • {reason}\n"
        
        if not adjustments:
            report += "  • No adjustments needed - model performing within targets\n"
        
        report += f"""
🎲 Model Improvements Expected:
  • Better home/away balance prediction
  • More accurate total scoring
  • Enhanced bullpen factor integration
  • Improved winner prediction accuracy

📈 Next Steps:
  • Monitor performance over next 7-14 days
  • Re-run analysis if new performance issues emerge
  • Fine-tune bullpen factors as more data becomes available
"""
        
        return report

def main():
    """Run the advanced model retuning analysis"""
    print("🚀 Advanced MLB Model Retuning System")
    print("=" * 50)
    
    retuner = AdvancedModelRetuner()
    
    # Run full analysis
    results = retuner.run_full_retuning_analysis(days_back=14)
    
    if results.get('success'):
        print(results['summary'])
        print(f"\n✅ Analysis complete! Processed {results['games_analyzed']} games")
        print(f"📁 Results saved to: {retuner.results_file}")
        print(f"⚙️ Config updated: {retuner.config_file}")
    else:
        print(f"❌ Analysis failed: {results.get('error', 'Unknown error')}")

if __name__ == "__main__":
    main()
