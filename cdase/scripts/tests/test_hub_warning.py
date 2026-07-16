"""Unit tests for hub-down warning builder."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

from hub_warning import build_hub_warning  # noqa: E402


class BuildHubWarningTest(unittest.TestCase):
    def test_none_when_hub_up(self):
        self.assertIsNone(
            build_hub_warning("http://127.0.0.1:7423", {"ok": True}, offline_ok=True)
        )

    def test_warning_when_hub_down_offline_ok(self):
        warn = build_hub_warning(
            "http://127.0.0.1:7423",
            {"error": "connection refused"},
            offline_ok=True,
        )
        self.assertIsNotNone(warn)
        self.assertTrue(warn["show_to_user"])
        self.assertIn("unreachable", warn["message"])
        self.assertIn("connection refused", warn["message"])
        self.assertTrue(warn["offline_ok"])
        self.assertIn("show hub_warning.message", warn["agent_rule"])

    def test_warning_when_hub_down_offline_not_ok(self):
        warn = build_hub_warning(
            "http://127.0.0.1:7423",
            {"error": "connection refused"},
            offline_ok=False,
        )
        self.assertIsNotNone(warn)
        self.assertFalse(warn["offline_ok"])
        self.assertIn("blocked", warn["message"])


if __name__ == "__main__":
    unittest.main()
