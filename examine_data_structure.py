#!/usr/bin/env python3
"""
Test to examine the exact data structure returned by get_app_betting_recommendations
"""

import json
import sys
import logging

# Add the project root to the path
project_root = r'c:\Users\mostg\OneDrive\Coding\MLB-Betting'
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)

def examine_data_structure():
    """Examine the exact data structure returned by get_app_betting_recommendations"""
    try:
        logger.info("🔍 Testing get_app_betting_recommendations data structure...")
        
        from app_betting_integration import get_app_betting_recommendations
        raw_recommendations, frontend_recommendations = get_app_betting_recommendations()
        
        logger.info(f"✅ Got {len(raw_recommendations)} raw recommendations")
        
        if raw_recommendations:
            # Get first game
            first_game_key = list(raw_recommendations.keys())[0]
            first_game_data = raw_recommendations[first_game_key]
            
            logger.info(f"📊 First game key: {first_game_key}")
            logger.info(f"📊 First game data keys: {list(first_game_data.keys())}")
            
            # Print the structure
            print("\n" + "="*60)
            print("STRUCTURE EXAMINATION")
            print("="*60)
            print(f"Raw recommendations type: {type(raw_recommendations)}")
            print(f"Number of games: {len(raw_recommendations)}")
            print(f"\nFirst game key: {first_game_key}")
            print(f"First game data type: {type(first_game_data)}")
            print(f"First game keys: {list(first_game_data.keys())}")
            
            # Check each expected field
            expected_fields = ['away_team', 'home_team', 'predictions', 'betting_recommendations']
            for field in expected_fields:
                if field in first_game_data:
                    print(f"✅ {field}: {type(first_game_data[field])}")
                    if field == 'betting_recommendations':
                        betting_recs = first_game_data[field]
                        print(f"   └─ betting_recommendations keys: {list(betting_recs.keys())}")
                        if 'value_bets' in betting_recs:
                            print(f"   └─ value_bets count: {len(betting_recs['value_bets'])}")
                else:
                    print(f"❌ {field}: MISSING")
            
            # Now try to replicate the exact processing from load_betting_recommendations
            print(f"\n{'='*60}")
            print("REPLICATING load_betting_recommendations PROCESSING")
            print("="*60)
            
            try:
                # This is the exact code from load_betting_recommendations
                for game_key, game_data in raw_recommendations.items():
                    print(f"\nProcessing game: {game_key}")
                    
                    # Try each field access that could fail
                    try:
                        away_team = game_data['away_team']
                        print(f"  ✅ away_team: {away_team}")
                    except KeyError as e:
                        print(f"  ❌ away_team KeyError: {e}")
                    
                    try:
                        home_team = game_data['home_team']
                        print(f"  ✅ home_team: {home_team}")
                    except KeyError as e:
                        print(f"  ❌ home_team KeyError: {e}")
                    
                    try:
                        predictions = game_data['predictions']
                        print(f"  ✅ predictions: {type(predictions)}")
                    except KeyError as e:
                        print(f"  ❌ predictions KeyError: {e}")
                    
                    try:
                        betting_recommendations = game_data.get('betting_recommendations', {})
                        value_bets = betting_recommendations.get('value_bets', [])
                        print(f"  ✅ value_bets: {len(value_bets)} bets")
                        
                        # Try processing each bet (this might be where the error occurs)
                        for i, bet in enumerate(value_bets):
                            print(f"    Bet {i+1}: {list(bet.keys())}")
                            # Check if bet has all expected keys
                            expected_bet_fields = ['type', 'recommendation', 'confidence', 'expected_value', 'american_odds', 'reasoning']
                            for bet_field in expected_bet_fields:
                                if bet_field in bet:
                                    print(f"      ✅ {bet_field}")
                                else:
                                    print(f"      ❌ {bet_field}: MISSING")
                                    
                    except Exception as e:
                        print(f"  ❌ betting_recommendations processing error: {e}")
                        import traceback
                        print(f"     Traceback: {traceback.format_exc()}")
                    
                    # Only process first game for debugging
                    break
                    
            except Exception as e:
                print(f"❌ Processing failed: {e}")
                import traceback
                print(f"Traceback: {traceback.format_exc()}")
            
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    logger.info("🚀 Starting data structure examination...")
    success = examine_data_structure()
    logger.info(f"🏁 Test result: {'✅ SUCCESS' if success else '❌ FAILED'}")
