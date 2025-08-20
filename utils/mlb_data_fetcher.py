"""
MLB Data Fetcher
================

Utility for fetching real-time MLB data from official APIs.
Supports schedule, starting pitchers, and game results.
"""

import requests
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)

class MLBDataFetcher:
    def __init__(self, data_dir: str = None):
        self.data_dir = data_dir or os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
        self.base_url = "https://statsapi.mlb.com/api/v1"
        
    def fetch_schedule_for_date(self, date_str: str) -> List[Dict[str, Any]]:
        """Fetch MLB schedule for a specific date"""
        try:
            url = f"{self.base_url}/schedule"
            params = {
                'sportId': 1,
                'date': date_str,
                'hydrate': 'game(content(editorial(preview,recap)),decisions,person,probablePitcher,stats,homeRuns,previousPlay,team),linescore(runners),xrefId,story'
            }
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            games = []
            
            for date_entry in data.get('dates', []):
                for game in date_entry.get('games', []):
                    game_data = self._parse_game_data(game, date_str)
                    games.append(game_data)
            
            logger.info(f"Fetched {len(games)} games for {date_str}")
            return games
            
        except Exception as e:
            logger.error(f"Error fetching schedule for {date_str}: {str(e)}")
            return []
    
    def _parse_game_data(self, game: Dict, date_str: str) -> Dict[str, Any]:
        """Parse raw MLB API game data into our format"""
        game_data = {
            'game_pk': game.get('gamePk'),
            'game_date': date_str,
            'status': game.get('status', {}).get('detailedState', 'Unknown'),
            'status_code': game.get('status', {}).get('statusCode', ''),
            'game_time': game.get('gameDate'),
            'away_team': game.get('teams', {}).get('away', {}).get('team', {}).get('name', ''),
            'away_team_id': game.get('teams', {}).get('away', {}).get('team', {}).get('id'),
            'home_team': game.get('teams', {}).get('home', {}).get('team', {}).get('name', ''),
            'home_team_id': game.get('teams', {}).get('home', {}).get('team', {}).get('id'),
            'venue': game.get('venue', {}).get('name', ''),
            'away_score': game.get('teams', {}).get('away', {}).get('score'),
            'home_score': game.get('teams', {}).get('home', {}).get('score'),
            'is_final': game.get('status', {}).get('statusCode') == 'F',
            'data_source': 'MLB API'
        }
        
        # Extract pitchers
        probable_pitchers = game.get('teams', {})
        if 'away' in probable_pitchers and 'probablePitcher' in probable_pitchers['away']:
            away_pitcher = probable_pitchers['away']['probablePitcher']
            game_data['away_pitcher'] = away_pitcher.get('fullName', 'TBD')
            game_data['away_pitcher_id'] = away_pitcher.get('id')
        else:
            game_data['away_pitcher'] = 'TBD'
            game_data['away_pitcher_id'] = None
        
        if 'home' in probable_pitchers and 'probablePitcher' in probable_pitchers['home']:
            home_pitcher = probable_pitchers['home']['probablePitcher']
            game_data['home_pitcher'] = home_pitcher.get('fullName', 'TBD')
            game_data['home_pitcher_id'] = home_pitcher.get('id')
        else:
            game_data['home_pitcher'] = 'TBD'
            game_data['home_pitcher_id'] = None
        
        return game_data
    
    def fetch_date_range(self, start_date: str, end_date: str) -> Dict[str, List[Dict]]:
        """Fetch schedule for a range of dates"""
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        
        all_games = {}
        current_dt = start_dt
        
        while current_dt <= end_dt:
            date_str = current_dt.strftime('%Y-%m-%d')
            games = self.fetch_schedule_for_date(date_str)
            all_games[date_str] = games
            current_dt += timedelta(days=1)
        
        return all_games
    
    def fetch_pitcher_stats(self, pitcher_id: int, season: int = 2025) -> Dict[str, Any]:
        """Fetch detailed pitcher statistics"""
        try:
            url = f"{self.base_url}/people/{pitcher_id}/stats"
            params = {
                'stats': 'season',
                'sportId': 1,
                'season': season
            }
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # Extract pitching stats
            for stat_group in data.get('stats', []):
                for split in stat_group.get('splits', []):
                    stats = split.get('stat', {})
                    if 'era' in stats:  # This is pitching stats
                        return {
                            'era': stats.get('era'),
                            'whip': stats.get('whip'),
                            'strikeouts': stats.get('strikeOuts'),
                            'walks': stats.get('baseOnBalls'),
                            'innings_pitched': stats.get('inningsPitched'),
                            'games_started': stats.get('gamesStarted'),
                            'wins': stats.get('wins'),
                            'losses': stats.get('losses'),
                            'saves': stats.get('saves')
                        }
            
            return {}
            
        except Exception as e:
            logger.error(f"Error fetching pitcher stats for {pitcher_id}: {str(e)}")
            return {}
    
    def fetch_team_stats(self, team_id: int, season: int = 2025) -> Dict[str, Any]:
        """Fetch team statistics"""
        try:
            url = f"{self.base_url}/teams/{team_id}/stats"
            params = {
                'stats': 'season',
                'sportId': 1,
                'season': season
            }
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # Extract team stats
            for stat_group in data.get('stats', []):
                for split in stat_group.get('splits', []):
                    stats = split.get('stat', {})
                    return {
                        'wins': stats.get('wins'),
                        'losses': stats.get('losses'),
                        'win_percentage': stats.get('winningPercentage'),
                        'runs_scored': stats.get('runs'),
                        'runs_allowed': stats.get('runsAllowed'),
                        'home_runs': stats.get('homeRuns'),
                        'era': stats.get('era'),
                        'batting_avg': stats.get('avg')
                    }
            
            return {}
            
        except Exception as e:
            logger.error(f"Error fetching team stats for {team_id}: {str(e)}")
            return {}

