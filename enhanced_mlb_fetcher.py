#!/usr/bin/env python3
"""
Minimal enhanced MLB data fetcher (shim).
Provides fetch_todays_complete_games(date) using the MLB Stats API (no key required).
Returns a list of games with basic fields: away_team, home_team, away_pitcher, home_pitcher, game_time, game_pk
"""
import requests
from datetime import datetime
from typing import List, Dict


def fetch_todays_complete_games(date: str) -> List[Dict]:
    """Fetch today's games and probable pitchers from the MLB Stats API.

    Args:
        date: YYYY-MM-DD

    Returns:
        List of game dicts. If nothing found, returns an empty list.
    """
    try:
        # Include probablePitcher and team in hydrate to improve pitcher availability
        url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={date}&hydrate=probablePitcher,team"
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        dates = data.get('dates', [])
        if not dates:
            return []

        games = dates[0].get('games', [])
        results = []

        for g in games:
            try:
                game_pk = g.get('gamePk')
                game_time = g.get('gameDate')  # ISO datetime

                away = g.get('teams', {}).get('away', {})
                home = g.get('teams', {}).get('home', {})

                away_team = away.get('team', {}).get('name') or away.get('team', {}).get('fullName') or 'Unknown'
                home_team = home.get('team', {}).get('name') or home.get('team', {}).get('fullName') or 'Unknown'

                # Try probable pitcher fields (present in schedule for many games)
                away_pitcher = away.get('probablePitcher', {}).get('fullName') if isinstance(away.get('probablePitcher'), dict) else None
                home_pitcher = home.get('probablePitcher', {}).get('fullName') if isinstance(home.get('probablePitcher'), dict) else None

                # Fallbacks
                if not away_pitcher:
                    away_pitcher = 'TBD'
                if not home_pitcher:
                    home_pitcher = 'TBD'

                results.append({
                    'game_pk': game_pk,
                    'game_time': game_time,
                    'away_team': away_team,
                    'home_team': home_team,
                    'away_pitcher': away_pitcher,
                    'home_pitcher': home_pitcher
                })

            except Exception:
                # ignore malformed game
                continue

        return results

    except Exception:
        return []


if __name__ == '__main__':
    today = datetime.now().strftime('%Y-%m-%d')
    games = fetch_todays_complete_games(today)
    print(f"Fetched {len(games)} games for {today}")
