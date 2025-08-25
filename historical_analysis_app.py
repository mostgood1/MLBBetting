#!/usr/bin/env python3
"""
Dedicated Historical Analysis Flask Application
Separate from main app.py to avoid route conflicts and provide clean separation of concerns
"""

import os
import sys
import json
import logging
import traceback
from datetime import datetime, timedelta
from flask import Flask, jsonify, render_template, request

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import our comprehensive historical analysis module
from comprehensive_historical_analysis import ComprehensiveHistoricalAnalyzer
# Import team assets utilities for logos and colors
from team_assets_utils import get_team_assets, get_team_logo
from team_name_normalizer import normalize_team_name

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
# Simple CORS headers for basic functionality
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE')
    return response

# Initialize the historical analyzer
try:
    historical_analyzer = ComprehensiveHistoricalAnalyzer()
    logger.info("✅ Historical analyzer initialized successfully")
except Exception as e:
    logger.error(f"❌ Failed to initialize historical analyzer: {e}")
    historical_analyzer = None

# ================================================================================
# ROUTES FOR HISTORICAL ANALYSIS
# ================================================================================

@app.route('/')
def home():
    """Home page for historical analysis app"""
    return render_template('historical_analysis.html')

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'Historical Analysis API',
        'timestamp': datetime.now().isoformat(),
        'analyzer_status': 'initialized' if historical_analyzer else 'failed'
    })

@app.route('/api/available-dates')
def api_available_dates():
    """API endpoint to get all available dates for historical analysis"""
    try:
        if not historical_analyzer:
            return jsonify({
                'success': False,
                'error': 'Historical analyzer not initialized',
                'dates': [],
                'count': 0
            })
        
        available_dates = historical_analyzer.get_available_dates()
        
        logger.info(f"Available dates request: Found {len(available_dates)} dates")
        
        return jsonify({
            'success': True,
            'dates': available_dates,
            'count': len(available_dates),
            'message': f'Found {len(available_dates)} dates with complete data since 8/15'
        })
        
    except Exception as e:
        logger.error(f"Error getting available dates: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e),
            'dates': [],
            'count': 0
        })

@app.route('/api/cumulative')
def api_cumulative_analysis():
    """API endpoint for cumulative historical analysis since 8/15"""
    try:
        if not historical_analyzer:
            return jsonify({
                'success': False,
                'error': 'Historical analyzer not initialized'
            })
        
        logger.info("Starting cumulative historical analysis...")
        cumulative_stats = historical_analyzer.get_cumulative_analysis()
        
        logger.info(f"Cumulative analysis complete: {cumulative_stats.get('total_dates_analyzed', 0)} dates analyzed")
        
        return jsonify({
            'success': True,
            'data': cumulative_stats,
            'message': f'Cumulative analysis complete: {cumulative_stats.get("total_dates_analyzed", 0)} dates analyzed'
        })
        
    except Exception as e:
        logger.error(f"Error in cumulative historical analysis: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Failed to generate cumulative historical analysis'
        })

def load_starting_pitchers_for_date(date: str) -> dict:
    """Load starting pitchers data for a specific date"""
    try:
        # Format date for filename (replace hyphens with underscores)
        date_formatted = date.replace('-', '_')
        file_path = f"{DATA_DIR}/starting_pitchers_{date_formatted}.json"
        
        if not os.path.exists(file_path):
            logger.warning(f"No starting pitchers file found for {date}: {file_path}")
            return {}
            
        with open(file_path, 'r') as f:
            data = json.load(f)
            
        # Convert to dictionary keyed by game_key for easy lookup
        pitchers_dict = {}
        for game in data.get('games', []):
            game_key = game.get('game_key', '')
            if game_key:
                pitchers_dict[game_key] = {
                    'away_pitcher': game.get('away_pitcher', 'TBD'),
                    'home_pitcher': game.get('home_pitcher', 'TBD'),
                    'away_team': game.get('away_team', ''),
                    'home_team': game.get('home_team', '')
                }
                
        logger.info(f"Loaded starting pitchers for {date}: {len(pitchers_dict)} games")
        return pitchers_dict
        
    except Exception as e:
        logger.error(f"Error loading starting pitchers for {date}: {e}")
        return {}

# Data directory path
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')

