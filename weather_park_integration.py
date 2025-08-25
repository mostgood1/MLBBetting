"""
Weather and Park Factors Integration for MLB Betting System
Integrates real-time weather data and ballpark characteristics to improve total runs predictions
"""

import requests
import json
import os
from datetime import datetime, date
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

class WeatherParkFactorEngine:
    """
    Integrates weather and park factors for enhanced total runs predictions
    """
    
    def __init__(self, data_dir: str = None):
        if data_dir is None:
            self.data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
        else:
            self.data_dir = data_dir
        
        # Load static park factors
        self.park_factors = self._load_park_factors()
        
        # Weather API configuration (you'll need to add your API key)
        self.weather_api_key = os.environ.get('WEATHER_API_KEY', '')
        self.weather_base_url = "http://api.openweathermap.org/data/2.5/weather"
        
    def _load_park_factors(self) -> Dict[str, Dict]:
        """Load static ballpark characteristics affecting run scoring"""
        # MLB ballpark characteristics affecting offense
        park_factors = {
            "Arizona Diamondbacks": {
                "name": "Chase Field",
                "park_factor": 1.05,  # Slight hitter-friendly
                "altitude": 1117,     # feet above sea level
                "dome": True,         # Climate controlled
                "wall_height": 7.5,   # Average outfield wall height
                "foul_territory": "medium",
                "wind_factor": 0.0,   # Indoor stadium
                "run_environment": 1.03
            },
            "Atlanta Braves": {
                "name": "Truist Park",
                "park_factor": 1.02,
                "altitude": 1050,
                "dome": False,
                "wall_height": 8.0,
                "foul_territory": "small",
                "wind_factor": 1.0,
                "run_environment": 1.01
            },
            "Baltimore Orioles": {
                "name": "Oriole Park at Camden Yards",
                "park_factor": 1.08,  # Hitter-friendly
                "altitude": 20,
                "dome": False,
                "wall_height": 7.0,   # Low left field wall
                "foul_territory": "small",
                "wind_factor": 1.0,
                "run_environment": 1.05
            },
            "Boston Red Sox": {
                "name": "Fenway Park",
                "park_factor": 1.06,  # Green Monster effect
                "altitude": 20,
                "dome": False,
                "wall_height": 37.2,  # Green Monster
                "foul_territory": "small",
                "wind_factor": 1.0,
                "run_environment": 1.04
            },
            "Chicago Cubs": {
                "name": "Wrigley Field",
                "park_factor": 1.03,  # Wind dependent
                "altitude": 595,
                "dome": False,
                "wall_height": 11.2,
                "foul_territory": "small",
                "wind_factor": 1.2,   # Very wind dependent
                "run_environment": 1.02
            },
            "Chicago White Sox": {
                "name": "Guaranteed Rate Field",
                "park_factor": 1.01,
                "altitude": 595,
                "dome": False,
                "wall_height": 8.0,
                "foul_territory": "medium",
                "wind_factor": 1.0,
                "run_environment": 1.00
            },
            "Cincinnati Reds": {
                "name": "Great American Ball Park",
                "park_factor": 1.04,
                "altitude": 550,
                "dome": False,
                "wall_height": 12.0,
                "foul_territory": "medium",
                "wind_factor": 1.0,
                "run_environment": 1.02
            },
            "Cleveland Guardians": {
                "name": "Progressive Field",
                "park_factor": 0.98,  # Pitcher-friendly
                "altitude": 650,
                "dome": False,
                "wall_height": 19.0,
                "foul_territory": "large",
                "wind_factor": 1.0,
                "run_environment": 0.98
            },
            "Colorado Rockies": {
                "name": "Coors Field",
                "park_factor": 1.15,  # Most hitter-friendly
                "altitude": 5200,     # Mile high
                "dome": False,
                "wall_height": 8.0,
                "foul_territory": "large",
                "wind_factor": 1.1,
                "run_environment": 1.12  # Thin air effect
            },
            "Detroit Tigers": {
                "name": "Comerica Park",
                "park_factor": 0.96,  # Pitcher-friendly
                "altitude": 585,
                "dome": False,
                "wall_height": 8.0,
                "foul_territory": "large",
                "wind_factor": 1.0,
                "run_environment": 0.97
            },
            "Houston Astros": {
                "name": "Minute Maid Park",
                "park_factor": 1.00,
                "altitude": 22,
                "dome": True,         # Retractable roof
                "wall_height": 21.0,  # Tal Green Monster (left)
                "foul_territory": "small",
                "wind_factor": 0.0,
                "run_environment": 1.00
            },
            "Kansas City Royals": {
                "name": "Kauffman Stadium",
                "park_factor": 0.97,
                "altitude": 750,
                "dome": False,
                "wall_height": 12.0,
                "foul_territory": "large",
                "wind_factor": 1.0,
                "run_environment": 0.98
            },
            "Los Angeles Angels": {
                "name": "Angel Stadium",
                "park_factor": 0.99,
                "altitude": 150,
                "dome": False,
                "wall_height": 8.0,
                "foul_territory": "large",
                "wind_factor": 0.8,   # Usually calm
                "run_environment": 0.99
            },
            "Los Angeles Dodgers": {
                "name": "Dodger Stadium",
                "park_factor": 0.95,  # Pitcher-friendly
                "altitude": 540,
                "dome": False,
                "wall_height": 10.0,
                "foul_territory": "large",
                "wind_factor": 0.8,
                "run_environment": 0.96
            },
            "Miami Marlins": {
                "name": "loanDepot park",
                "park_factor": 0.94,  # Very pitcher-friendly
                "altitude": 9,
                "dome": True,         # Retractable roof
                "wall_height": 12.0,
                "foul_territory": "medium",
                "wind_factor": 0.0,
                "run_environment": 0.95
            },
            "Milwaukee Brewers": {
                "name": "American Family Field",
                "park_factor": 1.01,
                "altitude": 635,
                "dome": True,         # Retractable roof
                "wall_height": 8.0,
                "foul_territory": "medium",
                "wind_factor": 0.5,
                "run_environment": 1.00
            },
            "Minnesota Twins": {
                "name": "Target Field",
                "park_factor": 1.02,
                "altitude": 815,
                "dome": False,
                "wall_height": 8.0,
                "foul_territory": "medium",
                "wind_factor": 1.0,
                "run_environment": 1.01
            },
            "New York Mets": {
                "name": "Citi Field",
                "park_factor": 0.96,  # Pitcher-friendly
                "altitude": 20,
                "dome": False,
                "wall_height": 12.0,
                "foul_territory": "large",
                "wind_factor": 1.0,
                "run_environment": 0.97
            },
            "New York Yankees": {
                "name": "Yankee Stadium",
                "park_factor": 1.07,  # Short right field porch
                "altitude": 55,
                "dome": False,
                "wall_height": 8.0,   # Short right field
                "foul_territory": "small",
                "wind_factor": 1.0,
                "run_environment": 1.05
            },
            "Oakland Athletics": {
                "name": "Oakland Coliseum",
                "park_factor": 0.93,  # Very pitcher-friendly
                "altitude": 0,
                "dome": False,
                "wall_height": 10.0,
                "foul_territory": "very_large",  # Largest in MLB
                "wind_factor": 1.1,   # Bay area winds
                "run_environment": 0.92
            },
            "Philadelphia Phillies": {
                "name": "Citizens Bank Park",
                "park_factor": 1.05,
                "altitude": 60,
                "dome": False,
                "wall_height": 13.0,
                "foul_territory": "small",
                "wind_factor": 1.0,
                "run_environment": 1.03
            },
            "Pittsburgh Pirates": {
                "name": "PNC Park",
                "park_factor": 0.98,
                "altitude": 730,
                "dome": False,
                "wall_height": 6.0,   # Low right field wall
                "foul_territory": "medium",
                "wind_factor": 1.0,
                "run_environment": 0.99
            },
            "San Diego Padres": {
                "name": "Petco Park",
                "park_factor": 0.92,  # Very pitcher-friendly
                "altitude": 62,
                "dome": False,
                "wall_height": 17.6,  # High walls
                "foul_territory": "large",
                "wind_factor": 0.9,   # Ocean breeze
                "run_environment": 0.93
            },
            "San Francisco Giants": {
                "name": "Oracle Park",
                "park_factor": 0.89,  # Most pitcher-friendly
                "altitude": 0,
                "dome": False,
                "wall_height": 25.0,  # McCovey Cove wall
                "foul_territory": "large",
                "wind_factor": 1.2,   # Very windy
                "run_environment": 0.90
            },
            "Seattle Mariners": {
                "name": "T-Mobile Park",
                "park_factor": 0.95,
                "altitude": 350,
                "dome": True,         # Retractable roof
                "wall_height": 17.0,
                "foul_territory": "large",
                "wind_factor": 0.5,
                "run_environment": 0.96
            },
            "St. Louis Cardinals": {
                "name": "Busch Stadium",
                "park_factor": 1.00,  # Neutral
                "altitude": 465,
                "dome": False,
                "wall_height": 11.0,
                "foul_territory": "medium",
                "wind_factor": 1.0,
                "run_environment": 1.00
            },
            "Tampa Bay Rays": {
                "name": "Tropicana Field",
                "park_factor": 0.96,
                "altitude": 15,
                "dome": True,         # Fixed dome
                "wall_height": 10.0,
                "foul_territory": "medium",
                "wind_factor": 0.0,
                "run_environment": 0.97
            },
            "Texas Rangers": {
                "name": "Globe Life Field",
                "park_factor": 1.08,  # New hitter-friendly park
                "altitude": 551,
                "dome": True,         # Retractable roof
                "wall_height": 8.0,
                "foul_territory": "small",
                "wind_factor": 0.0,
                "run_environment": 1.06
            },
            "Toronto Blue Jays": {
                "name": "Rogers Centre",
                "park_factor": 1.03,
                "altitude": 300,
                "dome": True,         # Retractable roof
                "wall_height": 10.0,
                "foul_territory": "medium",
                "wind_factor": 0.0,
                "run_environment": 1.02
            },
            "Washington Nationals": {
                "name": "Nationals Park",
                "park_factor": 1.02,
                "altitude": 50,
                "dome": False,
                "wall_height": 8.0,
                "foul_territory": "medium",
                "wind_factor": 1.0,
                "run_environment": 1.01
            }
        }
        
        return park_factors
    
    def get_stadium_location(self, home_team: str) -> Tuple[float, float]:
        """Get stadium coordinates for weather API calls"""
        # MLB stadium coordinates (lat, lon)
        coordinates = {
            "Arizona Diamondbacks": (33.4453, -112.0667),
            "Atlanta Braves": (33.8906, -84.4677),
            "Baltimore Orioles": (39.2840, -76.6218),
            "Boston Red Sox": (42.3467, -71.0972),
            "Chicago Cubs": (41.9484, -87.6553),
            "Chicago White Sox": (41.8300, -87.6338),
            "Cincinnati Reds": (39.0975, -84.5088),
            "Cleveland Guardians": (41.4958, -81.6852),
            "Colorado Rockies": (39.7559, -104.9942),
            "Detroit Tigers": (42.3390, -83.0485),
            "Houston Astros": (29.7570, -95.3551),
            "Kansas City Royals": (39.0517, -94.4803),
            "Los Angeles Angels": (33.8003, -117.8827),
            "Los Angeles Dodgers": (34.0739, -118.2400),
            "Miami Marlins": (25.7781, -80.2196),
            "Milwaukee Brewers": (43.0280, -87.9712),
            "Minnesota Twins": (44.9817, -93.2776),
            "New York Mets": (40.7571, -73.8458),
            "New York Yankees": (40.8296, -73.9262),
            "Oakland Athletics": (37.7516, -122.2005),
            "Philadelphia Phillies": (39.9061, -75.1665),
            "Pittsburgh Pirates": (40.4469, -80.0056),
            "San Diego Padres": (32.7073, -117.1566),
            "San Francisco Giants": (37.7786, -122.3893),
            "Seattle Mariners": (47.5914, -122.3326),
            "St. Louis Cardinals": (38.6226, -90.1928),
            "Tampa Bay Rays": (27.7682, -82.6534),
            "Texas Rangers": (32.7511, -97.0832),
            "Toronto Blue Jays": (43.6414, -79.3894),
            "Washington Nationals": (38.8730, -77.0074)
        }
        
        return coordinates.get(home_team, (39.0, -77.0))  # Default to DC area
    
    def get_current_weather(self, home_team: str, game_date: str = None) -> Dict:
        """Fetch current weather data for stadium location"""
        if not self.weather_api_key:
            logger.warning("No weather API key configured, using default conditions")
            return self._get_default_weather()
        
        try:
            lat, lon = self.get_stadium_location(home_team)
            
            # Check if it's a dome stadium first
            park_info = self.park_factors.get(home_team, {})
            if park_info.get('dome', False):
                return {
                    'temperature': 72,  # Climate controlled
                    'humidity': 45,
                    'wind_speed': 0,
                    'wind_direction': 0,
                    'conditions': 'dome',
                    'visibility': 10,
                    'pressure': 30.0
                }
            
            # Make weather API call
            params = {
                'lat': lat,
                'lon': lon,
                'appid': self.weather_api_key,
                'units': 'imperial'
            }
            
            response = requests.get(self.weather_base_url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                return {
                    'temperature': data['main']['temp'],
                    'humidity': data['main']['humidity'],
                    'wind_speed': data['wind'].get('speed', 0),
                    'wind_direction': data['wind'].get('deg', 0),
                    'conditions': data['weather'][0]['main'],
                    'visibility': data.get('visibility', 10000) / 1609.34,  # Convert to miles
                    'pressure': data['main']['pressure'] * 0.02953  # Convert to inHg
                }
            else:
                logger.warning(f"Weather API error: {response.status_code}")
                return self._get_default_weather()
                
        except Exception as e:
            logger.warning(f"Error fetching weather: {e}")
            return self._get_default_weather()
    
    def _get_default_weather(self) -> Dict:
        """Default weather conditions for fallback"""
        return {
            'temperature': 75,
            'humidity': 50,
            'wind_speed': 5,
            'wind_direction': 180,
            'conditions': 'Clear',
            'visibility': 10,
            'pressure': 30.0
        }
    
    def calculate_weather_impact(self, weather: Dict, park_info: Dict) -> float:
        """Calculate weather impact on run scoring"""
        if park_info.get('dome', False):
            return 1.0  # No weather impact in domes
        
        impact = 1.0
        
        # Temperature impact (optimal range: 70-85°F)
        temp = weather.get('temperature', 75)
        if temp < 50:
            impact *= 0.90  # Cold weather reduces offense
        elif temp > 95:
            impact *= 0.95  # Very hot weather slightly reduces offense
        elif 75 <= temp <= 85:
            impact *= 1.05  # Ideal hitting weather
        
        # Wind impact
        wind_speed = weather.get('wind_speed', 0)
        wind_direction = weather.get('wind_direction', 180)
        park_wind_factor = park_info.get('wind_factor', 1.0)
        
        # Wind speed impact
        if wind_speed > 15:  # Strong wind
            if 45 <= wind_direction <= 135 or 225 <= wind_direction <= 315:
                # Crosswind - less impact
                impact *= (0.98 * park_wind_factor)
            elif 135 < wind_direction < 225:
                # Headwind - reduces offense
                impact *= (0.92 * park_wind_factor)
            else:
                # Tailwind - increases offense
                impact *= (1.08 * park_wind_factor)
        elif wind_speed > 8:  # Moderate wind
            if 135 < wind_direction < 225:
                impact *= (0.96 * park_wind_factor)
            elif wind_direction <= 45 or wind_direction >= 315:
                impact *= (1.04 * park_wind_factor)
        
        # Humidity impact (high humidity reduces ball travel)
        humidity = weather.get('humidity', 50)
        if humidity > 80:
            impact *= 0.97
        elif humidity < 30:
            impact *= 1.02
        
        # Pressure impact (low pressure helps ball travel)
        pressure = weather.get('pressure', 30.0)
        if pressure < 29.5:
            impact *= 1.03  # Low pressure - ball travels farther
        elif pressure > 30.5:
            impact *= 0.98  # High pressure - ball doesn't travel as far
        
        # Weather conditions impact
        conditions = weather.get('conditions', 'Clear').lower()
        if 'rain' in conditions:
            impact *= 0.85  # Rain significantly reduces offense
        elif 'snow' in conditions:
            impact *= 0.80  # Snow drastically reduces offense
        elif 'fog' in conditions:
            impact *= 0.92  # Fog reduces visibility
        
        return max(0.75, min(1.25, impact))  # Bound the impact
    
    def get_total_park_weather_factor(self, home_team: str, game_date: str = None) -> Dict:
        """Get combined park and weather factor for run scoring"""
        park_info = self.park_factors.get(home_team, {})
        weather = self.get_current_weather(home_team, game_date)
        
        # Base park factor
        base_park_factor = park_info.get('run_environment', 1.0)
        
        # Weather impact
        weather_impact = self.calculate_weather_impact(weather, park_info)
        
        # Combined factor
        total_factor = base_park_factor * weather_impact
        
        return {
            'total_factor': total_factor,
            'park_factor': base_park_factor,
            'weather_factor': weather_impact,
            'park_info': park_info,
            'weather': weather,
            'stadium_name': park_info.get('name', 'Unknown Stadium')
        }
    
    def save_daily_park_weather_data(self, date_str: str = None) -> str:
        """Save park and weather data for all teams for a given date"""
        if date_str is None:
            date_str = datetime.now().strftime('%Y-%m-%d')
        
        all_teams = list(self.park_factors.keys())
        daily_data = {
            'date': date_str,
            'updated_at': datetime.now().isoformat(),
            'teams': {}
        }
        
        for team in all_teams:
            try:
                factor_data = self.get_total_park_weather_factor(team, date_str)
                daily_data['teams'][team] = factor_data
                print(f"✅ {team}: Park={factor_data['park_factor']:.3f}, Weather={factor_data['weather_factor']:.3f}, Total={factor_data['total_factor']:.3f}")
            except Exception as e:
                print(f"❌ Error processing {team}: {e}")
                # Use park factor only as fallback
                park_info = self.park_factors.get(team, {})
                daily_data['teams'][team] = {
                    'total_factor': park_info.get('run_environment', 1.0),
                    'park_factor': park_info.get('run_environment', 1.0),
                    'weather_factor': 1.0,
                    'error': str(e)
                }
        
        # Save to file
        filename = f"park_weather_factors_{date_str.replace('-', '_')}.json"
        filepath = os.path.join(self.data_dir, filename)
        
        with open(filepath, 'w') as f:
            json.dump(daily_data, f, indent=2)
        
        print(f"\n📊 Park and weather factors saved to: {filepath}")
        return filepath

def main():
    """Test the weather and park factors system"""
    print("🌤️ MLB Weather and Park Factors Integration Test")
    print("=" * 60)
    
    engine = WeatherParkFactorEngine()
    
    # Test a few teams
    test_teams = [
        "Colorado Rockies",      # High altitude
        "San Francisco Giants",  # Windy
        "Houston Astros",       # Dome
        "Boston Red Sox",       # Green Monster
        "Oakland Athletics"     # Pitcher-friendly
    ]
    
    print("🏟️ Individual Team Analysis:")
    for team in test_teams:
        factor_data = engine.get_total_park_weather_factor(team)
        print(f"\n{team}:")
        print(f"  Stadium: {factor_data['stadium_name']}")
        print(f"  Park Factor: {factor_data['park_factor']:.3f}")
        print(f"  Weather Factor: {factor_data['weather_factor']:.3f}")
        print(f"  Total Factor: {factor_data['total_factor']:.3f}")
        
        weather = factor_data['weather']
        print(f"  Weather: {weather['temperature']}°F, {weather['conditions']}, Wind: {weather['wind_speed']} mph")
    
    print(f"\n📅 Generating daily data for all teams...")
    filepath = engine.save_daily_park_weather_data()
    print(f"✅ Complete! Data saved to: {filepath}")

if __name__ == "__main__":
    main()
