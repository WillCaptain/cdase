"""Integration tests: sync + messages-only hub model."""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from hub_test_support import (  # noqa: E402
    DEFAULT_TEST_PORT,
    EphemeralHub,
    run_client,
    test_app_cdase_root,
)
from machine_identity import machine_user_id, write_member_record  # noqa: E402


@unittest.skipUnless(
    (os.environ.get("CDASE_SKIP_HUB_INTEGRATION") or "").lower() not in ("1", "true", "yes"),
    "CDASE_SKIP_HUB_INTEGRATION=1",
)
class HubSyncIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.hub = EphemeralHub(port=DEFAULT_TEST_PORT)
        cls.hub_url = cls.hub.start()
        cls.root = test_app_cdase_root()
        cls.machine = "integration-test-machine"
        cls.member_path = write_member_record(
            cls.root,
            name="will",
            user_id=machine_user_id(cls.machine),
            role="lead",
        )
        cls.env = {
            "CDASE_ROOT": str(cls.root),
            "CDASE_USER": "will",
            "CDASE_HUB_URL": cls.hub_url,
            "CDASE_REPO_ID": "cdase-test-app",
            "CDASE_MACHINE_ID": cls.machine,
        }

    @classmethod
    def tearDownClass(cls):
        if cls.member_path.exists():
            cls.member_path.unlink()
        cls.hub.stop()

    def test_sync_health_and_inbox(self):
        code, data = run_client("sync", env=self.env)
        self.assertEqual(code, 0, data)
        self.assertTrue(data["hub_health"].get("ok"), data)
        self.assertIn("trust_model", data)
        self.assertIn("trusted_unread_count", data)

    def test_team_trust_model(self):
        code, data = run_client("team", env=self.env)
        self.assertEqual(code, 0, data)
        self.assertIn("trust_model", data)
        self.assertIn("new_to_you", data)
        self.assertIn("agent_brief", data)


if __name__ == "__main__":
    unittest.main()
