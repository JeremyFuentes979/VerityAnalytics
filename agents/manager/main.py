#!/usr/bin/env python3
"""
Quorum Manager Module — Synthesis & Delivery
=============================================
The final agent in the multi-agent workflow. This module:

1. Reads all session artifacts (profile.json, analysis.json, cleaned_data.csv, audit_trail.json)
2. Resolves conflicts between Analyst and Auditor findings
3. Generates a structured decision memo (JSON)
4. Produces a polished Excel workbook (.xlsx) with:
   - Summary sheet (executive overview, key metrics, decisions)
   - Cleaned data sheet (final cleaned dataset)
   - Analysis sheet (metrics, charts, pattern findings)
   - Audit trail sheet (transparent correction record)

Usage:
    python main.py --session-dir /path/to/session
    python main.py --session-dir /path/to/session --output /path/to/output/folder

Environment:
    Set QUORUM_SESSION_DIR to override the default session directory.
"""

import argparse
import json
import logging
import os
import sys


def repo_root():
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))


def default_sessions_dir():
    env_value = os.environ.get('QUORUM_SESSIONS_DIR')
    if env_value:
        return env_value
    return os.path.join(repo_root(), 'sessions')


from conflict_resolver import resolve_session
from decision_memo import generate_memo
from workbook_builder import build_workbook

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="[%(name)s] %(levelname)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("manager")


# ── Default paths ────────────────────────────────────────────────────────────
# By convention, session artifacts live in a session directory.
# The lead / orchestrator passes this in, or it can be set via env var.
DEFAULT_SESSION_DIR = os.environ.get("QUORUM_SESSION_DIR", default_sessions_dir())


def discover_session_dir(candidate: str) -> str:
    """
    Walk up from the candidate to find a directory containing
    session artifacts. This allows flexible placement.
    """
    # Check candidate directly
    required = ["profile.json", "analysis.json", "cleaned_data.csv", "audit_trail.json"]
    if all(os.path.exists(os.path.join(candidate, f)) for f in required):
        return os.path.abspath(candidate)

    # Check if it's a parent directory — sometimes artifacts are in a subfolder
    for root, dirs, files in os.walk(candidate):
        found = all(f in files for f in required)
        if found:
            return os.path.abspath(root)

    # Return candidate anyway — caller may have partial data
    logger.warning(f"Could not find all session artifacts in {candidate}. Using as-is.")
    return os.path.abspath(candidate)


def main():
    parser = argparse.ArgumentParser(
        description="Quorum Manager — Synthesis & Delivery Module"
    )
    parser.add_argument(
        "--session-dir",
        default=DEFAULT_SESSION_DIR,
        help="Directory containing session artifacts (profile.json, analysis.json, cleaned_data.csv, audit_trail.json)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output directory for the decision memo and workbook (defaults to session-dir)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Run even if some artifacts are missing",
    )
    args = parser.parse_args()

    session_dir = discover_session_dir(args.session_dir)
    output_dir = args.output or session_dir
    os.makedirs(output_dir, exist_ok=True)

    logger.info(f"Session directory: {session_dir}")
    logger.info(f"Output directory: {output_dir}")

    # ── Step 1: Load artifacts and resolve conflicts ────────────────────────
    logger.info("Step 1/4: Loading artifacts and resolving conflicts...")
    conflict_result = resolve_session(session_dir)
    summary = conflict_result.get("summary", {})

    if not args.force:
        # Check we have at least SOME data
        total = summary.get("total_findings", 0)
        if total == 0:
            logger.error(
                "No findings detected. Are the Analyst and Auditor modules complete? "
                "Use --force to generate empty artifacts."
            )
            sys.exit(1)

    logger.info(f"Conflict resolution complete: {json.dumps(summary, indent=2)}")

    # Save conflict resolution separately
    cr_path = os.path.join(output_dir, "conflict_resolution.json")
    with open(cr_path, "w") as f:
        json.dump(conflict_result, f, indent=2)
    logger.info(f"Conflict resolution saved to {cr_path}")

    # ── Step 2: Generate decision memo ──────────────────────────────────────
    logger.info("Step 2/4: Generating decision memo...")
    memo = generate_memo(session_dir, conflict_result)

    memo_path = os.path.join(output_dir, "decision_memo.json")
    with open(memo_path, "w") as f:
        json.dump(memo, f, indent=2)
    logger.info(f"Decision memo saved to {memo_path}")

    # ── Step 3: Build Excel workbook ────────────────────────────────────────
    logger.info("Step 3/4: Building professional Excel workbook...")
    workbook_path = os.path.join(output_dir, "final_workbook.xlsx")
    build_workbook(session_dir, memo, workbook_path)
    logger.info(f"Workbook saved to {workbook_path}")

    # ── Step 4: Generate summary report ─────────────────────────────────────
    logger.info("Step 4/4: Final summary:")
    print("─" * 60)
    print("  QUORUM — Manager Synthesis Complete")
    print("─" * 60)
    print(f"  Session:       {session_dir}")
    print(f"  Artifacts:")
    print(f"    • Decision Memo:    {memo_path}")
    print(f"    • Excel Workbook:   {workbook_path}")
    print(f"    • Conflict Report:  {cr_path}")
    print(f"  Resolution Summary:")
    print(f"    • Total Findings:   {summary.get('total_findings', 0)}")
    print(f"    • Confirmed:        {summary.get('confirmed', 0)}")
    print(f"    • Auditor Only:     {summary.get('auditor_only', 0)}")
    print(f"    • Analyst Only:     {summary.get('analyst_only', 0)}")
    print(f"    • Resolutions:      {summary.get('resolutions_count', 0)}")
    print("─" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())