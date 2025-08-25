"""
Betting Integration Layer - Converts unified betting engine output to frontend-compatible format
This module handles the critical data conversion between the unified betting engine and the Flask API.
"""

import json
import logging
from typing import Dict, Any, Optional, Tuple, List

# Set up logging
logger = logging.getLogger(__name__)

def get_app_betting_recommendations() -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Get betting recommendations from unified engine and convert to frontend format
    
    Returns:
        Tuple of (raw_recommendations_dict, frontend_recommendations_list)
    """
    try:
        logger.info("🎯 Loading unified betting engine recommendations...")
        
        # First try to load existing cached recommendations
        from datetime import datetime
        current_date = datetime.now().strftime('%Y-%m-%d')
        cache_file = f'data/betting_recommendations_{current_date.replace("-", "_")}.json'
        
        try:
            logger.info(f"🔄 Loading cached recommendations from {cache_file}...")
            with open(cache_file, 'r') as f:
                cached_recommendations = json.load(f)
            
            # Check if we have the new structured format with 'games' key
            if 'games' in cached_recommendations:
                logger.info("✅ Found structured cached recommendations with 'games' key")
                games_data = cached_recommendations['games']
            else:
                logger.info("✅ Found direct games dictionary format in cache")
                games_data = cached_recommendations
            
            # Convert to frontend format
            # formatted_recommendations = convert_to_frontend_format(games_data)  # TEMPORARILY DISABLED FOR DEBUG
            
            # Create raw recommendations that app.py expects
            raw_recommendations = {}
            frontend_recommendations = []
            
            for game_key, game_data in games_data.items():
                # Raw format that app.py can process
                raw_recommendations[game_key] = {
                    'away_team': game_data.get('away_team', ''),
                    'home_team': game_data.get('home_team', ''),
                    'predicted_score': game_data.get('predicted_score', 'N/A'),
                    'predicted_total_runs': game_data.get('predicted_total_runs', 0),
                    'win_probabilities': game_data.get('win_probabilities', {}),
                    'value_bets': game_data.get('value_bets', [])
                }
                
                # Frontend list that app.py might use
                for bet in game_data.get('value_bets', []):
                    frontend_recommendations.append({
                        'game': game_key,
                        'type': bet.get('type'),
                        'recommendation': bet.get('recommendation'),
                        'expected_value': bet.get('expected_value', 0),
                        'win_probability': bet.get('win_probability', 0),
                        'confidence': bet.get('confidence', 'medium'),
                        'american_odds': bet.get('american_odds', 'N/A'),
                        'reasoning': bet.get('reasoning', '')
                    })
            
            logger.info(f"DEBUG: raw recommendations: {raw_recommendations}")
            logger.info(f"DEBUG: frontend recommendations: {frontend_recommendations}")
            logger.info(f"✅ Cached betting integration complete: {len(raw_recommendations)} games processed")
            
            return raw_recommendations, frontend_recommendations
            
        except FileNotFoundError:
            logger.warning(f"No cached recommendations found at {cache_file}, generating fresh...")
            # Fallback to generating fresh recommendations - will continue to unified engine code below
            
        # Import the unified betting engine
        from unified_betting_engine import UnifiedBettingEngine
        
        # Initialize the engine
        logger.info("🔄 Initializing unified betting engine...")
        engine = UnifiedBettingEngine()
        
        # Get raw recommendations from unified engine
        logger.info("🔄 Calling unified engine generate_recommendations()...")
        raw_recommendations = engine.generate_recommendations()
        
        logger.info(f"DEBUG: unified engine raw recommendations type: {type(raw_recommendations)}")
        logger.info(f"DEBUG: unified engine raw keys: {list(raw_recommendations.keys()) if isinstance(raw_recommendations, dict) else 'Not a dict'}")
        
        # CRITICAL FIX: Handle structured response with 'games' key
        if isinstance(raw_recommendations, dict):
            # Check if we have the new structured format with 'games' key
            if 'games' in raw_recommendations:
                logger.info("✅ Found structured response with 'games' key - extracting games data")
                games_data = raw_recommendations['games']
                logger.info(f"DEBUG: games_data type: {type(games_data)}")
                logger.info(f"DEBUG: games_data keys: {list(games_data.keys()) if isinstance(games_data, dict) else 'Not a dict'}")
            else:
                logger.info("✅ Found direct games dictionary format")
                games_data = raw_recommendations
        else:
            logger.warning("⚠️ Unexpected recommendation format - using empty dict")
            games_data = {}
        
        # Convert to frontend format
        # formatted_recommendations = convert_to_frontend_format(games_data)  # TEMPORARILY DISABLED FOR DEBUG
        
        # Create raw recommendations that app.py expects
        raw_recommendations = {}
        frontend_recommendations = []
        
        for game_key, game_data in games_data.items():
            logger.info(f"DEBUG: Processing game {game_key}")
            logger.info(f"DEBUG: Game data type: {type(game_data)}")
            logger.info(f"DEBUG: Game data keys: {list(game_data.keys()) if isinstance(game_data, dict) else 'Not a dict'}")
            
            # Raw format that app.py can process
            try:
                raw_recommendations[game_key] = {
                    'away_team': game_data.get('away_team', ''),
                    'home_team': game_data.get('home_team', ''),
                    'predicted_score': game_data.get('predicted_score', 'N/A'),
                    'predicted_total_runs': game_data.get('predicted_total_runs', 0),
                    'win_probabilities': game_data.get('win_probabilities', {}),
                    'value_bets': game_data.get('value_bets', [])
                }
                logger.info(f"DEBUG: Successfully processed raw data for {game_key}")
            except Exception as e:
                logger.error(f"DEBUG: Error processing raw data for {game_key}: {e}")
                continue
            
            # Frontend list that app.py might use
            try:
                for bet in game_data.get('value_bets', []):
                    frontend_recommendations.append({
                        'game': game_key,
                        'type': bet.get('type'),
                        'recommendation': bet.get('recommendation'),
                        'expected_value': bet.get('expected_value', 0),
                        'win_probability': bet.get('win_probability', 0),
                        'confidence': bet.get('confidence', 'medium'),
                        'american_odds': bet.get('american_odds', 'N/A'),
                        'reasoning': bet.get('reasoning', '')
                    })
                logger.info(f"DEBUG: Successfully processed frontend data for {game_key}")
            except Exception as e:
                logger.error(f"DEBUG: Error processing frontend data for {game_key}: {e}")
                continue
        
        logger.info(f"DEBUG: raw recommendations: {raw_recommendations}")
        logger.info(f"DEBUG: frontend recommendations: {frontend_recommendations}")
        logger.info(f"✅ Fresh unified betting integration complete: {len(raw_recommendations)} games processed")
        
        return raw_recommendations, frontend_recommendations
        
    except Exception as e:
        logger.error(f"❌ Error in get_app_betting_recommendations: {e}")
        logger.error(f"❌ Error type: {type(e)}")
        if "'predictions'" in str(e):
            logger.error(f"❌ FOUND THE PREDICTIONS ERROR! Full traceback:")
            import traceback
            logger.error(traceback.format_exc())
        logger.error(f"❌ Traceback: ", exc_info=True)
        return {}, []

def convert_to_frontend_format(games_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert unified engine games data to frontend-compatible format
    
    Args:
        games_data: Dictionary of game data from unified engine
        
    Returns:
        Dictionary formatted for frontend consumption
    """
    try:
        if not games_data or not isinstance(games_data, dict):
            logger.warning("⚠️ No valid games data provided to convert_to_frontend_format")
            return {}
        
        formatted_games = {}
        
        for game_key, game_data in games_data.items():
            if not isinstance(game_data, dict):
                logger.warning(f"⚠️ Skipping invalid game data for {game_key}")
                continue
            
            # Extract team information
            away_team = game_data.get('away_team', '')
            home_team = game_data.get('home_team', '')
            
            if not away_team or not home_team:
                logger.warning(f"⚠️ Missing team data for {game_key}")
                continue
            
            # CRITICAL FIX: Get betting recommendations from the correct location
            # The cached data has value_bets directly at game level, not in betting_recommendations
            value_bets_array = game_data.get('value_bets', [])
            recommendations_array = game_data.get('recommendations', [])
            betting_recommendations = game_data.get('betting_recommendations', {})
            
            # Convert to the format expected by the API
            if value_bets_array and isinstance(value_bets_array, list):
                # Data already has value_bets format - just standardize the structure
                logger.info(f"✅ Found {len(value_bets_array)} value bets for {game_key}")
                formatted_betting = convert_value_bets_to_standard_format(value_bets_array)
            elif recommendations_array and isinstance(recommendations_array, list):
                # Convert from recommendations array format to value_bets format
                logger.info(f"🔄 Converting {len(recommendations_array)} recommendations for {game_key}")
                formatted_betting = convert_recommendations_array_to_value_bets(recommendations_array)
            elif betting_recommendations:
                # Check if we have the new value_bets format
                if 'value_bets' in betting_recommendations:
                    formatted_betting = betting_recommendations
                else:
                    # Convert old format to new format
                    formatted_betting = convert_legacy_betting_format(betting_recommendations)
            else:
                # No betting recommendations available
                formatted_betting = {
                    'value_bets': [],
                    'summary': 'No betting opportunities identified',
                    'total_bets': 0
                }
            
            # Store in the formatted games dictionary
            # Use the same key format as the input for consistency
            formatted_games[game_key] = {
                'away_team': away_team,
                'home_team': home_team,
                'betting_recommendations': formatted_betting,
                'raw_data': game_data  # Keep original data for debugging
            }
        
        logger.info(f"✅ Successfully converted {len(formatted_games)} games to frontend format")
        return formatted_games
        
    except Exception as e:
        logger.error(f"❌ Error in convert_to_frontend_format: {e}")
        return {}

