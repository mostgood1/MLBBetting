#!/usr/bin/env python3
"""
Real daily_ultrafastengine_predictions script - generates predictions using UltraFast engine

This script uses the UltraFast prediction engine to generate daily predictions for all MLB games.
"""
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add current directory and engines directory to path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))
sys.path.insert(0, str(current_dir / "engines"))


import argparse

def main():
    """Generate predictions for a given date using UltraFast engine"""
    parser = argparse.ArgumentParser(description="MLB UltraFast Prediction Engine")
    parser.add_argument('--date', type=str, help='Date for predictions (YYYY-MM-DD)', default=None)
    args = parser.parse_args()

    if args.date:
        prediction_date = args.date
    else:
        prediction_date = datetime.now().strftime('%Y-%m-%d')

    print(f"Generating UltraFast engine predictions for {prediction_date}")

    try:
        from engines.ultra_fast_engine import FastPredictionEngine
        engine = FastPredictionEngine()
        data_dir = current_dir / "data"
        games_file = data_dir / f"games_{prediction_date}.json"
        if not games_file.exists():
            print(f"No games file found at {games_file}. Run fetch_today_games.py first.")
            return False
        with open(games_file, 'r') as f:
            games = json.load(f)
        if not games:
            print(f"No games found for {prediction_date}")
            return False
        predictions_by_game = {}
        for game in games:
            away_team = game.get('away_team')
            home_team = game.get('home_team')
            away_pitcher = game.get('away_probable_pitcher', 'TBD')
            home_pitcher = game.get('home_probable_pitcher', 'TBD')
            if not away_team or not home_team:
                continue
            print(f"Generating prediction for {away_team} @ {home_team}")
            prediction = engine.get_fast_prediction(
                away_team=away_team,
                home_team=home_team,
                game_date=prediction_date,
                away_pitcher=away_pitcher if away_pitcher != 'TBD' else None,
                home_pitcher=home_pitcher if home_pitcher != 'TBD' else None
            )
            game_key = f"{away_team}_vs_{home_team}"
            predictions_by_game[game_key] = prediction
        # Save to unified predictions cache (append by date)
        cache_path = data_dir / 'unified_predictions_cache.json'
        data_dir.mkdir(exist_ok=True)
        if cache_path.exists():
            with open(cache_path, 'r') as f:
                try:
                    existing_cache = json.load(f)
                except Exception:
                    existing_cache = {}
        else:
            existing_cache = {}
        if 'predictions_by_date' not in existing_cache:
            existing_cache['predictions_by_date'] = {}
        existing_cache['predictions_by_date'][prediction_date] = {
            'games': predictions_by_game,
            'metadata': {
                'engine': 'UltraFast',
                'generated_at': datetime.now().isoformat(),
                'game_count': len(predictions_by_game)
            }
        }
        with open(cache_path, 'w') as f:
            json.dump(existing_cache, f, indent=2)
        print(f"Generated {len(predictions_by_game)} predictions and appended to {cache_path}")
        return True
    except Exception as e:
        print(f"Error generating UltraFast predictions: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
