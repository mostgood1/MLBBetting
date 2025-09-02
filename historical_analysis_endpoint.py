"""
Historical Analysis Endpoint - Comprehensive Model & Betting Performance Analysis
=============================================================================
This module provides detailed analysis of model predictability, betting accuracy, and ROI
for any historical date with complete predictions and final scores.

Analysis Components:
1. Predictability - Model accuracy on winners and score predictions
2. Betting Lens - Performance from a betting perspective (winners + totals)
3. Betting Recommendations - Analysis of recommendation accuracy and types
4. ROI Analysis - Financial performance assuming $100 unit bets
"""

import json
import os
import logging
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request
from typing import Dict, List, Tuple, Optional
from team_name_normalizer import normalize_team_name

# Setup logging
logger = logging.getLogger(__name__)

# Create Blueprint
historical_analysis_bp = Blueprint('historical_analysis', __name__)

class HistoricalAnalyzer:
    """Comprehensive historical analysis for MLB predictions and betting performance"""
    def log_normalized_keys(self, games: Dict, final_scores: Dict):
        logger.info("--- Normalized Keys Comparison ---")
        logger.info("Betting Recommendations Keys:")
        for game_key, game_data in games.items():
            away = self.normalize_team_name(game_data.get('away_team', ''))
            home = self.normalize_team_name(game_data.get('home_team', ''))
            key = f"{away}_vs_{home}"
            logger.info(f"  {key}")
        logger.info("Final Scores Keys:")
        for score_key in final_scores.keys():
            logger.info(f"  {score_key}")
        logger.info("--- End Comparison ---")
"""
Historical Analysis Endpoint - Comprehensive Model & Betting Performance Analysis
=============================================================================
This module provides detailed analysis of model predictability, betting accuracy, and ROI
for any historical date with complete predictions and final scores.

Analysis Components:
1. Predictability - Model accuracy on winners and score predictions
2. Betting Lens - Performance from a betting perspective (winners + totals)
3. Betting Recommendations - Analysis of recommendation accuracy and types
4. ROI Analysis - Financial performance assuming $100 unit bets
"""

import json
import os
import logging
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request
from typing import Dict, List, Tuple, Optional
from team_name_normalizer import normalize_team_name

# Setup logging
logger = logging.getLogger(__name__)

# Create Blueprint
historical_analysis_bp = Blueprint('historical_analysis', __name__)

