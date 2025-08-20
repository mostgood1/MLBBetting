#!/usr/bin/env python3

"""
MLB Team Logo and Color Utilities
Provides team logo URLs, colors, and styling functions for the web interface
"""

import json
import os
from typing import Dict, Optional, Any

def normalize_team_name(team_name: str) -> str:
    """
    Normalize team names to match our team_assets.json naming convention.
    This ensures consistent team name handling across the application.
    """
    if not team_name:
        return team_name
        
    # Strip whitespace and handle basic cleanup
    team_name = team_name.strip()
    
    # Dictionary mapping variations to the exact names used in team_assets.json
    name_mappings = {
        # Athletics variations - special case using just "Athletics"
        'Oakland Athletics': 'Athletics',
        'Oakland A\'s': 'Athletics',
        'Oakland As': 'Athletics',
        'A\'s': 'Athletics',
        'As': 'Athletics',
        'OAK': 'Athletics',
        
        # Angels variations - use full "Los Angeles Angels"
        'Angels': 'Los Angeles Angels',
        'Anaheim Angels': 'Los Angeles Angels',
        'California Angels': 'Los Angeles Angels',
        'LAA': 'Los Angeles Angels',
        'ANA': 'Los Angeles Angels',
        'Los Angeles Angels of Anaheim': 'Los Angeles Angels',
        
        # Dodgers variations - use full "Los Angeles Dodgers"
        'Dodgers': 'Los Angeles Dodgers',
        'LA Dodgers': 'Los Angeles Dodgers',
        'LAD': 'Los Angeles Dodgers',
        
        # Yankees variations - use full "New York Yankees"
        'Yankees': 'New York Yankees',
        'NY Yankees': 'New York Yankees',
        'NYY': 'New York Yankees',
        
        # Mets variations - use full "New York Mets"
        'Mets': 'New York Mets',
        'NY Mets': 'New York Mets',
        'NYM': 'New York Mets',
        
        # White Sox variations - use full "Chicago White Sox"
        'White Sox': 'Chicago White Sox',
        'CHW': 'Chicago White Sox',
        'CWS': 'Chicago White Sox',
        
        # Cubs variations - use full "Chicago Cubs"
        'Cubs': 'Chicago Cubs',
        'CHC': 'Chicago Cubs',
        
        # Cardinals variations - use full "St. Louis Cardinals"
        'Cardinals': 'St. Louis Cardinals',
        'Saint Louis Cardinals': 'St. Louis Cardinals',
        'St Louis Cardinals': 'St. Louis Cardinals',
        'STL': 'St. Louis Cardinals',
        
        # Red Sox variations - use full "Boston Red Sox"
        'Red Sox': 'Boston Red Sox',
        'BOS': 'Boston Red Sox',
        
        # Blue Jays variations - use full "Toronto Blue Jays"
        'Blue Jays': 'Toronto Blue Jays',
        'TOR': 'Toronto Blue Jays',
        'TBJ': 'Toronto Blue Jays',
        
        # Rays variations - use full "Tampa Bay Rays"
        'Rays': 'Tampa Bay Rays',
        'Tampa Bay Devil Rays': 'Tampa Bay Rays',
        'TB': 'Tampa Bay Rays',
        'TBR': 'Tampa Bay Rays',
        
        # Orioles variations - use full "Baltimore Orioles"
        'Orioles': 'Baltimore Orioles',
        'BAL': 'Baltimore Orioles',
        
        # Guardians variations - use full "Cleveland Guardians"
        'Guardians': 'Cleveland Guardians',
        'Cleveland Indians': 'Cleveland Guardians',  # Legacy name
        'CLE': 'Cleveland Guardians',
        'CLG': 'Cleveland Guardians',
        
        # Tigers variations - use full "Detroit Tigers"
        'Tigers': 'Detroit Tigers',
        'DET': 'Detroit Tigers',
        
        # Royals variations - use full "Kansas City Royals"
        'Royals': 'Kansas City Royals',
        'KC': 'Kansas City Royals',
        'KCR': 'Kansas City Royals',
        
        # Twins variations - use full "Minnesota Twins"
        'Twins': 'Minnesota Twins',
        'MIN': 'Minnesota Twins',
        
        # Astros variations - use full "Houston Astros"
        'Astros': 'Houston Astros',
        'HOU': 'Houston Astros',
        
        # Mariners variations - use full "Seattle Mariners"
        'Mariners': 'Seattle Mariners',
        'SEA': 'Seattle Mariners',
        
        # Rangers variations - use full "Texas Rangers"
        'Rangers': 'Texas Rangers',
        'TEX': 'Texas Rangers',
        
        # Braves variations - use full "Atlanta Braves"
        'Braves': 'Atlanta Braves',
        'ATL': 'Atlanta Braves',
        
        # Marlins variations - use full "Miami Marlins"
        'Marlins': 'Miami Marlins',
        'Florida Marlins': 'Miami Marlins',  # Legacy name
        'MIA': 'Miami Marlins',
        'FLA': 'Miami Marlins',
        
        # Phillies variations - use full "Philadelphia Phillies"
        'Phillies': 'Philadelphia Phillies',
        'PHI': 'Philadelphia Phillies',
        
        # Nationals variations - use full "Washington Nationals"
        'Nationals': 'Washington Nationals',
        'WAS': 'Washington Nationals',
        'WSN': 'Washington Nationals',
        
        # Diamondbacks variations - use full "Arizona Diamondbacks"
        'Diamondbacks': 'Arizona Diamondbacks',
        'ARI': 'Arizona Diamondbacks',
        'AZ': 'Arizona Diamondbacks',
        
        # Rockies variations - use full "Colorado Rockies"
        'Rockies': 'Colorado Rockies',
        'COL': 'Colorado Rockies',
        
        # Padres variations - use full "San Diego Padres"
        'Padres': 'San Diego Padres',
        'SD': 'San Diego Padres',
        'SDP': 'San Diego Padres',
        
        # Giants variations - use full "San Francisco Giants"
        'Giants': 'San Francisco Giants',
        'SF': 'San Francisco Giants',
        'SFG': 'San Francisco Giants',
        
        # Brewers variations - use full "Milwaukee Brewers"
        'Brewers': 'Milwaukee Brewers',
        'MIL': 'Milwaukee Brewers',
        
        # Reds variations - use full "Cincinnati Reds"
        'Reds': 'Cincinnati Reds',
        'CIN': 'Cincinnati Reds',
        
        # Pirates variations - use full "Pittsburgh Pirates"
        'Pirates': 'Pittsburgh Pirates',
        'PIT': 'Pittsburgh Pirates',
    }
    
    # Check for exact match first (case-sensitive)
    if team_name in name_mappings:
        return name_mappings[team_name]
    
    # Check for case-insensitive match
    for variant, standard in name_mappings.items():
        if team_name.lower() == variant.lower():
            return standard
    
    # If no mapping found, return the original name (might already be correct)
    return team_name

