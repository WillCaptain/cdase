from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

from api_registry import (  # noqa: E402
    content_hash,
    legacy_publish_gate,
    parse_api_blocks,
    sync_state,
)


class ApiRegistryTest(unittest.TestCase):
    def test_parses_only_cdase_api_blocks(self):
        definitions = parse_api_blocks(
            '# API\n```json cdase-api\n{"api_id":"a","version":"v1"}\n```\n'
            '```json\n{"ignored":true}\n```\n'
        )
        self.assertEqual(1, len(definitions))

    def test_provenance_does_not_change_content_hash(self):
        native = self.definition()
        legacy = {
            **native,
            "origin": "LEGACY_IMPORT",
            "discovery_confidence": "LOW",
            "scan_id": "scan-1",
            "approval_ref": "approval.json",
            "discovery_evidence": [{"kind": "route", "path": "src/api.py"}],
        }
        self.assertEqual(content_hash(native), content_hash(legacy))

    def test_sync_states_are_derived(self):
        local = self.definition()
        remote = {
            "api": {
                **local,
                "content_hash": content_hash(local),
            }
        }
        self.assertEqual("SYNCED", sync_state(local, remote, commit="abc")["state"])

        changed = {**remote["api"], "content_hash": "different"}
        self.assertEqual(
            "STALE",
            sync_state(local, {"api": changed}, commit="abc")["state"],
        )
        self.assertEqual(
            "MISSING",
            sync_state(local, {"error": "not found", "status": 404}, commit="abc")["state"],
        )
        conflict = {
            "api": {
                **remote["api"],
                "source": {**remote["api"]["source"], "repo": "other/repo"},
            }
        }
        self.assertEqual("CONFLICT", sync_state(local, conflict, commit="abc")["state"])

    def test_legacy_publish_gate_blocks_unapproved_imports(self):
        legacy = {
            **self.definition(),
            "origin": "LEGACY_IMPORT",
            "discovery_confidence": "HIGH",
            "scan_id": "scan-1",
        }
        error = legacy_publish_gate(
            legacy,
            git_root=Path("."),
            registry_repo_path="cdase/api/modules/order.api.md",
        )
        self.assertIn("approval_ref", error)
        self.assertIsNone(
            legacy_publish_gate(
                self.definition(),
                git_root=Path("."),
                registry_repo_path="cdase/api/modules/order.api.md",
            )
        )

    @staticmethod
    def definition():
        return {
            "api_id": "acme/orders/getOrder",
            "system": "orders",
            "module": "order",
            "name": "getOrder",
            "kind": "REST",
            "version": "v1",
            "capability": "Retrieve an order",
            "signature": "GET /orders/{id}",
            "use_when": ["Order identifier is known"],
            "do_not_use_when": [],
            "inputs": [],
            "outputs": [],
            "errors": [],
            "side_effects": [],
            "source": {
                "repo": "acme/orders",
                "path": "cdase/api/modules/order.api.md",
                "commit": "abc",
                "owner": "will",
            },
        }


if __name__ == "__main__":
    unittest.main()
