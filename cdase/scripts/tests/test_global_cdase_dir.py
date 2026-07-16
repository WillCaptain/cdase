#!/usr/bin/env python3
"""Tests for agent-neutral ~/.cdase global dir resolution."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from context_loader import global_cdase_dir, migrate_legacy_global_dir


class GlobalCdaseDirTests(unittest.TestCase):
    def test_env_override(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.dict(os.environ, {"CDASE_GLOBAL": tmp}, clear=False):
                self.assertEqual(global_cdase_dir(), Path(tmp))

    def test_prefers_canonical_when_both_exist(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            preferred = home / ".cdase"
            legacy = home / ".cursor" / "cdase"
            preferred.mkdir()
            legacy.mkdir(parents=True)
            with mock.patch.dict(os.environ, {}, clear=False):
                os.environ.pop("CDASE_GLOBAL", None)
                with mock.patch("context_loader.DEFAULT_GLOBAL_CDASE_DIR", preferred), \
                     mock.patch("context_loader.LEGACY_GLOBAL_CDASE_DIR", legacy):
                    self.assertEqual(global_cdase_dir(), preferred)

    def test_migrates_then_uses_canonical(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            preferred = home / ".cdase"
            legacy = home / ".cursor" / "cdase"
            legacy.mkdir(parents=True)
            (legacy / "user.context.md").write_text("- Name: test\n", encoding="utf-8")
            (legacy / "setting.context.md").write_text("- Address: http://h\n", encoding="utf-8")
            with mock.patch.dict(os.environ, {}, clear=False):
                os.environ.pop("CDASE_GLOBAL", None)
                with mock.patch("context_loader.DEFAULT_GLOBAL_CDASE_DIR", preferred), \
                     mock.patch("context_loader.LEGACY_GLOBAL_CDASE_DIR", legacy):
                    self.assertEqual(global_cdase_dir(), preferred)
                    self.assertTrue((preferred / "user.context.md").exists())
                    self.assertTrue((preferred / "setting.context.md").exists())

    def test_migrate_does_not_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            preferred = Path(tmp) / ".cdase"
            legacy = Path(tmp) / ".cursor" / "cdase"
            preferred.mkdir()
            legacy.mkdir(parents=True)
            (preferred / "user.context.md").write_text("NEW\n", encoding="utf-8")
            (legacy / "user.context.md").write_text("OLD\n", encoding="utf-8")
            copied = migrate_legacy_global_dir(preferred, legacy)
            self.assertEqual(copied, [])
            self.assertEqual((preferred / "user.context.md").read_text(), "NEW\n")

    def test_new_install_uses_canonical(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            preferred = home / ".cdase"
            legacy = home / ".cursor" / "cdase"
            with mock.patch.dict(os.environ, {}, clear=False):
                os.environ.pop("CDASE_GLOBAL", None)
                with mock.patch("context_loader.DEFAULT_GLOBAL_CDASE_DIR", preferred), \
                     mock.patch("context_loader.LEGACY_GLOBAL_CDASE_DIR", legacy):
                    self.assertEqual(global_cdase_dir(), preferred)

    def test_writes_always_use_canonical(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            preferred = home / ".cdase"
            legacy = home / ".cursor" / "cdase"
            legacy.mkdir(parents=True)
            (legacy / "setting.context.md").write_text("legacy\n", encoding="utf-8")
            with mock.patch.dict(os.environ, {}, clear=False):
                os.environ.pop("CDASE_GLOBAL", None)
                with mock.patch("context_loader.DEFAULT_GLOBAL_CDASE_DIR", preferred), \
                     mock.patch("context_loader.LEGACY_GLOBAL_CDASE_DIR", legacy):
                    self.assertEqual(global_cdase_dir(for_write=True), preferred)
                    self.assertTrue((preferred / "setting.context.md").exists())


if __name__ == "__main__":
    unittest.main()
