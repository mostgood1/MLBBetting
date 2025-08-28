#!/usr/bin/env python3
"""
Comprehensive MLB Analysis System
=================================

This system provides multi-dimensional analysis of:
1. Model Predictive Accuracy (winner picking, score accuracy)
2. Betting Line Performance (over/under accuracy vs market)  
3. Betting Recommendation Intelligence (moneyline, runline, total accuracy)
4. Daily Performance Breakdown with game-by-game details
5. Model Improvement Recommendations
6. Betting Strategy Optimization

Author: Baseball Analytics Team
Date: August 2025
"""

import json
import os
import glob
from datetime import datetime, timedelta
from collections import defaultdict
import statistics
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import re

@dataclass
class GamePrediction:
    """Structured game prediction data"""
    date: str
    away_team: str
    home_team: str
    predicted_away_score: float
    predicted_home_score: float
    predicted_total: float
    home_win_probability: float
    actual_away_score: int = None
    actual_home_score: int = None
    actual_total: int = None
    
@dataclass
class BettingLine:
    """Betting line data"""
    moneyline_home: str = None
    moneyline_away: str = None
    total_line: float = None
    total_over_odds: str = None
    total_under_odds: str = None
    runline_home: float = None
    runline_away: float = None

@dataclass
class BettingRecommendation:
    """Betting recommendation data"""
    bet_type: str  # moneyline, runline, total
    recommendation: str
    confidence: str
    edge: float = None
    expected_value: float = None
    reasoning: str = ""

@dataclass
class GameAnalysis:
    """Complete game analysis"""
    prediction: GamePrediction
    betting_lines: BettingLine
    recommendations: List[BettingRecommendation]
    
    # Accuracy metrics
    winner_correct: bool = None
    score_diff_away: float = None
    score_diff_home: float = None
    avg_score_diff: float = None
    total_diff: float = None
    
    # Betting performance
    over_under_correct: bool = None
    model_beat_total_line: bool = None
    recommendation_results: Dict[str, bool] = None

