"""
Comprehensive Day-by-Day Analysis Script
This script generates detailed analysis separating MODEL performance (all games) 
from BETTING RECOMMENDATION performance (only recommended bets)
"""

from comprehensive_historical_analysis import ComprehensiveHistoricalAnalyzer
import json

def analyze_all_days():
    analyzer = ComprehensiveHistoricalAnalyzer()
    cumulative = analyzer.get_cumulative_analysis()
    daily_breakdown = cumulative.get('daily_breakdown', [])
    
    print("🏆 COMPREHENSIVE DAY-BY-DAY ANALYSIS")
    print("=" * 80)
    print()
    
    # Summary statistics
    total_model_games = 0
    total_betting_recommendations = 0
    profitable_days = 0
    
    for i, day in enumerate(daily_breakdown):
        date = day.get('date', 'UNKNOWN')
        
        print(f"📅 DAY {i+1}: {date}")
        print("=" * 80)
        
        # MODEL PERFORMANCE (ALL GAMES)
        model_perf = day.get('model_performance', {})
        if model_perf:
            total_games = model_perf.get('total_games', 0)
            winner_accuracy = model_perf.get('winner_accuracy', 0)
            total_model_games += total_games
            
            print("📊 MODEL PERFORMANCE (Prediction Accuracy for ALL Games):")
            print(f"   🎯 Total games analyzed: {total_games}")
            print(f"   ✅ Winner prediction accuracy: {winner_accuracy}%")
            
            # Additional model metrics if available
            if 'total_runs_accuracy_1' in model_perf:
                print(f"   🔢 Total runs accuracy (±1): {model_perf.get('total_runs_accuracy_1', 'N/A')}%")
            if 'total_runs_accuracy_2' in model_perf:
                print(f"   🔢 Total runs accuracy (±2): {model_perf.get('total_runs_accuracy_2', 'N/A')}%")
            if 'average_score_diff' in model_perf:
                print(f"   📈 Average score difference: {model_perf.get('average_score_diff', 'N/A')}")
                
        else:
            print("❌ MODEL PERFORMANCE: No prediction data available")
        print()
        
        # BETTING RECOMMENDATION PERFORMANCE (ONLY RECOMMENDED BETS)
        betting_perf = day.get('betting_performance', {})
        if betting_perf:
            total_recs = betting_perf.get('total_recommendations', 0)
            overall_accuracy = betting_perf.get('overall_accuracy', 0)
            roi = betting_perf.get('roi_percentage', 0)
            net_profit = betting_perf.get('net_profit', 0)
            
            total_betting_recommendations += total_recs
            if net_profit > 0:
                profitable_days += 1
                
            print("💰 BETTING RECOMMENDATION PERFORMANCE (Recommended Bets Only):")
            print(f"   📋 Total recommendations made: {total_recs}")
            print(f"   🎯 Overall betting accuracy: {overall_accuracy}%")
            
            # Bet type breakdown
            ml_stats = betting_perf.get('moneyline_stats', {})
            rl_stats = betting_perf.get('runline_stats', {})
            total_stats = betting_perf.get('total_stats', {})
            
            print("   📊 Bet Type Breakdown:")
            print(f"      💵 Moneyline: {ml_stats.get('total', 0)} bets → {ml_stats.get('correct', 0)} wins ({ml_stats.get('accuracy', 0)}% win rate)")
            print(f"      📈 Run Line: {rl_stats.get('total', 0)} bets → {rl_stats.get('correct', 0)} wins ({rl_stats.get('accuracy', 0)}% win rate)")
            print(f"      🎯 Total O/U: {total_stats.get('total', 0)} bets → {total_stats.get('correct', 0)} wins ({total_stats.get('accuracy', 0)}% win rate)")
            
            # Financial performance
            wagered = betting_perf.get('total_bet_amount', 0)
            returned = betting_perf.get('total_winnings', 0)
            
            print("   💸 Financial Performance:")
            print(f"      💰 Total wagered: ${wagered}")
            print(f"      📈 Total returned: ${returned}")
            print(f"      {'📊' if net_profit >= 0 else '📉'} Net profit/loss: ${net_profit}")
            print(f"      {'🎉' if roi >= 0 else '😞'} ROI: {roi}%")
            
            # Day status
            if roi > 10:
                print("   🌟 STATUS: EXCELLENT DAY")
            elif roi > 0:
                print("   ✅ STATUS: PROFITABLE DAY")
            elif roi > -10:
                print("   ⚠️ STATUS: MINOR LOSS")
            else:
                print("   ❌ STATUS: SIGNIFICANT LOSS")
                
        else:
            print("❌ BETTING RECOMMENDATION PERFORMANCE: No betting data available")
        
        print()
        print("─" * 80)
        print()
    
    # SUMMARY STATISTICS
    print("📈 OVERALL SUMMARY")
    print("=" * 80)
    print(f"🎯 Total games with model predictions: {total_model_games}")
    print(f"💰 Total betting recommendations made: {total_betting_recommendations}")
    print(f"✅ Profitable days: {profitable_days} out of {len(daily_breakdown)} days")
    print(f"📊 Profitability rate: {(profitable_days/len(daily_breakdown)*100):.1f}%")
    
    # Overall performance from cumulative
    cumulative_betting = cumulative.get('betting_performance', {})
    print(f"🎪 Overall system performance:")
    print(f"   Total bets: {cumulative_betting.get('total_recommendations', 0)}")
    print(f"   Overall accuracy: {cumulative_betting.get('overall_accuracy', 0)}%")
    print(f"   Overall ROI: {cumulative_betting.get('roi_percentage', 0)}%")
    print(f"   Net profit/loss: ${cumulative_betting.get('net_profit', 0)}")

if __name__ == "__main__":
    analyze_all_days()