@app.route('/api/date/<date>')
def api_date_analysis(date):
    """API endpoint for historical analysis of a specific date"""
    try:
        if not historical_analyzer:
            return jsonify({
                'success': False,
                'error': 'Historical analyzer not initialized',
                'date': date
            })
        
        logger.info(f"Analyzing historical data for {date}...")
        date_analysis = historical_analyzer.get_date_analysis(date)
        
        if 'error' in date_analysis:
            return jsonify({
                'success': False,
                'error': date_analysis['error'],
                'date': date
            })
        
        logger.info(f"Date analysis complete for {date}")
        
        return jsonify({
            'success': True,
            'data': date_analysis,
            'message': f'Analysis complete for {date}'
        })
        
    except Exception as e:
        logger.error(f"Error in date historical analysis for {date}: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e),
            'date': date,
            'message': f'Failed to analyze {date}'
        })

@app.route('/api/today-games/<date>')
def api_today_games(date):
    """API endpoint to get today's games with predictions for date selection"""
    try:
        if not historical_analyzer:
            return jsonify({
                'success': False,
                'error': 'Historical analyzer not initialized',
                'games': [],
                'count': 0
            })
        
        # Load predictions for the date
        predictions = historical_analyzer.load_predictions_for_date(date)
        
        if not predictions:
            return jsonify({
                'success': False,
                'error': f'No predictions found for {date}',
                'games': [],
                'count': 0
            })
        
        # Load starting pitchers data for the date
        starting_pitchers = load_starting_pitchers_for_date(date)
        logger.info(f"Loaded starting pitchers data: {len(starting_pitchers)} games")
        
        # Convert predictions to game card format with enhanced data
        games = []
        
        # Load final scores for this date to show actual results
        final_scores = historical_analyzer.load_final_scores_for_date(date)
        
        for game_key, prediction in predictions.items():
            # Extract team names safely
            away_team = normalize_team_name(prediction.get('away_team', ''))
            home_team = normalize_team_name(prediction.get('home_team', ''))
            
            # Skip if we don't have team names
            if not away_team or not home_team:
                continue
            
            # Get team assets for logos and colors
            away_team_assets = get_team_assets(away_team)
            home_team_assets = get_team_assets(home_team)
            
            # Extract win probabilities from predictions - handle both old and new formats
            predictions = prediction.get('predictions', {})
            win_probabilities = prediction.get('win_probabilities', {})
            
            # Try new format first, then fall back to old format
            if win_probabilities:
                away_prob = win_probabilities.get('away_prob', 0.5)
                home_prob = win_probabilities.get('home_prob', 0.5)
            else:
                away_prob = predictions.get('away_win_prob', 0.5)
                home_prob = predictions.get('home_win_prob', 0.5)
            
            # Convert to percentages if needed
            if away_prob <= 1:
                away_prob *= 100
            if home_prob <= 1:
                home_prob *= 100
            
            # Try new format first, then old format for total runs
            predicted_total = prediction.get('predicted_total_runs', 0)
            if not predicted_total:
                predicted_total = predictions.get('predicted_total_runs', 0)
            
            # Extract betting recommendations - handle both old and new formats
            value_bets = prediction.get('value_bets', [])
            if not value_bets:
                value_bets = prediction.get('recommendations', [])
            
            # Extract pitcher names - try multiple sources for real names
            away_pitcher = prediction.get('away_pitcher', 'TBD')
            home_pitcher = prediction.get('home_pitcher', 'TBD')
            
            logger.info(f"DEBUG: Initial pitcher data for {away_team} @ {home_team}: away={away_pitcher}, home={home_pitcher}")
            
            # Try to get pitcher names from pitcher_info nested structure
            pitcher_info = prediction.get('pitcher_info', {})
            if pitcher_info:
                away_pitcher_from_info = pitcher_info.get('away_pitcher_name', pitcher_info.get('away_pitcher', ''))
                home_pitcher_from_info = pitcher_info.get('home_pitcher_name', pitcher_info.get('home_pitcher', ''))
                
                if away_pitcher_from_info and away_pitcher_from_info not in ['TBD', 'None', '']:
                    away_pitcher = away_pitcher_from_info
                    logger.info(f"DEBUG: Updated away pitcher from pitcher_info: {away_pitcher}")
                if home_pitcher_from_info and home_pitcher_from_info not in ['TBD', 'None', '']:
                    home_pitcher = home_pitcher_from_info
                    logger.info(f"DEBUG: Updated home pitcher from pitcher_info: {home_pitcher}")
            
            # Try to get pitcher names from starting pitchers data if still TBD
            if (away_pitcher in ['TBD', 'None', '', None] or home_pitcher in ['TBD', 'None', '', None]) and starting_pitchers:
                # Try multiple game key formats
                possible_keys = [
                    game_key,
                    f"{away_team} @ {home_team}",
                    f"{away_team}_vs_{home_team}",
                    f"{away_team} vs {home_team}"
                ]
                
                for key in possible_keys:
                    if key in starting_pitchers:
                        pitcher_data = starting_pitchers[key]
                        if away_pitcher in ['TBD', 'None', '', None] and pitcher_data.get('away_pitcher'):
                            away_pitcher = pitcher_data['away_pitcher']
                            logger.info(f"DEBUG: Updated away pitcher from starting_pitchers: {away_pitcher}")
                        if home_pitcher in ['TBD', 'None', '', None] and pitcher_data.get('home_pitcher'):
                            home_pitcher = pitcher_data['home_pitcher']
                            logger.info(f"DEBUG: Updated home pitcher from starting_pitchers: {home_pitcher}")
                        break
            
            # Clean up pitcher names - remove null/None values
            if away_pitcher in ['TBD', 'None', '', None]:
                away_pitcher = 'TBD'
            if home_pitcher in ['TBD', 'None', '', None]:
                home_pitcher = 'TBD'
                
            logger.info(f"FINAL: Pitchers for {away_team} @ {home_team}: {away_pitcher} vs {home_pitcher}")
            logger.info(f"DEBUG: Betting recommendations count: {len(value_bets)}")
            if len(value_bets) > 0:
                logger.info(f"DEBUG: First betting recommendation: {value_bets[0]}")
            
            # Get final score data if available
            normalized_key = f"{away_team}_vs_{home_team}"
            final_score = final_scores.get(normalized_key, {})
            
            # Check if game is final and get actual scores
            is_final = final_score.get('is_final', False)
            away_score = final_score.get('away_score', 0) if is_final else None
            home_score = final_score.get('home_score', 0) if is_final else None
            actual_total = final_score.get('total_runs', 0) if is_final else None
            actual_winner = final_score.get('winner', '') if is_final else None
            
            # Calculate prediction accuracy if game is final
            winner_correct = None
            total_diff = None
            if is_final and actual_winner:
                predicted_winner = away_team if away_prob > home_prob else home_team
                winner_correct = (predicted_winner == away_team and actual_winner == 'away') or \
                               (predicted_winner == home_team and actual_winner == 'home')
                if actual_total and predicted_total:
                    total_diff = abs(predicted_total - actual_total)
            
            # Evaluate betting recommendation correctness
            evaluated_bets = []
            correct_bets = 0
            total_bets = len(value_bets)
            
            for bet in value_bets:
                bet_copy = bet.copy()
                bet_copy['is_correct'] = None
                bet_copy['result_status'] = 'pending'
                
                if is_final:
                    if bet['type'] == 'total':
                        betting_line = bet.get('betting_line', 0)
                        if 'over' in bet['recommendation'].lower():
                            bet_copy['is_correct'] = actual_total > betting_line
                        elif 'under' in bet['recommendation'].lower():
                            bet_copy['is_correct'] = actual_total < betting_line
                    elif bet['type'] == 'moneyline':
                        if away_team.lower() in bet['recommendation'].lower():
                            bet_copy['is_correct'] = actual_winner == 'away'
                        elif home_team.lower() in bet['recommendation'].lower():
                            bet_copy['is_correct'] = actual_winner == 'home'
                    elif bet['type'] == 'spread':
                        # Handle spread betting (if we have spread data)
                        # This would need spread line information
                        pass
                    
                    # Set result status
                    if bet_copy['is_correct'] is True:
                        bet_copy['result_status'] = 'won'
                        correct_bets += 1
                    elif bet_copy['is_correct'] is False:
                        bet_copy['result_status'] = 'lost'
                    else:
                        bet_copy['result_status'] = 'pending'
                
                evaluated_bets.append(bet_copy)
            
            game_obj = {
                'game_id': game_key,
                'away_team': away_team,
                'home_team': home_team,
                'away_logo': get_team_logo(away_team),
                'home_logo': get_team_logo(home_team),
                'away_team_assets': away_team_assets,
                'home_team_assets': home_team_assets,
                'away_pitcher': away_pitcher,
                'home_pitcher': home_pitcher,
                'predicted_total_runs': predicted_total,
                'away_win_probability': round(away_prob, 2),
                'home_win_probability': round(home_prob, 2),
                'predicted_winner': away_team if away_prob > home_prob else home_team,
                'confidence': round(max(away_prob, home_prob), 2),
                'value_bets_count': len(value_bets),
                'has_betting_recommendations': len(value_bets) > 0,
                'betting_recommendations': evaluated_bets,  # Use evaluated bets with correctness
                'correct_bets': correct_bets,
                'total_bets': total_bets,
                'betting_accuracy': round((correct_bets / total_bets * 100), 2) if total_bets > 0 else None,
                'date': date,
                
                # Final score information
                'is_final': is_final,
                'away_score': away_score,
                'home_score': home_score,
                'actual_total': actual_total,
                'actual_winner': actual_winner,
                'winner_correct': winner_correct,
                'total_diff': round(total_diff, 2) if total_diff is not None else None,
                
                # Prediction vs actual comparison
                'has_final_score': is_final,
                'game_status': 'Final' if is_final else 'Scheduled'
            }
            
            games.append(game_obj)
        
        # Calculate daily summary statistics
        total_games = len(games)
        final_games = sum(1 for game in games if game['is_final'])
        
        # Win prediction accuracy
        correct_winners = sum(1 for game in games if game.get('winner_correct') is True)
        winner_accuracy = round((correct_winners / final_games * 100), 2) if final_games > 0 else 0
        
        # Betting recommendations summary
        total_bets_all_games = sum(game['total_bets'] for game in games)
        correct_bets_all_games = sum(game['correct_bets'] for game in games)
        overall_betting_accuracy = round((correct_bets_all_games / total_bets_all_games * 100), 2) if total_bets_all_games > 0 else 0
        
        # Total accuracy (average total prediction difference)
        total_diffs = [game.get('total_diff') for game in games if game.get('total_diff') is not None]
        avg_total_diff = round(sum(total_diffs) / len(total_diffs), 2) if total_diffs else 0
        
        # Games with betting recommendations
        games_with_bets = sum(1 for game in games if game['has_betting_recommendations'])
        
        daily_summary = {
            'date': date,
            'total_games': total_games,
            'final_games': final_games,
            'pending_games': total_games - final_games,
            'winner_accuracy': winner_accuracy,
            'correct_winners': correct_winners,
            'total_bets': total_bets_all_games,
            'correct_bets': correct_bets_all_games,
            'betting_accuracy': overall_betting_accuracy,
            'games_with_bets': games_with_bets,
            'avg_total_diff': avg_total_diff,
            'performance_grade': 'A' if overall_betting_accuracy >= 70 else 'B' if overall_betting_accuracy >= 60 else 'C' if overall_betting_accuracy >= 50 else 'D'
        }
        
        logger.info(f"Today games for {date}: {len(games)} games found")
        
        return jsonify({
            'success': True,
            'games': games,
            'count': len(games),
            'date': date,
            'daily_summary': daily_summary,
            'message': f'Found {len(games)} games for {date}'
        })
        
    except Exception as e:
        logger.error(f"Error getting today games for {date}: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e),
            'games': [],
            'count': 0,
            'date': date
        })

