from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

from legacy_api_approval import (  # noqa: E402
    apply_approved_candidates,
    build_approval_spec,
    save_scan_report,
)
from legacy_api_scan import (  # noqa: E402
    build_scan_job,
    collect_legacy_evidence,
    validate_scan_report,
)


class LegacyApiScanTest(unittest.TestCase):
    def test_evidence_and_job_are_read_only_and_isolated(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "src"
            src.mkdir()
            (src / "api.py").write_text(
                "from fastapi import FastAPI\n"
                "app = FastAPI()\n"
                "@app.get('/orders/{order_id}')\n"
                "def get_order(order_id: str): return {'id': order_id}\n"
            )
            evidence = collect_legacy_evidence(root)
            self.assertEqual("LEGACY", evidence["maturity"]["codebase_state"])
            self.assertFalse(evidence["mutation_allowed"])
            self.assertTrue(any(e["kind"] == "http_route" for e in evidence["evidence"]))

            job = build_scan_job(root, evidence)
            self.assertTrue(job["session"]["must_be_new"])
            self.assertTrue(job["session"]["read_only"])
            self.assertIn("Do not upload to Hub", job["prompt"])

    def test_report_validation_requires_confidence_and_evidence(self):
        report = self.report()
        self.assertEqual("scan-1", validate_scan_report(report)["scan_id"])
        report["candidates"][0]["discovery_confidence"] = "CERTAIN"
        with self.assertRaises(ValueError):
            validate_scan_report(report)

    def test_approval_defaults_high_and_applies_only_selected(self):
        report = self.report()
        spec = build_approval_spec(report)
        self.assertEqual("multi_choice", spec["kind"])
        selected_defaults = [o["id"] for o in spec["options"] if o["selected"]]
        self.assertEqual(["high-api"], selected_defaults)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cdase = root / "cdase"
            paths = save_scan_report(cdase, report)
            self.assertTrue(Path(paths["json"]).is_file())
            self.assertIn("legacy_api_scan_", Path(paths["json"]).name)
            self.assertIn("legacy_api_scan_", Path(paths["markdown"]).name)
            result = apply_approved_candidates(
                cdase,
                report,
                {"selected": ["medium-api"]},
                repo_id="github.com/acme/legacy",
                owner="will",
            )
            self.assertEqual(["medium-api"], result["selected"])
            self.assertFalse(result["upload_performed"])
            registry = cdase / "api" / "modules" / "invoice.api.md"
            text = registry.read_text()
            self.assertIn("createInvoice", text)
            self.assertNotIn("getOrder", text)
            definition = json.loads(
                text.split("```json cdase-api\n", 1)[1].split("\n```", 1)[0]
            )
            self.assertEqual("LEGACY_IMPORT", definition["origin"])
            self.assertEqual("MEDIUM", definition["discovery_confidence"])
            self.assertTrue(Path(result["approval"]).is_file())

    @staticmethod
    def report():
        return {
            "schema": "cdase/legacy-api-scan/v1",
            "scan_id": "scan-1",
            "classification": "LEGACY",
            "candidates": [
                {
                    "candidate_id": "high-api",
                    "api": {
                        "system": "orders",
                        "module": "order",
                        "name": "getOrder",
                        "kind": "REST",
                        "capability": "Retrieve an order",
                        "signature": "GET /orders/{id}",
                    },
                    "discovery_confidence": "HIGH",
                    "evidence": [
                        {"kind": "route", "path": "src/orders.py", "line": 2}
                    ],
                    "uncertainties": [],
                },
                {
                    "candidate_id": "medium-api",
                    "api": {
                        "system": "billing",
                        "module": "invoice",
                        "name": "createInvoice",
                        "kind": "REST",
                        "capability": "Create an invoice",
                        "signature": "POST /invoices",
                    },
                    "discovery_confidence": "MEDIUM",
                    "evidence": [
                        {"kind": "route", "path": "src/billing.py", "line": 8}
                    ],
                    "uncertainties": ["errors not explicit"],
                },
            ],
            "excluded": [],
        }


if __name__ == "__main__":
    unittest.main()
