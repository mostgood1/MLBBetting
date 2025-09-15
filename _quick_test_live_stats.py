import json
from app import app

def normalize_name(s: str) -> str:
    return (s or '').strip().lower()

if __name__ == "__main__":
    with app.test_client() as c:
        rl = c.get('/api/pitcher-props/live-stats')
        print('live-stats status', rl.status_code)
        if rl.status_code == 200:
            data = rl.get_json()
            print('keys', list(data.keys()))
            print('count', data.get('count'))
            print('by_id', 'live_stats_by_id' in data, 'entries', len(data.get('live_stats_by_id', {})))
            ls = data.get('live_stats', {})
            print('sample_names', list(ls.keys())[:5])

        ru = c.get('/api/pitcher-props/unified')
        print('unified status', ru.status_code)
        if ru.status_code == 200:
            u = ru.get_json()
            cards = u.get('pitchers', []) or u.get('data', {}).get('pitchers', [])
            # collect normalized names and ids from cards
            names = set()
            ids = set()
            for p in cards:
                name = p.get('name') or p.get('player_name') or p.get('pitcher_name')
                if name:
                    names.add(normalize_name(name))
                pid = p.get('mlb_player_id') or p.get('player_id')
                if pid:
                    ids.add(str(pid))
            live_names = set(map(str, (rl.get_json() or {}).get('live_stats', {}).keys())) if rl.status_code == 200 else set()
            live_ids = set(map(str, (rl.get_json() or {}).get('live_stats_by_id', {}).keys())) if rl.status_code == 200 else set()
            print('cards', len(cards), 'card_names', len(names), 'card_ids', len(ids))
            print('live_names', len(live_names), 'intersection', len(names & live_names))
            print('live_ids', len(live_ids), 'id intersection', len(ids & live_ids))
