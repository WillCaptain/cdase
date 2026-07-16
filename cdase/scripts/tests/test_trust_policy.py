"""Unit tests for trust policy."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

from trust_policy import classify_message, merge_team, split_messages  # noqa: E402


class TrustPolicyTest(unittest.TestCase):
    def test_unknown_sender_not_auto_reply(self):
        roster = [{"name": "evan", "uuid": "39cb62d4"}]
        msg = {"from_uuid": "8021d819", "from": "will", "body": "help?", "read": False}
        out = classify_message(msg, {"39cb62d4"})
        self.assertFalse(out["auto_reply_allowed"])
        self.assertEqual(out["status"], "unknown_sender")

    def test_trusted_sender_may_reply(self):
        roster = [{"name": "evan", "uuid": "39cb62d4"}, {"name": "will", "uuid": "8021d819"}]
        msg = {"from_uuid": "8021d819", "from": "will", "body": "help?", "read": False}
        out = classify_message(msg, {"39cb62d4", "8021d819"})
        self.assertTrue(out["auto_reply_allowed"])

    def test_merge_team_new_to_you(self):
        roster = [{"name": "evan", "uuid": "39cb62d4", "role": "dev"}]
        hub = [
            {"uuid": "39cb62d4", "name": "evan", "active": True},
            {"uuid": "8021d819", "name": "will", "active": True},
        ]
        members = merge_team(roster, hub)
        new = [m for m in members if m.get("status") == "new_to_you"]
        self.assertEqual(len(new), 1)
        self.assertEqual(new[0]["name"], "will")

    def test_split_messages_counts(self):
        roster = [{"name": "evan", "uuid": "39cb62d4"}]
        msgs = [
            {"from_uuid": "39cb62d4", "from": "evan", "read": True},
            {"from_uuid": "8021d819", "from": "will", "read": False},
        ]
        split = split_messages(msgs, roster)
        self.assertEqual(split["unknown_unread_count"], 1)
        self.assertEqual(len(split["trusted"]), 1)


if __name__ == "__main__":
    unittest.main()
