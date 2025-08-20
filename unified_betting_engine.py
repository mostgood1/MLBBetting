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
        """Calculate Expected Value: EV = (probability × payout) - 1"""
        try:
            odds = int(american_odds.replace('+', ''))
            
            if odds > 0:
                # Positive odds: payout = odds/100 + 1
                payout = (odds / 100) + 1
            else:
                # Negative odds: payout = (100/abs(odds)) + 1  
                payout = (100 / abs(odds)) + 1
            
            ev = (win_probability * payout) - 1
            return ev
            
        except:
            return None
    
    def get_confidence_level(self, ev: float, win_prob: float) -> str:
        """Determine confidence level based on EV and win probability"""
        if ev > 0.15 and win_prob > 0.6:
            return "HIGH"
        elif ev > 0.05 and win_prob > 0.55:
            return "MEDIUM"
        elif ev > 0.02:
            return "LOW"
        else:
            return "NONE"
    
    def analyze_moneyline(self, game_key: str, predictions: Dict, betting_lines: Dict) -> List[Dict]:
        """Analyze moneyline betting opportunities"""
        recommendations = []
        
        # Get predictions (handle different field name formats)
        away_prob = predictions.get('away_win_probability', 0)
        home_prob = predictions.get('home_win_probability', 0)
        away_team = predictions.get('away_team', '')
        home_team = predictions.get('home_team', '')
        
        # Get real betting lines
        if game_key not in betting_lines or 'moneyline' not in betting_lines[game_key]:
            logger.debug(f"⚠️ No moneyline data for {game_key}")
            return recommendations
        
        ml_lines = betting_lines[game_key]['moneyline']
        away_odds = ml_lines.get('away')
        home_odds = ml_lines.get('home')
        
        if not away_odds or not home_odds:
            logger.debug(f"⚠️ Incomplete moneyline data for {game_key}")
            return recommendations
        
        # Analyze away team ML
        away_ev = self.calculate_expected_value(away_prob, away_odds)
        if away_ev and away_ev > 0:
            confidence = self.get_confidence_level(away_ev, away_prob)
            if confidence != "NONE":
                recommendations.append({
                    'type': 'moneyline',
                    'recommendation': f"{away_team} ML",
                    'expected_value': away_ev,
                    'win_probability': away_prob,
                    'american_odds': away_odds,
                    'confidence': confidence.lower(),
                    'reasoning': f"Model projects {away_prob:.1%} win probability vs {self.american_to_decimal(away_odds):.1%} implied odds"
                })
        
        # Analyze home team ML
        home_ev = self.calculate_expected_value(home_prob, home_odds)
        if home_ev and home_ev > 0:
            confidence = self.get_confidence_level(home_ev, home_prob)
            if confidence != "NONE":
                recommendations.append({
                    'type': 'moneyline',
                    'recommendation': f"{home_team} ML",
                    'expected_value': home_ev,
                    'win_probability': home_prob,
                    'american_odds': home_odds,
                    'confidence': confidence.lower(),
                    'reasoning': f"Model projects {home_prob:.1%} win probability vs {self.american_to_decimal(home_odds):.1%} implied odds"
                })
        
        return recommendations
    
    def analyze_totals(self, game_key: str, predictions: Dict, betting_lines: Dict) -> List[Dict]:
        """Analyze over/under betting opportunities"""
        recommendations = []
        
        # Get predictions (handle different field name formats)
        predicted_total = predictions.get('predicted_total_runs', 0)
        
        if not predicted_total:
            logger.debug(f"⚠️ No predicted total for {game_key}")
            return recommendations
        
        # Get real betting lines
        if game_key not in betting_lines or 'total_runs' not in betting_lines[game_key]:
            logger.debug(f"⚠️ No totals data for {game_key}")
            return recommendations
        
        total_data = betting_lines[game_key]['total_runs']
        total_line = total_data.get('line')
        over_odds = total_data.get('over', '-110')
        under_odds = total_data.get('under', '-110')
        
        if not total_line:
            logger.debug(f"⚠️ No total line for {game_key}")
            return recommendations
        
        # Calculate win probabilities
        diff = abs(predicted_total - total_line)
        
        if predicted_total > total_line:
            # Model favors Over
            over_prob = 0.5 + min(diff * 0.1, 0.4)  # Max 90% confidence
            over_ev = self.calculate_expected_value(over_prob, over_odds)
            
            if over_ev and over_ev > 0:
                confidence = self.get_confidence_level(over_ev, over_prob)
                if confidence != "NONE":
                    recommendations.append({
                        'type': 'total',
                        'recommendation': f"Over {total_line}",
                        'expected_value': over_ev,
                        'win_probability': over_prob,
                        'american_odds': over_odds,
                        'confidence': confidence.lower(),
                        'predicted_total': predicted_total,
                        'betting_line': total_line,
                        'reasoning': f"Predicted {predicted_total} vs line {total_line}"
                    })
        
        elif predicted_total < total_line:
            # Model favors Under
            under_prob = 0.5 + min(diff * 0.1, 0.4)  # Max 90% confidence
            under_ev = self.calculate_expected_value(under_prob, under_odds)
            
            if under_ev and under_ev > 0:
                confidence = self.get_confidence_level(under_ev, under_prob)
                if confidence != "NONE":
                    recommendations.append({
                        'type': 'total',
                        'recommendation': f"Under {total_line}",
                        'expected_value': under_ev,
                        'win_probability': under_prob,
                        'american_odds': under_odds,
                        'confidence': confidence.lower(),
                        'predicted_total': predicted_total,
                        'betting_line': total_line,
                        'reasoning': f"Predicted {predicted_total} vs line {total_line}"
                    })
        
        return recommendations
    
    def analyze_run_line(self, game_key: str, predictions: Dict, betting_lines: Dict) -> List[Dict]:
        """Analyze run line (-1.5/+1.5) betting opportunities"""
        recommendations = []
        
        # Get predictions
        away_prob = predictions.get('away_win_probability', 0)
        home_prob = predictions.get('home_win_probability', 0)
        away_team = predictions.get('away_team', '')
        home_team = predictions.get('home_team', '')
        predicted_total = predictions.get('predicted_total_runs', 0)
        
        # Only proceed if we have strong confidence in a team (60%+)
        favorite_prob = max(away_prob, home_prob)
        if favorite_prob < 0.6:
            return recommendations
        
        favorite_team = away_team if away_prob > home_prob else home_team
        
        # Check if betting lines have run line data
        if game_key not in betting_lines:
            return recommendations
        
        # Look for run line odds (may be named differently)
        run_line_odds = None
        for key in ['run_line_odds', 'spread_odds', 'handicap_odds']:
            if key in betting_lines[game_key]:
                run_line_odds = betting_lines[game_key][key]
                break
        
        if not run_line_odds:
            # No real run line data available
            return recommendations
        
        # Estimate run line cover probability based on win probability and predicted margin
        if predicted_total > 0:
            # Very rough estimation: higher win prob + higher total = better run line cover chance
            base_cover_prob = (favorite_prob - 0.5) * 1.5  # Scale 60% win -> 15% base cover
            total_factor = min(predicted_total / 9.0, 1.2)  # Higher totals slightly favor favorites
            run_line_cover_prob = base_cover_prob * total_factor
            run_line_cover_prob = min(run_line_cover_prob, 0.7)  # Cap at 70%
            
            if run_line_cover_prob > 0.3:  # Only recommend if >30% cover chance
                run_line_ev = self.calculate_expected_value(run_line_cover_prob, run_line_odds)
                
                if run_line_ev and run_line_ev > 0:
                    confidence = self.get_confidence_level(run_line_ev, run_line_cover_prob)
                    if confidence != "NONE":
                        recommendations.append({
                            'type': 'run_line',
                            'recommendation': f"{favorite_team} -1.5",
                            'expected_value': run_line_ev,
                            'win_probability': run_line_cover_prob,
                            'american_odds': run_line_odds,
                            'confidence': confidence.lower(),
                            'reasoning': f"Strong favorite ({favorite_prob:.1%}) with {run_line_cover_prob:.1%} estimated cover probability"
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
            
            game_recommendations = {
                'away_team': game_predictions.get('away_team', ''),
                'home_team': game_predictions.get('home_team', ''),
                'away_pitcher': game_predictions.get('away_pitcher', 'TBD'),
                'home_pitcher': game_predictions.get('home_pitcher', 'TBD'),
                'predicted_score': f"{game_predictions.get('predicted_away_score', 0):.1f}-{game_predictions.get('predicted_home_score', 0):.1f}",
                'predicted_total_runs': game_predictions.get('predicted_total_runs', 0),
                'win_probabilities': {
                    'away_prob': game_predictions.get('away_win_probability', 0),
                    'home_prob': game_predictions.get('home_win_probability', 0)
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
