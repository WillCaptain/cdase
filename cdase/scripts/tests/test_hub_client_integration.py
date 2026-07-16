"""Integration tests: hub tools auto-refresh presence and team shows online."""

from __future__ import annotations

import os
import unittest

from hub_test_support import (
    DEFAULT_TEST_PORT,
    EphemeralHub,
    hub_health,
    run_client,
    test_app_cdase_root,
)


@unittest.skipUnless(
    (os.environ.get("CDASE_SKIP_HUB_INTEGRATION") or "").lower() not in ("1", "true", "yes"),
    "CDASE_SKIP_HUB_INTEGRATION=1",
)
class HubClientIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.hub = EphemeralHub(port=DEFAULT_TEST_PORT)
        cls.hub_url = cls.hub.start()
        cls.env = {
            "CDASE_ROOT": str(test_app_cdase_root()),
            "CDASE_USER": "will",
            "CDASE_HUB_URL": cls.hub_url,
            "CDASE_REPO_ID": "cdase-test-app",
            "CDASE_MACHINE_ID": "integration-test-machine",
        }

    @classmethod
    def tearDownClass(cls):
        cls.hub.stop()

    def test_check_hits_hub_and_refreshes_presence(self):
        code, data = run_client("check", env=self.env)
        self.assertEqual(code, 0, data)
        self.assertTrue(data["hub_health"].get("ok"), data["hub_health"])
        presence = data["hub_presence"]
        self.assertTrue(presence.get("ok"), presence)
        self.assertIn(presence["method"], ("ping", "login"))
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
        presence = data["hub_presence"]
        self.assertTrue(presence.get("ok"), presence)
        self.assertIn("agent_brief", data)
        self.assertTrue(data.get("must_use_agent_brief"))

        will_rows = [m for m in data["members"] if m["name"] == "will" and m["in_roster"]]
        self.assertEqual(len(will_rows), 1, data["members"])
        self.assertEqual(will_rows[0]["status"], "online", will_rows[0])

    def test_second_team_uses_ping_not_only_login(self):
        run_client("team", env=self.env)
        code, data = run_client("check", env=self.env)
        self.assertEqual(code, 0, data)
        self.assertEqual(data["hub_presence"].get("method"), "ping")

    def test_hub_users_list_includes_active_will(self):
        run_client("team", env=self.env)
        code, data = run_client("users", env=self.env)
        self.assertEqual(code, 0, data)
        will = next(u for u in data["users"] if u.get("name") == "will")
        self.assertTrue(will.get("active"), will)


class HubHealthGuardTest(unittest.TestCase):
    """Fast sanity check that default hub URL responds when a server is already up."""

    def test_default_hub_health_optional(self):
        health = hub_health("http://127.0.0.1:7423")
        if health is None:
            self.skipTest("no hub on :7423 — integration suite starts its own ephemeral hub")
        self.assertTrue(health.get("ok"))


if __name__ == "__main__":
    unittest.main()
