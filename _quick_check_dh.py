from app import app, api_today_games

# Check doubleheader coverage for today's date
ctx = app.test_request_context('/api/today-games')
ctx.push()
try:
    resp = api_today_games()
    data = resp.get_json() or {}
    games = data.get('games', [])
    # Filter for doubleheader-marked games or duplicate matchups
    dh_games = [g for g in games if (g.get('live_status') or {}).get('status') or (g.get('meta') or {}).get('doubleheader')]

    # Build a map by matchup to detect multiple games
    by_matchup = {}
    for g in games:
        key = (g.get('away_team'), g.get('home_team'))
        by_matchup.setdefault(key, []).append(g)

    found = False
    for (away, home), glist in by_matchup.items():
        if len(glist) > 1:
            found = True
            print(f"MATCHUP {away} @ {home} -> {len(glist)} games")
            # Sort by explicit game_number if present; otherwise leave order
            def _sort_key(x):
                meta = x.get('meta') or {}
                gn = meta.get('game_number')
                # Prefer integers; if missing, push to end with large number
                try:
                    return int(gn) if gn is not None else 99
                except Exception:
                    return 99
            for i, g in enumerate(sorted(glist, key=_sort_key)):
                meta = g.get('meta') or {}
                preds = (g.get('predicted_away_score'), g.get('predicted_home_score'))
                vb = len((g.get('betting_recommendations') or {}).get('value_bets') or [])
                print(f"  G{meta.get('game_number') or i+1} game_pk={meta.get('game_pk') or g.get('game_id')} time={g.get('game_time')} preds={preds} has_lines={g.get('has_real_betting_lines')} value_bets={vb}")
    if not found:
        print('No doubleheaders detected in today-games payload; total games:', len(games))
except Exception as e:
    import traceback
    print('ERROR checking DH:', e)
    traceback.print_exc()
finally:
    ctx.pop()