class HistoricalAnalyzer:
    """Comprehensive historical analysis for MLB predictions and betting performance"""
    
    def __init__(self):
        self.predictions_cache_path = 'data/unified_predictions_cache.json'
        self.base_scores_path = 'data/final_scores_{date}.json'
        
    def normalize_team_name(self, team_name: str) -> str:
        return normalize_team_name(team_name)

    def parse_american_odds(self, od) -> int:
        """Parse American odds from str/int to int, with safe fallbacks.

        Examples:
        "+110" -> 110, "-120" -> -120, 150 -> 150, "N/A" -> -110 (default)
        """
        try:
            if od is None:
                return -110
            if isinstance(od, (int, float)):
                return int(od)
            s = str(od).strip()
            if not s or s.upper() == 'N/A':
                return -110
            # Normalize unicode minus
            s = s.replace('−', '-')
            if s.startswith('+'):
                s = s[1:]
            return int(float(s))
        except Exception:
            return -110

    def _normalize_rec_type(self, t: str) -> str:
        """Normalize various recommendation type labels into canonical ones.

        Maps: total_runs/totals/over_under -> total; runline/rl/spread -> run_line.
        Defaults to lowercased input when unrecognized.
        """
        if not t:
            return 'other'
        s = str(t).strip().lower()
        if s in ('total_runs', 'totals', 'total', 'over_under', 'o/u'):
            return 'total'
        if s in ('runline', 'run_line', 'rl', 'spread'):
            return 'run_line'
        if s in ('ml', 'money_line', 'moneyline'):
            return 'moneyline'
        if s in ('market analysis', 'market_analysis'):
            return 'market_analysis'
        return s

    def _is_noise_rec(self, rec: Dict) -> bool:
        """Filter out non-bet rows like MARKET ANALYSIS from older files."""
        t = self._normalize_rec_type(rec.get('type'))
        if t == 'market_analysis':
            return True
        cat = str(rec.get('category', '')).strip().lower()
        if cat in ('market analysis', 'market_analysis'):
            return True
        text = str(rec.get('recommendation', '')).strip().lower()
        if 'market analysis' in text:
            return True
        return False

    def _extract_recommendations(self, game_data: Dict) -> List[Dict]:
        """Extract recommendations from a game entry across known formats.

        Returns a list of normalized recommendation dicts with keys:
        - type (moneyline|total|run_line|other), side/recommendation, line, odds/american_odds, expected_value, confidence, reasoning
        """
        # 1) Embedded under prediction.recommendations
        pred_block = game_data.get('prediction')
        if isinstance(pred_block, dict) and 'recommendations' in pred_block:
            recs = pred_block.get('recommendations') or []
        # 2) Direct recommendations
        elif 'recommendations' in game_data:
            recs = game_data.get('recommendations') or []
        else:
            # 3) Unified betting engine embeddings
            br = game_data.get('betting_recommendations', {}) or {}
            recs = br.get('unified_value_bets') or br.get('value_bets') or []
            # 3b) Legacy object keys (moneyline/total_runs/run_line)
            if not recs and isinstance(br, dict) and any(k in br for k in ('moneyline', 'total_runs', 'run_line')):
                legacy: List[Dict] = []
                if br.get('moneyline'):
                    legacy.append({'type': 'moneyline', 'recommendation': br['moneyline']})
                if br.get('total_runs'):
                    legacy.append({'type': 'total', 'recommendation': br['total_runs'], 'line': br.get('line')})
                if br.get('run_line'):
                    legacy.append({'type': 'run_line', 'recommendation': br['run_line'], 'spread': br.get('spread', 1.5)})
                recs = legacy

        # If recommendations is a dict, convert legacy keys to list
        if isinstance(recs, dict):
            legacy: List[Dict] = []
            if recs.get('moneyline'):
                legacy.append({'type': 'moneyline', 'recommendation': recs['moneyline']})
            if recs.get('total_runs'):
                legacy.append({'type': 'total', 'recommendation': recs['total_runs'], 'line': recs.get('line')})
            if recs.get('run_line'):
                legacy.append({'type': 'run_line', 'recommendation': recs['run_line'], 'spread': recs.get('spread', 1.5)})
            recs = legacy

        # Normalize and filter noise
        out: List[Dict] = []
        for r in recs or []:
            if not isinstance(r, dict):
                continue
            if self._is_noise_rec(r):
                continue
            t = self._normalize_rec_type(r.get('type'))
            side = r.get('side', r.get('bet', r.get('recommendation', 'unknown')))
            # Try parse total line from free text if missing
            line = r.get('line')
            if line in (None, '') and t == 'total':
                txt = str(r.get('recommendation', '')).lower()
                # naive parse: look for numbers like 8.5 or 7
                import re
                m = re.search(r'(\d+\.?\d*)', txt)
                if m:
                    try:
                        line = float(m.group(1))
                    except Exception:
                        line = None
            odds = r.get('odds', r.get('american_odds', -110))
            out.append({
                'type': t,
                'side': side,
                'line': line,
                'odds': odds,
                'expected_value': r.get('expected_value', 0),
                'confidence': r.get('confidence', 'UNKNOWN'),
                'reasoning': r.get('reasoning', r.get('notes', '')),
                # keep original fields for any extra checks
                **({k: v for k, v in r.items() if k not in {'type','side','line','odds','american_odds','expected_value','confidence','reasoning'}})
            })
        # If nothing left after filtering, fallback to unified_value_bets under betting_recommendations
        if not out:
            br = game_data.get('betting_recommendations', {}) or {}
            uvb = br.get('unified_value_bets') or br.get('value_bets') or []
            for vb in uvb:
                if not isinstance(vb, dict):
                    continue
                t = self._normalize_rec_type(vb.get('type'))
                if t == 'market_analysis':
                    continue
                side = vb.get('side', vb.get('recommendation', 'unknown'))
                odds = vb.get('odds', vb.get('american_odds', -110))
                out.append({
                    'type': t,
                    'side': side,
                    'line': vb.get('line'),
                    'odds': odds,
                    'expected_value': vb.get('expected_value', 0),
                    'confidence': vb.get('confidence', 'UNKNOWN'),
                    'reasoning': vb.get('reasoning', vb.get('notes', '')),
                })
        return out
    
    def log_normalized_keys(self, games: Dict, final_scores: Dict):
        logger.info("--- Normalized Keys Comparison ---")
        logger.info("Betting Recommendations Keys:")
        for game_key, game_data in games.items():
            away = self.normalize_team_name(game_data.get('away_team', ''))
            home = self.normalize_team_name(game_data.get('home_team', ''))
            key = f"{away}_vs_{home}"
            logger.info(f"  {key}")
        logger.info("Final Scores Keys:")
        for score_key in final_scores.keys():
            logger.info(f"  {score_key}")
        logger.info("--- End Comparison ---")
    
    def load_predictions_for_date(self, target_date: str) -> Dict:
        """Load games from unified_predictions_cache.json for specific date"""
        try:
            with open(self.predictions_cache_path, 'r') as f:
                cache = json.load(f)
            
            predictions_by_date = cache.get('predictions_by_date', {})
            date_data = predictions_by_date.get(target_date, {})
            games = date_data.get('games', {})
            
            if isinstance(games, dict):
                logger.info(f"Loaded {len(games)} games from unified cache for {target_date}")
                if games:
                    # Attempt to enrich with enhanced per-day recommendations if present
                    try:
                        date_formatted = target_date.replace('-', '_')
                        candidate_paths = [
                            os.path.join('data', f'betting_recommendations_{date_formatted}_enhanced.json'),
                            os.path.join('data', f'betting_recommendations_{date_formatted}.json'),
                        ]
                        for rec_path in candidate_paths:
                            if not os.path.exists(rec_path):
                                continue
                            with open(rec_path, 'r') as f:
                                rec_data = json.load(f)
                            egames = rec_data.get('games', {}) or {}
                            if not isinstance(egames, dict) or not egames:
                                continue
                            enrich_count = 0
                            eg_keys = set(egames.keys())
                            for gk, g in games.items():
                                # Create key variants to find match in egames
                                variants = []
                                variants.append(gk)
                                variants.append(gk.replace('_', ' '))
                                away_disp = g.get('away_team') or ''
                                home_disp = g.get('home_team') or ''
                                if away_disp and home_disp:
                                    variants.append(f"{away_disp}_vs_{home_disp}")
                                # Try matching
                                match_key = next((v for v in variants if v in eg_keys), None)
                                if not match_key:
                                    continue
                                egd = egames.get(match_key, {}) or {}
                                # Pull unified_value_bets from enhanced structure
                                uvb = (egd.get('unified_value_bets') or egd.get('value_bets') or [])
                                br = egd.get('betting_recommendations', {}) or {}
                                if not uvb and isinstance(br, dict):
                                    uvb = br.get('unified_value_bets') or br.get('value_bets') or []
                                # Filter out MARKET ANALYSIS
                                uvb_clean = []
                                for vb in uvb:
                                    if isinstance(vb, dict) and self._normalize_rec_type(vb.get('type')) == 'market_analysis':
                                        continue
                                    uvb_clean.append(vb)
                                # Enrich predictive fields when available so analysis can run
                                enriched_any = False
                                if uvb_clean:
                                    existing_br = g.get('betting_recommendations')
                                    if not isinstance(existing_br, dict):
                                        existing_br = {}
                                    existing_br['unified_value_bets'] = uvb_clean
                                    g['betting_recommendations'] = existing_br
                                    enriched_any = True

                                # NEW: Copy nested predictions from per-day structure if present
                                try:
                                    per_day_pred_block = egd.get('predictions') or {}
                                    inner_preds = per_day_pred_block.get('predictions') if isinstance(per_day_pred_block, dict) else None
                                    if isinstance(inner_preds, dict) and inner_preds:
                                        # Ensure a 'prediction' container exists on the unified game
                                        g_prediction = g.get('prediction')
                                        if not isinstance(g_prediction, dict):
                                            g_prediction = {}
                                        # Keep away/home/team/date at prediction level
                                        for k in ('away_team', 'home_team', 'game_date'):
                                            if per_day_pred_block.get(k) is not None:
                                                g_prediction[k] = per_day_pred_block.get(k)
                                        # Copy key numeric predictions and win probs
                                        pred_container = g_prediction.get('predictions')
                                        if not isinstance(pred_container, dict):
                                            pred_container = {}
                                        for src_key, dst_key in [
                                            ('away_win_prob', 'away_win_prob'),
                                            ('home_win_prob', 'home_win_prob'),
                                            ('predicted_away_score', 'predicted_away_score'),
                                            ('predicted_home_score', 'predicted_home_score'),
                                            ('predicted_total_runs', 'predicted_total_runs'),
                                            ('away_score', 'away_score'),
                                            ('home_score', 'home_score'),
                                            ('away_runs', 'away_runs'),
                                            ('home_runs', 'home_runs'),
                                        ]:
                                            if inner_preds.get(src_key) is not None and pred_container.get(dst_key) is None:
                                                pred_container[dst_key] = inner_preds.get(src_key)
                                        g_prediction['predictions'] = pred_container
                                        g['prediction'] = g_prediction
                                        enriched_any = True

                                        # Also expose convenience fields at top-level when missing
                                        if g.get('win_probabilities') is None:
                                            awp = inner_preds.get('away_win_prob')
                                            hwp = inner_preds.get('home_win_prob')
                                            if awp is not None and hwp is not None:
                                                g['win_probabilities'] = {'away_prob': awp, 'home_prob': hwp}
                                                enriched_any = True
                                        # predicted_score string for fallback parsing
                                        if g.get('predicted_score') is None:
                                            pa = inner_preds.get('predicted_away_score')
                                            ph = inner_preds.get('predicted_home_score')
                                            if pa is not None and ph is not None:
                                                try:
                                                    g['predicted_score'] = f"{float(pa)}-{float(ph)}"
                                                    enriched_any = True
                                                except Exception:
                                                    pass
                                except Exception:
                                    # don't let enrichment fail if structure is unexpected
                                    pass

                                # Copy win probabilities if present in per-day game
                                if isinstance(egd.get('win_probabilities'), dict):
                                    g['win_probabilities'] = egd['win_probabilities']
                                    enriched_any = True
                                # Copy predicted score string if present
                                if isinstance(egd.get('predicted_score'), str):
                                    g['predicted_score'] = egd['predicted_score']
                                    enriched_any = True
                                # Also copy explicit predicted score numbers if present
                                for k in ('predicted_away_score','predicted_home_score','away_score','home_score','away_runs','home_runs'):
                                    if k in egd and g.get(k) is None:
                                        g[k] = egd[k]
                                        enriched_any = True
                                # Ensure team names exist on the game object
                                if not g.get('away_team') or not g.get('home_team'):
                                    away_team = egd.get('away_team')
                                    home_team = egd.get('home_team')
                                    if not (away_team and home_team):
                                        # Parse from the match_key if needed
                                        mk = match_key.replace(' @ ', '_vs_').replace(' vs ', '_vs_')
                                        if '_vs_' in mk:
                                            away_team, home_team = mk.split('_vs_', 1)
                                    if away_team and home_team:
                                        g['away_team'] = away_team
                                        g['home_team'] = home_team
                                        enriched_any = True

                                if enriched_any:
                                    enrich_count += 1
                            if enrich_count:
                                logger.info(f"Enriched {enrich_count} games for {target_date} using {os.path.basename(rec_path)}")
                                break
                    except Exception as e:
                        logger.warning(f"Could not enrich unified cache games for {target_date}: {e}")
                    # After enrichment, also merge starting pitchers for this date to replace TBDs
                    try:
                        sp_date = target_date.replace('-', '_')
                        sp_path = os.path.join('data', f'starting_pitchers_{sp_date}.json')
                        if os.path.exists(sp_path):
                            with open(sp_path, 'r') as f:
                                sp_data = json.load(f)
                            sp_map = {}
                            for gsp in sp_data.get('games', []):
                                a = self.normalize_team_name(gsp.get('away_team', ''))
                                h = self.normalize_team_name(gsp.get('home_team', ''))
                                if a and h:
                                    sp_map[(a, h)] = {
                                        'away': gsp.get('away_pitcher', 'TBD'),
                                        'home': gsp.get('home_pitcher', 'TBD')
                                    }
                            updated = 0
                            for gk, g in games.items():
                                try:
                                    away_name = self.normalize_team_name(g.get('away_team', ''))
                                    home_name = self.normalize_team_name(g.get('home_team', ''))
                                    if not (away_name and home_name):
                                        continue
                                    sp = sp_map.get((away_name, home_name))
                                    if not sp:
                                        continue
                                    # Apply if missing or TBD
                                    def is_tbd(v):
                                        return (not v) or str(v).strip().upper() == 'TBD'
                                    ap = g.get('away_pitcher')
                                    hp = g.get('home_pitcher')
                                    new_ap = sp['away'] if is_tbd(ap) else ap
                                    new_hp = sp['home'] if is_tbd(hp) else hp
                                    # Write back to game
                                    if new_ap != ap:
                                        g['away_pitcher'] = new_ap
                                    if new_hp != hp:
                                        g['home_pitcher'] = new_hp
                                    # Mirror into prediction containers for downstream extractors
                                    pred_block = g.get('prediction') or {}
                                    preds = pred_block.get('predictions') or {}
                                    if is_tbd(preds.get('away_pitcher')) and new_ap:
                                        preds['away_pitcher'] = new_ap
                                    if is_tbd(preds.get('home_pitcher')) and new_hp:
                                        preds['home_pitcher'] = new_hp
                                    if preds:
                                        pred_block['predictions'] = preds
                                        g['prediction'] = pred_block
                                    # Also add pitcher_info
                                    pi = g.get('pitcher_info') or {}
                                    if is_tbd(pi.get('away_pitcher_name')) and new_ap:
                                        pi['away_pitcher_name'] = new_ap
                                    if is_tbd(pi.get('home_pitcher_name')) and new_hp:
                                        pi['home_pitcher_name'] = new_hp
                                    if pi:
                                        g['pitcher_info'] = pi
                                    if (new_ap != ap) or (new_hp != hp):
                                        updated += 1
                                except Exception:
                                    continue
                            if updated:
                                logger.info(f"Enriched starting pitchers for {updated} games using {os.path.basename(sp_path)}")
                    except Exception as _e:
                        logger.warning(f"Starting pitchers enrichment failed for {target_date}: {_e}")
                    return games
                # Fall through to legacy per-day files if empty
            else:
                logger.warning(f"Games data for {target_date} is not a dict in unified cache.")
                # continue to fallback
                
        except FileNotFoundError:
            logger.error(f"Unified predictions cache not found: {self.predictions_cache_path}")
            # fallthrough to legacy loader below
        except Exception as e:
            logger.error(f"Error loading unified predictions cache: {e}")
            # continue to legacy loader

        # Legacy/per-day betting recommendations fallback
        try:
            date_formatted = target_date.replace('-', '_')
            candidate_paths = [
                os.path.join('data', f'betting_recommendations_{date_formatted}_enhanced.json'),
                os.path.join('data', f'betting_recommendations_{target_date}.json'),
                os.path.join('data', f'betting_recommendations_{date_formatted}.json'),
            ]
            for rec_path in candidate_paths:
                if not os.path.exists(rec_path):
                    continue
                with open(rec_path, 'r') as f:
                    rec_data = json.load(f)
                games = rec_data.get('games', {})
                if isinstance(games, dict) and games:
                    logger.info(f"Loaded {len(games)} games from betting recommendations fallback for {target_date} ({os.path.basename(rec_path)})")
                    return games
        except Exception as e:
            logger.error(f"Error loading betting recommendations fallback for {target_date}: {e}")
        return {}
    
    def load_final_scores_for_date(self, target_date: str) -> Dict:
        """Load final scores for specific date (robust to dict or list JSON).

        Order of attempts:
        1) Local file data/final_scores_YYYY_MM_DD.json (underscore)
        2) Local file data/final_scores_YYYY-MM-DD.json (dash)
        3) Bundle cache data/historical_final_scores_cache.json[YYYY-MM-DD]
        4) Fallback to comprehensive loader (live fetch or disk) and persist
        """
        # Convert date format: 2025-08-20 -> 2025_08_20
        date_formatted = target_date.replace('-', '_')
        scores_path = self.base_scores_path.format(date=date_formatted)
        scores_path_alt = f"data/final_scores_{target_date}.json"

        def _normalize_items_to_scores(items: List[Dict]) -> Dict[str, Dict]:
            scores_dict: Dict[str, Dict] = {}
            for score in items:
                try:
                    raw_away = score.get('away_team', '')
                    raw_home = score.get('home_team', '')
                    away_team = self.normalize_team_name(raw_away)
                    home_team = self.normalize_team_name(raw_home)
                    if not away_team or not home_team:
                        continue
                    key = f"{away_team}_vs_{home_team}"
                    # Ensure numeric fields exist
                    away_score = score.get('away_score', 0)
                    home_score = score.get('home_score', 0)
                    total_runs = score.get('total_runs', (away_score or 0) + (home_score or 0))
                    winner = score.get('winner')
                    if not winner:
                        winner = 'away' if (away_score or 0) > (home_score or 0) else 'home'
                    base_entry = {
                        'away_team': away_team,
                        'home_team': home_team,
                        'away_team_display': raw_away,
                        'home_team_display': raw_home,
                        'away_score': away_score,
                        'home_score': home_score,
                        'total_runs': total_runs,
                        'winner': winner,
                        'game_pk': score.get('game_pk', ''),
                        'is_final': bool(score.get('is_final', True))
                    }
                    scores_dict[key] = base_entry
                    # Also include a display-name variant key to improve matching in clients
                    if raw_away and raw_home:
                        disp_key = f"{self.normalize_team_name(raw_away)}_vs_{self.normalize_team_name(raw_home)}"
                        scores_dict[disp_key] = base_entry
                except Exception:
                    continue
            return scores_dict

        def _load_from_per_date_file() -> Dict[str, Dict]:
            try:
                path_to_use = scores_path if os.path.exists(scores_path) else (scores_path_alt if os.path.exists(scores_path_alt) else None)
                if not path_to_use:
                    raise FileNotFoundError(scores_path)
                with open(path_to_use, 'r') as f:
                    raw = json.load(f)
                # Normalize to iterable of score dicts
                if isinstance(raw, dict):
                    items = list(raw.values())
                elif isinstance(raw, list):
                    items = raw
                else:
                    items = []
                return _normalize_items_to_scores(items)
            except FileNotFoundError:
                logger.warning(f"Final scores not found: {scores_path} or {scores_path_alt}")
                return {}
            except Exception as e:
                logger.error(f"Error loading final scores from per-date file for {target_date}: {e}")
                return {}

        def _load_from_cache_file() -> Dict[str, Dict]:
            cache_path = os.path.join('data', 'historical_final_scores_cache.json')
            try:
                with open(cache_path, 'r') as f:
                    cache = json.load(f)
                day = cache.get(target_date) or {}
                # day can already be a dict mapping keys->score dicts; normalize to list of score dicts
                if isinstance(day, dict):
                    items = list(day.values())
                elif isinstance(day, list):
                    items = day
                else:
                    items = []
                scores = _normalize_items_to_scores(items)
                if scores:
                    logger.info(f"Loaded {len(scores)} final scores for {target_date} from cache")
                return scores
            except FileNotFoundError:
                logger.warning(f"Final scores cache not found: {cache_path}")
                return {}
            except Exception as e:
                logger.error(f"Error loading final scores from cache for {target_date}: {e}")
                return {}

        # Try per-date file first
        scores_dict = _load_from_per_date_file()
        if not scores_dict:
            # Fallback to cache
            scores_dict = _load_from_cache_file()

        # Last resort: comprehensive loader (live/disk) to hydrate
        if not scores_dict:
            try:
                from comprehensive_historical_analysis import ComprehensiveHistoricalAnalyzer
                cha = ComprehensiveHistoricalAnalyzer()
                scores_dict = cha.load_final_scores_for_date(target_date) or {}
                if scores_dict:
                    # Persist to underscore-style per-date file for future fast loads
                    try:
                        out_path = f"data/final_scores_{date_formatted}.json"
                        with open(out_path, 'w') as f:
                            json.dump(scores_dict, f, indent=2)
                        logger.info(f"Persisted {len(scores_dict)} final scores to {out_path}")
                    except Exception as _pe:
                        logger.warning(f"Could not persist final scores for {target_date}: {_pe}")
            except Exception as _fe:
                logger.warning(f"Comprehensive fallback failed for {target_date}: {_fe}")

        logger.info(f"Loaded {len(scores_dict)} final scores for {target_date}")
        return scores_dict
    
    def extract_prediction_values(self, game_data: Dict) -> Dict:
        """Extract prediction values from game data with robust fallback logic"""
        # Try multiple nested structures to find predictions
        prediction_obj = game_data.get('prediction', game_data)
        predictions = prediction_obj.get('predictions', prediction_obj)
        
        # Extract team names
        away_team = self.normalize_team_name(prediction_obj.get('away_team', game_data.get('away_team', '')))
        home_team = self.normalize_team_name(prediction_obj.get('home_team', game_data.get('home_team', '')))
        
        # Extract win probabilities with multiple fallback keys
        away_win_prob = None
        home_win_prob = None
        
        # First try the old structure
        for key in ['away_win_probability', 'away_win_prob', 'away_win']:
            if away_win_prob is None:
                away_win_prob = predictions.get(key)
        
        for key in ['home_win_probability', 'home_win_prob', 'home_win']:
            if home_win_prob is None:
                home_win_prob = predictions.get(key)
        
        # NEW: Try the unified betting engine structure (win_probabilities object)
        if away_win_prob is None or home_win_prob is None:
            win_probs = game_data.get('win_probabilities', {})
            if win_probs:
                away_win_prob = win_probs.get('away_prob', away_win_prob)
                home_win_prob = win_probs.get('home_prob', home_win_prob)
        
        # Extract predicted scores with fallback keys
        predicted_away = None
        predicted_home = None
        
        # First try the old structure
        for key in ['predicted_away_score', 'away_score', 'away_runs']:
            if predicted_away is None:
                predicted_away = predictions.get(key)
        
        for key in ['predicted_home_score', 'home_score', 'home_runs']:
            if predicted_home is None:
                predicted_home = predictions.get(key)
        
        # NEW: Try parsing the unified betting engine's "predicted_score" string format
        if predicted_away is None or predicted_home is None:
            predicted_score_str = game_data.get('predicted_score', '')
            if predicted_score_str and '-' in predicted_score_str:
                try:
                    parts = predicted_score_str.split('-')
                    if len(parts) == 2:
                        predicted_away = float(parts[0])
                        predicted_home = float(parts[1])
                except (ValueError, IndexError):
                    pass
        
        # Extract pitchers with robust fallbacks to avoid TBD
        def coalesce_pitcher(primary: Optional[str], *candidates: Optional[str]) -> Optional[str]:
            # Return the first non-empty, non-'TBD' value
            def is_real(v: Optional[str]) -> bool:
                return bool(v) and str(v).strip().upper() != 'TBD'
            if is_real(primary):
                return primary
            for c in candidates:
                if is_real(c):
                    return c
            # fallback to primary (even if TBD) for consistency
            return primary if primary else 'TBD'

        # Base values from common locations
        away_pitcher_base = predictions.get('away_pitcher', game_data.get('away_pitcher'))
        home_pitcher_base = predictions.get('home_pitcher', game_data.get('home_pitcher'))

        # Pitcher info object (preferred)
        pi = prediction_obj.get('pitcher_info') or game_data.get('pitcher_info') or {}
        pi_away = pi.get('away_pitcher_name') or pi.get('away_name') or pi.get('away')
        pi_home = pi.get('home_pitcher_name') or pi.get('home_name') or pi.get('home')

        # Other common fields used around the codebase
        alt_away = (
            predictions.get('away_pitcher_name') or game_data.get('away_pitcher_name') or
            predictions.get('away_probable_pitcher') or game_data.get('away_probable_pitcher') or
            predictions.get('away_starter') or game_data.get('away_starter')
        )
        alt_home = (
            predictions.get('home_pitcher_name') or game_data.get('home_pitcher_name') or
            predictions.get('home_probable_pitcher') or game_data.get('home_probable_pitcher') or
            predictions.get('home_starter') or game_data.get('home_starter')
        )

        away_pitcher = coalesce_pitcher(away_pitcher_base, pi_away, alt_away)
        home_pitcher = coalesce_pitcher(home_pitcher_base, pi_home, alt_home)
        
        return {
            'away_team': away_team,
            'home_team': home_team,
            'away_win_probability': away_win_prob,
            'home_win_probability': home_win_prob,
            'predicted_away_score': predicted_away,
            'predicted_home_score': predicted_home,
            'away_pitcher': away_pitcher,
            'home_pitcher': home_pitcher
        }
    
    def analyze_predictability(self, games: Dict, final_scores: Dict) -> Dict:
        """Analyze model predictability - winner accuracy and score accuracy.

        Adds breakdown for away/home score errors and % of games with total error within 1 and 2 runs.
        Uses robust final-score key matching (vs/@ and reversed).
        """
        self.log_normalized_keys(games, final_scores)

        total_games = len(games)
        matched_games = 0
        winner_correct = 0

        team_score_errors: List[float] = []
        away_score_errors: List[float] = []
        home_score_errors: List[float] = []
        total_score_errors: List[float] = []
        total_within_1 = 0
        total_within_2 = 0

        for game_key, game_data in games.items():
            pred_values = self.extract_prediction_values(game_data)

            # Need at least team names to attempt a match
            if not pred_values['away_team'] or not pred_values['home_team']:
                continue

            # Robust final score matching
            away_norm = self.normalize_team_name(pred_values['away_team'])
            home_norm = self.normalize_team_name(pred_values['home_team'])
            candidates = [
                f"{away_norm}_vs_{home_norm}",
                f"{away_norm} @ {home_norm}",
                f"{home_norm}_vs_{away_norm}",
                f"{home_norm} @ {away_norm}",
            ]
            final_score = None
            for ck in candidates:
                final_score = final_scores.get(ck)
                if final_score:
                    break
            if not final_score:
                continue
            matched_games += 1

            # Winner accuracy if we have win probabilities
            awp = pred_values.get('away_win_probability')
            hwp = pred_values.get('home_win_probability')
            if awp is not None and hwp is not None:
                try:
                    away_prob_float = float(awp)
                    home_prob_float = float(hwp)
                    predicted_winner = pred_values['away_team'] if away_prob_float > home_prob_float else pred_values['home_team']
                    actual_winner = pred_values['away_team'] if float(final_score['away_score']) > float(final_score['home_score']) else pred_values['home_team']
                    if self.normalize_team_name(predicted_winner) == self.normalize_team_name(actual_winner):
                        winner_correct += 1
                except Exception:
                    pass

            # Score errors if we have predicted scores
            pa = pred_values.get('predicted_away_score')
            ph = pred_values.get('predicted_home_score')
            if pa is not None and ph is not None:
                try:
                    pred_away = float(pa)
                    pred_home = float(ph)
                    actual_away = float(final_score['away_score'])
                    actual_home = float(final_score['home_score'])

                    away_err = abs(pred_away - actual_away)
                    home_err = abs(pred_home - actual_home)
                    team_score_errors.extend([away_err, home_err])
                    away_score_errors.append(away_err)
                    home_score_errors.append(home_err)

                    total_err = abs((pred_away + pred_home) - (actual_away + actual_home))
                    total_score_errors.append(total_err)
                    if total_err <= 1.0:
                        total_within_1 += 1
                    if total_err <= 2.0:
                        total_within_2 += 1
                except Exception:
                    pass

        return {
            'total_games': total_games,
            'matched_games': matched_games,
            'winner_accuracy': round(winner_correct / matched_games, 4) if matched_games > 0 else 0.0,
            'avg_team_score_error': round(sum(team_score_errors) / len(team_score_errors), 2) if team_score_errors else 0.0,
            'avg_total_score_error': round(sum(total_score_errors) / len(total_score_errors), 2) if total_score_errors else 0.0,
            'avg_away_score_error': round(sum(away_score_errors) / len(away_score_errors), 2) if away_score_errors else 0.0,
            'avg_home_score_error': round(sum(home_score_errors) / len(home_score_errors), 2) if home_score_errors else 0.0,
            'percent_total_within_1': round((total_within_1 / matched_games) * 100, 2) if matched_games > 0 else 0.0,
            'percent_total_within_2': round((total_within_2 / matched_games) * 100, 2) if matched_games > 0 else 0.0,
            'count_total_within_1': total_within_1,
            'count_total_within_2': total_within_2,
            'coverage_rate': round(matched_games / total_games, 4) if total_games > 0 else 0.0
        }
    
    def analyze_betting_lens(self, games: Dict, final_scores: Dict) -> Dict:
        """Analyze performance from betting perspective - winners and totals"""
        winner_correct = 0
        total_side_correct = 0
        total_bets = 0
        total_side_bets = 0
        matched_games = 0
        
        for game_key, game_data in games.items():
            pred_values = self.extract_prediction_values(game_data)
            # Skip if essential data missing
            if not all([pred_values['away_team'], pred_values['home_team']]):
                continue
            # Find matching final score using robust normalization
            away_norm = self.normalize_team_name(pred_values['away_team'])
            home_norm = self.normalize_team_name(pred_values['home_team'])
            score_key_vs = f"{away_norm}_vs_{home_norm}"
            score_key_at = f"{away_norm} @ {home_norm}"
            final_score = final_scores.get(score_key_vs)
            if not final_score:
                final_score = final_scores.get(score_key_at)
            if not final_score:
                # Try reverse order
                score_key_vs_rev = f"{home_norm}_vs_{away_norm}"
                score_key_at_rev = f"{home_norm} @ {away_norm}"
                final_score = final_scores.get(score_key_vs_rev)
                if not final_score:
                    final_score = final_scores.get(score_key_at_rev)
            if not final_score:
                continue
            matched_games += 1
            
            # Winner betting analysis (if we have win probabilities)
            if (pred_values['away_win_probability'] is not None and 
                pred_values['home_win_probability'] is not None):
                total_bets += 1
                away_prob = float(pred_values['away_win_probability'])
                home_prob = float(pred_values['home_win_probability'])
                predicted_winner = (pred_values['away_team'] 
                                  if away_prob > home_prob 
                                  else pred_values['home_team'])
                actual_away_score = final_score['away_score']
                actual_home_score = final_score['home_score']
                actual_winner = (pred_values['away_team'] 
                               if actual_away_score > actual_home_score 
                               else pred_values['home_team'])
                if self.normalize_team_name(predicted_winner) == self.normalize_team_name(actual_winner):
                    winner_correct += 1
            
            # Total betting analysis (if we have score predictions)
            if (pred_values['predicted_away_score'] is not None and 
                pred_values['predicted_home_score'] is not None):
                
                total_side_bets += 1
                pred_total = float(pred_values['predicted_away_score']) + float(pred_values['predicted_home_score'])
                actual_total = final_score['away_score'] + final_score['home_score']
                
                # For betting analysis, assume we would bet the side with larger edge
                # This is simplified - in reality we'd need betting lines
                if abs(pred_total - 8.5) > 0.5:  # Using 8.5 as typical MLB total
                    if pred_total > 8.5 and actual_total > 8.5:  # Bet Over, Over hit
                        total_side_correct += 1
                    elif pred_total < 8.5 and actual_total < 8.5:  # Bet Under, Under hit
                        total_side_correct += 1
        
        return {
            'matched_games': matched_games,
            'winner_accuracy': round(winner_correct / total_bets, 4) if total_bets > 0 else 0.0,
            'total_side_accuracy': round(total_side_correct / total_side_bets, 4) if total_side_bets > 0 else 0.0,
            'total_winner_bets': total_bets,
            'total_side_bets': total_side_bets
        }
    
    def analyze_betting_recommendations(self, games: Dict, final_scores: Dict) -> Dict:
        """Analyze betting recommendations accuracy and types"""
        recommendation_types = {'moneyline': 0, 'total': 0, 'run_line': 0, 'other': 0}
        correct_recommendations = {'moneyline': 0, 'total': 0, 'run_line': 0, 'other': 0}
        total_recommendations = 0
        total_correct = 0
        games_with_recommendations = []
        
        for game_key, game_data in games.items():
            pred_values = self.extract_prediction_values(game_data)
            
            # Skip if no team data
            if not all([pred_values['away_team'], pred_values['home_team']]):
                continue
            
            # Find matching final score
            away_norm = self.normalize_team_name(pred_values['away_team'])
            home_norm = self.normalize_team_name(pred_values['home_team'])
            score_key = f"{away_norm}_vs_{home_norm}"
            
            final_score = final_scores.get(score_key)
            if not final_score:
                continue
            
            # Extract betting recommendations - handle nested/legacy structures
            recommendations = self._extract_recommendations(game_data)
            
            game_analysis = {
                'game_key': game_key,
                'away_team': pred_values['away_team'],
                'home_team': pred_values['home_team'],
                'recommendations': [],
                'total_correct': 0,
                'total_recommendations': len(recommendations)
            }
            
            for rec in recommendations:
                total_recommendations += 1
                rec_type = self._normalize_rec_type(rec.get('type', 'other'))
                
                # Count recommendation type
                if rec_type in recommendation_types:
                    recommendation_types[rec_type] += 1
                else:
                    recommendation_types['other'] += 1
                
                # Check if recommendation was correct
                is_correct = self.check_recommendation_accuracy(rec, final_score, pred_values)
                
                rec_analysis = {
                    'type': rec_type,
                    'side': rec.get('side', rec.get('recommendation', 'unknown')),
                    'line': rec.get('line', 0),
                    'odds': rec.get('odds', rec.get('odds', 0)),
                    'expected_value': rec.get('expected_value', 0),
                    'confidence': rec.get('confidence', 'UNKNOWN'),
                    'reasoning': rec.get('reasoning', ''),
                    'is_correct': is_correct,
                    'payout': self._calculate_payout(rec, is_correct)
                }
                
                game_analysis['recommendations'].append(rec_analysis)
                
                if is_correct:
                    total_correct += 1
                    game_analysis['total_correct'] += 1
                    if rec_type in correct_recommendations:
                        correct_recommendations[rec_type] += 1
                    else:
                        correct_recommendations['other'] += 1
            
            if recommendations:
                games_with_recommendations.append(game_analysis)
        
        # Calculate accuracy by type
        accuracy_by_type = {}
        for rec_type in recommendation_types:
            total_type = recommendation_types[rec_type]
            correct_type = correct_recommendations[rec_type]
            accuracy_by_type[rec_type] = round(correct_type / total_type, 4) if total_type > 0 else 0.0
        
        return {
            'total_recommendations': total_recommendations,
            'total_correct': total_correct,
            'overall_accuracy': round(total_correct / total_recommendations, 4) if total_recommendations > 0 else 0.0,
            'recommendation_types': recommendation_types,
            'accuracy_by_type': accuracy_by_type,
            'games_with_recommendations': games_with_recommendations
        }
    
    def check_recommendation_accuracy(self, recommendation: Dict, final_score: Dict, pred_values: Dict) -> bool:
        """Check if a specific recommendation was correct"""
        rec_type = self._normalize_rec_type(recommendation.get('type', ''))
        
        if rec_type == 'moneyline':
            # Extract team from recommendation
            side_field = str(recommendation.get('side', '')).strip().lower()
            bet_field = str(recommendation.get('bet', '')).strip().lower()
            rec_text = str(recommendation.get('recommendation', '')).strip()
            
            # Determine actual winner
            actual_winner = (pred_values['away_team'] 
                           if final_score['away_score'] > final_score['home_score'] 
                           else pred_values['home_team'])
            
            # Check if recommendation matches actual winner
            away_norm = self.normalize_team_name(pred_values['away_team'])
            home_norm = self.normalize_team_name(pred_values['home_team'])
            # Side hints
            if side_field in ('away', 'visitor') or bet_field in ('away', 'visitor'):
                return actual_winner == pred_values['away_team']
            if side_field in ('home', 'host') or bet_field in ('home', 'host'):
                return actual_winner == pred_values['home_team']
            # Team name text
            rec_norm = self.normalize_team_name(rec_text)
            return (rec_norm and rec_norm in away_norm and actual_winner == pred_values['away_team']) or \
                   (rec_norm and rec_norm in home_norm and actual_winner == pred_values['home_team'])
        
        elif rec_type == 'total':
            # Extract over/under and line from recommendation
            side = str(recommendation.get('side', '')).lower()
            rec_text = str(recommendation.get('recommendation', '')).lower()
            line = recommendation.get('line', 8.5)  # Default line
            
            actual_total = final_score['away_score'] + final_score['home_score']
            
            # Check side from explicit field first, then text
            if side == 'over' or 'over' in rec_text:
                return actual_total > line
            elif side == 'under' or 'under' in rec_text:
                return actual_total < line
            
        elif rec_type == 'run_line':
            # Run line analysis - simplified
            rec_text = str(recommendation.get('recommendation', '')).lower()
            spread = recommendation.get('spread', 1.5)
            
            score_diff = abs(final_score['away_score'] - final_score['home_score'])
            
            if 'favorite' in rec_text or 'cover' in rec_text:
                return score_diff > spread
            else:
                return score_diff <= spread
        
        return False
    
    def _calculate_payout(self, recommendation: Dict, is_correct: bool, unit_size: float = 100.0) -> float:
        """Calculate payout for a recommendation"""
        if not is_correct:
            return -unit_size  # Lost the bet
        
        # Get odds - handle different formats
        raw_odds = recommendation.get('odds')
        if raw_odds in (None, '', 'N/A'):
            raw_odds = recommendation.get('american_odds', -110)
        odds = self.parse_american_odds(raw_odds)
        
        # Convert American odds to payout multiplier
        if odds > 0:
            # Positive odds: $100 bet wins $odds
            payout_multiplier = odds / 100
        else:
            # Negative odds: Need to bet $|odds| to win $100
            payout_multiplier = 100 / abs(odds)
        
        return unit_size * payout_multiplier
    
    def calculate_roi(self, games: Dict, final_scores: Dict, unit_size: float = 100.0) -> Dict:
        """Calculate ROI assuming $100 unit bets on all recommendations"""
        total_bet = 0.0
        total_winnings = 0.0
        total_bets_placed = 0
        winning_bets = 0
        game_results = []
        
        # Simplified odds for calculation (in reality, would use actual betting lines)
        default_odds = {
            'moneyline': -110,  # Typical moneyline odds
            'total': -110,      # Typical total odds
            'run_line': -110    # Typical run line odds
        }
        
        for game_key, game_data in games.items():
            pred_values = self.extract_prediction_values(game_data)
            
            # Skip if no team data
            if not all([pred_values['away_team'], pred_values['home_team']]):
                continue
            
            # Find matching final score
            away_norm = self.normalize_team_name(pred_values['away_team'])
            home_norm = self.normalize_team_name(pred_values['home_team'])
            score_key = f"{away_norm}_vs_{home_norm}"
            
            final_score = final_scores.get(score_key)
            if not final_score:
                continue
            
            # Extract betting recommendations - handle nested/legacy structures
            recommendations = self._extract_recommendations(game_data)
            
            game_profit = 0.0
            game_bets = 0
            game_wins = 0
            game_bet_details = []
            
            for rec in recommendations:
                total_bets_placed += 1
                total_bet += unit_size
                game_bets += 1
                
                # Check if bet won
                is_correct = self.check_recommendation_accuracy(rec, final_score, pred_values)
                
                # Calculate winnings based on odds
                rec_type = self._normalize_rec_type(rec.get('type', 'other'))
                raw_odds = rec.get('odds')
                if raw_odds in (None, '', 'N/A'):
                    raw_odds = rec.get('american_odds')
                if raw_odds in (None, '', 'N/A'):
                    raw_odds = default_odds.get(rec_type, -110)
                odds = self.parse_american_odds(raw_odds)
                
                bet_profit = 0.0
                if is_correct:
                    winning_bets += 1
                    game_wins += 1
                    
                    if odds > 0:
                        # Positive odds: bet $100 to win $odds
                        winnings = unit_size + (unit_size * odds / 100)
                        bet_profit = unit_size * odds / 100
                    else:
                        # Negative odds: bet $|odds| to win $100
                        winnings = unit_size + (unit_size * 100 / abs(odds))
                        bet_profit = unit_size * 100 / abs(odds)
                    
                    total_winnings += winnings
                    game_profit += bet_profit
                else:
                    # Lost the bet
                    game_profit -= unit_size
                
                game_bet_details.append({
                    'type': rec_type,
                    'side': rec.get('side', 'unknown'),
                    'line': rec.get('line', 0),
                    'odds': odds,
                    'is_correct': is_correct,
                    'profit': bet_profit if is_correct else -unit_size
                })
            
            if game_bets > 0:
                game_results.append({
                    'game_key': game_key,
                    'away_team': pred_values['away_team'],
                    'home_team': pred_values['home_team'],
                    'final_score': f"{final_score['away_score']}-{final_score['home_score']}",
                    'total_bets': game_bets,
                    'winning_bets': game_wins,
                    'profit': round(game_profit, 2),
                    'bet_details': game_bet_details
                })
        
        net_profit = total_winnings - total_bet
        roi_percentage = (net_profit / total_bet * 100) if total_bet > 0 else 0.0
        win_rate = (winning_bets / total_bets_placed) if total_bets_placed > 0 else 0.0
        
        return {
            'total_bets_placed': total_bets_placed,
            'total_amount_bet': round(total_bet, 2),
            'total_winnings': round(total_winnings, 2),
            'net_profit': round(net_profit, 2),
            'roi_percentage': round(roi_percentage, 2),
            'win_rate': round(win_rate, 4),
            'winning_bets': winning_bets,
            'unit_size': unit_size,
            'game_results': game_results
        }
    
    def analyze_individual_games(self, games: Dict, final_scores: Dict) -> List[Dict]:
        """Analyze each game individually for detailed breakdown"""
        game_cards = []
        
        for game_key, game_data in games.items():
            pred_values = self.extract_prediction_values(game_data)
            
            # Skip if no team data
            if not all([pred_values['away_team'], pred_values['home_team']]):
                continue
            
            # Find matching final score
            away_norm = self.normalize_team_name(pred_values['away_team'])
            home_norm = self.normalize_team_name(pred_values['home_team'])
            score_key = f"{away_norm}_vs_{home_norm}"
            
            final_score = final_scores.get(score_key)
            
            # Model Predictability Analysis
            predictability = {
                'winner_correct': False,
                'away_score_error': None,
                'home_score_error': None,
                'total_score_error': None,
                'confidence': pred_values.get('confidence', 0)
            }
            
            if final_score:
                # Winner prediction accuracy
                if (pred_values['away_win_probability'] and pred_values['home_win_probability']):
                    away_prob = float(pred_values['away_win_probability'])
                    home_prob = float(pred_values['home_win_probability'])
                    predicted_winner = (pred_values['away_team'] 
                                     if away_prob > home_prob 
                                     else pred_values['home_team'])
                    actual_winner = (pred_values['away_team'] 
                                   if float(final_score['away_score']) > float(final_score['home_score']) 
                                   else pred_values['home_team'])
                    predictability['winner_correct'] = predicted_winner == actual_winner
                
                # Score prediction accuracy
                if pred_values['predicted_away_score'] is not None:
                    predictability['away_score_error'] = abs(float(pred_values['predicted_away_score']) - final_score['away_score'])
                if pred_values['predicted_home_score'] is not None:
                    predictability['home_score_error'] = abs(float(pred_values['predicted_home_score']) - final_score['home_score'])
                if (pred_values['predicted_away_score'] is not None and pred_values['predicted_home_score'] is not None):
                    pred_total = float(pred_values['predicted_away_score']) + float(pred_values['predicted_home_score'])
                    actual_total = final_score['away_score'] + final_score['home_score']
                    predictability['total_score_error'] = abs(pred_total - actual_total)
            
            # Betting Analysis
            betting_analysis = {
                'winner_bet_correct': predictability['winner_correct'],
                'total_bet_correct': None,
                'over_under_recommendation': None
            }
            
            if (final_score and pred_values['predicted_away_score'] is not None and 
                pred_values['predicted_home_score'] is not None):
                pred_total = float(pred_values['predicted_away_score']) + float(pred_values['predicted_home_score'])
                actual_total = final_score['away_score'] + final_score['home_score']
                
                # Assume standard 8.5 total line for betting analysis
                if abs(pred_total - 8.5) > 0.5:
                    betting_analysis['over_under_recommendation'] = 'Over' if float(pred_total) > 8.5 else 'Under'
                    if float(pred_total) > 8.5 and float(actual_total) > 8.5:
                        betting_analysis['total_bet_correct'] = True
                    elif float(pred_total) < 8.5 and float(actual_total) < 8.5:
                        betting_analysis['total_bet_correct'] = True
                    else:
                        betting_analysis['total_bet_correct'] = False
            
            # Recommendations Analysis using unified extractor
            raw_recommendations = self._extract_recommendations(game_data)
            recommendations = []
            for rec in raw_recommendations:
                # Normalize odds
                odds_val = self.parse_american_odds(rec.get('odds'))
                norm_rec = {
                    'type': rec.get('type', 'unknown'),
                    'side': rec.get('side', 'unknown'),
                    'line': rec.get('line', 0),
                    'odds': odds_val,
                    'expected_value': rec.get('expected_value', 0),
                    'confidence': rec.get('confidence', 'UNKNOWN'),
                    'reasoning': rec.get('reasoning', ''),
                    'is_correct': False,
                    'profit': 0.0
                }
                if final_score:
                    norm_rec['is_correct'] = self.check_recommendation_accuracy(norm_rec, final_score, pred_values)
                    norm_rec['profit'] = self._calculate_payout(norm_rec, norm_rec['is_correct'], 100.0)
                recommendations.append(norm_rec)
            
            # ROI for this game
            game_roi = {
                'total_bets': len(recommendations),
                'winning_bets': sum(1 for r in recommendations if r['is_correct']),
                'total_profit': sum(r['profit'] for r in recommendations),
                'win_rate': (sum(1 for r in recommendations if r['is_correct']) / len(recommendations)) if recommendations else 0
            }
            
            game_card = {
                'game_key': game_key,
                'away_team': pred_values['away_team'],
                'home_team': pred_values['home_team'],
                'away_pitcher': pred_values.get('away_pitcher', 'TBD'),
                'home_pitcher': pred_values.get('home_pitcher', 'TBD'),
                'predicted_scores': {
                    'away': pred_values['predicted_away_score'],
                    'home': pred_values['predicted_home_score'],
                    'total': (float(pred_values['predicted_away_score']) + float(pred_values['predicted_home_score'])) 
                            if (pred_values['predicted_away_score'] is not None and pred_values['predicted_home_score'] is not None) else None
                },
                'final_scores': final_score if final_score else {'away_score': None, 'home_score': None},
                'win_probabilities': {
                    'away': pred_values['away_win_probability'],
                    'home': pred_values['home_win_probability']
                },
                'predictability': predictability,
                'betting_analysis': betting_analysis,
                'recommendations': recommendations,
                'roi': game_roi,
                'has_final_score': final_score is not None
            }
            
            game_cards.append(game_card)
        
        return game_cards

    def get_available_dates(self) -> List[str]:
        """Get list of available dates from cache and legacy per-day recommendation files."""
        dates_set = set()
        # From unified cache
        try:
            with open(self.predictions_cache_path, 'r') as f:
                cache = json.load(f)
            for date_str in (cache.get('predictions_by_date', {}) or {}).keys():
                dates_set.add(date_str)
        except Exception as e:
            logger.warning(f"Unable to read unified cache dates: {e}")

        # From data/betting_recommendations_*.json
        try:
            data_dir = 'data'
            if os.path.isdir(data_dir):
                for fn in os.listdir(data_dir):
                    if not fn.startswith('betting_recommendations_') or not fn.endswith('.json'):
                        continue
                    # Expect forms like betting_recommendations_2025_08_22[_enhanced].json
                    base = fn[len('betting_recommendations_'):-len('.json')]
                    base = base.replace('_enhanced', '')
                    # Normalize to YYYY-MM-DD
                    if '_' in base:
                        parts = base.split('_')
                        if len(parts) == 3 and all(p.isdigit() for p in parts):
                            try:
                                y, m, d = parts
                                dates_set.add(f"{y}-{m}-{d}")
                            except Exception:
                                pass
                    elif '-' in base:
                        # already dash format
                        dates_set.add(base)
        except Exception as e:
            logger.warning(f"Unable to read legacy recommendation dates: {e}")

        return sorted(dates_set)
    
    def perform_cumulative_analysis(self, start_date: str = None, end_date: str = None) -> Dict:
        """Perform cumulative analysis across all available dates within [start_date, end_date].

        Defaults:
        - start_date: 2025-08-15
        - end_date: day before today ("yesterday")
        """
        available_dates = self.get_available_dates()

        if not available_dates:
            return {
                'error': 'No historical data available',
                'available_dates': []
            }

        # Default bounds
        if start_date is None:
            start_date = '2025-08-15'
        if end_date is None:
            end_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        # Filter to inclusive range [start_date, end_date]
        available_dates = [d for d in available_dates if start_date <= d <= end_date]

        if not available_dates:
            return {
                'error': f'No data available since {start_date}',
                'available_dates': self.get_available_dates()
            }

        logger.info(f"Performing cumulative analysis for dates: {available_dates}")

        # Aggregate data across all dates
        daily_summaries: List[Dict] = []

        total_predictions = 0
        total_matched = 0
        total_winner_correct = 0
        total_recommendations = 0
        total_rec_correct = 0
        total_bet_amount = 0.0
        total_winnings = 0.0
        total_bets_placed = 0
        winning_bets = 0

        team_score_errors: List[float] = []
        total_score_errors: List[float] = []
        away_score_errors_all: List[float] = []
        home_score_errors_all: List[float] = []
        cum_total_within_1 = 0
        cum_total_within_2 = 0
        cum_matched_games = 0

        for date in available_dates:
            # Get daily analysis
            daily_analysis = self.perform_complete_analysis(date)

            if 'error' in daily_analysis:
                logger.warning(f"Skipping {date}: {daily_analysis['error']}")
                continue

            # Track daily summary (model reliability focused)
            pred_day = daily_analysis.get('predictability', {})
            matched_games = pred_day.get('matched_games', 0)
            daily_summary = {
                'date': date,
                # For model reliability, show matched predictions as games
                'games': matched_games,
                'winner_accuracy': pred_day.get('winner_accuracy', 0.0),
                'avg_team_score_error': pred_day.get('avg_team_score_error', 0.0),
                'avg_total_score_error': pred_day.get('avg_total_score_error', 0.0),
                'avg_away_score_error': pred_day.get('avg_away_score_error', 0.0),
                'avg_home_score_error': pred_day.get('avg_home_score_error', 0.0),
                'percent_total_within_1': pred_day.get('percent_total_within_1', 0.0),
                'percent_total_within_2': pred_day.get('percent_total_within_2', 0.0),
                # Keep additional fields for other pages (not used on model page)
                'rec_accuracy': daily_analysis['betting_recommendations']['overall_accuracy'],
                'roi': daily_analysis['roi_analysis'].get('roi_percentage', 0.0),
                'profit': daily_analysis['roi_analysis'].get('net_profit', 0.0),
                'total_bets': daily_analysis['roi_analysis'].get('total_bets_placed', 0)
            }
            daily_summaries.append(daily_summary)

            # Aggregate metrics
            pred = daily_analysis['predictability']
            total_predictions += pred['total_games']
            total_matched += pred['matched_games']
            cum_matched_games += pred['matched_games']
            cum_total_within_1 += pred.get('count_total_within_1', 0)
            cum_total_within_2 += pred.get('count_total_within_2', 0)

            # Count correct winners across all matched games
            if pred['matched_games'] > 0:
                total_winner_correct += int(pred['winner_accuracy'] * pred['matched_games'])

            # Aggregate recommendation data
            rec = daily_analysis['betting_recommendations']
            total_recommendations += rec['total_recommendations']
            total_rec_correct += rec['total_correct']

            # Aggregate ROI data
            roi = daily_analysis['roi_analysis']
            total_bet_amount += roi['total_amount_bet']
            total_winnings += roi['total_winnings']
            total_bets_placed += roi['total_bets_placed']
            winning_bets += roi['winning_bets']

            # Aggregate errors for game cards that have final scores
            for card in daily_analysis['game_cards']:
                if card['has_final_score'] and card['predictability']:
                    if card['predictability']['away_score_error'] is not None:
                        team_score_errors.append(card['predictability']['away_score_error'])
                        away_score_errors_all.append(card['predictability']['away_score_error'])
                    if card['predictability']['home_score_error'] is not None:
                        team_score_errors.append(card['predictability']['home_score_error'])
                        home_score_errors_all.append(card['predictability']['home_score_error'])
                    if card['predictability']['total_score_error'] is not None:
                        total_score_errors.append(card['predictability']['total_score_error'])

        # Calculate cumulative metrics
        cumulative_winner_accuracy = total_winner_correct / total_matched if total_matched > 0 else 0.0
        cumulative_rec_accuracy = total_rec_correct / total_recommendations if total_recommendations > 0 else 0.0
        net_profit = total_winnings - total_bet_amount
        cumulative_roi = (net_profit / total_bet_amount * 100) if total_bet_amount > 0 else 0.0
        cumulative_win_rate = winning_bets / total_bets_placed if total_bets_placed > 0 else 0.0
        avg_team_score_error = sum(team_score_errors) / len(team_score_errors) if team_score_errors else 0.0
        avg_total_score_error = sum(total_score_errors) / len(total_score_errors) if total_score_errors else 0.0
        avg_away_score_error = sum(away_score_errors_all) / len(away_score_errors_all) if away_score_errors_all else 0.0
        avg_home_score_error = sum(home_score_errors_all) / len(home_score_errors_all) if home_score_errors_all else 0.0
        percent_within_1 = (cum_total_within_1 / cum_matched_games * 100) if cum_matched_games > 0 else 0.0
        percent_within_2 = (cum_total_within_2 / cum_matched_games * 100) if cum_matched_games > 0 else 0.0

        # Calculate performance trends (model reliability focus)
        if len(daily_summaries) > 0:
            window = daily_summaries[-3:]
            recent_accuracy = sum(d.get('winner_accuracy', 0.0) for d in window) / len(window)
        else:
            recent_accuracy = 0.0

        return {
            'analysis_type': 'cumulative',
            'date_range': {
                'start_date': available_dates[0],
                'end_date': available_dates[-1],
                'total_days': len(available_dates)
            },
            'generated_at': datetime.now().isoformat(),
            'data_summary': {
                'total_games_predicted': total_predictions,
                'total_games_matched': total_matched,
                'coverage_rate': total_matched / total_predictions if total_predictions > 0 else 0.0
            },
            'cumulative_performance': {
                'winner_accuracy': round(cumulative_winner_accuracy, 4),
                'recommendation_accuracy': round(cumulative_rec_accuracy, 4),
                'roi_percentage': round(cumulative_roi, 2),
                'win_rate': round(cumulative_win_rate, 4),
                'total_profit': round(net_profit, 2),
                'total_amount_bet': round(total_bet_amount, 2),
                'total_recommendations': total_recommendations,
                'total_bets_placed': total_bets_placed,
                'winning_bets': winning_bets,
                'avg_team_score_error': round(avg_team_score_error, 2),
                'avg_total_score_error': round(avg_total_score_error, 2),
                'avg_away_score_error': round(avg_away_score_error, 2),
                'avg_home_score_error': round(avg_home_score_error, 2),
                'percent_total_within_1': round(percent_within_1, 2),
                'percent_total_within_2': round(percent_within_2, 2),
                'count_total_within_1': cum_total_within_1,
                'count_total_within_2': cum_total_within_2,
                'matched_games': cum_matched_games
            },
            'recent_performance': {
                'recent_accuracy': round(recent_accuracy, 4)
            },
            'daily_summaries': daily_summaries,
            'daily_game_details': self.get_daily_game_details(available_dates),
            'summary': {
                'model_winner_accuracy': round(cumulative_winner_accuracy, 4),
                'recommendation_accuracy': round(cumulative_rec_accuracy, 4),
                'roi_percentage': round(cumulative_roi, 2),
                'total_profit': round(net_profit, 2),
                'days_tracked': len(available_dates)
            }
        }

    def get_daily_game_details(self, available_dates: List[str]) -> List[Dict]:
        """Get detailed game cards for each day"""
        daily_details = []
        
        for date in available_dates:
            try:
                # Get single day analysis for detailed game cards
                daily_analysis = self.perform_complete_analysis(date)
                
                if 'error' not in daily_analysis:
                    day_detail = {
                        'date': date,
                        'games_count': len(daily_analysis['game_cards']),
                        'day_stats': {
                            'winner_accuracy': daily_analysis['predictability']['winner_accuracy'],
                            'roi': daily_analysis['roi_analysis']['roi_percentage'],
                            'profit': daily_analysis['roi_analysis']['net_profit'],
                            'total_bets': daily_analysis['roi_analysis']['total_bets_placed']
                        },
                        'game_cards': daily_analysis['game_cards']
                    }
                    daily_details.append(day_detail)
                    
            except Exception as e:
                logger.error(f"Error getting game details for {date}: {e}")
                
        return daily_details

    def perform_complete_analysis(self, target_date: str) -> Dict:
        """Perform complete historical analysis for a given date"""
        logger.info(f"Starting historical analysis for {target_date}")
        
        # Load data
        games = self.load_predictions_for_date(target_date)
        final_scores = self.load_final_scores_for_date(target_date)

        if not games:
            return {
                'error': f'No prediction data found for {target_date}',
                'date': target_date
            }

        # If final scores are missing, still return all prediction and recommendation data
        scores_available = bool(final_scores)

        # Perform all analyses (if scores available, else use empty scores for analysis)
        predictability = self.analyze_predictability(games, final_scores if scores_available else {})
        betting_lens = self.analyze_betting_lens(games, final_scores if scores_available else {})
        betting_recommendations = self.analyze_betting_recommendations(games, final_scores if scores_available else {})
        roi_analysis = self.calculate_roi(games, final_scores if scores_available else {})
        game_cards = self.analyze_individual_games(games, final_scores if scores_available else {})

        # Mark game cards as missing final scores if not available
        if not scores_available:
            for card in game_cards:
                card['has_final_score'] = False
                card['final_scores'] = {'away_score': None, 'home_score': None}

        # Compile comprehensive report
        report = {
            'date': target_date,
            'generated_at': datetime.now().isoformat(),
            'data_summary': {
                'total_games_predicted': len(games),
                'final_scores_available': len(final_scores),
                'matched_games': predictability['matched_games']
            },
            'predictability': predictability,
            'betting_lens': betting_lens,
            'betting_recommendations': betting_recommendations,
            'roi_analysis': roi_analysis,
            'game_cards': game_cards,
            'summary': {
                'model_winner_accuracy': predictability.get('winner_accuracy', 0.0),
                'avg_team_score_error': predictability.get('avg_team_score_error', 0.0),
                'avg_total_score_error': predictability.get('avg_total_score_error', 0.0),
                # keep betting fields for other pages, even if not surfaced on model page
                'betting_winner_accuracy': betting_lens.get('winner_accuracy', 0.0),
                'recommendation_accuracy': betting_recommendations.get('overall_accuracy', 0.0),
                'roi_percentage': roi_analysis.get('roi_percentage', 0.0),
                'total_profit': roi_analysis.get('net_profit', 0.0)
            },
            'final_scores_missing': not scores_available
        }

        logger.info(f"Historical analysis completed for {target_date}")
        logger.info(f"Found {len(games)} games, {len(final_scores)} final scores")
        logger.info(f"Model accuracy: {predictability.get('winner_accuracy', 0):.1%}")
        logger.info(f"Total recommendations: {betting_recommendations.get('total_recommendations', 0)}")
        logger.info(f"ROI: {roi_analysis.get('roi_percentage', 0):.2f}%")

        return report

