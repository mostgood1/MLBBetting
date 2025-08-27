"""
Historical Analysis Endpoint - Comprehensive Model & Betting Performance Analysis
=============================================================================
This module provides detailed analysis of model predictability, betting accuracy, and ROI
for any historical date with complete predictions and final scores.

Analysis Components:
1. Predictability - Model accuracy on winners and score predictions
2. Betting Lens - Performance from a betting perspective (winners + totals)
3. Betting Recommendations - Analysis of recommendation accuracy and types
4. ROI Analysis - Financial performance assuming $100 unit bets
"""

import json
import os
import logging
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request
from typing import Dict, List, Tuple, Optional
from team_name_normalizer import normalize_team_name

# Setup logging
logger = logging.getLogger(__name__)

# Create Blueprint
historical_analysis_bp = Blueprint('historical_analysis', __name__)

class HistoricalAnalyzer:
    """Comprehensive historical analysis for MLB predictions and betting performance"""
    def log_normalized_keys(self, games: Dict, final_scores: Dict):
        logger.info("--- Normalized Keys Comparison ---")
        logger.info("Betting Recommendations Keys:")
        for game_key, game_data in games.items():
            away = self.normalize_team_name(game_data.get('away_team', ''))
            home = self.normalize_team_name(game_data.get('home_team', ''))
            key = f"{away}_vs_{home}"
            logger.info(f"  {key}")
        logger.info("Final Scores Keys:")
        for score_key in final_scores.keys():
            logger.info(f"  {score_key}")
        logger.info("--- End Comparison ---")
"""
Historical Analysis Endpoint - Comprehensive Model & Betting Performance Analysis
=============================================================================
This module provides detailed analysis of model predictability, betting accuracy, and ROI
for any historical date with complete predictions and final scores.

Analysis Components:
1. Predictability - Model accuracy on winners and score predictions
2. Betting Lens - Performance from a betting perspective (winners + totals)
3. Betting Recommendations - Analysis of recommendation accuracy and types
4. ROI Analysis - Financial performance assuming $100 unit bets
"""

import json
import os
import logging
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request
from typing import Dict, List, Tuple, Optional
from team_name_normalizer import normalize_team_name

# Setup logging
logger = logging.getLogger(__name__)

# Create Blueprint
historical_analysis_bp = Blueprint('historical_analysis', __name__)

