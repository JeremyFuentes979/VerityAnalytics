import os
import unittest

from workflow import orchestrator


class LocalPathResolutionTests(unittest.TestCase):
    def test_resolve_shared_dir_falls_back_to_repo_root(self):
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        resolved = orchestrator.resolve_shared_dir()
        self.assertTrue(os.path.isdir(resolved))
        self.assertIn("Quorum", resolved)
        self.assertTrue(os.path.exists(os.path.join(resolved, "agents")))

    def test_default_session_dir_is_repo_relative(self):
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        default_dir = orchestrator.default_sessions_dir()
        self.assertEqual(default_dir, os.path.join(repo_root, "sessions"))


if __name__ == "__main__":
    unittest.main()