def convert_value_bets_to_standard_format(value_bets_array: list) -> Dict[str, Any]:
    """
    Convert value_bets array to standard frontend format
    
    Args:
        value_bets_array: List of value bet objects from cached data
        
    Returns:
        Dictionary with standardized value_bets format
    """
    try:
        standardized_bets = []
        
        for bet in value_bets_array:
            if not isinstance(bet, dict):
                continue
                
            # Standardize the bet structure
            standardized_bet = {
                'bet_type': bet.get('type', 'Unknown').title(),
                'pick': bet.get('recommendation', ''),
                'confidence': bet.get('confidence', 'MEDIUM').upper(),
                'odds': bet.get('american_odds', 'N/A'),
                'reasoning': bet.get('reasoning', 'Value identified by model'),
                'edge': bet.get('edge', bet.get('expected_value', 0)),
                'expected_value': bet.get('expected_value', 0)
            }
            
            # Only add if there's a real pick
            if standardized_bet['pick']:
                standardized_bets.append(standardized_bet)
        
        # Create summary
        high_confidence_count = sum(1 for bet in standardized_bets if bet['confidence'] == 'HIGH')
        medium_confidence_count = sum(1 for bet in standardized_bets if bet['confidence'] == 'MEDIUM')
        low_confidence_count = sum(1 for bet in standardized_bets if bet['confidence'] == 'LOW')
        
        if high_confidence_count > 0 or medium_confidence_count > 0:
            summary = f"{high_confidence_count} high-confidence, {medium_confidence_count} medium-confidence"
            if low_confidence_count > 0:
                summary += f", {low_confidence_count} low-confidence opportunities"
            else:
                summary += " opportunities"
        else:
            summary = "No betting opportunities identified"
        
        return {
            'value_bets': standardized_bets,
            'summary': summary,
            'total_bets': len(standardized_bets)
        }
        
    except Exception as e:
        logger.error(f"❌ Error converting value bets to standard format: {e}")
        return {
            'value_bets': [],
            'summary': 'Error processing betting recommendations',
            'total_bets': 0
        }

