from app import app, api_today_games

def main():
    # Use heavy mode and sufficient sims; rely on app's internals for date
    with app.test_request_context('/api/today-games?heavy=1&sim_count=5000'):
        resp = api_today_games()
        data = resp.get_json()
        games = data.get('games', []) if isinstance(data, dict) else []
        print(f"games_count={len(games)} heavy_mode={data.get('meta', {}).get('heavy_mode') if isinstance(data, dict) else None}")
        # Find ATL @ WSH if present
        for g in games:
            away = g.get('away_team') or g.get('away_team_name') or g.get('away', {}).get('team')
            home = g.get('home_team') or g.get('home_team_name') or g.get('home', {}).get('team')
            if not away or not home:
                continue
            if ('Atlanta' in away and 'Washington' in home) or ('Atlanta' in home and 'Washington' in away):
                preds = g.get('predictions', {})
                print(f"{away} @ {home} | wp A/H: {preds.get('away_win_prob')} / {preds.get('home_win_prob')} | scores A-H: {preds.get('predicted_away_score')}-{preds.get('predicted_home_score')} | game_pk={g.get('game_pk')} g#={g.get('game_number')} starters: {g.get('away_pitcher')} vs {g.get('home_pitcher')}")

if __name__ == '__main__':
    main()
