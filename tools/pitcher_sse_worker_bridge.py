#!/usr/bin/env python3
"""Optional bridge: post updater events to the web app for SSE broadcast and persistence.

Usage: import and call send_events([...]) from the worker when needed.
The web app must expose /internal/pitcher-props/broadcast with token auth.
"""
import os, json, urllib.request
from urllib.error import HTTPError, URLError

WEB_BASE = os.environ.get('WEB_BASE_URL')  # e.g., https://mlb-betting-system.onrender.com
TOKEN = os.environ.get('PITCHER_SSE_INGEST_TOKEN')
DEBUG = os.environ.get('PITCHER_SSE_BRIDGE_DEBUG','0') == '1'

def send_events(events):
    if not WEB_BASE or not TOKEN:
        if DEBUG:
            print(f"[Bridge] Missing WEB_BASE_URL or PITCHER_SSE_INGEST_TOKEN (WEB_BASE_URL={bool(WEB_BASE)} TOKEN_SET={bool(TOKEN)})")
        return False
    try:
        url = WEB_BASE.rstrip('/') + '/internal/pitcher-props/broadcast'
        data = json.dumps({'type':'batch','events': events}).encode('utf-8')
        if DEBUG:
            print(f"[Bridge] POST {url} bytes={len(data)} events={len(events)} types={[e.get('type') for e in events][:5]}")
        req = urllib.request.Request(url, data=data, headers={'Content-Type':'application/json', 'Authorization': f'Bearer {TOKEN}'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            ok = 200 <= resp.status < 300
            if DEBUG and not ok:
                print(f"[Bridge] Non-2xx status: {resp.status}")
            return ok
    except HTTPError as e:
        if DEBUG:
            try:
                body = e.read().decode('utf-8', errors='ignore')[:300]
            except Exception:
                body = ''
            print(f"[Bridge] HTTPError {e.code}: {body}")
        return False
    except URLError as e:
        if DEBUG:
            print(f"[Bridge] URLError: {e}")
        return False
    except Exception as e:
        if DEBUG:
            print(f"[Bridge] Unexpected error: {e}")
        return False

if __name__ == '__main__':
    ok = send_events([{'type':'ping','ts':'now'}])
    print('bridge ok' if ok else 'bridge fail')