def convert_recommendations_array_to_value_bets(recommendations_array: list) -> Dict[str, Any]:
    """
    Convert recommendations array format to value_bets format
    
    Args:
        recommendations_array: List of recommendation objects from cached data
        
    Returns:
        Dictionary with value_bets array format
    """
    try:
        value_bets = []
        
        for rec in recommendations_array:
            if not isinstance(rec, dict):
                continue
                
            # Skip "No Strong Value" recommendations
            if rec.get('bet') == 'No Strong Value' or rec.get('recommendation') == 'No clear value identified':
                continue
                
            # Convert recommendation to value bet format
            bet_type = rec.get('type', 'Unknown')
            pick = rec.get('bet', rec.get('recommendation', ''))
            confidence = rec.get('confidence', 'MEDIUM')
            reasoning = rec.get('reasoning', 'Value identified by model')
            
            # Only add if there's a real pick (not "No Strong Value", etc.)
            if pick and pick not in ['No Strong Value', 'No clear value identified', 'PASS']:
                value_bets.append({
                    'bet_type': bet_type,
                    'pick': pick,
                    'confidence': confidence,
                    'odds': rec.get('estimated_odds', 'N/A'),
                    'reasoning': reasoning,
                    'edge': rec.get('edge', 0),
                    'expected_value': rec.get('expected_value', 0)
                })
        
        # Create summary
        high_confidence_count = sum(1 for bet in value_bets if bet['confidence'] == 'HIGH')
        medium_confidence_count = sum(1 for bet in value_bets if bet['confidence'] == 'MEDIUM')
        
        if high_confidence_count > 0 or medium_confidence_count > 0:
            summary = f"{high_confidence_count} high-confidence, {medium_confidence_count} medium-confidence opportunities"
        else:
            summary = "No betting opportunities identified"
        
        return {
            'value_bets': value_bets,
            'summary': summary,
            'total_bets': len(value_bets)
        }
        
    except Exception as e:
        logger.error(f"❌ Error converting recommendations array: {e}")
        return {
            'value_bets': [],
            'summary': 'Error processing betting recommendations',
            'total_bets': 0
        }

