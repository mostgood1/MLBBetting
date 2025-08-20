#!/usr/bin/env python3
"""
Comprehensive Betting Performance Tracker
==========================================
Tracks performance across all betting types:
- Moneyline (ML): Picking the right winner
- Over/Under Totals: Being on the right side of the betting line for runs
- Run Line: Spread betting performance  
- Perfect Games: Picking both winner and total correctly
"""

import json
import logging
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import os

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ComprehensiveBettingPerformanceTracker:
    """Tracks comprehensive betting performance across all betting types"""
    
    def __init__(self, data_dir: str = None):
        self.data_dir = Path(data_dir) if data_dir else Path(__file__).parent / "MLB-Betting" / "data"
        self.performance_file = self.data_dir / "comprehensive_betting_performance.json"
        self.today = datetime.now().strftime('%Y-%m-%d')
        
    def load_performance_history(self) -> Dict:
        """Load existing comprehensive performance history"""
        try:
            if self.performance_file.exists():
                with open(self.performance_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading comprehensive performance history: {e}")
        
        return {
            'metadata': {
                'created': datetime.now().isoformat(),
                'last_updated': datetime.now().isoformat(),
                'version': '2.0'
            },
            'betting_types': {
                'moneyline': {
                    'total_bets': 0,
                    'total_wins': 0,
                    'total_losses': 0,
                    'win_rate': 0.0,
                    'roi': 0.0,
                    'total_profit': 0.0
                },
                'totals': {
                    'total_bets': 0,
                    'total_wins': 0,
                    'total_losses': 0,
                    'win_rate': 0.0,
                    'roi': 0.0,
                    'total_profit': 0.0
                },
                'run_line': {
                    'total_bets': 0,
                    'total_wins': 0,
                    'total_losses': 0,
                    'win_rate': 0.0,
                    'roi': 0.0,
                    'total_profit': 0.0
                },
                'perfect_games': {
                    'total_opportunities': 0,
                    'perfect_hits': 0,
                    'success_rate': 0.0,
                    'value_created': 0.0
                }
            },
            'daily_performance': {},
            'bet_history': []
        }
    
    def record_betting_recommendations(self, predictions_data: Dict) -> None:
        """Record betting recommendations from predictions data"""
        try:
            performance_data = self.load_performance_history()
            
            today_key = self.today
            if today_key not in performance_data['daily_performance']:
                performance_data['daily_performance'][today_key] = {
                    'date': today_key,
                    'moneyline': {'recommendations': 0, 'pending': 0, 'completed': 0, 'wins': 0},
                    'totals': {'recommendations': 0, 'pending': 0, 'completed': 0, 'wins': 0},
                    'run_line': {'recommendations': 0, 'pending': 0, 'completed': 0, 'wins': 0},
                    'perfect_games': {'opportunities': 0, 'perfect_hits': 0}
                }
            
            recommendations_recorded = 0
            
            # Process each game prediction
            for game_key, game_data in predictions_data.items():
                if not isinstance(game_data, dict) or 'teams' not in game_data:
                    continue
                
                game_id = f"{game_data['teams']['away']} @ {game_data['teams']['home']}"
                
                # Extract betting recommendations
                ml_recommendation = self._extract_moneyline_recommendation(game_data)
                total_recommendation = self._extract_total_recommendation(game_data)
                rl_recommendation = self._extract_runline_recommendation(game_data)
                
                # Record moneyline bet
                if ml_recommendation:
                    bet_record = {
                        'date': today_key,
                        'game': game_id,
                        'betting_type': 'moneyline',
                        'recommendation': ml_recommendation['recommendation'],
                        'team': ml_recommendation['team'],
                        'confidence': ml_recommendation.get('confidence', 'MEDIUM'),
                        'reasoning': ml_recommendation.get('reasoning', ''),
                        'odds': ml_recommendation.get('odds', '-110'),
                        'status': 'pending',
                        'actual_result': None,
                        'recorded_at': datetime.now().isoformat()
                    }
                    performance_data['bet_history'].append(bet_record)
                    performance_data['daily_performance'][today_key]['moneyline']['recommendations'] += 1
                    performance_data['daily_performance'][today_key]['moneyline']['pending'] += 1
                    recommendations_recorded += 1
                
                # Record totals bet
                if total_recommendation:
                    bet_record = {
                        'date': today_key,
                        'game': game_id,
                        'betting_type': 'totals',
                        'recommendation': total_recommendation['recommendation'],
                        'predicted_total': total_recommendation.get('predicted_total'),
                        'betting_line': total_recommendation.get('betting_line'),
                        'confidence': total_recommendation.get('confidence', 'MEDIUM'),
                        'reasoning': total_recommendation.get('reasoning', ''),
                        'odds': total_recommendation.get('odds', '-110'),
                        'status': 'pending',
                        'actual_result': None,
                        'recorded_at': datetime.now().isoformat()
                    }
                    performance_data['bet_history'].append(bet_record)
                    performance_data['daily_performance'][today_key]['totals']['recommendations'] += 1
                    performance_data['daily_performance'][today_key]['totals']['pending'] += 1
                    recommendations_recorded += 1
                
                # Record run line bet
                if rl_recommendation:
                    bet_record = {
                        'date': today_key,
                        'game': game_id,
                        'betting_type': 'run_line',
                        'recommendation': rl_recommendation['recommendation'],
                        'team': rl_recommendation['team'],
                        'side': rl_recommendation['side'],
                        'cover_probability': rl_recommendation.get('cover_probability'),
                        'expected_value': rl_recommendation.get('expected_value'),
                        'confidence': rl_recommendation.get('confidence', 'MEDIUM'),
                        'reasoning': rl_recommendation.get('reasoning', ''),
                        'odds': rl_recommendation.get('odds', '-110'),
                        'status': 'pending',
                        'actual_result': None,
                        'recorded_at': datetime.now().isoformat()
                    }
                    performance_data['bet_history'].append(bet_record)
                    performance_data['daily_performance'][today_key]['run_line']['recommendations'] += 1
                    performance_data['daily_performance'][today_key]['run_line']['pending'] += 1
                    recommendations_recorded += 1
                
                # Track perfect game opportunities
                if ml_recommendation and total_recommendation:
                    performance_data['daily_performance'][today_key]['perfect_games']['opportunities'] += 1
            
            # Update metadata
            performance_data['metadata']['last_updated'] = datetime.now().isoformat()
            performance_data['metadata']['total_recommendations_tracked'] = len(performance_data['bet_history'])
            
            self.save_performance_history(performance_data)
            logger.info(f"🎯 Recorded {recommendations_recorded} comprehensive betting recommendations for {today_key}")
            
        except Exception as e:
            logger.error(f"Error recording betting recommendations: {e}")
    
    def _extract_moneyline_recommendation(self, game_data: Dict) -> Optional[Dict]:
        """Extract moneyline betting recommendation from game data"""
        try:
            prediction = game_data.get('prediction', {})
            confidence = prediction.get('confidence', 0)
            
            # Only recommend if confidence is reasonable
            if confidence < 55:  # Less than 55% confidence
                return None
            
            winner = prediction.get('winner')
            if not winner:
                return None
            
            return {
                'recommendation': f"{winner} ML",
                'team': winner,
                'confidence': self._get_confidence_level(confidence),
                'reasoning': f"Predicted winner with {confidence}% confidence",
                'odds': '-110'  # Standard moneyline odds
            }
        except Exception as e:
            logger.error(f"Error extracting moneyline recommendation: {e}")
            return None
    
    def _extract_total_recommendation(self, game_data: Dict) -> Optional[Dict]:
        """Extract totals betting recommendation from game data"""
        try:
            prediction = game_data.get('prediction', {})
            predicted_total = prediction.get('total_runs')
            
            # Get betting line (or use predicted total as proxy)
            betting_line = game_data.get('betting_lines', {}).get('total')
            if not betting_line:
                return None
            
            if not predicted_total:
                return None
            
            # Determine over/under recommendation
            if predicted_total > betting_line:
                recommendation = f"Over {betting_line}"
                reasoning = f"Predicted {predicted_total} runs vs line of {betting_line}"
            else:
                recommendation = f"Under {betting_line}"
                reasoning = f"Predicted {predicted_total} runs vs line of {betting_line}"
            
            return {
                'recommendation': recommendation,
                'predicted_total': predicted_total,
                'betting_line': betting_line,
                'confidence': 'MEDIUM',
                'reasoning': reasoning,
                'odds': '-110'
            }
        except Exception as e:
            logger.error(f"Error extracting totals recommendation: {e}")
            return None
    
    def _extract_runline_recommendation(self, game_data: Dict) -> Optional[Dict]:
        """Extract run line betting recommendation from game data"""
        try:
            run_line_analysis = game_data.get('run_line_analysis')
            if not run_line_analysis:
                return None
            
            recommendation = run_line_analysis.get('recommendation')
            if not recommendation or recommendation == 'NO BET':
                return None
            
            team = run_line_analysis.get('recommended_team')
            side = run_line_analysis.get('recommended_side', 'away')
            
            return {
                'recommendation': recommendation,
                'team': team,
                'side': side,
                'cover_probability': run_line_analysis.get('cover_probability'),
                'expected_value': run_line_analysis.get('expected_value'),
                'confidence': run_line_analysis.get('confidence', 'MEDIUM'),
                'reasoning': run_line_analysis.get('reasoning', ''),
                'odds': '-110'
            }
        except Exception as e:
            logger.error(f"Error extracting run line recommendation: {e}")
            return None
    
    def _get_confidence_level(self, confidence_pct: float) -> str:
        """Convert confidence percentage to level"""
        if confidence_pct >= 70:
            return 'HIGH'
        elif confidence_pct >= 60:
            return 'MEDIUM'
        else:
            return 'LOW'
    
    def update_results_from_actual_scores(self, scores_data: Dict) -> None:
        """Update bet results based on actual game scores"""
        try:
            performance_data = self.load_performance_history()
            updates_made = 0
            
            for bet in performance_data['bet_history']:
                if bet['status'] != 'pending':
                    continue
                
                # Find matching game in scores data
                game_result = self._find_game_result(bet, scores_data)
                if not game_result:
                    continue
                
                # Update bet result based on type
                if bet['betting_type'] == 'moneyline':
                    bet['actual_result'] = self._check_moneyline_result(bet, game_result)
                elif bet['betting_type'] == 'totals':
                    bet['actual_result'] = self._check_totals_result(bet, game_result)
                elif bet['betting_type'] == 'run_line':
                    bet['actual_result'] = self._check_runline_result(bet, game_result)
                
                if bet['actual_result'] is not None:
                    bet['status'] = 'won' if bet['actual_result'] else 'lost'
                    updates_made += 1
            
            # Check for perfect games
            self._update_perfect_games(performance_data)
            
            # Recalculate performance statistics
            self._recalculate_all_performance_stats(performance_data)
            
            # Save updated data
            performance_data['metadata']['last_updated'] = datetime.now().isoformat()
            self.save_performance_history(performance_data)
            
            if updates_made > 0:
                logger.info(f"✅ Updated {updates_made} bet results from actual scores")
            
        except Exception as e:
            logger.error(f"Error updating results from actual scores: {e}")
    
    def _find_game_result(self, bet: Dict, scores_data: Dict) -> Optional[Dict]:
        """Find the game result for a bet in the scores data"""
        # Implementation to match bet game with actual scores
        # This would match based on teams and date
        return None  # Placeholder - implement based on your scores data structure
    
    def _check_moneyline_result(self, bet: Dict, game_result: Dict) -> bool:
        """Check if moneyline bet won"""
        home_score = game_result.get('home_score', 0)
        away_score = game_result.get('away_score', 0)
        
        if home_score > away_score:
            winner = game_result.get('home_team')
        else:
            winner = game_result.get('away_team')
        
        return bet['team'] == winner
    
    def _check_totals_result(self, bet: Dict, game_result: Dict) -> bool:
        """Check if totals bet won"""
        total_runs = game_result.get('home_score', 0) + game_result.get('away_score', 0)
        betting_line = bet['betting_line']
        
        if 'Over' in bet['recommendation']:
            return total_runs > betting_line
        else:  # Under
            return total_runs < betting_line
    
    def _check_runline_result(self, bet: Dict, game_result: Dict) -> bool:
        """Check if run line bet won"""
        home_score = game_result.get('home_score', 0)
        away_score = game_result.get('away_score', 0)
        
        if bet['side'] == 'away':
            # Away team +1.5: wins if they lose by 1 or win outright
            margin = away_score - home_score
            return margin >= -1
        else:
            # Home team -1.5: wins if they win by 2 or more
            margin = home_score - away_score
            return margin >= 2
    
    def _update_perfect_games(self, performance_data: Dict) -> None:
        """Update perfect game statistics"""
        # Group bets by game and check for perfect hits
        games = {}
        for bet in performance_data['bet_history']:
            if bet['status'] in ['won', 'lost']:
                game_key = f"{bet['date']}_{bet['game']}"
                if game_key not in games:
                    games[game_key] = {'moneyline': None, 'totals': None}
                
                if bet['betting_type'] == 'moneyline':
                    games[game_key]['moneyline'] = bet['actual_result']
                elif bet['betting_type'] == 'totals':
                    games[game_key]['totals'] = bet['actual_result']
        
        # Count perfect games
        perfect_hits = 0
        for game_data in games.values():
            if (game_data['moneyline'] is True and game_data['totals'] is True):
                perfect_hits += 1
        
        # Update metadata
        performance_data['betting_types']['perfect_games']['perfect_hits'] = perfect_hits
        if len(games) > 0:
            performance_data['betting_types']['perfect_games']['success_rate'] = (perfect_hits / len(games)) * 100
    
    def _recalculate_all_performance_stats(self, performance_data: Dict) -> None:
        """Recalculate performance statistics for all betting types"""
        betting_types = ['moneyline', 'totals', 'run_line']
        
        for betting_type in betting_types:
            completed_bets = [bet for bet in performance_data['bet_history'] 
                            if bet['betting_type'] == betting_type and bet['status'] in ['won', 'lost']]
            
            wins = [bet for bet in completed_bets if bet['status'] == 'won']
            losses = [bet for bet in completed_bets if bet['status'] == 'lost']
            
            total_completed = len(completed_bets)
            total_wins = len(wins)
            total_losses = len(losses)
            
            win_rate = (total_wins / total_completed * 100) if total_completed > 0 else 0.0
            
            # Calculate ROI (assuming standard -110 odds)
            total_profit = 0
            for bet in completed_bets:
                if bet['status'] == 'won':
                    total_profit += 0.91  # Win $0.91 for every $1 bet at -110 odds
                else:
                    total_profit -= 1.0   # Lose $1 for every bet
            
            roi = (total_profit / total_completed * 100) if total_completed > 0 else 0.0
            
            # Update betting type statistics
            performance_data['betting_types'][betting_type].update({
                'total_bets': total_completed,
                'total_wins': total_wins,
                'total_losses': total_losses,
                'win_rate': round(win_rate, 2),
                'roi': round(roi, 2),
                'total_profit': round(total_profit, 2)
            })
    
    def save_performance_history(self, performance_data: Dict) -> None:
        """Save comprehensive performance history to file"""
        try:
            # Ensure directory exists
            self.data_dir.mkdir(parents=True, exist_ok=True)
            
            with open(self.performance_file, 'w') as f:
                json.dump(performance_data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving comprehensive performance history: {e}")
    
    def get_performance_summary(self) -> Dict:
        """Get comprehensive performance summary for API/frontend"""
        performance_data = self.load_performance_history()
        
        # Get recent performance (last 30 days)
        current_date = datetime.now()
        recent_cutoff = current_date - timedelta(days=30)
        
        summary = {
            'overall': {},
            'recent_30_days': {},
            'last_updated': performance_data.get('metadata', {}).get('last_updated')
        }
        
        betting_types = ['moneyline', 'totals', 'run_line', 'perfect_games']
        
        for betting_type in betting_types:
            type_data = performance_data.get('betting_types', {}).get(betting_type, {})
            
            # Overall performance
            summary['overall'][betting_type] = {
                'total_bets': type_data.get('total_bets', 0),
                'win_rate': type_data.get('win_rate', 0.0),
                'roi': type_data.get('roi', 0.0),
                'total_profit': type_data.get('total_profit', 0.0)
            }
            
            # Recent 30-day performance
            recent_bets = []
            for bet in performance_data.get('bet_history', []):
                if bet.get('betting_type') == betting_type:
                    bet_date = datetime.fromisoformat(bet['date'])
                    if bet_date >= recent_cutoff:
                        recent_bets.append(bet)
            
            recent_completed = [bet for bet in recent_bets if bet['status'] in ['won', 'lost']]
            recent_wins = len([bet for bet in recent_completed if bet['status'] == 'won'])
            recent_win_rate = (recent_wins / len(recent_completed) * 100) if recent_completed else 0.0
            
            summary['recent_30_days'][betting_type] = {
                'total_bets': len(recent_bets),
                'completed_bets': len(recent_completed),
                'win_rate': round(recent_win_rate, 2),
                'pending_bets': len([bet for bet in recent_bets if bet['status'] == 'pending'])
            }
        
        return summary

if __name__ == "__main__":
    # Example usage
    tracker = ComprehensiveBettingPerformanceTracker()
    
    # Load predictions and record recommendations
    try:
        # Try current day's betting recommendations first
        betting_file = f'data/betting_recommendations_{datetime.now().strftime("%Y_%m_%d")}.json'
        if not os.path.exists(betting_file):
            # Fall back to unified cache
            betting_file = 'MLB-Betting/data/unified_predictions_cache.json'
        
        print(f"Loading betting recommendations from: {betting_file}")
        with open(betting_file, 'r') as f:
            betting_data = json.load(f)
        
        # Convert betting recommendations format to prediction format for tracking
        if 'games' in betting_data:
            # Current day's betting recommendations format
            predictions = {}
            for game_key, game_data in betting_data['games'].items():
                # Convert to expected format
                prediction_data = {
                    'teams': {
                        'away': game_data['away_team'],
                        'home': game_data['home_team']
                    },
                    'prediction': {
                        'winner': game_data['away_team'] if game_data['win_probabilities']['away_prob'] > 0.55 
                                 else game_data['home_team'] if game_data['win_probabilities']['home_prob'] > 0.55 
                                 else None,
                        'confidence': max(game_data['win_probabilities']['away_prob'], 
                                        game_data['win_probabilities']['home_prob']) * 100,
                        'total_runs': game_data['predicted_total_runs']
                    },
                    'betting_lines': {
                        'total': game_data['betting_recommendations']['total_runs'].get('line', 9.5)
                    },
                    'run_line_analysis': game_data.get('run_line_analysis', {})
                }
                predictions[game_key] = prediction_data
        else:
            # Legacy unified cache format
            predictions = betting_data
        
        tracker.record_betting_recommendations(predictions)
        
        # Print summary
        summary = tracker.get_performance_summary()
        print(f"Comprehensive Betting Performance Summary:")
        for betting_type in ['moneyline', 'totals', 'run_line', 'perfect_games']:
            overall = summary['overall'][betting_type]
            print(f"{betting_type.replace('_', ' ').title()}: {overall['total_bets']} bets, {overall['win_rate']:.1f}% win rate, {overall['roi']:.1f}% ROI")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
