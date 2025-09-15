import os, sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from app import app

TARGET = 'colin rea'

def norm(s: str) -> str:
    return (s or '').strip().lower()

if __name__ == '__main__':
    with app.test_client() as c:
        ls = c.get('/api/pitcher-props/live-stats').get_json()
        u = c.get('/api/pitcher-props/unified').get_json()
        print('live count', ls.get('count'))
        names = [k for k in ls.get('live_stats',{}).keys() if 'rea' in k]
        print('live name hits', names)
        if names:
            print('live entry', ls['live_stats'][names[0]])
        by_id = ls.get('live_stats_by_id',{})
        print('by_id size', len(by_id))
        # Show any ids whose names look like Rea
        sus = []
        for name, st in ls.get('live_stats',{}).items():
            if 'rea' in name:
                # find its id if present in any box entry (not directly mapped here)
                pass
        cards = u.get('pitchers', []) or u.get('data',{}).get('pitchers',[])
        target=None
        for p in cards:
            nm=(p.get('display_name') or p.get('name') or p.get('player_name') or '').lower()
            if 'colin' in nm and 'rea' in nm:
                target=p; break
        print('card exists', bool(target))
        if target:
            pid = target.get('mlb_player_id') or target.get('player_id')
            print('card ids mlb/player', target.get('mlb_player_id'), '/', target.get('player_id'))
            print('in live_by_id?', str(pid) in by_id)
