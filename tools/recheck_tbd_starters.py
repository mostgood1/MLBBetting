import json
import os
import subprocess
import sys
import time
from datetime import datetime


def load_tbd_games(date_str: str):
    """Return list of games with TBD pitchers for the given date (YYYY-MM-DD)."""
    path = os.path.join('data', f"starting_pitchers_{date_str.replace('-', '_')}.json")
    if not os.path.exists(path):
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        games = data.get('games', [])
        tbd = [g for g in games if (g.get('away_pitcher', 'TBD') == 'TBD' or g.get('home_pitcher', 'TBD') == 'TBD')]
        return tbd
    except Exception:
        return None


def append_log(log_path: str, line: str) -> None:
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(f"[{ts}] {line}\n")


def main():
    # Config via args: interval seconds, max attempts
    # Usage: python tools/recheck_tbd_starters.py [interval_sec] [max_attempts]
    interval = int(sys.argv[1]) if len(sys.argv) > 1 else 900  # 15 minutes
    max_attempts = int(sys.argv[2]) if len(sys.argv) > 2 else 12  # 3 hours

    today = datetime.now().strftime('%Y-%m-%d')
    log_path = os.path.join('data', f'tbd_recheck_{today}.log')
    append_log(log_path, f"Starting TBD recheck loop (interval={interval}s, max_attempts={max_attempts})")

    # Initialize baseline TBD set
    baseline = load_tbd_games(today) or []
    prev_tbd = {(g.get('away_team'), g.get('home_team')) for g in baseline}
    append_log(log_path, f"Initial TBD count: {len(prev_tbd)} -> {sorted(list(prev_tbd))}")

    for i in range(1, max_attempts + 1):
        # Re-fetch starters
        try:
            result = subprocess.run(
                [sys.executable, 'fetch_todays_starters.py'],
                capture_output=True,
                text=True,
                cwd=os.getcwd()
            )
            if result.stdout:
                append_log(log_path, result.stdout.strip())
            if result.stderr:
                append_log(log_path, f"STDERR: {result.stderr.strip()}")
        except Exception as e:
            append_log(log_path, f"Error running fetch_todays_starters.py: {e}")

        # Count TBDs and detect resolved matchups
        current = load_tbd_games(today) or []
        current_tbd = {(g.get('away_team'), g.get('home_team')) for g in current}
        resolved = prev_tbd - current_tbd
        append_log(log_path, f"Attempt {i}: TBD remaining: {len(current_tbd)}")

        # If any matchups resolved, regenerate today's predictions and recommendations
        if resolved:
            pretty = ", ".join([f"{a} @ {h}" for a, h in sorted(list(resolved))])
            append_log(log_path, f"Resolved TBD matchups: {pretty}. Regenerating predictions/recommendations for today...")
            try:
                pr = subprocess.run([sys.executable, 'daily_ultrafastengine_predictions.py', '--date', today], capture_output=True, text=True)
                append_log(log_path, pr.stdout.strip())
                if pr.stderr:
                    append_log(log_path, f"STDERR (predictions): {pr.stderr.strip()}")
            except Exception as e:
                append_log(log_path, f"Error running daily_ultrafastengine_predictions.py: {e}")
            try:
                rr = subprocess.run([sys.executable, 'betting_recommendations_engine.py', '--date', today], capture_output=True, text=True)
                append_log(log_path, rr.stdout.strip())
                if rr.stderr:
                    append_log(log_path, f"STDERR (recommendations): {rr.stderr.strip()}")
            except Exception as e:
                append_log(log_path, f"Error running betting_recommendations_engine.py: {e}")

        prev_tbd = current_tbd

        if len(current_tbd) == 0:
            append_log(log_path, "All TBDs resolved. Exiting.")
            print("All TBDs resolved. Exiting.")
            return 0

        if i < max_attempts:
            time.sleep(interval)

    append_log(log_path, "Max attempts reached. Some TBDs may remain.")
    print("Max attempts reached. Some TBDs may remain.")
    return 1


if __name__ == '__main__':
    sys.exit(main())
