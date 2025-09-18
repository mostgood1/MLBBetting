#!/usr/bin/env python3
"""Refresh MLB pitcher props and optionally push updated files to git.

Intended for cron/worker environments (e.g., Render). Safe to run repeatedly;
uses environment variables to control push behavior.

Env flags:
  PITCHER_GIT_PUSH_ENABLED=1     # allow git push
  AUTO_GIT_PUSH_DISABLED=1       # force-disable push
  GIT_AUTHOR_NAME / GIT_AUTHOR_EMAIL (optional)
  GIT_COMMITTER_NAME / GIT_COMMITTER_EMAIL (optional)
  GIT_PUSH_URL (optional)        # if set, use as remote URL for push

Exit codes:
  0 on success (either fetch or generate succeeded)
  1 on failure
"""
import os
import sys
import time
import json
import glob
import subprocess as sp
from datetime import datetime

# Ensure repository root is on sys.path (script lives in scripts/)
try:
    _HERE = os.path.dirname(os.path.abspath(__file__))
    _ROOT = os.path.abspath(os.path.join(_HERE, os.pardir))
    if _ROOT not in sys.path:
        sys.path.insert(0, _ROOT)
except Exception:
    pass


def log(msg: str):
    ts = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{ts} UTC] {msg}")


def run_refresh() -> tuple[bool, dict, list[str]]:
    results = {}
    errors: list[str] = []
    ok_any = False
    try:
        from fetch_bovada_pitcher_props import main as fetch_props_main
        ok_fetch = bool(fetch_props_main())
        results['fetch_props'] = ok_fetch
        ok_any = ok_any or ok_fetch
        log(f"fetch_bovada_pitcher_props: {'OK' if ok_fetch else 'FAIL'}")
    except Exception as e:
        errors.append(f"fetch_props: {e}")
        log(f"ERROR fetch_bovada_pitcher_props: {e}")
        results['fetch_props'] = False
    try:
        from generate_pitcher_prop_projections import main as gen_recs_main
        ok_gen = bool(gen_recs_main())
        results['generate_recommendations'] = ok_gen
        ok_any = ok_any or ok_gen
        log(f"generate_pitcher_prop_projections: {'OK' if ok_gen else 'FAIL'}")
    except Exception as e:
        errors.append(f"generate_recommendations: {e}")
        log(f"ERROR generate_pitcher_prop_projections: {e}")
        results['generate_recommendations'] = False
    return ok_any, results, errors


def git_push(biz_today: str) -> dict:
    out: dict = {'attempted': True}
    allow_push_env = os.environ.get('PITCHER_GIT_PUSH_ENABLED') or os.environ.get('AUTO_GIT_PUSH_ENABLED')
    disabled = os.environ.get('AUTO_GIT_PUSH_DISABLED')
    if disabled and str(disabled).lower() in ('1','true','yes','y'):
        return {**out, 'skipped': True, 'reason': 'disabled by AUTO_GIT_PUSH_DISABLED'}
    if not allow_push_env or str(allow_push_env).lower() in ('0','false','no','n'):
        return {**out, 'skipped': True, 'reason': 'not enabled (set PITCHER_GIT_PUSH_ENABLED=1)'}
    try:
        chk = sp.run(['git','rev-parse','--is-inside-work-tree'], capture_output=True, text=True, check=True)
        if str(chk.stdout).strip().lower() != 'true':
            return {**out, 'error': 'not a git work tree'}
    except Exception as e:
        return {**out, 'error': f'git check failed: {e}'}
    # Optional identity
    user_name = os.environ.get('GIT_AUTHOR_NAME') or os.environ.get('GIT_COMMITTER_NAME')
    user_email = os.environ.get('GIT_AUTHOR_EMAIL') or os.environ.get('GIT_COMMITTER_EMAIL')
    if user_name:
        sp.run(['git','config','user.name', user_name], check=False)
    if user_email:
        sp.run(['git','config','user.email', user_email], check=False)
    # Optional override remote URL
    push_url = os.environ.get('GIT_PUSH_URL')
    if push_url:
        # Set a temporary remote named 'push-tmp'
        sp.run(['git','remote','remove','push-tmp'], check=False)
        sp.run(['git','remote','add','push-tmp', push_url], check=False)
    remote = 'push-tmp' if push_url else 'origin'
    safe_date = biz_today.replace('-', '_')
    patterns = [os.path.join('data','daily_bovada', f'*{safe_date}*.json')]
    files = []
    for pat in patterns:
        files.extend(glob.glob(pat))
    if not files:
        return {**out, 'added': 0, 'committed': False, 'pushed': False, 'note': 'no files matched'}
    sp.run(['git','add'] + files, check=False)
    status = sp.run(['git','status','--porcelain'], capture_output=True, text=True, check=False)
    if status.stdout.strip():
        msg = f"Automation: pitcher props update {biz_today}"
        sp.run(['git','commit','-m', msg], check=False)
        p = sp.run(['git','push', remote], capture_output=True, text=True, check=False)
        return {**out, 'added': len(files), 'committed': True, 'pushed': p.returncode==0, 'stdout': p.stdout[-2000:], 'stderr': p.stderr[-2000:]}
    return {**out, 'added': len(files), 'committed': False, 'pushed': False, 'note': 'no changes to commit'}


def get_business_date() -> str:
    # Try to reuse app.get_business_date if available
    try:
        import app as _app
        return _app.get_business_date()  # type: ignore
    except Exception:
        return datetime.now().strftime('%Y-%m-%d')


def main() -> int:
    started = time.time()
    biz_today = get_business_date()
    log(f"Starting pitcher props refresh for {biz_today}")
    ok, results, errors = run_refresh()
    push_info = None
    if ok:
        push_info = git_push(biz_today)
    dur = round(time.time() - started, 2)
    payload = {
        'date': biz_today,
        'success': bool(ok),
        'results': results,
        'errors': errors,
        'git_push': push_info,
        'duration_sec': dur,
    }
    print(json.dumps(payload, indent=2))
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
