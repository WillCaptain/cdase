"""End-to-end tests for the Hub global API pool HTTP contract."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen

from hub_test_support import (
    EphemeralHub,
    ensure_test_member,
    run_client,
    test_app_cdase_root,
)


class LegacyApiPoolHandler(BaseHTTPRequestHandler):
    entries = {}
    authorization = None

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api-pool/health":
            self.respond({"ok": True, "provider": "legacy-http-test"})
            return
        if parsed.path == "/api-pool/apis":
            api_id = parse_qs(parsed.query).get("api_id", [None])[0]
            version = parse_qs(parsed.query).get("version", [None])[0]
            api = self.entries.get((api_id, version))
            self.respond(
                {"ok": True, "api": api}
                if api
                else {"ok": False, "error": "API not found"}
            )
            return
        if parsed.path == "/api-pool/graph":
            self.respond({
                "ok": True,
                "graph": {"modules": [], "apis": list(self.entries.values()), "relations": []},
            })
            return
        self.respond({"error": "not found"}, status=404)

    def do_POST(self):
        parsed = urlparse(self.path)
        self.__class__.authorization = self.headers.get("Authorization")
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
        if parsed.path == "/api-pool/apis":
            api = {
                key: value
                for key, value in body.items()
                if key not in {"embedding", "replace_embedding"}
            }
            api["embedding_dimensions"] = len(body.get("embedding") or [])
            self.entries[(api["api_id"], api["version"])] = api
            self.respond({"ok": True, "api": api})
            return
        if parsed.path == "/api-pool/search":
            query = body["query"].lower()
            results = [
                {
                    "api_id": api["api_id"],
                    "version": api["version"],
                    "status": api["status"],
                    "capability": api["capability"],
                    "score": 1.0,
                }
                for api in self.entries.values()
                if any(word in api["capability"].lower() for word in query.split())
            ]
            self.respond({"ok": True, "results": results})
            return
        self.respond({"error": "not found"}, status=404)

    def respond(self, body, status=200):
        payload = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *_args):
        pass


class ApiPoolIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.token = "api-pool-test-token"
        cls.member = ensure_test_member()
        cls.hub = EphemeralHub(
            port=17424,
            env={
                "CDASE_KB_PROVIDER": "embedded",
                "CDASE_KB_WRITE_TOKEN": cls.token,
            },
        )
        cls.url = cls.hub.start()

    def client_env(self, **extra):
        env = {
            "CDASE_ROOT": self.member["CDASE_ROOT"],
            "CDASE_MACHINE_ID": self.member["CDASE_MACHINE_ID"],
            "CDASE_HUB_URL": self.url,
            "CDASE_KB_WRITE_TOKEN": self.token,
        }
        env.update(extra)
        return env

    @classmethod
    def tearDownClass(cls):
        cls.hub.stop()
        member_path = Path(cls.member.get("member_path", ""))
        if member_path.is_file() and "cdase-api-pool-test-machine" in cls.member.get(
            "CDASE_MACHINE_ID", ""
        ):
            member_path.unlink(missing_ok=True)
            members_dir = member_path.parent
            if members_dir.is_dir() and not any(members_dir.iterdir()):
                members_dir.rmdir()

    def test_publish_search_transition_get_and_graph(self):
        api = {
            "api_id": "billing/invoice/createInvoice",
            "system": "billing",
            "module": "invoice",
            "name": "createInvoice",
            "kind": "REST",
            "version": "v1",
            "status": "DEVELOPING",
            "capability": "Create a payable invoice for an accepted order",
            "use_when": ["An order has passed validation"],
            "do_not_use_when": ["Creating a draft quotation"],
            "signature": "POST /invoices",
            "inputs": [
                {
                    "name": "orderId",
                    "type": "string",
                    "description": "Accepted order",
                    "required": True,
                }
            ],
            "outputs": [
                {
                    "name": "invoiceId",
                    "type": "string",
                    "description": "Created invoice",
                    "required": True,
                }
            ],
            "errors": [{"code": "ORDER_NOT_FOUND", "description": "No order"}],
            "side_effects": ["Persists invoice"],
            "source": {
                "repo": "github.com/acme/billing",
                "path": "cdase/api/modules/invoice.api.md",
                "commit": "abc123",
                "owner": "billing-team",
            },
        }

        unauthorized_code, _ = self.request("POST", "/api-pool/apis", api)
        self.assertEqual(401, unauthorized_code)

        client_env = self.client_env()
        code, published = run_client(
            "api-publish",
            "--json",
            json.dumps(api),
            env=client_env,
        )
        self.assertEqual(0, code)
        self.assertTrue(published["ok"])
        self.assertEqual("DEVELOPING", published["api"]["status"])

        unauthorized_transition, _ = self.request(
            "POST",
            "/api-pool/transition",
            {
                "api_id": "billing/invoice/createInvoice",
                "version": "v1",
                "status": "RELEASED",
            },
        )
        self.assertEqual(401, unauthorized_transition)

        code, search = run_client(
            "api-search",
            "create invoice from accepted order",
            "--system",
            "billing",
            "--limit",
            "10",
            env=client_env,
        )
        self.assertEqual(0, code)
        self.assertEqual(1, search["count"])
        self.assertEqual("billing/invoice/createInvoice", search["results"][0]["api_id"])
        self.assertFalse(search["semantic_search"])

        code, released = run_client(
            "api-transition",
            "billing/invoice/createInvoice",
            "v1",
            "RELEASED",
            env=client_env,
        )
        self.assertEqual(0, code)
        self.assertEqual("RELEASED", released["api"]["status"])

        code, fetched = run_client(
            "api-get",
            "billing/invoice/createInvoice",
            "--version",
            "v1",
            env=client_env,
        )
        self.assertEqual(0, code)
        self.assertEqual("POST /invoices", fetched["api"]["signature"])
        self.assertEqual(2, len(fetched["api"]["lifecycle_events"]))

        v2 = dict(api)
        v2["version"] = "v2"
        v2["capability"] = "Create a payable invoice including tax details"
        code, published_v2 = run_client(
            "api-publish",
            "--json",
            json.dumps(v2),
            env=client_env,
        )
        self.assertEqual(0, code, published_v2)
        code, _ = run_client(
            "api-transition",
            "billing/invoice/createInvoice",
            "v2",
            "RELEASED",
            env=client_env,
        )
        self.assertEqual(0, code)
        code, superseded = run_client(
            "api-transition",
            "billing/invoice/createInvoice",
            "v1",
            "SUPERSEDED",
            "--superseded-by-version",
            "v2",
            env=client_env,
        )
        self.assertEqual(0, code, superseded)
        self.assertEqual("SUPERSEDED", superseded["api"]["status"])

        code, upgraded_search = run_client(
            "api-search",
            "create payable invoice",
            "--system",
            "billing",
            env=client_env,
        )
        self.assertEqual(0, code)
        self.assertEqual("v2", upgraded_search["results"][0]["version"])

        code, old_version = run_client(
            "api-get",
            "billing/invoice/createInvoice",
            "--version",
            "v1",
            env=client_env,
        )
        self.assertEqual(0, code)
        self.assertEqual("SUPERSEDED", old_version["api"]["status"])
        self.assertEqual(
            "v2",
            old_version["api"]["lifecycle_events"][-1]["related_version"],
        )

        code, graph = run_client(
            "api-graph",
            "--system",
            "billing",
            env=client_env,
        )
        self.assertEqual(0, code)
        self.assertEqual(1, len(graph["graph"]["modules"]))
        self.assertEqual(2, len(graph["graph"]["apis"]))

        code, health = self.request("GET", "/api-pool/health")
        self.assertEqual(200, code)
        self.assertEqual("embedded", health["provider"])
        self.assertEqual("disabled", health["embedding_model"])

    def test_approved_committed_legacy_import_uploads_and_checks_synced(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cdase_root = root / "cdase"
            (cdase_root / "context").mkdir(parents=True)
            global_root = root / ".cdase-global"
            global_root.mkdir()
            (global_root / "user.context.md").write_text(
                "# Global User Profile\n\n## Identity\n- Name: integration-user\n"
            )
            (global_root / "setting.context.md").write_text(
                f"# CDASE Settings\n\n## Hub\n- Address: {self.url}\n"
            )
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(
                [
                    "git", "remote", "add", "origin",
                    "https://github.com/acme/legacy-e2e.git",
                ],
                cwd=root,
                check=True,
            )
            env = {
                "CDASE_ROOT": str(cdase_root),
                "CDASE_GLOBAL": str(global_root),
                "CDASE_HUB_URL": self.url,
                "CDASE_KB_WRITE_TOKEN": self.token,
            }
            code, boot = run_client("boot", env=env)
            self.assertEqual(0, code)
            self.assertTrue(boot["identity_ok"])

            report = {
                "schema": "cdase/legacy-api-scan/v1",
                "scan_id": "legacy-scan-e2e",
                "classification": "LEGACY",
                "candidates": [{
                    "candidate_id": "legacy-health",
                    "api": {
                        "system": "legacy-e2e",
                        "module": "health",
                        "name": "getLegacyHealth",
                        "kind": "REST",
                        "capability": "Read legacy service health",
                        "signature": "GET /legacy-health",
                    },
                    "discovery_confidence": "HIGH",
                    "evidence": [{
                        "kind": "http_route",
                        "path": "src/health.py",
                        "line": 4,
                        "detail": "Explicit route",
                    }],
                    "uncertainties": [],
                }],
                "excluded": [],
            }
            code, saved = run_client(
                "legacy-scan-save", "--json", json.dumps(report), env=env
            )
            self.assertEqual(0, code)
            code, applied = run_client(
                "legacy-api-apply",
                "--report",
                saved["artifacts"]["json"],
                "--selection-json",
                json.dumps({"selected": ["legacy-health"]}),
                env=env,
            )
            self.assertEqual(0, code)
            self.assertFalse(applied["upload_performed"])

            git_env = {
                **os.environ,
                "GIT_AUTHOR_NAME": "CDASE Test",
                "GIT_AUTHOR_EMAIL": "cdase@example.invalid",
                "GIT_COMMITTER_NAME": "CDASE Test",
                "GIT_COMMITTER_EMAIL": "cdase@example.invalid",
            }
            subprocess.run(["git", "add", "cdase"], cwd=root, check=True)
            subprocess.run(
                ["git", "commit", "-q", "-m", "add approved legacy API"],
                cwd=root,
                env=git_env,
                check=True,
            )
            approval = (
                cdase_root / "run_log"
                / "legacy_api_approval_legacy-scan-e2e.json"
            )
            code, uploaded = run_client(
                "legacy-api-upload", "--approval", str(approval), env=env
            )
            self.assertEqual(0, code, uploaded)
            self.assertEqual(1, uploaded["uploaded"])

            registry = cdase_root / "api" / "modules" / "health.api.md"
            code, checked = run_client(
                "api-sync", str(registry), "--check", env=env
            )
            self.assertEqual(0, code, checked)
            self.assertEqual("hub", checked.get("verify_mode"))
            self.assertEqual(1, checked["counts"]["SYNCED"])

            # Ordinary api-sync of uncommitted LEGACY_IMPORT must fail.
            dirty_registry = cdase_root / "api" / "modules" / "dirty.api.md"
            dirty_registry.write_text(
                registry.read_text().replace(
                    "getLegacyHealth",
                    "getDirtyLegacyHealth",
                ).replace(
                    "legacy-e2e/health/getLegacyHealth",
                    "legacy-e2e/health/getDirtyLegacyHealth",
                )
            )
            code, blocked = run_client(
                "api-sync", str(dirty_registry), env=env
            )
            self.assertNotEqual(0, code)
            self.assertIn("committed", str(blocked.get("error", "")).lower())

    def test_api_sync_publishes_canonical_registry_blocks(self):
        registry = """