@app.route('/api/roi-summary')
def api_roi_summary():
    """API endpoint for ROI summary with $100 bet calculations"""
    try:
        if not historical_analyzer:
            return jsonify({
                'success': False,
                'error': 'Historical analyzer not initialized'
            })
        
        logger.info("Calculating ROI summary...")
        
        # Get cumulative analysis which includes ROI calculations
        cumulative_data = historical_analyzer.get_cumulative_analysis()
        
        # Extract ROI-specific data
        roi_data = {
            'total_investment': cumulative_data.get('betting_analysis', {}).get('total_investment', 0),
            'total_winnings': cumulative_data.get('betting_analysis', {}).get('total_winnings', 0),
            'net_profit': cumulative_data.get('betting_analysis', {}).get('net_profit', 0),
            'roi_percentage': cumulative_data.get('betting_analysis', {}).get('roi_percentage', 0),
            'total_bets': cumulative_data.get('betting_analysis', {}).get('total_bets', 0),
            'winning_bets': cumulative_data.get('betting_analysis', {}).get('winning_bets', 0),
            'win_rate': cumulative_data.get('betting_analysis', {}).get('win_rate', 0),
            'bet_type_breakdown': cumulative_data.get('betting_analysis', {}).get('bet_type_performance', {}),
            'confidence_breakdown': cumulative_data.get('betting_analysis', {}).get('confidence_performance', {}),
            'dates_analyzed': cumulative_data.get('total_dates_analyzed', 0),
            'period': f"Since 8/15 ({cumulative_data.get('total_dates_analyzed', 0)} days)"
        }
        
        logger.info(f"ROI summary complete: {roi_data['total_bets']} bets, {roi_data['roi_percentage']:.1f}% ROI")
        
        return jsonify({
            'success': True,
            'data': roi_data,
            'message': f'ROI analysis complete: {roi_data["total_bets"]} total bets with {roi_data["roi_percentage"]:.1f}% ROI'
        })
        
    except Exception as e:
        logger.error(f"Error calculating ROI summary: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Failed to calculate ROI summary'
        })

