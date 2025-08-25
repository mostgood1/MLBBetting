import os
print(f"[DEBUG] Executing: {os.path.abspath(__file__)}")
#!/usr/bin/env python3
"""
MLB Betting Recommendations Engine
=================================

Generates comprehensive betting recommendations including:
- Moneyline picks
- Over/Under total runs recommendations
- Confidence ratings
- Auto-refresh when TBDs are resolved
"""

import json
import logging
import os
import requests
from datetime import date, datetime
from typing import Dict, List, Optional

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BettingRecommendationsEngine:
    def fetch_current_betting_lines(self):
        # Load real betting lines for the current date
        date_str = self.current_date.replace('-', '_')
        lines_path = f"data/real_betting_lines_{date_str}.json"
        try:
            with open(lines_path, 'r') as f:
                lines_data = json.load(f)
            return lines_data
        except Exception as e:
            logger.error(f"Error loading betting lines from {lines_path}: {e}")
            return {}
    def __init__(self, date=None):
        if date is None:
            self.current_date = datetime.now().strftime('%Y-%m-%d')
        else:
            self.current_date = date
    def load_pitcher_info(self, date):
        import os
        date_underscore = date.replace('-', '_')
        pitcher_path = os.path.join('data', f'starting_pitchers_{date_underscore}.json')
        pitcher_lookup = {}
        try:
            with open(pitcher_path, 'r') as f:
                pitcher_data = json.load(f)
            for g in pitcher_data.get('games', []):
                away = g.get('away_team')
                home = g.get('home_team')
                away_norm = self.normalize_team_name(away)
                home_norm = self.normalize_team_name(home)
                key = f"{away_norm}_vs_{home_norm}"
                pitcher_lookup[key] = {
                    'away_pitcher': g.get('away_pitcher', 'TBD'),
                    'home_pitcher': g.get('home_pitcher', 'TBD')
                }
        except Exception:
            pass
        return pitcher_lookup
    def generate_betting_recommendations(self) -> Dict:
        import os
        cache_path = os.path.abspath(os.path.join(os.getcwd(), 'data', 'unified_predictions_cache.json'))
        logger.info(f"🔬 Diagnostic: Attempting to open predictions cache at: {cache_path}")
        if not os.path.exists(cache_path):
            logger.error(f"❌ Predictions cache file does not exist at: {cache_path}")
            raise FileNotFoundError(f"Predictions cache file not found: {cache_path}")
        try:
            with open(cache_path, 'r') as f:
                predictions_data = json.load(f)
        except Exception as e:
            logger.error(f"Error loading predictions from {cache_path}: {e}")
            return {}
        # Confirm available date keys
        available_dates = list(predictions_data.get('predictions_by_date', {}).keys())
        logger.info(f"🔬 Available dates in cache: {available_dates}")
        today_data = predictions_data.get('predictions_by_date', {}).get(self.current_date, {})
        if not today_data:
            logger.error(f"❌ No predictions found for date: {self.current_date}")
            return {}
        if 'games' in today_data:
            for k in today_data['games'].keys():
                logger.info(f"🔑 Game key: {k}")
        logger.info(f"🎯 Generating betting recommendations for {self.current_date}")
        # ...existing code...

        # Load pitcher info for the date
        pitcher_lookup = self.load_pitcher_info(self.current_date)

        # Get betting lines
        lines = self.fetch_current_betting_lines()

        # Get today's games
        if 'games' not in today_data:
            logger.warning(f"No games found for {self.current_date}")
            return {}

        games = today_data['games']
        recommendations = {
            'date': self.current_date,
            'generated_at': datetime.now().isoformat(),
            'betting_lines': lines,
            'games': {},
            'summary': {
                'total_games': len(games),
                'moneyline_picks': 0,
                'over_picks': 0,
                'under_picks': 0,
                'high_confidence_picks': 0
            }
        }
        # Populate each game from cache, copying all prediction fields
        for game_key, game_data in games.items():
            rec_game = {}
            # Copy basic info
            rec_game['away_team'] = game_data.get('away_team')
            rec_game['home_team'] = game_data.get('home_team')
            rec_game['game_date'] = game_data.get('game_date')
            # Copy predictions
            predictions = game_data.get('predictions', {})
            rec_game['predictions'] = predictions
            # Copy betting lines
            rec_game['betting_lines'] = game_data.get('betting_lines', {})
            # Copy recommendations
            rec_game['recommendations'] = game_data.get('recommendations', [])
            # Copy pitcher info
            rec_game['pitcher_info'] = game_data.get('pitcher_info', {})
            recommendations['games'][game_key] = rec_game
        # Diagnostics
        try:
            num_games = len(recommendations['games'])
            logger.info(f"🔎 Diagnostic: {num_games} games in recommendations output.")
            if num_games == 0:
                logger.error("❌ No games populated in recommendations output. Check extraction logic and input data.")
            else:
                sample_key = next(iter(recommendations['games']))
                sample_game = recommendations['games'][sample_key]
                logger.info(f"🔎 Sample game: {sample_key} | Predicted home: {sample_game['predictions'].get('predicted_home_score')} | Predicted away: {sample_game['predictions'].get('predicted_away_score')}")
        except Exception:
            pass
        return recommendations

def main():
    logger.info("🎯 MLB Betting Recommendations Engine Starting")
    import argparse
    parser = argparse.ArgumentParser(description="MLB Betting Recommendations Engine")
    parser.add_argument('--date', type=str, help='Date for recommendations (YYYY-MM-DD)', default=None)
    args = parser.parse_args()
    engine = BettingRecommendationsEngine(date=args.date)
    recommendations = engine.generate_betting_recommendations()
    if recommendations:
        logger.info("✅ Betting recommendations generated successfully!")
        output_path = f"data/betting_recommendations_{engine.current_date.replace('-', '_')}.json"
        try:
            with open(output_path, "w") as f:
                import json
                json.dump(recommendations, f, indent=2)
            logger.info(f"💾 Saved to {output_path}")
        except Exception as e:
            logger.error(f"❌ Failed to write recommendations file: {e}")
    else:
        logger.error("❌ Failed to generate betting recommendations")

if __name__ == "__main__":
    main()
