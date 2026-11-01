#!/usr/bin/env python3
"""
Verity Analytics workflow orchestrator.

Usage:
    python orchestrator.py <session-id-or-dir> [--stage profile|full]

Stages
    profile  Researcher only. Free; runs right after upload to produce the preview.
    full     Researcher (if needed) -> Analyst -> Auditor -> Manager. Paid; refuses to
             run unless session.json carries a `paidAt` timestamp.

Session status written to session.json:
    uploaded -> profiling -> profiled | profile_error
    paid -> running_<agent> ... -> complete | error
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
AGENTS_DIR = os.path.join(REPO_ROOT, "agents")
SESSION_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def resolve_shared_dir():
    """Directory that contains agents/ (the repo root unless overridden)."""
    return os.environ.get("VERITY_SHARED_DIR") or REPO_ROOT


def default_sessions_dir():
    return os.environ.get("VERITY_SESSIONS_DIR") or os.path.join(resolve_shared_dir(), "sessions")


def agent_script(*parts):
    return os.path.join(resolve_shared_dir(), "agents", *parts)


def python_executable():
    explicit = os.environ.get("VERITY_PYTHON")
    if explicit:
        return explicit
    venv = os.path.join(REPO_ROOT, ".venv", "bin", "python")
    return venv if os.path.exists(venv) else sys.executable


RESEARCHER = {"name": "Researcher", "script": ("researcher", "main.py"), "output": "profile.json", "timeout": 180}
FULL_AGENTS = [
    {"name": "Analyst", "script": ("analyst", "analyst.py"), "output": "analysis.json", "timeout": 300},
    {"name": "Auditor", "script": ("auditor", "auditor.py"), "output": "audit_trail.json", "timeout": 300},
    {"name": "Manager", "script": ("manager", "main.py"), "output": "final_workbook.xlsx", "timeout": 900},
]


# -- session.json helpers ------------------------------------------------------

def session_path(session_dir):
    return os.path.join(session_dir, "session.json")


def read_session(session_dir):
    try:
        with open(session_path(session_dir), "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def write_session(session_dir, session):
    fd, tmp = tempfile.mkstemp(dir=session_dir, prefix=".session-", suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(session, f, indent=2)
    os.replace(tmp, session_path(session_dir))


def update_session(session_dir, status=None, detail=None, **fields):
    session = read_session(session_dir)
    if status is not None:
        session["status"] = status
    if detail is not None:
        session["detail"] = detail
    session.update(fields)
    session["updatedAt"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    write_session(session_dir, session)


# -- locking -------------------------------------------------------------------

def _pid_alive(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def acquire_lock(session_dir):
    lock = os.path.join(session_dir, ".workflow.lock")
    for _ in range(2):
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(os.getpid()).encode())
            os.close(fd)
            return lock
        except FileExistsError:
            try:
                with open(lock) as f:
                    owner = int(f.read().strip() or 0)
            except (OSError, ValueError):
                owner = 0
            if owner and _pid_alive(owner):
                return None
            try:
                os.unlink(lock)  # stale lock from a crashed run
            except OSError:
                return None
    return None


def release_lock(lock):
    try:
        os.unlink(lock)
    except OSError:
        pass


# -- running agents ------------------------------------------------------------

def run_agent(agent, session_dir):
    """Run one agent. Returns (ok, seconds, message)."""
    name = agent["name"]
    script = agent_script(*agent["script"])
    print(f"\n{'=' * 60}\n  Running: {name}\n  Script:  {script}\n{'=' * 60}", flush=True)

    if not os.path.exists(script):
        return False, 0.0, f"{name} script not found"

    started = time.time()
    try:
        result = subprocess.run(
            [python_executable(), script, session_dir],
            capture_output=True, text=True, timeout=agent["timeout"], env=os.environ.copy(),
        )
    except subprocess.TimeoutExpired:
        return False, time.time() - started, f"{name} timed out after {agent['timeout']}s"
    except Exception as exc:  # noqa: BLE001
        return False, time.time() - started, f"{name} could not start: {exc}"

    elapsed = time.time() - started
    if result.stdout:
        print(result.stdout[-2000:].rstrip(), flush=True)
    if result.returncode != 0:
        if result.stderr:
            print(result.stderr[-2000:].rstrip(), flush=True)
        last = (result.stdout.strip().splitlines() or ["no output"])[-1]
        return False, elapsed, f"{name} failed: {last}"
    return True, elapsed, ""


def profile_error_message(session_dir):
    try:
        with open(os.path.join(session_dir, "profile_error.json"), encoding="utf-8") as f:
            return json.load(f).get("message") or "The file could not be read."
    except (OSError, ValueError):
        return "The file could not be read."


def run_profile(session_dir):
    update_session(session_dir, "profiling", "Researcher is profiling your data")
    ok, seconds, message = run_agent(RESEARCHER, session_dir)
    timings = read_session(session_dir).get("agentSeconds", {})
    timings["Researcher"] = round(seconds, 2)
    if ok:
        update_session(session_dir, "profiled", "Profile ready", agentSeconds=timings)
        return True
    update_session(session_dir, "profile_error", profile_error_message(session_dir) or message, agentSeconds=timings)
    return False


def run_full(session_dir, require_payment=True):
    session = read_session(session_dir)
    if require_payment and not session.get("paidAt") and os.environ.get("VERITY_ALLOW_UNPAID") != "1":
        print("REFUSED: this session has not been paid for.", flush=True)
        return False

    started = time.time()
    timings = dict(session.get("agentSeconds", {}))
    update_session(session_dir, "running_researcher" if not os.path.exists(os.path.join(session_dir, "profile.json")) else "queued",
                   "Workflow starting", workflowStartedAt=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))

    agents = list(FULL_AGENTS)
    if not os.path.exists(os.path.join(session_dir, "profile.json")):
        agents.insert(0, RESEARCHER)

    for agent in agents:
        update_session(session_dir, f"running_{agent['name'].lower()}", f"{agent['name']} is working")
        ok, seconds, message = run_agent(agent, session_dir)
        timings[agent["name"]] = round(seconds, 2)
        if not ok:
            update_session(session_dir, "error", message, agentSeconds=timings)
            print(f"\n  FAILED at {agent['name']}: {message}", flush=True)
            return False

    update_session(session_dir, "complete", "All agents finished successfully",
                   agentSeconds=timings, totalSeconds=round(time.time() - started, 2),
                   completedAt=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    print("\n  WORKFLOW COMPLETE", flush=True)
    return True


def resolve_session_dir(arg):
    if os.path.isabs(arg):
        return os.path.abspath(arg)
    if not SESSION_ID_RE.match(arg):
        raise ValueError(f"Invalid session id: {arg!r}")
    return os.path.join(default_sessions_dir(), arg)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Verity Analytics workflow orchestrator")
    parser.add_argument("session", help="session id or session directory")
    parser.add_argument("--stage", choices=["profile", "full"], default="full")
    args = parser.parse_args(argv)

    try:
        session_dir = resolve_session_dir(args.session)
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 2
    if not os.path.isdir(session_dir):
        print(f"ERROR: session not found: {session_dir}")
        return 2

    lock = acquire_lock(session_dir)
    if lock is None:
        print("Another workflow is already running for this session; exiting.")
        return 0
    try:
        print(f"VERITY ANALYTICS ORCHESTRATOR  stage={args.stage}  session={os.path.basename(session_dir)}", flush=True)
        ok = run_profile(session_dir) if args.stage == "profile" else run_full(session_dir)
        return 0 if ok else 1
    finally:
        release_lock(lock)


if __name__ == "__main__":
    sys.exit(main())