class OddsAPIFetcher:
    """Fetcher for betting odds from OddsAPI"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.the-odds-api.com/v4"
    
    def fetch_mlb_odds(self, date_str: str = None) -> List[Dict[str, Any]]:
        """Fetch MLB betting odds"""
        try:
            url = f"{self.base_url}/sports/baseball_mlb/odds"
            params = {
                'apiKey': self.api_key,
                'regions': 'us',
                'markets': 'h2h,spreads,totals',
                'oddsFormat': 'american',
                'dateFormat': 'iso'
            }
            
            if date_str:
                params['date'] = date_str
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"Fetched odds for {len(data)} games")
            return data
            
        except Exception as e:
            logger.error(f"Error fetching odds: {str(e)}")
            return []
    
    def parse_odds_data(self, odds_data: List[Dict]) -> Dict[str, Dict]:
        """Parse odds data into our format"""
        parsed_odds = {}
        
        for game in odds_data:
            home_team = game.get('home_team', '')
            away_team = game.get('away_team', '')
            
            if not home_team or not away_team:
                continue
            
            game_key = f"{away_team}_at_{home_team}"
            
            parsed_odds[game_key] = {
                'home_team': home_team,
                'away_team': away_team,
                'commence_time': game.get('commence_time'),
                'bookmakers': self._parse_bookmakers(game.get('bookmakers', []))
            }
        
        return parsed_odds
    
    def _parse_bookmakers(self, bookmakers: List[Dict]) -> Dict[str, Dict]:
        """Parse bookmaker data"""
        parsed = {}
        
        for book in bookmakers:
            book_name = book.get('title', '')
            markets = {}
            
            for market in book.get('markets', []):
                market_key = market.get('key', '')
                outcomes = {}
                
                for outcome in market.get('outcomes', []):
                    outcome_name = outcome.get('name', '')
                    outcomes[outcome_name] = {
                        'price': outcome.get('price'),
                        'point': outcome.get('point')
                    }
                
                markets[market_key] = outcomes
            
            parsed[book_name] = markets
        
        return parsed

if __name__ == "__main__":
    # Test the fetcher
    fetcher = MLBDataFetcher()
    
    # Fetch today's games
    today = datetime.now().strftime('%Y-%m-%d')
    games = fetcher.fetch_schedule_for_date(today)
    
    print(f"Found {len(games)} games for {today}")
    for game in games[:3]:  # Show first 3 games
        print(f"{game['away_team']} @ {game['home_team']}")
        print(f"  Pitchers: {game['away_pitcher']} vs {game['home_pitcher']}")
        print(f"  Status: {game['status']}")
        print()
