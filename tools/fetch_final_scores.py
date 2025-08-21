import requests
import json
from datetime import datetime

def fetch_final_scores(date_str):
    """
    Fetch final MLB scores for a given date (YYYY-MM-DD) and output in the required format.
    """
    # Convert date to YYYY-MM-DD
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    year = date_obj.year
    month = date_obj.month
    day = date_obj.day
    
    # Use statsapi endpoint
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={date_str}"
    resp = requests.get(url)
    data = resp.json()
    games = data.get('dates', [{}])[0].get('games', [])
    results = []
    for game in games:
        teams = game.get('teams', {})
        away = teams.get('away', {})
        home = teams.get('home', {})
        away_team = away.get('team', {}).get('name', '')
        home_team = home.get('team', {}).get('name', '')
        away_score = away.get('score')
        home_score = home.get('score')
        # Only include games with final scores
        if away_score is not None and home_score is not None:
            results.append({
                "away_team": away_team,
                "home_team": home_team,
                "away_score": away_score,
                "home_score": home_score
            })
    # Save to file
    out_path = f"data/final_scores_{date_str.replace('-', '_')}.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Saved {len(results)} final scores to {out_path}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        date_str = sys.argv[1]
    else:
        date_str = datetime.now().strftime("%Y-%m-%d")
    fetch_final_scores(date_str)
