#!/usr/bin/env python3
"""
Normalize older per-day betting_recommendations files (8/22, 8/23) into a unified format
with unified_value_bets and enhanced fields. Writes *_enhanced.json next to the source.
"""
import json, os, sys
from datetime import datetime

def parse_odds(val):
    try:
        if val in (None, '', 'N/A'): return -110
        s = str(val).strip().replace('−','-')
        if s.startswith('+'): s = s[1:]
        return int(float(s))
    except Exception:
        return -110

def unify_game(game_key, game_data):
    away = game_data.get('away_team')
    home = game_data.get('home_team')
    preds = (game_data.get('predictions') or {})
    nested = (preds.get('recommendations') or [])
    uvb = []
    # pull existing unified_value_bets if any
    uvb.extend((game_data.get('unified_value_bets') or []))
    # pull value_bets if any
    uvb.extend((game_data.get('value_bets') or []))
    # add from nested predictions.recommendations
    for pr in nested:
        rtype = (pr.get('type') or 'unknown').lower()
        side = pr.get('side')
        line = pr.get('line')
        pick = pr.get('recommendation')
        if not pick:
            if rtype.startswith('total') and side and line is not None:
                pick = f"{str(side).title()} {line}"
            elif rtype.startswith('moneyline') and side:
                pick = str(side)
        odds = pr.get('american_odds', pr.get('odds', -110))
        uvb.append({
            'type': 'total' if rtype.startswith('total') else ('moneyline' if rtype.startswith('moneyline') else rtype),
            'recommendation': pick,
            'side': pr.get('side'),
            'line': pr.get('line'),
            'american_odds': odds,
            'odds': parse_odds(odds),
            'expected_value': pr.get('expected_value', 0),
            'confidence': pr.get('confidence', 'UNKNOWN'),
            'kelly_bet_size': pr.get('kelly_bet_size'),
            'predicted_total': pr.get('model_total'),
            'betting_line': pr.get('line'),
            'reasoning': pr.get('reasoning', '')
        })
    # de-duplicate by (type,recommendation)
    seen=set(); out=[]
    for r in uvb:
        key=(r.get('type'), r.get('recommendation'))
        if key in seen: continue
        seen.add(key); out.append(r)
    game_data['unified_value_bets']=out
    return game_data

def normalize_file(path):
    with open(path,'r',encoding='utf-8') as f:
        data=json.load(f)
    games=data.get('games',{})
    for k in list(games.keys()):
        games[k]=unify_game(k, games[k])
    data['source']=data.get('source','Unified Betting Engine v1.0')+" (enhanced)"
    data['enhanced_generated_at']=datetime.now().isoformat()
    out=path.replace('.json','_enhanced.json')
    with open(out,'w',encoding='utf-8') as f:
        json.dump(data,f,indent=2,ensure_ascii=False)
    return out

if __name__=='__main__':
    targets=['data/betting_recommendations_2025_08_22.json','data/betting_recommendations_2025_08_23.json']
    if len(sys.argv)>1:
        targets=sys.argv[1:]
    for p in targets:
        if os.path.exists(p):
            out=normalize_file(p)
            print(f"Wrote {out}")
        else:
            print(f"Missing {p}")
