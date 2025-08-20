#!/usr/bin/env python3

"""
MLB Team Name Normalization Utility
Provides consistent team name normalization across the entire application
"""

def normalize_team_name(team_name: str) -> str:
    """
    Normalize team names to match our internal naming convention.
    This function should be used throughout the application to ensure consistency.
    """
    if not team_name:
        return team_name
        
    # Strip whitespace and convert underscores to spaces for consistent comparison
    team_name = team_name.strip().replace('_', ' ')
    
    # Dictionary of all possible team name variations to our standard names
    # These map to the exact names used in team_assets.json
    name_mappings = {
        # Athletics variations - special case using just "Athletics"
        'Oakland Athletics': 'Athletics',
        'Oakland A\'s': 'Athletics',
        'Oakland As': 'Athletics',
        'A\'s': 'Athletics',
        'As': 'Athletics',
        'OAK': 'Athletics',
        'Athletics': 'Athletics',  # Identity mapping
        
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
    
    # If no mapping found, return the original name
    return team_name

def get_team_abbreviation(team_name: str) -> str:
    """Get the standard 3-letter abbreviation for a team"""
    # First normalize the team name
    normalized = normalize_team_name(team_name)
    
    # Mapping from normalized names to abbreviations
    abbreviations = {
        'Athletics': 'OAK',
        'Angels': 'LAA',
        'Dodgers': 'LAD',
        'Yankees': 'NYY',
        'Mets': 'NYM',
        'White Sox': 'CHW',
        'Cubs': 'CHC',
        'Cardinals': 'STL',
        'Red Sox': 'BOS',
        'Blue Jays': 'TOR',
        'Rays': 'TBR',
        'Orioles': 'BAL',
        'Guardians': 'CLE',
        'Tigers': 'DET',
        'Royals': 'KCR',
        'Twins': 'MIN',
        'Astros': 'HOU',
        'Mariners': 'SEA',
        'Rangers': 'TEX',
        'Braves': 'ATL',
        'Marlins': 'MIA',
        'Phillies': 'PHI',
        'Nationals': 'WSN',
        'Diamondbacks': 'ARI',
        'Rockies': 'COL',
        'Padres': 'SDP',
        'Giants': 'SFG',
        'Brewers': 'MIL',
        'Reds': 'CIN',
        'Pirates': 'PIT',
    }
    
    return abbreviations.get(normalized, 'UNK')

def get_standard_team_names():
    """Get a list of all standard team names used in the system (matches team_assets.json)"""
    return [
        'Athletics', 'Los Angeles Angels', 'Los Angeles Dodgers', 'New York Yankees', 
        'New York Mets', 'Chicago White Sox', 'Chicago Cubs', 'St. Louis Cardinals', 
        'Boston Red Sox', 'Toronto Blue Jays', 'Tampa Bay Rays', 'Baltimore Orioles', 
        'Cleveland Guardians', 'Detroit Tigers', 'Kansas City Royals', 'Minnesota Twins', 
        'Houston Astros', 'Seattle Mariners', 'Texas Rangers', 'Atlanta Braves',
        'Miami Marlins', 'Philadelphia Phillies', 'Washington Nationals', 'Arizona Diamondbacks', 
        'Colorado Rockies', 'San Diego Padres', 'San Francisco Giants', 'Milwaukee Brewers', 
        'Cincinnati Reds', 'Pittsburgh Pirates'
    ]

def validate_team_name(team_name: str) -> bool:
    """Check if a team name can be normalized to a valid MLB team"""
    normalized = normalize_team_name(team_name)
    return normalized in get_standard_team_names()

# Usage examples and testing
if __name__ == "__main__":
    print("=== MLB Team Name Normalization Testing ===")
    
    test_cases = [
        'Oakland Athletics',
        'Oakland A\'s',
        'OAK',
        'Athletics',
        'Los Angeles Angels',
        'Anaheim Angels',
        'LAA',
        'New York Yankees',
        'Chicago White Sox',
        'St. Louis Cardinals',
        'Tampa Bay Rays',
        'Invalid Team Name'
    ]
    
    for test_name in test_cases:
        normalized = normalize_team_name(test_name)
        abbreviation = get_team_abbreviation(test_name)
        is_valid = validate_team_name(test_name)
        print(f"{test_name:20} -> {normalized:15} ({abbreviation}) [Valid: {is_valid}]")