@app.route('/api/model-performance')
def api_model_performance():
    """API endpoint for model performance metrics"""
    try:
        if not historical_analyzer:
            return jsonify({
                'success': False,
                'error': 'Historical analyzer not initialized'
            })
        
        logger.info("Calculating model performance metrics...")
        
        # Get cumulative analysis
        cumulative_data = historical_analyzer.get_cumulative_analysis()
        
        # Extract model performance data
        model_data = {
            'total_games': cumulative_data.get('model_performance', {}).get('total_games_analyzed', 0),
            'games_with_results': cumulative_data.get('model_performance', {}).get('games_with_final_scores', 0),
            'winner_accuracy': cumulative_data.get('model_performance', {}).get('winner_prediction_accuracy', 0),
            'total_accuracy': cumulative_data.get('model_performance', {}).get('total_prediction_accuracy', 0),
            'average_score_difference': cumulative_data.get('model_performance', {}).get('average_score_difference', 0),
            'total_runs_accuracy': cumulative_data.get('model_performance', {}).get('total_runs_accuracy', 0),
            'confidence_breakdown': cumulative_data.get('model_performance', {}).get('confidence_level_performance', {}),
            'daily_performance': cumulative_data.get('daily_breakdown', []),
            'dates_analyzed': cumulative_data.get('total_dates_analyzed', 0)
        }
        
        logger.info(f"Model performance complete: {model_data['winner_accuracy']:.1f}% winner accuracy")
        
        return jsonify({
            'success': True,
            'data': model_data,
            'message': f'Model performance analysis complete: {model_data["winner_accuracy"]:.1f}% winner accuracy over {model_data["dates_analyzed"]} days'
        })
        
    except Exception as e:
        logger.error(f"Error calculating model performance: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Failed to calculate model performance'
        })