class HistoricalAnalyzer:
    """Comprehensive historical analysis for MLB predictions and betting performance"""
    
    def __init__(self):
        self.predictions_cache_path = 'data/unified_predictions_cache.json'
        self.base_scores_path = 'data/final_scores_{date}.json'
        
    def normalize_team_name(self, team_name: str) -> str:
        return normalize_team_name(team_name)
    
    def log_normalized_keys(self, games: Dict, final_scores: Dict):
        logger.info("--- Normalized Keys Comparison ---")
        logger.info("Betting Recommendations Keys:")
        for game_key, game_data in games.items():
            away = self.normalize_team_name(game_data.get('away_team', ''))
            home = self.normalize_team_name(game_data.get('home_team', ''))
            key = f"{away}_vs_{home}"
            logger.info(f"  {key}")
        logger.info("Final Scores Keys:")
        for score_key in final_scores.keys():
            logger.info(f"  {score_key}")
        logger.info("--- End Comparison ---")
    
    def load_predictions_for_date(self, target_date: str) -> Dict:
        """Load games from betting_recommendations JSON for specific date"""
        import os
        date_formatted = target_date.replace('-', '_')
        rec_path = os.path.join('data', f'betting_recommendations_{date_formatted}.json')
        try:
            with open(rec_path, 'r') as f:
                rec_data = json.load(f)
            games = rec_data.get('games', {})
            if isinstance(games, dict):
                logger.info(f"Loaded {len(games)} games from betting recommendations for {target_date}")
                return games
            else:
                logger.warning(f"Games key in betting recommendations for {target_date} is not a dict.")
                return {}
        except FileNotFoundError:
            logger.error(f"Betting recommendations file not found: {rec_path}")
            return {}
        except Exception as e:
            logger.error(f"Error loading betting recommendations: {e}")
            return {}
    
    def load_final_scores_for_date(self, target_date: str) -> Dict:
        """Load final scores for specific date"""
        # Convert date format: 2025-08-20 -> 2025_08_20
        date_formatted = target_date.replace('-', '_')
        scores_path = self.base_scores_path.format(date=date_formatted)
        
        try:
            with open(scores_path, 'r') as f:
                scores_list = json.load(f)
            
            # Create lookup dict with normalized team names
            scores_dict = {}
            for score in scores_list:
                away_team = self.normalize_team_name(score['away_team'])
                home_team = self.normalize_team_name(score['home_team'])
                key = f"{away_team}_vs_{home_team}"
                scores_dict[key] = score
            
            logger.info(f"Loaded {len(scores_dict)} final scores for {target_date}")
            return scores_dict
            
        except FileNotFoundError:
            logger.error(f"Final scores not found: {scores_path}")
            return {}
        except Exception as e:
            logger.error(f"Error loading final scores: {e}")
            return {}
    
    def extract_prediction_values(self, game_data: Dict) -> Dict:
        """Extract prediction values from game data with robust fallback logic"""
        # Try multiple nested structures to find predictions
        prediction_obj = game_data.get('prediction', game_data)
        predictions = prediction_obj.get('predictions', prediction_obj)
        
        # Extract team names
        away_team = self.normalize_team_name(prediction_obj.get('away_team', game_data.get('away_team', '')))
        home_team = self.normalize_team_name(prediction_obj.get('home_team', game_data.get('home_team', '')))
        
        # Extract win probabilities with multiple fallback keys
        away_win_prob = None
        home_win_prob = None
        
        # First try the old structure
        for key in ['away_win_probability', 'away_win_prob', 'away_win']:
            if away_win_prob is None:
                away_win_prob = predictions.get(key)
        
        for key in ['home_win_probability', 'home_win_prob', 'home_win']:
            if home_win_prob is None:
                home_win_prob = predictions.get(key)
        
        # NEW: Try the unified betting engine structure (win_probabilities object)
        if away_win_prob is None or home_win_prob is None:
            win_probs = game_data.get('win_probabilities', {})
            if win_probs:
                away_win_prob = win_probs.get('away_prob', away_win_prob)
                home_win_prob = win_probs.get('home_prob', home_win_prob)
        
        # Extract predicted scores with fallback keys
        predicted_away = None
        predicted_home = None
        
        # First try the old structure
        for key in ['predicted_away_score', 'away_score', 'away_runs']:
            if predicted_away is None:
                predicted_away = predictions.get(key)
        
        for key in ['predicted_home_score', 'home_score', 'home_runs']:
            if predicted_home is None:
                predicted_home = predictions.get(key)
        
        # NEW: Try parsing the unified betting engine's "predicted_score" string format
        if predicted_away is None or predicted_home is None:
            predicted_score_str = game_data.get('predicted_score', '')
            if predicted_score_str and '-' in predicted_score_str:
                try:
                    parts = predicted_score_str.split('-')
                    if len(parts) == 2:
                        predicted_away = float(parts[0])
                        predicted_home = float(parts[1])
                except (ValueError, IndexError):
                    pass
        
        # Extract pitchers
        away_pitcher = predictions.get('away_pitcher', game_data.get('away_pitcher', 'TBD'))
        home_pitcher = predictions.get('home_pitcher', game_data.get('home_pitcher', 'TBD'))
        
        return {
            'away_team': away_team,
            'home_team': home_team,
            'away_win_probability': away_win_prob,
            'home_win_probability': home_win_prob,
            'predicted_away_score': predicted_away,
            'predicted_home_score': predicted_home,
            'away_pitcher': away_pitcher,
            'home_pitcher': home_pitcher
        }
    
    def analyze_predictability(self, games: Dict, final_scores: Dict) -> Dict:
        self.log_normalized_keys(games, final_scores)
        """Analyze model predictability - winner accuracy and score accuracy"""
        total_games = len(games)
        winner_correct = 0
        team_score_errors = []
        total_score_errors = []
        matched_games = 0

        logger.info(f"Prediction keys: {list(games.keys())}")
        logger.info(f"Final score keys: {list(final_scores.keys())}")

        for game_key, game_data in games.items():
            pred_values = self.extract_prediction_values(game_data)

            # Skip if essential prediction data is missing
            if not all([
                pred_values['away_team'],
                pred_values['home_team'],
                pred_values['away_win_probability'] is not None,
                pred_values['home_win_probability'] is not None,
                pred_values['predicted_away_score'] is not None,
                pred_values['predicted_home_score'] is not None
            ]):
                continue

            # Find matching final score
            away_norm = self.normalize_team_name(pred_values['away_team'])
            home_norm = self.normalize_team_name(pred_values['home_team'])
            score_key = f"{away_norm}_vs_{home_norm}"

            logger.info(f"Trying to match: {score_key} (from prediction) against final scores keys: {list(final_scores.keys())}")
            final_score = final_scores.get(score_key)
            if not final_score:
                logger.warning(f"No match found for: {score_key}. Away: {pred_values['away_team']} -> {away_norm}, Home: {pred_values['home_team']} -> {home_norm}")
                continue

            matched_games += 1

            # Winner Analysis
            logger.info(f"Win probabilities for game {score_key}: away={pred_values['away_win_probability']} ({type(pred_values['away_win_probability'])}), home={pred_values['home_win_probability']} ({type(pred_values['home_win_probability'])})")
            try:
                away_prob_float = float(pred_values['away_win_probability'])
                home_prob_float = float(pred_values['home_win_probability'])
                predicted_winner = (
                    pred_values['away_team'] if away_prob_float > home_prob_float else pred_values['home_team']
                )
            except (TypeError, ValueError):
                logger.warning(f"Skipping game {score_key} due to invalid win probability values: away={pred_values['away_win_probability']}, home={pred_values['home_win_probability']}")
                continue

            actual_away_score = final_score['away_score']
            actual_home_score = final_score['home_score']
            # Diagnostic: log types and values
            logger.info(f"Scores for game {score_key}: away={actual_away_score} ({type(actual_away_score)}), home={actual_home_score} ({type(actual_home_score)})")
            try:
                away_score_float = float(actual_away_score)
                home_score_float = float(actual_home_score)
            except (TypeError, ValueError):
                logger.warning(f"Skipping game {score_key} due to invalid score values: away={actual_away_score}, home={actual_home_score}")
                continue
            actual_winner = (pred_values['away_team']
                           if away_score_float > home_score_float
                           else pred_values['home_team'])

            if self.normalize_team_name(predicted_winner) == self.normalize_team_name(actual_winner):
                winner_correct += 1

            # Score Analysis
            pred_away = float(pred_values['predicted_away_score'])
            pred_home = float(pred_values['predicted_home_score'])

            # Individual team score errors
            team_score_errors.append(abs(pred_away - actual_away_score))
            team_score_errors.append(abs(pred_home - actual_home_score))

            # Total game score error
            pred_total = pred_away + pred_home
            actual_total = actual_away_score + actual_home_score
            total_score_errors.append(abs(pred_total - actual_total))

        return {
            'total_games': total_games,
            'matched_games': matched_games,
            'winner_accuracy': round(winner_correct / matched_games, 4) if matched_games > 0 else 0.0,
            'avg_team_score_error': round(sum(team_score_errors) / len(team_score_errors), 2) if team_score_errors else 0.0,
            'avg_total_score_error': round(sum(total_score_errors) / len(total_score_errors), 2) if total_score_errors else 0.0,
            'coverage_rate': round(matched_games / total_games, 4) if total_games > 0 else 0.0
        }
    
    def analyze_betting_lens(self, games: Dict, final_scores: Dict) -> Dict:
        """Analyze performance from betting perspective - winners and totals"""
        winner_correct = 0
        total_side_correct = 0
        total_bets = 0
        total_side_bets = 0
        matched_games = 0
        
        for game_key, game_data in games.items():
            pred_values = self.extract_prediction_values(game_data)
            # Skip if essential data missing
            if not all([pred_values['away_team'], pred_values['home_team']]):
                continue
            # Find matching final score using robust normalization
            away_norm = self.normalize_team_name(pred_values['away_team'])
            home_norm = self.normalize_team_name(pred_values['home_team'])
            score_key_vs = f"{away_norm}_vs_{home_norm}"
            score_key_at = f"{away_norm} @ {home_norm}"
            final_score = final_scores.get(score_key_vs)
            if not final_score:
                final_score = final_scores.get(score_key_at)
            if not final_score:
                # Try reverse order
                score_key_vs_rev = f"{home_norm}_vs_{away_norm}"
                score_key_at_rev = f"{home_norm} @ {away_norm}"
                final_score = final_scores.get(score_key_vs_rev)
                if not final_score:
                    final_score = final_scores.get(score_key_at_rev)
            if not final_score:
                continue
            matched_games += 1
            
            # Winner betting analysis (if we have win probabilities)
            if (pred_values['away_win_probability'] is not None and 
                pred_values['home_win_probability'] is not None):
                total_bets += 1
                away_prob = float(pred_values['away_win_probability'])
                home_prob = float(pred_values['home_win_probability'])
                predicted_winner = (pred_values['away_team'] 
                                  if away_prob > home_prob 
                                  else pred_values['home_team'])
                actual_away_score = final_score['away_score']
                actual_home_score = final_score['home_score']
                actual_winner = (pred_values['away_team'] 
                               if actual_away_score > actual_home_score 
                               else pred_values['home_team'])
                if self.normalize_team_name(predicted_winner) == self.normalize_team_name(actual_winner):
                    winner_correct += 1
            
            # Total betting analysis (if we have score predictions)
            if (pred_values['predicted_away_score'] is not None and 
                pred_values['predicted_home_score'] is not None):
                
                total_side_bets += 1
                pred_total = float(pred_values['predicted_away_score']) + float(pred_values['predicted_home_score'])
                actual_total = final_score['away_score'] + final_score['home_score']
                
                # For betting analysis, assume we would bet the side with larger edge
                # This is simplified - in reality we'd need betting lines
                if abs(pred_total - 8.5) > 0.5:  # Using 8.5 as typical MLB total
                    if pred_total > 8.5 and actual_total > 8.5:  # Bet Over, Over hit
                        total_side_correct += 1
                    elif pred_total < 8.5 and actual_total < 8.5:  # Bet Under, Under hit
                        total_side_correct += 1
        
        return {
            'matched_games': matched_games,
            'winner_accuracy': round(winner_correct / total_bets, 4) if total_bets > 0 else 0.0,
            'total_side_accuracy': round(total_side_correct / total_side_bets, 4) if total_side_bets > 0 else 0.0,
            'total_winner_bets': total_bets,
            'total_side_bets': total_side_bets
        }
    
    def analyze_betting_recommendations(self, games: Dict, final_scores: Dict) -> Dict:
        """Analyze betting recommendations accuracy and types"""
        recommendation_types = {'moneyline': 0, 'total': 0, 'run_line': 0, 'other': 0}
        correct_recommendations = {'moneyline': 0, 'total': 0, 'run_line': 0, 'other': 0}
        total_recommendations = 0
        total_correct = 0
        games_with_recommendations = []
        
        for game_key, game_data in games.items():
            pred_values = self.extract_prediction_values(game_data)
            
            # Skip if no team data
            if not all([pred_values['away_team'], pred_values['home_team']]):
                continue
            
            # Find matching final score
            away_norm = self.normalize_team_name(pred_values['away_team'])
            home_norm = self.normalize_team_name(pred_values['home_team'])
            score_key = f"{away_norm}_vs_{home_norm}"
            
            final_score = final_scores.get(score_key)
            if not final_score:
                continue
            
            # Extract betting recommendations - handle nested structure
            recommendations = []
            
            # Method 1: Check nested prediction structure (2025-08-20 format)
            if 'prediction' in game_data and 'recommendations' in game_data['prediction']:
                recommendations = game_data['prediction']['recommendations']
            # Method 2: Check direct recommendations
            elif 'recommendations' in game_data:
                recommendations = game_data['recommendations']
            # Method 3: Check betting_recommendations structure
            else:
                betting_recs = game_data.get('betting_recommendations', {})
                value_bets = betting_recs.get('unified_value_bets', [])
                
                if not value_bets:
                    # Try alternative structure
                    if 'moneyline' in betting_recs and betting_recs['moneyline']:
                        value_bets.append({'type': 'moneyline', 'recommendation': betting_recs['moneyline']})
                    if 'total_runs' in betting_recs and betting_recs['total_runs']:
                        value_bets.append({'type': 'total', 'recommendation': betting_recs['total_runs']})
                    if 'run_line' in betting_recs and betting_recs['run_line']:
                        value_bets.append({'type': 'run_line', 'recommendation': betting_recs['run_line']})
                
                recommendations = value_bets
            
            game_analysis = {
                'game_key': game_key,
                'away_team': pred_values['away_team'],
                'home_team': pred_values['home_team'],
                'recommendations': [],
                'total_correct': 0,
                'total_recommendations': len(recommendations)
            }
            
            for rec in recommendations:
                total_recommendations += 1
                rec_type = rec.get('type', 'other').lower()
                
                # Count recommendation type
                if rec_type in recommendation_types:
                    recommendation_types[rec_type] += 1
                else:
                    recommendation_types['other'] += 1
                
                # Check if recommendation was correct
                is_correct = self.check_recommendation_accuracy(rec, final_score, pred_values)
                
                rec_analysis = {
                    'type': rec_type,
                    'side': rec.get('side', rec.get('recommendation', 'unknown')),
                    'line': rec.get('line', 0),
                    'odds': rec.get('odds', rec.get('odds', 0)),
                    'expected_value': rec.get('expected_value', 0),
                    'confidence': rec.get('confidence', 'UNKNOWN'),
                    'reasoning': rec.get('reasoning', ''),
                    'is_correct': is_correct,
                    'payout': self._calculate_payout(rec, is_correct)
                }
                
                game_analysis['recommendations'].append(rec_analysis)
                
                if is_correct:
                    total_correct += 1
                    game_analysis['total_correct'] += 1
                    if rec_type in correct_recommendations:
                        correct_recommendations[rec_type] += 1
                    else:
                        correct_recommendations['other'] += 1
            
            if recommendations:
                games_with_recommendations.append(game_analysis)
        
        # Calculate accuracy by type
        accuracy_by_type = {}
        for rec_type in recommendation_types:
            total_type = recommendation_types[rec_type]
            correct_type = correct_recommendations[rec_type]
            accuracy_by_type[rec_type] = round(correct_type / total_type, 4) if total_type > 0 else 0.0
        
        return {
            'total_recommendations': total_recommendations,
            'total_correct': total_correct,
            'overall_accuracy': round(total_correct / total_recommendations, 4) if total_recommendations > 0 else 0.0,
            'recommendation_types': recommendation_types,
            'accuracy_by_type': accuracy_by_type,
            'games_with_recommendations': games_with_recommendations
        }
    
    def check_recommendation_accuracy(self, recommendation: Dict, final_score: Dict, pred_values: Dict) -> bool:
        """Check if a specific recommendation was correct"""
        rec_type = recommendation.get('type', '').lower()
        
        if rec_type == 'moneyline':
            # Extract team from recommendation
            rec_text = str(recommendation.get('bet', recommendation.get('recommendation', '')))
            
            # Determine actual winner
            actual_winner = (pred_values['away_team'] 
                           if final_score['away_score'] > final_score['home_score'] 
                           else pred_values['home_team'])
            
            # Check if recommendation matches actual winner
            away_norm = self.normalize_team_name(pred_values['away_team'])
            home_norm = self.normalize_team_name(pred_values['home_team'])
            rec_norm = self.normalize_team_name(rec_text)
            
            return (rec_norm in away_norm and actual_winner == pred_values['away_team']) or \
                   (rec_norm in home_norm and actual_winner == pred_values['home_team'])
        
        elif rec_type == 'total':
            # Extract over/under and line from recommendation
            side = recommendation.get('side', '').lower()
            rec_text = str(recommendation.get('recommendation', '')).lower()
            line = recommendation.get('line', 8.5)  # Default line
            
            actual_total = final_score['away_score'] + final_score['home_score']
            
            # Check side from explicit field first, then text
            if side == 'over' or 'over' in rec_text:
                return actual_total > line
            elif side == 'under' or 'under' in rec_text:
                return actual_total < line
            
        elif rec_type == 'run_line':
            # Run line analysis - simplified
            rec_text = str(recommendation.get('recommendation', '')).lower()
            spread = recommendation.get('spread', 1.5)
            
            score_diff = abs(final_score['away_score'] - final_score['home_score'])
            
            if 'favorite' in rec_text or 'cover' in rec_text:
                return score_diff > spread
            else:
                return score_diff <= spread
        
        return False
    
    def _calculate_payout(self, recommendation: Dict, is_correct: bool, unit_size: float = 100.0) -> float:
        """Calculate payout for a recommendation"""
        if not is_correct:
            return -unit_size  # Lost the bet
        
        # Get odds - handle different formats
        odds = recommendation.get('odds', -110)
        
        # Convert American odds to payout multiplier
        if odds > 0:
            # Positive odds: $100 bet wins $odds
            payout_multiplier = odds / 100
        else:
            # Negative odds: Need to bet $|odds| to win $100
            payout_multiplier = 100 / abs(odds)
        
        return unit_size * payout_multiplier
    
    def calculate_roi(self, games: Dict, final_scores: Dict, unit_size: float = 100.0) -> Dict:
        """Calculate ROI assuming $100 unit bets on all recommendations"""
        total_bet = 0.0
        total_winnings = 0.0
        total_bets_placed = 0
        winning_bets = 0
        game_results = []
        
        # Simplified odds for calculation (in reality, would use actual betting lines)
        default_odds = {
            'moneyline': -110,  # Typical moneyline odds
            'total': -110,      # Typical total odds
            'run_line': -110    # Typical run line odds
        }
        
        for game_key, game_data in games.items():
            pred_values = self.extract_prediction_values(game_data)
            
            # Skip if no team data
            if not all([pred_values['away_team'], pred_values['home_team']]):
                continue
            
            # Find matching final score
            away_norm = self.normalize_team_name(pred_values['away_team'])
            home_norm = self.normalize_team_name(pred_values['home_team'])
            score_key = f"{away_norm}_vs_{home_norm}"
            
            final_score = final_scores.get(score_key)
            if not final_score:
                continue
            
            # Extract betting recommendations - handle nested structure
            recommendations = []
            
            # Method 1: Check nested prediction structure (2025-08-20 format)
            if 'prediction' in game_data and 'recommendations' in game_data['prediction']:
                recommendations = game_data['prediction']['recommendations']
            # Method 2: Check direct recommendations
            elif 'recommendations' in game_data:
                recommendations = game_data['recommendations']
            # Method 3: Check betting_recommendations structure
            else:
                betting_recs = game_data.get('betting_recommendations', {})
                value_bets = betting_recs.get('unified_value_bets', [])
                recommendations = value_bets
            
            game_profit = 0.0
            game_bets = 0
            game_wins = 0
            game_bet_details = []
            
            for rec in recommendations:
                total_bets_placed += 1
                total_bet += unit_size
                game_bets += 1
                
                # Check if bet won
                is_correct = self.check_recommendation_accuracy(rec, final_score, pred_values)
                
                # Calculate winnings based on odds
                rec_type = rec.get('type', 'other').lower()
                odds = rec.get('odds', rec.get('american_odds', default_odds.get(rec_type, -110)))
                
                bet_profit = 0.0
                if is_correct:
                    winning_bets += 1
                    game_wins += 1
                    
                    if odds > 0:
                        # Positive odds: bet $100 to win $odds
                        winnings = unit_size + (unit_size * odds / 100)
                        bet_profit = unit_size * odds / 100
                    else:
                        # Negative odds: bet $|odds| to win $100
                        winnings = unit_size + (unit_size * 100 / abs(odds))
                        bet_profit = unit_size * 100 / abs(odds)
                    
                    total_winnings += winnings
                    game_profit += bet_profit
                else:
                    # Lost the bet
                    game_profit -= unit_size
                
                game_bet_details.append({
                    'type': rec_type,
                    'side': rec.get('side', 'unknown'),
                    'line': rec.get('line', 0),
                    'odds': odds,
                    'is_correct': is_correct,
                    'profit': bet_profit if is_correct else -unit_size
                })
            
            if game_bets > 0:
                game_results.append({
                    'game_key': game_key,
                    'away_team': pred_values['away_team'],
                    'home_team': pred_values['home_team'],
                    'final_score': f"{final_score['away_score']}-{final_score['home_score']}",
                    'total_bets': game_bets,
                    'winning_bets': game_wins,
                    'profit': round(game_profit, 2),
                    'bet_details': game_bet_details
                })
        
        net_profit = total_winnings - total_bet
        roi_percentage = (net_profit / total_bet * 100) if total_bet > 0 else 0.0
        win_rate = (winning_bets / total_bets_placed) if total_bets_placed > 0 else 0.0
        
        return {
            'total_bets_placed': total_bets_placed,
            'total_amount_bet': round(total_bet, 2),
            'total_winnings': round(total_winnings, 2),
            'net_profit': round(net_profit, 2),
            'roi_percentage': round(roi_percentage, 2),
            'win_rate': round(win_rate, 4),
            'winning_bets': winning_bets,
            'unit_size': unit_size,
            'game_results': game_results
        }
    
    def analyze_individual_games(self, games: Dict, final_scores: Dict) -> List[Dict]:
        """Analyze each game individually for detailed breakdown"""
        game_cards = []
        
        for game_key, game_data in games.items():
            pred_values = self.extract_prediction_values(game_data)
            
            # Skip if no team data
            if not all([pred_values['away_team'], pred_values['home_team']]):
                continue
            
            # Find matching final score
            away_norm = self.normalize_team_name(pred_values['away_team'])
            home_norm = self.normalize_team_name(pred_values['home_team'])
            score_key = f"{away_norm}_vs_{home_norm}"
            
            final_score = final_scores.get(score_key)
            
            # Model Predictability Analysis
            predictability = {
                'winner_correct': False,
                'away_score_error': None,
                'home_score_error': None,
                'total_score_error': None,
                'confidence': pred_values.get('confidence', 0)
            }
            
            if final_score:
                # Winner prediction accuracy
                if (pred_values['away_win_probability'] and pred_values['home_win_probability']):
                    away_prob = float(pred_values['away_win_probability'])
                    home_prob = float(pred_values['home_win_probability'])
                    predicted_winner = (pred_values['away_team'] 
                                     if away_prob > home_prob 
                                     else pred_values['home_team'])
                    actual_winner = (pred_values['away_team'] 
                                   if float(final_score['away_score']) > float(final_score['home_score']) 
                                   else pred_values['home_team'])
                    predictability['winner_correct'] = predicted_winner == actual_winner
                
                # Score prediction accuracy
                if pred_values['predicted_away_score'] is not None:
                    predictability['away_score_error'] = abs(float(pred_values['predicted_away_score']) - final_score['away_score'])
                if pred_values['predicted_home_score'] is not None:
                    predictability['home_score_error'] = abs(float(pred_values['predicted_home_score']) - final_score['home_score'])
                if (pred_values['predicted_away_score'] is not None and pred_values['predicted_home_score'] is not None):
                    pred_total = float(pred_values['predicted_away_score']) + float(pred_values['predicted_home_score'])
                    actual_total = final_score['away_score'] + final_score['home_score']
                    predictability['total_score_error'] = abs(pred_total - actual_total)
            
            # Betting Analysis
            betting_analysis = {
                'winner_bet_correct': predictability['winner_correct'],
                'total_bet_correct': None,
                'over_under_recommendation': None
            }
            
            if (final_score and pred_values['predicted_away_score'] is not None and 
                pred_values['predicted_home_score'] is not None):
                pred_total = float(pred_values['predicted_away_score']) + float(pred_values['predicted_home_score'])
                actual_total = final_score['away_score'] + final_score['home_score']
                
                # Assume standard 8.5 total line for betting analysis
                if abs(pred_total - 8.5) > 0.5:
                    betting_analysis['over_under_recommendation'] = 'Over' if float(pred_total) > 8.5 else 'Under'
                    if float(pred_total) > 8.5 and float(actual_total) > 8.5:
                        betting_analysis['total_bet_correct'] = True
                    elif float(pred_total) < 8.5 and float(actual_total) < 8.5:
                        betting_analysis['total_bet_correct'] = True
                    else:
                        betting_analysis['total_bet_correct'] = False
            
            # Recommendations Analysis
            recommendations = []
            
            # Extract betting recommendations - handle nested structure
            if 'prediction' in game_data and 'recommendations' in game_data['prediction']:
                raw_recommendations = game_data['prediction']['recommendations']
            elif 'recommendations' in game_data:
                raw_recommendations = game_data['recommendations']
            else:
                raw_recommendations = []
            
            for rec in raw_recommendations:
                rec_analysis = {
                    'type': rec.get('type', 'unknown'),
                    'side': rec.get('side', 'unknown'),
                    'line': rec.get('line', 0),
                    'odds': rec.get('odds', -110),
                    'expected_value': rec.get('expected_value', 0),
                    'confidence': rec.get('confidence', 'UNKNOWN'),
                    'reasoning': rec.get('reasoning', ''),
                    'is_correct': False,
                    'profit': 0.0
                }
                
                if final_score:
                    rec_analysis['is_correct'] = self.check_recommendation_accuracy(rec, final_score, pred_values)
                    rec_analysis['profit'] = self._calculate_payout(rec, rec_analysis['is_correct'], 100.0)
                
                recommendations.append(rec_analysis)
            
            # ROI for this game
            game_roi = {
                'total_bets': len(recommendations),
                'winning_bets': sum(1 for r in recommendations if r['is_correct']),
                'total_profit': sum(r['profit'] for r in recommendations),
                'win_rate': (sum(1 for r in recommendations if r['is_correct']) / len(recommendations)) if recommendations else 0
            }
            
            game_card = {
                'game_key': game_key,
                'away_team': pred_values['away_team'],
                'home_team': pred_values['home_team'],
                'away_pitcher': pred_values.get('away_pitcher', 'TBD'),
                'home_pitcher': pred_values.get('home_pitcher', 'TBD'),
                'predicted_scores': {
                    'away': pred_values['predicted_away_score'],
                    'home': pred_values['predicted_home_score'],
                    'total': (float(pred_values['predicted_away_score']) + float(pred_values['predicted_home_score'])) 
                            if (pred_values['predicted_away_score'] is not None and pred_values['predicted_home_score'] is not None) else None
                },
                'final_scores': final_score if final_score else {'away_score': None, 'home_score': None},
                'win_probabilities': {
                    'away': pred_values['away_win_probability'],
                    'home': pred_values['home_win_probability']
                },
                'predictability': predictability,
                'betting_analysis': betting_analysis,
                'recommendations': recommendations,
                'roi': game_roi,
                'has_final_score': final_score is not None
            }
            
            game_cards.append(game_card)
        
        return game_cards
    def get_available_dates(self) -> List[str]:
        """Get list of available dates with both predictions and final scores"""
        available_dates = []
        
        # Check predictions cache for available dates
        try:
            with open(self.predictions_cache_path, 'r') as f:
                cache = json.load(f)
            
            predictions_by_date = cache.get('predictions_by_date', {})
            
            for date_str in predictions_by_date.keys():
                # Check if corresponding final scores exist
                scores_file = self.base_scores_path.format(date=date_str.replace('-', '_'))
                if os.path.exists(scores_file):
                    available_dates.append(date_str)
            
        except Exception as e:
            logger.error(f"Error getting available dates: {e}")
        
        return sorted(available_dates)
    
    def perform_cumulative_analysis(self, start_date: str = None) -> Dict:
        """Perform cumulative analysis across all available dates since start_date"""
        available_dates = self.get_available_dates()

        if not available_dates:
            return {
                'error': 'No historical data available',
                'available_dates': []
            }

        # Default start_date to 2025-08-15 if not provided
        if start_date is None:
            start_date = '2025-08-15'
        available_dates = [d for d in available_dates if d >= start_date]

        if not available_dates:
            return {
                'error': f'No data available since {start_date}',
                'available_dates': self.get_available_dates()
            }
        
        logger.info(f"Performing cumulative analysis for dates: {available_dates}")
        
        # Aggregate data across all dates
        cumulative_games = {}
        cumulative_scores = {}
        daily_summaries = []
        
        total_predictions = 0
        total_matched = 0
        total_winner_correct = 0
        total_recommendations = 0
        total_rec_correct = 0
        total_bet_amount = 0.0
        total_winnings = 0.0
        total_bets_placed = 0
        winning_bets = 0
        
        team_score_errors = []
        total_score_errors = []
        
        for date in available_dates:
            # Get daily analysis
            daily_analysis = self.perform_complete_analysis(date)
            
            if 'error' in daily_analysis:
                logger.warning(f"Skipping {date}: {daily_analysis['error']}")
                continue
            
            # Track daily summary
            daily_summary = {
                'date': date,
                'games': daily_analysis['data_summary']['matched_games'],
                'winner_accuracy': daily_analysis['predictability']['winner_accuracy'],
                'rec_accuracy': daily_analysis['betting_recommendations']['overall_accuracy'],
                'roi': daily_analysis['roi_analysis']['roi_percentage'],
                'profit': daily_analysis['roi_analysis']['net_profit'],
                'total_bets': daily_analysis['roi_analysis']['total_bets_placed']
            }
            daily_summaries.append(daily_summary)
            
            # Aggregate metrics
            pred = daily_analysis['predictability']
            total_predictions += pred['total_games']
            total_matched += pred['matched_games']
            
            # Count correct winners across all matched games
            if pred['matched_games'] > 0:
                total_winner_correct += int(pred['winner_accuracy'] * pred['matched_games'])
            
            # Aggregate recommendation data
            rec = daily_analysis['betting_recommendations']
            total_recommendations += rec['total_recommendations']
            total_rec_correct += rec['total_correct']
            
            # Aggregate ROI data
            roi = daily_analysis['roi_analysis']
            total_bet_amount += roi['total_amount_bet']
            total_winnings += roi['total_winnings']
            total_bets_placed += roi['total_bets_placed']
            winning_bets += roi['winning_bets']
            
            # Aggregate errors for game cards that have final scores
            for card in daily_analysis['game_cards']:
                if card['has_final_score'] and card['predictability']:
                    if card['predictability']['away_score_error'] is not None:
                        team_score_errors.append(card['predictability']['away_score_error'])
                    if card['predictability']['home_score_error'] is not None:
                        team_score_errors.append(card['predictability']['home_score_error'])
                    if card['predictability']['total_score_error'] is not None:
                        total_score_errors.append(card['predictability']['total_score_error'])
        
        # Calculate cumulative metrics
        cumulative_winner_accuracy = total_winner_correct / total_matched if total_matched > 0 else 0.0
        cumulative_rec_accuracy = total_rec_correct / total_recommendations if total_recommendations > 0 else 0.0
        net_profit = total_winnings - total_bet_amount
        cumulative_roi = (net_profit / total_bet_amount * 100) if total_bet_amount > 0 else 0.0
        cumulative_win_rate = winning_bets / total_bets_placed if total_bets_placed > 0 else 0.0
        avg_team_score_error = sum(team_score_errors) / len(team_score_errors) if team_score_errors else 0.0
        avg_total_score_error = sum(total_score_errors) / len(total_score_errors) if total_score_errors else 0.0
        
        # Calculate performance trends
        if len(daily_summaries) > 1:
            recent_accuracy = sum(d['winner_accuracy'] for d in daily_summaries[-3:]) / min(3, len(daily_summaries))
            recent_roi = sum(d['roi'] for d in daily_summaries[-3:]) / min(3, len(daily_summaries))
        else:
            recent_accuracy = daily_summaries[0]['winner_accuracy'] if daily_summaries else 0.0
            recent_roi = daily_summaries[0]['roi'] if daily_summaries else 0.0
        
        return {
            'analysis_type': 'cumulative',
            'date_range': {
                'start_date': available_dates[0],
                'end_date': available_dates[-1],
                'total_days': len(available_dates)
            },
            'generated_at': datetime.now().isoformat(),
            'data_summary': {
                'total_games_predicted': total_predictions,
                'total_games_matched': total_matched,
                'coverage_rate': total_matched / total_predictions if total_predictions > 0 else 0.0
            },
            'cumulative_performance': {
                'winner_accuracy': round(cumulative_winner_accuracy, 4),
                'recommendation_accuracy': round(cumulative_rec_accuracy, 4),
                'roi_percentage': round(cumulative_roi, 2),
                'win_rate': round(cumulative_win_rate, 4),
                'total_profit': round(net_profit, 2),
                'total_amount_bet': round(total_bet_amount, 2),
                'total_recommendations': total_recommendations,
                'total_bets_placed': total_bets_placed,
                'winning_bets': winning_bets,
                'avg_team_score_error': round(avg_team_score_error, 2),
                'avg_total_score_error': round(avg_total_score_error, 2)
            },
            'recent_performance': {
                'recent_accuracy': round(recent_accuracy, 4),
                'recent_roi': round(recent_roi, 2)
            },
            'daily_summaries': daily_summaries,
            'daily_game_details': self.get_daily_game_details(available_dates),
            'summary': {
                'model_winner_accuracy': round(cumulative_winner_accuracy, 4),
                'recommendation_accuracy': round(cumulative_rec_accuracy, 4),
                'roi_percentage': round(cumulative_roi, 2),
                'total_profit': round(net_profit, 2),
                'days_tracked': len(available_dates)
            }
        }

    def get_daily_game_details(self, available_dates: List[str]) -> List[Dict]:
        """Get detailed game cards for each day"""
        daily_details = []
        
        for date in available_dates:
            try:
                # Get single day analysis for detailed game cards
                daily_analysis = self.perform_complete_analysis(date)
                
                if 'error' not in daily_analysis:
                    day_detail = {
                        'date': date,
                        'games_count': len(daily_analysis['game_cards']),
                        'day_stats': {
                            'winner_accuracy': daily_analysis['predictability']['winner_accuracy'],
                            'roi': daily_analysis['roi_analysis']['roi_percentage'],
                            'profit': daily_analysis['roi_analysis']['net_profit'],
                            'total_bets': daily_analysis['roi_analysis']['total_bets_placed']
                        },
                        'game_cards': daily_analysis['game_cards']
                    }
                    daily_details.append(day_detail)
                    
            except Exception as e:
                logger.error(f"Error getting game details for {date}: {e}")
                
        return daily_details

    def perform_complete_analysis(self, target_date: str) -> Dict:
        """Perform complete historical analysis for a given date"""
        logger.info(f"Starting historical analysis for {target_date}")
        
        # Load data
        games = self.load_predictions_for_date(target_date)
        final_scores = self.load_final_scores_for_date(target_date)

        if not games:
            return {
                'error': f'No prediction data found for {target_date}',
                'date': target_date
            }

        # If final scores are missing, still return all prediction and recommendation data
        scores_available = bool(final_scores)

        # Perform all analyses (if scores available, else use empty scores for analysis)
        predictability = self.analyze_predictability(games, final_scores if scores_available else {})
        betting_lens = self.analyze_betting_lens(games, final_scores if scores_available else {})
        betting_recommendations = self.analyze_betting_recommendations(games, final_scores if scores_available else {})
        roi_analysis = self.calculate_roi(games, final_scores if scores_available else {})
        game_cards = self.analyze_individual_games(games, final_scores if scores_available else {})

        # Mark game cards as missing final scores if not available
        if not scores_available:
            for card in game_cards:
                card['has_final_score'] = False
                card['final_scores'] = {'away_score': None, 'home_score': None}

        # Compile comprehensive report
        report = {
            'date': target_date,
            'generated_at': datetime.now().isoformat(),
            'data_summary': {
                'total_games_predicted': len(games),
                'final_scores_available': len(final_scores),
                'matched_games': predictability['matched_games']
            },
            'predictability': predictability,
            'betting_lens': betting_lens,
            'betting_recommendations': betting_recommendations,
            'roi_analysis': roi_analysis,
            'game_cards': game_cards,
            'summary': {
                'model_winner_accuracy': predictability.get('winner_accuracy', 0.0),
                'betting_winner_accuracy': betting_lens.get('winner_accuracy', 0.0),
                'recommendation_accuracy': betting_recommendations.get('overall_accuracy', 0.0),
                'roi_percentage': roi_analysis.get('roi_percentage', 0.0),
                'total_profit': roi_analysis.get('net_profit', 0.0)
            },
            'final_scores_missing': not scores_available
        }

        logger.info(f"Historical analysis completed for {target_date}")
        logger.info(f"Found {len(games)} games, {len(final_scores)} final scores")
        logger.info(f"Model accuracy: {predictability.get('winner_accuracy', 0):.1%}")
        logger.info(f"Total recommendations: {betting_recommendations.get('total_recommendations', 0)}")
        logger.info(f"ROI: {roi_analysis.get('roi_percentage', 0):.2f}%")

        return report

