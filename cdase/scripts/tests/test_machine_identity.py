#!/usr/bin/env python3
"""Tests for machine-as-user identity."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from machine_identity import (  # noqa: E402
    ensure_machine_member,
    machine_user_id,
    write_member_record,
)
from context_loader import load_members, load_user_context, validate_identity  # noqa: E402


class MachineIdentityTests(unittest.TestCase):
    def test_machine_user_id_stable(self):
        a = machine_user_id("host-abc")
        b = machine_user_id("host-abc")
        c = machine_user_id("host-xyz")
        self.assertEqual(a, b)
        self.assertEqual(len(a), 8)
        self.assertNotEqual(a, c)

    def test_ensure_found(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "cdase"
            mid = "test-machine-1"
            uid = machine_user_id(mid)
            write_member_record(root, name="will", user_id=uid, role="lead")
            with mock.patch.dict(os.environ, {"CDASE_MACHINE_ID": mid}, clear=False):
                res = ensure_machine_member(root)
            self.assertEqual(res["action"], "found")
            self.assertEqual(res["name"], "will")

    def test_ensure_adds_from_global_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            gdir = Path(tmp) / "global"
            gdir.mkdir()
            (gdir / "user.context.md").write_text(
                "# Global\n\n## Identity\n- Name: will\n", encoding="utf-8"
            )
            root = Path(tmp) / "cdase"
            (root / "context").mkdir(parents=True)
            write_member_record(root, name="bob", user_id="400edd13", role="dev")
            mid = "new-laptop"
            uid = machine_user_id(mid)
            with mock.patch.dict(
                os.environ, {"CDASE_GLOBAL": str(gdir), "CDASE_MACHINE_ID": mid}, clear=False
            ):
                res = ensure_machine_member(root)
                self.assertEqual(res["action"], "added")
                self.assertEqual(res["user_id"], uid)
                members = load_members(root)
                self.assertTrue(any(m["uuid"] == uid and m["name"] == "will" for m in members))
                user = load_user_context(root)
                ok, errors = validate_identity(user, members)
                self.assertTrue(ok, errors)

    def test_ensure_need_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            gdir = Path(tmp) / "global"
            gdir.mkdir()
            root = Path(tmp) / "cdase"
            (root / "context").mkdir(parents=True)
            with mock.patch.dict(
                os.environ, {"CDASE_GLOBAL": str(gdir), "CDASE_MACHINE_ID": "x"}, clear=False
            ):
                res = ensure_machine_member(root)
            self.assertEqual(res["action"], "need_name")
            self.assertFalse(res["ok"])


if __name__ == "__main__":
    unittest.main()
