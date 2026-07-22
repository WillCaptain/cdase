#!/usr/bin/env python3
"""Unit tests for zero-to-start boot journey and hub URL gating."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from boot_journey import build_boot_journey
from context_loader import hub_url_state, load_settings
from machine_identity import write_member_record


class HubUrlStateTests(unittest.TestCase):
    def test_default_only_blocks_hub_tools(self):
        settings = {
            "hub_address": "http://127.0.0.1:7423",
            "sources": ["defaults"],
        }
        state = hub_url_state(settings)
        self.assertFalse(state["hub_tools_allowed"])
        self.assertFalse(state["configured"])

    def test_global_setting_allows_hub_tools(self):
        settings = {
            "hub_address": "http://127.0.0.1:7423",
            "sources": ["global"],
        }
        state = hub_url_state(settings)
        self.assertTrue(state["hub_tools_allowed"])
        self.assertEqual(state["address"], "http://127.0.0.1:7423")

    def test_env_override_allows_hub_tools(self):
        settings = {
            "hub_address": "http://10.0.0.5:7423",
            "sources": ["defaults", "CDASE_HUB_URL"],
        }
        state = hub_url_state(settings)
        self.assertTrue(state["hub_tools_allowed"])


class BootJourneyTests(unittest.TestCase):
    def _settings(self, *, sources: list[str], address: str = "http://127.0.0.1:7423") -> dict:
        return {
            "hub_address": address,
            "sources": sources,
            "source": "+".join(sources),
        }

    def test_blocks_hub_until_url_configured(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "cdase"
            (root / "context").mkdir(parents=True)
            write_member_record(root, name="evan", user_id="39cb62d4", role="lead")
            journey = build_boot_journey(
                identity_ok=False,
                settings=self._settings(sources=["defaults"]),
                cdase_root=root,
                errors=["identity name missing"],
            )
            self.assertTrue(journey["hub_tools_blocked"])
            self.assertEqual(journey["next_step"]["id"], "user_profile")

    def test_ready_for_sync_when_profile_and_url_set(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "cdase"
            (root / "context").mkdir(parents=True)
            write_member_record(root, name="evan", user_id="39cb62d4", role="lead")
            journey = build_boot_journey(
                identity_ok=True,
                settings=self._settings(sources=["global"]),
                cdase_root=root,
                errors=[],
            )
            self.assertFalse(journey["hub_tools_blocked"])
            self.assertEqual(journey["next_step"]["id"], "sync")
            step7 = next(s for s in journey["journey"] if s["id"] == "team")
            self.assertEqual(step7["status"], "ready")


class ClientHubGateTests(unittest.TestCase):
    def test_sync_blocked_without_explicit_hub_url(self):
        from tests.hub_test_support import run_client, test_app_cdase_root

        env = {
            "CDASE_ROOT": str(test_app_cdase_root()),
            "CDASE_GLOBAL": tempfile.mkdtemp(prefix="cdase-global-"),
        }
        # No global setting file → defaults only
        code, payload = run_client("sync", env=env)
        self.assertEqual(code, 1)
        self.assertTrue(payload.get("hub_tools_blocked"))
        self.assertEqual(payload.get("reason"), "hub_url_not_configured")


if __name__ == "__main__":
    unittest.main()
