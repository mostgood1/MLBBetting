import os
print(f"[DEBUG] Executing: {os.path.abspath(__file__)}")
#!/usr/bin/env python3
"""
MLB Betting Recommendation            # Copy betting lines
            rec_game['betting_lines'] = game_data.get('betting_lines', {})
            # Copy recommendations
            recs = game_data.get('recommendations', [])
            if not recs:
                recs = [{'type': 'none', 'recommendation': 'No recommendations'}]
            rec_game['recommendations'] = recs
            # Copy pitcher info
            rec_game['pitcher_info'] = game_data.get('pitcher_info', {})
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
    
    def get_real_betting_lines_for_game(self, game_data, lines_data):
        """Extract real betting lines for a specific game"""
        away_team = game_data.get('away_team', '')
        home_team = game_data.get('home_team', '')
        
        # Try different key formats to match the real betting lines
        possible_keys = [
            f"{away_team} @ {home_team}",
            f"{away_team} vs {home_team}",
            f"{away_team}@{home_team}",
            f"{away_team} at {home_team}",
            f"{away_team}_vs_{home_team}"
        ]
        
        lines = lines_data.get('lines', {})
        game_lines = None
        
        # Debug: log what we're looking for
        logger.info(f"🔍 Looking for betting lines for: {away_team} vs {home_team}")
        logger.info(f"🔍 Available keys in real_betting_lines: {list(lines.keys())[:3]}...")
        
        for key in possible_keys:
            if key in lines:
                game_lines = lines[key]
                logger.info(f"✅ Found betting lines with key: {key}")
                break
        
        if not game_lines:
            logger.warning(f"❌ No betting lines found for {away_team} vs {home_team}")
            # Return default structure if no real lines found
            return {
                "home_ml": None,
                "away_ml": None,
                "total_line": None,
                "over_odds": None,
                "under_odds": None,
                "run_line": None,
                "run_line_odds": None
            }
        
        # Extract betting lines from real data
        betting_lines = {}
        
        # Moneyline
        if 'moneyline' in game_lines:
            ml = game_lines['moneyline']
            betting_lines['home_ml'] = ml.get('home')
            betting_lines['away_ml'] = ml.get('away')
            logger.info(f"📊 Moneyline: Home {ml.get('home')}, Away {ml.get('away')}")
        
        # Total runs
        if 'total_runs' in game_lines:
            tr = game_lines['total_runs']
            betting_lines['total_line'] = tr.get('line')
            betting_lines['over_odds'] = tr.get('over')
            betting_lines['under_odds'] = tr.get('under')
            logger.info(f"📊 Total: Line {tr.get('line')}, Over {tr.get('over')}, Under {tr.get('under')}")
        
        # Run line (spread)
        if 'run_line' in game_lines:
            rl = game_lines['run_line']
            betting_lines['run_line'] = rl.get('line')
            betting_lines['run_line_odds'] = rl.get('odds')
            logger.info(f"📊 Run line: {rl.get('line')} at {rl.get('odds')}")
        
        # Also check markets array for totals if not found above
        if 'markets' in game_lines and not betting_lines.get('total_line'):
            logger.info("🔍 Checking markets array for totals...")
            for market in game_lines['markets']:
                if market.get('key') == 'totals' and 'outcomes' in market:
                    outcomes = market['outcomes']
                    for outcome in outcomes:
                        if outcome.get('name') == 'Over':
                            betting_lines['total_line'] = outcome.get('point')
                            betting_lines['over_odds'] = outcome.get('price')
                            logger.info(f"📊 From markets - Over: {outcome.get('point')} at {outcome.get('price')}")
                        elif outcome.get('name') == 'Under':
                            betting_lines['under_odds'] = outcome.get('price')
                            logger.info(f"📊 From markets - Under: {outcome.get('price')}")
                
                # Extract spreads (run line) from markets
                if market.get('key') == 'spreads' and 'outcomes' in market:
                    outcomes = market['outcomes']
                    for outcome in outcomes:
                        if outcome.get('point') and outcome['point'] > 0:  # Home team spread
                            betting_lines['run_line'] = abs(outcome['point'])
                            betting_lines['run_line_odds'] = outcome.get('price')
                            logger.info(f"📊 From markets - Run line: {abs(outcome['point'])} at {outcome.get('price')}")
        
        logger.info(f"📊 Final betting lines: {betting_lines}")
        return betting_lines
    
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
            
            # Copy ONLY the predictions data (not the entire game_data structure)
            predictions = game_data.get('predictions', {})
            rec_game['predictions'] = predictions
            
            # Set betting lines with real data (not from cache)
            real_betting_lines = self.get_real_betting_lines_for_game(game_data, lines)
            rec_game['betting_lines'] = real_betting_lines
            
            # Copy recommendations
            recs = game_data.get('recommendations', [])
            if not recs:
                recs = [{'type': 'none', 'recommendation': 'No recommendations'}]
            rec_game['recommendations'] = recs
            
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
