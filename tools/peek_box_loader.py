import os, sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from app import _load_boxscore_pitcher_stats

if __name__ == '__main__':
    box = _load_boxscore_pitcher_stats('2025-09-13')
    print('box count', len(box))
    names = [k for k in box.keys() if 'rea' in k]
    print('keys with rea', names)
    if names:
        print('entry', box[names[0]])
