"""
Closing Lines Data Fetcher
========================

Enhanced data fetcher specifically designed to capture closing betting lines
for accurate betting analysis and system validation.
"""

import requests
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import logging
import time

logger = logging.getLogger(__name__)

class ClosingLinesOddsAPIFetcher:
    """Enhanced fetcher for closing betting lines from OddsAPI"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.the-odds-api.com/v4"
    
    def fetch_closing_lines_for_date(self, date_str: str) -> Dict[str, Any]:
        """
        Fetch closing lines for a specific date by getting historical odds
        at game time for completed games
        """
        try:
            # First get the schedule for the date to know game times
            games_schedule = self._get_games_schedule(date_str)
            
            closing_lines = {}
            
            for game in games_schedule:
                game_time = datetime.fromisoformat(game['commence_time'].replace('Z', '+00:00'))
                
                # For completed games, fetch historical odds at game time
                if self._is_game_completed(game_time):
                    historical_odds = self._fetch_historical_odds_at_time(
                        game['id'], 
                        game_time
                    )
                    
                    if historical_odds:
                        closing_lines[game['id']] = {
                            'game_info': game,
                            'closing_odds': historical_odds,
                            'fetch_time': game_time.isoformat(),
                            'line_type': 'closing'
                        }
                        
                        logger.info(f"Fetched closing line for {game['away_team']} @ {game['home_team']}")
                
                # Rate limiting to avoid API limits
                time.sleep(0.5)
            
            return {
                'date': date_str,
                'lines_type': 'closing',
                'games': closing_lines,
                'total_games': len(closing_lines),
                'fetched_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error fetching closing lines for {date_str}: {str(e)}")
            return {}
    
    def _get_games_schedule(self, date_str: str) -> List[Dict]:
        """Get games schedule for the date"""
        try:
            url = f"{self.base_url}/sports/baseball_mlb/odds"
            params = {
                'apiKey': self.api_key,
                'regions': 'us',
                'markets': 'h2h,spreads,totals',
                'oddsFormat': 'american',
                'dateFormat': 'iso',
                'date': date_str
            }
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Error fetching schedule for {date_str}: {str(e)}")
            return []
    
    def _fetch_historical_odds_at_time(self, game_id: str, game_time: datetime) -> Optional[Dict]:
        """
        Fetch historical odds as close to game time as possible
        Note: This requires OddsAPI historical endpoint access
        """
        try:
            # Calculate the optimal time to fetch (15 minutes before game time)
            fetch_time = game_time - timedelta(minutes=15)
            
            url = f"{self.base_url}/sports/baseball_mlb/odds-history"
            params = {
                'apiKey': self.api_key,
                'regions': 'us',
                'markets': 'h2h,spreads,totals',
                'oddsFormat': 'american',
                'dateFormat': 'iso',
                'date': fetch_time.strftime('%Y-%m-%dT%H:%M:%SZ')
            }
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            # Find the specific game in historical data
            historical_data = response.json()
            for game in historical_data:
                if game.get('id') == game_id:
                    return game.get('bookmakers', [])
            
            return None
            
        except Exception as e:
            logger.error(f"Error fetching historical odds for game {game_id}: {str(e)}")
            return None
    
    def _is_game_completed(self, game_time: datetime) -> bool:
        """Check if a game is completed (game time + 4 hours has passed)"""
        now = datetime.now(game_time.tzinfo)
        return now > (game_time + timedelta(hours=4))
    
    def fetch_live_closing_lines(self) -> Dict[str, Any]:
        """
        Fetch lines for games that are about to start (within 30 minutes)
        These are considered 'closing' lines for live games
        """
        try:
            url = f"{self.base_url}/sports/baseball_mlb/odds"
            params = {
                'apiKey': self.api_key,
                'regions': 'us',
                'markets': 'h2h,spreads,totals',
                'oddsFormat': 'american',
                'dateFormat': 'iso'
            }
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            closing_games = {}
            now = datetime.now()
            
            for game in data:
                game_time = datetime.fromisoformat(game['commence_time'].replace('Z', '+00:00'))
                time_to_game = (game_time.replace(tzinfo=None) - now).total_seconds() / 60
                
                # Consider games starting within 30 minutes as 'closing line' candidates
                if 0 <= time_to_game <= 30:
                    closing_games[game['id']] = {
                        'game_info': game,
                        'closing_odds': game.get('bookmakers', []),
                        'fetch_time': now.isoformat(),
                        'line_type': 'near_closing',
                        'minutes_to_game': time_to_game
                    }
            
            return {
                'lines_type': 'near_closing',
                'games': closing_games,
                'total_games': len(closing_games),
                'fetched_at': now.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error fetching live closing lines: {str(e)}")
            return {}

class ClosingLineValidator:
    """Utility to validate and analyze betting line quality"""
    
    @staticmethod
    def analyze_line_timing(betting_data: Dict) -> Dict[str, Any]:
        """Analyze the timing of betting lines to determine if they're closing lines"""
        analysis = {
            'is_closing_lines': False,
            'line_quality': 'unknown',
            'recommendations': []
        }
        
        try:
            fetch_time = datetime.fromisoformat(betting_data.get('updated_at', ''))
            
            # Check individual games
            game_analyses = []
            for game_key, game_data in betting_data.get('games', {}).items():
                if isinstance(game_data, dict) and 'start_time' in game_data:
                    start_time = datetime.fromisoformat(game_data['start_time'].replace('Z', '+00:00'))
                    time_diff = (start_time.replace(tzinfo=None) - fetch_time).total_seconds() / 60
                    
                    game_analyses.append({
                        'game': f"{game_data.get('away_team')} @ {game_data.get('home_team')}",
                        'minutes_before_game': time_diff,
                        'is_closing': time_diff <= 30
                    })
            
            if game_analyses:
                avg_time_diff = sum(g['minutes_before_game'] for g in game_analyses) / len(game_analyses)
                closing_percentage = sum(1 for g in game_analyses if g['is_closing']) / len(game_analyses)
                
                analysis.update({
                    'avg_minutes_before_game': avg_time_diff,
                    'closing_line_percentage': closing_percentage,
                    'total_games_analyzed': len(game_analyses),
                    'game_details': game_analyses
                })
                
                # Determine line quality
                if avg_time_diff <= 30:
                    analysis['line_quality'] = 'closing'
                    analysis['is_closing_lines'] = True
                elif avg_time_diff <= 120:
                    analysis['line_quality'] = 'late_pregame'
                elif avg_time_diff <= 360:
                    analysis['line_quality'] = 'mid_pregame'
                else:
                    analysis['line_quality'] = 'early_pregame'
                
                # Generate recommendations
                if not analysis['is_closing_lines']:
                    analysis['recommendations'].extend([
                        f"Lines were fetched {avg_time_diff:.0f} minutes before games",
                        "Consider fetching odds closer to game time (within 30 minutes)",
                        "Use historical odds API for completed games",
                        "Implement automatic fetching 15-30 minutes before each game"
                    ])
        
        except Exception as e:
            analysis['error'] = str(e)
        
        return analysis

if __name__ == "__main__":
    # Example usage and validation
    print("🔍 Closing Lines Validator")
    
    # Load current betting data for analysis
    try:
        with open('data/master_betting_lines.json', 'r') as f:
            current_data = json.load(f)
        
        validator = ClosingLineValidator()
        analysis = validator.analyze_line_timing(current_data)
        
        print(f"\n📊 Line Quality Analysis:")
        print(f"   Line Quality: {analysis.get('line_quality', 'unknown').upper()}")
        print(f"   Is Closing Lines: {analysis.get('is_closing_lines', False)}")
        print(f"   Avg Time Before Game: {analysis.get('avg_minutes_before_game', 0):.0f} minutes")
        print(f"   Closing Line %: {analysis.get('closing_line_percentage', 0)*100:.0f}%")
        
        if analysis.get('recommendations'):
            print(f"\n💡 Recommendations:")
            for rec in analysis['recommendations']:
                print(f"   • {rec}")
    
    except Exception as e:
        print(f"❌ Error analyzing current data: {e}")
