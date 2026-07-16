"""Unit tests for hub presence refresh logic."""

from __future__ import annotations

import unittest

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

from hub_presence import refresh_hub_presence  # noqa: E402


class RefreshHubPresenceTest(unittest.TestCase):
    def test_skips_incomplete_identity(self):
        calls: list[tuple] = []

        def fake_hub_call(hub_url, method, path, payload=None, params=None):
            calls.append((method, path))
            return {"ok": True}

        result = refresh_hub_presence(
            "http://127.0.0.1:7423",
            {"name": "will"},
            [{"name": "will", "uuid": "a227ca54"}],
            fake_hub_call,
            "test-machine",
        )
        self.assertEqual(result, {"skipped": True, "reason": "identity incomplete"})
        self.assertEqual(calls, [])

    def test_ping_when_already_registered(self):
        calls: list[tuple] = []

        def fake_hub_call(hub_url, method, path, payload=None, params=None):
            calls.append((method, path, payload))
            if path == "/ping":
                return {"ok": True, "unread": 2}
            return {"error": "unexpected"}

        user = {"name": "will", "uuid": "a227ca54", "role": "lead"}
        roster = [{"name": "will", "uuid": "a227ca54", "role": "lead"}]
        result = refresh_hub_presence(
            "http://127.0.0.1:7423", user, roster, fake_hub_call, "test-machine"
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["method"], "ping")
        self.assertEqual(result["unread"], 2)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0], "POST")
        self.assertEqual(calls[0][1], "/ping")
        self.assertEqual(calls[0][2]["uuid"], "a227ca54")

    def test_login_when_ping_unknown_user(self):
        calls: list[str] = []

        def fake_hub_call(hub_url, method, path, payload=None, params=None):
            calls.append(path)
            if path == "/ping":
                return {"error": "unknown user, login first"}
            if path == "/login":
                return {"ok": True, "unread": 0}
            return {"error": "unexpected"}

        user = {"name": "will", "uuid": "a227ca54", "role": "lead"}
        roster = [{"name": "will", "uuid": "a227ca54", "role": "lead"}]
        result = refresh_hub_presence(
            "http://127.0.0.1:7423", user, roster, fake_hub_call, "test-machine"
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["method"], "login")
        self.assertEqual(calls, ["/ping", "/login"])

    def test_reports_hub_unreachable(self):
        def fake_hub_call(hub_url, method, path, payload=None, params=None):
            return {"error": "hub unreachable", "offline_ok": True}

        user = {"name": "will", "uuid": "a227ca54"}
        roster = [{"name": "will", "uuid": "a227ca54"}]
        result = refresh_hub_presence(
            "http://127.0.0.1:7423", user, roster, fake_hub_call, "test-machine"
        )
        self.assertFalse(result["ok"])
        self.assertIn("error", result)


if __name__ == "__main__":
    unittest.main()
