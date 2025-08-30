"""
Comprehensive Historical Analysis System
=====================================
Complete revamp of historical tracking focusing on:
1. Model performance metrics since 8/15
2. Betting recommendations accuracy
3. ROI calculations with $100 unit bets
4. Day-by-day performance breakdown
5. Game-level analysis

This replaces all previous historical analysis systems.
"""

import json
import os
import glob
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from team_name_normalizer import normalize_team_name
import requests

logger = logging.getLogger(__name__)

class ComprehensiveHistoricalAnalyzer:
    """Complete historical analysis system for MLB predictions and betting performance"""
    
    def __init__(self):
        self.start_date = "2025-08-15"  # Analysis start date
        self.data_dir = "data"
        # In-process caches to speed up repeated calls within the same process/request
        self._unified_cache: Optional[Dict[str, Any]] = None
        self._unified_cache_mtime: Optional[float] = None
        self._predictions_cache_by_date: Dict[str, Dict] = {}
        self._final_scores_cache_by_date: Dict[str, Dict] = {}
        self._final_scores_bundle: Optional[Dict[str, Any]] = None
        self._final_scores_bundle_mtime: Optional[float] = None
        self._summary_cache: Optional[Dict[str, Any]] = None
        self._summary_cache_mtime: Optional[float] = None

    def _load_final_scores_bundle_once(self) -> Dict[str, Any]:
        """Load historical_final_scores_cache.json once per file change."""
        try:
            bundle_path = os.path.join(self.data_dir, 'historical_final_scores_cache.json')
            if not os.path.exists(bundle_path):
                return {}
            mtime = os.path.getmtime(bundle_path)
            if self._final_scores_bundle is not None and self._final_scores_bundle_mtime == mtime:
                return self._final_scores_bundle
            with open(bundle_path, 'r') as f:
                data = json.load(f)
            self._final_scores_bundle = data if isinstance(data, dict) else {}
            self._final_scores_bundle_mtime = mtime
            return self._final_scores_bundle
        except Exception:
            return {}

    def _persist_final_scores_bundle(self, bundle: Dict[str, Any]) -> None:
        try:
            os.makedirs(self.data_dir, exist_ok=True)
            bundle_path = os.path.join(self.data_dir, 'historical_final_scores_cache.json')
            with open(bundle_path, 'w') as f:
                json.dump(bundle, f, indent=2)
            self._final_scores_bundle = bundle
            self._final_scores_bundle_mtime = os.path.getmtime(bundle_path)
        except Exception:
            pass

    def _load_summary_cache(self) -> Dict[str, Any]:
        try:
            summary_path = os.path.join(self.data_dir, 'historical_summary_cache.json')
            if not os.path.exists(summary_path):
                return {}
            mtime = os.path.getmtime(summary_path)
            if self._summary_cache is not None and self._summary_cache_mtime == mtime:
                return self._summary_cache
            with open(summary_path, 'r') as f:
                data = json.load(f)
            self._summary_cache = data if isinstance(data, dict) else {}
            self._summary_cache_mtime = mtime
            return self._summary_cache
        except Exception:
            return {}

    def _persist_summary_cache(self, summary: Dict[str, Any]) -> None:
        try:
            os.makedirs(self.data_dir, exist_ok=True)
            summary_path = os.path.join(self.data_dir, 'historical_summary_cache.json')
            with open(summary_path, 'w') as f:
                json.dump(summary, f, indent=2)
            self._summary_cache = summary
            self._summary_cache_mtime = os.path.getmtime(summary_path)
        except Exception:
            pass

    def _load_unified_cache_once(self) -> Dict[str, Any]:
        """Load unified_predictions_cache.json only once per file change.

        Returns the parsed JSON dict. If the file does not exist, returns an empty dict.
        """
        try:
            cache_path = os.path.join(self.data_dir, 'unified_predictions_cache.json')
            if not os.path.exists(cache_path):
                return {}

            mtime = os.path.getmtime(cache_path)
            if self._unified_cache is not None and self._unified_cache_mtime == mtime:
                return self._unified_cache

            with open(cache_path, 'r') as f:
                data = json.load(f)
            self._unified_cache = data if isinstance(data, dict) else {}
            self._unified_cache_mtime = mtime
            return self._unified_cache
        except Exception:
            # On any error, fall back to empty structure (callers have fallbacks too)
            return {}
        
    def get_available_dates(self) -> List[str]:
        """Get all available dates with both predictions and final scores"""
        # Load dates from unified cache (fast, no network)
        available_dates = set()
        cache_data = self._load_unified_cache_once()
        predictions_by_date = cache_data.get('predictions_by_date', {}) if isinstance(cache_data, dict) else {}
        cache_dates = set(predictions_by_date.keys())
        if cache_dates:
            logger.info(f"Found {len(cache_dates)} dates in unified cache")
            available_dates.update(cache_dates)
        else:
            logger.info("Unified cache not available or empty, falling back to legacy files")

        # Also check legacy format files (fallback)
        betting_files = glob.glob(f"{self.data_dir}/betting_recommendations_2025_08_*.json")
        games_files = glob.glob(f"{self.data_dir}/games_2025-08-*.json")
        
        # Extract dates from filenames
        betting_dates = set()
        for file in betting_files:
            date_part = os.path.basename(file).replace('betting_recommendations_', '').replace('.json', '')
            betting_dates.add(date_part.replace('_', '-'))
        
        games_dates = set()
        for file in games_files:
            date_part = os.path.basename(file).replace('games_', '').replace('.json', '')
            games_dates.add(date_part)
        
        # Find common dates (where we have both predictions and games data)
        legacy_common_dates = betting_dates & games_dates
        available_dates.update(legacy_common_dates)
        
        # Convert to sorted list and filter
        all_dates = list(available_dates)
        all_dates.sort()
        
        # Filter to start from our analysis start date and exclude today
        # Avoid live API calls here to keep this fast; get_cumulative_analysis will skip dates w/o finals.
        from datetime import date as _date
        today_str = _date.today().strftime('%Y-%m-%d')
        filtered_dates = [d for d in all_dates if d >= self.start_date and d < today_str]
        
        logger.info(f"Found {len(filtered_dates)} dates since {self.start_date} (finals checked later)")
        return filtered_dates
    
    def load_predictions_for_date(self, date: str) -> Dict:
        """Load betting recommendations for a specific date"""
        # First try from in-memory cache
        if date in self._predictions_cache_by_date:
            return self._predictions_cache_by_date[date]

        # Try to load from unified cache (single file, loaded once)
        try:
            cache_data = self._load_unified_cache_once()
            # Check if date exists in unified cache structures
            predictions_by_date = cache_data.get('predictions_by_date', {}) if isinstance(cache_data, dict) else {}
            if isinstance(predictions_by_date, dict) and date in predictions_by_date:
                date_data = predictions_by_date.get(date) or {}
                games_data = date_data.get('games', {}) if isinstance(date_data, dict) else {}
                if games_data:
                    logger.info(f"Loaded {len(games_data)} games from unified cache for {date}")
                    self._predictions_cache_by_date[date] = games_data
                    return games_data

            # Fallback: some unified caches store dates at top-level
            if isinstance(cache_data, dict) and date in cache_data:
                date_blob = cache_data.get(date) or {}
                games_data = date_blob.get('games') if isinstance(date_blob, dict) else None
                if not games_data and isinstance(date_blob, dict):
                    # Some formats store games directly under the date as keys
                    games_data = {k: v for k, v in date_blob.items() if k not in ['metadata', 'generated_at']}
                if games_data:
                    logger.info(f"Loaded {len(games_data)} games from top-level unified cache for {date}")
                    self._predictions_cache_by_date[date] = games_data
                    return games_data
        except Exception as e:
            logger.info(f"Unified cache not available for {date}, trying legacy format: {e}")
        
        # Fallback to legacy format
        date_formatted = date.replace('-', '_')
        file_path = f"{self.data_dir}/betting_recommendations_{date_formatted}.json"

        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            games_data = data.get('games', {})

            # Validate that the data has proper predictions (support both old and new formats)
            if games_data:
                sample_game = next(iter(games_data.values()))

                # Check for new format first (win_probabilities structure at top level)
                win_probs = sample_game.get('win_probabilities', {})
                if (win_probs.get('home_prob') is not None and 
                    win_probs.get('away_prob') is not None and
                    sample_game.get('predicted_total_runs') is not None):
                    logger.info(f"Cached data for {date} is in new format")
                    self._predictions_cache_by_date[date] = games_data
                    return games_data

                # Check for current format (has both predictions and recommendations)
                if ('predictions' in sample_game and 
                    'recommendations' in sample_game and
                    sample_game.get('predictions', {}).get('predicted_total_runs') is not None):
                    logger.info(f"Cached data for {date} is in current format with recommendations")
                    self._predictions_cache_by_date[date] = games_data
                    return games_data

                # Check for old format (predictions structure only, needs conversion)
                predictions = sample_game.get('predictions', {})
                if (predictions.get('home_win_prob') is not None and
                    predictions.get('away_win_prob') is not None and
                    predictions.get('predicted_total_runs') is not None and
                    'recommendations' not in sample_game):
                    logger.info(f"Cached data for {date} is in old format, converting...")
                    # Convert old format to new format
                    converted = self._convert_old_format_to_new(games_data)
                    self._predictions_cache_by_date[date] = converted
                    return converted

                # If neither format is valid, try regeneration
                logger.warning(f"Cached data for {date} has invalid predictions, regenerating...")
                raise ValueError("Invalid cached data")

            return games_data
        except (FileNotFoundError, ValueError):
            logger.info(f"Generating fresh predictions for {date} using enhanced engine...")
            return self._generate_predictions_for_date(date)
        except Exception as e:
            logger.error(f"Error loading predictions for {date}: {e}")
            return {}
    
    def _generate_predictions_for_date(self, date: str) -> Dict:
        """Generate fresh predictions using the enhanced betting engine"""
        try:
            from betting_recommendations_engine import BettingRecommendationsEngine
            
            # Initialize enhanced engine
            engine = BettingRecommendationsEngine()
            
            # Generate predictions for the specific date
            engine.target_date = date
            recommendations = engine.generate_betting_recommendations()
            
            if recommendations.get('success') and recommendations.get('games'):
                logger.info(f"Generated {len(recommendations['games'])} predictions for {date}")
                return recommendations['games']
            else:
                logger.warning(f"Failed to generate predictions for {date}: {recommendations.get('error', 'Unknown error')}")
                return {}
                
        except Exception as e:
            logger.error(f"Error generating predictions for {date}: {e}")
            return {}
    
    def _convert_old_format_to_new(self, old_games_data: Dict) -> Dict:
        """Convert old format cached data to new format structure"""
        new_games_data = {}
        
        for game_key, old_game in old_games_data.items():
            try:
                predictions = old_game.get('predictions', {})
                
                # Extract basic game info
                new_game = {
                    'away_team': old_game.get('away_team', ''),
                    'home_team': old_game.get('home_team', ''),
                    'away_pitcher': old_game.get('away_pitcher', ''),
                    'home_pitcher': old_game.get('home_pitcher', ''),
                }
                
                # Convert win probabilities
                home_prob = predictions.get('home_win_prob', 0.5)
                away_prob = predictions.get('away_win_prob', 0.5)
                
                new_game['win_probabilities'] = {
                    'home_prob': home_prob,
                    'away_prob': away_prob
                }
                
                # Extract predicted total runs
                new_game['predicted_total_runs'] = predictions.get('predicted_total_runs', 8.5)
                
                # Extract predicted score
                home_score = predictions.get('predicted_home_score', 4.0)
                away_score = predictions.get('predicted_away_score', 4.5)
                new_game['predicted_score'] = f"{away_score}-{home_score}"
                
                # Convert recommendations to value_bets format
                recommendations = old_game.get('recommendations', [])
                value_bets = []
                
                for rec in recommendations:
                    if isinstance(rec, dict):
                        bet = {
                            'type': rec.get('type', 'moneyline'),
                            'recommendation': rec.get('recommendation', ''),
                            'expected_value': rec.get('expected_value', 0),
                            'win_probability': rec.get('win_probability', away_prob if 'away' in str(rec.get('recommendation', '')).lower() else home_prob),
                            'american_odds': str(rec.get('odds', 100)),
                            'confidence': rec.get('confidence', 'medium'),
                            'reasoning': rec.get('reasoning', 'Converted from old format')
                        }
                        value_bets.append(bet)
                
                new_game['value_bets'] = value_bets
                new_games_data[game_key] = new_game
                
            except Exception as e:
                logger.warning(f"Error converting old format for game {game_key}: {e}")
                continue
        
        logger.info(f"Converted {len(new_games_data)} games from old format to new format")
        return new_games_data
    
    def load_final_scores_for_date(self, date: str) -> Dict:
        """Load final scores for a specific date with caching and disk-first strategy.

        Order of attempts:
        1) In-memory cache
        2) Local file data/final_scores_YYYY_MM_DD.json
        3) Live MLB API (once), then persist to file and memory
        """
        # In-memory cache
        if date in self._final_scores_cache_by_date:
            return self._final_scores_cache_by_date[date]

        # Bundle cache (all dates in one file)
        bundle = self._load_final_scores_bundle_once()
        if date in bundle:
            finals = bundle.get(date) or {}
            if isinstance(finals, dict) and finals:
                self._final_scores_cache_by_date[date] = finals
                return finals

        # Disk cache
        try:
            cache_path = os.path.join(self.data_dir, f"final_scores_{date.replace('-', '_')}.json")
            if os.path.exists(cache_path):
                with open(cache_path, 'r') as f:
                    cached = json.load(f)
                final_scores: Dict[str, Any] = {}
                if isinstance(cached, dict):
                    for _, v in cached.items():
                        away_team = normalize_team_name(v.get('away_team', ''))
                        home_team = normalize_team_name(v.get('home_team', ''))
                        key = f"{away_team}_vs_{home_team}"
                        final_scores[key] = {
                            'away_team': away_team,
                            'home_team': home_team,
                            'away_score': v.get('away_score', 0),
                            'home_score': v.get('home_score', 0),
                            'total_runs': v.get('total_runs', v.get('away_score', 0) + v.get('home_score', 0)),
                            'winner': v.get('winner', 'away' if v.get('away_score', 0) > v.get('home_score', 0) else 'home'),
                            'game_pk': v.get('game_pk', ''),
                            'is_final': True
                        }
                if final_scores:
                    logger.info(f"Loaded {len(final_scores)} final scores for {date} from disk cache")
                    self._final_scores_cache_by_date[date] = final_scores
                    # Also hydrate bundle and persist
                    try:
                        bundle = self._load_final_scores_bundle_once()
                        bundle[date] = final_scores
                        self._persist_final_scores_bundle(bundle)
                    except Exception:
                        pass
                    return final_scores
        except Exception:
            # Non-fatal; fall through to live fetch
            pass

        # Live fetch (last resort)
        try:
            from live_mlb_data import LiveMLBData
            mlb_api = LiveMLBData()
            live_games = mlb_api.get_enhanced_games_data(date)

            final_scores: Dict[str, Any] = {}
            for game in live_games:
                if game.get('is_final', False):
                    away_team = normalize_team_name(game.get('away_team', ''))
                    home_team = normalize_team_name(game.get('home_team', ''))
                    game_key = f"{away_team}_vs_{home_team}"

                    final_scores[game_key] = {
                        'away_team': away_team,
                        'home_team': home_team,
                        'away_score': game.get('away_score', 0),
                        'home_score': game.get('home_score', 0),
                        'total_runs': game.get('away_score', 0) + game.get('home_score', 0),
                        'winner': 'away' if game.get('away_score', 0) > game.get('home_score', 0) else 'home',
                        'game_pk': game.get('game_pk', ''),
                        'is_final': True
                    }

            # Persist to disk for future fast loads
            try:
                if final_scores:
                    out_path = os.path.join(self.data_dir, f"final_scores_{date.replace('-', '_')}.json")
                    with open(out_path, 'w') as f:
                        json.dump(final_scores, f, indent=2)
                    # Update bundle cache as well
                    try:
                        bundle = self._load_final_scores_bundle_once()
                        bundle[date] = final_scores
                        self._persist_final_scores_bundle(bundle)
                    except Exception:
                        pass
            except Exception:
                # If persisting fails, still return in-memory result
                pass

            logger.info(f"Loaded {len(final_scores)} final scores for {date}")
            self._final_scores_cache_by_date[date] = final_scores
            return final_scores
        except Exception as e:
            logger.error(f"Error loading final scores for {date}: {e}")
            return {}
    
    def analyze_model_performance(self, predictions: Dict, final_scores: Dict) -> Dict:
        """Analyze core model performance - winner predictions and score accuracy"""
        stats = {
            'total_games': 0,
            'winner_correct': 0,
            'total_runs_within_1': 0,
            'total_runs_within_2': 0,
            'average_score_diff': 0,
            'games_analyzed': []
        }
        
        total_score_diff = 0
        
        for game_key, prediction in predictions.items():
            # Normalize the key for matching
            away_team = normalize_team_name(prediction.get('away_team', ''))
            home_team = normalize_team_name(prediction.get('home_team', ''))
            normalized_key = f"{away_team}_vs_{home_team}"
            
            if normalized_key not in final_scores:
                continue
            
            final_score = final_scores[normalized_key]
            stats['total_games'] += 1
            
            # Extract prediction data
            win_probs = prediction.get('win_probabilities', {})
            predictions_data = prediction.get('predictions', {})
            
            # Try to get from different possible locations
            away_prob = win_probs.get('away_prob') or predictions_data.get('away_win_prob', 0.5)
            home_prob = win_probs.get('home_prob') or predictions_data.get('home_win_prob', 0.5)
            predicted_total = (prediction.get('predicted_total_runs') or 
                             predictions_data.get('predicted_total_runs', 0))
            
            # Winner accuracy
            predicted_winner = 'away' if away_prob > home_prob else 'home'
            actual_winner = final_score['winner']
            winner_correct = predicted_winner == actual_winner
            
            if winner_correct:
                stats['winner_correct'] += 1
            
            # Total runs accuracy
            actual_total = final_score['total_runs']
            total_diff = abs(predicted_total - actual_total)
            total_score_diff += total_diff
            
            if total_diff <= 1:
                stats['total_runs_within_1'] += 1
            if total_diff <= 2:
                stats['total_runs_within_2'] += 1
            
            # Store game analysis with enhanced display data
            stats['games_analyzed'].append({
                'game_key': normalized_key,
                'away_team': away_team,
                'home_team': home_team,
                'predicted_winner': predicted_winner,
                'actual_winner': actual_winner,
                'winner_correct': winner_correct,
                'predicted_total': predicted_total,
                'actual_total': actual_total,
                'total_diff': total_diff,
                'away_prob': away_prob,
                'home_prob': home_prob,
                'away_score': final_score.get('away_score', 0),
                'home_score': final_score.get('home_score', 0),
                'game_pk': final_score.get('game_pk', ''),
                'is_final': final_score.get('is_final', True)
            })
        
        # Calculate percentages and averages - LIMITED TO 2 DECIMAL PLACES MAX
        if stats['total_games'] > 0:
            stats['winner_accuracy'] = round((stats['winner_correct'] / stats['total_games']) * 100, 2)
            stats['total_runs_accuracy_1'] = round((stats['total_runs_within_1'] / stats['total_games']) * 100, 2)
            stats['total_runs_accuracy_2'] = round((stats['total_runs_within_2'] / stats['total_games']) * 100, 2)
            stats['average_score_diff'] = round(total_score_diff / stats['total_games'], 2)
        else:
            stats['winner_accuracy'] = 0
            stats['total_runs_accuracy_1'] = 0
            stats['total_runs_accuracy_2'] = 0
            stats['average_score_diff'] = 0
        
        return stats
    
    def analyze_betting_recommendations(self, predictions: Dict, final_scores: Dict) -> Dict:
        """Analyze betting recommendations performance and calculate ROI - handles varied data structures"""
        stats = {
            'total_recommendations': 0,
            'correct_recommendations': 0,
            'moneyline_stats': {'total': 0, 'correct': 0, 'accuracy': 0},
            'total_stats': {'total': 0, 'correct': 0, 'accuracy': 0},
            'runline_stats': {'total': 0, 'correct': 0, 'accuracy': 0},
            'total_bet_amount': 0,
            'total_winnings': 0,
            'roi_percentage': 0,
            'detailed_bets': []
        }
        
        bet_unit = 100  # $100 per bet
        logger.info(f"Analyzing {len(predictions)} games with {len(final_scores)} final scores")
        
        # Process each game individually to handle varied data structures
        for game_key, prediction in predictions.items():
            game_stats = self.analyze_single_game_bets(game_key, prediction, final_scores, bet_unit)
            
            # Aggregate the stats
            stats['total_recommendations'] += game_stats['total_recommendations']
            stats['correct_recommendations'] += game_stats['correct_recommendations']
            stats['total_bet_amount'] += game_stats['total_bet_amount']
            stats['total_winnings'] += game_stats['total_winnings']
            
            # Aggregate by bet type
            for bet_type in ['moneyline_stats', 'total_stats', 'runline_stats']:
                stats[bet_type]['total'] += game_stats[bet_type]['total']
                stats[bet_type]['correct'] += game_stats[bet_type]['correct']
            
            # Add detailed bets
            stats['detailed_bets'].extend(game_stats['detailed_bets'])
        
        # Calculate final percentages and ROI
        if stats['total_recommendations'] > 0:
            stats['overall_accuracy'] = round((stats['correct_recommendations'] / stats['total_recommendations']) * 100, 2)
        else:
            stats['overall_accuracy'] = 0
        
        for bet_type in ['moneyline_stats', 'total_stats', 'runline_stats']:
            if stats[bet_type]['total'] > 0:
                stats[bet_type]['accuracy'] = round((stats[bet_type]['correct'] / stats[bet_type]['total']) * 100, 2)
        
        if stats['total_bet_amount'] > 0:
            net_profit = stats['total_winnings'] - stats['total_bet_amount']
            stats['roi_percentage'] = round((net_profit / stats['total_bet_amount']) * 100, 2)
            stats['net_profit'] = round(net_profit, 2)
        else:
            stats['roi_percentage'] = 0
            stats['net_profit'] = 0
        
        logger.info(f"Analysis complete: {stats['total_recommendations']} bets, {stats['correct_recommendations']} correct, {stats['roi_percentage']}% ROI")
        return stats
    
    def analyze_single_game_bets(self, game_key: str, prediction: Dict, final_scores: Dict, bet_unit: float) -> Dict:
        """Analyze betting recommendations for a single game - handles varied data structures"""
        game_stats = {
            'total_recommendations': 0,
            'correct_recommendations': 0,
            'moneyline_stats': {'total': 0, 'correct': 0},
            'total_stats': {'total': 0, 'correct': 0},
            'runline_stats': {'total': 0, 'correct': 0},
            'total_bet_amount': 0,
            'total_winnings': 0,
            'detailed_bets': []
        }
        
        # Normalize game key for matching final scores
        away_team = normalize_team_name(prediction.get('away_team', ''))
        home_team = normalize_team_name(prediction.get('home_team', ''))
        normalized_key = f"{away_team}_vs_{home_team}"
        
        # Find final score for this game
        final_score = None
        if normalized_key in final_scores:
            final_score = final_scores[normalized_key]
        else:
            # Try alternative matching methods
            for score_key, score_data in final_scores.items():
                if (away_team in score_key and home_team in score_key):
                    final_score = score_data
                    break
        
        if not final_score:
            logger.warning(f"No final score found for {game_key} (normalized: {normalized_key})")
            return game_stats
        
        # Extract betting recommendations using multiple approaches
        recommendations = self.extract_game_recommendations(prediction)
        
        if not recommendations:
            logger.debug(f"No recommendations found for {game_key}")
            return game_stats
        
        logger.debug(f"Found {len(recommendations)} recommendations for {game_key}")
        
        # Process each recommendation
        for rec in recommendations:
            try:
                bet_result = self.evaluate_single_bet(rec, final_score, prediction, bet_unit)
                
                if bet_result['is_valid']:
                    game_stats['total_recommendations'] += 1
                    game_stats['total_bet_amount'] += bet_unit
                    
                    if bet_result['bet_won']:
                        game_stats['correct_recommendations'] += 1
                        game_stats['total_winnings'] += bet_result['winnings']
                    
                    # Track by bet type
                    bet_type = bet_result['bet_type']
                    if bet_type == 'moneyline':
                        game_stats['moneyline_stats']['total'] += 1
                        if bet_result['bet_won']:
                            game_stats['moneyline_stats']['correct'] += 1
                    elif bet_type == 'total':
                        game_stats['total_stats']['total'] += 1
                        if bet_result['bet_won']:
                            game_stats['total_stats']['correct'] += 1
                    elif bet_type in ['runline', 'run_line']:
                        game_stats['runline_stats']['total'] += 1
                        if bet_result['bet_won']:
                            game_stats['runline_stats']['correct'] += 1
                    
                    # Add detailed bet info
                    game_stats['detailed_bets'].append({
                        'game_key': normalized_key,
                        'away_team': away_team,
                        'home_team': home_team,
                        'bet_type': bet_result['bet_type'],
                        'recommendation': bet_result['recommendation'],
                        'american_odds': bet_result['american_odds'],
                        'expected_value': bet_result.get('expected_value', 0),
                        'bet_amount': bet_unit,
                        'bet_won': bet_result['bet_won'],
                        'winnings': bet_result['winnings'] if bet_result['bet_won'] else 0,
                        'confidence': bet_result.get('confidence', 'UNKNOWN')
                    })
                    
            except Exception as e:
                logger.warning(f"Error evaluating bet for {game_key}: {e}")
                continue
        
        return game_stats
    
    def extract_game_recommendations(self, prediction: Dict) -> List[Dict]:
        """Extract betting recommendations from game data - handles multiple data formats"""
        recommendations = []
        away_team = normalize_team_name(prediction.get('away_team', ''))
        home_team = normalize_team_name(prediction.get('home_team', ''))

        # Helper to detect non-bet commentary that should not be counted
        commentary_types = {
            'market analysis', 'market_analysis', 'analysis', 'commentary', 'lean', 'watchlist'
        }
        commentary_markers = [
            'market analysis', 'efficiently priced', 'efficiently-priced',
            'no clear value', 'no recommendation', 'no recommendations',
            'no bet', 'pass', 'stay away', 'monitor only', 'monitor-only',
            'lean only', 'lean-only'
        ]

        def is_non_bet_commentary(bt: str, conf: str, text: str) -> bool:
            bt_l = (bt or '').lower().strip()
            conf_l = (conf or '').lower().strip()
            txt_l = (text or '').lower()
            if bt_l in commentary_types:
                return True
            # Treat LOW-confidence entries that read like market commentary as non-bets
            if 'low' in conf_l and any(marker in txt_l for marker in commentary_markers):
                return True
            # Generic phrasing strongly implying "no bet" regardless of confidence
            if any(kw in txt_l for kw in ['no bet', 'no recommendation', 'no clear value']):
                return True
            return False

        def derive_side_and_line(text: str, existing_side: str, bet_type: str, line_val):
            text_l = (text or '').lower()
            side = (existing_side or '').lower()
            line_out = line_val
            import re

            def infer_side_via_aliases(txt: str, away: str, home: str) -> str:
                # Tokenize and try to normalize each token to a team; covers KC, STL, LAA, nicknames
                tokens = re.findall(r"[A-Za-z\.']+", txt)
                for tok in tokens:
                    norm = normalize_team_name(tok)
                    if norm and norm == away:
                        return 'away'
                    if norm and norm == home:
                        return 'home'
                return ''
            # Totals: try to parse Over/Under X
            if bet_type == 'total':
                if not side:
                    if 'over' in text_l:
                        side = 'over'
                    elif 'under' in text_l:
                        side = 'under'
                if (line_out is None or not isinstance(line_out, (int, float)) or line_out <= 0):
                    m = re.search(r"(over|under)\s*([0-9]+(?:\.[0-9])?)", text_l)
                    if m:
                        try:
                            line_out = float(m.group(2))
                        except Exception:
                            pass
            # Moneyline: infer home/away via team names or aliases in text
            elif bet_type == 'moneyline':
                if not side:
                    tl = text_l
                    if away_team and away_team.lower() in tl:
                        side = 'away'
                    elif home_team and home_team.lower() in tl:
                        side = 'home'
                    elif 'road' in tl or 'away' in tl:
                        side = 'away'
                    elif 'home' in tl:
                        side = 'home'
                    if not side:
                        inferred = infer_side_via_aliases(text, away_team, home_team)
                        if inferred:
                            side = inferred
            # Runline: parse like Team -1.5 / +1.5
            elif bet_type in ['runline', 'run_line']:
                if (line_out is None or not isinstance(line_out, (int, float)) or line_out == 0):
                    m = re.search(r"([+-][0-9]+(?:\.[0-9])?)", text_l)
                    if m:
                        try:
                            line_out = float(m.group(1))
                        except Exception:
                            pass
                if not side:
                    tl = text_l
                    if away_team and away_team.lower() in tl:
                        side = 'away'
                    elif home_team and home_team.lower() in tl:
                        side = 'home'
                    if not side:
                        inferred = infer_side_via_aliases(text, away_team, home_team)
                        if inferred:
                            side = inferred
            return side, line_out
        
        # Method 0: Some dates (e.g., 8/22, 8/23) nest recommendations under prediction['predictions']
        try:
            nested = prediction.get('predictions') or {}
            nested_recs = nested.get('recommendations') if isinstance(nested, dict) else None
            if isinstance(nested_recs, list) and nested_recs:
                for rec in nested_recs:
                    if not isinstance(rec, dict):
                        continue
                    bt = str(rec.get('type', '')).lower()
                    conf = str(rec.get('confidence', ''))
                    rec_text = str(rec.get('recommendation', '') or rec.get('reasoning', ''))
                    # Skip commentary / non-bet entries
                    if is_non_bet_commentary(bt, conf, rec_text):
                        continue
                    side = str(rec.get('side', '')).lower()
                    line_val = rec.get('line', rec.get('betting_line', 0))
                    # Try to derive if missing
                    side, line_val = derive_side_and_line(rec_text, side, bt, line_val)
                    if bt in ['total', 'moneyline', 'runline', 'run_line'] and not side:
                        continue
                    recommendations.append({
                        'source': 'predictions.recommendations',
                        'type': bt,
                        'side': side,
                        'line': line_val or 0,
                        'odds': rec.get('odds', rec.get('american_odds', '-110')),
                        'expected_value': rec.get('expected_value', 0),
                        'confidence': rec.get('confidence', 'MEDIUM'),
                        'reasoning': rec.get('reasoning', rec_text)
                    })
        except Exception:
            pass
        
        # Method 1: Direct recommendations field (current format)
        if 'recommendations' in prediction and prediction['recommendations']:
            for rec in prediction['recommendations']:
                if isinstance(rec, dict) and rec.get('type'):
                    # Filter out invalid/empty recommendations
                    bet_type = str(rec.get('type', '')).lower()
                    side = str(rec.get('side', '')).lower()
                    rec_text = str(rec.get('recommendation', '') or rec.get('reasoning', ''))
                    conf = str(rec.get('confidence', ''))
                    
                    # Skip invalid bet types
                    if bet_type in ['none', 'unknown', '']:
                        continue
                    # Skip commentary / non-bet entries
                    if is_non_bet_commentary(bet_type, conf, rec_text):
                        continue
                    
                    # If side missing, attempt to derive from text and team names
                    line_val = rec.get('line', 0)
                    if bet_type in ['total', 'moneyline', 'runline', 'run_line'] and not side:
                        d_side, d_line = derive_side_and_line(rec_text, side, bet_type, line_val)
                        side = d_side or side
                        line_val = d_line if d_line is not None else line_val
                    
                    recommendations.append({
                        'source': 'recommendations',
                        'type': bet_type,
                        'side': side,
                        'line': line_val,
                        'odds': rec.get('odds', -110),
                        'expected_value': rec.get('expected_value', 0),
                        'confidence': rec.get('confidence', 'MEDIUM'),
                        'reasoning': rec.get('reasoning', '')
                    })
        
        # Method 2: value_bets field (converted/newer format)
        if 'value_bets' in prediction and prediction['value_bets']:
            for bet in prediction['value_bets']:
                if isinstance(bet, dict) and bet.get('type'):
                    # Filter out invalid bet types
                    bet_type = str(bet.get('type', '')).lower()
                    if bet_type in ['none', 'unknown', '']:
                        continue
                    
                    # Parse the recommendation field for side/direction
                    rec_text = str(bet.get('recommendation', '')).lower()
                    if rec_text in ['no recommendations', 'no clear value identified', '']:
                        continue
                    # Skip commentary / non-bet entries
                    conf = str(bet.get('confidence', ''))
                    if is_non_bet_commentary(bet_type, conf, rec_text):
                        continue
                    # Start with provided side and line, then try to derive from text/team names
                    side = str(bet.get('side', '')).lower()
                    line_val = bet.get('betting_line', bet.get('line', 0))
                    side, line_val = derive_side_and_line(rec_text or bet.get('reasoning', ''), side, bet_type, line_val)
                    
                    # Skip if no valid side found
                    if not side:
                        continue
                    
                    recommendations.append({
                        'source': 'value_bets',
                        'type': bet_type,
                        'side': side,
                        'line': line_val or 0,
                        'odds': bet.get('american_odds', bet.get('odds', '-110')),
                        'expected_value': bet.get('expected_value', 0),
                        'confidence': bet.get('confidence', 'MEDIUM'),
                        'reasoning': bet.get('reasoning', '')
                    })
        
        # Method 3: Legacy unified recommendations
        if 'unified_value_bets' in prediction:
            unified_bets = prediction['unified_value_bets']
            if isinstance(unified_bets, list):
                for bet in unified_bets:
                    if isinstance(bet, dict) and bet.get('type'):
                        bt = str(bet.get('type', '')).lower()
                        conf = str(bet.get('confidence', ''))
                        rec_text = str(bet.get('recommendation', '') or bet.get('reasoning', ''))
                        # Skip commentary / non-bet entries
                        if is_non_bet_commentary(bt, conf, rec_text):
                            continue
                        # Optionally skip entries with no side and no parseable text
                        side_val = str(bet.get('side', '')).lower()
                        if not side_val and not any(k in rec_text.lower() for k in ['over', 'under', 'home', 'away', away_team.lower(), home_team.lower()] if isinstance(rec_text, str)):
                            continue
                        recommendations.append({
                            'source': 'unified_value_bets',
                            'type': bt,
                            'side': side_val,
                            'line': bet.get('line', 0),
                            'odds': bet.get('odds', -110),
                            'expected_value': bet.get('expected_value', 0),
                            'confidence': bet.get('confidence', 'MEDIUM'),
                            'reasoning': bet.get('reasoning', '')
                        })

        # Method 4: Alternate field 'betting_recommendations' used in some dates
        if 'betting_recommendations' in prediction and prediction['betting_recommendations']:
            br = prediction['betting_recommendations']
            # It can be a dict keyed by type or a list
            if isinstance(br, dict):
                # Example: {'moneyline': {...}, 'total': {...}}
                for bt, val in br.items():
                    if isinstance(val, dict):
                        rec_text = str(val.get('recommendation', '')).lower()
                        side = str(val.get('side', '')).lower()
                        line_val = val.get('line', val.get('betting_line', 0))
                        bt_l = str(bt).lower().replace(' ', '_')
                        conf = str(val.get('confidence', ''))
                        # Skip commentary / non-bet entries
                        if is_non_bet_commentary(bt_l, conf, rec_text or val.get('reasoning', '')):
                            continue
                        side, line_val = derive_side_and_line(rec_text or val.get('reasoning', ''), side, bt_l, line_val)
                        if not side:
                            continue
                        recommendations.append({
                            'source': 'betting_recommendations',
                            'type': bt_l,
                            'side': side,
                            'line': line_val or 0,
                            'odds': val.get('odds', val.get('american_odds', '-110')),
                            'expected_value': val.get('expected_value', 0),
                            'confidence': val.get('confidence', 'MEDIUM'),
                            'reasoning': val.get('reasoning', rec_text)
                        })
            elif isinstance(br, list):
                for val in br:
                    if not isinstance(val, dict):
                        continue
                    bt = str(val.get('type', '')).lower()
                    if bt in ['none', 'unknown', '']:
                        continue
                    rec_text = str(val.get('recommendation', '')).lower()
                    conf = str(val.get('confidence', ''))
                    # Skip commentary / non-bet entries
                    if is_non_bet_commentary(bt, conf, rec_text or val.get('reasoning', '')):
                        continue
                    side = str(val.get('side', '')).lower()
                    line_val = val.get('line', val.get('betting_line', 0))
                    side, line_val = derive_side_and_line(rec_text or val.get('reasoning', ''), side, bt, line_val)
                    if not side:
                        continue
                    recommendations.append({
                        'source': 'betting_recommendations',
                        'type': bt,
                        'side': side,
                        'line': line_val or 0,
                        'odds': val.get('odds', val.get('american_odds', '-110')),
                        'expected_value': val.get('expected_value', 0),
                        'confidence': val.get('confidence', 'MEDIUM'),
                        'reasoning': val.get('reasoning', rec_text)
                    })
        
        return recommendations
    
    def evaluate_single_bet(self, recommendation: Dict, final_score: Dict, prediction: Dict, bet_unit: float) -> Dict:
        """Evaluate a single betting recommendation"""
        bet_type = recommendation.get('type', '').lower()
        side = recommendation.get('side', '').lower()
        line = recommendation.get('line', 0)
        odds = recommendation.get('odds', -110)
        
        # If side is missing, try to infer it using team names and text
        if bet_type and not side:
            try:
                away_team = normalize_team_name(prediction.get('away_team', ''))
                home_team = normalize_team_name(prediction.get('home_team', ''))
                text = (str(recommendation.get('recommendation', '')) + ' ' + str(recommendation.get('reasoning', ''))).lower()
                # Moneyline: match team name to home/away
                if bet_type == 'moneyline':
                    if away_team and away_team.lower() in text:
                        side = 'away'
                    elif home_team and home_team.lower() in text:
                        side = 'home'
                # Totals: parse Over/Under
                elif bet_type == 'total':
                    if 'over' in text:
                        side = 'over'
                    elif 'under' in text:
                        side = 'under'
                    # Try to parse a line if missing/invalid
                    if not (isinstance(line, (int, float)) and line > 0):
                        import re
                        m = re.search(r"(over|under)\s*([0-9]+(?:\.[0-9])?)", text)
                        if m:
                            try:
                                line = float(m.group(2))
                            except Exception:
                                pass
                # Runline: infer team and parse +/- line
                elif bet_type in ['runline', 'run_line']:
                    if away_team and away_team.lower() in text:
                        side = 'away'
                    elif home_team and home_team.lower() in text:
                        side = 'home'
                    if not (isinstance(line, (int, float)) and line != 0):
                        import re
                        m = re.search(r"([+-][0-9]+(?:\.[0-9])?)", text)
                        if m:
                            try:
                                line = float(m.group(1))
                            except Exception:
                                pass
            except Exception:
                pass

        # Validate bet has required fields after inference
        if not bet_type or not side:
            return {'is_valid': False}
        
        # Convert odds to string format if needed
        try:
            if isinstance(odds, (int, float)):
                american_odds = f"{int(odds):+d}"
            else:
                american_odds = str(odds).strip()
        except Exception:
            american_odds = "-110"
            
        # Ensure odds have proper sign
        if not american_odds.startswith(('+', '-')):
            # If numeric string without sign, default to negative (favorite-style) odds
            american_odds = f"-{american_odds}" if american_odds.replace('.', '').isdigit() else american_odds
        
        actual_total = final_score.get('total_runs', 0)
        actual_winner = final_score.get('winner', '')
        
        bet_won = False
        
        # Evaluate based on bet type
        if bet_type == 'total' and line > 0:
            if side == 'over':
                bet_won = actual_total > line
            elif side == 'under':
                bet_won = actual_total < line
                
        elif bet_type == 'moneyline':
            if side in ['away', 'home']:
                bet_won = actual_winner == side
                
        elif bet_type in ['runline', 'run_line'] and line != 0:
            if side == 'away':
                # Away team getting points
                away_score_adjusted = final_score.get('away_score', 0) + abs(line)
                bet_won = away_score_adjusted > final_score.get('home_score', 0)
            elif side == 'home':
                # Home team giving points
                home_score_adjusted = final_score.get('home_score', 0) - abs(line)
                bet_won = home_score_adjusted > final_score.get('away_score', 0)
        
        # Calculate winnings if bet won
        winnings = 0
        if bet_won:
            winnings = self.calculate_winnings(bet_unit, american_odds)
        
        return {
            'is_valid': True,
            'bet_type': bet_type,
            'recommendation': f"{side} {line}" if line else side,
            'american_odds': american_odds,
            'bet_won': bet_won,
            'winnings': winnings,
            'expected_value': recommendation.get('expected_value', 0),
            'confidence': recommendation.get('confidence', 'UNKNOWN')
        }
    
    def evaluate_bet(self, bet: Dict, final_score: Dict, prediction: Dict) -> bool:
        """Evaluate if a specific bet won based on final score"""
        recommendation = bet.get('recommendation', '').lower().strip()
        bet_type = bet.get('type', '').lower()
        side = bet.get('side', '').lower()
        reasoning = bet.get('reasoning', '').lower()
        
        # Return False for empty or invalid recommendations
        if (not bet_type or bet_type in ['none', 'unknown'] or
            (not side and not recommendation) or
            recommendation in ['no recommendations', 'no clear value identified']):
            return False
        
        actual_total = final_score['total_runs']
        actual_winner = final_score['winner']
        
        # Handle total bets (over/under)
        if bet_type == 'total':
            betting_line = bet.get('line', 0)
            
            # Get the side/direction of the bet
            bet_side = side or ('over' if 'over' in recommendation else 'under' if 'under' in recommendation else '')
            
            if betting_line and bet_side:
                if bet_side == 'over':
                    return actual_total > betting_line
                elif bet_side == 'under':
                    return actual_total < betting_line
        
        # Handle moneyline bets
        elif bet_type == 'moneyline':
            # Get the side/team of the bet
            bet_side = side or ('away' if 'away' in recommendation else 'home' if 'home' in recommendation else '')
            
            if bet_side:
                return actual_winner == bet_side
            
            # Fallback: check team names in recommendation
            away_team = normalize_team_name(prediction.get('away_team', ''))
            home_team = normalize_team_name(prediction.get('home_team', ''))
            
            if away_team.lower() in recommendation:
                return actual_winner == 'away'
            elif home_team.lower() in recommendation:
                return actual_winner == 'home'
        
        # Handle run line bets (spread)
        elif bet_type in ['runline', 'run_line']:
            run_line = bet.get('line', 1.5)  # Default MLB run line
            bet_side = side or ('away' if 'away' in recommendation else 'home' if 'home' in recommendation else '')
            
            if bet_side == 'away':
                # Away team getting points (underdog)
                away_score_adjusted = final_score['away_score'] + abs(run_line)
                return away_score_adjusted > final_score['home_score']
            elif bet_side == 'home':
                # Home team giving points (favorite)  
                home_score_adjusted = final_score['home_score'] - abs(run_line)
                return home_score_adjusted > final_score['away_score']
        
        # If we can't determine the bet type or outcome, return False
        return False
    
    def calculate_winnings(self, bet_amount: float, american_odds: str) -> float:
        """Calculate total winnings from American odds (including original bet back)"""
        try:
            # Check if odds are negative BEFORE removing the minus sign
            is_negative = american_odds.startswith('-')
            odds = int(american_odds.replace('+', '').replace('-', ''))
            
            if is_negative:
                # Negative odds (favorite): bet $odds to win $100
                # Example: -110 means bet $110 to win $100
                profit = bet_amount * (100 / odds)
            else:
                # Positive odds (underdog): bet $100 to win $odds
                # Example: +150 means bet $100 to win $150
                profit = bet_amount * (odds / 100)
            
            # Return total payout: original bet + profit
            return round(bet_amount + profit, 2)
        except:
            # Default to even money if odds parsing fails - return double the bet
            return bet_amount * 2
    
    def get_cumulative_analysis(self) -> Dict:
        """Get cumulative analysis across all available dates.

        Uses a disk cache when the set of available dates hasn't changed to avoid recomputation.
        """
        available_dates = self.get_available_dates()

        # Try summary cache first
        summary_cache = self._load_summary_cache()
        cached_dates = summary_cache.get('available_dates') if isinstance(summary_cache, dict) else None
        if isinstance(cached_dates, list) and cached_dates == available_dates and summary_cache.get('model_performance') and summary_cache.get('betting_performance'):
            logger.info("📦 Using cached historical summary (dates unchanged)")
            return summary_cache
        
        cumulative_stats = {
            'analysis_period': f"{self.start_date} to {max(available_dates) if available_dates else 'present'}",
            'total_dates_analyzed': len(available_dates),
            'model_performance': {
                'total_games': 0,
                'winner_correct': 0,
                'winner_accuracy': 0,
                'total_runs_within_1': 0,
                'total_runs_within_2': 0,
                'total_runs_accuracy_1': 0,
                'total_runs_accuracy_2': 0,
                'average_score_diff': 0
            },
            'betting_performance': {
                'total_recommendations': 0,
                'correct_recommendations': 0,
                'overall_accuracy': 0,
                'moneyline_stats': {'total': 0, 'correct': 0, 'accuracy': 0},
                'total_stats': {'total': 0, 'correct': 0, 'accuracy': 0},
                'runline_stats': {'total': 0, 'correct': 0, 'accuracy': 0},
                'total_bet_amount': 0,
                'total_winnings': 0,
                'net_profit': 0,
                'roi_percentage': 0
            },
            'daily_breakdown': []
        }
        
        total_score_diff_sum = 0
        total_games_for_avg = 0
        
        for date in available_dates:
            logger.info(f"Analyzing {date}...")
            
            predictions = self.load_predictions_for_date(date)
            final_scores = self.load_final_scores_for_date(date)
            
            if not predictions or not final_scores:
                logger.warning(f"Skipping {date} - missing data")
                continue
            
            # Analyze this date
            model_perf = self.analyze_model_performance(predictions, final_scores)
            betting_perf = self.analyze_betting_recommendations(predictions, final_scores)
            
            # Add to cumulative stats
            cumulative_stats['model_performance']['total_games'] += model_perf['total_games']
            cumulative_stats['model_performance']['winner_correct'] += model_perf['winner_correct']
            cumulative_stats['model_performance']['total_runs_within_1'] += model_perf['total_runs_within_1']
            cumulative_stats['model_performance']['total_runs_within_2'] += model_perf['total_runs_within_2']
            total_score_diff_sum += model_perf['average_score_diff'] * model_perf['total_games']
            total_games_for_avg += model_perf['total_games']
            
            cumulative_stats['betting_performance']['total_recommendations'] += betting_perf['total_recommendations']
            cumulative_stats['betting_performance']['correct_recommendations'] += betting_perf['correct_recommendations']
            cumulative_stats['betting_performance']['total_bet_amount'] += betting_perf['total_bet_amount']
            cumulative_stats['betting_performance']['total_winnings'] += betting_perf['total_winnings']
            
            # Add bet type stats
            for bet_type in ['moneyline_stats', 'total_stats', 'runline_stats']:
                cumulative_stats['betting_performance'][bet_type]['total'] += betting_perf[bet_type]['total']
                cumulative_stats['betting_performance'][bet_type]['correct'] += betting_perf[bet_type]['correct']
            
            # Store daily breakdown
            cumulative_stats['daily_breakdown'].append({
                'date': date,
                'model_performance': model_perf,
                'betting_performance': betting_perf
            })
        
        # Calculate final percentages - LIMITED TO 2 DECIMAL PLACES MAX
        mp = cumulative_stats['model_performance']
        if mp['total_games'] > 0:
            mp['winner_accuracy'] = round((mp['winner_correct'] / mp['total_games']) * 100, 2)
            mp['total_runs_accuracy_1'] = round((mp['total_runs_within_1'] / mp['total_games']) * 100, 2)
            mp['total_runs_accuracy_2'] = round((mp['total_runs_within_2'] / mp['total_games']) * 100, 2)
            mp['average_score_diff'] = round(total_score_diff_sum / total_games_for_avg, 2) if total_games_for_avg > 0 else 0
        
        bp = cumulative_stats['betting_performance']
        if bp['total_recommendations'] > 0:
            bp['overall_accuracy'] = round((bp['correct_recommendations'] / bp['total_recommendations']) * 100, 2)
        
        for bet_type in ['moneyline_stats', 'total_stats', 'runline_stats']:
            if bp[bet_type]['total'] > 0:
                bp[bet_type]['accuracy'] = round((bp[bet_type]['correct'] / bp[bet_type]['total']) * 100, 2)
        
        if bp['total_bet_amount'] > 0:
            bp['net_profit'] = round(bp['total_winnings'] - bp['total_bet_amount'], 2)
            bp['roi_percentage'] = round((bp['net_profit'] / bp['total_bet_amount']) * 100, 2)
        
        logger.info(f"Cumulative analysis complete: {mp['total_games']} games, {bp['total_recommendations']} bets, {bp['roi_percentage']}% ROI")
        # Persist summary to disk with available_dates for fast subsequent loads
        try:
            to_cache = dict(cumulative_stats)
            to_cache['available_dates'] = available_dates
            self._persist_summary_cache(to_cache)
        except Exception:
            pass
        return cumulative_stats

    def count_all_recommendations(self) -> Tuple[int, Dict[str, int]]:
        """Count all betting recommendations found in predictions, regardless of evaluability.

        Returns a tuple of (total_found, per_date_counts).
        """
        total_found = 0
        per_date: Dict[str, int] = {}

        dates = self.get_available_dates()
        for date in dates:
            try:
                predictions = self.load_predictions_for_date(date) or {}
            except Exception:
                predictions = {}
            count = 0
            for _, prediction in predictions.items():
                try:
                    recs = self.extract_game_recommendations(prediction)
                    count += len(recs)
                except Exception:
                    continue
            per_date[date] = count
            total_found += count
        return total_found, per_date

    def analyze_betting_files(self) -> Dict:
        """Evaluate recommendations directly from betting_recommendations_*.json files.

        Returns a dict with cumulative betting performance and a raw total of recs found.
        """
        # Initialize cumulative structure similar to get_cumulative_analysis betting_performance
        cumulative: Dict = {
            'betting_performance': {
                'total_recommendations': 0,
                'correct_recommendations': 0,
                'overall_accuracy': 0,
                'moneyline_stats': {'total': 0, 'correct': 0, 'accuracy': 0},
                'total_stats': {'total': 0, 'correct': 0, 'accuracy': 0},
                'runline_stats': {'total': 0, 'correct': 0, 'accuracy': 0},
                'total_bet_amount': 0,
                'total_winnings': 0,
                'net_profit': 0,
                'roi_percentage': 0
            },
            'raw_total_found': 0,
            # Provide a per-date breakdown so UIs can build a daily table aligned to this evaluation path
            'daily_breakdown': []
        }

        # Find all betting files and deduplicate by date (prefer *_enhanced when both exist)
        all_files = glob.glob(f"{self.data_dir}/betting_recommendations_2025_08_*.json")
        all_files.sort()
        by_date: Dict[str, str] = {}
        for fp in all_files:
            base = os.path.basename(fp)
            date_key = None
            try:
                name_part = base.replace('betting_recommendations_', '').replace('.json', '')
                parts = name_part.split('_')
                if len(parts) >= 3 and parts[0].isdigit():
                    date_key = f"{parts[0]}-{parts[1]}-{parts[2]}"
            except Exception:
                date_key = None
            if not date_key:
                date_key = base
            prev = by_date.get(date_key)
            if prev is None:
                by_date[date_key] = fp
            else:
                if ('enhanced' in base.lower()) and ('enhanced' not in os.path.basename(prev).lower()):
                    by_date[date_key] = fp

        files = [by_date[k] for k in sorted(by_date.keys())]

        import datetime as _dt
        today_str = _dt.date.today().strftime('%Y-%m-%d')

        for fp in files:
            try:
                with open(fp, 'r') as f:
                    data = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to read {fp}: {e}")
                continue

            # Extract date from file or content
            date = data.get('date')
            if not date:
                base = os.path.basename(fp)
                date = base.replace('betting_recommendations_', '').replace('.json', '').replace('_', '-')

            if date < self.start_date:
                continue
            if date == today_str:
                # Skip current day for logging until next day
                continue

            predictions = data.get('games', {}) or {}

            # Count raw recs found in this file
            raw_count = 0
            for _, pred in predictions.items():
                try:
                    raw_count += len(self.extract_game_recommendations(pred))
                except Exception:
                    continue
            cumulative['raw_total_found'] += raw_count

            # Load final scores for evaluation
            final_scores = self.load_final_scores_for_date(date)
            if not final_scores:
                # Can't evaluate this date; move on but keep raw count
                continue

            # Evaluate using existing routine
            day_stats = self.analyze_betting_recommendations(predictions, final_scores)

            bp = cumulative['betting_performance']
            bp['total_recommendations'] += day_stats.get('total_recommendations', 0)
            bp['correct_recommendations'] += day_stats.get('correct_recommendations', 0)
            bp['total_bet_amount'] += day_stats.get('total_bet_amount', 0)
            bp['total_winnings'] += day_stats.get('total_winnings', 0)
            for bt in ['moneyline_stats', 'total_stats', 'runline_stats']:
                bp[bt]['total'] += day_stats.get(bt, {}).get('total', 0)
                bp[bt]['correct'] += day_stats.get(bt, {}).get('correct', 0)

            # Capture per-date stats for downstream daily tables
            cumulative['daily_breakdown'].append({
                'date': date,
                'betting_performance': day_stats
            })

        # Finalize accuracies and ROI
        bp = cumulative['betting_performance']
        if bp['total_recommendations'] > 0:
            bp['overall_accuracy'] = round((bp['correct_recommendations'] / bp['total_recommendations']) * 100, 2)
        for bt in ['moneyline_stats', 'total_stats', 'runline_stats']:
            total = bp[bt]['total']
            if total > 0:
                bp[bt]['accuracy'] = round((bp[bt]['correct'] / total) * 100, 2)
        if bp['total_bet_amount'] > 0:
            bp['net_profit'] = round(bp['total_winnings'] - bp['total_bet_amount'], 2)
            bp['roi_percentage'] = round((bp['net_profit'] / bp['total_bet_amount']) * 100, 2)

        return cumulative

    def analyze_betting_files_gaps(self) -> Dict:
        """Diagnose why some recommendations are not evaluated.

        Returns a dict with counts and categorized reasons per date and overall.
        """
        summary = {
            'overall': {
                'raw_found': 0,
                'with_final_scores': 0,
                'evaluated': 0,
                'skipped': 0,
                'reasons': {}
            },
            'by_date': {}
        }

        def add_reason(bucket: Dict, reason: str):
            bucket['reasons'][reason] = bucket['reasons'].get(reason, 0) + 1

        files = glob.glob(f"{self.data_dir}/betting_recommendations_2025_08_*.json")
        files.sort()
        import datetime
        today_str = datetime.date.today().strftime('%Y-%m-%d')
        for fp in files:
            try:
                with open(fp, 'r') as f:
                    data = json.load(f)
            except Exception:
                continue

            date = data.get('date')
            if not date:
                base = os.path.basename(fp)
                date = base.replace('betting_recommendations_', '').replace('.json', '').replace('_', '-')
            if date < self.start_date:
                continue
            if date == today_str:
                # Exclude current day from diagnostics as it's not logged yet
                continue

            predictions = data.get('games', {}) or {}
            date_bucket = summary['by_date'].setdefault(date, {
                'raw_found': 0,
                'with_final_scores': 0,
                'evaluated': 0,
                'skipped': 0,
                'reasons': {}
            })

            # Load final scores once per date
            final_scores = self.load_final_scores_for_date(date)

            for _, pred in predictions.items():
                recs = []
                try:
                    recs = self.extract_game_recommendations(pred)
                except Exception:
                    pass
                date_bucket['raw_found'] += len(recs)
                summary['overall']['raw_found'] += len(recs)

                # Build normalized key and check final score
                away_team = normalize_team_name(pred.get('away_team', ''))
                home_team = normalize_team_name(pred.get('home_team', ''))
                normalized_key = f"{away_team}_vs_{home_team}"
                fs = final_scores.get(normalized_key)
                if not fs:
                    # None of the recs for this game can be evaluated
                    date_bucket['skipped'] += len(recs)
                    summary['overall']['skipped'] += len(recs)
                    add_reason(date_bucket, 'no_final_score_for_game')
                    add_reason(summary['overall'], 'no_final_score_for_game')
                    continue

                date_bucket['with_final_scores'] += len(recs)
                summary['overall']['with_final_scores'] += len(recs)

                for rec in recs:
                    # Quick validity checks mirroring evaluate_single_bet
                    bet_type = str(rec.get('type', '')).lower()
                    side = str(rec.get('side', '')).lower()
                    line = rec.get('line', 0)

                    if not bet_type or bet_type in ['none', 'unknown']:
                        date_bucket['skipped'] += 1
                        summary['overall']['skipped'] += 1
                        add_reason(date_bucket, 'unsupported_or_missing_bet_type')
                        add_reason(summary['overall'], 'unsupported_or_missing_bet_type')
                        continue

                    if not side:
                        date_bucket['skipped'] += 1
                        summary['overall']['skipped'] += 1
                        add_reason(date_bucket, 'missing_side')
                        add_reason(summary['overall'], 'missing_side')
                        continue

                    if bet_type == 'total' and not (isinstance(line, (int, float)) and line > 0):
                        date_bucket['skipped'] += 1
                        summary['overall']['skipped'] += 1
                        add_reason(date_bucket, 'missing_or_invalid_total_line')
                        add_reason(summary['overall'], 'missing_or_invalid_total_line')
                        continue

                    if bet_type in ['runline', 'run_line'] and not (isinstance(line, (int, float)) and line != 0):
                        date_bucket['skipped'] += 1
                        summary['overall']['skipped'] += 1
                        add_reason(date_bucket, 'missing_or_zero_runline')
                        add_reason(summary['overall'], 'missing_or_zero_runline')
                        continue

                    # If it passes basic checks, consider it evaluated
                    date_bucket['evaluated'] += 1
                    summary['overall']['evaluated'] += 1

        return summary

    def get_missing_side_examples(self, limit: int = 20) -> List[Dict]:
        """Return concrete examples of recommendations missing a resolvable 'side'."""
        examples: List[Dict] = []
        files = glob.glob(f"{self.data_dir}/betting_recommendations_2025_08_*.json")
        files.sort()
        for fp in files:
            try:
                with open(fp, 'r') as f:
                    data = json.load(f)
            except Exception:
                continue
            date = data.get('date')
            if not date:
                base = os.path.basename(fp)
                date = base.replace('betting_recommendations_', '').replace('.json', '').replace('_', '-')
            if date < self.start_date:
                continue
            games = data.get('games', {}) or {}
            for game_key, pred in games.items():
                away_team = normalize_team_name(pred.get('away_team', ''))
                home_team = normalize_team_name(pred.get('home_team', ''))
                # direct recommendations list (some legacy)
                recs = pred.get('recommendations')
                if isinstance(recs, list):
                    for rec in recs:
                        if not isinstance(rec, dict):
                            continue
                        bt = str(rec.get('type', '')).lower()
                        side = str(rec.get('side', '')).lower()
                        if not side and bt in ['total', 'moneyline', 'runline', 'run_line']:
                            examples.append({
                                'date': date,
                                'game': f"{away_team} vs {home_team}",
                                'source': 'recommendations',
                                'type': bt,
                                'recommendation': rec.get('recommendation', ''),
                                'raw': rec
                            })
                            if len(examples) >= limit:
                                return examples
                # unified_value_bets often missing explicit side
                uvb = pred.get('unified_value_bets')
                if isinstance(uvb, list):
                    for bet in uvb:
                        bt = str(bet.get('type', '')).lower()
                        side = str(bet.get('side', '')).lower()
                        rec_text = str(bet.get('recommendation', ''))
                        if not side:
                            examples.append({
                                'date': date,
                                'game': f"{away_team} vs {home_team}",
                                'source': 'unified_value_bets',
                                'type': bt,
                                'recommendation': rec_text,
                                'raw': bet
                            })
                            if len(examples) >= limit:
                                return examples
                # betting_recommendations dict/list with missing side and no parseable text
                br = pred.get('betting_recommendations')
                if isinstance(br, dict):
                    for bt, val in br.items():
                        if not isinstance(val, dict):
                            continue
                        side = str(val.get('side', '')).lower()
                        rec_text = str(val.get('recommendation', ''))
                        if not side and not any(k in rec_text.lower() for k in ['over', 'under', 'home', 'away', away_team.lower(), home_team.lower()] if isinstance(rec_text, str)):
                            examples.append({
                                'date': date,
                                'game': f"{away_team} vs {home_team}",
                                'source': 'betting_recommendations',
                                'type': str(bt).lower(),
                                'recommendation': rec_text,
                                'raw': val
                            })
                            if len(examples) >= limit:
                                return examples
                elif isinstance(br, list):
                    for val in br:
                        if not isinstance(val, dict):
                            continue
                        bt = str(val.get('type', '')).lower()
                        side = str(val.get('side', '')).lower()
                        rec_text = str(val.get('recommendation', ''))
                        if not side and not any(k in rec_text.lower() for k in ['over', 'under', 'home', 'away', away_team.lower(), home_team.lower()] if isinstance(rec_text, str)):
                            examples.append({
                                'date': date,
                                'game': f"{away_team} vs {home_team}",
                                'source': 'betting_recommendations',
                                'type': bt,
                                'recommendation': rec_text,
                                'raw': val
                            })
                            if len(examples) >= limit:
                                return examples
                # value_bets with no side in text (rare, but include if present)
                vb = pred.get('value_bets')
                if isinstance(vb, list):
                    for bet in vb:
                        bt = str(bet.get('type', '')).lower()
                        rec_text = str(bet.get('recommendation', ''))
                        if bt in ['total', 'moneyline', 'runline', 'run_line']:
                            tl = rec_text.lower()
                            implied_side = ''
                            if away_team and away_team.lower() in tl:
                                implied_side = 'away'
                            elif home_team and home_team.lower() in tl:
                                implied_side = 'home'
                            has_side_marker = any(k in tl for k in ['over', 'under', 'home', 'away']) or bool(bet.get('side')) or bool(implied_side)
                            if not has_side_marker:
                                examples.append({
                                    'date': date,
                                    'game': f"{away_team} vs {home_team}",
                                    'source': 'value_bets',
                                    'type': bt,
                                    'recommendation': rec_text,
                                    'raw': bet
                                })
                                if len(examples) >= limit:
                                    return examples
                if len(examples) >= limit:
                    return examples
        return examples

    def collect_gap_samples(self, reason_filter: Optional[str] = None, limit: int = 50) -> Dict[str, List[Dict]]:
        """Collect detailed examples of skipped recommendations grouped by reason.

        reason_filter: if provided, only include that reason.
        limit: maximum examples per reason.
        Returns: { reason: [ examples... ] }
        """
        results: Dict[str, List[Dict]] = {}
        files = glob.glob(f"{self.data_dir}/betting_recommendations_2025_08_*.json")
        files.sort()

        for fp in files:
            try:
                with open(fp, 'r') as f:
                    data = json.load(f)
            except Exception:
                continue
            date = data.get('date')
            if not date:
                base = os.path.basename(fp)
                date = base.replace('betting_recommendations_', '').replace('.json', '').replace('_', '-')
            if date < self.start_date:
                continue

            predictions = data.get('games', {}) or {}
            final_scores = self.load_final_scores_for_date(date)

            for game_key, pred in predictions.items():
                away_team = normalize_team_name(pred.get('away_team', ''))
                home_team = normalize_team_name(pred.get('home_team', ''))
                normalized_key = f"{away_team}_vs_{home_team}"
                fs = final_scores.get(normalized_key)

                try:
                    recs = self.extract_game_recommendations(pred)
                except Exception:
                    recs = []

                if not fs and recs:
                    reason = 'no_final_score_for_game'
                    if not reason_filter or reason_filter == reason:
                        bucket = results.setdefault(reason, [])
                        for rec in recs:
                            if len(bucket) >= limit:
                                break
                            bucket.append({
                                'date': date,
                                'game': normalized_key,
                                'bet_type': rec.get('type'),
                                'side': rec.get('side'),
                                'line': rec.get('line'),
                                'odds': rec.get('odds'),
                                'confidence': rec.get('confidence'),
                                'expected_value': rec.get('expected_value'),
                                'recommendation_text': rec.get('reasoning') or rec.get('recommendation')
                            })
                    continue

                for rec in recs:
                    bet_type = str(rec.get('type', '')).lower()
                    side = str(rec.get('side', '')).lower()
                    line = rec.get('line', 0)
                    reason = None
                    if not bet_type or bet_type in ['none', 'unknown']:
                        reason = 'unsupported_or_missing_bet_type'
                    elif not side:
                        reason = 'missing_side'
                    elif bet_type == 'total' and not (isinstance(line, (int, float)) and line > 0):
                        reason = 'missing_or_invalid_total_line'
                    elif bet_type in ['runline', 'run_line'] and not (isinstance(line, (int, float)) and line != 0):
                        reason = 'missing_or_zero_runline'

                    if reason and (not reason_filter or reason_filter == reason):
                        bucket = results.setdefault(reason, [])
                        if len(bucket) < limit:
                            bucket.append({
                                'date': date,
                                'game': normalized_key,
                                'bet_type': bet_type,
                                'side': side,
                                'line': line,
                                'odds': rec.get('odds'),
                                'confidence': rec.get('confidence'),
                                'expected_value': rec.get('expected_value'),
                                'recommendation_text': rec.get('reasoning') or rec.get('recommendation')
                            })
        return results
    
    def get_date_analysis(self, date: str) -> Dict:
        """Get detailed analysis for a specific date"""
        predictions = self.load_predictions_for_date(date)
        final_scores = self.load_final_scores_for_date(date)
        
        if not predictions:
            return {'error': f'No predictions found for {date}'}
        
        if not final_scores:
            return {'error': f'No final scores found for {date}'}
        
        model_perf = self.analyze_model_performance(predictions, final_scores)
        betting_perf = self.analyze_betting_recommendations(predictions, final_scores)
        
        return {
            'date': date,
            'model_performance': model_perf,
            'betting_performance': betting_perf,
            'predictions': predictions,
            'final_scores': final_scores
        }

# Global analyzer instance
historical_analyzer = ComprehensiveHistoricalAnalyzer()