# Initialize analyzer
analyzer = HistoricalAnalyzer()

@historical_analysis_bp.route('/api/historical-analysis', methods=['GET'])
def get_historical_analysis():
    """API endpoint for historical analysis - defaults to cumulative since 8-15"""
    try:
        # Get parameters from query
        target_date = request.args.get('date')
        analysis_type = request.args.get('type', 'cumulative')  # Default to cumulative
        start_date = request.args.get('start_date', '2025-08-15')  # Default to 8-15

        if analysis_type == 'cumulative':
            # Perform cumulative analysis
            analysis = analyzer.perform_cumulative_analysis(start_date)
        else:
            # Single date analysis
            if not target_date:
                # Default to yesterday if no date provided
                yesterday = datetime.now() - timedelta(days=1)
                target_date = yesterday.strftime('%Y-%m-%d')

            # Validate date format
            try:
                datetime.strptime(target_date, '%Y-%m-%d')
            except ValueError:
                return jsonify({
                    'error': 'Invalid date format. Use YYYY-MM-DD',
                    'example': '2025-08-20'
                }), 400

            # Perform single date analysis
            analysis = analyzer.perform_complete_analysis(target_date)

        if 'error' in analysis:
            logger.error(f"Analysis error: {analysis.get('error')}, details: {analysis}")
            return jsonify(analysis), 404

        return jsonify(analysis)

    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        logger.error(f"Error in historical analysis endpoint: {e}\nTraceback:\n{tb}")
        return jsonify({
            'error': 'Internal server error',
            'message': str(e),
            'traceback': tb
        }), 500

