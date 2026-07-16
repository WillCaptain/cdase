#!/usr/bin/env python3
"""Tests: skill setting.context.md template → ~/.cdase copy."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from input_specs import ensure_global_setting_from_template, setting_context_template_path


class SettingTemplateTests(unittest.TestCase):
    def test_template_has_12th_hub(self):
        text = setting_context_template_path().read_text(encoding="utf-8")
        self.assertIn("https://12th.ai/cdase", text)
        self.assertIn("Address:", text)

    def test_copy_once_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.dict(os.environ, {"CDASE_GLOBAL": tmp}, clear=False):
                first = ensure_global_setting_from_template()
                self.assertTrue(first["copied"])
                dest = Path(tmp) / "setting.context.md"
                self.assertTrue(dest.is_file())
                self.assertIn("https://12th.ai/cdase", dest.read_text())

                dest.write_text("CUSTOM\n", encoding="utf-8")
                second = ensure_global_setting_from_template()
                self.assertFalse(second["copied"])
                self.assertEqual(dest.read_text(), "CUSTOM\n")


if __name__ == "__main__":
    unittest.main()