# Define the team assets manager class inline to avoid circular imports
class MLBTeamAssets:
    """Team assets manager singleton for MLB logos and colors"""
    
    def __init__(self):
        """Initialize the team assets manager"""
        self._assets = {}
        self._load_assets()
    
    def _load_assets(self):
        """Load team assets from JSON files"""
        # Look for team assets only within the MLB-Betting directory
        asset_path = os.path.join(os.path.dirname(__file__), 'data', 'team_assets.json')
        
        if os.path.exists(asset_path):
            try:
                with open(asset_path, 'r', encoding='utf-8') as f:
                    self._assets = json.load(f)
                print(f"✓ Team assets loaded from {asset_path}")
            except Exception as e:
                print(f"❌ Error loading team assets from {asset_path}: {e}")
                self._assets = {}
        else:
            print(f"❌ Team assets file not found: {asset_path}")
            self._assets = {}
    
    def get_team_assets(self, team_name: str) -> Dict[str, Any]:
        """Get the assets for a specific team"""
        # Normalize team name first using the global function
        normalized_name = normalize_team_name(team_name)
        
        # Try to find the team by exact name
        if normalized_name in self._assets:
            return self._assets[normalized_name]
        
        # Try to find the team by case-insensitive match
        for name, assets in self._assets.items():
            if name.lower() == normalized_name.lower():
                return assets
        
        # Try to find the team by abbreviation
        for name, assets in self._assets.items():
            if assets.get('abbreviation', '').lower() == normalized_name.lower():
                return assets
        
        # If no match found, return None
        return None
    
    def get_all_team_assets(self) -> Dict[str, Dict[str, Any]]:
        """Get all team assets"""
        return self._assets