# Module API Registry

```json cdase-api
{
  "api_id": "orders/order/getOrder",
  "system": "orders",
  "module": "order",
  "name": "getOrder",
  "kind": "REST",
  "version": "v1",
  "status": "DEVELOPING",
  "capability": "Retrieve an order by its identifier",
  "use_when": ["A caller needs authoritative order details"],
  "do_not_use_when": ["Searching orders by customer"],
  "signature": "GET /orders/{orderId}",
  "inputs": [{"name": "orderId", "type": "string", "required": true}],
  "outputs": [{"name": "order", "type": "Order", "required": true}],
  "errors": [{"code": "ORDER_NOT_FOUND"}],
  "side_effects": [],
  "source": {"repo": "github.com/acme/orders", "owner": "orders-team"}
}
```
"""
        repo_root = Path(__file__).resolve().parents[3]
        client_env = self.client_env()
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".api.md",
            dir=repo_root / "tests" / "fixtures" / "app",
            encoding="utf-8",
        ) as api_file:
            api_file.write(registry)
            api_file.flush()
            code, result = run_client("api-sync", api_file.name, env=client_env)

        self.assertEqual(0, code, result)
        self.assertEqual(1, result["published"])
        self.assertTrue(result["results"][0]["ok"])

        code, search = run_client(
            "api-search",
            "retrieve authoritative order details",
            "--system",
            "orders",
            env=client_env,
        )
        self.assertEqual(0, code)
        self.assertEqual("orders/order/getOrder", search["results"][0]["api_id"])

    def test_writes_are_disabled_when_server_token_is_not_configured(self):
        with EphemeralHub(port=17425, env={"CDASE_KB_PROVIDER": "embedded"}) as url:
            original_url = self.url
            self.url = url
            try:
                code, response = self.request(
                    "POST",
                    "/api-pool/apis",
                    {"api_id": "unsafe/write"},
                    token="guessed-token",
                )
            finally:
                self.url = original_url
        self.assertEqual(503, code)
        self.assertIn("writes are disabled", response["error"])

    def test_hub_relocates_api_pool_to_legacy_http_provider(self):
        LegacyApiPoolHandler.entries = {}
        LegacyApiPoolHandler.authorization = None
        backend = ThreadingHTTPServer(("127.0.0.1", 0), LegacyApiPoolHandler)
        backend_thread = threading.Thread(target=backend.serve_forever, daemon=True)
        backend_thread.start()
        backend_url = f"http://127.0.0.1:{backend.server_address[1]}"
        try:
            with EphemeralHub(
                port=17426,
                env={
                    "CDASE_KB_PROVIDER": "http",
                    "CDASE_KB_HTTP_URL": backend_url,
                    "CDASE_KB_HTTP_TOKEN": "backend-secret",
                    "CDASE_KB_WRITE_TOKEN": self.token,
                },
            ) as hub_url:
                client_env = self.client_env(CDASE_HUB_URL=hub_url)
                api = {
                    "api_id": "identity/session/createSession",
                    "system": "identity",
                    "module": "session",
                    "name": "createSession",
                    "kind": "REST",
                    "version": "v1",
                    "status": "DEVELOPING",
                    "capability": "Create an authenticated user session",
                    "signature": "POST /sessions",
                    "source": {
                        "repo": "github.com/acme/identity",
                        "path": "cdase/api/modules/session.api.md",
                        "commit": "abc123",
                        "owner": "identity-team",
                    },
                }
                code, published = run_client(
                    "api-publish",
                    "--json",
                    json.dumps(api),
                    env=client_env,
                )
                self.assertEqual(0, code, published)
                self.assertEqual(
                    "identity/session/createSession",
                    published["api"]["api_id"],
                )

                code, search = run_client(
                    "api-search",
                    "authenticated session",
                    env=client_env,
                )
                self.assertEqual(0, code, search)
                self.assertEqual(1, search["count"])
                self.assertEqual(
                    "identity/session/createSession",
                    search["results"][0]["api_id"],
                )
                self.assertNotIn("CDASE_KB_HTTP_URL", client_env)
                self.assertEqual(
                    "Bearer backend-secret",
                    LegacyApiPoolHandler.authorization,
                )
        finally:
            backend.shutdown()
            backend.server_close()
            backend_thread.join(timeout=5)

    @unittest.skipUnless(
        os.environ.get("CDASE_TEST_POSTGRES_URL"),
        "CDASE_TEST_POSTGRES_URL not configured",
    )
    def test_hub_to_postgres_provider_path(self):
        unique = str(time.time_ns())
        with EphemeralHub(
            port=17427,
            env={
                "CDASE_KB_PROVIDER": "postgres",
                "CDASE_KB_JDBC_URL": os.environ["CDASE_TEST_POSTGRES_URL"],
                "CDASE_KB_JDBC_USER": os.environ.get("CDASE_TEST_POSTGRES_USER", ""),
                "CDASE_KB_JDBC_PASSWORD": os.environ.get(
                    "CDASE_TEST_POSTGRES_PASSWORD",
                    "",
                ),
                "CDASE_KB_WRITE_TOKEN": self.token,
            },
        ) as hub_url:
            client_env = self.client_env(CDASE_HUB_URL=hub_url)
            api = {
                "api_id": f"test/hub/postgres-{unique}",
                "system": "test",
                "module": "hub",
                "name": f"postgres{unique}",
                "kind": "METHOD",
                "version": "v1",
                "status": "DEVELOPING",
                "capability": "Verify Hub to PostgreSQL API-pool wiring",
                "signature": f"postgres{unique}()",
                "source": {
                    "repo": "test/repository",
                    "path": "cdase/api/modules/test.api.md",
                    "commit": unique,
                    "owner": "test",
                },
            }
            code, published = run_client(
                "api-publish",
                "--json",
                json.dumps(api),
                env=client_env,
            )
            self.assertEqual(0, code, published)
            code, search = run_client(
                "api-search",
                "PostgreSQL wiring",
                "--system",
                "test",
                env=client_env,
            )
            self.assertEqual(0, code, search)
            self.assertTrue(
                any(row["api_id"] == api["api_id"] for row in search["results"])
            )

    def request(self, method, path, body=None, token=None):
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        data = json.dumps(body).encode() if body is not None else None
        req = Request(self.url + path, data=data, method=method, headers=headers)
        try:
            with urlopen(req, timeout=5) as response:
                return response.status, json.loads(response.read())
        except HTTPError as error:
            try:
                return error.code, json.loads(error.read())
            finally:
                error.close()


if __name__ == "__main__":
    unittest.main()
