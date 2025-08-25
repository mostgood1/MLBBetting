#!/usr/bin/env python3
"""
Check game key matching between betting recommendations and final scores
"""

import json
import os
from team_name_normalizer import normalize_team_name

def check_game_matching(date):
    """Check if games from betting recommendations match final scores"""
    print(f"\n🎯 Checking game matching for {date}")
    print("=" * 50)
    
    # Load betting recommendations
    date_underscore = date.replace('-', '_')
    rec_file = f'data/betting_recommendations_{date_underscore}.json'
    scores_file = f'data/final_scores_{date_underscore}.json'
    
    try:
        with open(rec_file, 'r') as f:
            rec_data = json.load(f)
        games = rec_data.get('games', {})
        print(f"✅ Loaded {len(games)} games from betting recommendations")
    except FileNotFoundError:
        print(f"❌ Betting recommendations file not found: {rec_file}")
        return
    
    try:
        with open(scores_file, 'r') as f:
            scores_list = json.load(f)
        print(f"✅ Loaded {len(scores_list)} final scores")
    except FileNotFoundError:
        print(f"❌ Final scores file not found: {scores_file}")
        return
    
    # Create normalized lookup for final scores (like historical analysis does)
    scores_dict = {}
    for score in scores_list:
        away_team = normalize_team_name(score['away_team'])
        home_team = normalize_team_name(score['home_team'])
        key = f"{away_team}_vs_{home_team}"
        scores_dict[key] = score
    
    print(f"\n📊 GAME KEY ANALYSIS:")
    print("Betting Recommendations Keys:")
    rec_keys = []
    for game_key, game_data in games.items():
        # Extract team names from game data
        away_team = game_data.get('away_team', '')
        home_team = game_data.get('home_team', '')
        
        # Create normalized key like historical analysis does
        away_norm = normalize_team_name(away_team)
        home_norm = normalize_team_name(home_team)
        normalized_key = f"{away_norm}_vs_{home_norm}"
        
        rec_keys.append(normalized_key)
        print(f"  Original: {game_key}")
        print(f"  Teams: {away_team} vs {home_team}")
        print(f"  Normalized: {normalized_key}")
        print()
    
    print("Final Scores Keys:")
    score_keys = list(scores_dict.keys())
    for key in score_keys:
        print(f"  {key}")
    
    # Check matches
    print(f"\n🔍 MATCHING ANALYSIS:")
    matches = 0
    mismatches = []
    
    for rec_key in rec_keys:
        if rec_key in score_keys:
            matches += 1
            print(f"✅ MATCH: {rec_key}")
        else:
            mismatches.append(rec_key)
            print(f"❌ NO MATCH: {rec_key}")
    
    print(f"\n📈 SUMMARY:")
    print(f"Total games in recommendations: {len(rec_keys)}")
    print(f"Total final scores: {len(score_keys)}")
    print(f"Successful matches: {matches}")
    print(f"Missing matches: {len(mismatches)}")
    print(f"Match rate: {matches/len(rec_keys)*100:.1f}%")
    
    if mismatches:
        print(f"\n⚠️ MISMATCHED GAMES:")
        for mismatch in mismatches:
            print(f"  {mismatch}")
        
        # Try to find potential matches
        print(f"\n🔍 POTENTIAL MATCHES FOR MISMATCHED GAMES:")
        for mismatch in mismatches:
            mismatch_parts = mismatch.split('_vs_')
            if len(mismatch_parts) == 2:
                away, home = mismatch_parts
                for score_key in score_keys:
                    score_parts = score_key.split('_vs_')
                    if len(score_parts) == 2:
                        score_away, score_home = score_parts
                        if away in score_away or score_away in away:
                            print(f"    {mismatch} might match {score_key} (away team)")
                        if home in score_home or score_home in home:
                            print(f"    {mismatch} might match {score_key} (home team)")

if __name__ == "__main__":
    # Test with a couple of dates
    test_dates = ['2025-08-22', '2025-08-21', '2025-08-20']
    
    for date in test_dates:
        check_game_matching(date)
