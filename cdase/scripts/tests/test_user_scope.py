#!/usr/bin/env python3
"""Tests for global vs repo user profile writes and scope preset."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from input_specs import (
    interpret_user_scope,
    resolve_input_spec,
    write_global_user_profile,
    write_repo_user_profile,
)
from context_loader import global_cdase_dir
from unittest import mock
import os


class UserScopeTests(unittest.TestCase):
    def test_scope_preset(self):
        spec = resolve_input_spec("user.scope")
        self.assertEqual(spec["kind"], "choice")
        ids = {o["id"] for o in spec["options"]}
        self.assertEqual(ids, {"global", "repo"})

    def test_interpret_scope(self):
        self.assertEqual(interpret_user_scope({"choice": "global"}), "global")
        self.assertEqual(interpret_user_scope({"choice": "this repo"}), "repo")
        self.assertEqual(interpret_user_scope({"choice": "x"}), "unknown")


class WriteUserTests(unittest.TestCase):
    def test_write_global(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.dict(os.environ, {"CDASE_GLOBAL": tmp}, clear=False):
                path = write_global_user_profile({"Name": "evan", "Role": "lead"})
                self.assertEqual(path, Path(tmp) / "user.context.md")
                text = path.read_text()
                self.assertIn("- Name: evan", text)

    def test_write_repo_override(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "cdase"
            path = write_repo_user_profile(root, {"Name": "will", "Role": "developer"})
            self.assertEqual(path, root / "context" / "user.context.md")
            self.assertIn("- Name: will", path.read_text())
            self.assertIn("Repo User Override", path.read_text())


if __name__ == "__main__":
    unittest.main()
