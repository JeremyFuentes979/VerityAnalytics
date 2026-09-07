#!/usr/bin/env python3
"""
Quorum Workflow Orchestrator
Chains all four agents in sequence for a given session.
Usage: python3 orchestrator.py <session-id>
"""

import json
import os
import subprocess
import sys
import time


def resolve_shared_dir():
    """Prefer the deployment path when available, otherwise use the local repo checkout."""
    env_value = os.environ.get('QUORUM_SHARED_DIR')
    if env_value:
        return env_value
    if os.path.exists('/home/team/shared'):
        return '/home/team/shared'
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


def default_sessions_dir():
    """Return a repo-local default for sessions when running outside the deployment server."""
    env_value = os.environ.get('QUORUM_SESSIONS_DIR')
    if env_value:
        return env_value
    repo_root = resolve_shared_dir()
    return os.path.join(repo_root, 'sessions')


SHARED_DIR = resolve_shared_dir()
SESSIONS_DIR = default_sessions_dir()

AGENTS = [
    {
        'name': 'Researcher',
        'script': os.path.join(SHARED_DIR, 'researcher', 'main.py'),
        'output': 'profile.json',
        'timeout': 120,
    },
    {
        'name': 'Analyst',
        'script': os.path.join(SHARED_DIR, 'analyst', 'analyst.py'),
        'output': 'analysis.json',
        'timeout': 180,
    },
    {
        'name': 'Auditor',
        'script': os.path.join(SHARED_DIR, 'auditor', 'auditor.py'),
        'output': 'audit_trail.json',
        'timeout': 180,
    },
    {
        'name': 'Manager',
        'script': os.path.join(SHARED_DIR, 'manager', 'main.py'),
        'output': 'final_workbook.xlsx',
        'timeout': 300,
    },
]


def update_session_status(session_id: str, status: str, detail: str = ''):
    """Update the session.json status field."""
    session_path = os.path.join(SESSIONS_DIR, session_id, 'session.json')
    try:
        with open(session_path, 'r') as f:
            session = json.load(f)
        session['status'] = status
        session['updatedAt'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        if detail:
            session['detail'] = detail
        with open(session_path, 'w') as f:
            json.dump(session, f, indent=2)
    except Exception as e:
        print(f"  [WARN] Could not update session status: {e}")


def run_agent(agent, session_id: str) -> bool:
    """Run a single agent's script. Returns True on success."""
    name = agent['name']
    script = agent['script']
    output = agent['output']
    session_dir = os.path.join(SESSIONS_DIR, session_id)

    print(f"\n{'='*60}")
    print(f"  Running: {name}")
    print(f"  Script:  {script}")
    print(f"  Output:  {os.path.join(session_dir, output)}")
    print(f"{'='*60}")

    if not os.path.exists(script):
        print(f"  [ERROR] Script not found: {script}")
        return False

    # Check if venv exists for Manager
    env = os.environ.copy()
    manager_venv = os.path.join(SHARED_DIR, 'manager', 'venv', 'bin', 'python3')
    if name == 'Manager' and os.path.exists(manager_venv):
        python_cmd = manager_venv
    else:
        python_cmd = 'python3'

    # Build command
    cmd = [python_cmd, script, session_dir]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=agent['timeout'],
            env=env,
        )
        
        if result.returncode == 0:
            print(f"  ✅ {name} completed successfully")
            if result.stdout:
                for line in result.stdout.strip().split('\n')[-5:]:
                    print(f"     {line}")
            return True
        else:
            print(f"  ❌ {name} failed (exit code: {result.returncode})")
            if result.stdout:
                print(f"     stdout: {result.stdout[-500:].strip()}")
            if result.stderr:
                print(f"     stderr: {result.stderr[-500:].strip()}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"  ⏰ {name} timed out after {agent['timeout']}s")
        return False
    except Exception as e:
        print(f"  💥 {name} error: {e}")
        return False


def run_full_workflow(session_id: str) -> bool:
    """Run the full multi-agent workflow for a session."""
    print(f"\n{'#'*60}")
    print(f"  QUORUM WORKFLOW ORCHESTRATOR")
    print(f"  Session: {session_id}")
    print(f"{'#'*60}")

    update_session_status(session_id, 'hired', 'Workflow starting')

    for i, agent in enumerate(AGENTS):
        update_session_status(session_id, f'running_{agent["name"].lower()}', f'{agent["name"]} is working')
        
        success = run_agent(agent, session_id)
        if not success:
            update_session_status(session_id, 'error', f'{agent["name"]} failed')
            print(f"\n  ❌ Workflow failed at step: {agent['name']}")
            return False

    update_session_status(session_id, 'complete', 'All agents finished successfully')
    print(f"\n{'#'*60}")
    print(f"  ✅ WORKFLOW COMPLETE")
    print(f"  Session: {session_id}")
    print(f"{'#'*60}")
    return True


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python3 orchestrator.py <session-id>')
        sys.exit(1)
    
    session_id = sys.argv[1]
    success = run_full_workflow(session_id)
    sys.exit(0 if success else 1)