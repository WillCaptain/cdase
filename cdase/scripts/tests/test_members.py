#!/usr/bin/env python3
"""Tests for conflict-free project member records."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

from context_loader import load_members, load_user_context, resolve_recipient, trusted_uuids
from machine_identity import ensure_machine_member, machine_user_id, write_member_record
from team import member_commit_states, members_are_committed


class MemberRecordTests(unittest.TestCase):
    def test_distinct_users_write_distinct_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "cdase"
            first = write_member_record(root, name="alice", user_id="a1b2c3d4")
            second = write_member_record(root, name="bob", user_id="b2c3d4e5")
            self.assertNotEqual(first, second)
            self.assertEqual({m["uuid"] for m in load_members(root)}, {"a1b2c3d4", "b2c3d4e5"})

    def test_filename_and_declared_id_must_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cdase" / "context" / "members" / "a1b2c3d4.context.md"
            path.parent.mkdir(parents=True)
            path.write_text(
                "# Project Member\n\n- User ID: b2c3d4e5\n- Alias: alice\n- Status: active\n"
            )
            with self.assertRaisesRegex(ValueError, "filename/id mismatch"):
                load_members(Path(tmp) / "cdase")

    def test_member_fields_reject_record_injection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "cdase"
            with self.assertRaisesRegex(ValueError, "control characters"):
                write_member_record(
                    root,
                    name="alice\n- Status: inactive",
                    user_id="a1b2c3d4",
                )
            with self.assertRaisesRegex(ValueError, "required"):
                write_member_record(root, name="   ", user_id="a1b2c3d4")

    def test_inactive_member_is_not_trusted_or_resolvable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "cdase"
            write_member_record(
                root, name="alice", user_id="a1b2c3d4", status="inactive"
            )
            members = load_members(root)
            self.assertEqual(trusted_uuids(members), [])
            self.assertIsNone(resolve_recipient("a1b2c3d4", members))

    def test_duplicate_alias_requires_user_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "cdase"
            write_member_record(root, name="will", user_id="a1b2c3d4")
            write_member_record(root, name="will", user_id="b2c3d4e5")
            members = load_members(root)
            self.assertIsNone(resolve_recipient("will", members))
            self.assertEqual(resolve_recipient("a1b2c3d4", members)["uuid"], "a1b2c3d4")

    def test_repo_alias_overrides_and_publishes_member_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "cdase"
            global_dir = Path(tmp) / "global"
            global_dir.mkdir()
            (global_dir / "user.context.md").write_text(
                "# Global\n\n## Identity\n- Name: global-name\n- Role: developer\n"
            )
            repo_user = root / "context" / "user.context.md"
            repo_user.parent.mkdir(parents=True)
            repo_user.write_text(
                "# Repo\n\n## Identity\n- Name: project-alias\n- Role: lead\n"
            )
            machine = "member-alias-test"
            with mock.patch.dict(
                os.environ,
                {"CDASE_GLOBAL": str(global_dir), "CDASE_MACHINE_ID": machine},
                clear=False,
            ):
                result = ensure_machine_member(root)
                user = load_user_context(root)
            self.assertEqual(result["action"], "added")
            self.assertEqual(user["name"], "project-alias")
            member = load_members(root)[0]
            self.assertEqual(member["uuid"], machine_user_id(machine))
            self.assertEqual(member["name"], "project-alias")
            self.assertEqual(member["alias"], "project-alias")
            self.assertEqual(member["role"], "lead")

    def test_member_git_states_distinguish_pending_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            subprocess.run(
                ["git", "init", "-q"], cwd=repo, check=True, capture_output=True
            )
            root = repo / "cdase"
            path = write_member_record(root, name="alice", user_id="a1b2c3d4")
            states = member_commit_states(root, repo)
            rel = path.resolve().relative_to(repo.resolve()).as_posix()
            self.assertEqual(states[rel], "untracked")
            self.assertFalse(members_are_committed(root, repo))
            pending = load_members(root)
            self.assertFalse(pending[0]["committed"])
            self.assertEqual(trusted_uuids(pending), [])
            self.assertIsNone(resolve_recipient("a1b2c3d4", pending))
            subprocess.run(["git", "add", rel], cwd=repo, check=True, capture_output=True)
            self.assertEqual(member_commit_states(root, repo)[rel], "staged")

    def test_ignored_member_is_not_reported_committed(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            subprocess.run(
                ["git", "init", "-q"], cwd=repo, check=True, capture_output=True
            )
            (repo / ".gitignore").write_text("cdase/context/members/\n")
            root = repo / "cdase"
            path = write_member_record(root, name="alice", user_id="a1b2c3d4")
            rel = path.resolve().relative_to(repo.resolve()).as_posix()
            self.assertEqual(member_commit_states(root, repo)[rel], "ignored")
            self.assertFalse(members_are_committed(root, repo))


if __name__ == "__main__":
    unittest.main()
