#!/usr/bin/env python3
"""
UNIFIED MLB Betting Recommendations Engine
==========================================

Single source of truth for all betting recommendations.
- Only uses REAL betting lines (no defaults/hardcoded values)
- Calculates Expected Value (EV) based on real market odds
- Provides ML, O/U, and Run Line recommendations
- No duplicate logic anywhere

Author: AI Assistant
Created: 2025-08-19
"""

import json
import os
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class UnifiedBettingEngine:
    """Single, unified betting recommendations engine"""
    
    def __init__(self):
        self.current_date = datetime.now().strftime('%Y-%m-%d')
        self.root_dir = os.path.dirname(os.path.abspath(__file__))
        
        # File paths
        self.predictions_cache_path = os.path.join(self.root_dir, 'data', 'unified_predictions_cache.json')
        self.betting_lines_path = os.path.join(self.root_dir, 'data', f'real_betting_lines_{self.current_date.replace("-", "_")}.json')
        self.output_path = os.path.join(self.root_dir, 'data', f'betting_recommendations_{self.current_date.replace("-", "_")}.json')
        
        logger.info(f"🎯 Unified Betting Engine initialized for {self.current_date}")
        logger.info(f"📊 Using predictions: {self.predictions_cache_path}")
        logger.info(f"💰 Using betting lines: {self.betting_lines_path}")
    
    def load_predictions(self) -> Dict:
        """Load predictions from unified cache"""
        try:
            with open(self.predictions_cache_path, 'r') as f:
                data = json.load(f)
            
            # Check both structures: direct date key or nested under 'predictions_by_date'
            predictions_data = None
            if self.current_date in data:
                predictions_data = data[self.current_date]
            elif 'predictions_by_date' in data and self.current_date in data['predictions_by_date']:
                predictions_data = data['predictions_by_date'][self.current_date]
            
            if predictions_data:
                # Handle nested structure with 'games' key
                if 'games' in predictions_data:
                    games = predictions_data['games']
                else:
                    games = predictions_data
                
                logger.info(f"📊 Loaded {len(games)} game predictions for {self.current_date}")
                return games
            else:
                # Try latest available date if current date not found
                available_dates = []
                if 'predictions_by_date' in data:
                    available_dates = list(data['predictions_by_date'].keys())
                else:
                    available_dates = [k for k in data.keys() if k != 'metadata']
                
                if available_dates:
                    latest_date = max(available_dates)
                    logger.warning(f"⚠️ No predictions for {self.current_date}, using latest: {latest_date}")
                    
                    if 'predictions_by_date' in data:
                        predictions_data = data['predictions_by_date'][latest_date]
                    else:
                        predictions_data = data[latest_date]
                    
                    if 'games' in predictions_data:
                        games = predictions_data['games']
                    else:
                        games = predictions_data
                    
                    logger.info(f"📊 Loaded {len(games)} game predictions for {latest_date}")
                    return games
                else:
                    logger.warning(f"⚠️ No predictions found in cache")
                    return {}
                
        except FileNotFoundError:
            logger.error(f"❌ Predictions cache not found: {self.predictions_cache_path}")
            return {}
        except Exception as e:
            logger.error(f"❌ Error loading predictions: {e}")
            return {}
    
    def load_real_betting_lines(self) -> Dict:
        """Load REAL betting lines (no defaults allowed)"""
        try:
            with open(self.betting_lines_path, 'r') as f:
                data = json.load(f)
            
            if 'lines' in data:
                lines = data['lines']
                logger.info(f"💰 Loaded REAL betting lines for {len(lines)} games")
                return lines
            else:
                logger.warning(f"⚠️ No betting lines found in file")
                return {}
                
        except FileNotFoundError:
            logger.warning(f"⚠️ Real betting lines file not found: {self.betting_lines_path}")
            return {}
        except Exception as e:
            logger.error(f"❌ Error loading betting lines: {e}")
            return {}
    
    def get_betting_line_key(self, prediction_key: str) -> str:
        """Convert prediction key format to betting line key format"""
        # Convert "Boston Red Sox_vs_New York Yankees" to "Boston Red Sox @ New York Yankees"
        return prediction_key.replace("_vs_", " @ ")
    
    def american_to_decimal(self, american_odds: str) -> Optional[float]:
        """Convert American odds to decimal probability"""
        try:
            odds = int(american_odds.replace('+', ''))
            if odds > 0:
                return 100 / (odds + 100)
            else:
                return abs(odds) / (abs(odds) + 100)
        except:
            return None
    
    def calculate_expected_value(self, win_probability: float, american_odds: str) -> Optional[float]:
        """Calculate Expected Value: EV = (win_prob * profit) - (lose_prob * stake)"""
        try:
            odds = int(american_odds.replace('+', ''))
            
            if odds > 0:
                # Positive odds: profit on $1 bet = odds/100
                profit = odds / 100
            else:
                # Negative odds: profit on $1 bet = 100/abs(odds)
                profit = 100 / abs(odds)
            
            # Standard EV formula: (win_prob * profit) - (lose_prob * stake)
            ev = (win_probability * profit) - ((1 - win_probability) * 1)
            return ev
            
        except:
            return None
    
    def get_confidence_level(self, ev: float, win_prob: float) -> str:
        """Determine confidence level based on EV and win probability - MORE SELECTIVE"""
        if ev > 0.25 and win_prob > 0.65:
            return "HIGH"
        elif ev > 0.15 and win_prob > 0.6:
            return "MEDIUM"
        elif ev > 0.08 and win_prob > 0.55:
            return "LOW"
        else:
            return "NONE"
    
    def analyze_moneyline(self, game_key: str, predictions: Dict, betting_lines: Dict) -> List[Dict]:
        """Analyze moneyline betting opportunities"""
        recommendations = []
        
        # Get predictions (handle different field name formats) - FIXED STRUCTURE
        prediction_data = predictions.get('predictions', {})
        away_prob = prediction_data.get('away_win_prob', 0)
        home_prob = prediction_data.get('home_win_prob', 0)
        away_team = predictions.get('away_team', '')
        home_team = predictions.get('home_team', '')
        
        # Get real betting lines
        betting_line_key = self.get_betting_line_key(game_key)
        if betting_line_key not in betting_lines or 'moneyline' not in betting_lines[betting_line_key]:
            logger.debug(f"⚠️ No moneyline data for {game_key} (betting key: {betting_line_key})")
            return recommendations
        
        ml_lines = betting_lines[betting_line_key]['moneyline']
        away_odds = ml_lines.get('away')
        home_odds = ml_lines.get('home')
        
        if not away_odds or not home_odds:
            logger.debug(f"⚠️ Incomplete moneyline data for {game_key}")
            return recommendations
        
        # Analyze away team ML - only recommend if significant edge
        away_ev = self.calculate_expected_value(away_prob, str(away_odds))
        if away_ev and away_ev > 0.05:  # Require at least 5% edge
            confidence = self.get_confidence_level(away_ev, away_prob)
            if confidence != "NONE":
                recommendations.append({
                    'type': 'moneyline',
                    'recommendation': f"{away_team} ML",
                    'expected_value': away_ev,
                    'win_probability': away_prob,
                    'american_odds': str(away_odds),
                    'confidence': confidence.lower(),
                    'reasoning': f"Model projects {away_prob:.1%} win probability vs {self.american_to_decimal(str(away_odds)):.1%} implied odds"
                })
        
        # Analyze home team ML - only recommend if significant edge
        home_ev = self.calculate_expected_value(home_prob, str(home_odds))
        if home_ev and home_ev > 0.05:  # Require at least 5% edge
            confidence = self.get_confidence_level(home_ev, home_prob)
            if confidence != "NONE":
                recommendations.append({
                    'type': 'moneyline',
                    'recommendation': f"{home_team} ML",
                    'expected_value': home_ev,
                    'win_probability': home_prob,
                    'american_odds': str(home_odds),
                    'confidence': confidence.lower(),
                    'reasoning': f"Model projects {home_prob:.1%} win probability vs {self.american_to_decimal(str(home_odds)):.1%} implied odds"
                })
        
        return recommendations
    
    def analyze_totals(self, game_key: str, predictions: Dict, betting_lines: Dict) -> List[Dict]:
        """Analyze over/under betting opportunities"""
        recommendations = []
        
        # Get predictions (handle different field name formats) - FIXED STRUCTURE
        prediction_data = predictions.get('predictions', {})
        predicted_total = prediction_data.get('predicted_total_runs', 0)
        
        if not predicted_total:
            logger.debug(f"⚠️ No predicted total for {game_key}")
            return recommendations
        
        # Get real betting lines
        betting_line_key = self.get_betting_line_key(game_key)
        if betting_line_key not in betting_lines:
            logger.debug(f"⚠️ No betting lines for {game_key} (betting key: {betting_line_key})")
            return recommendations
            
        game_lines = betting_lines[betting_line_key]
        
        # Extract totals from markets array (real betting lines structure)
        totals_options = []
        
        # Check markets array for totals - collect all available lines
        for market in game_lines.get('markets', []):
            if market.get('key') == 'totals':
                over_outcome = None
                under_outcome = None
                for outcome in market.get('outcomes', []):
                    if 'Over' in outcome.get('name', ''):
                        over_outcome = outcome
                    elif 'Under' in outcome.get('name', ''):
                        under_outcome = outcome
                
                # If we have both Over and Under for this line
                if over_outcome and under_outcome:
                    totals_options.append({
                        'line': over_outcome.get('point'),
                        'over_odds': over_outcome.get('price'),
                        'under_odds': under_outcome.get('price')
                    })
        
        # Fallback: Check for total_runs structure if markets array not found
        if not totals_options and 'total_runs' in game_lines:
            total_runs = game_lines['total_runs']
            if all(k in total_runs for k in ['line', 'over', 'under']):
                totals_options.append({
                    'line': total_runs['line'],
                    'over_odds': total_runs['over'],
                    'under_odds': total_runs['under']
                })
                logger.debug(f"✅ Using total_runs structure for {game_key}: line {total_runs['line']}")
        
        if not totals_options:
            logger.debug(f"⚠️ No total lines found for {game_key}")
            return recommendations
        
        # Analyze each totals option
        for totals_option in totals_options:
            total_line = totals_option['line']
            over_odds = totals_option['over_odds']
            under_odds = totals_option['under_odds']
        
        # Analyze each totals option and keep only the best one
        best_recommendation = None
        best_ev = 0
        
        for totals_option in totals_options:
            total_line = totals_option['line']
            over_odds = totals_option['over_odds']
            under_odds = totals_option['under_odds']
            
            # Calculate win probabilities
            diff = abs(predicted_total - total_line)
            
            if predicted_total > total_line:
                # Model favors Over
                over_prob = 0.5 + min(diff * 0.1, 0.4)  # Max 90% confidence
                over_ev = self.calculate_expected_value(over_prob, str(over_odds))
                
                if over_ev and over_ev > best_ev:
                    confidence = self.get_confidence_level(over_ev, over_prob)
                    if confidence != "NONE":
                        best_recommendation = {
                            'type': 'total',
                            'recommendation': f"Over {total_line}",
                            'expected_value': over_ev,
                            'win_probability': over_prob,
                            'american_odds': str(over_odds),
                            'confidence': confidence.lower(),
                            'predicted_total': predicted_total,
                            'betting_line': total_line,
                            'reasoning': f"Predicted {predicted_total} vs line {total_line}"
                        }
                        best_ev = over_ev
            
            elif predicted_total < total_line:
                # Model favors Under
                under_prob = 0.5 + min(diff * 0.1, 0.4)  # Max 90% confidence
                under_ev = self.calculate_expected_value(under_prob, str(under_odds))
                
                if under_ev and under_ev > best_ev:
                    confidence = self.get_confidence_level(under_ev, under_prob)
                    if confidence != "NONE":
                        best_recommendation = {
                            'type': 'total',
                            'recommendation': f"Under {total_line}",
                            'expected_value': under_ev,
                            'win_probability': under_prob,
                            'american_odds': str(under_odds),
                            'confidence': confidence.lower(),
                            'predicted_total': predicted_total,
                            'betting_line': total_line,
                            'reasoning': f"Predicted {predicted_total} vs line {total_line}"
                        }
                        best_ev = under_ev
        
        # Only add the best recommendation
        if best_recommendation:
            recommendations.append(best_recommendation)
        
        return recommendations
    
    def analyze_run_line(self, game_key: str, predictions: Dict, betting_lines: Dict) -> List[Dict]:
        """Analyze run line (-1.5/+1.5) betting opportunities"""
        recommendations = []
        
        # Get predictions (handle different field name formats) - FIXED STRUCTURE
        prediction_data = predictions.get('predictions', {})
        away_prob = prediction_data.get('away_win_prob', 0)
        home_prob = prediction_data.get('home_win_prob', 0)
        away_team = predictions.get('away_team', '')
        home_team = predictions.get('home_team', '')
        
        # Only proceed if we have reasonable confidence in a team (55%+)
        favorite_prob = max(away_prob, home_prob)
        if favorite_prob < 0.55:
            return recommendations
        
        favorite_team = away_team if away_prob > home_prob else home_team
        underdog_team = home_team if away_prob > home_prob else away_team
        
        # Get real betting lines
        betting_line_key = self.get_betting_line_key(game_key)
        if betting_line_key not in betting_lines:
            logger.debug(f"⚠️ No betting lines for {game_key} (betting key: {betting_line_key})")
            return recommendations
            
        game_lines = betting_lines[betting_line_key]
        
        # Extract run lines from markets array
        for market in game_lines.get('markets', []):
            if market.get('key') == 'spreads':
                for outcome in market.get('outcomes', []):
                    team_name = outcome.get('name', '')
                    spread = outcome.get('point', 0)
                    odds = outcome.get('price')
                    
                    # Check if this is the favorite getting runs (-1.5) or underdog giving runs (+1.5)
                    if favorite_team in team_name and spread < 0:
                        # Favorite giving runs (e.g., Yankees -1.5)
                        # Calculate probability of winning by 2+ runs
                        cover_prob = favorite_prob * 0.7  # Estimate based on win probability
                        rl_ev = self.calculate_expected_value(cover_prob, str(odds))
                        
                        if rl_ev and rl_ev > 0.1:  # Require at least 10% edge for run lines
                            confidence = self.get_confidence_level(rl_ev, cover_prob)
                            if confidence != "NONE":
                                recommendations.append({
                                    'type': 'run_line',
                                    'recommendation': f"{favorite_team} {spread}",
                                    'expected_value': rl_ev,
                                    'win_probability': cover_prob,
                                    'american_odds': str(odds),
                                    'confidence': confidence.lower(),
                                    'reasoning': f"Strong favorite {favorite_team} ({favorite_prob:.1%}) to cover run line"
                                })
                    
                    elif underdog_team in team_name and spread > 0:
                        # Underdog getting runs (e.g., Red Sox +1.5)
                        # Calculate probability of losing by 1 or winning outright
                        cover_prob = (1 - favorite_prob) + (favorite_prob * 0.3)  # Win outright + lose by 1
                        rl_ev = self.calculate_expected_value(cover_prob, str(odds))
                        
                        if rl_ev and rl_ev > 0.1:  # Require at least 10% edge for run lines
                            confidence = self.get_confidence_level(rl_ev, cover_prob)
                            if confidence != "NONE":
                                recommendations.append({
                                    'type': 'run_line',
                                    'recommendation': f"{underdog_team} +{spread}",
                                    'expected_value': rl_ev,
                                    'win_probability': cover_prob,
                                    'american_odds': str(odds),
                                    'confidence': confidence.lower(),
                                    'reasoning': f"Underdog {underdog_team} value on run line"
                                })
        
        return recommendations
    
    def generate_recommendations(self) -> Dict:
        """Generate all betting recommendations"""
        logger.info("🔄 Generating unified betting recommendations...")
        
        # Load data
        predictions = self.load_predictions()
        betting_lines = self.load_real_betting_lines()
        
        if not predictions:
            logger.error("❌ No predictions available")
            return {}
        
        if not betting_lines:
            logger.warning("⚠️ No real betting lines available - recommendations will be limited")
        
        # Generate recommendations for each game
        all_recommendations = {
            'date': self.current_date,
            'generated_at': datetime.now().isoformat(),
            'source': 'Unified Betting Engine v1.0',
            'games': {}
        }
        
        total_value_bets = 0
        
        for game_key, game_predictions in predictions.items():
            logger.debug(f"🎯 Analyzing {game_key}")
            
            # Extract pitcher info from the correct location
            pitcher_info = game_predictions.get('pitcher_info', {})
            away_pitcher = pitcher_info.get('away_pitcher_name', game_predictions.get('away_pitcher', 'TBD'))
            home_pitcher = pitcher_info.get('home_pitcher_name', game_predictions.get('home_pitcher', 'TBD'))
            
            # Debug pitcher extraction
            if away_pitcher != 'TBD' or home_pitcher != 'TBD':
                logger.info(f"🎯 PITCHER INFO: {game_key} - {away_pitcher} vs {home_pitcher}")
            else:
                logger.debug(f"⚠️ No pitcher info found for {game_key}")
                logger.debug(f"   pitcher_info structure: {pitcher_info}")
                logger.debug(f"   game_predictions keys: {list(game_predictions.keys())}")
            
            game_recommendations = {
                'away_team': game_predictions.get('away_team', ''),
                'home_team': game_predictions.get('home_team', ''),
                'away_pitcher': away_pitcher,
                'home_pitcher': home_pitcher,
                'predicted_score': f"{game_predictions.get('predictions', {}).get('predicted_away_score', 0):.1f}-{game_predictions.get('predictions', {}).get('predicted_home_score', 0):.1f}",
                'predicted_total_runs': game_predictions.get('predictions', {}).get('predicted_total_runs', 0),
                'win_probabilities': {
                    'away_prob': game_predictions.get('predictions', {}).get('away_win_prob', 0),
                    'home_prob': game_predictions.get('predictions', {}).get('home_win_prob', 0)
                },
                'value_bets': []
            }
            
            # Analyze each bet type
            ml_recs = self.analyze_moneyline(game_key, game_predictions, betting_lines)
            total_recs = self.analyze_totals(game_key, game_predictions, betting_lines)
            rl_recs = self.analyze_run_line(game_key, game_predictions, betting_lines)
            
            # Combine all recommendations
            all_recs = ml_recs + total_recs + rl_recs
            
            # Sort by expected value
            all_recs.sort(key=lambda x: x.get('expected_value', 0), reverse=True)
            
            game_recommendations['value_bets'] = all_recs
            total_value_bets += len(all_recs)
            
            all_recommendations['games'][game_key] = game_recommendations
            
            if all_recs:
                logger.info(f"✅ {game_key}: {len(all_recs)} value bet(s) found")
            else:
                logger.debug(f"➖ {game_key}: No value bets found")
        
        # Summary
        all_recommendations['summary'] = {
            'total_games_analyzed': len(predictions),
            'games_with_betting_lines': len([g for g in predictions.keys() if g in betting_lines]),
            'total_value_bets': total_value_bets,
            'high_confidence_bets': len([bet for game in all_recommendations['games'].values() for bet in game['value_bets'] if bet['confidence'] == 'high']),
            'medium_confidence_bets': len([bet for game in all_recommendations['games'].values() for bet in game['value_bets'] if bet['confidence'] == 'medium'])
        }
        
        logger.info(f"📊 Analysis complete: {total_value_bets} total value bets found across {len(predictions)} games")
        return all_recommendations
    
    def save_recommendations(self, recommendations: Dict) -> bool:
        """Save recommendations to file"""
        try:
            os.makedirs(os.path.dirname(self.output_path), exist_ok=True)
            
            with open(self.output_path, 'w') as f:
                json.dump(recommendations, f, indent=2)
            
            logger.info(f"💾 Recommendations saved to {self.output_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to save recommendations: {e}")
            return False

def main():
    """Main execution"""
    logger.info("🚀 Starting Unified MLB Betting Engine")
    
    try:
        engine = UnifiedBettingEngine()
        recommendations = engine.generate_recommendations()
        
        if recommendations and engine.save_recommendations(recommendations):
            summary = recommendations.get('summary', {})
            logger.info("✅ SUCCESS: Unified betting recommendations generated")
            logger.info(f"📊 Summary: {summary.get('total_value_bets', 0)} value bets across {summary.get('total_games_analyzed', 0)} games")
            logger.info(f"🔥 High confidence: {summary.get('high_confidence_bets', 0)}")
            logger.info(f"⚡ Medium confidence: {summary.get('medium_confidence_bets', 0)}")
        else:
            logger.error("❌ Failed to generate recommendations")
            
    except Exception as e:
        logger.error(f"❌ Engine failed: {e}")
        raise

if __name__ == "__main__":
    main()
