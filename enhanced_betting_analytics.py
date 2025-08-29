#!/usr/bin/env python3
"""
Enhanced Betting Analytics System
================================
Provides three distinct views:
1. System Performance Overview - Complete model accuracy across all predictions
2. Historical Performance - Kelly betting recommendations with actual bet tracking  
3. Today's Opportunities - Current Kelly recommendations for live betting

This separates predictive analytics from betting performance tracking.
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import os
import sys

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from comprehensive_historical_analysis import ComprehensiveHistoricalAnalyzer
from comprehensive_betting_performance_tracker import ComprehensiveBettingPerformanceTracker

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EnhancedBettingAnalytics:
    """Enhanced analytics system with separate views for model performance vs betting performance"""
    
    def __init__(self, data_dir: str = None):
        self.data_dir = Path(data_dir) if data_dir else Path(__file__).parent / "data"
        self.unified_cache = self.data_dir / "unified_predictions_cache.json"
        self.historical_analyzer = ComprehensiveHistoricalAnalyzer()
        self.betting_tracker = ComprehensiveBettingPerformanceTracker()
        
    def get_system_performance_overview(self, days_back: int = 14) -> Dict:
        """
        System Performance Overview - Complete model accuracy across ALL predictions
        Shows how well the model predicts outcomes regardless of betting confidence
        """
        logger.info("🔍 Generating System Performance Overview - Complete Model Accuracy")
        
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days_back)
        
        total_games = 0
        total_predictions = 0
        correct_predictions = 0
        
        # Performance by prediction type (ALL predictions, not just bets)
        prediction_types = {
            'moneyline': {'total': 0, 'correct': 0, 'accuracy': 0.0},
            'totals': {'total': 0, 'correct': 0, 'accuracy': 0.0},
            'run_line': {'total': 0, 'correct': 0, 'accuracy': 0.0}
        }
        
        # Performance by confidence level
        confidence_levels = {
            'high': {'threshold': 0.65, 'total': 0, 'correct': 0, 'accuracy': 0.0},
            'medium': {'threshold': 0.55, 'total': 0, 'correct': 0, 'accuracy': 0.0},
            'low': {'threshold': 0.45, 'total': 0, 'correct': 0, 'accuracy': 0.0}
        }
        
        # Daily performance tracking
        daily_performance = {}
        
        try:
            # Load cache data
            if not self.unified_cache.exists():
                logger.warning("No predictions cache found")
                return self._empty_system_overview()
                
            with open(self.unified_cache, 'r') as f:
                cache_data = json.load(f)
            
            current_date = start_date
            while current_date <= end_date:
                date_str = current_date.strftime('%Y-%m-%d')
                
                if date_str in cache_data:
                    date_data = cache_data[date_str]
                    daily_correct = 0
                    daily_total = 0
                    
                    # Process each game for this date
                    for game_key, game_data in date_data.items():
                        if game_key in ['metadata', 'generated_at']:
                            continue
                            
                        # Get actual score if available
                        actual_score = game_data.get('actual_score')
                        if not actual_score:
                            continue
                            
                        total_games += 1
                        predictions = game_data.get('predictions', {})
                        
                        # Evaluate moneyline prediction
                        if 'home_score' in predictions and 'away_score' in predictions:
                            predicted_winner = 'home' if predictions['home_score'] > predictions['away_score'] else 'away'
                            actual_winner = 'home' if actual_score['home'] > actual_score['away'] else 'away'
                            
                            prediction_types['moneyline']['total'] += 1
                            total_predictions += 1
                            daily_total += 1
                            
                            if predicted_winner == actual_winner:
                                prediction_types['moneyline']['correct'] += 1
                                correct_predictions += 1
                                daily_correct += 1
                            
                            # Check confidence levels
                            confidence = abs(predictions['home_score'] - predictions['away_score']) / (predictions['home_score'] + predictions['away_score'])
                            for level, data in confidence_levels.items():
                                if confidence >= data['threshold']:
                                    data['total'] += 1
                                    if predicted_winner == actual_winner:
                                        data['correct'] += 1
                                    break
                        
                        # Evaluate totals prediction
                        if 'total_runs' in predictions:
                            predicted_total = predictions['total_runs']
                            actual_total = actual_score['home'] + actual_score['away']
                            
                            prediction_types['totals']['total'] += 1
                            
                            # Consider within 0.5 runs as correct
                            if abs(predicted_total - actual_total) <= 0.5:
                                prediction_types['totals']['correct'] += 1
                    
                    # Record daily performance
                    if daily_total > 0:
                        daily_performance[date_str] = {
                            'total_predictions': daily_total,
                            'correct_predictions': daily_correct,
                            'accuracy': round(daily_correct / daily_total * 100, 1)
                        }
                
                current_date += timedelta(days=1)
            
            # Calculate accuracies
            for pred_type in prediction_types.values():
                if pred_type['total'] > 0:
                    pred_type['accuracy'] = round(pred_type['correct'] / pred_type['total'] * 100, 1)
            
            for conf_level in confidence_levels.values():
                if conf_level['total'] > 0:
                    conf_level['accuracy'] = round(conf_level['correct'] / conf_level['total'] * 100, 1)
            
            overall_accuracy = round(correct_predictions / total_predictions * 100, 1) if total_predictions > 0 else 0
            
            return {
                'overview': {
                    'period': f'{start_date} to {end_date}',
                    'total_games': total_games,
                    'total_predictions': total_predictions,
                    'correct_predictions': correct_predictions,
                    'overall_accuracy': overall_accuracy
                },
                'prediction_types': prediction_types,
                'confidence_levels': confidence_levels,
                'daily_performance': daily_performance,
                'summary': {
                    'best_prediction_type': max(prediction_types.keys(), key=lambda x: prediction_types[x]['accuracy']),
                    'avg_daily_accuracy': round(sum(day['accuracy'] for day in daily_performance.values()) / len(daily_performance), 1) if daily_performance else 0
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating system performance overview: {e}")
            return self._empty_system_overview()
    
    def get_historical_kelly_performance(self, days_back: int = 14) -> Dict:
        """
        Historical Performance - Kelly betting recommendations that were actually placed
        Shows actual betting performance and profitability
        """
        logger.info("💰 Generating Historical Kelly Performance - Actual Betting Results")
        
        try:
            # Use the historical analyzer to get actual betting performance
            analysis_result = self.historical_analyzer.get_cumulative_analysis()
            
            if not analysis_result:
                logger.warning("No historical betting data available")
                return self._empty_kelly_performance()
            
            # Extract betting performance data
            betting_performance = analysis_result.get('betting_performance', {})
            daily_breakdown = analysis_result.get('daily_breakdown', [])
            
            # Structure for Kelly performance view
            kelly_performance = {
                'summary': {
                    'period': analysis_result.get('analysis_period', f"Last {days_back} days"),
                    'total_betting_days': len(daily_breakdown),
                    'total_kelly_recommendations': betting_performance.get('total_recommendations', 0),
                    'successful_bets': betting_performance.get('correct_recommendations', 0),
                    'win_rate': round(betting_performance.get('overall_accuracy', 0), 1),
                    'total_roi': round(betting_performance.get('roi_percentage', 0), 2),
                    'net_profit': round(betting_performance.get('net_profit', 0), 2)
                },
                'confidence_breakdown': {
                    'high_confidence': {'count': 0, 'wins': 0, 'roi': 0.0},
                    'medium_confidence': {'count': 0, 'wins': 0, 'roi': 0.0},
                    'low_confidence': {'count': 0, 'wins': 0, 'roi': 0.0}
                },
                'bet_type_performance': {
                    'moneyline': {
                        'count': betting_performance.get('moneyline_stats', {}).get('total', 0),
                        'wins': betting_performance.get('moneyline_stats', {}).get('correct', 0),
                        'roi': round(betting_performance.get('moneyline_stats', {}).get('accuracy', 0), 1)
                    },
                    'totals': {
                        'count': betting_performance.get('total_stats', {}).get('total', 0),
                        'wins': betting_performance.get('total_stats', {}).get('correct', 0),
                        'roi': round(betting_performance.get('total_stats', {}).get('accuracy', 0), 1)
                    },
                    'run_line': {
                        'count': betting_performance.get('runline_stats', {}).get('total', 0),
                        'wins': betting_performance.get('runline_stats', {}).get('correct', 0),
                        'roi': round(betting_performance.get('runline_stats', {}).get('accuracy', 0), 1)
                    }
                },
                'daily_results': [],
                'top_performers': []
            }
            
            # Process daily results for Kelly-specific metrics
            for day_result in daily_breakdown:
                if not day_result.get('date'):
                    continue
                    
                # Extract betting performance data from the day result
                betting_data = day_result.get('betting_performance', {})
                
                betting_recs = betting_data.get('total_recommendations', 0)
                correct_recs = betting_data.get('correct_recommendations', 0)
                roi = betting_data.get('roi_percentage', 0)
                net_profit = betting_data.get('net_profit', 0)
                betting_accuracy = betting_data.get('overall_accuracy', 0)
                
                day_kelly = {
                    'date': day_result['date'],
                    'kelly_bets': betting_recs,
                    'successful_bets': correct_recs,
                    'roi': round(roi, 2),
                    'net_profit': round(net_profit, 2),
                    'win_rate': round(betting_accuracy, 1)
                }
                
                kelly_performance['daily_results'].append(day_kelly)
                
                # Track top performing days (days with >20% ROI)
                if day_kelly['roi'] > 20:
                    kelly_performance['top_performers'].append(day_kelly)
            
            # Sort top performers by ROI
            kelly_performance['top_performers'].sort(key=lambda x: x['roi'], reverse=True)
            kelly_performance['top_performers'] = kelly_performance['top_performers'][:5]  # Top 5
            
            return kelly_performance
            
        except Exception as e:
            logger.error(f"Error generating Kelly performance: {e}")
            return self._empty_kelly_performance()
    
    def get_todays_opportunities(self) -> Dict:
        """
        Today's Opportunities - Current Kelly recommendations for live betting
        Shows today's recommended bets with confidence levels and expected values
        """
        logger.info("🎯 Generating Today's Opportunities - Live Kelly Recommendations")
        
        today = datetime.now().strftime('%Y-%m-%d')
        
        try:
            # Load today's predictions
            if not self.unified_cache.exists():
                logger.warning("No predictions cache found")
                return self._empty_todays_opportunities()
            
            with open(self.unified_cache, 'r') as f:
                cache_data = json.load(f)
            
            if today not in cache_data:
                logger.warning(f"No predictions found for {today}")
                return self._empty_todays_opportunities()
            
            today_data = cache_data[today]
            opportunities = []
            
            for game_key, game_data in today_data.items():
                if game_key in ['metadata', 'generated_at']:
                    continue
                
                # Extract betting recommendations
                betting_recs = game_data.get('betting_recommendations', {})
                if not betting_recs:
                    continue
                
                # Process each betting recommendation
                for bet_type, bet_data in betting_recs.items():
                    if not isinstance(bet_data, dict):
                        continue
                    
                    # Calculate confidence and expected value
                    confidence = bet_data.get('confidence', 0)
                    expected_value = bet_data.get('expected_value', 0)
                    kelly_fraction = bet_data.get('kelly_fraction', 0)
                    
                    # Only include if it meets Kelly criteria
                    if kelly_fraction > 0.02:  # At least 2% Kelly recommendation
                        opportunity = {
                            'game': game_key.replace('_vs_', ' vs '),
                            'bet_type': bet_type,
                            'recommendation': bet_data.get('recommendation', ''),
                            'odds': bet_data.get('odds', 0),
                            'confidence': round(confidence * 100, 1),
                            'expected_value': round(expected_value, 3),
                            'kelly_fraction': round(kelly_fraction, 3),
                            'suggested_bet_size': round(kelly_fraction * 100, 1),  # As percentage of bankroll
                            'reasoning': bet_data.get('reasoning', ''),
                            'risk_level': self._categorize_risk(kelly_fraction)
                        }
                        
                        opportunities.append(opportunity)
            
            # Sort by Kelly fraction (highest first)
            opportunities.sort(key=lambda x: x['kelly_fraction'], reverse=True)
            
            # Categorize opportunities
            high_value = [opp for opp in opportunities if opp['kelly_fraction'] >= 0.1]
            medium_value = [opp for opp in opportunities if 0.05 <= opp['kelly_fraction'] < 0.1]
            low_value = [opp for opp in opportunities if 0.02 <= opp['kelly_fraction'] < 0.05]
            
            return {
                'date': today,
                'total_opportunities': len(opportunities),
                'summary': {
                    'high_value_bets': len(high_value),
                    'medium_value_bets': len(medium_value),
                    'low_value_bets': len(low_value),
                    'total_kelly_allocation': round(sum(opp['kelly_fraction'] for opp in opportunities), 3),
                    'avg_confidence': round(sum(opp['confidence'] for opp in opportunities) / len(opportunities), 1) if opportunities else 0
                },
                'opportunities': {
                    'high_value': high_value,
                    'medium_value': medium_value,
                    'low_value': low_value
                },
                'all_opportunities': opportunities
            }
            
        except Exception as e:
            logger.error(f"Error generating today's opportunities: {e}")
            return self._empty_todays_opportunities()
    
    def _categorize_risk(self, kelly_fraction: float) -> str:
        """Categorize risk level based on Kelly fraction"""
        if kelly_fraction >= 0.1:
            return "High Value"
        elif kelly_fraction >= 0.05:
            return "Medium Value"
        else:
            return "Low Value"
    
    def _empty_system_overview(self) -> Dict:
        """Return empty system overview structure"""
        return {
            'overview': {'total_games': 0, 'total_predictions': 0, 'correct_predictions': 0, 'overall_accuracy': 0},
            'prediction_types': {'moneyline': {'total': 0, 'correct': 0, 'accuracy': 0}, 'totals': {'total': 0, 'correct': 0, 'accuracy': 0}},
            'confidence_levels': {'high': {'total': 0, 'correct': 0, 'accuracy': 0}, 'medium': {'total': 0, 'correct': 0, 'accuracy': 0}},
            'daily_performance': {},
            'summary': {'best_prediction_type': 'moneyline', 'avg_daily_accuracy': 0}
        }
    
    def _empty_kelly_performance(self) -> Dict:
        """Return empty Kelly performance structure"""
        return {
            'summary': {'total_kelly_recommendations': 0, 'successful_bets': 0, 'win_rate': 0, 'total_roi': 0, 'net_profit': 0},
            'confidence_breakdown': {'high_confidence': {'count': 0, 'wins': 0, 'roi': 0}, 'medium_confidence': {'count': 0, 'wins': 0, 'roi': 0}},
            'bet_type_performance': {'moneyline': {'count': 0, 'wins': 0, 'roi': 0}, 'totals': {'count': 0, 'wins': 0, 'roi': 0}},
            'daily_results': [],
            'top_performers': []
        }
    
    def _empty_todays_opportunities(self) -> Dict:
        """Return empty today's opportunities structure"""
        return {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'total_opportunities': 0,
            'summary': {'high_value_bets': 0, 'medium_value_bets': 0, 'low_value_bets': 0, 'total_kelly_allocation': 0, 'avg_confidence': 0},
            'opportunities': {'high_value': [], 'medium_value': [], 'low_value': []},
            'all_opportunities': []
        }

