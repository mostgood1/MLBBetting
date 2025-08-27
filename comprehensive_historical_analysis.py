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
        """Get list of available analysis dates from unified cache and betting files"""
        available_dates = set()
        
        # First, check unified cache
        cache_path = f"{self.data_dir}/unified_predictions_cache.json"
        try:
            with open(cache_path, 'r') as f:
                cache = json.load(f)
            
            predictions_by_date = cache.get('predictions_by_date', {})
            available_dates.update(predictions_by_date.keys())
            logger.info(f"Found {len(predictions_by_date)} dates in unified cache")
            
        except FileNotFoundError:
            logger.warning("Unified cache not found, using file-based approach")
        except Exception as e:
            logger.error(f"Error reading unified cache: {e}")
        
        # Also check for betting recommendation files as fallback
        betting_files = glob.glob(f"{self.data_dir}/betting_recommendations_2025_08_*.json")
        games_files = glob.glob(f"{self.data_dir}/games_2025-08-*.json")
        
        # Extract dates from betting files
        betting_dates = set()
        for file in betting_files:
            date_part = os.path.basename(file).replace('betting_recommendations_', '').replace('.json', '')
            betting_dates.add(date_part.replace('_', '-'))
        
        # Extract dates from games files
        games_dates = set()
        for file in games_files:
            date_part = os.path.basename(file).replace('games_', '').replace('.json', '')
            games_dates.add(date_part)
        
        # Add dates that have either predictions or games data
        available_dates.update(betting_dates)
        available_dates.update(games_dates)
        
        # Filter to start from our analysis start date
        filtered_dates = [d for d in available_dates if d >= self.start_date]
        filtered_dates.sort()
        
        logger.info(f"Found {len(filtered_dates)} dates with complete data since {self.start_date}")
        return filtered_dates
    
    def load_predictions_for_date(self, date: str) -> Dict:
        """Load predictions for a specific date from unified cache"""
        cache_path = f"{self.data_dir}/unified_predictions_cache.json"
        
        try:
            with open(cache_path, 'r') as f:
                cache = json.load(f)
            
            predictions_by_date = cache.get('predictions_by_date', {})
            date_data = predictions_by_date.get(date, {})
            games = date_data.get('games', {})
            
            if games:
                logger.info(f"Loaded {len(games)} games from unified cache for {date}")
                return games
            else:
                logger.warning(f"No games found in unified cache for {date}")
                
        except FileNotFoundError:
            logger.warning(f"Unified cache not found, trying fallback for {date}")
        except Exception as e:
            logger.error(f"Error loading from unified cache for {date}: {e}")
        
        # Fallback to old format
        date_formatted = date.replace('-', '_')
        file_path = f"{self.data_dir}/betting_recommendations_{date_formatted}.json"
        
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            return data.get('games', {})
        except FileNotFoundError:
            logger.warning(f"No betting recommendations found for {date}")
            return {}
        except Exception as e:
            logger.error(f"Error loading predictions for {date}: {e}")
            return {}
    
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
        """Analyze betting recommendations performance and calculate ROI"""
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
        
        for game_key, prediction in predictions.items():
            # Normalize the key for matching
            away_team = normalize_team_name(prediction.get('away_team', ''))
            home_team = normalize_team_name(prediction.get('home_team', ''))
            normalized_key = f"{away_team}_vs_{home_team}"
            
            if normalized_key not in final_scores:
                continue
            
            final_score = final_scores[normalized_key]
            value_bets = prediction.get('value_bets', [])
            
            for bet in value_bets:
                stats['total_recommendations'] += 1
                stats['total_bet_amount'] += bet_unit
                
                bet_type = bet.get('type', 'unknown')
                recommendation = bet.get('recommendation', '')
                american_odds = bet.get('american_odds', '+100')
                expected_value = bet.get('expected_value', 0)
                
                # Determine if bet won
                bet_won = self.evaluate_bet(bet, final_score, prediction)
                
                if bet_won:
                    stats['correct_recommendations'] += 1
                    # Calculate winnings from American odds
                    winnings = self.calculate_winnings(bet_unit, american_odds)
                    stats['total_winnings'] += winnings
                else:
                    winnings = 0
                
                # Track by bet type
                if 'moneyline' in recommendation.lower() or bet_type == 'moneyline':
                    stats['moneyline_stats']['total'] += 1
                    if bet_won:
                        stats['moneyline_stats']['correct'] += 1
                elif 'total' in recommendation.lower() or 'over' in recommendation.lower() or 'under' in recommendation.lower() or bet_type == 'total':
                    stats['total_stats']['total'] += 1
                    if bet_won:
                        stats['total_stats']['correct'] += 1
                elif 'run' in recommendation.lower() or bet_type == 'runline':
                    stats['runline_stats']['total'] += 1
                    if bet_won:
                        stats['runline_stats']['correct'] += 1
                
                # Store detailed bet info
                stats['detailed_bets'].append({
                    'game_key': normalized_key,
                    'away_team': away_team,
                    'home_team': home_team,
                    'bet_type': bet_type,
                    'recommendation': recommendation,
                    'american_odds': american_odds,
                    'expected_value': expected_value,
                    'bet_amount': bet_unit,
                    'bet_won': bet_won,
                    'winnings': winnings,
                    'confidence': bet.get('confidence', 'unknown')
                })
        
        # Calculate percentages and ROI - LIMITED TO 2 DECIMAL PLACES MAX
        if stats['total_recommendations'] > 0:
            stats['overall_accuracy'] = round((stats['correct_recommendations'] / stats['total_recommendations']) * 100, 2)
        else:
            stats['overall_accuracy'] = 0
        
        for bet_type in ['moneyline_stats', 'total_stats', 'runline_stats']:
            if stats[bet_type]['total'] > 0:
                stats[bet_type]['accuracy'] = round((stats[bet_type]['correct'] / stats[bet_type]['total']) * 100, 2)
        
        # Calculate ROI
        if stats['total_bet_amount'] > 0:
            net_profit = stats['total_winnings'] - stats['total_bet_amount']
            stats['roi_percentage'] = round((net_profit / stats['total_bet_amount']) * 100, 2)
            stats['net_profit'] = round(net_profit, 2)
        else:
            stats['roi_percentage'] = 0
            stats['net_profit'] = 0
        
        return stats
    
    def evaluate_bet(self, bet: Dict, final_score: Dict, prediction: Dict) -> bool:
        """Evaluate if a specific bet won based on final score"""
        recommendation = bet.get('recommendation', '').lower()
        bet_type = bet.get('type', '').lower()
        
        actual_total = final_score['total_runs']
        actual_winner = final_score['winner']
        
        # Handle total bets (over/under)
        if 'over' in recommendation or 'under' in recommendation or bet_type == 'total':
            betting_line = bet.get('betting_line', 0)
            if not betting_line:
                # Try to extract from recommendation text
                import re
                line_match = re.search(r'(\d+\.?\d*)', recommendation)
                if line_match:
                    betting_line = float(line_match.group(1))
            
            if betting_line:
                if 'over' in recommendation:
                    return actual_total > betting_line
                elif 'under' in recommendation:
                    return actual_total < betting_line
        
        # Handle moneyline bets
        elif 'moneyline' in recommendation or bet_type == 'moneyline':
            # Extract team from recommendation
            away_team = normalize_team_name(prediction.get('away_team', ''))
            home_team = normalize_team_name(prediction.get('home_team', ''))
            
            if away_team.lower() in recommendation:
                return actual_winner == 'away'
            elif home_team.lower() in recommendation:
                return actual_winner == 'home'
        
        # Handle run line bets (spread)
        elif 'run' in recommendation or bet_type == 'runline':
            # This would need more specific logic based on the recommendation format
            # For now, return False for unhandled cases
            pass
        
        return False
    
    def calculate_winnings(self, bet_amount: float, american_odds: str) -> float:
        """Calculate winnings from American odds"""
        try:
            odds = int(american_odds.replace('+', '').replace('-', ''))
            
            if american_odds.startswith('-'):
                # Negative odds (favorite)
                winnings = bet_amount + (bet_amount * (100 / odds))
            else:
                # Positive odds (underdog)
                winnings = bet_amount + (bet_amount * (odds / 100))
            
            return round(winnings, 2)
        except:
            # Default to even money if odds parsing fails
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
        
        # If no final scores, return predictions only (for current/future dates)
        if not final_scores:
            logger.info(f"No final scores found for {date}, returning predictions only")
            return {
                'date': date,
                'prediction_analysis': {
                    'total_games': len(predictions),
                    'games': predictions,
                    'note': 'Final scores not available - predictions only'
                },
                'betting_performance': {
                    'total_recommendations': 0,
                    'correct_recommendations': 0,
                    'overall_accuracy': 0,
                    'roi_percentage': 0,
                    'net_profit': 0,
                    'total_bet_amount': 0,
                    'detailed_bets': [],
                    'moneyline_stats': {'total': 0, 'correct': 0, 'accuracy': 0},
                    'runline_stats': {'total': 0, 'correct': 0, 'accuracy': 0},
                    'total_stats': {'total': 0, 'correct': 0, 'accuracy': 0}
                },
                'predictions': predictions,
                'final_scores': {},
                'has_final_scores': False
            }
        
        model_perf = self.analyze_model_performance(predictions, final_scores)
        betting_perf = self.analyze_betting_recommendations(predictions, final_scores)
        
        return {
            'date': date,
            'prediction_analysis': model_perf,
            'betting_performance': betting_perf,
            'predictions': predictions,
            'final_scores': final_scores,
            'has_final_scores': True
        }

# Global analyzer instance
historical_analyzer = ComprehensiveHistoricalAnalyzer()
