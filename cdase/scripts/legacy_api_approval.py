"""Persist legacy scan reports and apply user-approved API selections."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from legacy_api_scan import render_scan_summary, validate_scan_report


def save_scan_report(cdase_root: Path, report: dict) -> dict:
    report = validate_scan_report(report)
    run_log = cdase_root / "run_log"
    run_log.mkdir(parents=True, exist_ok=True)
    stem = report["scan_id"].replace("/", "-")
    json_path = run_log / f"legacy_api_scan_{stem}.json"
    markdown_path = run_log / f"legacy_api_scan_{stem}.md"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    markdown_path.write_text(render_scan_summary(report) + "\n")
    return {"json": str(json_path), "markdown": str(markdown_path)}


def build_approval_spec(report: dict) -> dict:
    report = validate_scan_report(report)
    options = []
    for confidence in ("HIGH", "MEDIUM", "LOW"):
        for candidate in report["candidates"]:
            if candidate["discovery_confidence"] != confidence:
                continue
            api = candidate["api"]
            label = api.get("signature") or api.get("name") or candidate["candidate_id"]
            options.append({
                "id": candidate["candidate_id"],
                "label": f"[{confidence}] {label}",
                "group": confidence,
                "selected": confidence == "HIGH",
                "description": "; ".join(candidate.get("uncertainties") or []) or None,
            })
    return {
        "preset": "legacy.api.approval",
        "kind": "multi_choice",
        "title": "Approve legacy APIs for registry generation and upload",
        "description": (
            "HIGH candidates are selected by default. Review and select any combination "
            "across HIGH, MEDIUM, and LOW. No Hub upload occurs until committed."
        ),
        "options": options,
        "shortcuts": [
            {"id": "high", "label": "HIGH only (recommended)"},
            {"id": "high_medium", "label": "HIGH + MEDIUM"},
            {"id": "all", "label": "All candidates"},
            {"id": "none", "label": "Upload none"},
        ],
        "fallback_prompt": (
            "Reply with candidate IDs to approve, comma-separated; "
            "or HIGH, HIGH+MEDIUM, ALL, NONE."
        ),
        "render_hint": (
            "Use the host's multi-select UI if available; otherwise use grouped numbered "
            "choices and accept comma-separated IDs."
        ),
        "on_submit": {
            "handler": "agent",
            "command_hint": (
                "legacy-api-apply --report <report.json> "
                "--selection-json '{\"selected\":[\"...\"]}'"
            ),
        },
    }


def resolve_selection(report: dict, selection: dict) -> list[str]:
    report = validate_scan_report(report)
    candidates = {item["candidate_id"]: item for item in report["candidates"]}
    shortcut = str(selection.get("shortcut") or "").lower()
    if shortcut == "high":
        selected = [
            cid for cid, item in candidates.items()
            if item["discovery_confidence"] == "HIGH"
        ]
    elif shortcut in {"high_medium", "high+medium"}:
        selected = [
            cid for cid, item in candidates.items()
            if item["discovery_confidence"] in {"HIGH", "MEDIUM"}
        ]
    elif shortcut == "all":
        selected = list(candidates)
    elif shortcut == "none":
        selected = []
    else:
        selected = [str(value) for value in selection.get("selected", [])]
    unknown = sorted(set(selected) - set(candidates))
    if unknown:
        raise ValueError("unknown candidate ids: " + ", ".join(unknown))
    return list(dict.fromkeys(selected))


def apply_approved_candidates(
    cdase_root: Path,
    report: dict,
    selection: dict,
    *,
    repo_id: str,
    owner: str,
) -> dict:
    """Write only selected API blocks and a committed approval manifest."""
    report = validate_scan_report(report)
    selected_ids = resolve_selection(report, selection)
    selected = [
        item for item in report["candidates"]
        if item["candidate_id"] in selected_ids
    ]
    run_log = cdase_root / "run_log"
    modules_dir = cdase_root / "api" / "modules"
    run_log.mkdir(parents=True, exist_ok=True)
    modules_dir.mkdir(parents=True, exist_ok=True)

    approval_rel = f"cdase/run_log/legacy_api_approval_{report['scan_id']}.json"
    approval_path = cdase_root.parent / approval_rel
    approved_at = datetime.now(timezone.utc).isoformat()
    manifest = {
        "schema": "cdase/legacy-api-approval/v1",
        "scan_id": report["scan_id"],
        "approved_by": owner,
        "approved_at": approved_at,
        "selected": selected_ids,
        "report": f"cdase/run_log/{report['scan_id']}.json",
    }
    written: list[str] = []
    approved_apis: list[dict] = []
    for candidate in selected:
        definition = _definition(
            candidate,
            repo_id=repo_id,
            owner=owner,
            scan_id=report["scan_id"],
            approval_ref=approval_rel,
        )
        module_slug = _slug(definition["module"])
        registry = modules_dir / f"{module_slug}.api.md"
        approved_apis.append({
            "candidate_id": candidate["candidate_id"],
            "api_id": definition["api_id"],
            "version": definition["version"],
            "registry": str(registry.relative_to(cdase_root.parent)),
        })
        existing = registry.read_text() if registry.exists() else (
            f"# Module API Registry: {definition['system']}/{definition['module']}\n\n"
        )
        if f'"api_id": "{definition["api_id"]}"' in existing:
            continue
        block = (
            f"## API: {definition['name']}\n\n"
            "```json cdase-api\n"
            + json.dumps(definition, indent=2, ensure_ascii=False)
            + "\n```\n"
        )
        registry.write_text(existing.rstrip() + "\n\n" + block)
        written.append(str(registry))
    manifest["apis"] = approved_apis
    approval_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")

    return {
        "ok": True,
        "scan_id": report["scan_id"],
        "selected": selected_ids,
        "written": written,
        "approval": str(approval_path),
        "upload_performed": False,
        "next": "commit registry + approval files, then run legacy-api-upload",
    }


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def _definition(candidate, *, repo_id, owner, scan_id, approval_ref):
    api = dict(candidate["api"])
    system = _slug(str(api.get("system") or "legacy"))
    module = _slug(str(api.get("module") or "unknown"))
    name = _slug(str(api.get("name") or candidate["candidate_id"]))
    api_id = str(api.get("api_id") or f"{repo_id}/{system}/{module}/{name}")
    return {
        "api_id": api_id,
        "system": system,
        "module": module,
        "name": name,
        "kind": str(api.get("kind") or "METHOD").upper(),
        "version": str(api.get("version") or "v1"),
        "status": "RELEASED",
        "capability": str(api.get("capability") or f"Legacy API {name}"),
        "use_when": list(api.get("use_when") or []),
        "do_not_use_when": list(api.get("do_not_use_when") or []),
        "signature": str(api.get("signature") or name),
        "inputs": list(api.get("inputs") or []),
        "outputs": list(api.get("outputs") or []),
        "errors": list(api.get("errors") or []),
        "side_effects": list(api.get("side_effects") or []),
        "auth": api.get("auth"),
        "idempotency": api.get("idempotency"),
        "origin": "LEGACY_IMPORT",
        "discovery_confidence": candidate["discovery_confidence"],
        "scan_id": scan_id,
        "approval_ref": approval_ref,
        "discovery_evidence": candidate["evidence"],
        "source": {
            "repo": repo_id,
            "path": f"cdase/api/modules/{module}.api.md",
            "commit": "<pending-commit>",
            "owner": owner,
        },
        "relations": list(api.get("relations") or []),
    }


def _slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_-]+", "-", value.strip()).strip("-")
    return slug or "unknown"
