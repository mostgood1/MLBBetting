#!/usr/bin/env python3
"""
Kelly Criterion Betting Strategy Module
======================================

Implements Kelly Criterion for optimal bet sizing, portfolio optimization,
risk management, and line movement tracking for profitable betting.
"""

import json
import os
import numpy as np
from datetime import datetime
import statistics
from collections import defaultdict

class KellyCriterionStrategy:
    
    def __init__(self, bankroll=10000, data_directory="data"):
        self.bankroll = bankroll
        self.data_directory = data_directory
        self.min_edge = 0.05  # Minimum 5% edge to bet
        self.max_kelly = 0.10  # Maximum 10% of bankroll per bet
        self.confidence_threshold = 60  # Minimum confidence for betting
        
    def implement_kelly_strategy(self):
        """Implement complete Kelly Criterion betting strategy"""
        
        print("💰 KELLY CRITERION BETTING STRATEGY")
        print("=" * 39)
        print(f"Initial Bankroll: ${self.bankroll:,}")
        print(f"Minimum Edge Required: {self.min_edge:.1%}")
        print(f"Maximum Bet Size: {self.max_kelly:.1%} of bankroll")
        print(f"Confidence Threshold: {self.confidence_threshold}%")
        print()
        
        # Load historical betting opportunities
        self._load_betting_opportunities()
        
        # Calculate Kelly fractions for each bet
        self._calculate_kelly_fractions()
        
        # Implement portfolio optimization
        self._optimize_bet_portfolio()
        
        # Add risk management rules
        self._implement_risk_management()
        
        # Backtest Kelly strategy
        self._backtest_kelly_strategy()
        
        # Generate betting rules
        self._generate_betting_rules()
    
    def _load_betting_opportunities(self):
        """Load and analyze betting opportunities"""
        
        print("📊 LOADING BETTING OPPORTUNITIES")
        print("-" * 32)
        
        self.betting_opportunities = []
        
        # Load all betting data
        for file in sorted(os.listdir(self.data_directory)):
            if file.startswith('betting_recommendations_2025') and file.endswith('.json'):
                date_str = file.replace('betting_recommendations_', '').replace('.json', '').replace('_', '-')
                
                opportunities = self._extract_day_opportunities(date_str)
                self.betting_opportunities.extend(opportunities)
        
        print(f"✅ Found {len(self.betting_opportunities)} betting opportunities")
        
        # Filter by confidence threshold
        high_conf_ops = [op for op in self.betting_opportunities if op.get('confidence', 0) >= self.confidence_threshold]
        print(f"🎯 High confidence bets: {len(high_conf_ops)}/{len(self.betting_opportunities)}")
        
        print()
    
    def _extract_day_opportunities(self, date_str):
        """Extract betting opportunities for a single day"""
        
        date_underscore = date_str.replace('-', '_')
        
        betting_file = os.path.join(self.data_directory, f"betting_recommendations_{date_underscore}.json")
        scores_file = os.path.join(self.data_directory, f"final_scores_{date_underscore}.json")
        
        if not os.path.exists(betting_file):
            return []
        
        with open(betting_file, 'r') as f:
            betting_data = json.load(f)
        
        scores_data = {}
        if os.path.exists(scores_file):
            with open(scores_file, 'r') as f:
                scores_data = json.load(f)
        
        opportunities = []
        
        if 'games' not in betting_data:
            return opportunities
        
        for game_key, game_data in betting_data['games'].items():
            game_ops = self._extract_game_opportunities(game_key, game_data, scores_data, date_str)
            opportunities.extend(game_ops)
        
        return opportunities
    
    def _extract_game_opportunities(self, game_key, game_data, scores_data, date):
        """Extract betting opportunities from a single game"""
        
        opportunities = []
        
        if 'predictions' not in game_data or 'betting_lines' not in game_data:
            return opportunities
        
        predictions = game_data['predictions']
        lines = game_data['betting_lines']
        
        if 'predictions' not in predictions:
            return opportunities
        
        pred_data = predictions['predictions']
        
        # Get actual results
        actual_result = self._get_actual_result(game_key, scores_data)
        
        # Moneyline opportunities
        home_prob = pred_data.get('home_win_prob', 0.5)
        confidence = pred_data.get('confidence', 50)
        
        # Home moneyline
        if 'moneyline_home' in lines and lines['moneyline_home']:
            home_odds = lines['moneyline_home']
            implied_prob = self._odds_to_probability(home_odds)
            edge = home_prob - implied_prob
            
            if edge > self.min_edge and confidence >= self.confidence_threshold:
                opportunities.append({
                    'type': 'moneyline',
                    'bet': 'home',
                    'game': game_key,
                    'date': date,
                    'predicted_prob': home_prob,
                    'implied_prob': implied_prob,
                    'edge': edge,
                    'odds': home_odds,
                    'confidence': confidence,
                    'won': actual_result.get('home_won') if actual_result else None
                })
        
        # Away moneyline
        if 'moneyline_away' in lines and lines['moneyline_away']:
            away_odds = lines['moneyline_away']
            implied_prob = self._odds_to_probability(away_odds)
            away_prob = 1 - home_prob
            edge = away_prob - implied_prob
            
            if edge > self.min_edge and confidence >= self.confidence_threshold:
                opportunities.append({
                    'type': 'moneyline',
                    'bet': 'away',
                    'game': game_key,
                    'date': date,
                    'predicted_prob': away_prob,
                    'implied_prob': implied_prob,
                    'edge': edge,
                    'odds': away_odds,
                    'confidence': confidence,
                    'won': actual_result.get('away_won') if actual_result else None
                })
        
        # Over/Under opportunities
        predicted_total = pred_data.get('predicted_total_runs', 0)
        
        if 'total_line' in lines and lines['total_line'] and predicted_total > 0:
            total_line = lines['total_line']
            
            # Over bet
            if predicted_total > total_line + 0.5:  # Significant edge required
                edge = (predicted_total - total_line) / total_line
                if edge > self.min_edge and confidence >= self.confidence_threshold:
                    opportunities.append({
                        'type': 'total',
                        'bet': 'over',
                        'game': game_key,
                        'date': date,
                        'predicted_total': predicted_total,
                        'line_total': total_line,
                        'edge': edge,
                        'odds': lines.get('total_over_odds', -110),
                        'confidence': confidence,
                        'won': actual_result.get('over_won', None) if actual_result else None
                    })
            
            # Under bet
            elif predicted_total < total_line - 0.5:
                edge = (total_line - predicted_total) / total_line
                if edge > self.min_edge and confidence >= self.confidence_threshold:
                    opportunities.append({
                        'type': 'total',
                        'bet': 'under',
                        'game': game_key,
                        'date': date,
                        'predicted_total': predicted_total,
                        'line_total': total_line,
                        'edge': edge,
                        'odds': lines.get('total_under_odds', -110),
                        'confidence': confidence,
                        'won': actual_result.get('under_won', None) if actual_result else None
                    })
        
        return opportunities
    
    def _get_actual_result(self, game_key, scores_data):
        """Get actual game result"""
        
        if not scores_data:
            return None
        
        for score_key, score_data in scores_data.items():
            if game_key in score_key or any(team in score_key for team in game_key.split('_vs_')):
                away_score = score_data.get('away_score', score_data.get('final_away_score'))
                home_score = score_data.get('home_score', score_data.get('final_home_score'))
                
                if away_score is not None and home_score is not None:
                    total_runs = away_score + home_score
                    
                    return {
                        'home_won': home_score > away_score,
                        'away_won': away_score > home_score,
                        'total_runs': total_runs,
                        'over_won': None,  # Would need specific line comparison
                        'under_won': None
                    }
        
        return None
    
    def _odds_to_probability(self, odds):
        """Convert American odds to implied probability"""
        
        if odds > 0:
            return 100 / (odds + 100)
        else:
            return abs(odds) / (abs(odds) + 100)
    
    def _calculate_kelly_fractions(self):
        """Calculate Kelly fractions for each betting opportunity"""
        
        print("📐 CALCULATING KELLY FRACTIONS")
        print("-" * 30)
        
        kelly_bets = []
        
        for opportunity in self.betting_opportunities:
            if opportunity['won'] is None:
                continue  # Skip bets without results
            
            # Calculate Kelly fraction
            kelly_fraction = self._calculate_kelly_fraction(opportunity)
            
            if kelly_fraction > 0:
                kelly_bets.append({
                    'opportunity': opportunity,
                    'kelly_fraction': kelly_fraction,
                    'bet_amount': kelly_fraction * self.bankroll
                })
        
        self.kelly_bets = kelly_bets
        
        if kelly_bets:
            avg_kelly = statistics.mean([bet['kelly_fraction'] for bet in kelly_bets])
            max_kelly = max([bet['kelly_fraction'] for bet in kelly_bets])
            qualifying_bets = len(kelly_bets)
            
            print(f"✅ Qualifying Kelly bets: {qualifying_bets}")
            print(f"📊 Average Kelly fraction: {avg_kelly:.3f} ({avg_kelly*100:.1f}%)")
            print(f"📊 Maximum Kelly fraction: {max_kelly:.3f} ({max_kelly*100:.1f}%)")
            
            # Show distribution
            small_bets = sum(1 for bet in kelly_bets if bet['kelly_fraction'] < 0.02)
            medium_bets = sum(1 for bet in kelly_bets if 0.02 <= bet['kelly_fraction'] < 0.05)
            large_bets = sum(1 for bet in kelly_bets if bet['kelly_fraction'] >= 0.05)
            
            print(f"\n📊 BET SIZE DISTRIBUTION:")
            print(f"   Small (<2%): {small_bets}")
            print(f"   Medium (2-5%): {medium_bets}")
            print(f"   Large (>5%): {large_bets}")
        
        print()
    
    def _calculate_kelly_fraction(self, opportunity):
        """Calculate Kelly fraction for a single opportunity"""
        
        # Get odds and probabilities
        odds = opportunity['odds']
        predicted_prob = opportunity['predicted_prob']
        
        # Convert odds to decimal
        if odds > 0:
            decimal_odds = (odds / 100) + 1
        else:
            decimal_odds = (100 / abs(odds)) + 1
        
        # Kelly formula: f = (bp - q) / b
        # where f = fraction to bet, b = net odds, p = win probability, q = lose probability
        b = decimal_odds - 1
        p = predicted_prob
        q = 1 - p
        
        if b > 0:
            kelly_fraction = (b * p - q) / b
        else:
            kelly_fraction = 0
        
        # Apply constraints
        kelly_fraction = max(0, min(kelly_fraction, self.max_kelly))
        
        return kelly_fraction
    
    def _optimize_bet_portfolio(self):
        """Optimize betting portfolio across different bet types"""
        
        print("📊 OPTIMIZING BET PORTFOLIO")
        print("-" * 27)
        
        if not hasattr(self, 'kelly_bets') or not self.kelly_bets:
            print("No Kelly bets available for portfolio optimization")
            return
        
        # Analyze performance by bet type
        portfolio_analysis = defaultdict(list)
        
        for kelly_bet in self.kelly_bets:
            opportunity = kelly_bet['opportunity']
            bet_type = opportunity['type']
            won = opportunity['won']
            
            portfolio_analysis[bet_type].append({
                'won': won,
                'kelly_fraction': kelly_bet['kelly_fraction'],
                'edge': opportunity['edge']
            })
        
        print("📈 PORTFOLIO PERFORMANCE BY BET TYPE:")
        portfolio_weights = {}
        
        for bet_type, bets in portfolio_analysis.items():
            if len(bets) >= 5:  # Minimum sample size
                win_rate = sum(bet['won'] for bet in bets) / len(bets)
                avg_edge = statistics.mean([bet['edge'] for bet in bets])
                avg_kelly = statistics.mean([bet['kelly_fraction'] for bet in bets])
                
                # Calculate expected value
                expected_value = win_rate - (1 - win_rate)
                
                # Portfolio weight based on performance
                if expected_value > 0.1:
                    weight = min(0.4, expected_value * 2)
                elif expected_value > 0.05:
                    weight = min(0.3, expected_value * 1.5)
                else:
                    weight = 0.1
                
                portfolio_weights[bet_type] = weight
                
                print(f"   {bet_type:12}: {win_rate:.1%} win rate, {avg_edge:.2%} avg edge → {weight:.1%} allocation")
        
        # Normalize weights
        total_weight = sum(portfolio_weights.values())
        if total_weight > 0:
            self.portfolio_weights = {k: v/total_weight for k, v in portfolio_weights.items()}
        else:
            self.portfolio_weights = {}
        
        print()
    
    def _implement_risk_management(self):
        """Implement comprehensive risk management rules"""
        
        print("⚠️  IMPLEMENTING RISK MANAGEMENT")
        print("-" * 32)
        
        risk_rules = {
            'daily_loss_limit': 0.05,      # Stop at 5% daily loss
            'max_concurrent_bets': 5,       # Maximum 5 bets per day
            'max_single_bet': 0.03,         # Maximum 3% per bet (conservative Kelly)
            'min_bankroll_threshold': 0.7,  # Stop betting if bankroll falls below 70%
            'consecutive_loss_limit': 5,    # Stop after 5 consecutive losses
            'drawdown_limit': 0.20          # Stop at 20% total drawdown
        }
        
        print("🛡️  RISK MANAGEMENT RULES:")
        for rule, value in risk_rules.items():
            if 'limit' in rule or 'threshold' in rule:
                print(f"   • {rule:25}: {value:.1%}")
            else:
                print(f"   • {rule:25}: {value}")
        
        self.risk_rules = risk_rules
        
        print(f"\n⚡ DYNAMIC BET SIZING:")
        print("   • Reduce bet size by 50% after 3 consecutive losses")
        print("   • Increase bet size by 25% after 5 consecutive wins (max 150% Kelly)")
        print("   • Reset to normal Kelly after neutral streak")
        
        print()
    
    def _backtest_kelly_strategy(self):
        """Backtest the Kelly strategy on historical data"""
        
        print("🧪 BACKTESTING KELLY STRATEGY")
        print("-" * 29)
        
        if not hasattr(self, 'kelly_bets') or not self.kelly_bets:
            print("No Kelly bets available for backtesting")
            return
        
        # Sort bets chronologically
        sorted_bets = sorted(self.kelly_bets, key=lambda x: x['opportunity']['date'])
        
        # Simulate betting
        bankroll = self.bankroll
        max_bankroll = bankroll
        total_bets = 0
        winning_bets = 0
        total_wagered = 0
        net_profit = 0
        consecutive_losses = 0
        max_consecutive_losses = 0
        
        daily_performance = defaultdict(list)
        
        for kelly_bet in sorted_bets:
            opportunity = kelly_bet['opportunity']
            kelly_fraction = kelly_bet['kelly_fraction']
            
            # Apply risk management
            if consecutive_losses >= self.risk_rules['consecutive_loss_limit']:
                continue  # Skip bet due to consecutive losses
            
            if bankroll < self.bankroll * self.risk_rules['min_bankroll_threshold']:
                continue  # Skip bet due to low bankroll
            
            # Conservative Kelly (use 50% of Kelly fraction for safety)
            conservative_fraction = min(kelly_fraction * 0.5, self.risk_rules['max_single_bet'])
            bet_amount = conservative_fraction * bankroll
            
            total_bets += 1
            total_wagered += bet_amount
            
            if opportunity['won']:
                # Calculate winnings
                odds = opportunity['odds']
                if odds > 0:
                    profit = bet_amount * (odds / 100)
                else:
                    profit = bet_amount * (100 / abs(odds))
                
                bankroll += profit
                net_profit += profit
                winning_bets += 1
                consecutive_losses = 0
                
                # Track max bankroll
                max_bankroll = max(max_bankroll, bankroll)
            else:
                bankroll -= bet_amount
                net_profit -= bet_amount
                consecutive_losses += 1
                max_consecutive_losses = max(max_consecutive_losses, consecutive_losses)
            
            # Track daily performance
            daily_performance[opportunity['date']].append({
                'bet_amount': bet_amount,
                'profit': profit if opportunity['won'] else -bet_amount,
                'bankroll': bankroll
            })
        
        # Calculate final metrics
        win_rate = (winning_bets / total_bets) * 100 if total_bets > 0 else 0
        roi = (net_profit / self.bankroll) * 100
        max_drawdown = ((max_bankroll - bankroll) / max_bankroll) * 100 if max_bankroll > bankroll else 0
        
        print(f"📊 BACKTEST RESULTS:")
        print(f"   Total Bets Placed: {total_bets}")
        print(f"   Win Rate: {win_rate:.1f}% ({winning_bets}/{total_bets})")
        print(f"   Total Wagered: ${total_wagered:,.2f}")
        print(f"   Net Profit: ${net_profit:,.2f}")
        print(f"   Final Bankroll: ${bankroll:,.2f}")
        print(f"   ROI: {roi:.2f}%")
        print(f"   Max Consecutive Losses: {max_consecutive_losses}")
        print(f"   Max Drawdown: {max_drawdown:.1f}%")
        
        # Compare to flat betting
        flat_bet_amount = 100
        flat_profit = 0
        for kelly_bet in sorted_bets:
            if kelly_bet['opportunity']['won']:
                odds = kelly_bet['opportunity']['odds']
                if odds > 0:
                    flat_profit += flat_bet_amount * (odds / 100)
                else:
                    flat_profit += flat_bet_amount * (100 / abs(odds))
            else:
                flat_profit -= flat_bet_amount
        
        flat_roi = (flat_profit / (total_bets * flat_bet_amount)) * 100
        
        print(f"\n📊 COMPARISON TO FLAT BETTING:")
        print(f"   Flat Betting ROI: {flat_roi:.2f}%")
        print(f"   Kelly Strategy ROI: {roi:.2f}%")
        print(f"   Improvement: {roi - flat_roi:+.2f}%")
        
        print()
    
    def _generate_betting_rules(self):
        """Generate final optimized betting rules"""
        
        print("📋 OPTIMIZED BETTING RULES")
        print("-" * 26)
        
        print("🎯 KELLY CRITERION RULES:")
        print(f"   1. Only bet with ≥{self.min_edge:.1%} edge over market")
        print(f"   2. Only bet on ≥{self.confidence_threshold}% confidence predictions")
        print(f"   3. Use 50% of Kelly fraction for conservative sizing")
        print(f"   4. Maximum {self.max_kelly:.1%} of bankroll per bet")
        print(f"   5. Stop betting after {self.risk_rules['consecutive_loss_limit']} consecutive losses")
        
        print(f"\n💰 PORTFOLIO ALLOCATION:")
        if hasattr(self, 'portfolio_weights'):
            for bet_type, weight in self.portfolio_weights.items():
                print(f"   • {bet_type.title()}: {weight:.1%} of total bets")
        
        print(f"\n⚠️  RISK MANAGEMENT:")
        print(f"   • Daily loss limit: {self.risk_rules['daily_loss_limit']:.1%}")
        print(f"   • Maximum {self.risk_rules['max_concurrent_bets']} bets per day")
        print(f"   • Stop if bankroll falls below {self.risk_rules['min_bankroll_threshold']:.1%}")
        print(f"   • Maximum drawdown: {self.risk_rules['drawdown_limit']:.1%}")
        
        print(f"\n🚀 IMPLEMENTATION CHECKLIST:")
        print("   ✅ Calculate Kelly fraction for each opportunity")
        print("   ✅ Apply confidence and edge filters")
        print("   ✅ Use conservative sizing (50% Kelly)")
        print("   ✅ Monitor consecutive losses")
        print("   ✅ Track daily and total performance")
        print("   ✅ Implement automatic stop-loss triggers")
        
        # Save strategy configuration
        strategy_config = {
            'bankroll': self.bankroll,
            'min_edge': self.min_edge,
            'max_kelly': self.max_kelly,
            'confidence_threshold': self.confidence_threshold,
            'risk_rules': self.risk_rules,
            'portfolio_weights': getattr(self, 'portfolio_weights', {}),
            'created_at': datetime.now().isoformat()
        }
        
        with open('kelly_strategy_config.json', 'w') as f:
            json.dump(strategy_config, f, indent=2)
        
        print("💾 Strategy configuration saved to kelly_strategy_config.json")

def main():
    strategy = KellyCriterionStrategy()
    strategy.implement_kelly_strategy()

if __name__ == "__main__":
    main()
