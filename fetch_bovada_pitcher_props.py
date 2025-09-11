#!/usr/bin/env python3
"""Fetch Bovada MLB pitcher prop lines and store normalized JSON.

Creates data/daily_bovada/bovada_pitcher_props_<YYYY_MM_DD>.json

Resilient version with multiple endpoint fallbacks, retry logic, and
basic bot-avoidance headers. If all sources fail, writes an empty stub
so downstream code doesn't break.
"""
import os
import json
import logging
import unicodedata
import time
import random
import re
from datetime import datetime
from typing import Dict, Any, List

import requests

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("bovada_pitcher_props")

DATA_DIR = os.path.join('data', 'daily_bovada')
os.makedirs(DATA_DIR, exist_ok=True)

# Primary + fallback endpoints (Bovada occasionally shifts structures)
BASE_ENDPOINTS = [
    # Original
    "https://www.bovada.lv/services/sports/event/v2/events/A/description/baseball/mlb",
    # With explicit lang
    "https://www.bovada.lv/services/sports/event/v2/events/A/description/baseball/mlb?lang=en",
    # Generic baseball (filter for MLB inside)
    "https://www.bovada.lv/services/sports/event/v2/events/A/description/baseball?lang=en",
    # Add preMatchOnly param
    "https://www.bovada.lv/services/sports/event/v2/events/A/description/baseball/mlb?preMatchOnly=true&lang=en",
]

# Allow override for quick experimentation
if os.environ.get("BOVADA_EVENTS_URL"):
    BASE_ENDPOINTS.insert(0, os.environ["BOVADA_EVENTS_URL"])  # user-specified has priority

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.bovada.lv/baseball/mlb/game-lines",
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "no-cache",
}

TARGET_KEYWORDS = {
    'strikeouts': ['pitcher strikeouts', 'player strikeouts', 'total strikeouts'],
    'outs': ['pitcher outs', 'outs recorded', 'pitcher outs recorded'],
    'hits_allowed': ['hits allowed', 'pitcher hits allowed'],
    'walks': ['walks allowed', 'pitcher walks allowed', 'pitcher walks'],
    'earned_runs': ['earned runs', 'pitcher earned runs'],
}
ALT_STRIKEOUT_HINTS = ['alt strikeouts', 'alternate strikeouts']

MAX_RETRIES = 3
RETRY_SLEEP_MIN = 1.0
RETRY_SLEEP_MAX = 2.5

# Add detail endpoint pattern for individual event markets refresh
EVENT_DETAIL_PATTERN = "https://www.bovada.lv/services/sports/event/v2/events/A/description/{event_id}"

# Additional candidate event-specific endpoints (some expose deeper player prop groups)
EVENT_VARIANT_PATTERNS = [
    "https://www.bovada.lv/services/sports/event/v2/events/A/description/{event_id}",
    "https://www.bovada.lv/services/sports/event/v2/events/A/markets/{event_id}",
    "https://www.bovada.lv/services/sports/event/v2/events/A/description/{event_id}?lang=en&preMatchOnly=true",
    "https://www.bovada.lv/services/sports/event/v2/events/A/markets/{event_id}?lang=en&preMatchOnly=true",
]

DEBUG_DUMP = os.environ.get("BOVADA_DEBUG_PITCHER_EVENT")  # supply an event_id to dump raw JSON


def normalize_name(name: str) -> str:
    try:
        text = unicodedata.normalize('NFD', name)
        text = ''.join(ch for ch in text if unicodedata.category(ch) != 'Mn')
        return text.lower().strip()
    except Exception:
        return name.lower().strip()


def _match_market(market_name: str, keywords: List[str]) -> bool:
    m = market_name.lower()
    for kw in keywords:
        if kw in m:
            return True
    return False


