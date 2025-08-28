#!/usr/bin/env python3
"""
Advanced Betting Guidance System with Kelly Criterion
Provides clear betting recommendations based on historical performance and today's opportunities
"""

import os
import sys
import json
import logging
import math
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from comprehensive_historical_analysis import ComprehensiveHistoricalAnalyzer

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BettingGuidanceSystem:
    """
    Advanced betting guidance system with Kelly Criterion calculations
    """
    
    def __init__(self, base_unit: float = 100.0):
        """
        Initialize betting guidance system
        
        Args:
            base_unit: Base betting unit in dollars (default $100)
        """
        self.base_unit = base_unit
        self.historical_analyzer = ComprehensiveHistoricalAnalyzer()
        logger.info(f"✅ Betting Guidance System initialized with ${base_unit} base unit")
    
    def calculate_kelly_criterion(self, win_probability: float, odds_american: int) -> float:
        """
        Calculate Kelly Criterion betting percentage
        
        Args:
            win_probability: Probability of winning (0.0 to 1.0)
            odds_american: American odds format (-110, +150, etc.)
        
        Returns:
            Kelly percentage (0.0 to 1.0), 0 if no edge
        """
        try:
            # Convert American odds to decimal odds
            if odds_american > 0:
                decimal_odds = (odds_american / 100) + 1
            else:
                decimal_odds = (100 / abs(odds_american)) + 1
            
            # Kelly formula: f = (bp - q) / b
            # where f = fraction of bankroll to bet
            # b = odds received (decimal odds - 1)
            # p = probability of winning
            # q = probability of losing (1 - p)
            
            b = decimal_odds - 1  # Net odds
            p = win_probability
            q = 1 - p
            
            kelly_fraction = (b * p - q) / b
            
            # Only bet if we have positive expected value
            return max(0, min(kelly_fraction, 0.25))  # Cap at 25% for risk management
            
        except Exception as e:
            logger.error(f"Error calculating Kelly criterion: {e}")
            return 0.0
    
    def get_historical_performance_by_bet_type(self) -> Dict:
        """
        Get detailed historical performance breakdown by bet type
        """
        try:
            cumulative_data = self.historical_analyzer.get_cumulative_analysis()
            betting_analysis = cumulative_data.get('betting_analysis', {})
            
            # Extract performance by bet type
            bet_type_performance = betting_analysis.get('bet_type_performance', {})
            
            # Calculate ROI and accuracy for each bet type
            performance_summary = {}
            
            for bet_type, stats in bet_type_performance.items():
                total_bets = stats.get('total', 0)
                correct_bets = stats.get('correct', 0)
                total_invested = total_bets * self.base_unit  # Assuming $100 per bet
                
                # Calculate winnings based on actual odds (this needs real odds data)
                # For now, use simplified calculation
                if bet_type.lower() in ['moneyline', 'ml']:
                    avg_odds = -110  # Typical moneyline odds
                elif bet_type.lower() in ['total', 'over', 'under', 'ou']:
                    avg_odds = -110  # Typical total odds
                elif bet_type.lower() in ['run_line', 'runline', 'rl']:
                    avg_odds = -110  # Typical run line odds
                else:
                    avg_odds = -110  # Default
                
                # Calculate payout for winning bets
                if avg_odds > 0:
                    payout_per_win = self.base_unit + (self.base_unit * avg_odds / 100)
                else:
                    payout_per_win = self.base_unit + (self.base_unit * 100 / abs(avg_odds))
                
                total_winnings = correct_bets * payout_per_win
                net_profit = total_winnings - total_invested
                roi = (net_profit / total_invested * 100) if total_invested > 0 else 0
                accuracy = (correct_bets / total_bets * 100) if total_bets > 0 else 0
                
                performance_summary[bet_type] = {
                    'total_bets': total_bets,
                    'correct_bets': correct_bets,
                    'accuracy': round(accuracy, 1),
                    'total_invested': total_invested,
                    'total_winnings': round(total_winnings, 2),
                    'net_profit': round(net_profit, 2),
                    'roi': round(roi, 1),
                    'recommendation': self._get_bet_type_recommendation(accuracy, roi, total_bets)
                }
            
            return performance_summary
            
        except Exception as e:
            logger.error(f"Error getting historical performance: {e}")
            return {}
    
    def _get_bet_type_recommendation(self, accuracy: float, roi: float, sample_size: int) -> str:
        """
        Get recommendation for bet type based on historical performance
        """
        if sample_size < 10:
            return "INSUFFICIENT_DATA"
        elif accuracy >= 55 and roi >= 5:
            return "HIGHLY_RECOMMENDED"
        elif accuracy >= 52 and roi >= 0:
            return "RECOMMENDED"
        elif accuracy >= 50 and roi >= -5:
            return "CAUTIOUS"
        else:
            return "AVOID"
    
    def get_todays_betting_opportunities(self) -> Dict:
        """
        Get today's betting opportunities with Kelly Criterion calculations
        """
        try:
            # Load today's betting recommendations from the unified engine
            today_date = datetime.now().strftime('%Y_%m_%d')
            betting_recs_file = f"data/betting_recommendations_{today_date}.json"
            
            if not os.path.exists(betting_recs_file):
                return {
                    'success': False,
                    'message': f'No betting recommendations file found for today ({today_date})',
                    'opportunities': []
                }
            
            with open(betting_recs_file, 'r') as f:
                betting_data = json.load(f)
                betting_recs = betting_data.get('games', {})
            
            logger.info(f"📊 Loaded {len(betting_recs)} games with betting recommendations")
            
            opportunities = []
            total_kelly_investment = 0
            
            for game_key, recommendations in betting_recs.items():
                if not isinstance(recommendations, dict):
                    continue
                
                game_opportunities = {
                    'game': game_key,
                    'bets': [],
                    'total_kelly_amount': 0
                }
                
                # Process each bet type for this game
                for bet_type, bet_data in recommendations.items():
                    if not isinstance(bet_data, dict) or bet_data.get('recommendation') in ['PASS', None]:
                        continue
                    
                    # Extract bet details
                    confidence = bet_data.get('confidence', 'MEDIUM')
                    expected_value = bet_data.get('expected_value', 0)
                    odds = bet_data.get('odds', -110)
                    pick = bet_data.get('pick', bet_data.get('recommendation', ''))
                    
                    # Convert confidence to win probability
                    if confidence == 'HIGH':
                        win_prob = 0.60  # 60% confidence for high
                    elif confidence == 'MEDIUM':
                        win_prob = 0.55  # 55% confidence for medium
                    else:
                        win_prob = 0.52  # 52% confidence for low
                    
                    # Adjust win probability based on expected value
                    if expected_value > 0.1:
                        win_prob += 0.05
                    elif expected_value > 0.05:
                        win_prob += 0.02
                    
                    # Calculate Kelly Criterion
                    kelly_fraction = self.calculate_kelly_criterion(win_prob, odds)
                    kelly_amount = kelly_fraction * 1000  # Assuming $1000 bankroll
                    
                    # Adjust bet size based on unit system
                    if kelly_amount > 0:
                        # Round to nearest $10 for practical betting
                        suggested_bet = max(10, round(kelly_amount / 10) * 10)
                        suggested_bet = min(suggested_bet, self.base_unit * 2)  # Cap at 2x base unit
                    else:
                        suggested_bet = 0
                    
                    if suggested_bet > 0:
                        bet_opportunity = {
                            'bet_type': bet_type.replace('_', ' ').title(),
                            'pick': pick,
                            'odds': odds,
                            'confidence': confidence,
                            'win_probability': round(win_prob * 100, 1),
                            'expected_value': round(expected_value, 3),
                            'kelly_fraction': round(kelly_fraction * 100, 1),
                            'suggested_bet': suggested_bet,
                            'potential_profit': self._calculate_profit(suggested_bet, odds),
                            'risk_rating': self._get_risk_rating(kelly_fraction, confidence)
                        }
                        
                        game_opportunities['bets'].append(bet_opportunity)
                        game_opportunities['total_kelly_amount'] += suggested_bet
                
                if game_opportunities['bets']:
                    opportunities.append(game_opportunities)
                    total_kelly_investment += game_opportunities['total_kelly_amount']
            
            return {
                'success': True,
                'date': datetime.now().strftime('%Y-%m-%d'),
                'total_opportunities': len(opportunities),
                'total_recommended_investment': total_kelly_investment,
                'opportunities': opportunities,
                'bankroll_recommendation': {
                    'minimum_bankroll': total_kelly_investment * 5,  # 5x recommended for safety
                    'conservative_bankroll': total_kelly_investment * 10,
                    'notes': 'Kelly Criterion assumes these are your only bets. Adjust for your full portfolio.'
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting today's opportunities: {e}")
            return {
                'success': False,
                'error': str(e),
                'opportunities': []
            }
    
    def _calculate_profit(self, bet_amount: float, odds: int) -> float:
        """Calculate potential profit from bet"""
        if odds > 0:
            return bet_amount * (odds / 100)
        else:
            return bet_amount * (100 / abs(odds))
    
    def _get_risk_rating(self, kelly_fraction: float, confidence: str) -> str:
        """Get risk rating for bet"""
        if kelly_fraction > 0.15:
            return "HIGH_REWARD"
        elif kelly_fraction > 0.08:
            return "MODERATE"
        elif kelly_fraction > 0.03:
            return "LOW_RISK"
        else:
            return "MINIMAL"
    
    def generate_betting_report(self) -> Dict:
        """
        Generate comprehensive betting guidance report
        """
        try:
            # Get historical performance
            historical_performance = self.get_historical_performance_by_bet_type()
            
            # Get today's opportunities
            todays_opportunities = self.get_todays_betting_opportunities()
            
            # Get cumulative stats
            cumulative_data = self.historical_analyzer.get_cumulative_analysis()
            betting_stats = cumulative_data.get('betting_analysis', {})
            
            # Calculate overall system performance
            total_bets = betting_stats.get('total_recommendations', 0)
            winning_bets = betting_stats.get('correct_recommendations', 0)
            overall_accuracy = (winning_bets / total_bets * 100) if total_bets > 0 else 0
            overall_roi = betting_stats.get('roi_percentage', 0)
            
            # Generate recommendations
            system_recommendation = self._get_system_recommendation(overall_accuracy, overall_roi, total_bets)
            
            report = {
                'report_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'system_overview': {
                    'total_bets_analyzed': total_bets,
                    'overall_accuracy': round(overall_accuracy, 1),
                    'overall_roi': round(overall_roi, 1),
                    'system_recommendation': system_recommendation,
                    'analysis_period': f"Since 8/15 ({cumulative_data.get('total_dates_analyzed', 0)} days)"
                },
                'historical_performance': historical_performance,
                'todays_opportunities': todays_opportunities,
                'betting_guidelines': {
                    'base_unit': self.base_unit,
                    'kelly_criterion': 'Used for optimal bet sizing',
                    'risk_management': 'Maximum 25% of bankroll on any single bet',
                    'recommended_bankroll': '$1000+ for Kelly sizing',
                    'confidence_levels': {
                        'HIGH': 'Win probability 60%+',
                        'MEDIUM': 'Win probability 55%+',
                        'LOW': 'Win probability 52%+'
                    }
                }
            }
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating betting report: {e}")
            return {
                'error': str(e),
                'report_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
    
    def _get_system_recommendation(self, accuracy: float, roi: float, sample_size: int) -> str:
        """Get overall system recommendation"""
        if sample_size < 50:
            return "INSUFFICIENT_DATA - Need more historical data"
        elif accuracy >= 55 and roi >= 10:
            return "EXCELLENT - System performing very well"
        elif accuracy >= 52 and roi >= 5:
            return "GOOD - System showing positive returns"
        elif accuracy >= 50 and roi >= 0:
            return "MARGINAL - Proceed with caution"
        else:
            return "POOR - Consider system adjustments"

def main():
    """Test the betting guidance system"""
    guidance_system = BettingGuidanceSystem(base_unit=100.0)
    
    print("🎯 Generating Betting Guidance Report...")
    report = guidance_system.generate_betting_report()
    
    print(f"\n📊 SYSTEM OVERVIEW:")
    overview = report.get('system_overview', {})
    print(f"Total Bets Analyzed: {overview.get('total_bets_analyzed', 0)}")
    print(f"Overall Accuracy: {overview.get('overall_accuracy', 0)}%")
    print(f"Overall ROI: {overview.get('overall_roi', 0)}%")
    print(f"System Recommendation: {overview.get('system_recommendation', 'Unknown')}")
    
    print(f"\n💰 TODAY'S OPPORTUNITIES:")
    opportunities = report.get('todays_opportunities', {})
    if opportunities.get('success'):
        print(f"Total Opportunities: {opportunities.get('total_opportunities', 0)}")
        print(f"Recommended Investment: ${opportunities.get('total_recommended_investment', 0)}")
        
        for game_opp in opportunities.get('opportunities', []):
            print(f"\n🏟️ {game_opp['game']}:")
            for bet in game_opp['bets']:
                print(f"  • {bet['bet_type']}: {bet['pick']} ({bet['odds']}) - ${bet['suggested_bet']} ({bet['confidence']})")
    else:
        print("No opportunities available today")
    
    print(f"\n📈 HISTORICAL PERFORMANCE BY BET TYPE:")
    for bet_type, performance in report.get('historical_performance', {}).items():
        print(f"{bet_type}: {performance['accuracy']}% accuracy, {performance['roi']}% ROI - {performance['recommendation']}")

if __name__ == "__main__":
    main()
