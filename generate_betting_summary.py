"""
Today's MLB Betting Recommendations Summary
Generated with Comprehensive Optimized Model
===========================================

Date: August 25, 2025
Model: Comprehensive Optimized (v3.0 with Weather/Park/Betting Integration)
Games Analyzed: 13
Total Value Bets Found: 15
"""

import json
import sys
import os
from datetime import datetime

def load_todays_recommendations():
    """Load today's betting recommendations"""
    try:
        with open('data/betting_recommendations_2025_08_25.json', 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading recommendations: {e}")
        return None

def format_betting_summary(data):
    """Format betting recommendations into readable summary"""
    if not data:
        return "No data available"
    
    games = data.get('games', {})
    summary = []
    
    summary.append("=" * 80)
    summary.append("🎯 TODAY'S MLB BETTING RECOMMENDATIONS")
    summary.append("📅 Generated with COMPREHENSIVE OPTIMIZED MODEL")
    summary.append("🔧 Weather/Park Factors + Actual Results Optimization")
    summary.append("=" * 80)
    summary.append("")
    
    value_bet_count = 0
    strong_bets = []
    medium_bets = []
    
    for game_id, game in games.items():
        away_team = game.get('away_team', 'Unknown')
        home_team = game.get('home_team', 'Unknown')
        away_pitcher = game.get('away_pitcher', 'TBD')
        home_pitcher = game.get('home_pitcher', 'TBD')
        predicted_total = game.get('predicted_total_runs', 0)
        away_prob = game.get('win_probabilities', {}).get('away_prob', 0)
        home_prob = game.get('win_probabilities', {}).get('home_prob', 0)
        value_bets = game.get('value_bets', [])
        
        summary.append(f"🏟️ {away_team} @ {home_team}")
        summary.append(f"   Pitchers: {away_pitcher} vs {home_pitcher}")
        summary.append(f"   Predicted Total: {predicted_total:.1f} runs")
        summary.append(f"   Win Probabilities: {away_team} {away_prob:.1%} | {home_team} {home_prob:.1%}")
        
        if value_bets:
            value_bet_count += len(value_bets)
            summary.append(f"   💰 VALUE BETS FOUND: {len(value_bets)}")
            
            for bet in value_bets:
                bet_type = bet.get('type', 'unknown')
                recommendation = bet.get('recommendation', 'unknown')
                expected_value = bet.get('expected_value', 0)
                confidence = bet.get('confidence', 'unknown')
                reasoning = bet.get('reasoning', 'No reasoning provided')
                
                summary.append(f"      ⭐ {recommendation.upper()}")
                summary.append(f"         Type: {bet_type}")
                summary.append(f"         Expected Value: {expected_value:.3f}")
                summary.append(f"         Confidence: {confidence.upper()}")
                summary.append(f"         Reasoning: {reasoning}")
                
                # Categorize by confidence
                if confidence.lower() == 'high':
                    strong_bets.append(recommendation)
                elif confidence.lower() == 'medium':
                    medium_bets.append(recommendation)
        else:
            summary.append("   ❌ No value bets identified")
        
        summary.append("")
    
    # Summary statistics
    summary.append("=" * 80)
    summary.append("📊 BETTING SUMMARY")
    summary.append("=" * 80)
    summary.append(f"Total Games Analyzed: {len(games)}")
    summary.append(f"Total Value Bets Found: {value_bet_count}")
    summary.append(f"High Confidence Bets: {len(strong_bets)}")
    summary.append(f"Medium Confidence Bets: {len(medium_bets)}")
    summary.append("")
    
    if strong_bets:
        summary.append("🔥 HIGH CONFIDENCE RECOMMENDATIONS:")
        for bet in strong_bets:
            summary.append(f"   ⭐ {bet}")
        summary.append("")
    
    if medium_bets:
        summary.append("📈 MEDIUM CONFIDENCE RECOMMENDATIONS:")
        for bet in medium_bets:
            summary.append(f"   ⭐ {bet}")
        summary.append("")
    
    # Model information
    summary.append("=" * 80)
    summary.append("🔧 MODEL INFORMATION")
    summary.append("=" * 80)
    summary.append("✅ Comprehensive Optimized Configuration (v3.0)")
    summary.append("✅ Weather & Park Factors Integration")
    summary.append("✅ Real Betting Lines Integration") 
    summary.append("✅ Actual Game Results Optimization")
    summary.append("✅ Bias Correction Applied")
    summary.append("")
    summary.append("Key Optimizations Applied:")
    summary.append("• Base Lambda: 4.62 (corrected under-scoring)")
    summary.append("• Total Scoring Adjustment: 1.05 (environment correction)")
    summary.append("• Run Environment: 0.8788 (park factor integration)")
    summary.append("• Park/Weather Impact: Enhanced multiplier 1.1")
    summary.append("")
    summary.append(f"Generated: {data.get('generated_at', 'Unknown')}")
    summary.append(f"Source: {data.get('source', 'Unknown')}")
    summary.append("=" * 80)
    
    return "\n".join(summary)

def main():
    print("Loading today's betting recommendations...")
    data = load_todays_recommendations()
    
    if data:
        summary = format_betting_summary(data)
        print(summary)
        
        # Save summary to file
        with open('data/todays_betting_summary.txt', 'w') as f:
            f.write(summary)
        print(f"\n📁 Summary saved to: data/todays_betting_summary.txt")
    else:
        print("❌ Could not load betting recommendations")

if __name__ == "__main__":
    main()
