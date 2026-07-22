#!/usr/bin/env python3
"""Cross-platform repository boundary tests."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

from repo_boundary import classify_message_body


class RepoBoundaryTests(unittest.TestCase):
    def test_windows_backslashes_and_case_are_detected(self):
        with mock.patch("repo_boundary.Path.home", return_value=Path("C:/Users/Alice")):
            warning = classify_message_body(
                r"Read c:\USERS\ALICE\.CDASE\user.context.md",
                Path("C:/work/repo"),
            )
        self.assertIsNotNone(warning)
        self.assertIn("/.cdase", warning)

    def test_repo_path_is_not_flagged(self):
        with mock.patch("repo_boundary.Path.home", return_value=Path("/Users/alice")):
            warning = classify_message_body(
                "/Users/alice/work/repo/.env.example",
                Path("/Users/alice/work/repo"),
            )
        self.assertIsNone(warning)


if __name__ == "__main__":
    unittest.main()
