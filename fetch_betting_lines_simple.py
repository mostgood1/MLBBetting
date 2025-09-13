#!/usr/bin/env python3
"""
Simple Betting Lines Fetcher
Creates real_betting_lines_[date].json for today's games
"""

import json
import logging
from datetime import datetime
from pathlib import Path
import sys

def create_sample_betting_lines():
    """Create sample betting lines based on today's games"""
    today = datetime.now().strftime('%Y-%m-%d')
    today_underscore = today.replace('-', '_')
    
    # Load today's games
    games_file = Path(f"data/games_{today}.json")
    if not games_file.exists():
        print(f"ERROR: Games file not found: {games_file}")
        return False
    
    try:
        with open(games_file, 'r') as f:
            games_data = json.load(f)

        # Create sample betting lines structure
        lines = {}

        for game in games_data:
            away_team = game.get('away_team', '')
            home_team = game.get('home_team', '')
            matchup_key = f"{away_team} @ {home_team}"

            # Create sample lines (in production, these would come from real API)
            lines[matchup_key] = {
                "moneyline": {"away": -110, "home": -110},
                "total_runs": {"line": 8.5, "over": -110, "under": -110},
                "run_line": {"away": "-1.5 (+130)", "home": "+1.5 (-150)"}
            }

        # Save to file
        output_file = Path(f"data/real_betting_lines_{today_underscore}.json")

        output_data = {
            "lines": lines,
            "metadata": {
                "date": today,
                "source": "sample_fallback",
                "games_count": len(lines),
                "timestamp": datetime.now().isoformat()
            }
        }

        with open(output_file, 'w') as f:
            json.dump(output_data, f, indent=2)

        print(f"Created sample betting lines file: {output_file}")
        print(f"Generated lines for {len(lines)} games")
        return True

    except Exception as e:
        print(f"Error creating betting lines: {e}")
        return False

def try_integrated_closing_lines():
    """Try using the integrated closing lines manager"""
    try:
        from integrated_closing_lines import IntegratedClosingLinesManager

        print("Trying integrated closing lines manager...")
        manager = IntegratedClosingLinesManager()
        
        today = datetime.now().strftime('%Y-%m-%d')
        result = manager.get_closing_lines_for_date(today)
        
        if result and result.get('games'):
            print(f"Found {len(result['games'])} games via integrated manager")
            
            # Convert to the expected format
            lines = {}
            for game in result['games']:
                matchup_key = f"{game.get('away_team', '')} @ {game.get('home_team', '')}"
                
                # Convert the integrated manager format to our expected format
                game_lines = {
                    "moneyline": game.get('moneyline', {}),
                    "total_runs": {
                        "line": game.get('total', {}).get('line'),
                        "over": game.get('total', {}).get('over'),
                        "under": game.get('total', {}).get('under')
                    },
                    "run_line": {
                        "line": game.get('spread', {}).get('line'),
                        "away": game.get('spread', {}).get('away'),
                        "home": game.get('spread', {}).get('home')
                    }
                }
                lines[matchup_key] = game_lines
            
            if lines:
                today_underscore = today.replace('-', '_')
                output_file = Path(f"data/real_betting_lines_{today_underscore}.json")
                
                output_data = {
                    "date": today,
                    "fetched_at": datetime.now().isoformat(),
                    "source": "DraftKings_via_OddsAPI",
                    "lines": lines
                }
                
                with open(output_file, 'w') as f:
                    json.dump(output_data, f, indent=2)

                print(f"Created real betting lines file: {output_file}")
                return True

        print("No games found via integrated manager, falling back to sample data")
        return False

    except Exception as e:
        print(f"Integrated closing lines failed: {e}")
        return False

def main():
    """Main function"""
    print("Fetching betting lines for today...")
    
    # Try integrated closing lines first
    if try_integrated_closing_lines():
        return True
    
    # Fallback to sample data
    print("Creating sample betting lines...")
    return create_sample_betting_lines()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
