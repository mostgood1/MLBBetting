"""
Automated Closing Lines Fetcher for Future MLB Games
Fetches closing lines at optimal timing (15-30 minutes before game time)
Implements regular fetching cycle until game time as requested
"""

import json
import logging
import schedule
import time
import threading
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
import requests
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('automated_closing_lines.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AutomatedClosingLinesFetcher:
    """
    Automated system for fetching closing lines for future games
    """
    
    def __init__(self):
        self.base_dir = Path(__file__).parent.parent
        self.data_dir = self.base_dir / "data"
        self.master_lines_file = self.data_dir / "master_closing_lines.json"
        self.config_file = self.data_dir / "closing_lines_config.json"
        
        # Load configuration
        self.config = self.load_config()
        
        # API configurations
        api_keys = self.config.get('api_keys', {})
        self.odds_api_key = api_keys.get('odds_api_key', '')
        self.pinnacle_username = api_keys.get('pinnacle_username', '')
        self.pinnacle_password = api_keys.get('pinnacle_password', '')
        
        # Timing configurations (in minutes before game)
        fetch_timing = self.config.get('fetch_timing', {})
        self.optimal_fetch_time = fetch_timing.get('optimal_fetch_time', 20)  # 20 minutes before game
        self.backup_fetch_times = fetch_timing.get('fetch_timing_minutes', [45, 30, 15, 10, 5])  # Multiple attempts
        self.max_fetch_attempts = 3
        
        # Scheduled jobs tracking
        self.scheduled_jobs = {}
        self.fetching_active = False
        
    def load_config(self) -> Dict:
        """Load configuration file with API keys and settings"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            else:
                # Create default config
                default_config = {
                    "odds_api_key": "",
                    "pinnacle_username": "",
                    "pinnacle_password": "",
                    "fetch_timing_minutes": [45, 30, 20, 15, 10, 5],
                    "max_attempts_per_timing": 3,
                    "enable_email_alerts": False,
                    "email_config": {}
                }
                with open(self.config_file, 'w') as f:
                    json.dump(default_config, f, indent=2)
                logger.info(f"Created default config at {self.config_file}")
                return default_config
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return {}
    
    def get_todays_games(self) -> List[Dict]:
        """Get today's games from master data"""
        try:
            master_file = self.data_dir / "master_games.json"
            if not master_file.exists():
                logger.warning("Master games data not found")
                return []
            
            with open(master_file, 'r') as f:
                master_data = json.load(f)
            
            today = datetime.now().strftime('%Y-%m-%d')
            
            if today in master_data:
                games = master_data[today].get('games', [])
                logger.info(f"Found {len(games)} games for {today}")
                return games
            else:
                logger.info(f"No games found for {today}")
                return []
                
        except Exception as e:
            logger.error(f"Error getting today's games: {e}")
            return []
    
    def get_future_games(self, days_ahead: int = 7) -> Dict[str, List[Dict]]:
        """Get upcoming games for the next N days"""
        try:
            master_file = self.data_dir / "master_games.json"
            if not master_file.exists():
                return {}
            
            with open(master_file, 'r') as f:
                master_data = json.load(f)
            
            future_games = {}
            for i in range(days_ahead):
                date = (datetime.now() + timedelta(days=i)).strftime('%Y-%m-%d')
                if date in master_data:
                    games = master_data[date].get('games', [])
                    if games:
                        future_games[date] = games
                        logger.info(f"Found {len(games)} games for {date}")
            
            return future_games
            
        except Exception as e:
            logger.error(f"Error getting future games: {e}")
            return {}
    
    def fetch_live_closing_lines(self, game: Dict) -> Optional[Dict]:
        """
        Fetch actual closing lines from live sources
        Priority: Pinnacle > OddsAPI > Manual estimation
        """
        game_time_str = game.get('startTime', game.get('game_time', ''))
        current_time = datetime.now(timezone.utc)
        
        # Calculate minutes before game
        try:
            if 'T' in game_time_str:
                game_time = datetime.fromisoformat(game_time_str.replace('Z', '+00:00'))
            else:
                # Handle different time formats
                game_time = datetime.strptime(game_time_str, '%Y-%m-%d %H:%M:%S')
                game_time = game_time.replace(tzinfo=timezone.utc)
                
            minutes_before = (game_time - current_time).total_seconds() / 60
        except Exception as e:
            logger.error(f"Error parsing game time {game_time_str}: {e}")
            minutes_before = None
        
        # Try Pinnacle first (most accurate closing lines)
        closing_line = self.fetch_pinnacle_closing_line(game)
        if closing_line:
            closing_line['minutes_before_game'] = minutes_before
            closing_line['source'] = 'Pinnacle'
            closing_line['line_type'] = 'closing' if minutes_before and minutes_before <= 30 else 'late_pregame'
            return closing_line
        
        # Try OddsAPI
        closing_line = self.fetch_odds_api_closing_line(game)
        if closing_line:
            closing_line['minutes_before_game'] = minutes_before
            closing_line['source'] = 'OddsAPI'
            closing_line['line_type'] = 'closing' if minutes_before and minutes_before <= 30 else 'late_pregame'
            return closing_line
        
        # Fallback to manual estimation
        logger.warning(f"No live sources available for game {game.get('game_id', 'unknown')}, using estimation")
        return None
    
    def fetch_pinnacle_closing_line(self, game: Dict) -> Optional[Dict]:
        """Fetch closing line from Pinnacle API"""
        if not self.pinnacle_username or not self.pinnacle_password:
            return None
        
        try:
            # Pinnacle API endpoint for MLB
            url = "https://api.pinnacle.com/v2/odds"
            
            auth = (self.pinnacle_username, self.pinnacle_password)
            params = {
                'sportId': 246,  # MLB
                'leagueIds': 246,
                'oddsFormat': 'AMERICAN',
                'isLive': False
            }
            
            response = requests.get(url, auth=auth, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                # Parse Pinnacle response for this specific game
                return self.parse_pinnacle_response(data, game)
            else:
                logger.warning(f"Pinnacle API error {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching from Pinnacle: {e}")
            return None
    
    def fetch_odds_api_closing_line(self, game: Dict) -> Optional[Dict]:
        """Fetch closing line from OddsAPI"""
        if not self.odds_api_key:
            return None
        
        try:
            url = "https://api.the-odds-api.com/v4/sports/baseball_mlb/odds"
            
            params = {
                'apiKey': self.odds_api_key,
                'regions': 'us',
                'markets': 'h2h,spreads,totals',
                'oddsFormat': 'american',
                'bookmakers': 'pinnacle,fanduel,draftkings'
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return self.parse_odds_api_response(data, game)
            else:
                logger.warning(f"OddsAPI error {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching from OddsAPI: {e}")
            return None
    
    def parse_pinnacle_response(self, data: Dict, game: Dict) -> Optional[Dict]:
        """Parse Pinnacle API response for specific game"""
        try:
            away_team = game.get('away_team', '')
            home_team = game.get('home_team', '')
            
            # Find matching game in Pinnacle data
            for event in data.get('events', []):
                participants = event.get('participants', [])
                if len(participants) >= 2:
                    # Check if teams match
                    if (away_team in participants[0].get('name', '') or 
                        home_team in participants[1].get('name', '')):
                        
                        # Extract odds
                        periods = event.get('periods', [])
                        if periods:
                            period = periods[0]  # Full game
                            
                            closing_line = {
                                'game_id': game.get('game_id', ''),
                                'date': game.get('date', ''),
                                'away_team': away_team,
                                'home_team': home_team,
                                'game_time': game.get('startTime', game.get('game_time', '')),
                                'fetch_time': datetime.now(timezone.utc).isoformat(),
                                'moneyline': {},
                                'spread': {},
                                'total': {}
                            }
                            
                            # Parse moneyline
                            moneyline = period.get('moneyline', {})
                            if moneyline:
                                closing_line['moneyline'] = {
                                    'away': moneyline.get('away', 0),
                                    'home': moneyline.get('home', 0)
                                }
                            
                            # Parse spread
                            spread = period.get('spread', {})
                            if spread:
                                closing_line['spread'] = {
                                    'line': spread.get('hdp', 0),
                                    'away': spread.get('away', 0),
                                    'home': spread.get('home', 0)
                                }
                            
                            # Parse total
                            total = period.get('total', {})
                            if total:
                                closing_line['total'] = {
                                    'line': total.get('points', 0),
                                    'over': total.get('over', 0),
                                    'under': total.get('under', 0)
                                }
                            
                            return closing_line
            
            return None
            
        except Exception as e:
            logger.error(f"Error parsing Pinnacle response: {e}")
            return None
    
    def parse_odds_api_response(self, data: List, game: Dict) -> Optional[Dict]:
        """Parse OddsAPI response for specific game"""
        try:
            away_team = game.get('away_team', '')
            home_team = game.get('home_team', '')
            
            for event in data:
                # Check if teams match
                if (away_team in event.get('away_team', '') or 
                    home_team in event.get('home_team', '')):
                    
                    closing_line = {
                        'game_id': game.get('game_id', ''),
                        'date': game.get('date', ''),
                        'away_team': away_team,
                        'home_team': home_team,
                        'game_time': game.get('startTime', game.get('game_time', '')),
                        'fetch_time': datetime.now(timezone.utc).isoformat(),
                        'moneyline': {},
                        'spread': {},
                        'total': {}
                    }
                    
                    # Parse bookmaker odds (prefer Pinnacle)
                    bookmakers = event.get('bookmakers', [])
                    pinnacle_odds = None
                    backup_odds = None
                    
                    for bookmaker in bookmakers:
                        if bookmaker.get('key') == 'pinnacle':
                            pinnacle_odds = bookmaker
                            break
                        elif not backup_odds:
                            backup_odds = bookmaker
                    
                    odds_source = pinnacle_odds or backup_odds
                    if not odds_source:
                        continue
                    
                    # Parse markets
                    for market in odds_source.get('markets', []):
                        market_key = market.get('key', '')
                        outcomes = market.get('outcomes', [])
                        
                        if market_key == 'h2h' and len(outcomes) >= 2:
                            # Moneyline
                            for outcome in outcomes:
                                if outcome.get('name') == event.get('away_team'):
                                    closing_line['moneyline']['away'] = outcome.get('price', 0)
                                elif outcome.get('name') == event.get('home_team'):
                                    closing_line['moneyline']['home'] = outcome.get('price', 0)
                        
                        elif market_key == 'spreads' and len(outcomes) >= 2:
                            # Spread
                            for outcome in outcomes:
                                if outcome.get('name') == event.get('away_team'):
                                    closing_line['spread']['away'] = outcome.get('price', 0)
                                    closing_line['spread']['line'] = outcome.get('point', 0)
                                elif outcome.get('name') == event.get('home_team'):
                                    closing_line['spread']['home'] = outcome.get('price', 0)
                        
                        elif market_key == 'totals' and len(outcomes) >= 2:
                            # Total
                            for outcome in outcomes:
                                if outcome.get('name') == 'Over':
                                    closing_line['total']['over'] = outcome.get('price', 0)
                                    closing_line['total']['line'] = outcome.get('point', 0)
                                elif outcome.get('name') == 'Under':
                                    closing_line['total']['under'] = outcome.get('price', 0)
                    
                    return closing_line
            
            return None
            
        except Exception as e:
            logger.error(f"Error parsing OddsAPI response: {e}")
            return None
    
    def save_closing_line(self, closing_line: Dict):
        """Save closing line to master file"""
        try:
            # Load existing data
            if self.master_lines_file.exists():
                with open(self.master_lines_file, 'r') as f:
                    master_lines = json.load(f)
            else:
                master_lines = {}
            
            date = closing_line.get('date', '')
            if date not in master_lines:
                master_lines[date] = {
                    'date': date,
                    'games': []
                }
            
            # Check if game already exists
            game_id = closing_line.get('game_id', '')
            existing_game = None
            for i, game in enumerate(master_lines[date]['games']):
                if game.get('game_id') == game_id:
                    existing_game = i
                    break
            
            if existing_game is not None:
                # Update existing game
                master_lines[date]['games'][existing_game] = closing_line
                logger.info(f"Updated closing line for game {game_id}")
            else:
                # Add new game
                master_lines[date]['games'].append(closing_line)
                logger.info(f"Added new closing line for game {game_id}")
            
            # Save updated data
            with open(self.master_lines_file, 'w') as f:
                json.dump(master_lines, f, indent=2)
            
        except Exception as e:
            logger.error(f"Error saving closing line: {e}")
    
    def schedule_game_fetches(self, game: Dict):
        """Schedule multiple fetch attempts for a single game"""
        try:
            game_time_str = game.get('startTime', game.get('game_time', ''))
            if 'T' in game_time_str:
                game_time = datetime.fromisoformat(game_time_str.replace('Z', '+00:00'))
            else:
                game_time = datetime.strptime(game_time_str, '%Y-%m-%d %H:%M:%S')
                game_time = game_time.replace(tzinfo=timezone.utc)
            
            game_id = game.get('game_id', '')
            
            # Schedule fetches at multiple times before the game
            for minutes_before in self.config.get('fetch_timing_minutes', [45, 30, 20, 15, 10, 5]):
                fetch_time = game_time - timedelta(minutes=minutes_before)
                
                # Only schedule if fetch time is in the future
                if fetch_time > datetime.now(timezone.utc):
                    job_id = f"{game_id}_{minutes_before}min"
                    
                    # Schedule the job
                    schedule.every().day.at(fetch_time.strftime('%H:%M')).do(
                        self.fetch_and_save_game_line, game
                    ).tag(job_id)
                    
                    self.scheduled_jobs[job_id] = {
                        'game_id': game_id,
                        'fetch_time': fetch_time.isoformat(),
                        'minutes_before': minutes_before
                    }
                    
                    logger.info(f"Scheduled fetch for {game_id} at {fetch_time} ({minutes_before} min before)")
            
        except Exception as e:
            logger.error(f"Error scheduling fetches for game {game.get('game_id', 'unknown')}: {e}")
    
    def fetch_and_save_game_line(self, game: Dict):
        """Fetch and save closing line for a single game"""
        try:
            logger.info(f"Fetching closing line for game {game.get('game_id', 'unknown')}")
            
            closing_line = self.fetch_live_closing_lines(game)
            if closing_line:
                self.save_closing_line(closing_line)
                logger.info(f"Successfully fetched and saved closing line")
            else:
                logger.warning(f"Failed to fetch closing line for game {game.get('game_id', 'unknown')}")
        
        except Exception as e:
            logger.error(f"Error in fetch_and_save_game_line: {e}")
    
    def setup_automated_fetching(self):
        """Set up automated fetching for future games"""
        try:
            logger.info("Setting up automated closing lines fetching...")
            
            # Get future games
            future_games = self.get_future_games(days_ahead=7)
            
            total_scheduled = 0
            for date, games in future_games.items():
                logger.info(f"Scheduling fetches for {len(games)} games on {date}")
                for game in games:
                    self.schedule_game_fetches(game)
                    total_scheduled += 1
            
            logger.info(f"Scheduled fetching for {total_scheduled} games")
            
            # Save scheduled jobs info
            with open(self.data_dir / "scheduled_jobs.json", 'w') as f:
                json.dump(self.scheduled_jobs, f, indent=2)
            
            return total_scheduled
            
        except Exception as e:
            logger.error(f"Error setting up automated fetching: {e}")
            return 0
    
    def run_scheduler(self):
        """Run the scheduler in a separate thread"""
        logger.info("Starting automated closing lines scheduler...")
        self.fetching_active = True
        
        while self.fetching_active:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Error in scheduler: {e}")
                time.sleep(60)
    
    def start_automated_fetching(self):
        """Start the automated fetching system"""
        # Set up scheduled jobs
        scheduled_count = self.setup_automated_fetching()
        
        if scheduled_count > 0:
            # Start scheduler in background thread
            scheduler_thread = threading.Thread(target=self.run_scheduler, daemon=True)
            scheduler_thread.start()
            logger.info("Automated closing lines fetching started successfully")
            return True
        else:
            logger.warning("No games found to schedule")
            return False
    
    def stop_automated_fetching(self):
        """Stop the automated fetching system"""
        self.fetching_active = False
        schedule.clear()
        logger.info("Automated closing lines fetching stopped")
    
    def get_status(self) -> Dict:
        """Get current status of automated fetching"""
        return {
            'active': self.fetching_active,
            'scheduled_jobs': len(self.scheduled_jobs),
            'next_fetch': min([job['fetch_time'] for job in self.scheduled_jobs.values()]) if self.scheduled_jobs else None,
            'config_loaded': bool(self.config),
            'apis_configured': {
                'pinnacle': bool(self.pinnacle_username and self.pinnacle_password),
                'odds_api': bool(self.odds_api_key)
            }
        }

def main():
    """Main function for testing/running the automated fetcher"""
    fetcher = AutomatedClosingLinesFetcher()
    
    # Start automated fetching
    success = fetcher.start_automated_fetching()
    
    if success:
        print("Automated closing lines fetching started successfully!")
        print(f"Status: {fetcher.get_status()}")
        
        # Keep running
        try:
            while True:
                time.sleep(300)  # Check every 5 minutes
                logger.info(f"Fetcher status: {fetcher.get_status()}")
        except KeyboardInterrupt:
            fetcher.stop_automated_fetching()
            print("Automated fetching stopped.")
    else:
        print("Failed to start automated fetching.")

if __name__ == "__main__":
    main()
