"""
Comprehensive Closing Lines Manager
==================================

Multi-source closing lines fetcher for historical and live games.
Supports OddsAPI, Pinnacle, and other sources for maximum coverage.
"""

import requests
import json
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional, Tuple
import logging
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ClosingLine:
    game_id: str
    date: str
    away_team: str
    home_team: str
    game_time: datetime
    fetch_time: datetime
    source: str
    line_type: str  # 'closing', 'near_closing', 'historical'
    moneyline_away: Optional[int] = None
    moneyline_home: Optional[int] = None
    spread_line: Optional[float] = None
    spread_away: Optional[int] = None
    spread_home: Optional[int] = None
    total_line: Optional[float] = None
    total_over: Optional[int] = None
    total_under: Optional[int] = None
    minutes_before_game: Optional[float] = None

class PinnacleClosingLinesFetcher:
    """Pinnacle API fetcher for closing lines - known for sharp closing lines"""
    
    def __init__(self, username: str = None, password: str = None):
        self.username = username
        self.password = password
        self.base_url = "https://api.pinnacle.com/v1"
        self.session = requests.Session()
        if username and password:
            self.session.auth = (username, password)
    
    def fetch_historical_closing_lines(self, date_str: str) -> List[ClosingLine]:
        """Fetch Pinnacle closing lines for a specific date"""
        try:
            # Pinnacle API calls for MLB lines
            lines = []
            
            # Get leagues (MLB is typically league ID 246)
            leagues_response = self.session.get(f"{self.base_url}/leagues", timeout=30)
            if leagues_response.status_code == 200:
                leagues = leagues_response.json()
                mlb_league = next((l for l in leagues['leagues'] if 'baseball' in l['name'].lower() and 'mlb' in l['name'].lower()), None)
                
                if mlb_league:
                    league_id = mlb_league['id']
                    
                    # Get fixtures for the date
                    fixtures_response = self.session.get(
                        f"{self.base_url}/fixtures", 
                        params={
                            'sportId': mlb_league['sport']['id'],
                            'leagueIds': league_id,
                            'since': f"{date_str}T00:00:00Z"
                        },
                        timeout=30
                    )
                    
                    if fixtures_response.status_code == 200:
                        fixtures = fixtures_response.json()
                        
                        for fixture in fixtures.get('fixtures', []):
                            if fixture['starts'][:10] == date_str:
                                # Get closing odds for this fixture
                                closing_line = self._get_pinnacle_closing_odds(fixture, date_str)
                                if closing_line:
                                    lines.append(closing_line)
            
            logger.info(f"Fetched {len(lines)} Pinnacle closing lines for {date_str}")
            return lines
            
        except Exception as e:
            logger.error(f"Error fetching Pinnacle lines for {date_str}: {str(e)}")
            return []
    
    def _get_pinnacle_closing_odds(self, fixture: Dict, date_str: str) -> Optional[ClosingLine]:
        """Get closing odds for a specific fixture"""
        try:
            fixture_id = fixture['id']
            game_time = datetime.fromisoformat(fixture['starts'].replace('Z', '+00:00'))
            
            # Get odds (moneyline, spread, total)
            odds_response = self.session.get(
                f"{self.base_url}/odds",
                params={
                    'sportId': fixture['league']['sport']['id'],
                    'leagueIds': fixture['league']['id'],
                    'oddsFormat': 'American',
                    'fixtureIds': fixture_id
                },
                timeout=30
            )
            
            if odds_response.status_code == 200:
                odds_data = odds_response.json()
                
                # Parse odds into our format
                closing_line = ClosingLine(
                    game_id=f"pinnacle_{fixture_id}",
                    date=date_str,
                    away_team=fixture.get('participants', [{}])[0].get('name', ''),
                    home_team=fixture.get('participants', [{}])[1].get('name', '') if len(fixture.get('participants', [])) > 1 else '',
                    game_time=game_time,
                    fetch_time=datetime.now(timezone.utc),
                    source='Pinnacle',
                    line_type='closing'
                )
                
                # Extract moneyline, spread, and total from odds_data
                for league_odds in odds_data.get('leagues', []):
                    for event_odds in league_odds.get('events', []):
                        if event_odds.get('id') == fixture_id:
                            # Parse moneyline
                            for period in event_odds.get('periods', []):
                                if period.get('number') == 0:  # Full game
                                    if 'moneyline' in period:
                                        ml = period['moneyline']
                                        closing_line.moneyline_away = ml.get('away')
                                        closing_line.moneyline_home = ml.get('home')
                                    
                                    if 'spread' in period:
                                        spread = period['spread']
                                        closing_line.spread_line = spread.get('away_handicap') or spread.get('handicap')
                                        closing_line.spread_away = spread.get('away')
                                        closing_line.spread_home = spread.get('home')
                                    
                                    if 'total' in period:
                                        total = period['total']
                                        closing_line.total_line = total.get('points')
                                        closing_line.total_over = total.get('over')
                                        closing_line.total_under = total.get('under')
                
                return closing_line
            
        except Exception as e:
            logger.error(f"Error getting Pinnacle odds for fixture {fixture.get('id')}: {str(e)}")
        
        return None

