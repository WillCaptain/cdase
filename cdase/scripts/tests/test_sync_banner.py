"""Unit tests for compact sync banner."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

from hub_sync import build_sync_banner  # noqa: E402


class SyncBannerTest(unittest.TestCase):
    def test_all_clear_returns_none(self):
        sync = {
            "identity_ok": True,
            "hub_health": {"ok": True},
            "hub_warning": None,
            "trusted_unread_count": 0,
            "unknown_unread_count": 0,
            "trusted_messages": [],
            "unknown_messages": [],
        }
        self.assertIsNone(
            build_sync_banner(sync, workspace_short="aintegration", workspace_full="/long/path/aintegration")
        )

    def test_hub_offline_compact(self):
        sync = {
            "identity_ok": True,
            "hub_health": {"error": "refused"},
            "hub_warning": {"short_message": "hub offline (http://127.0.0.1:7423)"},
            "trusted_unread_count": 0,
            "unknown_unread_count": 0,
            "trusted_messages": [],
            "unknown_messages": [],
        }
        banner = build_sync_banner(sync, workspace_short="aintegration", workspace_full="/x/aintegration")
        self.assertIsNotNone(banner)
        self.assertIn("workspace:aintegration", banner)
        self.assertIn("hub offline", banner)
        self.assertNotIn("Connection refused", banner)  # no verbose dump in banner

    def test_unread_shows_count(self):
        sync = {
            "identity_ok": True,
            "hub_health": {"ok": True},
            "hub_warning": None,
            "trusted_unread_count": 1,
            "unknown_unread_count": 0,
            "trusted_messages": [{"from": "will", "subject": "blocked on API", "body": "", "read": False}],
            "unknown_messages": [],
        }
        banner = build_sync_banner(sync, workspace_short="aintegration", workspace_full="/x/aintegration")
        self.assertIn("1 trusted unread", banner)


if __name__ == "__main__":
    unittest.main()