# ================================================================================
# ERROR HANDLERS
# ================================================================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'error': 'Endpoint not found',
        'message': 'The requested endpoint does not exist',
        'available_endpoints': [
            '/health',
            '/api/available-dates',
            '/api/cumulative',
            '/api/date/<date>',
            '/api/today-games/<date>',
            '/api/roi-summary',
            '/api/model-performance'
        ]
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'success': False,
        'error': 'Internal server error',
        'message': 'An unexpected error occurred'
    }), 500

# ================================================================================
# MAIN APPLICATION STARTUP
# ================================================================================

if __name__ == '__main__':
    logger.info("🏟️ Starting Historical Analysis Flask Application")
    logger.info("📊 Dedicated service for MLB prediction historical analysis")
    
    # Verify historical analyzer is working
    if historical_analyzer:
        try:
            available_dates = historical_analyzer.get_available_dates()
            logger.info(f"✅ Historical analyzer ready: {len(available_dates)} dates available")
        except Exception as e:
            logger.error(f"❌ Historical analyzer test failed: {e}")
    else:
        logger.error("❌ Historical analyzer not initialized - some endpoints will fail")
    
    # Use PORT environment variable for Render deployment, fallback for local development
    port = int(os.environ.get('PORT', os.environ.get('HISTORICAL_PORT', 5001)))
    debug_mode = os.environ.get('FLASK_ENV') != 'production'
    
    logger.info(f"🚀 Starting Historical Analysis App on port {port} (debug: {debug_mode})")
    logger.info(f"📍 Access at: http://localhost:{port}")
    logger.info(f"🔍 Health check: http://localhost:{port}/health")
    logger.info(f"📅 Available dates: http://localhost:{port}/api/available-dates")
    
    app.run(debug=debug_mode, host='0.0.0.0', port=port)
