#!/usr/bin/env python3
import json

dates = ['2025-08-15', '2025-08-16']

print("Checking regenerated dates:")
for date in dates:
    file_path = f'data/betting_recommendations_{date.replace("-", "_")}.json'
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    games = data['games']
    total_recs = sum(len(game.get('value_bets', [])) for game in games.values())
    
    print(f'{date}: {len(games)} games, {total_recs} recommendations')
    
    # Show first recommendation if any
    for game_key, game in games.items():
        if game.get('value_bets'):
            rec = game['value_bets'][0]
            print(f'  First rec: {rec["recommendation"]} (EV: {rec["expected_value"]:.3f})')
            break
        else:
            continue
    else:
        if total_recs == 0:
            print(f'  No recommendations found for {date}')
