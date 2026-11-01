import os
import unittest

from tests.helpers import REPO_ROOT, orchestrator


class PathResolutionTests(unittest.TestCase):
    def test_shared_dir_is_the_repo_and_contains_agents(self):
        resolved = orchestrator.resolve_shared_dir()
        self.assertEqual(os.path.realpath(resolved), os.path.realpath(REPO_ROOT))
        self.assertTrue(os.path.isdir(os.path.join(resolved, "agents")))

    def test_every_agent_script_exists(self):
        agents = [orchestrator.RESEARCHER] + orchestrator.FULL_AGENTS
        for agent in agents:
            self.assertTrue(os.path.exists(orchestrator.agent_script(*agent["script"])), agent["name"])

    def test_sessions_dir_env_override(self):
        old = os.environ.get("VERITY_SESSIONS_DIR")
        os.environ["VERITY_SESSIONS_DIR"] = "/tmp/somewhere"
        try:
            self.assertEqual(orchestrator.default_sessions_dir(), "/tmp/somewhere")
        finally:
            if old is None:
                del os.environ["VERITY_SESSIONS_DIR"]
            else:
                os.environ["VERITY_SESSIONS_DIR"] = old

    def test_session_id_validation_rejects_traversal(self):
        for bad in ("../etc", "a b", "x;rm -rf", "", "a" * 65):
            with self.assertRaises(ValueError, msg=bad):
                orchestrator.resolve_session_dir(bad)


if __name__ == "__main__":
    unittest.main()
