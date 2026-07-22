# Module API Registry: <system>/<module>

> Canonical source for APIs owned by this repository. The Global API Pool is the
> discovery projection. Every `cdase-api` JSON block is independently publishable
> with `cdase_client.py api-sync <this-file>`.
>
> Before adding a block, search the Global API Pool and resolve exactly one:
> REUSE, EVOLVE, or CREATE. CREATE begins as `DEVELOPING`.

## API: <operation name>

```json cdase-api
{
  "api_id": "organization/system/module/operation",
  "system": "system",
  "module": "module",
  "name": "operation",
  "kind": "REST",
  "version": "v1",
  "status": "DEVELOPING",
  "capability": "One semantic sentence describing what this API provides",
  "use_when": [
    "Condition in which callers should reuse this API"
  ],
  "do_not_use_when": [
    "Semantically similar condition this API does not satisfy"
  ],
  "signature": "POST /resource or package.Class.method(Type) -> Type",
  "inputs": [
    {
      "name": "input",
      "type": "string",
      "description": "Meaning and constraints",
      "required": true
    }
  ],
  "outputs": [
    {
      "name": "result",
      "type": "string",
      "description": "Observable result",
      "required": true
    }
  ],
  "errors": [
    {
      "code": "ERROR_CODE",
      "description": "Exact failure condition"
    }
  ],
  "side_effects": [
    "State change or emitted event"
  ],
  "auth": "Required permission or public",
  "idempotency": "Idempotency key/behavior or none",
  "origin": "NATIVE",
  "source": {
    "repo": "host/organization/repository",
    "path": "cdase/api/modules/<module>.api.md",
    "commit": "<git commit>",
    "owner": "<team/user>"
  },
  "relations": [
    {
      "type": "DEPENDS_ON",
      "target_api_id": "organization/system/module/otherOperation",
      "target_version": "v1"
    }
  ]
}
```

For an approved legacy import, replace `"origin": "NATIVE"` with:

```json
{
  "origin": "LEGACY_IMPORT",
  "discovery_confidence": "HIGH",
  "scan_id": "legacy-scan-...",
  "approval_ref": "cdase/run_log/legacy_api_approval_....json",
  "discovery_evidence": [
    {
      "kind": "http_route",
      "path": "src/...",
      "line": 1,
      "symbol": "GET /resource",
      "detail": "Explicit route declaration and implementation"
    }
  ]
}
```

These provenance fields are relational audit metadata. They are not part of the
semantic content hash or embedding text.

## Lifecycle Rules

- `DEVELOPING`: globally reserved; coordinate rather than duplicate.
- `RELEASED`: implemented, tested, and preferred for reuse.
- `SUPERSEDED`: replaced by a newer version.
- `DEPRECATED`: still callable but discouraged.
- `RETIRED`: unavailable to new consumers.
- Upgrade by adding a new version, releasing it, then marking the old version
  `SUPERSEDED`; do not rewrite a released contract.
