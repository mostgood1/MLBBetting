"""
Ultra-Fast MLB Simulation Engine for MLB-Betting System
Optimized for speed while maintaining predictive accuracy with pitcher quality integration
"""

import numpy as np
import random
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import json
import os
import logging
from datetime import datetime, date
from typing import Dict
import numpy as np

# Set up logging
logger = logging.getLogger(__name__)

@dataclass
class FastGameResult:
    away_score: int
    home_score: int
    total_runs: int
    home_wins: bool
    run_differential: int

class UltraFastSimEngine:
    """
    Ultra-fast simulation engine using vectorized operations and pre-computed probabilities
    Adapted for MLB-Betting system with master data integration
    """
    
    def __init__(self, data_dir: str = None, config: dict = None):
        # Default to the data directory at the MLB-Betting root level
        if data_dir is None:
            # Get the parent directory of engines (MLB-Betting) and add data
            parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.data_dir = os.path.join(parent_dir, 'data')
        else:
            self.data_dir = data_dir
        
        # Load configuration or use defaults
        self.config = config or self._load_comprehensive_config()
        
        # Pre-compute probability distributions for maximum speed
        self.setup_fast_distributions()
        
        # Load team strengths and pitcher data from master files
        self.team_strengths = self._load_team_strengths()
        self.pitcher_stats = self._load_pitcher_stats()
        
        # Cache common calculations
        self._setup_speed_cache()
    
    def setup_fast_distributions(self):
        """Pre-compute probability distributions for vectorized sampling"""
        # TUNED TO REAL MLB DATA: Target 8.86 mean, 4.66 std dev
        self.run_probs = {
            0: 0.03, 1: 0.06, 2: 0.09, 3: 0.12, 4: 0.14, 5: 0.15,
            6: 0.12, 7: 0.10, 8: 0.08, 9: 0.06, 10: 0.03, 11: 0.02,
            12: 0.007, 13: 0.005, 14: 0.003, 15: 0.002
        }
        
        # Pre-compute cumulative probabilities for fast sampling
        self.run_values = list(self.run_probs.keys())
        self.run_cumprobs = np.cumsum(list(self.run_probs.values()))
        
        # Team advantage multipliers
        self.advantage_multipliers = np.linspace(0.85, 1.15, 21)
    
    def _load_team_strengths(self) -> Dict[str, float]:
        """Load team strengths from master data - NO FAKE DATA ALLOWED"""
        try:
            team_strength_file = os.path.join(self.data_dir, 'master_team_strength.json')
            if os.path.exists(team_strength_file):
                with open(team_strength_file, 'r') as f:
                    data = json.load(f)
                    print(f"Loaded real team strengths: {len(data)} teams")
                    return data
            else:
                raise FileNotFoundError(f"master_team_strength.json not found at {team_strength_file}")
        except Exception as e:
            print(f"CRITICAL: Could not load team strengths: {e}")
            raise FileNotFoundError(f"Real team strength data required but not found: {e}")
        
        # NO HARDCODED FALLBACK DATA ALLOWED
    
    def _load_pitcher_stats(self) -> Dict[str, Dict]:
        """Load pitcher stats from master data - NO FAKE DATA ALLOWED"""
        try:
            pitcher_file = os.path.join(self.data_dir, 'master_pitcher_stats.json')
            if os.path.exists(pitcher_file):
                with open(pitcher_file, 'r') as f:
                    data = json.load(f)
                    # Handle new refresh_info structure from daily refresh system
                    # Check for pitcher_data at top level first (new structure)
                    if 'pitcher_data' in data:
                        result = data['pitcher_data']
                    # Check for nested structure in refresh_info
                    elif 'refresh_info' in data and 'pitcher_data' in data['refresh_info']:
                        result = data['refresh_info']['pitcher_data']
                    # Fallback to direct structure for backward compatibility
                    else:
                        result = data
                    
                    print(f"Loaded real pitcher stats: {len(result)} pitchers")
                    return result
            else:
                raise FileNotFoundError(f"master_pitcher_stats.json not found at {pitcher_file}")
        except Exception as e:
            print(f"CRITICAL: Could not load pitcher stats: {e}")
            raise FileNotFoundError(f"Real pitcher data required but not found: {e}")
        
        # NO EMPTY FALLBACK ALLOWED - REAL DATA REQUIRED
    
    def _load_comprehensive_config(self):
        """Load comprehensive optimized configuration with all integrations"""
        try:
            # Try comprehensive optimized config first (highest priority)
            comprehensive_config_file = os.path.join(self.data_dir, 'comprehensive_optimized_config.json')
            if os.path.exists(comprehensive_config_file):
                with open(comprehensive_config_file, 'r') as f:
                    config = json.load(f)
                    logger.info("✅ UltraFastSimEngine: Loaded comprehensive optimized configuration")
                    print("✅ UltraFastSimEngine: Loaded comprehensive optimized configuration")
                    return config
            
            # Try betting-integrated config second
            betting_config_file = os.path.join(self.data_dir, 'betting_integrated_config.json')
            if os.path.exists(betting_config_file):
                with open(betting_config_file, 'r') as f:
                    config = json.load(f)
                    logger.info("✅ UltraFastSimEngine: Loaded betting-integrated configuration")
                    print("✅ UltraFastSimEngine: Loaded betting-integrated configuration")
                    return config
            
            # Fall back to other configs
            for config_name in ['balanced_tuned_config.json', 'optimized_config.json']:
                config_file = os.path.join(self.data_dir, config_name)
                if os.path.exists(config_file):
                    with open(config_file, 'r') as f:
                        config = json.load(f)
                        logger.info(f"✅ UltraFastSimEngine: Loaded fallback configuration: {config_name}")
                        print(f"✅ UltraFastSimEngine: Loaded fallback configuration: {config_name}")
                        return config
        except Exception as e:
            logger.debug(f"UltraFastSimEngine config loading error: {e}")
            print(f"⚠️ UltraFastSimEngine config loading error: {e}")
        
        logger.info("🔧 UltraFastSimEngine: Using default configuration")
        print("🔧 UltraFastSimEngine: Using default configuration")
        return self._get_default_config()
    
    def _get_default_config(self):
        """Get default configuration parameters - tuned to reduce away bias and lift totals"""
        return {
            "engine_parameters": {
                "home_field_advantage": 0.08,    # Slightly stronger home edge
                "away_field_boost": 0.01,        # Minimize away boost
                "base_lambda": 4.2,              # Slightly higher base scoring
                "team_strength_multiplier": 0.17, # Keep team impact stable
                "pitcher_era_weight": 0.78,      # ERA impact
                "pitcher_whip_weight": 0.38,     # WHIP impact
                "game_chaos_variance": 0.35,     # Slightly less randomness
                "total_scoring_adjustment": 1.03, # Lift totals ~3%
                "home_scoring_boost": 1.02,      # Boost home scoring a bit
                "away_scoring_boost": 0.99,      # Nudge away scoring down a touch
                "bullpen_weight": 0.15           # Bullpen integration
            },
            "betting_parameters": {
                "min_edge": 0.03,
                "kelly_fraction": 0.25,
                "high_confidence_ev": 0.10,
                "medium_confidence_ev": 0.05
            },
            "simulation_parameters": {
                "default_sim_count": 2000,
                "quick_sim_count": 1000,
                "detailed_sim_count": 5000,
                "max_sim_count": 10000
            },
            "pitcher_quality_bounds": {
                "min_quality_factor": 0.50,
                "max_quality_factor": 1.60,
                "ace_era_threshold": 2.75,
                "good_era_threshold": 3.50,
                "poor_era_threshold": 5.25,
                "min_games_started": 5
            }
        }
    
    def get_pitcher_quality_factor(self, pitcher_name: str) -> float:
        """
        Get pitcher quality factor based on 2025 stats with configurable weights
        Returns multiplier: <1.0 = good pitcher (allows fewer runs), >1.0 = poor pitcher
        """
        if not pitcher_name or not self.pitcher_stats:
            return 1.0
        
        # Get configuration
        pitcher_config = self.config.get('pitcher_quality_bounds', {})
        engine_params = self.config.get('engine_parameters', {})
        
        era_weight = engine_params.get('pitcher_era_weight', 0.70)
        whip_weight = engine_params.get('pitcher_whip_weight', 0.30)
        ace_era_threshold = pitcher_config.get('ace_era_threshold', 2.75)
        good_era_threshold = pitcher_config.get('good_era_threshold', 3.50)
        poor_era_threshold = pitcher_config.get('poor_era_threshold', 5.25)
        min_games_started = pitcher_config.get('min_games_started', 5)
        min_quality_factor = pitcher_config.get('min_quality_factor', 0.50)
        max_quality_factor = pitcher_config.get('max_quality_factor', 1.60)

        # Find pitcher by name match
        pitcher_data = None
        for pitcher_id, data in self.pitcher_stats.items():
            # Check if data is a dictionary (not a string)
            if isinstance(data, dict) and data.get('name', '').lower() == pitcher_name.lower():
                pitcher_data = data
                break
        
        if not pitcher_data:
            return 1.0
        
        try:
            era = float(pitcher_data.get('era', 4.50))
            whip = float(pitcher_data.get('whip', 1.30))
            games_started = int(pitcher_data.get('games_started', 0))
        except (ValueError, TypeError):
            return 1.0
        
        # Only apply to starting pitchers
        if games_started < min_games_started:
            return 1.0
        
        # Configurable ERA-based adjustment
        if era < 2.00:
            era_factor = 0.60
        elif era < ace_era_threshold:
            era_factor = 0.70
        elif era < good_era_threshold:
            era_factor = 0.85
        elif era < 4.25:
            era_factor = 0.95
        elif era < poor_era_threshold:
            era_factor = 1.15
        elif era < 6.50:
            era_factor = 1.25
        else:
            era_factor = 1.40
        
        # WHIP adjustment (unchanged logic but can be expanded)
        if whip < 1.00:
            whip_factor = 0.80
        elif whip < 1.15:
            whip_factor = 0.90
        elif whip < 1.30:
            whip_factor = 0.97
        elif whip < 1.45:
            whip_factor = 1.08
        else:
            whip_factor = 1.20
        
        # Innings pitched reliability factor
        try:
            innings_pitched = float(pitcher_data.get('innings_pitched', 0))
            if innings_pitched > 100:
                ip_factor = 1.0
            elif innings_pitched > 50:
                ip_factor = 0.8
            else:
                ip_factor = 0.5
        except:
            ip_factor = 0.5
        
        # Combine factors with configurable weights
        base_factor = (era_factor * era_weight) + (whip_factor * whip_weight)
        quality_factor = 1.0 + ((base_factor - 1.0) * ip_factor)
        
        return max(min_quality_factor, min(max_quality_factor, quality_factor))
    
    def get_matchup_starters(self, away_team: str, home_team: str, game_date: str = None) -> Tuple[Optional[str], Optional[str]]:
        """Get starting pitchers for this matchup from master games data"""
        try:
            games_file = os.path.join(self.data_dir, 'master_games.json')
            if os.path.exists(games_file):
                with open(games_file, 'r') as f:
                    games_data = json.load(f)
                
                # Use today if no date provided
                target_date = game_date or datetime.now().strftime('%Y-%m-%d')
                
                # Look for the game in the specified date
                if target_date in games_data.get('games_by_date', {}):
                    for game in games_data['games_by_date'][target_date]:
                        if (game.get('away_team') == away_team and 
                            game.get('home_team') == home_team):
                            return game.get('away_pitcher'), game.get('home_pitcher')
        except Exception as e:
            print(f"Warning: Could not load game starters: {e}")
        
        return None, None
    
    def _setup_speed_cache(self):
        """Setup caching for maximum speed with balanced parameters"""
        engine_params = self.config.get('engine_parameters', {})
        self.home_field_advantage = engine_params.get('home_field_advantage', 0.08)
        self.away_field_boost = engine_params.get('away_field_boost', 0.01)
        self.base_runs_per_team = 4.1  # Slight lift to raise totals
        self.base_lambda = engine_params.get('base_lambda', 4.2)
        self.team_strength_multiplier = engine_params.get('team_strength_multiplier', 0.17)
        self.game_chaos_variance = engine_params.get('game_chaos_variance', 0.35)
        self.total_scoring_adjustment = engine_params.get('total_scoring_adjustment', 1.03)
        self.home_scoring_boost = engine_params.get('home_scoring_boost', 1.02)
        self.away_scoring_boost = engine_params.get('away_scoring_boost', 0.99)
        self.bullpen_weight = engine_params.get('bullpen_weight', 0.15)
    
    def get_team_multiplier_with_pitchers(self, away_team: str, home_team: str, game_date: str = None) -> Tuple[float, float]:
        """Get run multipliers for both teams including pitcher quality with configurable parameters"""
        away_strength = self.team_strengths.get(away_team, 0.0) + self.away_field_boost  # Apply away boost
        home_strength = self.team_strengths.get(home_team, 0.0) + self.home_field_advantage
        
        # Get projected starters
        away_starter, home_starter = self.get_matchup_starters(away_team, home_team, game_date)
        
        # Get pitcher quality factors
        away_pitcher_factor = self.get_pitcher_quality_factor(home_starter)  # Home pitcher affects away scoring
        home_pitcher_factor = self.get_pitcher_quality_factor(away_starter)  # Away pitcher affects home scoring
        
        # Convert to multipliers using configurable team strength multiplier
        away_mult = 1.0 - (home_strength - away_strength) * self.team_strength_multiplier
        home_mult = 1.0 + (home_strength - away_strength) * self.team_strength_multiplier
        
        # Apply pitcher quality adjustments
        away_mult *= away_pitcher_factor
        home_mult *= home_pitcher_factor
        
        # Apply park and weather factors
        park_weather_factor = self._get_park_weather_factor(home_team, game_date)
        away_mult *= park_weather_factor
        home_mult *= park_weather_factor
        
        # Apply aggressive scoring bias corrections
        away_mult *= self.away_scoring_boost
        home_mult *= self.home_scoring_boost
        
        # Apply total scoring adjustment
        away_mult *= self.total_scoring_adjustment
        home_mult *= self.total_scoring_adjustment
        
        # Bounds for realistic variance
        away_mult = max(0.6, min(1.4, away_mult))
        home_mult = max(0.6, min(1.4, home_mult))
        
        return away_mult, home_mult
    
    def _get_park_weather_factor(self, home_team: str, game_date: str = None) -> float:
        """Get park and weather factor for run scoring"""
        if game_date is None:
            game_date = datetime.now().strftime('%Y-%m-%d')
        
        # Try to load daily park/weather data
        date_formatted = game_date.replace('-', '_')
        park_weather_file = os.path.join(self.data_dir, f'park_weather_factors_{date_formatted}.json')
        
        try:
            if os.path.exists(park_weather_file):
                with open(park_weather_file, 'r') as f:
                    data = json.load(f)
                    team_data = data.get('teams', {}).get(home_team, {})
                    return team_data.get('total_factor', 1.0)
        except Exception as e:
            logger.debug(f"Could not load park/weather data: {e}")
        
        # Fallback to static park factors if weather data unavailable
        static_park_factors = {
            "Colorado Rockies": 1.12,      # High altitude
            "Texas Rangers": 1.06,         # New hitter-friendly park
            "Baltimore Orioles": 1.05,     # Camden Yards
            "New York Yankees": 1.05,      # Short porch
            "Philadelphia Phillies": 1.03,
            "Boston Red Sox": 1.04,        # Green Monster
            "Cincinnati Reds": 1.02,
            "Chicago Cubs": 1.02,          # Wind dependent
            "Minnesota Twins": 1.01,
            "Atlanta Braves": 1.01,
            "Washington Nationals": 1.01,
            "Toronto Blue Jays": 1.02,
            "Milwaukee Brewers": 1.00,
            "Houston Astros": 1.00,
            "St. Louis Cardinals": 1.00,
            "Chicago White Sox": 1.00,
            "Pittsburgh Pirates": 0.99,
            "Kansas City Royals": 0.98,
            "Cleveland Guardians": 0.98,
            "Los Angeles Angels": 0.99,
            "Tampa Bay Rays": 0.97,
            "New York Mets": 0.97,
            "Detroit Tigers": 0.97,
            "Seattle Mariners": 0.96,
            "Los Angeles Dodgers": 0.96,
            "Miami Marlins": 0.95,
            "San Diego Padres": 0.93,
            "Oakland Athletics": 0.92,
            "San Francisco Giants": 0.90
        }
        
        return static_park_factors.get(home_team, 1.0)
    
    def simulate_game_vectorized(self, away_team: str, home_team: str, 
                               sim_count: int = 100, game_date: str = None,
                               away_pitcher: str = None, home_pitcher: str = None) -> List[FastGameResult]:
        """Ultra-fast vectorized simulation with realistic MLB variance"""
        # Set consistent seed for stable predictions
        seed_value = hash(f"{away_team}{home_team}{game_date or ''}") % 1000000
        np.random.seed(seed_value)
        random.seed(seed_value)
        
        # Get pitcher information - use passed parameters if available, otherwise lookup
        if away_pitcher and home_pitcher:
            away_starter = away_pitcher
            home_starter = home_pitcher
        else:
            away_starter, home_starter = self.get_matchup_starters(away_team, home_team, game_date)
        
        away_pitcher_factor = self.get_pitcher_quality_factor(away_starter)
        home_pitcher_factor = self.get_pitcher_quality_factor(home_starter)
        
        away_mult, home_mult = self.get_team_multiplier_with_pitchers(away_team, home_team, game_date)
        
        # Poisson parameters using configurable base lambda
        away_lambda = self.base_lambda * away_mult
        home_lambda = self.base_lambda * home_mult
        
        # Game-level variance using configurable chaos factor
        game_chaos_factor = np.random.normal(1.0, self.game_chaos_variance)
        game_chaos_factor = max(0.75, min(1.25, game_chaos_factor))
        
        away_lambda *= game_chaos_factor
        home_lambda *= game_chaos_factor
        
        # Generate scores
        away_scores = np.random.poisson(np.full(sim_count, away_lambda))
        home_scores = np.random.poisson(np.full(sim_count, home_lambda))
        
        away_scores = np.clip(away_scores, 0, 24)
        home_scores = np.clip(home_scores, 0, 24)
        
        # Create results
        results = []
        for i in range(sim_count):
            away_score = int(away_scores[i])
            home_score = int(home_scores[i])
            
            # Handle ties with extra innings
            if away_score == home_score:
                extra_innings = 0
                while away_score == home_score and extra_innings < 5:
                    extra_innings += 1
                    if random.random() < 0.6:
                        away_score += 1
                    if random.random() < 0.6:
                        home_score += 1
                
                if away_score == home_score:
                    if random.random() < 0.5:
                        away_score += 1
                    else:
                        home_score += 1
            
            total_run = away_score + home_score
            home_win = home_score > away_score
            run_diff = home_score - away_score
            
            results.append(FastGameResult(
                away_score=away_score,
                home_score=home_score,
                total_runs=total_run,
                home_wins=home_win,
                run_differential=run_diff
            ))
        
        return results, {
            'away_pitcher_name': away_starter,
            'home_pitcher_name': home_starter,
            'away_pitcher_factor': away_pitcher_factor,
            'home_pitcher_factor': home_pitcher_factor
        }

