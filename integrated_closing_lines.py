"""
Integrated Closing Lines Manager for MLB-Betting App
Connects OddsAPI closing lines with historical, today's, and future data
"""

import json
import logging
import requests
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import os
from dotenv import load_dotenv

class IntegratedClosingLinesManager:
    """
    Integrated manager for closing lines across historical, current, and future games
    """
    
    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.data_dir = self.base_dir / "data"

        # Set up logging early so other methods can use self.logger
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

        # Load environment variables from .env if present
        try:
            load_dotenv()
        except Exception as e:
            self.logger.debug(f"dotenv load skipped/failed: {e}")
        # Load configuration
        self.config = self.load_config()
        # Prefer config key, but allow environment to override for quick ops
        cfg_key = ''
        if isinstance(self.config, dict):
            api_keys = self.config.get('api_keys', {}) or {}
            # Prefer odds_api_key, but allow the_odds_api_key as an alias
            cfg_key = api_keys.get('odds_api_key') or api_keys.get('the_odds_api_key') or ''
        # Environment overrides: support multiple names
        env_key = os.getenv('ODDS_API_KEY') or os.getenv('THE_ODDS_API_KEY') or os.getenv('ODDSAPI_KEY') or ''
        # If an env key is provided, it takes precedence
        self.odds_api_key = (env_key or cfg_key)

        # File paths
        self.master_closing_lines_file = self.data_dir / "master_closing_lines.json"
        self.master_games_file = self.data_dir / "master_games.json"

        # Load existing data
        self.closing_lines_data = self.load_closing_lines_data()
        self.games_data = self.load_games_data()

        # Log a short preview and whether env override was used (without leaking secret)
        key_preview = (self.odds_api_key[:8] + '...' + self.odds_api_key[-4:]) if len(self.odds_api_key) > 12 else 'Short'
        src = 'ENV' if env_key else 'CONFIG'
        self.logger.info(
            f"Initialized with OddsAPI key: {key_preview} (source={src})"
        )
    
    def load_config(self) -> Dict:
        """Load configuration with API keys"""
        config_file = self.data_dir / "closing_lines_config.json"
        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            self.logger.warning(f"Could not load config: {e}")
            return {}
    
    def load_closing_lines_data(self) -> Dict:
        """Load existing closing lines data"""
        try:
            if self.master_closing_lines_file.exists():
                with open(self.master_closing_lines_file, 'r') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            self.logger.error(f"Error loading closing lines data: {e}")
            return {}
    
    def load_games_data(self) -> Dict:
        """Load master games data"""
        try:
            if self.master_games_file.exists():
                with open(self.master_games_file, 'r') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            self.logger.error(f"Error loading games data: {e}")
            return {}
    
    def save_closing_lines_data(self):
        """Save closing lines data to file"""
        try:
            with open(self.master_closing_lines_file, 'w') as f:
                json.dump(self.closing_lines_data, f, indent=2)
            self.logger.info("Closing lines data saved successfully")
        except Exception as e:
            self.logger.error(f"Error saving closing lines data: {e}")
    
    def fetch_live_odds(self, date: str) -> List[Dict]:
        """Fetch live odds from OddsAPI for a specific date"""
        if not self.odds_api_key:
            self.logger.warning("No OddsAPI key configured")
            return []
        
        try:
            url = "https://api.the-odds-api.com/v4/sports/baseball_mlb/odds"
            
            params = {
                'apiKey': self.odds_api_key,
                'regions': 'us',
                'markets': 'h2h,spreads,totals',
                'oddsFormat': 'american',
                'bookmakers': 'pinnacle,draftkings,fanduel,betmgm,caesars'
            }
            
            response = requests.get(url, params=params, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                self.logger.info(f"Successfully fetched {len(data)} games from OddsAPI")
                return data
            elif response.status_code == 401:
                self.logger.error("Invalid OddsAPI key")
                return []
            else:
                self.logger.warning(f"OddsAPI error {response.status_code}: {response.text}")
                return []
                
        except Exception as e:
            self.logger.error(f"Error fetching from OddsAPI: {e}")
            return []
    
    def parse_odds_data(self, odds_data: List[Dict], date: str) -> List[Dict]:
        """Parse OddsAPI response into closing lines format"""
        parsed_lines = []
        
        for event in odds_data:
            try:
                away_team = event.get('away_team', '')
                home_team = event.get('home_team', '')
                
                # Find DraftKings odds specifically
                draftkings_odds = self.extract_draftkings_odds(event.get('bookmakers', []), away_team, home_team)
                
                closing_line = {
                    'game_id': f"{away_team}_{home_team}_{date}".replace(' ', '_'),
                    'date': date,
                    'away_team': away_team,
                    'home_team': home_team,
                    'game_time': event.get('commence_time', ''),
                    'fetch_time': datetime.now(timezone.utc).isoformat(),
                    'source': 'OddsAPI_Live',
                    'bookmakers_count': len(event.get('bookmakers', [])),
                    'line_type': self.determine_line_type(event.get('commence_time', '')),
                    **draftkings_odds
                }
                
                parsed_lines.append(closing_line)
                
            except Exception as e:
                self.logger.error(f"Error parsing odds for event: {e}")
                continue
        
        return parsed_lines
    
    def extract_best_odds_from_bookmakers(self, bookmakers: List[Dict]) -> Dict:
        """Extract best odds across all bookmakers"""
        best_odds = {
            'moneyline': {'away': None, 'home': None},
            'spread': {'line': None, 'away': None, 'home': None},
            'total': {'line': None, 'over': None, 'under': None}
        }
        
        # Collect all odds
        all_moneyline = {'away': [], 'home': []}
        all_spreads = []
        all_totals = []
        
        for bookmaker in bookmakers:
            book_name = bookmaker.get('key', '')
            
            for market in bookmaker.get('markets', []):
                market_key = market.get('key', '')
                outcomes = market.get('outcomes', [])
                
                if market_key == 'h2h' and len(outcomes) >= 2:
                    # Moneyline
                    for i, outcome in enumerate(outcomes):
                        price = outcome.get('price')
                        if price:
                            if i == 0:  # First is typically away
                                all_moneyline['away'].append(price)
                            else:  # Second is typically home
                                all_moneyline['home'].append(price)
                
                elif market_key == 'spreads' and len(outcomes) >= 2:
                    # Spread
                    for outcome in outcomes:
                        price = outcome.get('price')
                        point = outcome.get('point')
                        name = outcome.get('name', '')
                        if price and point is not None:
                            all_spreads.append({
                                'name': name,
                                'point': point,
                                'price': price
                            })
                
                elif market_key == 'totals' and len(outcomes) >= 2:
                    # Total
                    for outcome in outcomes:
                        price = outcome.get('price')
                        point = outcome.get('point')
                        name = outcome.get('name', '')
                        if price and point is not None:
                            all_totals.append({
                                'name': name,
                                'point': point,
                                'price': price
                            })
        
        # Select best odds
        if all_moneyline['away']:
            best_odds['moneyline']['away'] = max(all_moneyline['away'])
        if all_moneyline['home']:
            best_odds['moneyline']['home'] = max(all_moneyline['home'])
        
        # For spreads, find most common line and best odds
        if all_spreads:
            # Group by point spread
            spread_groups = {}
            for spread in all_spreads:
                point = spread['point']
                if point not in spread_groups:
                    spread_groups[point] = {'away': [], 'home': []}
                
                if spread['point'] > 0:  # Away team getting points
                    spread_groups[point]['away'].append(spread['price'])
                else:  # Home team getting points
                    spread_groups[point]['home'].append(spread['price'])
            
            # Find most common spread
            if spread_groups:
                most_common_spread = max(spread_groups.keys(), key=lambda x: len(spread_groups[x]['away']) + len(spread_groups[x]['home']))
                best_odds['spread']['line'] = most_common_spread
                
                if spread_groups[most_common_spread]['away']:
                    best_odds['spread']['away'] = max(spread_groups[most_common_spread]['away'])
                if spread_groups[most_common_spread]['home']:
                    best_odds['spread']['home'] = max(spread_groups[most_common_spread]['home'])
        
        # For totals, find most common line and best odds
        if all_totals:
            # Group by total line
            total_groups = {}
            for total in all_totals:
                point = total['point']
                if point not in total_groups:
                    total_groups[point] = {'over': [], 'under': []}
                
                if total['name'].lower() == 'over':
                    total_groups[point]['over'].append(total['price'])
                else:
                    total_groups[point]['under'].append(total['price'])
            
            # Find most common total
            if total_groups:
                most_common_total = max(total_groups.keys(), key=lambda x: len(total_groups[x]['over']) + len(total_groups[x]['under']))
                best_odds['total']['line'] = most_common_total
                
                if total_groups[most_common_total]['over']:
                    best_odds['total']['over'] = max(total_groups[most_common_total]['over'])
                if total_groups[most_common_total]['under']:
                    best_odds['total']['under'] = max(total_groups[most_common_total]['under'])
        
        return best_odds
    
    def determine_line_type(self, game_time_str: str) -> str:
        """Determine line type based on timing"""
        try:
            if game_time_str:
                game_time = datetime.fromisoformat(game_time_str.replace('Z', '+00:00'))
                current_time = datetime.now(timezone.utc)
                minutes_before = (game_time - current_time).total_seconds() / 60
                
                if minutes_before <= 30:
                    return 'closing'
                elif minutes_before <= 120:
                    return 'late_pregame'
                else:
                    return 'early_pregame'
            return 'unknown_timing'
        except:
            return 'unknown_timing'
    
    def extract_draftkings_odds(self, bookmakers: List[Dict], away_team: str, home_team: str) -> Dict:
        """Extract DraftKings specific odds"""
        draftkings_odds = {
            'moneyline': {'away': None, 'home': None},
            'spread': {'line': None, 'away': None, 'home': None},
            'total': {'line': None, 'over': None, 'under': None}
        }
        
        # Find DraftKings bookmaker
        draftkings_book = None
        for bookmaker in bookmakers:
            if bookmaker.get('key', '').lower() == 'draftkings':
                draftkings_book = bookmaker
                break
        
        if not draftkings_book:
            # If no DraftKings data, fall back to best odds
            return self.extract_best_odds_from_bookmakers(bookmakers)
        
        for market in draftkings_book.get('markets', []):
            market_key = market.get('key', '')
            outcomes = market.get('outcomes', [])
            
            if market_key == 'h2h' and len(outcomes) >= 2:
                # Moneyline - match by team name instead of position
                for outcome in outcomes:
                    price = outcome.get('price')
                    team_name = outcome.get('name', '')
                    if price and team_name:
                        if team_name == away_team:
                            draftkings_odds['moneyline']['away'] = price
                        elif team_name == home_team:
                            draftkings_odds['moneyline']['home'] = price
            
            elif market_key == 'spreads' and len(outcomes) >= 2:
                # Spread - match by team name
                for outcome in outcomes:
                    price = outcome.get('price')
                    point = outcome.get('point')
                    team_name = outcome.get('name', '')
                    if price and point is not None and team_name:
                        if team_name == away_team:
                            draftkings_odds['spread']['line'] = abs(point)
                            draftkings_odds['spread']['away'] = price
                        elif team_name == home_team:
                            draftkings_odds['spread']['line'] = abs(point)
                            draftkings_odds['spread']['home'] = price
            
            elif market_key == 'totals' and len(outcomes) >= 2:
                # Total
                for outcome in outcomes:
                    price = outcome.get('price')
                    point = outcome.get('point')
                    name = outcome.get('name', '')
                    if price and point is not None:
                        draftkings_odds['total']['line'] = point
                        if name.lower() == 'over':
                            draftkings_odds['total']['over'] = price
                        else:
                            draftkings_odds['total']['under'] = price
        
        return draftkings_odds
    
    def get_closing_lines_for_date(self, date: str) -> Dict:
        """Get closing lines for a specific date (historical, today, or future)"""
        # Check if we already have data for this date
        if date in self.closing_lines_data:
            existing_data = self.closing_lines_data[date]
            self.logger.info(f"Found existing closing lines for {date}: {len(existing_data.get('games', []))} games")
            return existing_data
        
        # Check if this is today or future date
        today = datetime.now().strftime('%Y-%m-%d')
        
        if date >= today:
            # Try to fetch live data
            self.logger.info(f"Fetching live closing lines for {date}")
            live_odds = self.fetch_live_odds(date)
            
            if live_odds:
                parsed_lines = self.parse_odds_data(live_odds, date)
                
                # Save to our data
                self.closing_lines_data[date] = {
                    'date': date,
                    'games': parsed_lines,
                    'last_updated': datetime.now(timezone.utc).isoformat(),
                    'source': 'OddsAPI_Live'
                }
                
                self.save_closing_lines_data()
                self.logger.info(f"Saved {len(parsed_lines)} closing lines for {date}")
                
                return self.closing_lines_data[date]
        
        # If no live data available, return empty structure
        return {
            'date': date,
            'games': [],
            'last_updated': datetime.now(timezone.utc).isoformat(),
            'source': 'No_Data_Available'
        }
    
    def get_historical_closing_lines(self, start_date: str, end_date: str) -> Dict:
        """Get closing lines for a date range"""
        historical_data = {}
        
        current_date = datetime.strptime(start_date, '%Y-%m-%d')
        end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
        
        while current_date <= end_date_obj:
            date_str = current_date.strftime('%Y-%m-%d')
            historical_data[date_str] = self.get_closing_lines_for_date(date_str)
            current_date += timedelta(days=1)
        
        return historical_data
    
    def get_games_with_closing_lines(self, date: str) -> List[Dict]:
        """Get games for a date with their closing lines integrated"""
        games_with_lines = []
        
        # First, try to load enhanced game data from saved file
        enhanced_data_file = os.path.join(self.base_dir, 'data', 'todays_complete_games.json')
        fresh_games = []
        
        if os.path.exists(enhanced_data_file):
            try:
                with open(enhanced_data_file, 'r') as f:
                    enhanced_data = json.load(f)
                    if enhanced_data.get('date') == date:
                        fresh_games = enhanced_data.get('games', [])
                        print(f"✅ Using enhanced game data with {len(fresh_games)} games for {date}")
                    else:
                        print(f"⚠️ Enhanced data is for {enhanced_data.get('date')}, need {date}")
            except Exception as e:
                print(f"⚠️ Could not load enhanced game data: {e}")
        
        # If we have fresh enhanced data, use it; otherwise fallback to cached data
        if fresh_games:
            date_games = fresh_games
        else:
            # Fallback to cached data
            date_games = self.games_data.get(date, {}).get('games', [])
            print(f"⚠️ Using cached data for {date}")
        
        # If still no games data, try to get from closing lines data directly
        if not date_games:
            closing_lines_data = self.get_closing_lines_for_date(date)
            date_games = closing_lines_data.get('games', [])
        
        # Get closing lines for this date
        closing_lines_data = self.get_closing_lines_for_date(date)
        closing_lines = {
            line['game_id']: line 
            for line in closing_lines_data.get('games', [])
        }
        
        for game in date_games:
            # Create game ID that matches closing lines format
            away_team = game.get('away_team', '')
            home_team = game.get('home_team', '')
            game_id = f"{away_team}_{home_team}_{date}".replace(' ', '_')
            
            # Get closing lines data for this game
            game_closing_lines = closing_lines.get(game_id, None)
            
            # If game_closing_lines is None, try the game data itself (it might already contain closing lines)
            if game_closing_lines is None and 'closing_lines' in game:
                game_closing_lines = game['closing_lines']
            
            # Combine game data with closing lines
            combined_game = {
                **game,
                'game_id': game_id,
                'closing_lines': game_closing_lines,
                'has_closing_lines': game_closing_lines is not None
            }
            
            games_with_lines.append(combined_game)
        
        return games_with_lines
    
    def refresh_todays_closing_lines(self) -> Dict:
        """Refresh today's closing lines from live API"""
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Force refresh by removing existing data
        if today in self.closing_lines_data:
            del self.closing_lines_data[today]
        
        # Fetch fresh data
        return self.get_closing_lines_for_date(today)
    
    def get_status(self) -> Dict:
        """Get status of the closing lines system"""
        total_dates = len(self.closing_lines_data)
        total_games = sum(len(date_data.get('games', [])) for date_data in self.closing_lines_data.values())
        
        # Find date ranges
        dates = list(self.closing_lines_data.keys())
        dates.sort()
        
        status = {
            'total_dates': total_dates,
            'total_games': total_games,
            'date_range': {
                'earliest': dates[0] if dates else None,
                'latest': dates[-1] if dates else None
            },
            'api_key_configured': bool(self.odds_api_key),
            'api_key_preview': f"{self.odds_api_key[:8]}...{self.odds_api_key[-4:]}" if len(self.odds_api_key) > 12 else "Short key",
            'data_sources': list(set(
                date_data.get('source', 'Unknown') 
                for date_data in self.closing_lines_data.values()
            ))
        }
        
        return status

def main():
    """Test the integrated closing lines manager"""
    print("=== Testing Integrated Closing Lines Manager ===\n")
    
    manager = IntegratedClosingLinesManager()
    
    # Test status
    status = manager.get_status()
    print("📊 System Status:")
    for key, value in status.items():
        print(f"  {key}: {value}")
    
    # Test today's data
    today = datetime.now().strftime('%Y-%m-%d')
    print(f"\n🎯 Testing Today's Data ({today}):")
    
    todays_lines = manager.get_closing_lines_for_date(today)
    print(f"  Found {len(todays_lines.get('games', []))} games with closing lines")
    
    # Test games with closing lines integration
    print(f"\n🎮 Testing Games Integration:")
    games_with_lines = manager.get_games_with_closing_lines(today)
    print(f"  Found {len(games_with_lines)} total games")
    
    games_with_closing_lines = [g for g in games_with_lines if g['has_closing_lines']]
    print(f"  {len(games_with_closing_lines)} games have closing lines")
    
    if games_with_closing_lines:
        sample_game = games_with_closing_lines[0]
        print(f"  Sample: {sample_game['away_team']} @ {sample_game['home_team']}")
        if sample_game['closing_lines']:
            ml = sample_game['closing_lines'].get('moneyline', {})
            print(f"    Moneyline: Away {ml.get('away')}, Home {ml.get('home')}")

if __name__ == "__main__":
    main()
