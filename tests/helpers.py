import json
import os
import shutil
import sys
import tempfile
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, REPO_ROOT)

from workflow import orchestrator  # noqa: E402


def strict_json(path):
    """Load JSON the way a browser would: NaN / Infinity are errors."""
    def reject(token):
        raise ValueError(f"non-standard JSON constant {token} in {path}")
    with open(path, encoding="utf-8") as f:
        return json.load(f, parse_constant=reject)


class SessionTestCase(unittest.TestCase):
    """Runs agents against a throwaway sessions directory."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="verity-test-")
        self._env = dict(os.environ)
        os.environ["VERITY_SESSIONS_DIR"] = self.tmp
        os.environ["VERITY_PYTHON"] = sys.executable
        os.environ.pop("VERITY_ALLOW_UNPAID", None)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def make_session(self, name, filename, content, paid=False):
        session_dir = os.path.join(self.tmp, name)
        os.makedirs(session_dir)
        mode = "wb" if isinstance(content, bytes) else "w"
        with open(os.path.join(session_dir, filename), mode) as f:
            f.write(content)
        session = {"sessionId": name, "fileName": filename, "status": "uploaded"}
        if paid:
            session["paidAt"] = "2026-01-01T00:00:00Z"
        with open(os.path.join(session_dir, "session.json"), "w") as f:
            json.dump(session, f)
        return session_dir

    def session(self, session_dir):
        return strict_json(os.path.join(session_dir, "session.json"))
