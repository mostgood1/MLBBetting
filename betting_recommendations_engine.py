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
import requests
from datetime import datetime
from typing import Dict, List, Optional

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BettingRecommendationsEngine:
    def __init__(self):
        self.current_date = datetime.now().strftime('%Y-%m-%d')
        self.betting_lines = {}
        self.recommendations = {}
        self.real_betting_lines = {}  # Initialize real betting lines storage
        
    def fetch_current_betting_lines(self) -> Dict:
        """Fetch current real betting lines from our fetched data"""
        try:
            # Try to load real betting lines from our fetched data
            today_underscore = datetime.now().strftime('%Y_%m_%d')
            today_dash = datetime.now().strftime('%Y-%m-%d')
            
            # Check for both date formats
            possible_files = [
                f'MLB-Betting/data/real_betting_lines_{today_dash}.json',
                f'MLB-Betting/data/real_betting_lines_{today_underscore}.json'
            ]
            
            for file_path in possible_files:
                try:
                    with open(file_path, 'r') as f:
                        real_lines_data = json.load(f)
                        
                    if 'lines' in real_lines_data and real_lines_data['lines']:
                        logger.info(f"🎯 Loaded real betting lines from {file_path}")
                        logger.info(f"📊 Found {len(real_lines_data['lines'])} games with real market lines")
                        
                        # Store the real lines for game-specific lookups
                        self.real_betting_lines = real_lines_data['lines']
                        
                        # Return default thresholds (the actual lines are used per-game)
                        return {
                            'moneyline_threshold': 0.52,
                            'total_runs_threshold': 0.51,
                            'has_real_lines': True
                        }
                        
                except FileNotFoundError:
                    continue
                except json.JSONDecodeError as e:
                    logger.warning(f"Error reading {file_path}: {e}")
                    continue
            
            # Fallback to default if no real lines found
            logger.warning("⚠️ No real betting lines found, using default 9.5 total")
            self.real_betting_lines = {}
            return {
                'total_runs_line': 9.5,
                'moneyline_threshold': 0.52,
                'total_runs_threshold': 0.51,
                'has_real_lines': False
            }
            
        except Exception as e:
            logger.error(f"Error loading betting lines: {e}")
            self.real_betting_lines = {}
            return {
                'total_runs_line': 9.5,
                'moneyline_threshold': 0.52,
                'total_runs_threshold': 0.51,
                'has_real_lines': False
            }
    
    def safe_float(self, value, default=0.0):
        """Safely convert value to float, handling None and invalid values"""
        if value is None:
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default

    def calculate_win_probability(self, predicted_away: float, predicted_home: float) -> Dict:
        """Calculate win probabilities from predicted scores"""
        total_score = predicted_away + predicted_home
        
        if total_score == 0:
            return {'away_prob': 0.5, 'home_prob': 0.5}
        
        away_prob = predicted_away / total_score
        home_prob = predicted_home / total_score
        
        # Apply sigmoid transformation for more realistic probabilities
        import math
        
        score_diff = predicted_away - predicted_home
        win_prob = 1 / (1 + math.exp(-score_diff * 0.5))
        
        return {
            'away_prob': round(win_prob, 3),
            'home_prob': round(1 - win_prob, 3)
        }
    
    def generate_betting_recommendations(self) -> Dict:
        """Generate comprehensive betting recommendations"""
        
        logger.info(f"🎯 Generating betting recommendations for {self.current_date}")
        
        # Load current predictions
        try:
            with open('MLB-Betting/data/unified_predictions_cache.json', 'r') as f:
                predictions_data = json.load(f)
        except Exception as e:
            logger.error(f"Error loading predictions: {e}")
            return {}
        
        # Get betting lines
        lines = self.fetch_current_betting_lines()
        
        # Get today's games
        today_data = predictions_data.get('predictions_by_date', {}).get(self.current_date, {})
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
        
        logger.info(f"📊 Analyzing {len(games)} games for betting opportunities...")
        
        for game_key, game_data in games.items():
            away_team = game_data.get('away_team', '')
            home_team = game_data.get('home_team', '')
            away_pitcher = game_data.get('away_pitcher', 'TBD')
            home_pitcher = game_data.get('home_pitcher', 'TBD')
            
            pred_away_score = self.safe_float(game_data.get('predicted_away_score'), 0)
            pred_home_score = self.safe_float(game_data.get('predicted_home_score'), 0)
            pred_total_runs = self.safe_float(game_data.get('predicted_total_runs'), pred_away_score + pred_home_score)
            
            # Use real betting lines if available, otherwise fallback to default
            game_key = f"{away_team} @ {home_team}"
            total_runs_line = 9.5  # Default fallback
            
            # Check for real betting lines first
            if hasattr(self, 'real_betting_lines') and game_key in self.real_betting_lines:
                real_game_lines = self.real_betting_lines[game_key]
                if 'total_runs' in real_game_lines and 'line' in real_game_lines['total_runs']:
                    total_runs_line = self.safe_float(real_game_lines['total_runs']['line'], 9.5)
                    logger.info(f"🎯 Using REAL betting line for {game_key}: O/U {total_runs_line}")
                else:
                    logger.debug(f"⚠️ Real lines found but no total_runs for {game_key}")
            else:
                # Fallback to game-specific over/under line if available in prediction data
                game_ou_line = game_data.get('over_under_line')
                if game_ou_line and str(game_ou_line).replace('.', '').isdigit():
                    total_runs_line = self.safe_float(game_ou_line, 9.5)
                    logger.debug(f"📊 Using prediction O/U line for {game_key}: {total_runs_line}")
                else:
                    logger.debug(f"📈 Using default O/U line for {game_key}: {total_runs_line}")
            
            # Use actual win probabilities from cache (preferred) or calculate from scores (fallback)
            cached_away_prob = None
            cached_home_prob = None
            
            # Check for modern format first (cached_probabilities)
            if 'cached_probabilities' in game_data:
                cached_probs = game_data['cached_probabilities']
                cached_away_prob = cached_probs.get('away')
                cached_home_prob = cached_probs.get('home')
            # Check for legacy format (away_win_probability/home_win_probability)
            elif 'away_win_probability' in game_data and 'home_win_probability' in game_data:
                cached_away_prob = game_data.get('away_win_probability')
                cached_home_prob = game_data.get('home_win_probability')
            
            if cached_away_prob is not None and cached_home_prob is not None:
                # Use the sophisticated win probabilities from the prediction cache
                win_probs = {
                    'away_prob': round(self.safe_float(cached_away_prob), 3),
                    'home_prob': round(self.safe_float(cached_home_prob), 3)
                }
                logger.info(f"Using cached probabilities: {away_team} {win_probs['away_prob']*100:.1f}% vs {home_team} {win_probs['home_prob']*100:.1f}%")
            else:
                # Fallback: Calculate win probabilities from predicted scores
                win_probs = self.calculate_win_probability(pred_away_score, pred_home_score)
                logger.warning(f"No cached probabilities found, calculated from scores: {away_team} {win_probs['away_prob']*100:.1f}% vs {home_team} {win_probs['home_prob']*100:.1f}%")
            
            # Moneyline recommendation
            moneyline_pick = None
            moneyline_confidence = 0
            
            if win_probs['away_prob'] > lines['moneyline_threshold']:
                moneyline_pick = 'away'
                moneyline_confidence = win_probs['away_prob']
                recommendations['summary']['moneyline_picks'] += 1
            elif win_probs['home_prob'] > lines['moneyline_threshold']:
                moneyline_pick = 'home'
                moneyline_confidence = win_probs['home_prob']
                recommendations['summary']['moneyline_picks'] += 1
            
            # Over/Under recommendation
            ou_pick = None
            ou_confidence = 0
            
            if pred_total_runs > total_runs_line:
                ou_pick = 'over'
                # Calculate confidence based on how much over the line we are
                difference = pred_total_runs - total_runs_line
                ou_confidence = min(0.95, 0.5 + (difference / total_runs_line) * 0.3)
                if ou_confidence > lines['total_runs_threshold']:
                    recommendations['summary']['over_picks'] += 1
            elif pred_total_runs < total_runs_line:
                ou_pick = 'under'
                # Calculate confidence based on how much under the line we are
                difference = total_runs_line - pred_total_runs
                ou_confidence = min(0.95, 0.5 + (difference / total_runs_line) * 0.3)
                if ou_confidence > lines['total_runs_threshold']:
                    recommendations['summary']['under_picks'] += 1
            
            # Overall confidence rating
            has_tbds = (away_pitcher == 'TBD' or home_pitcher == 'TBD')
            confidence_penalty = 0.1 if has_tbds else 0
            
            overall_confidence = max(moneyline_confidence, ou_confidence) - confidence_penalty
            
            if overall_confidence > 0.7:
                recommendations['summary']['high_confidence_picks'] += 1
            
            # Create value_bets array for frontend compatibility
            value_bets = []
            
            # Add moneyline bet if confident enough
            if moneyline_pick and moneyline_confidence > lines['moneyline_threshold']:
                team_name = away_team if moneyline_pick == 'away' else home_team
                value_bets.append({
                    'type': 'moneyline',
                    'recommendation': f"{team_name} ML",
                    'expected_value': round((moneyline_confidence - 0.5) * 2, 3),  # Convert to EV
                    'win_probability': moneyline_confidence,
                    'american_odds': -120 if moneyline_confidence > 0.6 else +110,
                    'confidence': 'high' if moneyline_confidence > 0.7 else 'medium'
                })
            
            # Add total runs bet if confident enough
            if ou_pick and ou_confidence > lines['total_runs_threshold']:
                line_display = total_runs_line
                recommendation_text = f"{ou_pick.title()} {line_display}"
                value_bets.append({
                    'type': 'total',
                    'recommendation': recommendation_text,
                    'expected_value': round((ou_confidence - 0.5) * 2, 3),  # Convert to EV
                    'win_probability': ou_confidence,
                    'american_odds': -110,
                    'confidence': 'high' if ou_confidence > 0.7 else 'medium',
                    'predicted_total': pred_total_runs,
                    'betting_line': total_runs_line
                })

            # Game recommendation
            game_rec = {
                'away_team': away_team,
                'home_team': home_team,
                'away_pitcher': away_pitcher,
                'home_pitcher': home_pitcher,
                'has_tbd_pitchers': has_tbds,
                'predicted_score': f"{pred_away_score}-{pred_home_score}",
                'predicted_total_runs': pred_total_runs,
                'win_probabilities': win_probs,
                'betting_recommendations': {
                    'moneyline': {
                        'pick': moneyline_pick,
                        'team': away_team if moneyline_pick == 'away' else home_team if moneyline_pick == 'home' else None,
                        'confidence': round(moneyline_confidence, 3)
                    },
                    'total_runs': {
                        'line': total_runs_line,
                        'pick': ou_pick,
                        'predicted_total': pred_total_runs,
                        'confidence': round(ou_confidence, 3)
                    },
                    'value_bets': value_bets  # Add value_bets array for frontend
                },
                'overall_confidence': round(overall_confidence, 3),
                'recommendation_quality': 'HIGH' if overall_confidence > 0.7 else 'MEDIUM' if overall_confidence > 0.5 else 'LOW'
            }
            
            recommendations['games'][game_key] = game_rec
            
            # Log recommendation
            ml_text = f"{moneyline_pick.upper()} ({moneyline_confidence:.1%})" if moneyline_pick else "PASS"
            ou_text = f"{ou_pick.upper()} {total_runs_line} ({ou_confidence:.1%})" if ou_pick else "PASS"
            tbd_warning = " [TBD PITCHERS]" if has_tbds else ""
            
            logger.info(f"{away_team} @ {home_team}: ML={ml_text}, O/U={ou_text}{tbd_warning}")
        
        # Save recommendations
        with open(f'data/betting_recommendations_{self.current_date.replace("-", "_")}.json', 'w') as f:
            json.dump(recommendations, f, indent=2)
        
        logger.info("📈 BETTING RECOMMENDATIONS SUMMARY:")
        logger.info(f"Total Games: {recommendations['summary']['total_games']}")
        logger.info(f"Moneyline Picks: {recommendations['summary']['moneyline_picks']}")
        logger.info(f"Over Picks: {recommendations['summary']['over_picks']}")
        logger.info(f"Under Picks: {recommendations['summary']['under_picks']}")
        logger.info(f"High Confidence: {recommendations['summary']['high_confidence_picks']}")
        
        return recommendations

def main():
    """Main function"""
    logger.info("🎯 MLB Betting Recommendations Engine Starting")
    
    engine = BettingRecommendationsEngine()
    recommendations = engine.generate_betting_recommendations()
    
    if recommendations:
        logger.info("✅ Betting recommendations generated successfully!")
        logger.info(f"💾 Saved to data/betting_recommendations_{engine.current_date.replace('-', '_')}.json")
    else:
        logger.error("❌ Failed to generate betting recommendations")

if __name__ == "__main__":
    main()
