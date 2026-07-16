"""Unit tests for repo_id resolution."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

from repo_id import normalize_git_remote, resolve_repo_id  # noqa: E402


class RepoIdTest(unittest.TestCase):
    def test_normalize_https_remote(self):
        self.assertEqual(
            normalize_git_remote("https://github.com/org/aintegration.git"),
            "github.com/org/aintegration",
        )

    def test_normalize_scp_remote(self):
        self.assertEqual(
            normalize_git_remote("git@github.com:org/aintegration.git"),
            "github.com/org/aintegration",
        )

    def test_setting_overrides(self):
        cdase = Path("/tmp/fake/cdase")
        rid, src = resolve_repo_id(
            cdase,
            Path("/tmp/fake"),
            {"repo_id": "my-custom-id"},
        )
        self.assertEqual(rid, "my-custom-id")
        self.assertEqual(src, "setting")


if __name__ == "__main__":
    unittest.main()
