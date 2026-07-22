#!/usr/bin/env python3
"""Runtime root safety tests."""

from __future__ import annotations

import sys
import tempfile
import unittest
import os
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

from cdase_runtime import find_cdase_root


class CdaseRuntimeTests(unittest.TestCase):
    def test_cdase_root_override_rejects_framework_package(self):
        framework_cdase = SCRIPTS.parent
        with mock.patch.dict(os.environ, {"CDASE_ROOT": str(framework_cdase)}, clear=False):
            with self.assertRaisesRegex(RuntimeError, "framework"):
                find_cdase_root(SCRIPTS)

    def test_cdase_root_override_accepts_application_git_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "app"
            (repo / ".git").mkdir(parents=True)
            target = repo / "cdase"
            with mock.patch.dict(os.environ, {"CDASE_ROOT": str(target)}, clear=False):
                self.assertEqual(find_cdase_root(SCRIPTS), target.resolve())

    def test_framework_only_workspace_never_becomes_consumer_runtime(self):
        info = {
            "scenario": "1_framework_only",
            "repos": [{"path": "/framework", "is_framework": True}],
            "consumer_repos_without_cdase": [],
        }
        with (
            mock.patch("cdase_runtime.resolve_consumer_cdase_root", return_value=None),
            mock.patch("repo_discovery.classify_workspace", return_value=info),
        ):
            with self.assertRaisesRegex(RuntimeError, "not an application runtime"):
                find_cdase_root(SCRIPTS)


if __name__ == "__main__":
    unittest.main()
