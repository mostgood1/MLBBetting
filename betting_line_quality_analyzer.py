#!/usr/bin/env python3
"""
Betting Line Quality Analyzer
============================

Analyzes when the model beats betting lines vs when it follows the market.
Identifies patterns in over/under performance and line value.
"""

import json
import os
from datetime import datetime
from collections import defaultdict
import statistics

class BettingLineQualityAnalyzer:
    
    def __init__(self, data_directory="data"):
        self.data_directory = data_directory
        
    def analyze_line_performance(self):
        """Analyze betting line performance across all days"""
        
        print("💰 BETTING LINE QUALITY ANALYZER")
        print("=" * 40)
        print()
        
        # Load comprehensive report for overall stats
        self._load_and_analyze_all_days()
        
        # Identify best and worst line performance days
        self._find_line_performance_extremes()
        
        # Analyze what makes lines beatable vs unbeatable
        self._analyze_line_beating_patterns()
        
        # Generate betting strategy recommendations
        self._generate_line_strategy_recommendations()
    
    def _load_and_analyze_all_days(self):
        """Load and analyze all available days"""
        
        # Find all betting recommendation files
        betting_files = []
        for file in os.listdir(self.data_directory):
            if file.startswith('betting_recommendations_2025') and file.endswith('.json'):
                betting_files.append(file)
        
        daily_line_performance = {}
        
        for file in sorted(betting_files):
            date_str = file.replace('betting_recommendations_', '').replace('.json', '').replace('_', '-')
            
            line_stats = self._analyze_single_day_lines(date_str)
            if line_stats:
                daily_line_performance[date_str] = line_stats
        
        self.daily_line_performance = daily_line_performance
        self._print_line_performance_summary()
    
    def _analyze_single_day_lines(self, date_str):
        """Analyze betting line performance for a single day"""
        
        date_underscore = date_str.replace('-', '_')
        
        # Load betting recommendations
        betting_file = os.path.join(self.data_directory, f"betting_recommendations_{date_underscore}.json")
        if not os.path.exists(betting_file):
            return None
            
        # Load final scores
        scores_file = os.path.join(self.data_directory, f"final_scores_{date_underscore}.json")
        if not os.path.exists(scores_file):
            return None
        
        with open(betting_file, 'r') as f:
            betting_data = json.load(f)
        
        with open(scores_file, 'r') as f:
            scores_data = json.load(f)
        
        if 'games' not in betting_data:
            return None
        
        line_results = {
            'total_games': 0,
            'games_with_lines': 0,
            'over_under_correct': 0,
            'over_under_total': 0,
            'model_beat_market': 0,
            'model_followed_market': 0,
            'line_accuracy': 0,
            'avg_line_diff': 0,
            'sharp_moves': 0,
            'public_moves': 0
        }
        
        for game_key, game_data in betting_data['games'].items():
            line_results['total_games'] += 1
            
            # Check if game has betting lines
            if 'betting_lines' not in game_data:
                continue
                
            lines = game_data['betting_lines']
            total_line = lines.get('total_line')
            
            if not total_line:
                continue
                
            line_results['games_with_lines'] += 1
            
            # Get model prediction
            if 'predictions' in game_data and 'predictions' in game_data['predictions']:
                pred = game_data['predictions']['predictions']
                predicted_total = pred.get('predicted_total_runs', 0)
            else:
                continue
            
            # Find actual score
            actual_total = self._find_actual_total(game_key, scores_data)
            if actual_total is None:
                continue
            
            line_results['over_under_total'] += 1
            
            # Analyze over/under performance
            model_says_over = predicted_total > total_line
            actual_over = actual_total > total_line
            
            if model_says_over == actual_over:
                line_results['over_under_correct'] += 1
                line_results['model_beat_market'] += 1
            else:
                line_results['model_followed_market'] += 1
            
            # Calculate line difference
            line_diff = abs(predicted_total - total_line)
            line_results['avg_line_diff'] += line_diff
            
            # Identify sharp vs public moves
            if abs(predicted_total - total_line) > 1.5:
                line_results['sharp_moves'] += 1
            else:
                line_results['public_moves'] += 1
        
        # Calculate percentages
        if line_results['over_under_total'] > 0:
            line_results['line_accuracy'] = (line_results['over_under_correct'] / line_results['over_under_total']) * 100
            line_results['avg_line_diff'] = line_results['avg_line_diff'] / line_results['over_under_total']
        
        return line_results
    
    def _find_actual_total(self, game_key, scores_data):
        """Find actual total runs for a game"""
        
        # Try exact match first
        if game_key in scores_data:
            score_data = scores_data[game_key]
            away = score_data.get('away_score', score_data.get('final_away_score'))
            home = score_data.get('home_score', score_data.get('final_home_score'))
            
            if away is not None and home is not None:
                return away + home
        
        # Try team name matching
        if '_vs_' in game_key:
            away_team, home_team = game_key.split('_vs_')
            
            for score_key, score_data in scores_data.items():
                if away_team in score_key and home_team in score_key:
                    away = score_data.get('away_score', score_data.get('final_away_score'))
                    home = score_data.get('home_score', score_data.get('final_home_score'))
                    
                    if away is not None and home is not None:
                        return away + home
        
        return None
    
    def _print_line_performance_summary(self):
        """Print summary of line performance across all days"""
        
        if not self.daily_line_performance:
            print("❌ No line performance data available")
            return
        
        print("📊 OVERALL LINE PERFORMANCE SUMMARY")
        print("-" * 38)
        
        # Calculate overall stats
        total_accuracy = []
        total_beat_market = 0
        total_followed_market = 0
        total_sharp_moves = 0
        total_public_moves = 0
        
        for date, stats in self.daily_line_performance.items():
            if stats['line_accuracy'] > 0:
                total_accuracy.append(stats['line_accuracy'])
            
            total_beat_market += stats['model_beat_market']
            total_followed_market += stats['model_followed_market']
            total_sharp_moves += stats['sharp_moves']
            total_public_moves += stats['public_moves']
        
        if total_accuracy:
            avg_accuracy = statistics.mean(total_accuracy)
            best_day = max(self.daily_line_performance.items(), key=lambda x: x[1]['line_accuracy'])
            worst_day = min(self.daily_line_performance.items(), key=lambda x: x[1]['line_accuracy'])
            
            print(f"📈 Average Line Accuracy: {avg_accuracy:.1f}%")
            print(f"🏆 Best Day: {best_day[0]} ({best_day[1]['line_accuracy']:.1f}%)")
            print(f"📉 Worst Day: {worst_day[0]} ({worst_day[1]['line_accuracy']:.1f}%)")
            print(f"⚔️ Model Beat Market: {total_beat_market} times")
            print(f"👥 Model Followed Market: {total_followed_market} times")
            print(f"🔥 Sharp Moves: {total_sharp_moves}")
            print(f"🐑 Public Moves: {total_public_moves}")
            print()
    
    def _find_line_performance_extremes(self):
        """Find days with best and worst line performance"""
        
        print("🎯 LINE PERFORMANCE EXTREMES")
        print("-" * 30)
        
        if not self.daily_line_performance:
            print("No data available")
            return
        
        # Sort by line accuracy
        sorted_days = sorted(self.daily_line_performance.items(), 
                           key=lambda x: x[1]['line_accuracy'], reverse=True)
        
        print("🏆 TOP 3 LINE BEATING DAYS:")
        for i, (date, stats) in enumerate(sorted_days[:3]):
            if stats['line_accuracy'] > 0:
                print(f"   {i+1}. {date}: {stats['line_accuracy']:.1f}% accuracy ({stats['over_under_correct']}/{stats['over_under_total']})")
        
        print("\n📉 WORST 3 LINE PERFORMANCE DAYS:")
        for i, (date, stats) in enumerate(sorted_days[-3:]):
            if stats['line_accuracy'] > 0:
                print(f"   {i+1}. {date}: {stats['line_accuracy']:.1f}% accuracy ({stats['over_under_correct']}/{stats['over_under_total']})")
        
        print()
    
    def _analyze_line_beating_patterns(self):
        """Analyze patterns in when model beats lines"""
        
        print("🔍 LINE BEATING PATTERNS")
        print("-" * 25)
        
        high_performance_days = []
        low_performance_days = []
        
        for date, stats in self.daily_line_performance.items():
            if stats['line_accuracy'] > 60:
                high_performance_days.append((date, stats))
            elif stats['line_accuracy'] < 40 and stats['over_under_total'] > 0:
                low_performance_days.append((date, stats))
        
        if high_performance_days:
            print(f"✅ HIGH PERFORMANCE PATTERNS ({len(high_performance_days)} days):")
            
            avg_sharp_moves = statistics.mean([s[1]['sharp_moves'] for s in high_performance_days])
            avg_line_diff = statistics.mean([s[1]['avg_line_diff'] for s in high_performance_days])
            avg_games = statistics.mean([s[1]['games_with_lines'] for s in high_performance_days])
            
            print(f"   • Average Sharp Moves: {avg_sharp_moves:.1f}")
            print(f"   • Average Line Difference: {avg_line_diff:.1f}")
            print(f"   • Average Games w/ Lines: {avg_games:.1f}")
        
        if low_performance_days:
            print(f"\n❌ LOW PERFORMANCE PATTERNS ({len(low_performance_days)} days):")
            
            avg_sharp_moves = statistics.mean([s[1]['sharp_moves'] for s in low_performance_days])
            avg_line_diff = statistics.mean([s[1]['avg_line_diff'] for s in low_performance_days])
            avg_games = statistics.mean([s[1]['games_with_lines'] for s in low_performance_days])
            
            print(f"   • Average Sharp Moves: {avg_sharp_moves:.1f}")
            print(f"   • Average Line Difference: {avg_line_diff:.1f}")
            print(f"   • Average Games w/ Lines: {avg_games:.1f}")
        
        print()
    
    def _generate_line_strategy_recommendations(self):
        """Generate recommendations for line betting strategy"""
        
        print("🎯 LINE BETTING STRATEGY RECOMMENDATIONS")
        print("-" * 42)
        
        if not self.daily_line_performance:
            print("No data available for recommendations")
            return
        
        # Calculate overall performance metrics
        all_accuracies = [stats['line_accuracy'] for stats in self.daily_line_performance.values() 
                         if stats['line_accuracy'] > 0]
        
        if all_accuracies:
            avg_accuracy = statistics.mean(all_accuracies)
            
            print("📋 IMMEDIATE ACTIONS:")
            print("-" * 18)
            
            if avg_accuracy < 50:
                print("🚨 CRITICAL: Lines are beating the model consistently")
                print("   → STOP betting over/under until model improves")
                print("   → Focus on moneyline bets only")
                print("   → Investigate total runs calculation errors")
            elif avg_accuracy < 52:
                print("⚠️  WARNING: Model barely beating random chance")
                print("   → Reduce over/under bet sizes")
                print("   → Only bet when model differs from line by 2+ runs")
                print("   → Add weather and wind factors to total runs model")
            else:
                print("✅ GOOD: Model shows edge over betting lines")
                print("   → Increase over/under bet sizes on high-confidence days")
                print("   → Target games where model differs from line by 1.5+ runs")
                print("   → Monitor line movement throughout the day")
            
            print(f"\n🎯 TARGET METRICS:")
            print(f"   • Current O/U Accuracy: {avg_accuracy:.1f}%")
            print(f"   • Target O/U Accuracy: 55%+")
            print(f"   • Minimum Edge Required: 3%")
            print(f"   • Sharp Move Threshold: 1.5+ run difference")
            
            print(f"\n📈 IMPROVEMENT STRATEGIES:")
            print("   1. Add real-time weather data to total runs model")
            print("   2. Factor in bullpen usage from previous games")
            print("   3. Monitor line movement for reverse line movement")
            print("   4. Create 'line quality score' before betting")
            print("   5. Skip betting on days with limited line coverage")

def main():
    analyzer = BettingLineQualityAnalyzer()
    analyzer.analyze_line_performance()

if __name__ == "__main__":
    main()
