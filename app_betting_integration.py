#!/usr/bin/env python3
"""
App Integration for Unified Betting Engine
==========================================

Simple integration layer for Flask app to use the unified betting engine.
Provides a single function that app.py can call to get clean betting recommendations.

Author: AI Assistant  
Created: 2025-08-19
"""

import json
import os
import logging
from datetime import datetime
from unified_betting_engine import UnifiedBettingEngine

# Configure logging
logger = logging.getLogger(__name__)

def get_unified_betting_recommendations():
    """
    Single function for app.py to get clean betting recommendations.
    Returns properly formatted recommendations using only real betting lines.
    
    Returns:
        Dict: Betting recommendations or empty dict if none available
    """
    try:
        logger.info("🎯 Getting unified betting recommendations for app...")
        
        # Initialize unified engine
        engine = UnifiedBettingEngine()
        
        # Generate recommendations
        recommendations = engine.generate_recommendations()
        
        if not recommendations or 'games' not in recommendations:
            logger.warning("⚠️ No recommendations generated")
            return {}
        
        # Format for app consumption
        formatted_recommendations = {}
        total_value_bets = 0
        
        for game_key, game_data in recommendations['games'].items():
            if 'value_bets' in game_data and game_data['value_bets']:
                formatted_recommendations[game_key] = {
                    'away_team': game_data.get('away_team', ''),
                    'home_team': game_data.get('home_team', ''),
                    'predictions': {
                        'away_win_prob': game_data['win_probabilities']['away_prob'],
                        'home_win_prob': game_data['win_probabilities']['home_prob'],
                        'predicted_total': game_data.get('predicted_total_runs', 0)
                    },
                    'recommendations': game_data['value_bets']
                }
                total_value_bets += len(game_data['value_bets'])
        
        logger.info(f"✅ Unified engine found {total_value_bets} value bets across {len(formatted_recommendations)} games")
        return formatted_recommendations
        
    except Exception as e:
        logger.error(f"❌ Unified betting engine failed: {e}")
        return {}

def convert_to_frontend_format(recommendations):
    """
    Convert unified recommendations to frontend display format.
    
    Args:
        recommendations (Dict): Output from get_unified_betting_recommendations()
        
    Returns:
        List: Frontend-formatted betting recommendations
    """
    frontend_recommendations = []
    
    for game_key, game_data in recommendations.items():
        for bet in game_data.get('recommendations', []):
            # Convert to frontend format
            frontend_bet = {
                'game': f"{game_data['away_team']} @ {game_data['home_team']}",
                'type': bet['type'],
                'recommendation': bet['recommendation'],
                'confidence': bet['confidence'],
                'expected_value': bet.get('expected_value', 0),
                'win_probability': bet.get('win_probability', 0),
                'american_odds': bet.get('american_odds', ''),
                'reasoning': bet.get('reasoning', ''),
                'source': 'Unified Engine v1.0'
            }
            
            # Add bet-specific fields
            if bet['type'] == 'total':
                frontend_bet.update({
                    'predicted_total': bet.get('predicted_total', 0),
                    'betting_line': bet.get('betting_line', 0)
                })
            
            frontend_recommendations.append(frontend_bet)
    
    # Sort by expected value
    frontend_recommendations.sort(key=lambda x: x.get('expected_value', 0), reverse=True)
    
    return frontend_recommendations

# Example usage for app.py
def get_app_betting_recommendations():
    """
    Main function for app.py to get betting recommendations.
    Returns both raw and frontend-formatted recommendations.
    
    Returns:
        Tuple: (raw_recommendations, frontend_recommendations)
    """
    try:
        # Get unified recommendations
        raw_recommendations = get_unified_betting_recommendations()
        
        if not raw_recommendations:
            return {}, []
        
        # Convert to frontend format
        frontend_recommendations = convert_to_frontend_format(raw_recommendations)
        
        logger.info(f"🎯 App integration: {len(frontend_recommendations)} recommendations ready")
        return raw_recommendations, frontend_recommendations
        
    except Exception as e:
        logger.error(f"❌ App integration failed: {e}")
        return {}, []

if __name__ == "__main__":
    # Test the integration
    raw, frontend = get_app_betting_recommendations()
    print(f"Raw recommendations: {len(raw)} games")
    print(f"Frontend recommendations: {len(frontend)} bets")
    
    if frontend:
        print("\nSample recommendation:")
        print(json.dumps(frontend[0], indent=2))
