#!/usr/bin/env python3
"""
Verity Analytics Manager — Synthesis & Delivery
===============================================
The final agent in the multi-agent workflow. It:

1. Reads all session artifacts (profile.json, analysis.json, cleaned_data.csv, audit_trail.json)
2. Resolves conflicts between Analyst and Auditor findings
3. Generates a structured decision memo (decision_memo.json)
4. Produces the Excel workbook (final_workbook.xlsx): Summary, Cleaned Data, Analysis, Audit Trail

Usage:
    python main.py <session-dir>
    python main.py --session-dir <session-dir> [--output <dir>] [--force]

Environment:
    VERITY_SESSIONS_DIR   base directory for session folders (default: <repo>/sessions)
"""

import argparse
import logging
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, ".."))

from _shared.jsonio import write_json  # noqa: E402
from conflict_resolver import resolve_session  # noqa: E402
from decision_memo import generate_memo  # noqa: E402
from workbook_builder import build_workbook  # noqa: E402

logging.basicConfig(level=logging.INFO, format="[%(name)s] %(levelname)s: %(message)s", stream=sys.stdout)
logger = logging.getLogger("manager")

REQUIRED = ["profile.json", "analysis.json", "cleaned_data.csv", "audit_trail.json"]


def repo_root():
    return os.path.abspath(os.path.join(HERE, "..", ".."))


def default_sessions_dir():
    return os.environ.get("VERITY_SESSIONS_DIR") or os.path.join(repo_root(), "sessions")


def resolve_session_dir(arg):
    if os.path.isabs(arg) or os.sep in arg:
        return os.path.abspath(arg)
    return os.path.join(default_sessions_dir(), arg)


def main():
    parser = argparse.ArgumentParser(description="Verity Analytics Manager — Synthesis & Delivery")
    parser.add_argument("session", nargs="?", help="Session directory (or session id)")
    parser.add_argument("--session-dir", dest="session_dir", help="Session directory (alternative to the positional argument)")
    parser.add_argument("--output", default=None, help="Output directory (defaults to the session directory)")
    parser.add_argument("--force", action="store_true", help="Run even if some upstream artifacts are missing")
    args = parser.parse_args()

    target = args.session_dir or args.session
    if not target:
        parser.error("a session directory is required")

    session_dir = resolve_session_dir(target)
    output_dir = args.output or session_dir
    os.makedirs(output_dir, exist_ok=True)

    missing = [f for f in REQUIRED if not os.path.exists(os.path.join(session_dir, f))]
    if missing and not args.force:
        logger.error(f"Missing upstream artifacts in {session_dir}: {', '.join(missing)}")
        return 1

    logger.info(f"Session directory: {session_dir}")

    logger.info("Step 1/3: Resolving Analyst / Auditor findings...")
    conflict_result = resolve_session(session_dir)
    summary = conflict_result.get("summary", {})
    if isinstance(summary, dict) and summary.get("total_findings", 0) == 0:
        # A clean dataset is a valid outcome; the customer still gets the full deliverable.
        logger.warning("No findings were recorded; the workbook will report a clean dataset.")
    write_json(os.path.join(output_dir, "conflict_resolution.json"), conflict_result)

    logger.info("Step 2/3: Generating decision memo...")
    memo = generate_memo(session_dir, conflict_result)
    memo_path = os.path.join(output_dir, "decision_memo.json")
    write_json(memo_path, memo)

    logger.info("Step 3/3: Building Excel workbook...")
    final_path = os.path.join(output_dir, "final_workbook.xlsx")
    tmp_path = os.path.join(output_dir, ".final_workbook.partial.xlsx")
    build_workbook(session_dir, memo, tmp_path)
    os.replace(tmp_path, final_path)  # never expose a half-written workbook

    print("-" * 60)
    print("  VERITY ANALYTICS — Manager Synthesis Complete")
    print(f"  Decision memo: {memo_path}")
    print(f"  Workbook:      {final_path}")
    if isinstance(summary, dict):
        print(f"  Findings: {summary.get('total_findings', 0)} "
              f"(confirmed {summary.get('confirmed', 0)}, auditor-only {summary.get('auditor_only', 0)}, "
              f"analyst-only {summary.get('analyst_only', 0)})")
    print("-" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