def convert_legacy_betting_format(betting_recommendations: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert legacy betting recommendations format to new value_bets format
    
    Args:
        betting_recommendations: Legacy format betting recommendations
        
    Returns:
        New format with value_bets array
    """
    try:
        value_bets = []
        
        # Convert moneyline recommendation
        if 'moneyline' in betting_recommendations:
            moneyline = betting_recommendations['moneyline']
            if isinstance(moneyline, dict) and moneyline.get('pick') not in [None, 'PASS']:
                value_bets.append({
                    'bet_type': 'Moneyline',
                    'pick': moneyline.get('pick', ''),
                    'confidence': moneyline.get('confidence', 'MEDIUM'),
                    'odds': moneyline.get('odds', 'N/A'),
                    'reasoning': moneyline.get('reasoning', 'Statistical advantage identified')
                })
        
        # Convert total runs recommendation
        if 'total_runs' in betting_recommendations:
            total_runs = betting_recommendations['total_runs']
            if isinstance(total_runs, dict) and total_runs.get('recommendation', 'PASS') != 'PASS':
                value_bets.append({
                    'bet_type': 'Total Runs',
                    'pick': total_runs.get('recommendation', ''),
                    'confidence': total_runs.get('confidence', 'MEDIUM'),
                    'odds': total_runs.get('odds', 'N/A'),
                    'reasoning': total_runs.get('reasoning', 'Predicted total variance from market line')
                })
        
        # Convert run line recommendation
        if 'run_line' in betting_recommendations:
            run_line = betting_recommendations['run_line']
            if isinstance(run_line, dict) and run_line.get('recommendation'):
                value_bets.append({
                    'bet_type': 'Run Line',
                    'pick': run_line.get('recommendation', ''),
                    'confidence': run_line.get('confidence', 'MEDIUM'),
                    'odds': run_line.get('odds', 'N/A'),
                    'reasoning': run_line.get('reasoning', 'Spread value identified')
                })
        
        # Create summary
        high_confidence_count = sum(1 for bet in value_bets if bet['confidence'] == 'HIGH')
        medium_confidence_count = sum(1 for bet in value_bets if bet['confidence'] == 'MEDIUM')
        
        summary = f"{high_confidence_count} high-confidence, {medium_confidence_count} medium-confidence opportunities"
        
        return {
            'value_bets': value_bets,
            'summary': summary,
            'total_bets': len(value_bets)
        }
        
    except Exception as e:
        logger.error(f"❌ Error converting legacy betting format: {e}")
        return {
            'value_bets': [],
            'summary': 'Error processing betting recommendations',
            'total_bets': 0
        }

def load_betting_recommendations() -> Dict[str, Any]:
    """
    Load betting recommendations from cache file
    
    Returns:
        Dictionary of betting recommendations
    """
    try:
        with open('data/betting_recommendations_cache.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning("No betting recommendations cache file found")
        return {'games': {}}
    except Exception as e:
        logger.error(f"Error loading betting recommendations: {e}")
        return {'games': {}}

def load_real_betting_lines() -> Optional[Dict[str, Any]]:
    """
    Load real betting lines from cache file
    
    Returns:
        Dictionary of real betting lines or None if not available
    """
    try:
        with open('data/historical_betting_lines_cache.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning("No historical betting lines cache file found")
        return None
    except Exception as e:
        logger.error(f"Error loading real betting lines: {e}")
        return None

if __name__ == "__main__":
    # Test the integration
    recommendations, status = get_app_betting_recommendations()
    print(f"Status: {status}")
    print(f"Recommendations: {len(recommendations)} games")
    for game_key, game_data in recommendations.items():
        betting_recs = game_data.get('betting_recommendations', {})
        bet_count = len(betting_recs.get('value_bets', []))
        print(f"  {game_key}: {bet_count} betting opportunities")

def get_unified_betting_recommendations():
    """
    Legacy alias for get_app_betting_recommendations to maintain backward compatibility
    
    Returns:
        Same as get_app_betting_recommendations()
    """
    logger.info("🔄 get_unified_betting_recommendations called (legacy alias)")
    return get_app_betting_recommendations()
