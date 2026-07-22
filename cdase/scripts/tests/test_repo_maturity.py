from __future__ import annotations

import tempfile
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

from repo_maturity import classify_repo_maturity


class RepoMaturityTest(unittest.TestCase):
    def test_greenfield_is_uninitialized_without_implementation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "README.md").write_text("# New app")
            result = classify_repo_maturity(root)
            self.assertEqual("CDASE_UNINITIALIZED", result["adoption_state"])
            self.assertEqual("GREENFIELD", result["codebase_state"])

    def test_existing_first_party_code_is_legacy_before_cdase_init(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "src"
            source.mkdir()
            (source / "App.java").write_text(
                "public class App { public String run() { return \"ok\"; } }"
            )
            result = classify_repo_maturity(root)
            self.assertEqual("LEGACY", result["codebase_state"])
            self.assertTrue(result["legacy_scan_recommended"])

    def test_initialized_code_without_registry_is_partial_legacy(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "cdase" / "context").mkdir(parents=True)
            (root / "src").mkdir()
            (root / "src" / "api.py").write_text(
                "from fastapi import FastAPI\napp = FastAPI()\n@app.get('/x')\ndef x(): return 1"
            )
            result = classify_repo_maturity(root)
            self.assertEqual("CDASE_INITIALIZED", result["adoption_state"])
            self.assertEqual("PARTIAL_LEGACY", result["codebase_state"])

    def test_registry_makes_initialized_code_managed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "cdase" / "context").mkdir(parents=True)
            modules = root / "cdase" / "api" / "modules"
            modules.mkdir(parents=True)
            (modules / "orders.api.md").write_text("# APIs")
            (root / "src").mkdir()
            (root / "src" / "api.ts").write_text("export function getOrder() { return {}; }")
            result = classify_repo_maturity(root)
            self.assertEqual("MANAGED", result["codebase_state"])

    def test_vendor_generated_and_tests_do_not_make_repo_legacy(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for rel in ("vendor/lib.java", "generated/client.ts", "tests/test_api.py"):
                path = root / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("public class Generated {}")
            result = classify_repo_maturity(root)
            self.assertEqual("GREENFIELD", result["codebase_state"])

    def test_source_package_named_cdase_is_not_mistaken_for_governance_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "src" / "main" / "java" / "com" / "cdase" / "Api.java"
            path.parent.mkdir(parents=True)
            path.write_text("public class Api { public void call() {} }")
            result = classify_repo_maturity(root)
            self.assertEqual("LEGACY", result["codebase_state"])


if __name__ == "__main__":
    unittest.main()