class SmartBettingAnalyzer:
    """Advanced betting analyzer with real-time recommendations and configurable parameters"""
    
    def __init__(self, config: dict = None):
        self.config = config or {}
        betting_params = self.config.get('betting_parameters', {})
        self.min_edge = betting_params.get('min_edge', 0.03)  # 3% minimum edge
        self.kelly_fraction = betting_params.get('kelly_fraction', 0.25)  # Conservative Kelly sizing
        self.high_confidence_ev = betting_params.get('high_confidence_ev', 0.10)
        self.medium_confidence_ev = betting_params.get('medium_confidence_ev', 0.05)
        
    def analyze_moneyline_value(self, home_win_prob: float, away_win_prob: float,
                              home_odds: int, away_odds: int) -> List[Dict]:
        """Fast moneyline value analysis"""
        recommendations = []
        
        home_implied = self._odds_to_prob(home_odds)
        away_implied = self._odds_to_prob(away_odds)
        
        # Check home value
        if home_win_prob > home_implied + self.min_edge:
            ev = (home_win_prob * self._calculate_payout(home_odds)) - (1 - home_win_prob)
            kelly_size = min(self.kelly_fraction, ev * home_win_prob) * 100
            
            recommendations.append({
                'type': 'moneyline',
                'side': 'home',
                'team': 'home',
                'odds': home_odds,
                'model_prob': round(home_win_prob, 3),
                'implied_prob': round(home_implied, 3),
                'expected_value': round(ev, 3),
                'edge': round(home_win_prob - home_implied, 3),
                'kelly_bet_size': round(kelly_size, 1),
                'confidence': 'HIGH' if ev > self.high_confidence_ev else 'MEDIUM',
                'reasoning': f"Model: {home_win_prob:.1%} vs Market: {home_implied:.1%}"
            })
        
        # Check away value
        if away_win_prob > away_implied + self.min_edge:
            ev = (away_win_prob * self._calculate_payout(away_odds)) - (1 - away_win_prob)
            kelly_size = min(self.kelly_fraction, ev * away_win_prob) * 100
            
            recommendations.append({
                'type': 'moneyline',
                'side': 'away',
                'team': 'away',
                'odds': away_odds,
                'model_prob': round(away_win_prob, 3),
                'implied_prob': round(away_implied, 3),
                'expected_value': round(ev, 3),
                'edge': round(away_win_prob - away_implied, 3),
                'kelly_bet_size': round(kelly_size, 1),
                'confidence': 'HIGH' if ev > 0.1 else 'MEDIUM',
                'reasoning': f"Model: {away_win_prob:.1%} vs Market: {away_implied:.1%}"
            })
        
        return recommendations
    
    def analyze_total_value(self, predicted_total: float, total_line: float,
                          over_odds: int = -110, under_odds: int = -110) -> List[Dict]:
        """Fast total runs value analysis"""
        recommendations = []
        
        over_prob = 0.5 + (predicted_total - total_line) * 0.05
        under_prob = 1 - over_prob
        
        over_implied = self._odds_to_prob(over_odds)
        under_implied = self._odds_to_prob(under_odds)
        
        # Check over value
        if over_prob > over_implied + self.min_edge:
            ev = (over_prob * self._calculate_payout(over_odds)) - (1 - over_prob)
            kelly_size = min(self.kelly_fraction, ev * over_prob) * 100
            
            recommendations.append({
                'type': 'total',
                'side': 'over',
                'line': total_line,
                'odds': over_odds,
                'model_total': round(predicted_total, 1),
                'edge': round(predicted_total - total_line, 1),
                'expected_value': round(ev, 3),
                'kelly_bet_size': round(kelly_size, 1),
                'confidence': 'HIGH' if abs(predicted_total - total_line) > 1.0 else 'MEDIUM',
                'reasoning': f"Model: {predicted_total:.1f} vs Line: {total_line}"
            })
        
        # Check under value
        if under_prob > under_implied + self.min_edge:
            ev = (under_prob * self._calculate_payout(under_odds)) - (1 - under_prob)
            kelly_size = min(self.kelly_fraction, ev * under_prob) * 100
            
            recommendations.append({
                'type': 'total',
                'side': 'under',
                'line': total_line,
                'odds': under_odds,
                'model_total': round(predicted_total, 1),
                'edge': round(total_line - predicted_total, 1),
                'expected_value': round(ev, 3),
                'kelly_bet_size': round(kelly_size, 1),
                'confidence': 'HIGH' if abs(predicted_total - total_line) > 1.0 else 'MEDIUM',
                'reasoning': f"Model: {predicted_total:.1f} vs Line: {total_line}"
            })
        
        return recommendations
    
    def _odds_to_prob(self, odds: int) -> float:
        """Convert American odds to probability"""
        if odds > 0:
            return 100 / (odds + 100)
        else:
            return abs(odds) / (abs(odds) + 100)
    
    def _calculate_payout(self, odds: int) -> float:
        """Calculate payout multiplier"""
        if odds > 0:
            return odds / 100
        else:
            return 100 / abs(odds)

