import json
from pathlib import Path
from collections import deque

if __name__ == '__main__':
    p=Path('data/boxscore_cache.json')
    print('exists', p.exists(), 'size', p.stat().st_size if p.exists() else 0)
    obj=json.load(open(p, 'r', encoding='utf-8'))
    NAMES=set(); PLAYER_IDS=set()
    q=deque([obj])
    while q:
        x=q.popleft()
        if isinstance(x, dict):
            person=x.get('person') if isinstance(x.get('person'), dict) else None
            position=x.get('position') if isinstance(x.get('position'), dict) else None
            stats=x.get('stats') if isinstance(x.get('stats'), dict) else None
            if person and position and stats and position.get('abbreviation')=='P':
                nm=(person.get('fullName') or person.get('name') or '').strip().lower()
                if nm:
                    NAMES.add(nm)
                pid=person.get('id')
                if pid:
                    PLAYER_IDS.add(str(pid))
            for v in x.values(): q.append(v)
        elif isinstance(x, list):
            q.extend(x)
    print('pitcher entries', len(NAMES))
    print('rea matches', [n for n in NAMES if 'rea' in n])
    print('ids count', len(PLAYER_IDS))
