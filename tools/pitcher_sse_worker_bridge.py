#!/usr/bin/env python3
"""Optional bridge: post updater events to the web app for SSE broadcast and persistence.

Usage: import and call send_events([...]) from the worker when needed.
The web app must expose /internal/pitcher-props/broadcast with token auth.
"""
import os, json, urllib.request

WEB_BASE = os.environ.get('WEB_BASE_URL')  # e.g., https://mlb-betting-system.onrender.com
TOKEN = os.environ.get('PITCHER_SSE_INGEST_TOKEN')

def send_events(events):
    if not WEB_BASE or not TOKEN:
        return False
    try:
        url = WEB_BASE.rstrip('/') + '/internal/pitcher-props/broadcast'
        data = json.dumps({'type':'batch','events': events}).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers={'Content-Type':'application/json', 'Authorization': f'Bearer {TOKEN}'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return 200 <= resp.status < 300
    except Exception:
        return False

if __name__ == '__main__':
    ok = send_events([{'type':'ping','ts':'now'}])
    print('bridge ok' if ok else 'bridge fail')
