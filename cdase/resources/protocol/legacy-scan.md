# Legacy API Scan Protocol

## Purpose

Legacy scanning discovers existing callable APIs before normal CDASE execution.
It is contract discovery, not full-system reverse engineering.

## Session Boundary (HARD STOP)

The scan MUST run in a **new isolated session/agent**.

- The parent runs `legacy-scan-spec` and delegates the returned job packet.
- The scan session is read-only: no repository writes, Hub writes, Features, or Functions.
- The scan session returns strict JSON to the parent.
- Only the parent validates and persists the report.
- If the host cannot launch an isolated session, show the generated prompt and
  ask the user to start a new read-only session. Never silently scan in the parent.

## Deterministic Evidence First

The parent collects evidence from explicit contracts and public surfaces:
OpenAPI/AsyncAPI, GraphQL, protobuf, routes/controllers, exported interfaces,
CLI entry points, and events. Generated, vendor, build, fixture, example, and
test-only trees are excluded.

## Scan Prompt

```text
Mode: CDASE_LEGACY_API_SCAN
Scan ID: <scan-id>
Repository: <repo>
Classification: LEGACY | PARTIAL_LEGACY

You are an isolated, read-only API discovery agent.

Goals:
- Discover existing callable APIs.
- Produce one normalized candidate per API.
- Assign HIGH, MEDIUM, or LOW discovery confidence.
- Provide exact source evidence.

Rules:
- Do not modify files.
- Do not upload to Hub.
- Do not create Features or Functions.
- Inspect only first-party production code.
- Exclude generated, vendor, build, fixture, example, and test-only surfaces.
- Prefer explicit schemas, routes, exported interfaces, CLI commands, and events.
- Use comments only as supporting evidence.
- Never invent missing semantics; record uncertainties explicitly.

Confidence:
- HIGH: explicit public declaration + implementation + corroborating schema/test/call-site.
- MEDIUM: declaration and implementation exist, but semantics/corroboration are incomplete.
- LOW: heuristic inference, dynamic/reflection registration, comments, or uncertain reachability.

Return strict JSON only. Do not include Markdown.
```

## Required Output

```json
{
  "schema": "cdase/legacy-api-scan/v1",
  "scan_id": "<scan-id>",
  "classification": "LEGACY",
  "candidates": [
    {
      "candidate_id": "<stable-id>",
      "api": {
        "system": "...",
        "module": "...",
        "name": "...",
        "kind": "...",
        "capability": "...",
        "signature": "...",
        "inputs": [],
        "outputs": [],
        "errors": [],
        "side_effects": []
      },
      "discovery_confidence": "HIGH",
      "evidence": [
        {"kind": "route", "path": "src/...", "line": 1, "detail": "..."}
      ],
      "uncertainties": []
    }
  ],
  "excluded": []
}
```

## Parent Responsibilities

1. Validate `scan_id`, confidence, candidate uniqueness, and evidence.
2. Persist `/cdase/run_log/legacy_api_scan_<scan-id>.json` and `.md`.
3. Render confidence-grouped multi-select approval (`legacy-approval-spec`).
4. Generate contracts only for selected candidates (`legacy-api-apply`).
5. Do not upload until selected contracts + approval are committed
   (`legacy-api-upload`), then verify with `api-sync --check`
   (`POST /api-pool/verify` → `SYNCED | STALE | MISSING | CONFLICT`).
