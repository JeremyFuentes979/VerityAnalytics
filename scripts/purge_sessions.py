#!/usr/bin/env python3
"""Delete old session folders (uploaded customer data).

    python3 scripts/purge_sessions.py --days 30            # dry run: lists what would go
    python3 scripts/purge_sessions.py --days 30 --delete   # actually delete

A session's age is the time of its last update. Sessions that are currently running
are never touched. Run it from cron/launchd so customer files don't pile up.
"""

import argparse
import os
import shutil
import sys
import time

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RUNNING = ("queued", "running_")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--days", type=float, default=30, help="delete sessions not updated for this many days")
    parser.add_argument("--delete", action="store_true", help="really delete (default is a dry run)")
    parser.add_argument("--sessions-dir", default=os.environ.get("VERITY_SESSIONS_DIR") or os.path.join(REPO_ROOT, "sessions"))
    args = parser.parse_args()

    if not os.path.isdir(args.sessions_dir):
        print(f"No sessions directory at {args.sessions_dir}")
        return 0

    cutoff = time.time() - args.days * 86400
    removed = 0
    for name in sorted(os.listdir(args.sessions_dir)):
        path = os.path.join(args.sessions_dir, name)
        if not os.path.isdir(path) or os.path.islink(path):
            continue
        newest = max((os.path.getmtime(os.path.join(root, f)) for root, _, files in os.walk(path) for f in files),
                     default=os.path.getmtime(path))
        if newest >= cutoff:
            continue
        try:
            import json
            with open(os.path.join(path, "session.json")) as f:
                status = json.load(f).get("status", "")
        except (OSError, ValueError):
            status = ""
        if status.startswith(RUNNING):
            continue
        age = (time.time() - newest) / 86400
        print(f"{'DELETE' if args.delete else 'would delete'}  {name}  ({age:.0f} days old, status={status or 'unknown'})")
        if args.delete:
            shutil.rmtree(path)
        removed += 1
    print(f"{removed} session(s) {'deleted' if args.delete else 'would be deleted'}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