# Initialize analyzer
analyzer = HistoricalAnalyzer()

@historical_analysis_bp.route('/api/historical-analysis', methods=['GET'])
def get_historical_analysis():
    """API endpoint for historical analysis - defaults to cumulative since 8-15"""
    try:
        # Get parameters from query
        target_date = request.args.get('date')
        analysis_type = request.args.get('type', 'cumulative')  # Default to cumulative
        start_date = request.args.get('start_date', '2025-08-15')  # Default to 8-15
        end_date = request.args.get('end_date')  # Optional; default to yesterday inside analyzer

        if analysis_type == 'cumulative':
            # Perform cumulative analysis [start_date .. end_date]
            analysis = analyzer.perform_cumulative_analysis(start_date=start_date, end_date=end_date)
        else:
            # Single date analysis
            if not target_date:
                # Default to yesterday if no date provided
                yesterday = datetime.now() - timedelta(days=1)
                target_date = yesterday.strftime('%Y-%m-%d')

            # Validate date format
            try:
                datetime.strptime(target_date, '%Y-%m-%d')
            except ValueError:
                return jsonify({
                    'error': 'Invalid date format. Use YYYY-MM-DD',
                    'example': '2025-08-20'
                }), 400

            # Perform single date analysis
            analysis = analyzer.perform_complete_analysis(target_date)

        if 'error' in analysis:
            logger.error(f"Analysis error: {analysis.get('error')}, details: {analysis}")
            return jsonify(analysis), 404

        return jsonify(analysis)

    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        logger.error(f"Error in historical analysis endpoint: {e}\nTraceback:\n{tb}")
        return jsonify({
            'error': 'Internal server error',
            'message': str(e),
            'traceback': tb
        }), 500

