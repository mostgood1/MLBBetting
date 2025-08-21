#!/usr/bin/env python3
"""
Real Betting Lines Fetcher
Fetches actual betting lines from OddsAPI or copies from recent real data
NEVER creates fake/sample data
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
import sys

def get_recent_real_betting_lines():
    """Find the most recent real betting lines file to use as template"""
    data_dir = Path("data")
    
    # Look for recent real betting lines files
    pattern = "real_betting_lines_2025_*.json"
    betting_files = list(data_dir.glob(pattern))
    
    if not betting_files:
        print("❌ No existing real betting lines files found")
        return None, None
    
    # Sort by date (most recent first)
    betting_files.sort(reverse=True)
    
    for betting_file in betting_files:
        try:
            with open(betting_file, 'r') as f:
                data = json.load(f)
            
            # Skip if this was sample/fake data
            source = data.get('source', '')
            if 'sample' in source.lower() or 'generated' in source.lower() or 'fake' in source.lower():
                print(f"⚠️ Skipping {betting_file.name} - contains sample data")
                continue
            
            lines = data.get('lines', {})
            if lines and len(lines) > 0:
                print(f"✅ Found recent real betting lines: {betting_file.name} ({len(lines)} games)")
                return betting_file, data
        except Exception as e:
            print(f"⚠️ Error reading {betting_file.name}: {e}")
            continue
    
    print("❌ No valid recent real betting lines found")
    return None, None

def copy_and_adapt_recent_lines():
    """Copy recent real betting lines and adapt for today's games"""
    today = datetime.now().strftime('%Y-%m-%d')
    today_underscore = today.replace('-', '_')
    
    # Load today's games
    games_file = Path(f"data/games_{today}.json")
    if not games_file.exists():
        print(f"❌ Games file not found: {games_file}")
        return False
    
    try:
        with open(games_file, 'r') as f:
            games_data = json.load(f)
        
        # Get recent real betting lines
        recent_file, recent_data = get_recent_real_betting_lines()
        if not recent_data:
            print("❌ Cannot proceed - no real betting lines available to copy from")
            return False
        
        # Adapt lines for today's games - EXACT MATCHES ONLY
        recent_lines = recent_data.get('lines', {})
        adapted_lines = {}
        missing_games = []
        
        for game in games_data:
            away_team = game.get('away_team', '')
            home_team = game.get('home_team', '')
            matchup_key = f"{away_team} @ {home_team}"
            
            # Only accept exact matchup matches
            if matchup_key in recent_lines:
                adapted_lines[matchup_key] = recent_lines[matchup_key]
                print(f"✅ Exact match found: {matchup_key}")
            else:
                # Check for reverse matchup (home @ away)
                reverse_key = f"{home_team} @ {away_team}"
                if reverse_key in recent_lines:
                    # Flip the odds for reverse matchup
                    original_line = recent_lines[reverse_key]
                    flipped_line = {
                        "moneyline": {
                            "away": original_line["moneyline"]["home"],
                            "home": original_line["moneyline"]["away"]
                        },
                        "total_runs": original_line.get("total_runs", {}),  # Totals stay the same
                        "run_line": {
                            "away": original_line["run_line"]["home"],
                            "home": original_line["run_line"]["away"]
                        }
                    }
                    adapted_lines[matchup_key] = flipped_line
                    print(f"✅ Reverse match found and flipped: {matchup_key}")
                else:
                    # No acceptable match found
                    missing_games.append(matchup_key)
                    print(f"❌ No exact match found for: {matchup_key}")
        
        # If we're missing games, we cannot proceed with real data
        if missing_games:
            print(f"❌ Cannot create betting lines - missing exact matches for {len(missing_games)} games:")
            for game in missing_games:
                print(f"   - {game}")
            print("❌ Will not create incomplete or fake betting lines")
            return False
        
        # Create output data structure
        output_data = {
            "date": today,
            "fetched_at": datetime.now().isoformat(),
            "source": f"adapted_from_{recent_file.name}",
            "original_source": recent_data.get('source', 'unknown'),
            "lines": adapted_lines
        }
        
        # Save to file
        output_file = Path(f"data/real_betting_lines_{today_underscore}.json")
        with open(output_file, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        print(f"✅ Created adapted real betting lines file: {output_file}")
        print(f"📊 Adapted lines for {len(adapted_lines)} games from real data")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating betting lines: {e}")
        return False

def try_odds_api():
    """Try to fetch fresh betting lines from OddsAPI"""
    try:
        from integrated_closing_lines import IntegratedClosingLinesManager
        
        print("🔄 Trying OddsAPI via integrated closing lines manager...")
        manager = IntegratedClosingLinesManager()
        
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Try to fetch live odds
        odds_data = manager.fetch_live_odds(today)
        
        if odds_data and len(odds_data) > 0:
            print(f"✅ Found {len(odds_data)} games from OddsAPI")
            
            # Parse the odds data
            parsed_lines = manager.parse_odds_data(odds_data, today)
            
            if parsed_lines:
                # Convert to expected format
                lines = {}
                for line in parsed_lines:
                    matchup_key = f"{line.get('away_team', '')} @ {line.get('home_team', '')}"
                    # Map 'total' to 'total_runs' for output
                    total_runs = line.get('total', {})
                    lines[matchup_key] = {
                        "moneyline": line.get('moneyline', {}),
                        "total_runs": total_runs,
                        "run_line": line.get('run_line', {})
                    }
                
                today_underscore = today.replace('-', '_')
                output_file = Path(f"data/real_betting_lines_{today_underscore}.json")
                
                output_data = {
                    "date": today,
                    "fetched_at": datetime.now().isoformat(),
                    "source": "OddsAPI_live",
                    "lines": lines
                }
                
                with open(output_file, 'w') as f:
                    json.dump(output_data, f, indent=2)
                
                print(f"✅ Created fresh OddsAPI betting lines file: {output_file}")
                return True
        
        print("⚠️ No fresh odds available from OddsAPI")
        return False
        
    except Exception as e:
        print(f"⚠️ OddsAPI fetch failed: {e}")
        return False

def main():
    """Main function - try real sources only, never create fake data"""
    print("Fetching REAL betting lines for today...")
    
    # Try OddsAPI first for fresh data
    if try_odds_api():
        return True
    
    # NO FALLBACK TO OLD DATA - betting lines must be current
    print("FAILED: No real betting lines could be obtained from OddsAPI")
    print("ERROR: Cannot use old betting lines for current games")
    print("SOLUTION NEEDED:")
    print("  1. Configure OddsAPI key in data/closing_lines_config.json")
    print("  2. Verify API key is valid and has MLB permissions")
    print("  3. Check network connectivity to api.the-odds-api.com")
    return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
