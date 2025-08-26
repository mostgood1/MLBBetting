import json

# Check what keys are actually in the betting recommendations file
with open('data/betting_recommendations_2025_08_26.json', 'r') as f:
    data = json.load(f)

print('=== BETTING RECOMMENDATIONS FILE KEYS ===')
if 'games' in data:
    game_keys = list(data['games'].keys())
    print(f'Total games: {len(game_keys)}')
    print('First 10 game keys:')
    for i, key in enumerate(game_keys[:10]):
        print(f'  {i+1}. "{key}"')
    
    print()
    print('Looking for Boston Red Sox games:')
    for key in game_keys:
        if 'Boston Red Sox' in key:
            print(f'  Found: "{key}"')
    
    print()
    print('Looking for pattern with "_vs_":')
    for key in game_keys:
        if '_vs_' in key:
            print(f'  Found: "{key}"')
            break