# Test endpoint for development
@historical_analysis_bp.route('/api/historical-analysis/test', methods=['GET'])
def test_historical_analysis():
    """Test endpoint to verify the analysis works"""
    try:
        # Test with a known date
        test_date = '2025-08-20'
        
        # Load test data
        games = analyzer.load_predictions_for_date(test_date)
        final_scores = analyzer.load_final_scores_for_date(test_date)
        
        return jsonify({
            'test_date': test_date,
            'predictions_loaded': len(games),
            'final_scores_loaded': len(final_scores),
            'sample_game_keys': list(games.keys())[:3] if games else [],
            'sample_score_keys': list(final_scores.keys())[:3] if final_scores else [],
            'status': 'Test successful' if games and final_scores else 'Missing data'
        })
        
    except Exception as e:
        logger.error(f"Error in test endpoint: {e}")
        return jsonify({
            'error': 'Test failed',
            'message': str(e)
        }), 500

@historical_analysis_bp.route('/api/historical-analysis/dates', methods=['GET'])
def get_available_dates():
    """API endpoint to get available analysis dates"""
    try:
        available_dates = analyzer.get_available_dates()
        return jsonify({
            'available_dates': available_dates,
            'count': len(available_dates)
        })
    except Exception as e:
        logger.error(f"Error getting available dates: {e}")
        return jsonify({
            'error': f'Error getting available dates: {str(e)}',
            'available_dates': []
        }), 500
