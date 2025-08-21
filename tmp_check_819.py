import json,os
base=r'c:\Users\mostg\OneDrive\Coding\MLB-Betting\data\\'
with open(os.path.join(base,'games_2025-08-19.json'),'r',encoding='utf-8') as f: games=json.load(f)
with open(os.path.join(base,'unified_predictions_cache.json'),'r',encoding='utf-8') as f: unified=json.load(f)
with open(os.path.join(base,'historical_predictions_cache.json'),'r',encoding='utf-8') as f: hist=json.load(f)
with open(os.path.join(base,'real_betting_lines_2025_08_19.json'),'r',encoding='utf-8') as f: lines=json.load(f)
all_unified = {}
for date, val in unified.get('predictions_by_date',{}).items():
    for k,v in val.get('games',{}).items():
        all_unified[k]=v

def find_unified(away,home):
    for k,v in all_unified.items():
        kn = k.replace('_',' ').lower()
        if away.lower() in kn and home.lower() in kn:
            return k,v
        if away.split()[-1].lower() in kn and home.split()[-1].lower() in kn:
            return k,v
    return None,None

def find_betting_line(away,home):
    for k,v in lines.get('lines',{}).items():
        lk=k.lower()
        target=f"{away} @ {home}".lower()
        if lk==target:
            return k,v
        if away.split()[-1].lower() in lk and home.split()[-1].lower() in lk:
            return k,v
    return None,None

print('game_pk','away','home','unified_key','predicted_total','bet_line',sep=' | ')
for g in games:
    away=g.get('away_team')
    home=g.get('home_team')
    uk,uv=find_unified(away,home)
    if uv is not None:
        pt = None
        if 'predictions' in uv:
            pt = uv['predictions'].get('predicted_total_runs')
        else:
            pt = uv.get('predicted_total_runs')
    else:
        pt=None
    bk,bv=find_betting_line(away,home)
    bl = bv.get('total_runs',{}).get('line') if bv else None
    print(g.get('game_pk'), away, home, uk or '-', pt if pt is not None else '-', bl if bl is not None else '-')
