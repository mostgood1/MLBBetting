"""
Redesigned MLB Betting Analytics System
Three distinct tabs for different analytical focuses:
1. Model Performance - Prediction accuracy analysis
2. Betting Recommendations - All betting recommendations performance
3. Kelly Best of Best - High-confidence Kelly bets (started 8/27)
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
import os
from comprehensive_historical_analysis import ComprehensiveHistoricalAnalyzer

class RedesignedBettingAnalytics:
    def __init__(self):
        """Initialize the redesigned analytics system"""
        self.logger = logging.getLogger(__name__)
        self.base_path = Path(__file__).parent
        self.historical_analyzer = ComprehensiveHistoricalAnalyzer()
        
        # Key dates
        self.system_start_date = "2025-08-15"
        self.kelly_start_date = "2025-08-27"
        
        # Simple cache to avoid recalculating the same data
        self._cache = {}
        self._cache_timestamp = None
        self._cache_duration = 300  # 5 minutes cache
        
        self.logger.info("✅ Redesigned analytics system initialized")
    
    def _is_cache_valid(self):
        """Check if cache is still valid"""
        if self._cache_timestamp is None:
            return False
        
        current_time = datetime.now()
        cache_age = (current_time - self._cache_timestamp).total_seconds()
        return cache_age < self._cache_duration
    
    def _get_cached_cumulative_analysis(self):
        """Get cumulative analysis with caching"""
        if self._is_cache_valid() and 'cumulative_analysis' in self._cache:
            self.logger.info("📊 Using cached cumulative analysis data")
            return self._cache['cumulative_analysis']
        
        self.logger.info("📊 Fetching fresh cumulative analysis data...")
        all_data = self.historical_analyzer.get_cumulative_analysis()
        
        # Cache the result
        self._cache['cumulative_analysis'] = all_data
        self._cache_timestamp = datetime.now()
        
        return all_data
    
    def get_model_performance_analysis(self):
        """
        Tab 1: Model Performance Analysis
        Focus on prediction accuracy - winners, totals within 1-2 runs, home/away team run accuracy
        """
        try:
            self.logger.info("📊 Analyzing model performance...")
            
            # Get all prediction data since 8/15 (with caching)
            all_data = self._get_cached_cumulative_analysis()
            
            if not all_data.get('success', True):
                raise Exception("Failed to get cumulative analysis")
            
            # Extract model performance data
            model_perf = all_data.get('model_performance', {})
            daily_breakdown = all_data.get('daily_breakdown', [])
            
            # Initialize performance tracking with data from cumulative analysis
            model_performance = {
                'overall_stats': {
                    'total_games': model_perf.get('total_games', 0),
                    'winner_correct': model_perf.get('winner_correct', 0),
                    'winner_accuracy': model_perf.get('winner_accuracy', 0),
                    'totals_within_1_run': model_perf.get('total_runs_within_1', 0),
                    'totals_within_2_runs': model_perf.get('total_runs_within_2', 0),
                    'totals_within_1_pct': model_perf.get('total_runs_accuracy_1', 0),
                    'totals_within_2_pct': model_perf.get('total_runs_accuracy_2', 0),
                    'total_predictions': model_perf.get('total_games', 0),
                    # Initialize counters for home/away team run accuracy
                    'home_team_total_games': 0,
                    'home_team_runs_within_1': 0,
                    'home_team_runs_within_2': 0,
                    'away_team_total_games': 0,
                    'away_team_runs_within_1': 0,
                    'away_team_runs_within_2': 0,
                    'home_team_runs_accuracy_1': 0,
                    'home_team_runs_accuracy_2': 0,
                    'away_team_runs_accuracy_1': 0,
                    'away_team_runs_accuracy_2': 0
                },
                'daily_breakdown': {},
                'date_range': {
                    'start_date': self.system_start_date,
                    'end_date': datetime.now().strftime('%Y-%m-%d'),
                    'total_days': len(daily_breakdown)
                }
            }
            
            # Calculate home/away team run accuracy from all game data
            total_home_games = 0
            total_away_games = 0
            home_within_1 = 0
            home_within_2 = 0
            away_within_1 = 0
            away_within_2 = 0
            
            # Process daily breakdown data
            for day_data in daily_breakdown:
                if not day_data or day_data.get('date', '') < self.system_start_date:
                    continue
                    
                date_str = day_data.get('date', '')
                day_model_perf = day_data.get('model_performance', {})
                games_analyzed = day_model_perf.get('games_analyzed', [])
                
                # Process individual games for home/away accuracy
                day_home_games = 0
                day_away_games = 0
                day_home_within_1 = 0
                day_home_within_2 = 0
                day_away_within_1 = 0
                day_away_within_2 = 0
                
                for game in games_analyzed:
                    if isinstance(game, dict) and game.get('predicted_total', 0) > 0:
                        try:
                            actual_total = game.get('actual_total', 0)
                            predicted_total = game.get('predicted_total', 0)
                            home_score = game.get('home_score', 0)
                            away_score = game.get('away_score', 0)
                            
                            if predicted_total > 0:  # Only process games with valid predictions
                                # Calculate home and away team run predictions
                                # Estimated home/away split based on league averages (52/48 split)
                                predicted_home_runs = predicted_total * 0.52
                                predicted_away_runs = predicted_total * 0.48
                                
                                # Check home team accuracy
                                home_diff = abs(home_score - predicted_home_runs)
                                if home_diff <= 1:
                                    day_home_within_1 += 1
                                    home_within_1 += 1
                                if home_diff <= 2:
                                    day_home_within_2 += 1
                                    home_within_2 += 1
                                day_home_games += 1
                                total_home_games += 1
                                
                                # Check away team accuracy
                                away_diff = abs(away_score - predicted_away_runs)
                                if away_diff <= 1:
                                    day_away_within_1 += 1
                                    away_within_1 += 1
                                if away_diff <= 2:
                                    day_away_within_2 += 1
                                    away_within_2 += 1
                                day_away_games += 1
                                total_away_games += 1
                                    
                        except (ValueError, KeyError, TypeError):
                            continue
                
                # Calculate daily stats
                daily_stats = {
                    'date': date_str,
                    'games_analyzed': day_model_perf.get('total_games', 0),
                    'winner_predictions_correct': day_model_perf.get('winner_correct', 0),
                    'total_predictions_made': day_model_perf.get('total_games', 0),
                    'totals_within_1': day_model_perf.get('total_runs_within_1', 0),
                    'totals_within_2': day_model_perf.get('total_runs_within_2', 0),
                    'winner_accuracy': day_model_perf.get('winner_accuracy', 0),
                    'totals_within_1_pct': day_model_perf.get('total_runs_accuracy_1', 0),
                    'totals_within_2_pct': day_model_perf.get('total_runs_accuracy_2', 0),
                    'home_team_games': day_home_games,
                    'home_team_within_1': day_home_within_1,
                    'home_team_within_2': day_home_within_2,
                    'away_team_games': day_away_games,
                    'away_team_within_1': day_away_within_1,
                    'away_team_within_2': day_away_within_2,
                    'home_team_accuracy_1': (day_home_within_1 / day_home_games * 100) if day_home_games > 0 else 0,
                    'home_team_accuracy_2': (day_home_within_2 / day_home_games * 100) if day_home_games > 0 else 0,
                    'away_team_accuracy_1': (day_away_within_1 / day_away_games * 100) if day_away_games > 0 else 0,
                    'away_team_accuracy_2': (day_away_within_2 / day_away_games * 100) if day_away_games > 0 else 0
                }
                
                model_performance['daily_breakdown'][date_str] = daily_stats
            
            # Update overall stats with home/away accuracy
            overall = model_performance['overall_stats']
            overall['home_team_total_games'] = total_home_games
            overall['home_team_runs_within_1'] = home_within_1
            overall['home_team_runs_within_2'] = home_within_2
            overall['away_team_total_games'] = total_away_games
            overall['away_team_runs_within_1'] = away_within_1
            overall['away_team_runs_within_2'] = away_within_2
            overall['home_team_runs_accuracy_1'] = (home_within_1 / total_home_games * 100) if total_home_games > 0 else 0
            overall['home_team_runs_accuracy_2'] = (home_within_2 / total_home_games * 100) if total_home_games > 0 else 0
            overall['away_team_runs_accuracy_1'] = (away_within_1 / total_away_games * 100) if total_away_games > 0 else 0
            overall['away_team_runs_accuracy_2'] = (away_within_2 / total_away_games * 100) if total_away_games > 0 else 0
            
            self.logger.info(f"✅ Model performance analysis complete: {overall['total_games']} games analyzed")
            
            return {
                'success': True,
                'data': model_performance,
                'summary': f"Analyzed {overall['total_games']} games since {self.system_start_date}"
            }
            
        except Exception as e:
            self.logger.error(f"❌ Error in model performance analysis: {str(e)}")
            return {
                'success': False,
                'error': f"Model performance analysis failed: {str(e)}",
                'data': {}
            }
    
    def get_betting_recommendations_performance(self):
        """
        Tab 2: Betting Recommendations Performance
        All betting recommendations (ML/Run Line/Totals) since 8/15 - NOT Kelly based
        """
        try:
            self.logger.info("💰 Analyzing betting recommendations performance...")
            
            # Get betting recommendations data (with caching)
            all_data = self._get_cached_cumulative_analysis()
            
            if not all_data.get('success', True):
                raise Exception("Failed to get cumulative analysis")
            
            # Extract betting performance data
            betting_perf = all_data.get('betting_performance', {})
            daily_breakdown = all_data.get('daily_breakdown', [])
            
            betting_performance = {
                'overall_stats': {
                    'total_recommendations': betting_perf.get('total_recommendations', 0),
                    'ml_bets': {
                        'total': betting_perf.get('moneyline_stats', {}).get('total', 0),
                        'wins': betting_perf.get('moneyline_stats', {}).get('correct', 0),
                        'profit': 0,  # Will calculate
                        'win_rate': betting_perf.get('moneyline_stats', {}).get('accuracy', 0),
                        'roi': 0      # Will calculate
                    },
                    'runline_bets': {
                        'total': betting_perf.get('runline_stats', {}).get('total', 0),
                        'wins': betting_perf.get('runline_stats', {}).get('correct', 0),
                        'profit': 0,  # Will calculate
                        'win_rate': betting_perf.get('runline_stats', {}).get('accuracy', 0),
                        'roi': 0      # Will calculate
                    },
                    'totals_bets': {
                        'total': betting_perf.get('total_stats', {}).get('total', 0),
                        'wins': betting_perf.get('total_stats', {}).get('correct', 0),
                        'profit': 0,  # Will calculate
                        'win_rate': betting_perf.get('total_stats', {}).get('accuracy', 0),
                        'roi': 0      # Will calculate
                    },
                    'overall_profit': betting_perf.get('net_profit', 0),
                    'overall_roi': betting_perf.get('roi_percentage', 0)
                },
                'daily_breakdown': {},
                'bet_type_performance': {}
            }
            
            # Process daily breakdown for betting recommendations
            for day_data in daily_breakdown:
                if not day_data or day_data.get('date', '') < self.system_start_date:
                    continue
                
                date_str = day_data.get('date', '')
                
                daily_stats = {
                    'date': date_str,
                    'total_recommendations': day_data.get('betting_performance', {}).get('total_recommendations', 0),
                    'ml_bets': {
                        'total': day_data.get('betting_performance', {}).get('moneyline_stats', {}).get('total', 0),
                        'wins': day_data.get('betting_performance', {}).get('moneyline_stats', {}).get('correct', 0),
                        'profit': 0  # Calculate based on wins/losses
                    },
                    'runline_bets': {
                        'total': day_data.get('betting_performance', {}).get('runline_stats', {}).get('total', 0),
                        'wins': day_data.get('betting_performance', {}).get('runline_stats', {}).get('correct', 0),
                        'profit': 0  # Calculate based on wins/losses
                    },
                    'totals_bets': {
                        'total': day_data.get('betting_performance', {}).get('total_stats', {}).get('total', 0),
                        'wins': day_data.get('betting_performance', {}).get('total_stats', {}).get('correct', 0),
                        'profit': 0  # Calculate based on wins/losses
                    },
                    'daily_profit': day_data.get('betting_performance', {}).get('net_profit', 0),
                    'daily_roi': day_data.get('betting_performance', {}).get('roi_percentage', 0)
                }
                
                # Calculate profits for each bet type (simplified - assume $100 bets and -110 odds)
                for bet_type in ['ml_bets', 'runline_bets', 'totals_bets']:
                    wins = daily_stats[bet_type]['wins']
                    total = daily_stats[bet_type]['total']
                    losses = total - wins
                    # Profit = (wins * $91) - (losses * $100) [assuming -110 odds]
                    daily_stats[bet_type]['profit'] = (wins * 91) - (losses * 100)
                
                betting_performance['daily_breakdown'][date_str] = daily_stats
            
            # Calculate overall performance
            overall = betting_performance['overall_stats']
            overall['overall_profit'] = (
                overall['ml_bets']['profit'] + 
                overall['runline_bets']['profit'] + 
                overall['totals_bets']['profit']
            )
            
            overall['overall_roi'] = (
                (overall['overall_profit'] / (overall['total_recommendations'] * 100) * 100)
                if overall['total_recommendations'] > 0 else 0
            )
            
            # Calculate win rates by bet type
            for bet_type in ['ml_bets', 'runline_bets', 'totals_bets']:
                bet_data = overall[bet_type]
                bet_data['win_rate'] = (
                    (bet_data['wins'] / bet_data['total'] * 100)
                    if bet_data['total'] > 0 else 0
                )
                bet_data['roi'] = (
                    (bet_data['profit'] / (bet_data['total'] * 100) * 100)
                    if bet_data['total'] > 0 else 0
                )
            
            self.logger.info(f"✅ Betting recommendations analysis complete: {overall['total_recommendations']} recommendations")
            
            return {
                'success': True,
                'data': betting_performance,
                'summary': f"Analyzed {overall['total_recommendations']} betting recommendations since {self.system_start_date}"
            }
            
        except Exception as e:
            self.logger.error(f"❌ Error in betting recommendations analysis: {str(e)}")
            return {
                'success': False,
                'error': f"Betting recommendations analysis failed: {str(e)}",
                'data': {}
            }
    
    def get_kelly_best_of_best_performance(self):
        """
        Tab 3: Kelly "Best of Best" Performance
        High-confidence Kelly bets started 8/27 - track individual bets
        """
        try:
            self.logger.info("🎯 Analyzing Kelly 'Best of Best' performance...")
            
            # Load Kelly betting data
            kelly_data_file = self.base_path / 'data' / 'kelly_betting_recommendations.json'
            
            if not kelly_data_file.exists():
                return {
                    'success': False,
                    'error': 'Kelly betting data file not found',
                    'data': {}
                }
            
            with open(kelly_data_file, 'r') as f:
                kelly_data = json.load(f)
            
            kelly_performance = {
                'overall_stats': {
                    'total_kelly_bets': 0,
                    'total_wins': 0,
                    'total_losses': 0,
                    'win_rate': 0,
                    'total_invested': 0,
                    'total_profit': 0,
                    'roi': 0,
                    'best_day': {'date': '', 'profit': 0, 'roi': 0},
                    'worst_day': {'date': '', 'profit': 0, 'roi': 0}
                },
                'individual_bets': [],
                'daily_summary': {},
                'date_range': {
                    'start_date': self.kelly_start_date,
                    'end_date': datetime.now().strftime('%Y-%m-%d')
                }
            }
            
            # Process each Kelly bet
            for bet_record in kelly_data:
                bet_date = bet_record.get('date', '')
                
                # Only include bets from 8/27 onwards (Kelly "Best of Best" start)
                if bet_date < self.kelly_start_date:
                    continue
                
                # Extract bet details
                kelly_bet = {
                    'date': bet_date,
                    'game': bet_record.get('game', ''),
                    'bet_type': bet_record.get('bet_type', ''),
                    'bet_details': bet_record.get('bet_details', ''),
                    'confidence': bet_record.get('confidence', 0),
                    'kelly_percentage': bet_record.get('kelly_percentage', 0),
                    'recommended_bet': bet_record.get('recommended_bet', 100),
                    'outcome': bet_record.get('outcome', 'pending'),
                    'profit_loss': bet_record.get('profit_loss', 0),
                    'roi': bet_record.get('roi', 0)
                }
                
                kelly_performance['individual_bets'].append(kelly_bet)
                kelly_performance['overall_stats']['total_kelly_bets'] += 1
                kelly_performance['overall_stats']['total_invested'] += kelly_bet['recommended_bet']
                
                if kelly_bet['outcome'] == 'win':
                    kelly_performance['overall_stats']['total_wins'] += 1
                    kelly_performance['overall_stats']['total_profit'] += kelly_bet['profit_loss']
                elif kelly_bet['outcome'] == 'loss':
                    kelly_performance['overall_stats']['total_losses'] += 1
                    kelly_performance['overall_stats']['total_profit'] += kelly_bet['profit_loss']  # profit_loss will be negative
                
                # Track daily performance
                if bet_date not in kelly_performance['daily_summary']:
                    kelly_performance['daily_summary'][bet_date] = {
                        'date': bet_date,
                        'bets': 0,
                        'wins': 0,
                        'losses': 0,
                        'invested': 0,
                        'profit': 0,
                        'roi': 0
                    }
                
                daily = kelly_performance['daily_summary'][bet_date]
                daily['bets'] += 1
                daily['invested'] += kelly_bet['recommended_bet']
                daily['profit'] += kelly_bet['profit_loss']
                
                if kelly_bet['outcome'] == 'win':
                    daily['wins'] += 1
                elif kelly_bet['outcome'] == 'loss':
                    daily['losses'] += 1
            
            # Calculate daily ROI and find best/worst days
            for date, daily in kelly_performance['daily_summary'].items():
                daily['roi'] = (daily['profit'] / daily['invested'] * 100) if daily['invested'] > 0 else 0
                
                # Track best and worst days
                best_day = kelly_performance['overall_stats']['best_day']
                worst_day = kelly_performance['overall_stats']['worst_day']
                
                if daily['profit'] > best_day['profit']:
                    kelly_performance['overall_stats']['best_day'] = {
                        'date': date,
                        'profit': daily['profit'],
                        'roi': daily['roi']
                    }
                
                if daily['profit'] < worst_day['profit']:
                    kelly_performance['overall_stats']['worst_day'] = {
                        'date': date,
                        'profit': daily['profit'],
                        'roi': daily['roi']
                    }
            
            # Calculate overall statistics
            overall = kelly_performance['overall_stats']
            overall['win_rate'] = (
                (overall['total_wins'] / overall['total_kelly_bets'] * 100)
                if overall['total_kelly_bets'] > 0 else 0
            )
            
            overall['roi'] = (
                (overall['total_profit'] / overall['total_invested'] * 100)
                if overall['total_invested'] > 0 else 0
            )
            
            # Sort individual bets by date (most recent first)
            kelly_performance['individual_bets'].sort(key=lambda x: x['date'], reverse=True)
            
            self.logger.info(f"✅ Kelly 'Best of Best' analysis complete: {overall['total_kelly_bets']} Kelly bets")
            
            return {
                'success': True,
                'data': kelly_performance,
                'summary': f"Analyzed {overall['total_kelly_bets']} Kelly 'Best of Best' bets since {self.kelly_start_date}"
            }
            
        except Exception as e:
            self.logger.error(f"❌ Error in Kelly 'Best of Best' analysis: {str(e)}")
            return {
                'success': False,
                'error': f"Kelly 'Best of Best' analysis failed: {str(e)}",
                'data': {}
            }
    
    def _check_bet_result(self, recommendation, game_data):
        """Helper method to check if a betting recommendation won"""
        # Simplified bet result checking - would need more sophisticated logic
        # based on actual bet types and game outcomes
        try:
            actual_results = game_data.get('actual_results', {})
            bet_type = recommendation.get('bet_type', '').lower()
            
            # For now, return a placeholder - would need actual implementation
            # based on your specific bet tracking system
            return True  # Placeholder
            
        except Exception:
            return False
    
    def _calculate_bet_profit(self, recommendation, bet_amount):
        """Helper method to calculate profit from a winning bet"""
        try:
            # Simplified profit calculation - would need odds and bet type specifics
            # For now, assume standard -110 odds for most bets
            return bet_amount * 0.91  # Approximate profit for -110 odds
            
        except Exception:
            return 0

if __name__ == "__main__":
    # Test the redesigned analytics
    analytics = RedesignedBettingAnalytics()
    
    print("Testing Model Performance Analysis...")
    model_result = analytics.get_model_performance_analysis()
    print(f"Model Performance: {model_result['success']}")
    
    print("\nTesting Betting Recommendations Analysis...")
    betting_result = analytics.get_betting_recommendations_performance()
    print(f"Betting Recommendations: {betting_result['success']}")
    
    print("\nTesting Kelly Best of Best Analysis...")
    kelly_result = analytics.get_kelly_best_of_best_performance()
    print(f"Kelly Best of Best: {kelly_result['success']}")
