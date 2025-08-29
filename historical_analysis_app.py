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
from pathlib import Path
from flask import Flask, jsonify, render_template, request

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import our comprehensive historical analysis module
from comprehensive_historical_analysis import ComprehensiveHistoricalAnalyzer
# Import team assets utilities for logos and colors
from team_assets_utils import get_team_assets, get_team_logo
from team_name_normalizer import normalize_team_name
# Import enhanced betting analytics for three-view system
from redesigned_betting_analytics import RedesignedBettingAnalytics

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
    enhanced_analytics = RedesignedBettingAnalytics()
    logger.info("✅ Historical analyzer and enhanced analytics initialized successfully")
except Exception as e:
    logger.error(f"❌ Failed to initialize analytics systems: {e}")
    historical_analyzer = None
    enhanced_analytics = None

# ================================================================================
# ROUTES FOR HISTORICAL ANALYSIS
# ================================================================================

@app.route('/')
def home():
    """Home page with redesigned three-tab analytics"""
    return render_template('redesigned_analytics.html')

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
            
            # Extract win probabilities
            win_probs = prediction.get('win_probabilities', {})
            away_prob = win_probs.get('away_prob', 0.5)
            home_prob = win_probs.get('home_prob', 0.5)
            
            # Convert to percentages if needed
            if away_prob <= 1:
                away_prob *= 100
            if home_prob <= 1:
                home_prob *= 100
            
            predicted_total = prediction.get('predicted_total_runs', 0)
            
            # Extract betting recommendations if available
            betting_recs = prediction.get('betting_recommendations', {})
            value_bets = betting_recs.get('value_bets', [])
            
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
                'betting_recommendations': value_bets,  # Include full betting recommendations
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
        
        logger.info(f"Today games for {date}: {len(games)} games found")
        
        return jsonify({
            'success': True,
            'games': games,
            'count': len(games),
            'date': date,
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
        
        # Prefer file-based evaluation for ROI to align with recommendations card
        try:
            files_eval = historical_analyzer.analyze_betting_files()
        except Exception:
            files_eval = None

        roi_data = {}
        if files_eval and files_eval.get('betting_performance', {}).get('total_recommendations', 0) > 0:
            bp = files_eval['betting_performance']
            total_bets = bp.get('total_recommendations', 0)
            winning_bets = bp.get('correct_recommendations', 0)
            win_rate = round((winning_bets / total_bets) * 100, 2) if total_bets > 0 else 0
            roi_data = {
                'total_investment': bp.get('total_bet_amount', 0),
                'total_winnings': bp.get('total_winnings', 0),
                'net_profit': bp.get('net_profit', 0),
                'roi_percentage': bp.get('roi_percentage', 0),
                'total_bets': total_bets,
                'winning_bets': winning_bets,
                'win_rate': win_rate,
                'bet_type_breakdown': {
                    'moneyline': bp.get('moneyline_stats', {}),
                    'totals': bp.get('total_stats', {}),
                    'runline': bp.get('runline_stats', {})
                },
                'confidence_breakdown': {},
                'dates_analyzed': historical_analyzer.get_available_dates().__len__(),
                'period': f"Since {historical_analyzer.start_date} ({historical_analyzer.get_available_dates().__len__()} days)"
            }
        else:
            # Fallback to cumulative analysis (predictions-based) if file-based is unavailable
            cumulative_data = historical_analyzer.get_cumulative_analysis()
            roi_data = {
                'total_investment': cumulative_data.get('betting_performance', {}).get('total_bet_amount', 0),
                'total_winnings': cumulative_data.get('betting_performance', {}).get('total_winnings', 0),
                'net_profit': cumulative_data.get('betting_performance', {}).get('net_profit', 0),
                'roi_percentage': cumulative_data.get('betting_performance', {}).get('roi_percentage', 0),
                'total_bets': cumulative_data.get('betting_performance', {}).get('total_recommendations', 0),
                'winning_bets': cumulative_data.get('betting_performance', {}).get('correct_recommendations', 0),
                'win_rate': cumulative_data.get('betting_performance', {}).get('overall_accuracy', 0),
                'bet_type_breakdown': {
                    'moneyline': cumulative_data.get('betting_performance', {}).get('moneyline_stats', {}),
                    'totals': cumulative_data.get('betting_performance', {}).get('total_stats', {}),
                    'runline': cumulative_data.get('betting_performance', {}).get('runline_stats', {})
                },
                'confidence_breakdown': {},
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

@app.route('/api/kelly-betting-guidance')
def api_kelly_betting_guidance():
    """API endpoint for Kelly Criterion betting guidance"""
    try:
        # Import the betting guidance system
        from betting_guidance_system import BettingGuidanceSystem
        
        logger.info("Generating Kelly Criterion betting guidance...")
        
        # Initialize the betting guidance system
        betting_guidance = BettingGuidanceSystem()
        
        # Get historical performance by bet type
        historical_performance = betting_guidance.get_historical_performance_by_bet_type()
        
        # Get today's opportunities (if available)
        try:
            todays_opportunities = betting_guidance.get_todays_betting_opportunities()
        except Exception as e:
            logger.warning(f"Could not get today's opportunities: {e}")
            todays_opportunities = {'opportunities': [], 'total_recommended_investment': 0}
        
        # Generate comprehensive report
        guidance_data = {
            'historical_performance': historical_performance,
            'todays_opportunities': todays_opportunities,
            'system_status': {
                'total_bet_types_analyzed': len(historical_performance),
                'base_unit': betting_guidance.base_unit,
                'analysis_period': 'Since 8/15/2025'
            },
            'recommendations': {
                'high_confidence_types': [bt for bt, perf in historical_performance.items() 
                                        if perf.get('recommendation') == 'HIGHLY_RECOMMENDED'],
                'recommended_types': [bt for bt, perf in historical_performance.items() 
                                    if perf.get('recommendation') == 'RECOMMENDED'],
                'avoid_types': [bt for bt, perf in historical_performance.items() 
                              if perf.get('recommendation') == 'AVOID']
            }
        }
        
        logger.info(f"Kelly guidance complete: {len(historical_performance)} bet types analyzed")
        
        return jsonify({
            'success': True,
            'data': guidance_data,
            'message': f'Kelly Criterion guidance generated for {len(historical_performance)} bet types'
        })
        
    except Exception as e:
        logger.error(f"Error generating Kelly betting guidance: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Failed to generate Kelly betting guidance'
        })

def convert_daily_breakdown_to_performance(daily_breakdown):
    """Convert daily breakdown data to performance format expected by frontend"""
    performance = {}
    
    for date, day_data in daily_breakdown.items():
        # Convert model performance data to betting performance format
        total_games = day_data.get('games_analyzed', 0)
        wins = day_data.get('winner_predictions_correct', 0)
        
        # Calculate basic metrics
        win_rate = (wins / total_games * 100) if total_games > 0 else 0
        
        # For now, simulate ROI and profit based on win rate
        # This is a placeholder - in a real system you'd have actual betting data
        roi = (win_rate - 50) * 2  # Simple ROI calculation
        net_profit = roi * total_games if total_games > 0 else 0
        
        performance[date] = {
            'total_bets': total_games,
            'wins': wins,
            'roi': roi,
            'net_profit': net_profit
        }
    
    return performance

@app.route('/api/system-performance-overview')
def api_system_performance_overview():
    """API endpoint for System Performance Overview - Complete model accuracy"""
    try:
        logger.info("Generating System Performance Overview...")
        
        if not enhanced_analytics:
            return jsonify({
                'error': 'Enhanced analytics not initialized',
                'data': {},
                'message': 'System initialization failed'
            }), 500
        
        # Use model performance analysis as system overview
        model_performance = enhanced_analytics.get_model_performance_analysis()
        
        if not model_performance.get('success'):
            return jsonify({
                'error': 'Failed to get model performance data',
                'data': {},
                'message': 'Model performance analysis failed'
            }), 500
        
        # Extract overview data from model performance
        data = model_performance.get('data', {})
        overall_stats = data.get('overall_stats', {})

        # Also pull betting recommendation performance, preferring direct evaluation from betting_recommendations files
        try:
            files_eval = enhanced_analytics.historical_analyzer.analyze_betting_files()
            betting_perf = (files_eval or {}).get('betting_performance', {})
            raw_total = (files_eval or {}).get('raw_total_found', 0)
        except Exception:
            # Fallback to cumulative analyzer + raw recommendation counter
            try:
                cumulative = enhanced_analytics._get_cached_cumulative_analysis() if hasattr(enhanced_analytics, '_get_cached_cumulative_analysis') else enhanced_analytics.historical_analyzer.get_cumulative_analysis()
            except Exception:
                cumulative = {}
            betting_perf = (cumulative or {}).get('betting_performance', {})
            try:
                raw_total, _ = enhanced_analytics.historical_analyzer.count_all_recommendations()
            except Exception:
                raw_total = betting_perf.get('total_recommendations', 0)
        
        overview_data = {
            'overview': {
                'total_predictions': overall_stats.get('total_games', 0),
                'overall_accuracy': overall_stats.get('winner_accuracy', 0),  # Map winner_accuracy to overall_accuracy
                'winner_accuracy': overall_stats.get('winner_accuracy', 0),
                'total_accuracy_1': overall_stats.get('totals_within_1_pct', 0),
                'total_accuracy_2': overall_stats.get('totals_within_2_pct', 0),
                'home_runs_accuracy_1': overall_stats.get('home_team_runs_accuracy_1', 0),
                'away_runs_accuracy_1': overall_stats.get('away_team_runs_accuracy_1', 0),
                'home_runs_accuracy_2': overall_stats.get('home_team_runs_accuracy_2', 0),
                'away_runs_accuracy_2': overall_stats.get('away_team_runs_accuracy_2', 0)
            },
            'predictionTypes': {
                'total': overall_stats.get('total_games', 0),  # Use total games as total bets
                'spread': overall_stats.get('total_games', 0),  # For now, use total games as spread count
                'moneyline': overall_stats.get('total_games', 0),  # For now, use total games as moneyline count
                'accuracy_by_type': {
                    'total': overall_stats.get('totals_within_1_pct', 0)  # Use totals accuracy
                }
            },
            'bettingRecommendations': {
                # total_recommended now reflects all recs found; evaluated_recommended are those we could grade
                'total_recommended': raw_total,
                'evaluated_recommended': betting_perf.get('total_recommendations', 0),
                'moneyline_accuracy': betting_perf.get('moneyline_stats', {}).get('accuracy', 0),
                'runline_accuracy': betting_perf.get('runline_stats', {}).get('accuracy', 0),
                'totals_accuracy': betting_perf.get('total_stats', {}).get('accuracy', 0)
            },
            'dailyPerformance': convert_daily_breakdown_to_performance(data.get('daily_breakdown', {})),
            'date_range': data.get('date_range', {}),
            'daily_breakdown': data.get('daily_breakdown', [])
        }
        
        logger.info(f"System overview complete: {overview_data['overview']['total_predictions']} predictions analyzed")
        
        return jsonify({
            'success': True,
            'data': overview_data,
            'message': f'System performance overview generated'
        })
        
    except Exception as e:
        logger.error(f"Error generating system performance overview: {e}")
        traceback.print_exc()
        return jsonify({
            'error': str(e),
            'data': {},
            'message': 'Failed to generate system performance overview'
        }), 500

@app.route('/api/historical-kelly-performance')
def api_historical_kelly_performance():
    """API endpoint for Historical Kelly Performance - Actual betting results"""
    try:
        logger.info("Generating Historical Kelly Performance...")
        
        if not enhanced_analytics:
            return jsonify({
                'error': 'Enhanced analytics not initialized',
                'data': {},
                'message': 'System initialization failed'
            }), 500
        
        days_back = int(request.args.get('days', 14))
        kelly_raw_data = enhanced_analytics.get_kelly_best_of_best_performance()
        
        # Transform data structure for frontend compatibility
        kelly_actual_data = kelly_raw_data.get('data', {})
        daily_summary = kelly_actual_data.get('daily_summary', {})
        overall_stats = kelly_actual_data.get('overall_stats', {})
        
        # Map daily data to expected frontend structure
        mapped_daily_performance = {}
        for date, day_data in daily_summary.items():
            mapped_daily_performance[date] = {
                'total_bets': day_data.get('bets', 0),
                'wins': day_data.get('wins', 0),
                'losses': day_data.get('losses', 0),
                'roi': day_data.get('roi', 0),
                'net_profit': day_data.get('profit', 0),
                'invested': day_data.get('invested', 0)
            }
        
        # Map to expected frontend structure
        kelly_data = {
            'daily_performance': mapped_daily_performance,
            'summary': {
                'total_bets': overall_stats.get('total_kelly_bets', 0),
                'win_rate': overall_stats.get('win_rate', 0),
                'overall_roi': overall_stats.get('roi', 0),
                'net_profit': overall_stats.get('total_profit', 0)
            }
        }
        
        logger.info(f"Kelly performance complete: {overall_stats.get('total_kelly_bets', 0)} Kelly bets analyzed")
        
        return jsonify({
            'success': True,
            'data': kelly_data,
            'message': f'Historical Kelly performance generated'
        })
        
    except Exception as e:
        logger.error(f"Error generating historical Kelly performance: {e}")
        traceback.print_exc()
        return jsonify({
            'error': str(e),
            'data': {},
            'message': 'Failed to generate historical Kelly performance'
        }), 500

@app.route('/api/todays-opportunities')
def api_todays_opportunities():
    """API endpoint for Today's Opportunities - Live Kelly recommendations"""
    try:
        logger.info("Generating Today's Opportunities...")
        
        if not enhanced_analytics:
            return jsonify({
                'error': 'Enhanced analytics not initialized',
                'data': {},
                'message': 'System initialization failed'
            }), 500
        
        # Get today's date
        today_str = datetime.now().strftime('%Y-%m-%d')
        
    # Get today's Kelly recommendations from unified cache
        try:
            unified_cache_path = Path(__file__).parent / 'data' / 'unified_predictions_cache.json'
            with open(unified_cache_path, 'r') as f:
                cache_data = json.load(f)
            
            # Get today's predictions
            predictions_by_date = cache_data.get('predictions_by_date', {})
            today_data = predictions_by_date.get(today_str, {})
            today_games = today_data.get('games', {})
            
            # Extract Kelly opportunities from today's games
            kelly_opportunities = []
            # Betting unit configuration (overridable via query params): default $100 unit and 2x cap
            try:
                base_unit = int(request.args.get('unit') or request.args.get('unit_size') or 100)
            except Exception:
                base_unit = 100
            try:
                max_units = float(request.args.get('max_units') or 2)
            except Exception:
                max_units = 2
            bankroll_proxy = base_unit * 10  # align with prior guidance using ~$1,000 when unit=$100
            
            for game_key, game_data in today_games.items():
                recommendations = game_data.get('recommendations', [])
                
                for rec in recommendations:
                    # Only include recommendations with Kelly bet size >= 5% and HIGH confidence
                    kelly_size = rec.get('kelly_bet_size', 0)
                    confidence = rec.get('confidence', '').upper()
                    
                    if kelly_size >= 5.0 and confidence == 'HIGH':
                        # Convert Kelly % to fraction
                        kelly_fraction = (kelly_size or 0) / 100.0
                        # Dollar sizing: fraction of bankroll proxy, rounded to $10s, capped to 2x unit
                        kelly_amount = kelly_fraction * bankroll_proxy
                        suggested_bet = max(10, min(round(kelly_amount / 10) * 10, int(base_unit * max_units)))
                        opportunity = {
                            'date': today_str,
                            'game': f"{game_data.get('away_team')} vs {game_data.get('home_team')}",
                            'bet_type': 'Over/Under' if rec.get('type') == 'total' else rec.get('type', '').title(),
                            'bet_details': f"{rec.get('side', '').title()} {rec.get('line', '')} runs" if rec.get('type') == 'total' else f"{rec.get('side', '')} {rec.get('line', '')}",
                            'confidence': kelly_fraction,  # decimal
                            'kelly_percentage': kelly_size,
                            'recommended_bet': int(suggested_bet),
                            'expected_value': rec.get('expected_value', 0),
                            'edge': rec.get('edge', 0),
                            'reasoning': rec.get('reasoning', ''),
                            'odds': rec.get('odds', 0),
                            'model_prediction': rec.get('model_total', 0) if rec.get('type') == 'total' else None
                        }
                        kelly_opportunities.append(opportunity)
            
            opportunities_data = {
                'total_opportunities': len(kelly_opportunities),
                'opportunities': kelly_opportunities,
                'date': today_str
            }
            
        except Exception as e:
            logger.error(f"Error loading today's Kelly opportunities: {e}")
            # Fallback to Kelly betting recommendations file
            kelly_raw_data = enhanced_analytics.get_kelly_best_of_best_performance()
            kelly_actual_data = kelly_raw_data.get('data', {})
            individual_bets = kelly_actual_data.get('individual_bets', [])
            today_opportunities = [bet for bet in individual_bets if bet.get('date') == today_str]
            
            opportunities_data = {
                'total_opportunities': len(today_opportunities),
                'opportunities': today_opportunities,
                'date': today_str
            }
        
        logger.info(f"Today's opportunities complete: {opportunities_data['total_opportunities']} Kelly opportunities found")
        
        return jsonify({
            'success': True,
            'data': opportunities_data,
            'message': f"Today's opportunities generated: {opportunities_data['total_opportunities']} total"
        })
        
    except Exception as e:
        logger.error(f"Error generating today's opportunities: {e}")
        traceback.print_exc()
        return jsonify({
            'error': str(e),
            'data': {},
            'message': 'Failed to generate today\'s opportunities'
        }), 500

@app.route('/api/betting-evaluation-gaps')
def api_betting_evaluation_gaps():
    """API endpoint to diagnose why some recommendations aren't evaluated"""
    try:
        if not enhanced_analytics:
            return jsonify({
                'success': False,
                'error': 'Enhanced analytics not initialized'
            }), 500

        gaps = enhanced_analytics.historical_analyzer.analyze_betting_files_gaps()
        return jsonify({
            'success': True,
            'data': gaps
        })
    except Exception as e:
        logger.error(f"Error generating betting evaluation gaps: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/missing-side-examples')
def api_missing_side_examples():
    """Return sample recommendations that are missing a resolvable 'side'"""
    try:
        limit = int(request.args.get('limit', 20))
        examples = enhanced_analytics.historical_analyzer.get_missing_side_examples(limit=limit)
        return jsonify({'success': True, 'count': len(examples), 'examples': examples})
    except Exception as e:
        logger.error(f"Error getting missing side examples: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/evaluation-gap-samples')
def api_evaluation_gap_samples():
    """Return detailed examples of skipped recommendations grouped by reason."""
    try:
        reason = request.args.get('reason')  # e.g., 'missing_side', 'no_final_score_for_game'
        limit = int(request.args.get('limit', 50))
        samples = enhanced_analytics.historical_analyzer.collect_gap_samples(reason_filter=reason, limit=limit)
        return jsonify({'success': True, 'samples': samples})
    except Exception as e:
        logger.error(f"Error getting evaluation gap samples: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ================================================================================
# NEW THREE-TAB ANALYTICS ENDPOINTS
# ================================================================================

@app.route('/api/model-performance-tab')
def get_model_performance_tab():
    """Tab 1: Model Performance Analysis - Prediction accuracy, winners, totals within 1-2 runs"""
    try:
        logger.info("📊 API: Model Performance Tab requested")
        result = enhanced_analytics.get_model_performance_analysis()
        
        if result['success']:
            logger.info(f"✅ Model performance data retrieved: {result['summary']}")
        else:
            logger.error(f"❌ Model performance analysis failed: {result.get('error')}")
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"❌ Model performance tab endpoint error: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': f'Model performance analysis failed: {str(e)}'
        }), 500

@app.route('/api/betting-recommendations-tab')
def get_betting_recommendations_tab():
    """Tab 2: Betting Recommendations Performance - ML/Run Line/Totals performance since 8/15"""
    try:
        logger.info("💰 API: Betting Recommendations Tab requested")
        result = enhanced_analytics.get_betting_recommendations_performance()
        
        if result['success']:
            logger.info(f"✅ Betting recommendations data retrieved: {result['summary']}")
        else:
            logger.error(f"❌ Betting recommendations analysis failed: {result.get('error')}")
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"❌ Betting recommendations tab endpoint error: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': f'Betting recommendations analysis failed: {str(e)}'
        }), 500

@app.route('/api/kelly-best-of-best-tab')
def get_kelly_best_of_best_tab():
    """Tab 3: Kelly Best of Best Performance - High-confidence Kelly bets since 8/27"""
    try:
        logger.info("🎯 API: Kelly Best of Best Tab requested")
        result = enhanced_analytics.get_kelly_best_of_best_performance()
        
        if result['success']:
            logger.info(f"✅ Kelly best of best data retrieved: {result['summary']}")
        else:
            logger.error(f"❌ Kelly best of best analysis failed: {result.get('error')}")
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"❌ Kelly best of best tab endpoint error: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': f'Kelly best of best analysis failed: {str(e)}'
        }), 500

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
            '/api/model-performance',
            '/api/kelly-betting-guidance',
            '/api/model-performance-tab',
            '/api/betting-recommendations-tab',
            '/api/kelly-best-of-best-tab'
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
    
    # Use different port from main app to avoid conflicts
    port = int(os.environ.get('HISTORICAL_PORT', 5001))
    debug_mode = os.environ.get('FLASK_ENV') != 'production'
    
    logger.info(f"🚀 Starting Historical Analysis App on port {port} (debug: {debug_mode})")
    logger.info(f"📍 Access at: http://localhost:{port}")
    logger.info(f"🔍 Health check: http://localhost:{port}/health")
    logger.info(f"📅 Available dates: http://localhost:{port}/api/available-dates")
    
    app.run(debug=debug_mode, host='0.0.0.0', port=port)
