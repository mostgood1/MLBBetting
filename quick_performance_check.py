#!/usr/bin/env python3
"""
Quick Performance Checker - Checks accuracy of our enhanced predictions
"""
import json
import os
from datetime import datetime, timedelta

def load_recommendations(date_str):
    """Load betting recommendations for a specific date."""
    filename = f"data/betting_recommendations_{date_str.replace('-', '_')}.json"
    
    if not os.path.exists(filename):
        return None
        
    with open(filename, 'r') as f:
        return json.load(f)

def load_actual_results(date_str):
    """Load actual game results for a specific date."""
    filename = f"data/game_results_{date_str.replace('-', '_')}.json"
    
    if not os.path.exists(filename):
        return None
        
    with open(filename, 'r') as f:
        return json.load(f)

def calculate_accuracy(predictions, results):
    """Calculate prediction accuracy."""
    if not predictions or not results:
        return None
        
    correct_predictions = 0
    total_predictions = 0
    score_errors = []
    total_errors = []
    
    for game_key, pred_data in predictions.get('games', {}).items():
        if game_key not in results:
            continue
            
        result = results[game_key]
        prediction = pred_data.get('predictions', {})
        
        # Check winner prediction
        pred_home_win = prediction.get('home_win_prob', 0.5) > 0.5
        actual_home_win = result.get('home_score', 0) > result.get('away_score', 0)
        
        if pred_home_win == actual_home_win:
            correct_predictions += 1
        total_predictions += 1
        
        # Calculate score errors
        pred_home = prediction.get('predicted_home_score', 0)
        pred_away = prediction.get('predicted_away_score', 0)
        pred_total = prediction.get('predicted_total_runs', 0)
        
        actual_home = result.get('home_score', 0)
        actual_away = result.get('away_score', 0)
        actual_total = actual_home + actual_away
        
        if all([pred_home, pred_away, actual_home, actual_away]):
            home_error = abs(pred_home - actual_home)
            away_error = abs(pred_away - actual_away)
            total_error = abs(pred_total - actual_total)
            
            score_errors.append((home_error + away_error) / 2)
            total_errors.append(total_error)
    
    if total_predictions == 0:
        return None
        
    accuracy = (correct_predictions / total_predictions) * 100
    avg_score_error = sum(score_errors) / len(score_errors) if score_errors else 0
    avg_total_error = sum(total_errors) / len(total_errors) if total_errors else 0
    
    return {
        'accuracy': accuracy,
        'correct': correct_predictions,
        'total': total_predictions,
        'avg_score_error': avg_score_error,
        'avg_total_error': avg_total_error
    }

def analyze_recent_performance():
    """Analyze performance over recent days."""
    print("🎯 ENHANCED SYSTEM PERFORMANCE CHECK")
    print("=" * 50)
    
    # Check last 7 days
    today = datetime.now()
    total_correct = 0
    total_games = 0
    daily_results = []
    
    for i in range(7):
        check_date = today - timedelta(days=i)
        date_str = check_date.strftime("%Y-%m-%d")
        
        predictions = load_recommendations(date_str)
        results = load_actual_results(date_str)
        
        if predictions and results:
            accuracy_data = calculate_accuracy(predictions, results)
            if accuracy_data:
                daily_results.append({
                    'date': date_str,
                    'accuracy': accuracy_data['accuracy'],
                    'correct': accuracy_data['correct'],
                    'total': accuracy_data['total'],
                    'score_error': accuracy_data['avg_score_error'],
                    'total_error': accuracy_data['avg_total_error']
                })
                
                total_correct += accuracy_data['correct']
                total_games += accuracy_data['total']
                
                print(f"📅 {date_str}: {accuracy_data['accuracy']:.1f}% ({accuracy_data['correct']}/{accuracy_data['total']})")
    
    if total_games > 0:
        overall_accuracy = (total_correct / total_games) * 100
        print(f"\n🏆 OVERALL ACCURACY: {overall_accuracy:.1f}% ({total_correct}/{total_games})")
        
        if overall_accuracy > 52:
            print("✅ EXCELLENT! Above 52% threshold for profitability")
        elif overall_accuracy > 50:
            print("📈 GOOD! Above break-even point")
        else:
            print("⚠️ NEEDS IMPROVEMENT - Below break-even")
    else:
        print("❌ No matching prediction/result data found")
        
    return daily_results

def check_todays_recommendations():
    """Check today's recommendations quality."""
    today_str = datetime.now().strftime("%Y-%m-%d")
    predictions = load_recommendations(today_str)
    
    if not predictions:
        print(f"\n❌ No predictions found for {today_str}")
        return
        
    print(f"\n📊 TODAY'S RECOMMENDATIONS ({today_str})")
    print("-" * 40)
    
    total_games = len(predictions.get('games', {}))
    high_confidence = 0
    betting_recs = 0
    
    for game_key, game_data in predictions.get('games', {}).items():
        confidence = game_data.get('predictions', {}).get('confidence', 0)
        recommendations = game_data.get('recommendations', [])
        
        if confidence > 65:
            high_confidence += 1
            
        if any(rec.get('type') != 'none' for rec in recommendations):
            betting_recs += 1
    
    print(f"Total Games: {total_games}")
    print(f"High Confidence (>65%): {high_confidence}")
    print(f"Betting Recommendations: {betting_recs}")
    
    if high_confidence > 0:
        print(f"✅ {high_confidence} high-confidence predictions generated")
    else:
        print("⚠️ No high-confidence predictions today")

if __name__ == "__main__":
    analyze_recent_performance()
    check_todays_recommendations()
