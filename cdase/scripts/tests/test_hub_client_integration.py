"""Integration tests: hub tools auto-refresh presence and team shows online."""

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
    hub_health,
    run_client,
    test_app_cdase_root,
)
from machine_identity import machine_user_id, write_member_record  # noqa: E402


@unittest.skipUnless(
    (os.environ.get("CDASE_SKIP_HUB_INTEGRATION") or "").lower() not in ("1", "true", "yes"),
    "CDASE_SKIP_HUB_INTEGRATION=1",
)
class HubClientIntegrationTest(unittest.TestCase):
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

    def test_check_hits_hub_health_without_presence_side_effect(self):
        code, data = run_client("check", env=self.env)
        self.assertEqual(code, 0, data)
        self.assertTrue(data["hub_health"].get("ok"), data["hub_health"])
        self.assertNotIn("hub_presence", data)
        self.assertIsNone(data.get("hub_warning"))

    def test_check_hub_warning_when_hub_unreachable(self):
        bad_env = {**self.env, "CDASE_HUB_URL": "http://127.0.0.1:1"}
        code, data = run_client("check", env=bad_env)
        warn = data.get("hub_warning")
        self.assertIsNotNone(warn, data)
        self.assertTrue(warn["show_to_user"])
        self.assertIn("unreachable", warn["message"])

    def test_team_without_explicit_login_shows_will_online(self):
        code, data = run_client("team", env=self.env)
        self.assertEqual(code, 0, data)
        self.assertTrue(data["hub_online"], data)
        self.assertIn("agent_brief", data)
        self.assertTrue(data.get("must_use_agent_brief"))

        expected_id = machine_user_id(self.machine)
        will_rows = [
            m for m in data["members"]
            if m["uuid"] == expected_id and m["in_roster"]
        ]
        self.assertEqual(len(will_rows), 1, data["members"])
        self.assertEqual(will_rows[0]["name"], "will")
        self.assertEqual(will_rows[0]["status"], "online", will_rows[0])

    def test_second_team_uses_ping_not_only_login(self):
        run_client("team", env=self.env)
        code, data = run_client("sync", env=self.env)
        self.assertEqual(code, 0, data)
        self.assertEqual(data["hub_presence"].get("method"), "ping")

    def test_hub_users_list_includes_active_will(self):
        run_client("team", env=self.env)
        code, data = run_client("users", env=self.env)
        self.assertEqual(code, 0, data)
        will = next(u for u in data["users"] if u.get("name") == "will")
        self.assertTrue(will.get("active"), will)


class HubHealthGuardTest(unittest.TestCase):
    def test_hub_health_helper(self):
        with EphemeralHub(port=DEFAULT_TEST_PORT + 50) as url:
            self.assertTrue(hub_health(url))


if __name__ == "__main__":
    unittest.main()