def main():
    """Test the enhanced analytics system"""
    logger.info("🔄 TESTING ENHANCED BETTING ANALYTICS SYSTEM")
    logger.info("=" * 60)
    
    analytics = EnhancedBettingAnalytics()
    
    # Test system performance overview
    logger.info("\n1. SYSTEM PERFORMANCE OVERVIEW - Model Accuracy")
    logger.info("-" * 50)
    system_overview = analytics.get_system_performance_overview(days_back=14)
    logger.info(f"Overall Model Accuracy: {system_overview['overview']['overall_accuracy']}%")
    logger.info(f"Total Predictions Made: {system_overview['overview']['total_predictions']}")
    logger.info(f"Moneyline Accuracy: {system_overview['prediction_types']['moneyline']['accuracy']}%")
    
    # Test Kelly performance
    logger.info("\n2. HISTORICAL KELLY PERFORMANCE - Actual Betting Results")
    logger.info("-" * 50)
    kelly_performance = analytics.get_historical_kelly_performance(days_back=14)
    logger.info(f"Kelly Recommendations: {kelly_performance['summary']['total_kelly_recommendations']}")
    logger.info(f"Win Rate: {kelly_performance['summary']['win_rate']}%")
    logger.info(f"Total ROI: {kelly_performance['summary']['total_roi']}%")
    
    # Test today's opportunities
    logger.info("\n3. TODAY'S OPPORTUNITIES - Live Kelly Recommendations")
    logger.info("-" * 50)
    todays_opportunities = analytics.get_todays_opportunities()
    logger.info(f"Total Opportunities: {todays_opportunities['total_opportunities']}")
    logger.info(f"High Value Bets: {todays_opportunities['summary']['high_value_bets']}")
    logger.info(f"Total Kelly Allocation: {todays_opportunities['summary']['total_kelly_allocation']}")
    
    logger.info("\n✅ Enhanced analytics system test complete!")
    return True

if __name__ == "__main__":
    main()
