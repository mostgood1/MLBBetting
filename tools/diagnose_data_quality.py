import os
import json
from datetime import datetime, timedelta

def is_number(val):
    try:
        float(val)
        return True
    except (TypeError, ValueError):
        return False

def check_file(date_str):
    issues = []
    pred_path = f"data/betting_recommendations_{date_str}.json"
    score_path = f"data/final_scores_{date_str}.json"
    if not os.path.exists(pred_path):
        issues.append(f"Missing predictions file: {pred_path}")
        return issues
    if not os.path.exists(score_path):
        issues.append(f"Missing final scores file: {score_path}")
        return issues
    with open(pred_path, 'r') as f:
        try:
            predictions = json.load(f)
        except Exception as e:
            issues.append(f"Error loading predictions: {e}")
            return issues
    # If predictions is a dict, extract games from 'games' key
    if isinstance(predictions, dict):
        if 'games' in predictions and isinstance(predictions['games'], dict):
            predictions = list(predictions['games'].values())
        else:
            issues.append(f"Predictions file {pred_path} is a dict, no 'games' key with dict value found.")
            return issues
    if not isinstance(predictions, list):
        issues.append(f"Predictions file {pred_path} is not a list after extracting 'games'.")
        return issues
    with open(score_path, 'r') as f:
        try:
            scores = json.load(f)
        except Exception as e:
            issues.append(f"Error loading scores: {e}")
            return issues
    if isinstance(scores, dict):
        for key in ['games', 'scores', 'data']:
            if key in scores and isinstance(scores[key], list):
                scores = scores[key]
                break
        else:
            issues.append(f"Scores file {score_path} is a dict, no games list found.")
            return issues
    if not isinstance(scores, list):
        issues.append(f"Scores file {score_path} is not a list.")
        return issues
    # Check each game in predictions
    for game in predictions:
        if not isinstance(game, dict):
            issues.append(f"{date_str}: Prediction entry is not a dict: {game}")
            continue
        away_prob = game.get('away_win_probability')
        home_prob = game.get('home_win_probability')
        away_score = game.get('predicted_away_score')
        home_score = game.get('predicted_home_score')
        key = f"{game.get('away_team','?')}_vs_{game.get('home_team','?')}"
        if not is_number(away_prob):
            issues.append(f"{date_str} {key}: Invalid away_win_probability: {away_prob}")
        if not is_number(home_prob):
            issues.append(f"{date_str} {key}: Invalid home_win_probability: {home_prob}")
        if not is_number(away_score):
            issues.append(f"{date_str} {key}: Invalid predicted_away_score: {away_score}")
        if not is_number(home_score):
            issues.append(f"{date_str} {key}: Invalid predicted_home_score: {home_score}")
    # Check each game in scores
    for game in scores:
        if not isinstance(game, dict):
            issues.append(f"{date_str}: Score entry is not a dict: {game}")
            continue
        away_score = game.get('away_score')
        home_score = game.get('home_score')
        key = f"{game.get('away_team','?')}_vs_{game.get('home_team','?')}"
        if not is_number(away_score):
            issues.append(f"{date_str} {key}: Invalid final away_score: {away_score}")
        if not is_number(home_score):
            issues.append(f"{date_str} {key}: Invalid final home_score: {home_score}")
    return issues

def main():
    start_date = datetime.strptime('2025-08-15', '%Y-%m-%d')
    end_date = datetime.now()
    date = start_date
    all_issues = []
    while date <= end_date:
        date_str = date.strftime('%Y_%m_%d')
        issues = check_file(date_str)
        if issues:
            print(f"Issues for {date_str}:")
            for issue in issues:
                print(f"  - {issue}")
        date += timedelta(days=1)

if __name__ == '__main__':
    main()