# Test endpoint for development
@historical_analysis_bp.route('/api/historical-analysis/test', methods=['GET'])
def test_historical_analysis():
    """Test endpoint to verify the analysis works"""
    try:
        # Test with a known date
        test_date = '2025-08-20'
        
        # Load test data
        games = analyzer.load_predictions_for_date(test_date)
        final_scores = analyzer.load_final_scores_for_date(test_date)
        
        return jsonify({
            'test_date': test_date,
            'predictions_loaded': len(games),
            'final_scores_loaded': len(final_scores),
            'sample_game_keys': list(games.keys())[:3] if games else [],
            'sample_score_keys': list(final_scores.keys())[:3] if final_scores else [],
            'status': 'Test successful' if games and final_scores else 'Missing data'
        })
        
    except Exception as e:
        logger.error(f"Error in test endpoint: {e}")
        return jsonify({
            'error': 'Test failed',
            'message': str(e)
        }), 500

@historical_analysis_bp.route('/api/historical-analysis/dates', methods=['GET'])
def get_available_dates():
    """API endpoint to get available analysis dates"""
    try:
        available_dates = analyzer.get_available_dates()
        return jsonify({
            'available_dates': available_dates,
            'count': len(available_dates)
        })
    except Exception as e:
        logger.error(f"Error getting available dates: {e}")
        return jsonify({
            'error': f'Error getting available dates: {str(e)}',
            'available_dates': []
        }), 500

@historical_analysis_bp.route('/api/historical-analysis/final-scores/<date_str>', methods=['GET'])
def historical_final_scores(date_str: str):
    """Expose normalized final scores for a given date (YYYY-MM-DD)."""
    try:
        # basic validation
        try:
            datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400

        # Load with existing analyzer helper
        final_scores = analyzer.load_final_scores_for_date(date_str)
        return jsonify({
            'date': date_str,
            'count': len(final_scores or {}),
            'final_scores': final_scores or {}
        })
    except Exception as e:
        logger.exception(f"Error loading final scores for {date_str}: {e}")
        return jsonify({
            'error': 'Unable to load final scores',
            'message': str(e)
        }), 500
