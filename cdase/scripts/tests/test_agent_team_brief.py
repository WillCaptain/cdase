"""Unit tests for repo-only team brief."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

from team import build_agent_team_brief  # noqa: E402
from trust_policy import merge_team  # noqa: E402


class BuildAgentTeamBriefTest(unittest.TestCase):
    def test_lists_roster_and_new_to_you(self):
        roster = [
            {"name": "evan", "uuid": "39cb62d4", "role": "developer"},
        ]
        hub = [
            {"uuid": "39cb62d4", "name": "evan", "active": True},
            {"uuid": "8021d819", "name": "will", "active": True},
        ]
        members = merge_team(roster, hub)
        brief = build_agent_team_brief({"name": "evan"}, members)
        self.assertIn("will", brief["agent_brief"])
        self.assertIn("new_to_you", brief["agent_brief"])
        self.assertIn("will", brief["must_not_auto_trust"])

    def test_inactive_and_pending_members_are_not_listed_as_trusted(self):
        members = merge_team(
            [
                {"name": "former", "uuid": "8021d819", "status": "inactive"},
                {
                    "name": "pending",
                    "uuid": "a1b2c3d4",
                    "status": "active",
                    "committed": False,
                    "commit_state": "untracked",
                },
            ],
            [],
        )
        brief = build_agent_team_brief({"name": "evan"}, members)
        self.assertIn("Inactive project members", brief["agent_brief"])
        self.assertIn("Pending member records", brief["agent_brief"])
        self.assertEqual(brief["others_count"], 0)


if __name__ == "__main__":
    unittest.main()