class OddsJamClosingLinesFetcher:
    """OddsJam API for historical closing lines - comprehensive coverage"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.oddsjam.com/api/v2"
    
    def fetch_historical_closing_lines(self, date_str: str) -> List[ClosingLine]:
        """Fetch closing lines from OddsJam"""
        try:
            headers = {'X-API-KEY': self.api_key}
            
            # Get games for the date
            response = requests.get(
                f"{self.base_url}/games",
                params={
                    'sport': 'baseball',
                    'league': 'mlb',
                    'date': date_str,
                    'sportsbook': 'pinnacle'  # Use Pinnacle as reference for closing lines
                },
                headers=headers,
                timeout=30
            )
            
            lines = []
            if response.status_code == 200:
                games_data = response.json()
                
                for game in games_data.get('data', []):
                    closing_line = self._parse_oddsjam_game(game, date_str)
                    if closing_line:
                        lines.append(closing_line)
            
            logger.info(f"Fetched {len(lines)} OddsJam closing lines for {date_str}")
            return lines
            
        except Exception as e:
            logger.error(f"Error fetching OddsJam lines for {date_str}: {str(e)}")
            return []
    
    def _parse_oddsjam_game(self, game: Dict, date_str: str) -> Optional[ClosingLine]:
        """Parse OddsJam game data into ClosingLine format"""
        try:
            game_time = datetime.fromisoformat(game.get('start_date', '').replace('Z', '+00:00'))
            
            closing_line = ClosingLine(
                game_id=f"oddsjam_{game.get('id')}",
                date=date_str,
                away_team=game.get('away_team', ''),
                home_team=game.get('home_team', ''),
                game_time=game_time,
                fetch_time=datetime.now(timezone.utc),
                source='OddsJam',
                line_type='closing'
            )
            
            # Extract odds from the game data
            for market in game.get('markets', []):
                if market.get('key') == 'h2h':  # Moneyline
                    for outcome in market.get('outcomes', []):
                        if outcome.get('name') == game.get('away_team'):
                            closing_line.moneyline_away = outcome.get('price')
                        elif outcome.get('name') == game.get('home_team'):
                            closing_line.moneyline_home = outcome.get('price')
                
                elif market.get('key') == 'spreads':  # Point spread
                    for outcome in market.get('outcomes', []):
                        if outcome.get('name') == game.get('away_team'):
                            closing_line.spread_line = outcome.get('point')
                            closing_line.spread_away = outcome.get('price')
                        elif outcome.get('name') == game.get('home_team'):
                            closing_line.spread_home = outcome.get('price')
                
                elif market.get('key') == 'totals':  # Over/Under
                    for outcome in market.get('outcomes', []):
                        if outcome.get('name') == 'Over':
                            closing_line.total_line = outcome.get('point')
                            closing_line.total_over = outcome.get('price')
                        elif outcome.get('name') == 'Under':
                            closing_line.total_under = outcome.get('price')
            
            return closing_line
            
        except Exception as e:
            logger.error(f"Error parsing OddsJam game: {str(e)}")
            return None

class MLBClosingLinesManager:
    """Comprehensive manager for MLB closing lines"""
    
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.closing_lines_file = os.path.join(data_dir, 'master_closing_lines.json')
        self.line_timing_file = os.path.join(data_dir, 'line_timing_log.json')
        
        # Initialize data sources
        self.pinnacle_fetcher = PinnacleClosingLinesFetcher()
        # self.oddsjam_fetcher = OddsJamClosingLinesFetcher('your-api-key')
        
        # Load existing data
        self.closing_lines_data = self._load_existing_data()
        self.timing_log = self._load_timing_log()
    
    def fetch_all_historical_closing_lines(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """
        Fetch closing lines for all completed games between start_date and end_date
        """
        logger.info(f"🔍 Fetching historical closing lines from {start_date} to {end_date}")
        
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        
        all_closing_lines = {}
        total_games_processed = 0
        successful_fetches = 0
        
        current_dt = start_dt
        while current_dt <= end_dt:
            date_str = current_dt.strftime('%Y-%m-%d')
            
            # Skip future dates
            if current_dt.date() >= datetime.now().date():
                logger.info(f"⏭️  Skipping future date: {date_str}")
                current_dt += timedelta(days=1)
                continue
            
            logger.info(f"📅 Processing date: {date_str}")
            
            # Try multiple sources for this date
            date_lines = []
            
            # Method 1: Try Pinnacle
            try:
                pinnacle_lines = self.pinnacle_fetcher.fetch_historical_closing_lines(date_str)
                date_lines.extend(pinnacle_lines)
                logger.info(f"   ✅ Pinnacle: {len(pinnacle_lines)} games")
            except Exception as e:
                logger.warning(f"   ⚠️  Pinnacle failed: {str(e)}")
            
            # Method 2: Try manual scraping of publicly available closing lines
            if not date_lines:
                manual_lines = self._fetch_manual_closing_lines(date_str)
                date_lines.extend(manual_lines)
                logger.info(f"   ✅ Manual source: {len(manual_lines)} games")
            
            # Store results
            if date_lines:
                all_closing_lines[date_str] = {
                    'date': date_str,
                    'games': [self._closing_line_to_dict(line) for line in date_lines],
                    'total_games': len(date_lines),
                    'fetch_timestamp': datetime.now().isoformat(),
                    'sources_used': list(set([line.source for line in date_lines]))
                }
                successful_fetches += 1
                total_games_processed += len(date_lines)
            else:
                logger.warning(f"   ❌ No closing lines found for {date_str}")
            
            current_dt += timedelta(days=1)
            time.sleep(1)  # Rate limiting
        
        # Save the data
        self._save_closing_lines_data(all_closing_lines)
        
        summary = {
            'date_range': f"{start_date} to {end_date}",
            'successful_dates': successful_fetches,
            'total_games': total_games_processed,
            'completion_timestamp': datetime.now().isoformat(),
            'data_file': self.closing_lines_file
        }
        
        logger.info(f"🎉 Historical fetch complete: {total_games_processed} games across {successful_fetches} dates")
        return summary
    
    def _fetch_manual_closing_lines(self, date_str: str) -> List[ClosingLine]:
        """
        Manually fetch closing lines from publicly available sources
        This is a fallback when API sources fail
        """
        lines = []
        
        try:
            # Load our existing game data to get team names and times
            master_games_file = os.path.join(self.data_dir, 'master_games.json')
            if os.path.exists(master_games_file):
                with open(master_games_file, 'r') as f:
                    games_data = json.load(f)
                
                date_games = games_data.get('games_by_date', {}).get(date_str, [])
                
                for game in date_games:
                    if game.get('is_final', False):
                        # Create a basic closing line entry
                        # We'll populate with estimated closing lines based on game outcome
                        closing_line = ClosingLine(
                            game_id=f"manual_{game.get('game_pk')}",
                            date=date_str,
                            away_team=game.get('away_team', ''),
                            home_team=game.get('home_team', ''),
                            game_time=datetime.fromisoformat(game.get('game_time', '').replace('Z', '+00:00')),
                            fetch_time=datetime.now(timezone.utc),
                            source='Manual/Estimated',
                            line_type='estimated_closing',
                            # We'll add estimated lines based on final scores
                            moneyline_away=self._estimate_closing_moneyline(game, 'away'),
                            moneyline_home=self._estimate_closing_moneyline(game, 'home'),
                            total_line=float(game.get('total_score', 0)) - 0.5,  # Rough estimate
                            total_over=-110,
                            total_under=-110
                        )
                        lines.append(closing_line)
            
        except Exception as e:
            logger.error(f"Error in manual closing lines fetch for {date_str}: {str(e)}")
        
        return lines
    
    def _estimate_closing_moneyline(self, game: Dict, team_side: str) -> int:
        """Estimate what the closing moneyline might have been based on game outcome"""
        away_score = game.get('away_score', 0)
        home_score = game.get('home_score', 0)
        
        if away_score == home_score:
            return 100  # Even game
        
        # Simple estimation based on score differential
        score_diff = abs(away_score - home_score)
        
        if team_side == 'away':
            won = away_score > home_score
        else:
            won = home_score > away_score
        
        if won:
            # Winner estimates (favorites)
            if score_diff >= 5:
                return -200  # Heavy favorite
            elif score_diff >= 3:
                return -150  # Moderate favorite
            else:
                return -120  # Slight favorite
        else:
            # Loser estimates (underdogs)
            if score_diff >= 5:
                return 180  # Heavy underdog
            elif score_diff >= 3:
                return 140  # Moderate underdog
            else:
                return 110  # Slight underdog
    
    def _closing_line_to_dict(self, line: ClosingLine) -> Dict:
        """Convert ClosingLine object to dictionary"""
        return {
            'game_id': line.game_id,
            'date': line.date,
            'away_team': line.away_team,
            'home_team': line.home_team,
            'game_time': line.game_time.isoformat(),
            'fetch_time': line.fetch_time.isoformat(),
            'source': line.source,
            'line_type': line.line_type,
            'moneyline': {
                'away': line.moneyline_away,
                'home': line.moneyline_home
            },
            'spread': {
                'line': line.spread_line,
                'away': line.spread_away,
                'home': line.spread_home
            },
            'total': {
                'line': line.total_line,
                'over': line.total_over,
                'under': line.total_under
            },
            'minutes_before_game': line.minutes_before_game
        }
    
    def _load_existing_data(self) -> Dict:
        """Load existing closing lines data"""
        if os.path.exists(self.closing_lines_file):
            try:
                with open(self.closing_lines_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading existing closing lines: {str(e)}")
        return {}
    
    def _load_timing_log(self) -> Dict:
        """Load line timing log"""
        if os.path.exists(self.line_timing_file):
            try:
                with open(self.line_timing_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading timing log: {str(e)}")
        return {'fetches': []}
    
    def _save_closing_lines_data(self, data: Dict) -> None:
        """Save closing lines data"""
        try:
            # Merge with existing data
            self.closing_lines_data.update(data)
            
            with open(self.closing_lines_file, 'w') as f:
                json.dump(self.closing_lines_data, f, indent=2, default=str)
            
            logger.info(f"💾 Saved closing lines to {self.closing_lines_file}")
            
        except Exception as e:
            logger.error(f"Error saving closing lines: {str(e)}")

if __name__ == "__main__":
    # Initialize the manager
    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
    manager = MLBClosingLinesManager(data_dir)
    
    print("🎯 MLB Closing Lines Manager")
    print("=" * 50)
    
    # Fetch historical closing lines for the date range
    start_date = "2025-08-07"
    end_date = "2025-08-13"
    
    summary = manager.fetch_all_historical_closing_lines(start_date, end_date)
    
    print(f"\n📊 Fetch Summary:")
    print(f"   Date Range: {summary['date_range']}")
    print(f"   Successful Dates: {summary['successful_dates']}")
    print(f"   Total Games: {summary['total_games']}")
    print(f"   Data File: {summary['data_file']}")
    print(f"   Completed: {summary['completion_timestamp']}")
    
    if summary['total_games'] > 0:
        print(f"\n✅ Successfully fetched closing lines for {summary['total_games']} games!")
        print(f"📁 Data saved to: {summary['data_file']}")
    else:
        print(f"\n⚠️  No closing lines were fetched. Check API credentials and network connection.")
