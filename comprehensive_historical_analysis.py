"""
Comprehensive Historical Analysis System
=====================================
Complete revamp of historical tracking focusing on:
1. Model performance metrics since 8/15
2. Betting recommendations accuracy
3. ROI calculations with $100 unit bets
4. Day-by-day performance breakdown
5. Game-level analysis

This replaces all previous historical analysis systems.
"""

import json
import os
import glob
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from team_name_normalizer import normalize_team_name
import requests

logger = logging.getLogger(__name__)

class ComprehensiveHistoricalAnalyzer:
    """Complete historical analysis system for MLB predictions and betting performance"""
    
    def __init__(self):
        self.start_date = "2025-08-15"  # Analysis start date
        self.data_dir = "data"
        
    def get_available_dates(self) -> List[str]:
        """Get all available dates with both predictions and final scores"""
        betting_files = glob.glob(f"{self.data_dir}/betting_recommendations_2025_08_*.json")
        games_files = glob.glob(f"{self.data_dir}/games_2025-08-*.json")
        
        # Extract dates from filenames
        betting_dates = set()
        for file in betting_files:
            date_part = os.path.basename(file).replace('betting_recommendations_', '').replace('.json', '')
            betting_dates.add(date_part.replace('_', '-'))
        
        games_dates = set()
        for file in games_files:
            date_part = os.path.basename(file).replace('games_', '').replace('.json', '')
            games_dates.add(date_part)
        
        # Find common dates (where we have both predictions and games data)
        common_dates = list(betting_dates & games_dates)
        common_dates.sort()
        
        # Filter to start from our analysis start date
        filtered_dates = [d for d in common_dates if d >= self.start_date]
        
        logger.info(f"Found {len(filtered_dates)} dates with complete data since {self.start_date}")
        return filtered_dates
    
    def load_predictions_for_date(self, date: str) -> Dict:
        """Load betting recommendations for a specific date"""
        date_formatted = date.replace('-', '_')
        file_path = f"{self.data_dir}/betting_recommendations_{date_formatted}.json"
        
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            games_data = data.get('games', {})
            
            # Validate that the data has proper predictions (support both old and new formats)
            if games_data:
                sample_game = next(iter(games_data.values()))
                
                # Check for new format first (win_probabilities structure at top level)
                win_probs = sample_game.get('win_probabilities', {})
                if (win_probs.get('home_prob') is not None and 
                    win_probs.get('away_prob') is not None and
                    sample_game.get('predicted_total_runs') is not None):
                    logger.info(f"Cached data for {date} is in new format")
                    return games_data
                
                # Check for current format (has both predictions and recommendations)
                if ('predictions' in sample_game and 
                    'recommendations' in sample_game and
                    sample_game.get('predictions', {}).get('predicted_total_runs') is not None):
                    logger.info(f"Cached data for {date} is in current format with recommendations")
                    return games_data
                
                # Check for old format (predictions structure only, needs conversion)
                predictions = sample_game.get('predictions', {})
                if (predictions.get('home_win_prob') is not None and
                    predictions.get('away_win_prob') is not None and
                    predictions.get('predicted_total_runs') is not None and
                    'recommendations' not in sample_game):
                    logger.info(f"Cached data for {date} is in old format, converting...")
                    # Convert old format to new format
                    return self._convert_old_format_to_new(games_data)
                
                # If neither format is valid, try regeneration
                logger.warning(f"Cached data for {date} has invalid predictions, regenerating...")
                raise ValueError("Invalid cached data")
            
            return games_data
        except (FileNotFoundError, ValueError):
            logger.info(f"Generating fresh predictions for {date} using enhanced engine...")
            return self._generate_predictions_for_date(date)
        except Exception as e:
            logger.error(f"Error loading predictions for {date}: {e}")
            return {}
    
    def _generate_predictions_for_date(self, date: str) -> Dict:
        """Generate fresh predictions using the enhanced betting engine"""
        try:
            from betting_recommendations_engine import BettingRecommendationsEngine
            
            # Initialize enhanced engine
            engine = BettingRecommendationsEngine()
            
            # Generate predictions for the specific date
            engine.target_date = date
            recommendations = engine.generate_betting_recommendations()
            
            if recommendations.get('success') and recommendations.get('games'):
                logger.info(f"Generated {len(recommendations['games'])} predictions for {date}")
                return recommendations['games']
            else:
                logger.warning(f"Failed to generate predictions for {date}: {recommendations.get('error', 'Unknown error')}")
                return {}
                
        except Exception as e:
            logger.error(f"Error generating predictions for {date}: {e}")
            return {}
    
    def _convert_old_format_to_new(self, old_games_data: Dict) -> Dict:
        """Convert old format cached data to new format structure"""
        new_games_data = {}
        
        for game_key, old_game in old_games_data.items():
            try:
                predictions = old_game.get('predictions', {})
                
                # Extract basic game info
                new_game = {
                    'away_team': old_game.get('away_team', ''),
                    'home_team': old_game.get('home_team', ''),
                    'away_pitcher': old_game.get('away_pitcher', ''),
                    'home_pitcher': old_game.get('home_pitcher', ''),
                }
                
                # Convert win probabilities
                home_prob = predictions.get('home_win_prob', 0.5)
                away_prob = predictions.get('away_win_prob', 0.5)
                
                new_game['win_probabilities'] = {
                    'home_prob': home_prob,
                    'away_prob': away_prob
                }
                
                # Extract predicted total runs
                new_game['predicted_total_runs'] = predictions.get('predicted_total_runs', 8.5)
                
                # Extract predicted score
                home_score = predictions.get('predicted_home_score', 4.0)
                away_score = predictions.get('predicted_away_score', 4.5)
                new_game['predicted_score'] = f"{away_score}-{home_score}"
                
                # Convert recommendations to value_bets format
                recommendations = old_game.get('recommendations', [])
                value_bets = []
                
                for rec in recommendations:
                    if isinstance(rec, dict):
                        bet = {
                            'type': rec.get('type', 'moneyline'),
                            'recommendation': rec.get('recommendation', ''),
                            'expected_value': rec.get('expected_value', 0),
                            'win_probability': rec.get('win_probability', away_prob if 'away' in str(rec.get('recommendation', '')).lower() else home_prob),
                            'american_odds': str(rec.get('odds', 100)),
                            'confidence': rec.get('confidence', 'medium'),
                            'reasoning': rec.get('reasoning', 'Converted from old format')
                        }
                        value_bets.append(bet)
                
                new_game['value_bets'] = value_bets
                new_games_data[game_key] = new_game
                
            except Exception as e:
                logger.warning(f"Error converting old format for game {game_key}: {e}")
                continue
        
        logger.info(f"Converted {len(new_games_data)} games from old format to new format")
        return new_games_data
    
    def load_final_scores_for_date(self, date: str) -> Dict:
        """Load final scores for a specific date using live MLB API"""
        try:
            # Use the same live data API that powers the main dashboard
            from live_mlb_data import LiveMLBData
            mlb_api = LiveMLBData()
            live_games = mlb_api.get_enhanced_games_data(date)
            
            final_scores = {}
            for game in live_games:
                if game.get('is_final', False):
                    away_team = normalize_team_name(game.get('away_team', ''))
                    home_team = normalize_team_name(game.get('home_team', ''))
                    game_key = f"{away_team}_vs_{home_team}"
                    
                    final_scores[game_key] = {
                        'away_team': away_team,
                        'home_team': home_team,
                        'away_score': game.get('away_score', 0),
                        'home_score': game.get('home_score', 0),
                        'total_runs': game.get('away_score', 0) + game.get('home_score', 0),
                        'winner': 'away' if game.get('away_score', 0) > game.get('home_score', 0) else 'home',
                        'game_pk': game.get('game_pk', ''),
                        'is_final': True
                    }
            
            logger.info(f"Loaded {len(final_scores)} final scores for {date}")
            return final_scores
            
        except Exception as e:
            logger.error(f"Error loading final scores for {date}: {e}")
            return {}
    
    def analyze_model_performance(self, predictions: Dict, final_scores: Dict) -> Dict:
        """Analyze core model performance - winner predictions and score accuracy"""
        stats = {
            'total_games': 0,
            'winner_correct': 0,
            'total_runs_within_1': 0,
            'total_runs_within_2': 0,
            'average_score_diff': 0,
            'games_analyzed': []
        }
        
        total_score_diff = 0
        
        for game_key, prediction in predictions.items():
            # Normalize the key for matching
            away_team = normalize_team_name(prediction.get('away_team', ''))
            home_team = normalize_team_name(prediction.get('home_team', ''))
            normalized_key = f"{away_team}_vs_{home_team}"
            
            if normalized_key not in final_scores:
                continue
            
            final_score = final_scores[normalized_key]
            stats['total_games'] += 1
            
            # Extract prediction data
            win_probs = prediction.get('win_probabilities', {})
            away_prob = win_probs.get('away_prob', 0.5)
            home_prob = win_probs.get('home_prob', 0.5)
            predicted_total = prediction.get('predicted_total_runs', 0)
            
            # Winner accuracy
            predicted_winner = 'away' if away_prob > home_prob else 'home'
            actual_winner = final_score['winner']
            winner_correct = predicted_winner == actual_winner
            
            if winner_correct:
                stats['winner_correct'] += 1
            
            # Total runs accuracy
            actual_total = final_score['total_runs']
            total_diff = abs(predicted_total - actual_total)
            total_score_diff += total_diff
            
            if total_diff <= 1:
                stats['total_runs_within_1'] += 1
            if total_diff <= 2:
                stats['total_runs_within_2'] += 1
            
            # Store game analysis with enhanced display data
            stats['games_analyzed'].append({
                'game_key': normalized_key,
                'away_team': away_team,
                'home_team': home_team,
                'predicted_winner': predicted_winner,
                'actual_winner': actual_winner,
                'winner_correct': winner_correct,
                'predicted_total': predicted_total,
                'actual_total': actual_total,
                'total_diff': total_diff,
                'away_prob': away_prob,
                'home_prob': home_prob,
                'away_score': final_score.get('away_score', 0),
                'home_score': final_score.get('home_score', 0),
                'game_pk': final_score.get('game_pk', ''),
                'is_final': final_score.get('is_final', True)
            })
        
        # Calculate percentages and averages - LIMITED TO 2 DECIMAL PLACES MAX
        if stats['total_games'] > 0:
            stats['winner_accuracy'] = round((stats['winner_correct'] / stats['total_games']) * 100, 2)
            stats['total_runs_accuracy_1'] = round((stats['total_runs_within_1'] / stats['total_games']) * 100, 2)
            stats['total_runs_accuracy_2'] = round((stats['total_runs_within_2'] / stats['total_games']) * 100, 2)
            stats['average_score_diff'] = round(total_score_diff / stats['total_games'], 2)
        else:
            stats['winner_accuracy'] = 0
            stats['total_runs_accuracy_1'] = 0
            stats['total_runs_accuracy_2'] = 0
            stats['average_score_diff'] = 0
        
        return stats
    
    def analyze_betting_recommendations(self, predictions: Dict, final_scores: Dict) -> Dict:
        """Analyze betting recommendations performance and calculate ROI - handles varied data structures"""
        stats = {
            'total_recommendations': 0,
            'correct_recommendations': 0,
            'moneyline_stats': {'total': 0, 'correct': 0, 'accuracy': 0},
            'total_stats': {'total': 0, 'correct': 0, 'accuracy': 0},
            'runline_stats': {'total': 0, 'correct': 0, 'accuracy': 0},
            'total_bet_amount': 0,
            'total_winnings': 0,
            'roi_percentage': 0,
            'detailed_bets': []
        }
        
        bet_unit = 100  # $100 per bet
        logger.info(f"Analyzing {len(predictions)} games with {len(final_scores)} final scores")
        
        # Process each game individually to handle varied data structures
        for game_key, prediction in predictions.items():
            game_stats = self.analyze_single_game_bets(game_key, prediction, final_scores, bet_unit)
            
            # Aggregate the stats
            stats['total_recommendations'] += game_stats['total_recommendations']
            stats['correct_recommendations'] += game_stats['correct_recommendations']
            stats['total_bet_amount'] += game_stats['total_bet_amount']
            stats['total_winnings'] += game_stats['total_winnings']
            
            # Aggregate by bet type
            for bet_type in ['moneyline_stats', 'total_stats', 'runline_stats']:
                stats[bet_type]['total'] += game_stats[bet_type]['total']
                stats[bet_type]['correct'] += game_stats[bet_type]['correct']
            
            # Add detailed bets
            stats['detailed_bets'].extend(game_stats['detailed_bets'])
        
        # Calculate final percentages and ROI
        if stats['total_recommendations'] > 0:
            stats['overall_accuracy'] = round((stats['correct_recommendations'] / stats['total_recommendations']) * 100, 2)
        else:
            stats['overall_accuracy'] = 0
        
        for bet_type in ['moneyline_stats', 'total_stats', 'runline_stats']:
            if stats[bet_type]['total'] > 0:
                stats[bet_type]['accuracy'] = round((stats[bet_type]['correct'] / stats[bet_type]['total']) * 100, 2)
        
        if stats['total_bet_amount'] > 0:
            net_profit = stats['total_winnings'] - stats['total_bet_amount']
            stats['roi_percentage'] = round((net_profit / stats['total_bet_amount']) * 100, 2)
            stats['net_profit'] = round(net_profit, 2)
        else:
            stats['roi_percentage'] = 0
            stats['net_profit'] = 0
        
        logger.info(f"Analysis complete: {stats['total_recommendations']} bets, {stats['correct_recommendations']} correct, {stats['roi_percentage']}% ROI")
        return stats
    
    def analyze_single_game_bets(self, game_key: str, prediction: Dict, final_scores: Dict, bet_unit: float) -> Dict:
        """Analyze betting recommendations for a single game - handles varied data structures"""
        game_stats = {
            'total_recommendations': 0,
            'correct_recommendations': 0,
            'moneyline_stats': {'total': 0, 'correct': 0},
            'total_stats': {'total': 0, 'correct': 0},
            'runline_stats': {'total': 0, 'correct': 0},
            'total_bet_amount': 0,
            'total_winnings': 0,
            'detailed_bets': []
        }
        
        # Normalize game key for matching final scores
        away_team = normalize_team_name(prediction.get('away_team', ''))
        home_team = normalize_team_name(prediction.get('home_team', ''))
        normalized_key = f"{away_team}_vs_{home_team}"
        
        # Find final score for this game
        final_score = None
        if normalized_key in final_scores:
            final_score = final_scores[normalized_key]
        else:
            # Try alternative matching methods
            for score_key, score_data in final_scores.items():
                if (away_team in score_key and home_team in score_key):
                    final_score = score_data
                    break
        
        if not final_score:
            logger.warning(f"No final score found for {game_key} (normalized: {normalized_key})")
            return game_stats
        
        # Extract betting recommendations using multiple approaches
        recommendations = self.extract_game_recommendations(prediction)
        
        if not recommendations:
            logger.debug(f"No recommendations found for {game_key}")
            return game_stats
        
        logger.debug(f"Found {len(recommendations)} recommendations for {game_key}")
        
        # Process each recommendation
        for rec in recommendations:
            try:
                bet_result = self.evaluate_single_bet(rec, final_score, prediction, bet_unit)
                
                if bet_result['is_valid']:
                    game_stats['total_recommendations'] += 1
                    game_stats['total_bet_amount'] += bet_unit
                    
                    if bet_result['bet_won']:
                        game_stats['correct_recommendations'] += 1
                        game_stats['total_winnings'] += bet_result['winnings']
                    
                    # Track by bet type
                    bet_type = bet_result['bet_type']
                    if bet_type == 'moneyline':
                        game_stats['moneyline_stats']['total'] += 1
                        if bet_result['bet_won']:
                            game_stats['moneyline_stats']['correct'] += 1
                    elif bet_type == 'total':
                        game_stats['total_stats']['total'] += 1
                        if bet_result['bet_won']:
                            game_stats['total_stats']['correct'] += 1
                    elif bet_type in ['runline', 'run_line']:
                        game_stats['runline_stats']['total'] += 1
                        if bet_result['bet_won']:
                            game_stats['runline_stats']['correct'] += 1
                    
                    # Add detailed bet info
                    game_stats['detailed_bets'].append({
                        'game_key': normalized_key,
                        'away_team': away_team,
                        'home_team': home_team,
                        'bet_type': bet_result['bet_type'],
                        'recommendation': bet_result['recommendation'],
                        'american_odds': bet_result['american_odds'],
                        'expected_value': bet_result.get('expected_value', 0),
                        'bet_amount': bet_unit,
                        'bet_won': bet_result['bet_won'],
                        'winnings': bet_result['winnings'] if bet_result['bet_won'] else 0,
                        'confidence': bet_result.get('confidence', 'UNKNOWN')
                    })
                    
            except Exception as e:
                logger.warning(f"Error evaluating bet for {game_key}: {e}")
                continue
        
        return game_stats
    
    def extract_game_recommendations(self, prediction: Dict) -> List[Dict]:
        """Extract betting recommendations from game data - handles multiple data formats"""
        recommendations = []
        
        # Method 1: Direct recommendations field (current format)
        if 'recommendations' in prediction and prediction['recommendations']:
            for rec in prediction['recommendations']:
                if isinstance(rec, dict) and rec.get('type'):
                    # Filter out invalid/empty recommendations
                    bet_type = rec.get('type', '').lower()
                    side = rec.get('side', '').lower()
                    
                    # Skip invalid bet types
                    if bet_type in ['none', 'unknown', '']:
                        continue
                    
                    # Skip if no valid side for bet types that need it
                    if bet_type in ['total', 'moneyline', 'runline'] and not side:
                        continue
                    
                    recommendations.append({
                        'source': 'recommendations',
                        'type': bet_type,
                        'side': side,
                        'line': rec.get('line', 0),
                        'odds': rec.get('odds', -110),
                        'expected_value': rec.get('expected_value', 0),
                        'confidence': rec.get('confidence', 'MEDIUM'),
                        'reasoning': rec.get('reasoning', '')
                    })
        
        # Method 2: value_bets field (converted format)
        if 'value_bets' in prediction and prediction['value_bets']:
            for bet in prediction['value_bets']:
                if isinstance(bet, dict) and bet.get('type'):
                    # Filter out invalid bet types
                    bet_type = bet.get('type', '').lower()
                    if bet_type in ['none', 'unknown', '']:
                        continue
                    
                    # Parse the recommendation field for side/direction
                    rec_text = bet.get('recommendation', '').lower()
                    if rec_text in ['no recommendations', 'no clear value identified', '']:
                        continue
                        
                    side = ''
                    if 'over' in rec_text:
                        side = 'over'
                    elif 'under' in rec_text:
                        side = 'under'
                    elif 'home' in rec_text:
                        side = 'home'
                    elif 'away' in rec_text:
                        side = 'away'
                    
                    # Skip if no valid side found
                    if not side:
                        continue
                    
                    recommendations.append({
                        'source': 'value_bets',
                        'type': bet_type,
                        'side': side,
                        'line': bet.get('betting_line', 0),
                        'odds': bet.get('american_odds', '-110').replace('+', '').replace('-', ''),
                        'expected_value': bet.get('expected_value', 0),
                        'confidence': bet.get('confidence', 'MEDIUM'),
                        'reasoning': bet.get('reasoning', '')
                    })
        
        # Method 3: Legacy unified recommendations
        if 'unified_value_bets' in prediction:
            unified_bets = prediction['unified_value_bets']
            if isinstance(unified_bets, list):
                for bet in unified_bets:
                    if isinstance(bet, dict) and bet.get('type'):
                        recommendations.append({
                            'source': 'unified_value_bets',
                            'type': bet.get('type', ''),
                            'side': bet.get('side', ''),
                            'line': bet.get('line', 0),
                            'odds': bet.get('odds', -110),
                            'expected_value': bet.get('expected_value', 0),
                            'confidence': bet.get('confidence', 'MEDIUM'),
                            'reasoning': bet.get('reasoning', '')
                        })
        
        return recommendations
    
    def evaluate_single_bet(self, recommendation: Dict, final_score: Dict, prediction: Dict, bet_unit: float) -> Dict:
        """Evaluate a single betting recommendation"""
        bet_type = recommendation.get('type', '').lower()
        side = recommendation.get('side', '').lower()
        line = recommendation.get('line', 0)
        odds = recommendation.get('odds', -110)
        
        # Validate bet has required fields
        if not bet_type or not side:
            return {'is_valid': False}
        
        # Convert odds to string format if needed
        if isinstance(odds, (int, float)):
            american_odds = f"{odds:+d}" if odds else '+100'
        else:
            american_odds = str(odds)
            
        # Ensure odds have proper sign
        if not american_odds.startswith(('+', '-')):
            american_odds = f"-{american_odds}" if american_odds.isdigit() else american_odds
        
        actual_total = final_score.get('total_runs', 0)
        actual_winner = final_score.get('winner', '')
        
        bet_won = False
        
        # Evaluate based on bet type
        if bet_type == 'total' and line > 0:
            if side == 'over':
                bet_won = actual_total > line
            elif side == 'under':
                bet_won = actual_total < line
                
        elif bet_type == 'moneyline':
            if side in ['away', 'home']:
                bet_won = actual_winner == side
                
        elif bet_type in ['runline', 'run_line'] and line != 0:
            if side == 'away':
                # Away team getting points
                away_score_adjusted = final_score.get('away_score', 0) + abs(line)
                bet_won = away_score_adjusted > final_score.get('home_score', 0)
            elif side == 'home':
                # Home team giving points
                home_score_adjusted = final_score.get('home_score', 0) - abs(line)
                bet_won = home_score_adjusted > final_score.get('away_score', 0)
        
        # Calculate winnings if bet won
        winnings = 0
        if bet_won:
            winnings = self.calculate_winnings(bet_unit, american_odds)
        
        return {
            'is_valid': True,
            'bet_type': bet_type,
            'recommendation': f"{side} {line}" if line else side,
            'american_odds': american_odds,
            'bet_won': bet_won,
            'winnings': winnings,
            'expected_value': recommendation.get('expected_value', 0),
            'confidence': recommendation.get('confidence', 'UNKNOWN')
        }
    
    def evaluate_bet(self, bet: Dict, final_score: Dict, prediction: Dict) -> bool:
        """Evaluate if a specific bet won based on final score"""
        recommendation = bet.get('recommendation', '').lower().strip()
        bet_type = bet.get('type', '').lower()
        side = bet.get('side', '').lower()
        reasoning = bet.get('reasoning', '').lower()
        
        # Return False for empty or invalid recommendations
        if (not bet_type or bet_type in ['none', 'unknown'] or
            (not side and not recommendation) or
            recommendation in ['no recommendations', 'no clear value identified']):
            return False
        
        actual_total = final_score['total_runs']
        actual_winner = final_score['winner']
        
        # Handle total bets (over/under)
        if bet_type == 'total':
            betting_line = bet.get('line', 0)
            
            # Get the side/direction of the bet
            bet_side = side or ('over' if 'over' in recommendation else 'under' if 'under' in recommendation else '')
            
            if betting_line and bet_side:
                if bet_side == 'over':
                    return actual_total > betting_line
                elif bet_side == 'under':
                    return actual_total < betting_line
        
        # Handle moneyline bets
        elif bet_type == 'moneyline':
            # Get the side/team of the bet
            bet_side = side or ('away' if 'away' in recommendation else 'home' if 'home' in recommendation else '')
            
            if bet_side:
                return actual_winner == bet_side
            
            # Fallback: check team names in recommendation
            away_team = normalize_team_name(prediction.get('away_team', ''))
            home_team = normalize_team_name(prediction.get('home_team', ''))
            
            if away_team.lower() in recommendation:
                return actual_winner == 'away'
            elif home_team.lower() in recommendation:
                return actual_winner == 'home'
        
        # Handle run line bets (spread)
        elif bet_type in ['runline', 'run_line']:
            run_line = bet.get('line', 1.5)  # Default MLB run line
            bet_side = side or ('away' if 'away' in recommendation else 'home' if 'home' in recommendation else '')
            
            if bet_side == 'away':
                # Away team getting points (underdog)
                away_score_adjusted = final_score['away_score'] + abs(run_line)
                return away_score_adjusted > final_score['home_score']
            elif bet_side == 'home':
                # Home team giving points (favorite)  
                home_score_adjusted = final_score['home_score'] - abs(run_line)
                return home_score_adjusted > final_score['away_score']
        
        # If we can't determine the bet type or outcome, return False
        return False
    
    def calculate_winnings(self, bet_amount: float, american_odds: str) -> float:
        """Calculate total winnings from American odds (including original bet back)"""
        try:
            # Check if odds are negative BEFORE removing the minus sign
            is_negative = american_odds.startswith('-')
            odds = int(american_odds.replace('+', '').replace('-', ''))
            
            if is_negative:
                # Negative odds (favorite): bet $odds to win $100
                # Example: -110 means bet $110 to win $100
                profit = bet_amount * (100 / odds)
            else:
                # Positive odds (underdog): bet $100 to win $odds
                # Example: +150 means bet $100 to win $150
                profit = bet_amount * (odds / 100)
            
            # Return total payout: original bet + profit
            return round(bet_amount + profit, 2)
        except:
            # Default to even money if odds parsing fails - return double the bet
            return bet_amount * 2
    
    def get_cumulative_analysis(self) -> Dict:
        """Get cumulative analysis across all available dates"""
        available_dates = self.get_available_dates()
        
        cumulative_stats = {
            'analysis_period': f"{self.start_date} to {max(available_dates) if available_dates else 'present'}",
            'total_dates_analyzed': len(available_dates),
            'model_performance': {
                'total_games': 0,
                'winner_correct': 0,
                'winner_accuracy': 0,
                'total_runs_within_1': 0,
                'total_runs_within_2': 0,
                'total_runs_accuracy_1': 0,
                'total_runs_accuracy_2': 0,
                'average_score_diff': 0
            },
            'betting_performance': {
                'total_recommendations': 0,
                'correct_recommendations': 0,
                'overall_accuracy': 0,
                'moneyline_stats': {'total': 0, 'correct': 0, 'accuracy': 0},
                'total_stats': {'total': 0, 'correct': 0, 'accuracy': 0},
                'runline_stats': {'total': 0, 'correct': 0, 'accuracy': 0},
                'total_bet_amount': 0,
                'total_winnings': 0,
                'net_profit': 0,
                'roi_percentage': 0
            },
            'daily_breakdown': []
        }
        
        total_score_diff_sum = 0
        total_games_for_avg = 0
        
        for date in available_dates:
            logger.info(f"Analyzing {date}...")
            
            predictions = self.load_predictions_for_date(date)
            final_scores = self.load_final_scores_for_date(date)
            
            if not predictions or not final_scores:
                logger.warning(f"Skipping {date} - missing data")
                continue
            
            # Analyze this date
            model_perf = self.analyze_model_performance(predictions, final_scores)
            betting_perf = self.analyze_betting_recommendations(predictions, final_scores)
            
            # Add to cumulative stats
            cumulative_stats['model_performance']['total_games'] += model_perf['total_games']
            cumulative_stats['model_performance']['winner_correct'] += model_perf['winner_correct']
            cumulative_stats['model_performance']['total_runs_within_1'] += model_perf['total_runs_within_1']
            cumulative_stats['model_performance']['total_runs_within_2'] += model_perf['total_runs_within_2']
            total_score_diff_sum += model_perf['average_score_diff'] * model_perf['total_games']
            total_games_for_avg += model_perf['total_games']
            
            cumulative_stats['betting_performance']['total_recommendations'] += betting_perf['total_recommendations']
            cumulative_stats['betting_performance']['correct_recommendations'] += betting_perf['correct_recommendations']
            cumulative_stats['betting_performance']['total_bet_amount'] += betting_perf['total_bet_amount']
            cumulative_stats['betting_performance']['total_winnings'] += betting_perf['total_winnings']
            
            # Add bet type stats
            for bet_type in ['moneyline_stats', 'total_stats', 'runline_stats']:
                cumulative_stats['betting_performance'][bet_type]['total'] += betting_perf[bet_type]['total']
                cumulative_stats['betting_performance'][bet_type]['correct'] += betting_perf[bet_type]['correct']
            
            # Store daily breakdown
            cumulative_stats['daily_breakdown'].append({
                'date': date,
                'model_performance': model_perf,
                'betting_performance': betting_perf
            })
        
        # Calculate final percentages - LIMITED TO 2 DECIMAL PLACES MAX
        mp = cumulative_stats['model_performance']
        if mp['total_games'] > 0:
            mp['winner_accuracy'] = round((mp['winner_correct'] / mp['total_games']) * 100, 2)
            mp['total_runs_accuracy_1'] = round((mp['total_runs_within_1'] / mp['total_games']) * 100, 2)
            mp['total_runs_accuracy_2'] = round((mp['total_runs_within_2'] / mp['total_games']) * 100, 2)
            mp['average_score_diff'] = round(total_score_diff_sum / total_games_for_avg, 2) if total_games_for_avg > 0 else 0
        
        bp = cumulative_stats['betting_performance']
        if bp['total_recommendations'] > 0:
            bp['overall_accuracy'] = round((bp['correct_recommendations'] / bp['total_recommendations']) * 100, 2)
        
        for bet_type in ['moneyline_stats', 'total_stats', 'runline_stats']:
            if bp[bet_type]['total'] > 0:
                bp[bet_type]['accuracy'] = round((bp[bet_type]['correct'] / bp[bet_type]['total']) * 100, 2)
        
        if bp['total_bet_amount'] > 0:
            bp['net_profit'] = round(bp['total_winnings'] - bp['total_bet_amount'], 2)
            bp['roi_percentage'] = round((bp['net_profit'] / bp['total_bet_amount']) * 100, 2)
        
        logger.info(f"Cumulative analysis complete: {mp['total_games']} games, {bp['total_recommendations']} bets, {bp['roi_percentage']}% ROI")
        return cumulative_stats
    
    def get_date_analysis(self, date: str) -> Dict:
        """Get detailed analysis for a specific date"""
        predictions = self.load_predictions_for_date(date)
        final_scores = self.load_final_scores_for_date(date)
        
        if not predictions:
            return {'error': f'No predictions found for {date}'}
        
        if not final_scores:
            return {'error': f'No final scores found for {date}'}
        
        model_perf = self.analyze_model_performance(predictions, final_scores)
        betting_perf = self.analyze_betting_recommendations(predictions, final_scores)
        
        return {
            'date': date,
            'model_performance': model_perf,
            'betting_performance': betting_perf,
            'predictions': predictions,
            'final_scores': final_scores
        }

# Global analyzer instance
historical_analyzer = ComprehensiveHistoricalAnalyzer()