class FastPredictionEngine:
    """Complete fast prediction engine for MLB-Betting system with configurable parameters"""
    
    def __init__(self, data_dir: str = None, config: dict = None):
        # Default to the data directory at the MLB-Betting root level
        if data_dir is None:
            # Get the parent directory of engines (MLB-Betting) and add data
            parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.data_dir = os.path.join(parent_dir, 'data')
        else:
            self.data_dir = data_dir
        
        # Load configuration
        self.config = config or self._load_config()
        
        # Initialize components with configuration
        self.sim_engine = UltraFastSimEngine(self.data_dir, self.config)
        self.betting_analyzer = SmartBettingAnalyzer(self.config)
        self._load_master_data()
        # Caches for daily pitcher projection integration
        self._daily_proj_cache: dict[str, dict] = {}
        self._bullpen_cache = None
        self._league_avg_k9 = 8.7  # Approx baseline
        self._league_avg_bullpen_era = 4.15
        # Config flags
        try:
            from engine_config import config_manager
            bet_cfg = config_manager.get_betting_config()
            self._integrate_daily_pitchers = bet_cfg.get('INTEGRATE_DAILY_PITCHERS', True)
            bw = bet_cfg.get('PITCHER_BLEND_WEIGHTS', (0.6,0.4))
            if isinstance(bw, (list, tuple)) and len(bw)==2:
                self._blend_projection_w, self._blend_sim_w = float(bw[0]), float(bw[1])
            else:
                self._blend_projection_w, self._blend_sim_w = 0.6, 0.4
        except Exception:
            self._integrate_daily_pitchers = True
            self._blend_projection_w, self._blend_sim_w = 0.6, 0.4

    # ================= Pitcher Projection Integration ==================
    def _normalize_pitcher_name(self, name: str) -> str:
        if not name:
            return ''
        try:
            import unicodedata, re
            name = name.replace('φ','í')
            base = ''.join(c for c in unicodedata.normalize('NFD', name) if unicodedata.category(c) != 'Mn')
            base = re.sub(r'\s+',' ', base).strip().lower()
            return base
        except Exception:
            return name.lower().strip()

    def _load_bullpen_stats(self):
        if self._bullpen_cache is not None:
            return self._bullpen_cache
        path = os.path.join(self.data_dir, 'bullpen_stats.json')
        if os.path.exists(path):
            try:
                with open(path,'r') as f:
                    self._bullpen_cache = json.load(f) or {}
            except Exception:
                self._bullpen_cache = {}
        else:
            self._bullpen_cache = {}
        return self._bullpen_cache

    def _load_daily_pitcher_projections(self, game_date: str) -> dict:
        if game_date in self._daily_proj_cache:
            return self._daily_proj_cache[game_date]
        # Prefer existing json artifact to avoid recomputation
        date_token = game_date.replace('-','_')
        path = os.path.join(self.data_dir, 'daily_bovada', f'projection_features_{date_token}.json')
        proj_map = {}
        data = None
        if os.path.exists(path):
            try:
                with open(path,'r') as f:
                    data = json.load(f)
            except Exception:
                data = None
        if not data:
            # As fallback, try live computation (may be slower)
            try:
                from pitcher_projections import compute_pitcher_projections
                data = compute_pitcher_projections(game_date)
            except Exception:
                data = None
        if data and isinstance(data, dict) and 'pitchers' in data:
            for p in data['pitchers']:
                nm = self._normalize_pitcher_name(p.get('pitcher_name'))
                if nm:
                    proj_map[nm] = p
        self._daily_proj_cache[game_date] = proj_map
        return proj_map

    def _lookup_pitcher_projection(self, name: str, game_date: str):
        mp = self._load_daily_pitcher_projections(game_date)
        return mp.get(self._normalize_pitcher_name(name))

    def _corrected_opponent(self, pitcher_name: str, game_date: str) -> Optional[str]:
        p = self._lookup_pitcher_projection(pitcher_name, game_date)
        if p:
            return p.get('opponent')
        return None

    def _get_pitcher_id_from_projection(self, name: str, game_date: str) -> str | None:
        p = self._lookup_pitcher_projection(name, game_date)
        if p:
            return str(p.get('pitcher_id')) if p.get('pitcher_id') else None
        # Fallback: scan master pitcher stats
        for pid, info in getattr(self.sim_engine, 'pitcher_stats', {}).items():
            if isinstance(info, dict) and info.get('name','').lower() == (name or '').lower():
                return str(pid)
        return None

    def _expected_runs_allowed_plan(self, pitcher_name: str, team_name: str, game_date: str) -> dict:
        """Compute expected runs allowed by full game pitching plan using daily projections.

        Returns dict with keys: starter_ip, starter_er, strikeout_factor, bullpen_ip, bullpen_era, bullpen_runs, total_runs_allowed
        """
        proj = self._lookup_pitcher_projection(pitcher_name, game_date)
        bullpen_stats = self._load_bullpen_stats()
        bullpen = bullpen_stats.get(team_name, {}) if isinstance(bullpen_stats, dict) else {}
        bullpen_era = None
        for k in ('era','bullpen_era','adjusted_era'):
            v = bullpen.get(k)
            if isinstance(v,(int,float)) and v>0:
                bullpen_era = float(v)
                break
        if bullpen_era is None:
            bullpen_era = self._league_avg_bullpen_era
        starter_ip = None
        starter_er = None
        projected_k = None
        if proj:
            outs = proj.get('projected_outs') or proj.get('adjusted_projections', {}).get('outs')
            if isinstance(outs,(int,float)) and outs>0:
                starter_ip = float(outs)/3.0
            starter_er = proj.get('projected_earned_runs') or proj.get('adjusted_projections', {}).get('earned_runs')
            projected_k = proj.get('projected_strikeouts') or proj.get('adjusted_projections', {}).get('strikeouts')
        # Fallbacks
        if starter_ip is None or starter_ip<=0:
            # Use average from master stats if available
            starter_ip = 5.2  # default average
        if starter_er is None:
            # Approx from pitcher ERA in master stats
            # Find pitcher in master stats
            era = None
            for pid, info in getattr(self.sim_engine, 'pitcher_stats', {}).items():
                if isinstance(info, dict) and info.get('name','').lower() == (pitcher_name or '').lower():
                    try:
                        era = float(info.get('era'))
                    except Exception:
                        era = None
                    break
            if era is None:
                era = 4.30
            starter_er = era/9.0 * starter_ip
        # Strikeout run suppression factor
        strikeout_factor = 1.0
        if projected_k and starter_ip>0 and isinstance(projected_k,(int,float)):
            k9 = (projected_k / starter_ip) * 9.0
            try:
                ratio = max(0.4, min(2.0, k9 / self._league_avg_k9))
                # Higher K9 reduces runs: inverse power
                strikeout_factor = max(0.9, min(1.1, (1/ratio)**0.25))
            except Exception:
                pass
        bullpen_ip = max(0.0, 9.0 - starter_ip)
        bullpen_runs = bullpen_era/9.0 * bullpen_ip
        total = starter_er * strikeout_factor + bullpen_runs
        return {
            'starter_ip': round(starter_ip,2),
            'starter_er': round(starter_er,2),
            'strikeout_factor': round(strikeout_factor,4),
            'bullpen_ip': round(bullpen_ip,2),
            'bullpen_era': round(bullpen_era,2),
            'bullpen_runs': round(bullpen_runs,2),
            'total_runs_allowed': round(total,2)
        }
    
    def _load_config(self):
        """Load configuration from file with comprehensive optimization priority"""
        try:
            # Try comprehensive optimized config first (highest priority)
            comprehensive_config_file = os.path.join(self.data_dir, 'comprehensive_optimized_config.json')
            if os.path.exists(comprehensive_config_file):
                with open(comprehensive_config_file, 'r') as f:
                    config = json.load(f)
                    logger.info("✅ Loaded comprehensive optimized configuration with weather/park/betting integration")
                    return config
            
            # Try betting-integrated config second
            betting_config_file = os.path.join(self.data_dir, 'betting_integrated_config.json')
            if os.path.exists(betting_config_file):
                with open(betting_config_file, 'r') as f:
                    config = json.load(f)
                    logger.info("✅ Loaded betting-integrated configuration")
                    return config
            
            # Fall back to other configs
            for config_name in ['balanced_tuned_config.json', 'optimized_config.json']:
                config_file = os.path.join(self.data_dir, config_name)
                if os.path.exists(config_file):
                    with open(config_file, 'r') as f:
                        config = json.load(f)
                        logger.info(f"✅ Loaded fallback configuration: {config_name}")
                        return config
        except Exception as e:
            logger.debug(f"Config loading error: {e}")
        
        logger.info("🔧 Using default configuration")
        return self.sim_engine._get_default_config()
    
    def _load_master_data(self):
        """Load master data files"""
        try:
            # Load master games data
            games_file = os.path.join(self.data_dir, 'master_games.json')
            if os.path.exists(games_file):
                with open(games_file, 'r') as f:
                    self.master_games = json.load(f)
            else:
                self.master_games = {}
            
            # Load master predictions data
            predictions_file = os.path.join(self.data_dir, 'master_predictions.json')
            if os.path.exists(predictions_file):
                with open(predictions_file, 'r') as f:
                    self.master_predictions = json.load(f)
            else:
                self.master_predictions = {}
            
            # Load master betting lines
            betting_file = os.path.join(self.data_dir, 'master_betting_lines.json')
            if os.path.exists(betting_file):
                with open(betting_file, 'r') as f:
                    self.master_betting = json.load(f)
            else:
                self.master_betting = {}
                
        except Exception as e:
            print(f"Warning: Could not load master data: {e}")
            self.master_games = {}
            self.master_predictions = {}
            self.master_betting = {}
    
    def get_fast_prediction(self, away_team: str, home_team: str, 
                          sim_count: int = 2000, game_date: str = None,
                          away_pitcher: str = None, home_pitcher: str = None) -> Dict:
        """Generate complete prediction with recommendations"""
        start_time = datetime.now()
        
        # Use current date if not provided
        if not game_date:
            game_date = datetime.now().strftime('%Y-%m-%d')
        
        # Check for historical data first
        historical_result = self._get_historical_result(away_team, home_team, game_date)
        if historical_result:
            return historical_result
        
        # Run simulations with configurable count
        sim_params = self.config.get('simulation_parameters', {})
        default_sim_count = sim_params.get('default_sim_count', 2000)
        sim_count = sim_count or default_sim_count
        results, pitcher_info = self.sim_engine.simulate_game_vectorized(
            away_team, home_team, sim_count, game_date, away_pitcher, home_pitcher
        )

        # ================= New Pitcher Projection Integration Phase =================
        try:
            home_pitching_plan = self._expected_runs_allowed_plan(pitcher_info.get('home_pitcher_name'), home_team, game_date)
            away_pitching_plan = self._expected_runs_allowed_plan(pitcher_info.get('away_pitcher_name'), away_team, game_date)
        except Exception:
            home_pitching_plan = away_pitching_plan = None
        # If plans available, blend their totals with simulated Poisson base expectation
        # Derive original lambdas from sample means (will compute later). We'll blend on means after calculation.
        
        # Calculate statistics
        away_scores = [r.away_score for r in results]
        home_scores = [r.home_score for r in results]
        total_runs = [r.total_runs for r in results]
        home_wins = sum(r.home_wins for r in results)
        
        avg_away_raw = float(np.mean(away_scores))
        avg_home_raw = float(np.mean(home_scores))
        avg_total_raw = float(np.mean(total_runs))
        avg_away = avg_away_raw
        avg_home = avg_home_raw
        avg_total = avg_total_raw
        blend_meta = None
        if self._integrate_daily_pitchers and home_pitching_plan and away_pitching_plan:
            # Expected runs for away offense is home pitching plan total_runs_allowed
            away_expected = home_pitching_plan['total_runs_allowed']
            home_expected = away_pitching_plan['total_runs_allowed']
            # Blend: weight projection 0.6, simulation 0.4
            blended_away = self._blend_projection_w*away_expected + self._blend_sim_w*avg_away
            blended_home = self._blend_projection_w*home_expected + self._blend_sim_w*avg_home
            # Ensure non-negative
            avg_away = max(0.1, blended_away)
            avg_home = max(0.1, blended_home)
            avg_total = avg_away + avg_home
            blend_meta = {
                'projection_components': {
                    'away_pitching_expected_runs': away_expected,
                    'home_pitching_expected_runs': home_expected
                },
                'simulation_components': {
                    'away_sim_mean': avg_away_raw,
                    'home_sim_mean': avg_home_raw
                },
                'blended': {
                    'away_final_mean': avg_away,
                    'home_final_mean': avg_home,
                    'total_final_mean': avg_total
                }
            }
        home_win_prob = home_wins / sim_count
        away_win_prob = 1 - home_win_prob
        
        # Confidence intervals
        home_ci = (np.percentile(home_scores, 10), np.percentile(home_scores, 90))
        away_ci = (np.percentile(away_scores, 10), np.percentile(away_scores, 90))
        total_ci = (np.percentile(total_runs, 10), np.percentile(total_runs, 90))
        
        # Get betting lines
        betting_lines = self._get_betting_lines(away_team, home_team, game_date, home_win_prob)
        
        # Apply betting lines integration if enabled
        if self.config.get('betting_integration', {}).get('enabled', False):
            home_win_prob, avg_total = self._apply_betting_integration(
                home_win_prob, avg_total, betting_lines
            )
            away_win_prob = 1 - home_win_prob
        
        # Betting analysis
        ml_recs = self.betting_analyzer.analyze_moneyline_value(
            home_win_prob, away_win_prob,
            betting_lines['home_ml'], betting_lines['away_ml']
        )
        
        total_recs = self.betting_analyzer.analyze_total_value(
            avg_total, betting_lines['total_line'],
            betting_lines['over_odds'], betting_lines['under_odds']
        )
        
        all_recommendations = ml_recs + total_recs
        execution_time = (datetime.now() - start_time).total_seconds() * 1000
        
        # Pitcher IDs for audit
        home_pid = self._get_pitcher_id_from_projection(pitcher_info.get('home_pitcher_name'), game_date)
        away_pid = self._get_pitcher_id_from_projection(pitcher_info.get('away_pitcher_name'), game_date)

        return {
            'away_team': away_team,
            'home_team': home_team,
            'game_date': game_date,
            'predictions': {
                'home_win_prob': round(home_win_prob, 3),
                'away_win_prob': round(away_win_prob, 3),
                'predicted_home_score': round(avg_home, 1),
                'predicted_away_score': round(avg_away, 1),
                'predicted_total_runs': round(avg_total, 1),
                'home_score_range': (round(home_ci[0], 1), round(home_ci[1], 1)),
                'away_score_range': (round(away_ci[0], 1), round(away_ci[1], 1)),
                'total_runs_range': (round(total_ci[0], 1), round(total_ci[1], 1)),
                'confidence': round(90 - np.std(total_runs) * 10, 1)
            },
            'betting_lines': betting_lines,
            'recommendations': all_recommendations,
            'pitcher_info': pitcher_info,
            'pitching_integration': {
                'home_pitching_plan': home_pitching_plan,
                'away_pitching_plan': away_pitching_plan,
                'blend_weights': {'projection':self._blend_projection_w,'simulation':self._blend_sim_w} if (self._integrate_daily_pitchers and home_pitching_plan and away_pitching_plan) else None,
                'home_pitcher_id': home_pid,
                'away_pitcher_id': away_pid,
                'run_blend_audit': blend_meta,
                'raw_sim_means': {'away': avg_away_raw, 'home': avg_home_raw, 'total': avg_total_raw}
            },
            'meta': {
                'simulations_run': sim_count,
                'execution_time_ms': round(execution_time, 1),
                'recommendations_found': len(all_recommendations),
                'timestamp': datetime.now().isoformat(),
                'data_source': 'live_simulation'
            }
        }
    
    def _get_historical_result(self, away_team: str, home_team: str, game_date: str) -> Optional[Dict]:
        """Get historical result if available"""
        # Check if this is a historical date with actual results
        if game_date in self.master_predictions.get('predictions_by_date', {}):
            date_predictions = self.master_predictions['predictions_by_date'][game_date]
            
            # Look for this specific game
            for game_key, prediction in date_predictions.items():
                if away_team in game_key and home_team in game_key:
                    # This is a historical game with actual results
                    return {
                        'away_team': away_team,
                        'home_team': home_team,
                        'game_date': game_date,
                        'predictions': {
                            'predicted_away_score': prediction.get('predicted_away_score'),
                            'predicted_home_score': prediction.get('predicted_home_score'),
                            'predicted_total_runs': prediction.get('predicted_total_runs')
                        },
                        'actual_results': {
                            'away_score': prediction.get('actual_away_score'),
                            'home_score': prediction.get('actual_home_score'),
                            'prediction_error': prediction.get('prediction_error'),
                            'winner_correct': prediction.get('winner_correct')
                        },
                        'meta': {
                            'data_source': 'historical',
                            'is_completed': True,
                            'game_date': game_date
                        }
                    }
        
        return None
    
    def _get_betting_lines(self, away_team: str, home_team: str, game_date: str, home_win_prob: float) -> Dict:
        """Get betting lines from master data or generate sample lines"""
        # Try to get from master betting data
        if hasattr(self, 'master_betting') and self.master_betting:
            # Look for betting lines for this game
            for game_id, betting_data in self.master_betting.get('games', {}).items():
                if (betting_data.get('away_team') == away_team and 
                    betting_data.get('home_team') == home_team):
                    
                    # Extract betting lines
                    betting_odds = betting_data.get('betting_odds', {})
                    moneyline = betting_odds.get('moneyline', {})
                    total_runs = betting_odds.get('total_runs', {})
                    
                    return {
                        'home_ml': moneyline.get('home', self._prob_to_odds(home_win_prob)),
                        'away_ml': moneyline.get('away', self._prob_to_odds(1 - home_win_prob)),
                        'total_line': total_runs.get('line', 8.5),
                        'over_odds': total_runs.get('over', -110),
                        'under_odds': total_runs.get('under', -110)
                    }
        
        # Generate sample lines
        return self._generate_sample_lines(home_win_prob)
    
    def _prob_to_odds(self, prob: float) -> int:
        """Convert probability to American odds"""
        if prob > 0.5:
            return int(-100 * prob / (1 - prob))
        else:
            return int(100 * (1 - prob) / prob)
    
    def _generate_sample_lines(self, home_win_prob: float) -> Dict:
        """Generate realistic sample betting lines"""
        home_ml = self._prob_to_odds(home_win_prob)
        away_ml = self._prob_to_odds(1 - home_win_prob)
        
        return {
            'home_ml': home_ml,
            'away_ml': away_ml,
            'total_line': 8.5,
            'over_odds': -110,
            'under_odds': -110
        }
    
    def _apply_betting_integration(self, home_win_prob: float, predicted_total: float, 
                                 betting_lines: Dict) -> Tuple[float, float]:
        """Apply betting lines integration to adjust predictions"""
        betting_config = self.config.get('betting_integration', {})
        
        if not betting_config.get('enabled', False):
            return home_win_prob, predicted_total
        
        betting_weight = betting_config.get('betting_weight', 0.25)
        line_threshold = betting_config.get('line_confidence_threshold', 0.15)
        
        adjusted_home_prob = home_win_prob
        adjusted_total = predicted_total
        
        # Adjust moneyline prediction
        home_ml = betting_lines.get('home_ml')
        if home_ml is not None:
            lines_home_prob = self._moneyline_to_probability(home_ml)
            if lines_home_prob is not None:
                # Blend model prediction with lines probability
                adjusted_home_prob = (
                    (1 - betting_weight) * home_win_prob + 
                    betting_weight * lines_home_prob
                )
        
        # Adjust total prediction
        total_line = betting_lines.get('total_line')
        if total_line is not None:
            total_diff = abs(predicted_total - total_line)
            if total_diff > line_threshold:
                # Blend model total with lines total
                adjusted_total = (
                    (1 - betting_weight) * predicted_total + 
                    betting_weight * total_line
                )
        
        return adjusted_home_prob, adjusted_total
    
    def _moneyline_to_probability(self, moneyline: int) -> Optional[float]:
        """Convert American moneyline odds to implied probability"""
        try:
            if moneyline > 0:
                return 100 / (moneyline + 100)
            else:
                return abs(moneyline) / (abs(moneyline) + 100)
        except (TypeError, ZeroDivisionError):
            return None
    
    def get_todays_games(self, game_date: str = None) -> List[Tuple[str, str]]:
        """Get today's games from master schedule"""
        target_date = game_date or datetime.now().strftime('%Y-%m-%d')
        games = []
        
        if target_date in self.master_games.get('games_by_date', {}):
            for game in self.master_games['games_by_date'][target_date]:
                games.append((game['away_team'], game['home_team']))
        
        return games
    
    def _get_park_weather_factor(self, home_team: str, game_date: str = None) -> float:
        """Get park and weather factor for run scoring"""
        if game_date is None:
            game_date = datetime.now().strftime('%Y-%m-%d')
        
        # Try to load daily park/weather data
        date_formatted = game_date.replace('-', '_')
        park_weather_file = os.path.join(self.data_dir, f'park_weather_factors_{date_formatted}.json')
        
        try:
            if os.path.exists(park_weather_file):
                with open(park_weather_file, 'r') as f:
                    data = json.load(f)
                    team_data = data.get('teams', {}).get(home_team, {})
                    return team_data.get('total_factor', 1.0)
        except Exception as e:
            logger.debug(f"Could not load park/weather data: {e}")
        
        # Fallback to static park factors if weather data unavailable
        static_park_factors = {
            "Colorado Rockies": 1.12,      # High altitude
            "Texas Rangers": 1.06,         # New hitter-friendly park
            "Baltimore Orioles": 1.05,     # Camden Yards
            "New York Yankees": 1.05,      # Short porch
            "Philadelphia Phillies": 1.03,
            "Boston Red Sox": 1.04,        # Green Monster
            "Cincinnati Reds": 1.02,
            "Chicago Cubs": 1.02,          # Wind dependent
            "Minnesota Twins": 1.01,
            "Atlanta Braves": 1.01,
            "Washington Nationals": 1.01,
            "Toronto Blue Jays": 1.02,
            "Milwaukee Brewers": 1.00,
            "Houston Astros": 1.00,
            "St. Louis Cardinals": 1.00,
            "Chicago White Sox": 1.00,
            "Pittsburgh Pirates": 0.99,
            "Kansas City Royals": 0.98,
            "Cleveland Guardians": 0.98,
            "Los Angeles Angels": 0.99,
            "Tampa Bay Rays": 0.97,
            "New York Mets": 0.97,
            "Detroit Tigers": 0.97,
            "Seattle Mariners": 0.96,
            "Los Angeles Dodgers": 0.96,
            "Miami Marlins": 0.95,
            "San Diego Padres": 0.93,
            "Oakland Athletics": 0.92,
            "San Francisco Giants": 0.90
        }
        
        return static_park_factors.get(home_team, 1.0)

if __name__ == "__main__":
    # Test the engine
    engine = FastPredictionEngine()
    
    # Test with sample teams
    prediction = engine.get_fast_prediction("Yankees", "Red Sox")
    print(f"Prediction: {prediction['predictions']['predicted_total_runs']} total runs")
    print(f"Home win probability: {prediction['predictions']['home_win_prob']:.1%}")
    print(f"Execution time: {prediction['meta']['execution_time_ms']:.1f}ms")