def _http_get_json(url: str) -> Any:
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=25)
            # Some blocking responses return HTML (Cloudflare / Akamai) – detect
            ctype = resp.headers.get('Content-Type', '')
            if 'json' not in ctype.lower() and not resp.text.strip().startswith('[') and not resp.text.strip().startswith('{'):
                raise ValueError(f"Non-JSON response (content-type={ctype}, len={len(resp.text)})")
            data = resp.json()
            return data
        except Exception as e:
            logger.warning(f"Attempt {attempt}/{MAX_RETRIES} failed for {url}: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(random.uniform(RETRY_SLEEP_MIN, RETRY_SLEEP_MAX))
            else:
                return None


def fetch_raw_events() -> List[Dict[str, Any]]:
    aggregated: Dict[str, Dict[str, Any]] = {}
    for idx, url in enumerate(BASE_ENDPOINTS):
        logger.info(f"Fetching endpoint {idx+1}/{len(BASE_ENDPOINTS)}: {url}")
        data = _http_get_json(url)
        if not data:
            continue
        # Each top-level list entry may contain 'events'
        if isinstance(data, list):
            for grp in data:
                for ev in grp.get('events', []) or []:
                    eid = str(ev.get('id'))
                    aggregated[eid] = ev
        elif isinstance(data, dict):
            for ev in data.get('events', []) or []:
                eid = str(ev.get('id'))
                aggregated[eid] = ev
        # If we already have a decent number of events, we can stop early
        if len(aggregated) >= 50:  # heuristic
            break
    events = list(aggregated.values())
    if not events:
        logger.error("All Bovada endpoints failed – no events collected")
    else:
        logger.info(f"Collected {len(events)} total events across endpoints")
    return events


def parse_pitcher_props(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    pitcher_props: Dict[str, Dict[str, Any]] = {}
    for ev in events:
        display_groups = ev.get('displayGroups', []) or []
        for dg in display_groups:
            markets = dg.get('markets', []) or []
            for mk in markets:
                mk_desc = str(mk.get('description', '')).strip()
                pitcher_name = ''
                if ' - ' in mk_desc:
                    parts = mk_desc.split(' - ')
                    if len(parts) >= 2:
                        pitcher_name = parts[-1].strip()
                        market_label = ' - '.join(parts[:-1])
                    else:
                        market_label = mk_desc
                else:
                    market_label = mk_desc
                market_label_lc = market_label.lower()
                stat_key = None
                for key, kws in TARGET_KEYWORDS.items():
                    if _match_market(market_label_lc, kws):
                        stat_key = key
                        break
                is_alt_strikeouts = False
                if not stat_key and any(h in market_label_lc for h in ALT_STRIKEOUT_HINTS):
                    stat_key = 'strikeouts'
                    is_alt_strikeouts = True
                if not stat_key:
                    continue
                outcomes = mk.get('outcomes', []) or []
                if not pitcher_name:
                    for oc in outcomes:
                        pn = oc.get('participant') or oc.get('competitor') or ''
                        if pn and ' over' not in pn.lower():
                            pitcher_name = pn
                            break
                if not pitcher_name:
                    continue
                p_key = normalize_name(pitcher_name)
                entry = pitcher_props.setdefault(p_key, {})
                try:
                    if not is_alt_strikeouts:
                        line_val = None
                        over_odds = None
                        under_odds = None
                        for oc in outcomes:
                            desc = str(oc.get('description', '')).lower()
                            price = oc.get('price', {}) or {}
                            american = price.get('american') or price.get('handicap') or price.get('price')
                            if line_val is None:
                                raw_line = price.get('handicap') or oc.get('handicap')
                                if raw_line is not None:
                                    try:
                                        line_val = float(raw_line)
                                    except Exception:
                                        pass
                            if desc == 'over':
                                over_odds = american
                            elif desc == 'under':
                                under_odds = american
                        if line_val is not None:
                            entry.setdefault(stat_key, {})['line'] = line_val
                            if over_odds is not None:
                                entry[stat_key]['over_odds'] = over_odds
                            if under_odds is not None:
                                entry[stat_key]['under_odds'] = under_odds
                    else:
                        alt_list = entry.setdefault('strikeouts_alts', [])
                        for oc in outcomes:
                            price = oc.get('price', {}) or {}
                            raw_line = price.get('handicap') or oc.get('handicap')
                            odds = price.get('american') or price.get('price')
                            try:
                                if raw_line is not None:
                                    alt_list.append({'threshold': float(raw_line), 'odds': odds})
                            except Exception:
                                continue
                except Exception as e:
                    logger.debug(f"Market parse error {mk_desc}: {e}")
    return pitcher_props


def fetch_event_variants(event_id: str) -> List[Any]:
    out = []
    for pat in EVENT_VARIANT_PATTERNS:
        url = pat.format(event_id=event_id)
        data = _http_get_json(url)
        if data:
            out.append(data)
            # If we already got a markets variant with many displayGroups, we can stop
            try:
                if isinstance(data, list):
                    groups = sum(len(g.get('events', [])) for g in data)
                elif isinstance(data, dict):
                    groups = len(data.get('events', []) or [])
                else:
                    groups = 0
                if groups > 0 and len(out) >= 2:
                    break
            except Exception:
                pass
    return out


# Replace previous simple enrichment with deeper variant scraping

# NEW: attempt to enrich pitcher markets by visiting each event detail page for missing markets
PITCHER_MARKET_HINTS = ['strikeouts', 'outs', 'earned runs', 'hits allowed', 'walks']

def enrich_from_event_details(events: List[Dict[str, Any]], existing: Dict[str, Any]):
    for ev in events:
        ev_id = ev.get('id')
        if not ev_id:
            continue
        try:
            variants = fetch_event_variants(str(ev_id))
            combined_events = []
            for variant in variants:
                if isinstance(variant, list):
                    for grp in variant:
                        combined_events.extend(grp.get('events', []) or [])
                elif isinstance(variant, dict):
                    combined_events.extend(variant.get('events', []) or [])
            if not combined_events:
                continue
            parsed = parse_pitcher_props(combined_events)
            # Debug dump if requested
            if DEBUG_DUMP and DEBUG_DUMP == str(ev_id):
                dump_path = os.path.join(DATA_DIR, f'debug_event_{ev_id}.json')
                try:
                    with open(dump_path, 'w', encoding='utf-8') as f:
                        json.dump({'variants': variants}, f, indent=2)
                    logger.info(f"DEBUG dump written: {dump_path}")
                except Exception:
                    pass
            for p_key, new_markets in parsed.items():
                tgt = existing.setdefault(p_key, {})
                for mk, val in new_markets.items():
                    # If market missing or incomplete, replace
                    if mk not in tgt or (isinstance(val, dict) and (not tgt.get(mk) or 'line' not in tgt.get(mk, {}))):
                        tgt[mk] = val
        except Exception as e:
            logger.debug(f"Variant enrichment failed for event {ev_id}: {e}")
            continue


def main() -> bool:
    date_str = datetime.now().strftime('%Y-%m-%d')
    date_us = date_str.replace('-', '_')
    out_path = os.path.join(DATA_DIR, f'bovada_pitcher_props_{date_us}.json')
    logger.info(f"Fetching Bovada pitcher props for {date_str}")
    events = fetch_raw_events()
    if not events:
        logger.warning("No events retrieved; writing empty stub file")
    props = parse_pitcher_props(events)
    # If we are missing core markets widely (e.g., only walks captured), try enrichment
    have_walks_only = props and all(set(v.keys()) <= {'walks', 'strikeouts_alts'} for v in props.values())
    missing_k = all('strikeouts' not in v for v in props.values()) if props else True
    if have_walks_only or missing_k:
        logger.info("Attempting enrichment via per-event detail pages to fill missing pitcher markets...")
        enrich_from_event_details(events, props)
    payload = {
        'date': date_str,
        'retrieved_at': datetime.utcnow().isoformat(),
        'pitcher_props': props,
        'event_count': len(events)
    }
    try:
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(payload, f, indent=2)
        logger.info(f"Saved pitcher props file: {out_path} (pitchers={len(props)}, raw_events={len(events)})")
        if not props:
            logger.info("Hint: If this remains empty repeatedly, endpoint structure or geo-block may have changed. Consider manual capture or a proxy.")
        return True
    except Exception as e:
        logger.error(f"Failed writing props file: {e}")
        return False

if __name__ == '__main__':
    main()
