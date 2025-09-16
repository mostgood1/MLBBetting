from app import app, api_today_games_quick

# Use Flask test_request_context to call the route directly without running a server
ctx = app.test_request_context('/api/today-games/quick?no_network=1')
ctx.push()
try:
    resp = api_today_games_quick()
    data = resp.get_json()
    games = data.get('games', []) if isinstance(data, dict) else []
    value_bets_games = sum(1 for g in games if g.get('betting_recommendations', {}).get('value_bets'))
    print('quick_count:', data.get('count'))
    print('value_bets_games:', value_bets_games)
    # Print a short summary line for manual spot-checking
    if games:
        sample = games[0]
        gid = sample.get('game_id') or sample.get('gid')
        preds = sample.get('predictions') or {}
        print('sample_game:', gid, 'predicted_scores:', preds.get('predicted_away_score'), preds.get('predicted_home_score'))
except Exception as e:
    import traceback
    print('ERROR:', e)
    traceback.print_exc()
finally:
    ctx.pop()
