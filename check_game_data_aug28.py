#!/usr/bin/env python3
"""
Check if game data exists for August 28
"""

from enhanced_mlb_fetcher import enhanced_fetch_games_for_date

def check_game_data():
    date = '2025-08-28'
    try:
        games = enhanced_fetch_games_for_date(date)
        print(f"Games found for {date}: {len(games)}")
        
        if games:
            sample = games[0]
            print(f"Sample game: {sample.get('away_team', 'N/A')} vs {sample.get('home_team', 'N/A')}")
            print(f"Game status: {sample.get('status', 'N/A')}")
            print(f"Away score: {sample.get('away_score', 'N/A')}")
            print(f"Home score: {sample.get('home_score', 'N/A')}")
        
        return games
    except Exception as e:
        print(f"Error fetching games: {e}")
        return []

if __name__ == "__main__":
    games = check_game_data()