# Initialize the team assets manager as a singleton
_team_assets_manager = MLBTeamAssets()

def load_team_assets() -> Dict[str, Any]:
    """Load team assets from the manager"""
    return _team_assets_manager.get_all_team_assets()

def get_team_assets(team_name: str) -> Dict[str, Any]:
    """Get team assets (logo, colors) for a given team name"""
    if not team_name:
        return get_default_team_assets()
    
    # Use the team assets manager to get the team's assets
    team_assets = _team_assets_manager.get_team_assets(team_name)
    
    # If the team assets manager found a match, return it
    if team_assets:
        # Make sure it has all the required keys with default fallbacks
        if 'logo_url' not in team_assets and 'logo' in team_assets:
            team_assets['logo_url'] = team_assets['logo']
            
        if 'primary_color' not in team_assets and 'colors' in team_assets:
            team_assets['primary_color'] = team_assets['colors'].get('primary', '#333333')
            
        if 'secondary_color' not in team_assets and 'colors' in team_assets:
            team_assets['secondary_color'] = team_assets['colors'].get('secondary', '#666666')
            
        if 'text_color' not in team_assets:
            team_assets['text_color'] = '#FFFFFF'
            
        if 'bg_color' not in team_assets:
            team_assets['bg_color'] = team_assets.get('primary_color', '#333333')
            
        return team_assets
            
    # Return default if no match found
    print(f"⚠ Team assets not found for: {team_name}")
    return get_default_team_assets(team_name)

def get_default_team_assets(team_name: str = "Unknown") -> Dict[str, Any]:
    """Get default team assets for when a team is not found"""
    return {
        'name': team_name,
        'logo': '/static/default_team_logo.png',
        'logo_url': '/static/default_team_logo.png',
        'primary_color': '#333333',
        'secondary_color': '#666666',
        'text_color': '#FFFFFF',
        'bg_color': '#333333'
    }

def get_team_logo(team_name: str) -> str:
    """Get just the team logo URL for a team"""
    assets = get_team_assets(team_name)
    return assets.get('logo_url', '/static/default_team_logo.png')

def get_team_primary_color(team_name: str) -> str:
    """Get just the primary color for a team"""
    assets = get_team_assets(team_name)
    return assets.get('primary_color', '#333333')

def get_team_secondary_color(team_name: str) -> str:
    """Get just the secondary color for a team"""
    assets = get_team_assets(team_name)
    return assets.get('secondary_color', '#666666')

def get_team_css(team_name: str) -> str:
    """Get CSS styling for a team"""
    assets = get_team_assets(team_name)
    primary = assets.get('primary_color', '#333333')
    secondary = assets.get('secondary_color', '#666666')
    text = assets.get('text_color', '#FFFFFF')
    
    return f"background-color: {primary}; color: {text}; border-color: {secondary};"

def get_team_card_html(team: str, include_logo: bool = True) -> str:
    """Generate HTML for a team card with logo and styling"""
    try:
        assets = get_team_assets(team)
        logo = assets.get('logo_url', '')
        name = assets.get('name', team)
        style = get_team_css(team)
        
        if include_logo and logo:
            logo_html = f'<img src="{logo}" alt="{name}" class="team-logo" />'
        else:
            logo_html = ''
            
        return f'<div class="team-card" style="{style}">{logo_html}<span>{name}</span></div>'
    except Exception as e:
        print(f"Error generating team card: {str(e)}")
        return f'<div class="team-card default">{team}</div>'

def get_teams_comparison_html(away_team: str, home_team: str) -> str:
    """Generate HTML for a teams comparison (away @ home)"""
    away_card = get_team_card_html(away_team)
    home_card = get_team_card_html(home_team)
    
    return f'<div class="game-matchup">{away_card}<span class="at-symbol">@</span>{home_card}</div>'
