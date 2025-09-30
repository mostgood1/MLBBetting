#!/usr/bin/env python3
"""
Repo temp artifacts cleanup
- Finds old daily automation logs, tmp/bak files, and other scratch artifacts
- Default is dry-run; pass --yes to actually delete
- Keeps the most recent N automation logs and any from today
"""
import argparse
import sys
from pathlib import Path
import fnmatch
import datetime
import os

KEEP_RECENT_LOGS = 5
AUTOMATION_LOG_PREFIX = "complete_daily_automation_"

PATTERNS = [
    # High-confidence temp/scratch
    "*.tmp",
    "*.json.tmp",
    "*.bak",
    "tmp_*",
    # Logs (handle automation logs specially below)
    "*.log",
]

EXCLUDE_DIRS = {
    ".git", ".venv", ".idea", ".vscode", "node_modules",
    # avoid wiping structured data by pattern accidents
    "data", "models",
}


def is_today(p: Path) -> bool:
    try:
        today = datetime.datetime.now().date()
        mtime = datetime.datetime.fromtimestamp(p.stat().st_mtime).date()
        # also check filename contains today's date for the automation logs
        return mtime == today
    except Exception:
        return False


def find_automation_logs(root: Path):
    logs = []
    for p in root.glob(f"{AUTOMATION_LOG_PREFIX}*.log"):
        if p.is_file():
            logs.append(p)
    return sorted(logs, key=lambda x: x.stat().st_mtime, reverse=True)


def walk_patterns(root: Path):
    for dirpath, dirnames, filenames in os.walk(root):
        # prune excluded directories
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        # yield files matching any pattern
        for fname in filenames:
            fpath = Path(dirpath) / fname
            for pat in PATTERNS:
                if fnmatch.fnmatch(fname, pat):
                    yield fpath
                    break


def main():
    ap = argparse.ArgumentParser(description="Clean temporary artifacts from the repo")
    ap.add_argument("--yes", action="store_true", help="Apply deletions (default is dry-run)")
    ap.add_argument("--root", type=str, default=str(Path(__file__).resolve().parents[2]), help="Repo root")
    ap.add_argument("--keep-logs", type=int, default=KEEP_RECENT_LOGS, help="How many recent automation logs to keep")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    if not root.exists():
        print(f"Repo root not found: {root}", file=sys.stderr)
        return 2

    candidates = set()

    # Collect generic temp matches
    for f in walk_patterns(root):
        candidates.add(f)

    # Handle automation logs: keep N most recent and any from today
    auto_logs = find_automation_logs(root)
    keep_set = set(auto_logs[: max(args.keep_logs, 0)])
    keep_set.update([p for p in auto_logs if is_today(p)])

    delete_list = []
    total_bytes = 0
    for f in sorted(candidates):
        # If it's a .log but not an automation log, we still consider deletion,
        # but prefer to keep logs under a logs/ dir for user inspection
        if f.name.endswith('.log'):
            if f.name.startswith(AUTOMATION_LOG_PREFIX):
                if f in keep_set:
                    continue
            # If file is inside a logs/ folder, skip by default (user-curated)
            if any(part.lower() == 'logs' for part in f.parts):
                continue
        try:
            sz = f.stat().st_size
        except FileNotFoundError:
            continue
        delete_list.append(f)
        total_bytes += sz

    mode = "APPLY" if args.yes else "DRY-RUN"
    print(f"{mode}: {len(delete_list)} files would be deleted, total size ~{total_bytes/1024:.1f} KiB")
    for f in delete_list:
        print(f" - {f.relative_to(root)}")

    if not args.yes:
        print("\nNothing deleted (dry-run). Re-run with --yes to apply.")
        return 0

    # Apply deletions
    deleted = 0
    errors = 0
    for f in delete_list:
        try:
            f.unlink(missing_ok=True)
            deleted += 1
        except Exception as e:
            print(f"Failed to delete {f}: {e}", file=sys.stderr)
            errors += 1

    print(f"Deleted {deleted} files; {errors} errors")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
