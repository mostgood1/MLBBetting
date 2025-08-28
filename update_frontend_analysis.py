#!/usr/bin/env python3
"""
Enhanced Frontend Histo       with open('frontend_historical_summary.json', 'w') as f:
        json.dump(frontend_summary, f, indent=2)
    
    print("[OK] Frontend historical summary updated")
    return True open('frontend_historical_summary.json', 'w') as f:
        json.dump(frontend_summary, f, indent=2)
    
    print("[OK] Frontend historical summary updated")l Analysis Integration
Updates the frontend to show comprehensive analysis results
"""
import json
import os
from datetime import datetime, timedelta

def update_frontend_with_comprehensive_analysis():
    """Update frontend historical analysis with our comprehensive results."""
    
    # Check if comprehensive analysis report exists
    report_file = "comprehensive_mlb_analysis_report.json"
    
    if not os.path.exists(report_file):
        print("❌ Comprehensive analysis report not found")
        print("Run: python comprehensive_mlb_analysis_system.py")
        return False
    
    # Load comprehensive analysis results
    with open(report_file, 'r') as f:
        analysis_data = json.load(f)
    
    print("[OK] Loaded comprehensive analysis data")
    print(f"[STATS] Analysis covers {analysis_data['total_games_analyzed']} games from {analysis_data['date_range']['start_date']} to {analysis_data['date_range']['end_date']}")
    
    # Update the frontend summary
    frontend_summary = {
        "updated_at": datetime.now().isoformat(),
        "system_status": "enhanced",
        "total_games_analyzed": analysis_data['total_games_analyzed'],
        "overall_accuracy": analysis_data['model_predictive_accuracy']['winner_prediction']['accuracy_percentage'],
        "score_accuracy": {
            "average_error": analysis_data['model_predictive_accuracy']['score_accuracy']['average_score_error'],
            "within_1_run": analysis_data['model_predictive_accuracy']['score_accuracy']['within_1_run_percent'],
            "within_2_runs": analysis_data['model_predictive_accuracy']['score_accuracy']['within_2_runs_percent']
        },
        "betting_performance": {
            "over_under_accuracy": analysis_data['betting_line_performance']['over_under_accuracy']['accuracy_percentage'],
            "edge_over_market": analysis_data['betting_line_performance']['line_beating_performance']['edge_percentage']
        },
        "date_range": analysis_data['date_range'],
        "enhancements_applied": {
            "quick_enhancements": True,
            "ensemble_model": True,
            "kelly_criterion": True,
            "feature_engineering": True
        }
    }
    
    # Save updated frontend data
    with open('data/frontend_historical_summary.json', 'w') as f:
        json.dump(frontend_summary, f, indent=2)
    
    print("[OK] Frontend historical summary updated")
    return True

def check_daily_automation_status():
    """Check if daily automation needs to be updated."""
    
    # Check if automation is using enhanced engine
    automation_file = "complete_daily_automation.py"
    
    with open(automation_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if "betting_recommendations_engine.py" in content:
        print("[OK] Daily automation is using enhanced betting engine")
        
        # Check if it's running the comprehensive analysis
        if "comprehensive_mlb_analysis_system.py" in content:
            print("[OK] Daily automation includes comprehensive analysis")
        else:
            print("⚠️ Daily automation should include comprehensive analysis")
            return False
    else:
        print("❌ Daily automation not using enhanced engine")
        return False
    
    return True

def create_enhanced_daily_summary():
    """Create an enhanced daily summary for the frontend."""
    
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Load today's recommendations
    rec_file = f"data/betting_recommendations_{today.replace('-', '_')}.json"
    
    if not os.path.exists(rec_file):
        print(f"❌ No recommendations found for {today}")
        return False
    
    with open(rec_file, 'r') as f:
        recs = json.load(f)
    
    # Analyze today's recommendations
    total_games = len(recs.get('games', {}))
    high_confidence = 0
    betting_recs = 0
    total_confidence = 0
    
    high_conf_games = []
    
    for game_key, game_data in recs.get('games', {}).items():
        confidence = game_data.get('predictions', {}).get('confidence', 0)
        recommendations = game_data.get('recommendations', [])
        
        total_confidence += confidence
        
        if confidence > 65:
            high_confidence += 1
            high_conf_games.append({
                'game': f"{game_data['away_team']} @ {game_data['home_team']}",
                'confidence': confidence,
                'recommendation': recommendations[0] if recommendations else None
            })
            
        if any(rec.get('type') != 'none' for rec in recommendations):
            betting_recs += 1
    
    avg_confidence = total_confidence / total_games if total_games > 0 else 0
    
    daily_summary = {
        "date": today,
        "generated_at": datetime.now().isoformat(),
        "total_games": total_games,
        "high_confidence_games": high_confidence,
        "betting_recommendations": betting_recs,
        "average_confidence": round(avg_confidence, 1),
        "high_confidence_details": high_conf_games,
        "system_enhancements": {
            "active": True,
            "features": [
                "Enhanced pitcher factor validation",
                "Improved confidence calculation", 
                "Kelly Criterion bet sizing",
                "Advanced feature engineering",
                "Ensemble model integration"
            ]
        }
    }
    
    # Save daily summary
    os.makedirs('data/daily_summaries', exist_ok=True)
    with open(f'data/daily_summaries/summary_{today.replace("-", "_")}.json', 'w') as f:
        json.dump(daily_summary, f, indent=2)
    
    print(f"[OK] Enhanced daily summary created for {today}")
    print(f"[STATS] {total_games} games, {high_confidence} high-confidence, {betting_recs} betting recs")
    
    return True

if __name__ == "__main__":
    print(">> UPDATING FRONTEND WITH ENHANCED SYSTEM")
    print("=" * 50)
    
    # Update frontend with comprehensive analysis
    update_frontend_with_comprehensive_analysis()
    
    # Check daily automation status
    check_daily_automation_status()
    
    # Create enhanced daily summary
    create_enhanced_daily_summary()
    
    print("\n[OK] Frontend update complete!")
    print("\nNext steps:")
    print("1. Refresh your browser to see updated historical analysis")
    print("2. Check the daily summary for today's enhanced predictions")
    print("3. Monitor betting performance with new tracking system")