class ComprehensiveMLBAnalyzer:
    """Main analysis system"""
    
    def __init__(self, data_directory: str = "data"):
        self.data_directory = data_directory
        self.team_normalizer = self._load_team_normalizer()
        self.games = []
        self.daily_stats = defaultdict(dict)
        
    def _load_team_normalizer(self) -> Dict[str, str]:
        """Load team name normalization mapping"""
        try:
            with open('team_name_normalizer.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print("⚠️ Warning: team_name_normalizer.json not found, using basic normalization")
            return {}
    
    def normalize_team_name(self, team_name: str) -> str:
        """Normalize team names for consistent matching"""
        if not team_name:
            return ""
        
        # Basic normalization
        normalized = team_name.strip()
        
        # Use normalizer if available
        if normalized in self.team_normalizer:
            return self.team_normalizer[normalized]
            
        # Handle common variations
        if "Los Angeles Angels" in normalized:
            return "Los Angeles Angels"
        elif "Oakland Athletics" in normalized or normalized == "Athletics":
            return "Oakland Athletics"
            
        return normalized
    
    def load_historical_data(self, start_date: str = "2025-08-15", end_date: str = "2025-08-27"):
        """Load all historical data for analysis"""
        print(f">> Loading historical data from {start_date} to {end_date}")
        
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        
        current_dt = start_dt
        total_games = 0
        
        while current_dt <= end_dt:
            date_str = current_dt.strftime("%Y-%m-%d")
            games_loaded = self._load_date_data(date_str)
            total_games += games_loaded
            print(f"[DATE] {date_str}: {games_loaded} games loaded")
            current_dt += timedelta(days=1)
            
        print(f"[OK] Total games loaded: {total_games}")
        return total_games
    
    def _load_date_data(self, date_str: str) -> int:
        """Load data for a specific date"""
        games_loaded = 0
        
        # Load predictions
        predictions = self._load_predictions(date_str)
        if not predictions:
            return 0
            
        # Load final scores
        final_scores = self._load_final_scores(date_str)
        
        # Load betting recommendations
        betting_recs = self._load_betting_recommendations(date_str)
        
        # Process each game
        for game_key, pred_data in predictions.items():
            try:
                game_analysis = self._create_game_analysis(
                    date_str, game_key, pred_data, final_scores, betting_recs
                )
                if game_analysis:
                    self.games.append(game_analysis)
                    games_loaded += 1
            except Exception as e:
                print(f"⚠️ Error processing game {game_key} on {date_str}: {e}")
                
        return games_loaded
    
    def _load_predictions(self, date_str: str) -> Dict:
        """Load predictions for a date from betting recommendations files"""
        # Convert date format for file matching
        date_underscore = date_str.replace('-', '_')
        
        patterns = [
            f"betting_recommendations_{date_underscore}.json",
            f"betting_recommendations_{date_str}.json"
        ]
        
        for pattern in patterns:
            filepath = os.path.join(self.data_directory, pattern)
            if os.path.exists(filepath):
                try:
                    with open(filepath, 'r') as f:
                        data = json.load(f)
                        if 'games' in data:
                            # Convert betting recommendations format to prediction format
                            predictions = {}
                            for game_key, game_data in data['games'].items():
                                # Parse predicted score
                                predicted_score = game_data.get('predicted_score', '0-0')
                                if '-' in predicted_score:
                                    away_score, home_score = predicted_score.split('-')
                                    try:
                                        predicted_away_score = float(away_score)
                                        predicted_home_score = float(home_score)
                                    except ValueError:
                                        predicted_away_score = 0.0
                                        predicted_home_score = 0.0
                                else:
                                    predicted_away_score = 0.0
                                    predicted_home_score = 0.0
                                
                                predictions[game_key] = {
                                    'predicted_away_score': predicted_away_score,
                                    'predicted_home_score': predicted_home_score,
                                    'predicted_total_runs': game_data.get('predicted_total_runs', 0),
                                    'home_win_probability': game_data.get('win_probabilities', {}).get('home_prob', 0.5) * 100,
                                    'away_team': game_data.get('away_team', ''),
                                    'home_team': game_data.get('home_team', ''),
                                    'away_pitcher': game_data.get('away_pitcher', 'TBD'),
                                    'home_pitcher': game_data.get('home_pitcher', 'TBD'),
                                    'betting_data': {
                                        'total': {
                                            'line': self._extract_total_line(game_data.get('value_bets', []))
                                        }
                                    }
                                }
                            return predictions
                except Exception as e:
                    print(f"⚠️ Error loading {filepath}: {e}")
        
        return {}
    
    def _extract_total_line(self, value_bets: List[Dict]) -> Optional[float]:
        """Extract total line from value bets"""
        for bet in value_bets:
            if bet.get('type') == 'total' and 'betting_line' in bet:
                return bet['betting_line']
        return None
    
    def _load_final_scores(self, date_str: str) -> Dict:
        """Load final scores for a date"""
        # Convert date format for file matching
        date_underscore = date_str.replace('-', '_')
        
        patterns = [
            f"final_scores_{date_underscore}.json",
            f"final_scores_{date_str}.json",
            f"scores_{date_str}.json"
        ]
        
        for pattern in patterns:
            filepath = os.path.join(self.data_directory, pattern)
            if os.path.exists(filepath):
                try:
                    with open(filepath, 'r') as f:
                        data = json.load(f)
                        # Convert array format to dict format
                        if isinstance(data, list):
                            score_dict = {}
                            for game in data:
                                away_team = self.normalize_team_name(game.get('away_team', ''))
                                home_team = self.normalize_team_name(game.get('home_team', ''))
                                key1 = f"{away_team}_vs_{home_team}"
                                key2 = f"{away_team} @ {home_team}"
                                game_data = {
                                    'away_score': game.get('away_score'),
                                    'home_score': game.get('home_score'),
                                    'final_away_score': game.get('away_score'),
                                    'final_home_score': game.get('home_score')
                                }
                                score_dict[key1] = game_data
                                score_dict[key2] = game_data
                            return score_dict
                        return data
                except Exception as e:
                    print(f"⚠️ Error loading {filepath}: {e}")
        
        return {}
    
    def _load_betting_recommendations(self, date_str: str) -> Dict:
        """Load betting recommendations for a date"""
        # Convert date format for file matching
        date_underscore = date_str.replace('-', '_')
        
        patterns = [
            f"betting_recommendations_{date_underscore}.json",
            f"betting_recommendations_{date_str}.json",
            f"value_bets_{date_str}.json"
        ]
        
        for pattern in patterns:
            filepath = os.path.join(self.data_directory, pattern)
            if os.path.exists(filepath):
                try:
                    with open(filepath, 'r') as f:
                        return json.load(f)
                except Exception as e:
                    print(f"⚠️ Error loading {filepath}: {e}")
        
        return {}
    
    def _create_game_analysis(self, date_str: str, game_key: str, pred_data: Dict, 
                            final_scores: Dict, betting_recs: Dict) -> Optional[GameAnalysis]:
        """Create comprehensive game analysis"""
        
        # Handle nested predictions structure in newer format
        if 'predictions' in pred_data and isinstance(pred_data['predictions'], dict):
            if 'predictions' in pred_data['predictions']:
                # Double nested predictions format
                actual_pred_data = pred_data['predictions']['predictions']
            else:
                # Single nested predictions format
                actual_pred_data = pred_data['predictions']
        else:
            # Legacy format - predictions at root level
            actual_pred_data = pred_data
        
        # Extract team names from game key
        if " @ " in game_key:
            away_team, home_team = game_key.split(" @ ")
        elif "_vs_" in game_key:
            away_team, home_team = game_key.split("_vs_")
        else:
            print(f"⚠️ Cannot parse game key: {game_key}")
            return None
            
        away_team = self.normalize_team_name(away_team)
        home_team = self.normalize_team_name(home_team)
        
        # Create prediction object with proper field mapping
        prediction = GamePrediction(
            date=date_str,
            away_team=away_team,
            home_team=home_team,
            predicted_away_score=actual_pred_data.get('predicted_away_score', 0),
            predicted_home_score=actual_pred_data.get('predicted_home_score', 0),
            predicted_total=actual_pred_data.get('predicted_total_runs', 0),
            home_win_probability=actual_pred_data.get('home_win_prob', actual_pred_data.get('home_win_probability', 50.0)) * (100 if actual_pred_data.get('home_win_prob', 1) <= 1 else 1)
        )
        
        # Find actual scores
        self._add_actual_scores(prediction, final_scores, game_key)
        
        # Extract betting lines - look in both places
        betting_lines = self._extract_betting_lines(pred_data)
        
        # Extract recommendations from the betting_recs file
        recommendations = self._extract_recommendations_from_game_data(pred_data, game_key)
        
        # Create game analysis
        game_analysis = GameAnalysis(
            prediction=prediction,
            betting_lines=betting_lines,
            recommendations=recommendations
        )
        
        # Calculate accuracy metrics
        self._calculate_accuracy_metrics(game_analysis)
        
        # Calculate betting performance
        self._calculate_betting_performance(game_analysis)
        
        return game_analysis
    
    def _add_actual_scores(self, prediction: GamePrediction, final_scores: Dict, game_key: str):
        """Add actual scores to prediction"""
        # Try multiple key formats
        possible_keys = [
            game_key,
            f"{prediction.away_team} @ {prediction.home_team}",
            f"{prediction.away_team}_vs_{prediction.home_team}"
        ]
        
        for key in possible_keys:
            if key in final_scores:
                score_data = final_scores[key]
                prediction.actual_away_score = score_data.get('away_score', score_data.get('final_away_score'))
                prediction.actual_home_score = score_data.get('home_score', score_data.get('final_home_score'))
                if prediction.actual_away_score is not None and prediction.actual_home_score is not None:
                    prediction.actual_total = prediction.actual_away_score + prediction.actual_home_score
                return
                
        # Alternative team name matching
        for key, score_data in final_scores.items():
            if (prediction.away_team in key and prediction.home_team in key) or \
               (prediction.home_team in key and prediction.away_team in key):
                prediction.actual_away_score = score_data.get('away_score', score_data.get('final_away_score'))
                prediction.actual_home_score = score_data.get('home_score', score_data.get('final_home_score'))
                if prediction.actual_away_score is not None and prediction.actual_home_score is not None:
                    prediction.actual_total = prediction.actual_away_score + prediction.actual_home_score
                return
    
    def _extract_betting_lines(self, pred_data: Dict) -> BettingLine:
        """Extract betting line information"""
        # Try multiple locations for betting data
        betting_data = {}
        
        # Check direct betting_data
        if 'betting_data' in pred_data:
            betting_data = pred_data['betting_data']
        
        # Check in nested predictions
        elif 'predictions' in pred_data and isinstance(pred_data['predictions'], dict):
            if 'betting_data' in pred_data['predictions']:
                betting_data = pred_data['predictions']['betting_data']
        
        # Check for individual betting line fields
        if not betting_data:
            # Look for moneyline, total, spread directly
            betting_data = {
                'moneyline': {
                    'home': pred_data.get('home_moneyline'),
                    'away': pred_data.get('away_moneyline')
                },
                'total': {
                    'line': pred_data.get('total_line'),
                    'over': pred_data.get('over_odds'),
                    'under': pred_data.get('under_odds')
                },
                'spread': {
                    'home': pred_data.get('home_spread'),
                    'away': pred_data.get('away_spread')
                }
            }
        
        return BettingLine(
            moneyline_home=betting_data.get('moneyline', {}).get('home'),
            moneyline_away=betting_data.get('moneyline', {}).get('away'),
            total_line=betting_data.get('total', {}).get('line'),
            total_over_odds=betting_data.get('total', {}).get('over'),
            total_under_odds=betting_data.get('total', {}).get('under'),
            runline_home=betting_data.get('spread', {}).get('home'),
            runline_away=betting_data.get('spread', {}).get('away')
        )
    
    def _extract_recommendations_from_game_data(self, pred_data: Dict, game_key: str) -> List[BettingRecommendation]:
        """Extract betting recommendations directly from game data"""
        recommendations = []
        
        # Look for recommendations in various places in the data structure
        recommendation_sources = []
        
        # Check direct recommendations in pred_data
        if 'recommendations' in pred_data:
            recommendation_sources.append(pred_data['recommendations'])
        
        # Check nested recommendations in predictions
        if 'predictions' in pred_data and isinstance(pred_data['predictions'], dict):
            if 'recommendations' in pred_data['predictions']:
                recommendation_sources.append(pred_data['predictions']['recommendations'])
        
        # Process all found recommendation sources
        for rec_source in recommendation_sources:
            if isinstance(rec_source, list):
                for rec in rec_source:
                    if isinstance(rec, dict):
                        # New detailed format
                        rec_type = rec.get('type', 'unknown')
                        recommendation = rec.get('recommendation', rec.get('bet', ''))
                        if not recommendation and rec_type == 'total':
                            # Construct recommendation from betting data
                            if 'direction' in rec:
                                recommendation = f"{rec['direction'].upper()} {rec.get('line', '')}"
                        
                        if recommendation and "No Strong Value" not in recommendation:
                            recommendations.append(BettingRecommendation(
                                bet_type=rec_type,
                                recommendation=recommendation,
                                confidence=rec.get('confidence', 'MEDIUM'),
                                edge=rec.get('edge'),
                                expected_value=rec.get('expected_value'),
                                reasoning=rec.get('reasoning', '')
                            ))
                    elif isinstance(rec, str) and "No Strong Value" not in rec:
                        # Legacy string format
                        recommendations.append(BettingRecommendation(
                            bet_type='unknown',
                            recommendation=rec,
                            confidence='MEDIUM',
                            reasoning=''
                        ))
        
        return recommendations
    
    def _extract_recommendations(self, betting_recs: Dict, game_key: str) -> List[BettingRecommendation]:
        """Extract betting recommendations"""
        recommendations = []
        
        if not betting_recs:
            return recommendations
        
        # Check if this is the full betting recommendations file structure
        if 'games' in betting_recs and game_key in betting_recs['games']:
            game_data = betting_recs['games'][game_key]
            value_bets = game_data.get('value_bets', [])
            
            for bet in value_bets:
                if isinstance(bet, dict):
                    recommendations.append(BettingRecommendation(
                        bet_type=bet.get('type', 'unknown'),
                        recommendation=bet.get('recommendation', ''),
                        confidence=bet.get('confidence', 'MEDIUM'),
                        edge=None,  # Not directly available in this format
                        expected_value=bet.get('expected_value'),
                        reasoning=bet.get('reasoning', '')
                    ))
        elif game_key in betting_recs:
            # Direct game data format
            game_recs = betting_recs[game_key]
            
            # Handle new format (value_bets)
            if 'value_bets' in game_recs:
                for bet in game_recs['value_bets']:
                    if isinstance(bet, dict):
                        recommendations.append(BettingRecommendation(
                            bet_type=bet.get('type', 'unknown'),
                            recommendation=bet.get('recommendation', ''),
                            confidence=bet.get('confidence', 'MEDIUM'),
                            edge=bet.get('edge'),
                            expected_value=bet.get('expected_value'),
                            reasoning=bet.get('reasoning', '')
                        ))
            
            # Handle legacy format (recommendations)
            elif 'recommendations' in game_recs:
                for rec in game_recs['recommendations']:
                    if isinstance(rec, str) and "No Strong Value" not in rec:
                        recommendations.append(BettingRecommendation(
                            bet_type='unknown',
                            recommendation=rec,
                            confidence='MEDIUM',
                            reasoning=''
                        ))
        
        return recommendations
    
    def _calculate_accuracy_metrics(self, game_analysis: GameAnalysis):
        """Calculate prediction accuracy metrics"""
        pred = game_analysis.prediction
        
        if pred.actual_away_score is None or pred.actual_home_score is None:
            return
        
        # Winner accuracy
        predicted_winner = 'home' if pred.predicted_home_score > pred.predicted_away_score else 'away'
        actual_winner = 'home' if pred.actual_home_score > pred.actual_away_score else 'away'
        game_analysis.winner_correct = (predicted_winner == actual_winner)
        
        # Score accuracy
        game_analysis.score_diff_away = abs(pred.predicted_away_score - pred.actual_away_score)
        game_analysis.score_diff_home = abs(pred.predicted_home_score - pred.actual_home_score)
        game_analysis.avg_score_diff = (game_analysis.score_diff_away + game_analysis.score_diff_home) / 2
        
        # Total runs accuracy
        game_analysis.total_diff = abs(pred.predicted_total - pred.actual_total)
    
    def _calculate_betting_performance(self, game_analysis: GameAnalysis):
        """Calculate betting line performance"""
        pred = game_analysis.prediction
        lines = game_analysis.betting_lines
        
        if pred.actual_total is None:
            return
        
        # Over/Under performance vs betting line
        if lines.total_line is not None:
            game_analysis.over_under_correct = (
                (pred.predicted_total > lines.total_line and pred.actual_total > lines.total_line) or
                (pred.predicted_total < lines.total_line and pred.actual_total < lines.total_line)
            )
            game_analysis.model_beat_total_line = game_analysis.over_under_correct
        
        # Evaluate recommendation results
        game_analysis.recommendation_results = {}
        for rec in game_analysis.recommendations:
            result = self._evaluate_recommendation(rec, game_analysis)
            game_analysis.recommendation_results[rec.recommendation] = result
    
    def _evaluate_recommendation(self, rec: BettingRecommendation, game_analysis: GameAnalysis) -> bool:
        """Evaluate if a betting recommendation was correct"""
        pred = game_analysis.prediction
        lines = game_analysis.betting_lines
        
        if pred.actual_total is None:
            return False
        
        rec_text = rec.recommendation.lower()
        
        # Total bets
        if 'over' in rec_text and lines.total_line:
            return pred.actual_total > lines.total_line
        elif 'under' in rec_text and lines.total_line:
            return pred.actual_total < lines.total_line
        
        # Moneyline bets
        elif pred.home_team.lower() in rec_text or 'home' in rec_text:
            return pred.actual_home_score > pred.actual_away_score
        elif pred.away_team.lower() in rec_text or 'away' in rec_text:
            return pred.actual_away_score > pred.actual_home_score
        
        return False
    
    def generate_comprehensive_report(self) -> Dict:
        """Generate the complete analysis report"""
        print("[STATS] Generating comprehensive analysis report...")
        
        report = {
            'analysis_timestamp': datetime.now().isoformat(),
            'total_games_analyzed': len(self.games),
            'date_range': self._get_date_range(),
            'model_predictive_accuracy': self._analyze_model_accuracy(),
            'betting_line_performance': self._analyze_betting_performance(),
            'recommendation_intelligence': self._analyze_recommendation_performance(),
            'daily_breakdown': self._generate_daily_breakdown(),
            'improvement_recommendations': self._generate_improvement_recommendations(),
            'detailed_game_analysis': self._generate_detailed_game_analysis()
        }
        
        # Save report
        with open('comprehensive_mlb_analysis_report.json', 'w') as f:
            json.dump(report, f, indent=2)
        
        print("[OK] Report saved to comprehensive_mlb_analysis_report.json")
        return report
    
    def _get_date_range(self) -> Dict:
        """Get date range of analysis"""
        if not self.games:
            return {}
        
        dates = [game.prediction.date for game in self.games]
        return {
            'start_date': min(dates),
            'end_date': max(dates),
            'total_days': len(set(dates))
        }
    
    def _analyze_model_accuracy(self) -> Dict:
        """Analyze model's predictive accuracy"""
        valid_games = [g for g in self.games if g.winner_correct is not None]
        
        if not valid_games:
            return {'error': 'No valid games for analysis'}
        
        # Winner prediction accuracy
        winner_correct = sum(1 for g in valid_games if g.winner_correct)
        winner_accuracy = (winner_correct / len(valid_games)) * 100
        
        # Score accuracy metrics
        avg_score_diffs = [g.avg_score_diff for g in valid_games if g.avg_score_diff is not None]
        total_diffs = [g.total_diff for g in valid_games if g.total_diff is not None]
        
        # Accuracy by precision levels
        within_1_run = sum(1 for diff in avg_score_diffs if diff <= 1.0)
        within_2_runs = sum(1 for diff in avg_score_diffs if diff <= 2.0)
        within_3_runs = sum(1 for diff in avg_score_diffs if diff <= 3.0)
        
        total_within_1 = sum(1 for diff in total_diffs if diff <= 1.0)
        total_within_2 = sum(1 for diff in total_diffs if diff <= 2.0)
        total_within_3 = sum(1 for diff in total_diffs if diff <= 3.0)
        
        return {
            'total_games': len(valid_games),
            'winner_prediction': {
                'correct_predictions': winner_correct,
                'accuracy_percentage': round(winner_accuracy, 2),
                'incorrect_predictions': len(valid_games) - winner_correct
            },
            'score_accuracy': {
                'average_score_error': round(statistics.mean(avg_score_diffs) if avg_score_diffs else 0, 2),
                'median_score_error': round(statistics.median(avg_score_diffs) if avg_score_diffs else 0, 2),
                'within_1_run_percent': round((within_1_run / len(avg_score_diffs)) * 100 if avg_score_diffs else 0, 2),
                'within_2_runs_percent': round((within_2_runs / len(avg_score_diffs)) * 100 if avg_score_diffs else 0, 2),
                'within_3_runs_percent': round((within_3_runs / len(avg_score_diffs)) * 100 if avg_score_diffs else 0, 2)
            },
            'total_runs_accuracy': {
                'average_total_error': round(statistics.mean(total_diffs) if total_diffs else 0, 2),
                'median_total_error': round(statistics.median(total_diffs) if total_diffs else 0, 2),
                'within_1_run_percent': round((total_within_1 / len(total_diffs)) * 100 if total_diffs else 0, 2),
                'within_2_runs_percent': round((total_within_2 / len(total_diffs)) * 100 if total_diffs else 0, 2),
                'within_3_runs_percent': round((total_within_3 / len(total_diffs)) * 100 if total_diffs else 0, 2)
            }
        }
    
    def _analyze_betting_performance(self) -> Dict:
        """Analyze performance against betting lines"""
        valid_games = [g for g in self.games if g.over_under_correct is not None]
        
        if not valid_games:
            return {'error': 'No valid betting line data'}
        
        correct_predictions = sum(1 for g in valid_games if g.over_under_correct)
        accuracy = (correct_predictions / len(valid_games)) * 100
        
        return {
            'total_games_with_lines': len(valid_games),
            'over_under_accuracy': {
                'correct_predictions': correct_predictions,
                'accuracy_percentage': round(accuracy, 2),
                'incorrect_predictions': len(valid_games) - correct_predictions
            },
            'line_beating_performance': {
                'model_beat_line': correct_predictions,
                'model_followed_line': len(valid_games) - correct_predictions,
                'edge_percentage': round(accuracy - 50, 2)  # Edge over random
            }
        }
    
    def _analyze_recommendation_performance(self) -> Dict:
        """Analyze betting recommendation accuracy"""
        all_recommendations = []
        for game in self.games:
            for rec in game.recommendations:
                if rec.recommendation in game.recommendation_results:
                    all_recommendations.append({
                        'type': rec.bet_type,
                        'confidence': rec.confidence,
                        'correct': game.recommendation_results[rec.recommendation],
                        'edge': rec.edge,
                        'expected_value': rec.expected_value
                    })
        
        if not all_recommendations:
            return {'error': 'No betting recommendations found'}
        
        # Overall accuracy
        correct_recs = sum(1 for r in all_recommendations if r['correct'])
        total_recs = len(all_recommendations)
        overall_accuracy = (correct_recs / total_recs) * 100
        
        # Accuracy by confidence level
        by_confidence = defaultdict(list)
        for rec in all_recommendations:
            by_confidence[rec['confidence']].append(rec['correct'])
        
        confidence_stats = {}
        for conf, results in by_confidence.items():
            correct = sum(results)
            total = len(results)
            confidence_stats[conf] = {
                'correct': correct,
                'total': total,
                'accuracy': round((correct / total) * 100, 2)
            }
        
        # Accuracy by bet type
        by_type = defaultdict(list)
        for rec in all_recommendations:
            by_type[rec['type']].append(rec['correct'])
        
        type_stats = {}
        for bet_type, results in by_type.items():
            correct = sum(results)
            total = len(results)
            type_stats[bet_type] = {
                'correct': correct,
                'total': total,
                'accuracy': round((correct / total) * 100, 2)
            }
        
        return {
            'total_recommendations': total_recs,
            'overall_accuracy': {
                'correct_recommendations': correct_recs,
                'accuracy_percentage': round(overall_accuracy, 2)
            },
            'by_confidence_level': confidence_stats,
            'by_bet_type': type_stats,
            'high_value_performance': self._analyze_high_value_bets(all_recommendations)
        }
    
    def _analyze_high_value_bets(self, recommendations: List[Dict]) -> Dict:
        """Analyze performance of high-value betting recommendations"""
        high_value_bets = [r for r in recommendations if r.get('expected_value', 0) > 0.05]  # >5% EV
        
        if not high_value_bets:
            return {'message': 'No high-value bets identified'}
        
        correct = sum(1 for r in high_value_bets if r['correct'])
        total = len(high_value_bets)
        
        return {
            'total_high_value_bets': total,
            'correct': correct,
            'accuracy': round((correct / total) * 100, 2),
            'average_ev': round(statistics.mean([r.get('expected_value', 0) for r in high_value_bets]), 4)
        }
    
    def _generate_daily_breakdown(self) -> Dict:
        """Generate daily performance breakdown"""
        daily_stats = defaultdict(lambda: {
            'games': 0,
            'winner_correct': 0,
            'avg_score_error': [],
            'total_error': [],
            'betting_line_correct': 0,
            'betting_line_games': 0,
            'recommendations': 0,
            'recommendations_correct': 0
        })
        
        for game in self.games:
            date = game.prediction.date
            stats = daily_stats[date]
            
            stats['games'] += 1
            
            if game.winner_correct is not None:
                if game.winner_correct:
                    stats['winner_correct'] += 1
            
            if game.avg_score_diff is not None:
                stats['avg_score_error'].append(game.avg_score_diff)
            
            if game.total_diff is not None:
                stats['total_error'].append(game.total_diff)
            
            if game.over_under_correct is not None:
                stats['betting_line_games'] += 1
                if game.over_under_correct:
                    stats['betting_line_correct'] += 1
            
            for rec_result in (game.recommendation_results or {}).values():
                stats['recommendations'] += 1
                if rec_result:
                    stats['recommendations_correct'] += 1
        
        # Calculate percentages
        formatted_daily = {}
        for date, stats in daily_stats.items():
            formatted_daily[date] = {
                'total_games': stats['games'],
                'winner_accuracy': round((stats['winner_correct'] / stats['games']) * 100, 2) if stats['games'] > 0 else 0,
                'avg_score_error': round(statistics.mean(stats['avg_score_error']), 2) if stats['avg_score_error'] else 0,
                'total_runs_error': round(statistics.mean(stats['total_error']), 2) if stats['total_error'] else 0,
                'betting_line_accuracy': round((stats['betting_line_correct'] / stats['betting_line_games']) * 100, 2) if stats['betting_line_games'] > 0 else 0,
                'recommendation_accuracy': round((stats['recommendations_correct'] / stats['recommendations']) * 100, 2) if stats['recommendations'] > 0 else 0,
                'total_recommendations': stats['recommendations']
            }
        
        return formatted_daily
    
    def _generate_improvement_recommendations(self) -> Dict:
        """Generate recommendations for model improvement"""
        recommendations = {
            'model_accuracy_improvements': [],
            'betting_strategy_improvements': [],
            'data_quality_issues': []
        }
        
        # Analyze model accuracy patterns
        model_stats = self._analyze_model_accuracy()
        if model_stats.get('winner_prediction', {}).get('accuracy_percentage', 0) < 60:
            recommendations['model_accuracy_improvements'].append({
                'issue': 'Low winner prediction accuracy',
                'current_rate': f"{model_stats['winner_prediction']['accuracy_percentage']}%",
                'recommendation': 'Review pitcher factors and team strength calculations',
                'priority': 'HIGH'
            })
        
        if model_stats.get('score_accuracy', {}).get('average_score_error', 0) > 2.0:
            recommendations['model_accuracy_improvements'].append({
                'issue': 'High average score error',
                'current_error': f"{model_stats['score_accuracy']['average_score_error']} runs",
                'recommendation': 'Improve run environment factors and park effects',
                'priority': 'MEDIUM'
            })
        
        # Analyze betting performance
        betting_stats = self._analyze_betting_performance()
        if betting_stats.get('over_under_accuracy', {}).get('accuracy_percentage', 0) < 55:
            recommendations['betting_strategy_improvements'].append({
                'issue': 'Poor over/under performance vs market',
                'current_rate': f"{betting_stats['over_under_accuracy']['accuracy_percentage']}%",
                'recommendation': 'Recalibrate total runs model and weather factors',
                'priority': 'HIGH'
            })
        
        # Analyze recommendation system
        rec_stats = self._analyze_recommendation_performance()
        if 'overall_accuracy' in rec_stats and rec_stats.get('overall_accuracy', {}).get('accuracy_percentage', 0) < 55:
            recommendations['betting_strategy_improvements'].append({
                'issue': 'Low betting recommendation accuracy',
                'current_rate': f"{rec_stats['overall_accuracy']['accuracy_percentage']}%",
                'recommendation': 'Improve edge calculation and value identification',
                'priority': 'HIGH'
            })
        
        # Check data quality
        games_with_missing_scores = len([g for g in self.games if g.prediction.actual_total is None])
        if games_with_missing_scores > 0:
            recommendations['data_quality_issues'].append({
                'issue': 'Missing final scores',
                'count': games_with_missing_scores,
                'recommendation': 'Improve score fetching reliability',
                'priority': 'MEDIUM'
            })
        
        return recommendations
    
    def _generate_detailed_game_analysis(self) -> Dict:
        """Generate detailed game-by-game analysis for top/bottom performers"""
        
        # Sort games by various metrics
        valid_games = [g for g in self.games if g.winner_correct is not None and g.avg_score_diff is not None]
        
        if not valid_games:
            return {'error': 'No valid games for detailed analysis'}
        
        # Best predictions (winner correct + low score error)
        best_games = sorted(valid_games, key=lambda g: (g.winner_correct, -g.avg_score_diff))[:5]
        
        # Worst predictions (winner wrong + high score error)
        worst_games = sorted(valid_games, key=lambda g: (not g.winner_correct, g.avg_score_diff))[:5]
        
        def format_game_detail(game):
            return {
                'date': game.prediction.date,
                'matchup': f"{game.prediction.away_team} @ {game.prediction.home_team}",
                'predicted_score': f"{game.prediction.predicted_away_score}-{game.prediction.predicted_home_score}",
                'actual_score': f"{game.prediction.actual_away_score}-{game.prediction.actual_home_score}",
                'winner_correct': game.winner_correct,
                'score_error': round(game.avg_score_diff, 2),
                'total_error': round(game.total_diff, 2) if game.total_diff else None,
                'recommendations': len(game.recommendations),
                'recommendation_success': sum(game.recommendation_results.values()) if game.recommendation_results else 0
            }
        
        return {
            'best_predictions': [format_game_detail(g) for g in best_games],
            'worst_predictions': [format_game_detail(g) for g in worst_games],
            'analysis_notes': {
                'best_games_avg_error': round(statistics.mean([g.avg_score_diff for g in best_games]), 2),
                'worst_games_avg_error': round(statistics.mean([g.avg_score_diff for g in worst_games]), 2)
            }
        }
    
    def print_summary_report(self):
        """Print a human-readable summary report"""
        print("\n" + "="*80)
        print(">>  COMPREHENSIVE MLB ANALYSIS REPORT")
        print("="*80)
        
        print(f"\n[STATS] Dataset Overview:")
        print(f"   • Total Games Analyzed: {len(self.games)}")
        date_range = self._get_date_range()
        if date_range:
            print(f"   • Date Range: {date_range['start_date']} to {date_range['end_date']}")
            print(f"   • Total Days: {date_range['total_days']}")
        
        # Model Accuracy
        model_stats = self._analyze_model_accuracy()
        if 'winner_prediction' in model_stats:
            print(f"\n[ACCURACY] Model Predictive Accuracy:")
            wp = model_stats['winner_prediction']
            print(f"   • Winner Predictions: {wp['accuracy_percentage']}% ({wp['correct_predictions']}/{wp['correct_predictions'] + wp['incorrect_predictions']})")
            
            sa = model_stats['score_accuracy']
            print(f"   • Average Score Error: {sa['average_score_error']} runs")
            print(f"   • Within 1 Run: {sa['within_1_run_percent']}%")
            print(f"   • Within 2 Runs: {sa['within_2_runs_percent']}%")
            
            ta = model_stats['total_runs_accuracy']
            print(f"   • Total Runs Error: {ta['average_total_error']} runs")
            print(f"   • Total Within 1 Run: {ta['within_1_run_percent']}%")
        
        # Betting Performance
        betting_stats = self._analyze_betting_performance()
        if 'over_under_accuracy' in betting_stats:
            print(f"\n[BETTING] Betting Line Performance:")
            ou = betting_stats['over_under_accuracy']
            print(f"   • Over/Under Accuracy: {ou['accuracy_percentage']}% ({ou['correct_predictions']}/{ou['correct_predictions'] + ou['incorrect_predictions']})")
            
            edge = betting_stats['line_beating_performance']['edge_percentage']
            print(f"   • Edge Over Market: {edge:+.2f}%")
        
        # Recommendation Performance
        rec_stats = self._analyze_recommendation_performance()
        if 'overall_accuracy' in rec_stats:
            print(f"\n🧠 Betting Recommendation Intelligence:")
            oa = rec_stats['overall_accuracy']
            print(f"   • Overall Accuracy: {oa['accuracy_percentage']}% ({oa['correct_recommendations']}/{rec_stats['total_recommendations']})")
            
            if 'by_confidence_level' in rec_stats:
                print(f"   • By Confidence Level:")
                for conf, stats in rec_stats['by_confidence_level'].items():
                    print(f"     - {conf}: {stats['accuracy']}% ({stats['correct']}/{stats['total']})")
        
        # Top performing days
        daily_breakdown = self._generate_daily_breakdown()
        if daily_breakdown:
            print(f"\n[DAILY] Top Daily Performances:")
            sorted_days = sorted(daily_breakdown.items(), 
                               key=lambda x: x[1]['winner_accuracy'], reverse=True)[:3]
            for date, stats in sorted_days:
                print(f"   • {date}: {stats['winner_accuracy']}% winner accuracy, {stats['total_games']} games")
        
        print("\n" + "="*80)

def main():
    """Main execution function"""
    print(">> Starting Comprehensive MLB Analysis System")
    print("=" * 60)
    
    # Initialize analyzer
    analyzer = ComprehensiveMLBAnalyzer()
    
    # Load historical data
    total_games = analyzer.load_historical_data()
    
    if total_games == 0:
        print("❌ No data found for analysis")
        return
    
    # Generate comprehensive report
    report = analyzer.generate_comprehensive_report()
    
    # Print summary
    analyzer.print_summary_report()
    
    print(f"\n[OK] Analysis complete! Full report saved to 'comprehensive_mlb_analysis_report.json'")
    print(f"[STATS] {total_games} games analyzed across {len(set(g.prediction.date for g in analyzer.games))} days")

if __name__ == "__main__":
    main()
