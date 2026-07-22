"""Parse and compare canonical CDASE API registry definitions."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


def parse_api_blocks(text: str) -> list[dict]:
    blocks = re.findall(
        r"```json\s+cdase-api\s*\n(.*?)\n```",
        text,
        flags=re.DOTALL,
    )
    definitions = []
    for index, block in enumerate(blocks, start=1):
        try:
            definitions.append(json.loads(block))
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid cdase-api block {index}: {exc}") from exc
    return definitions


def find_api_definition(path: Path, api_id: str, version: str) -> dict:
    for definition in parse_api_blocks(path.read_text()):
        if definition.get("api_id") == api_id and definition.get("version") == version:
            return definition
    raise ValueError(f"{api_id}@{version} not found in {path}")


def content_hash(definition: dict) -> str:
    lines = [
        f"System: {definition.get('system')}",
        f"Module: {definition.get('module')}",
        f"API: {definition.get('name')}",
        f"Kind: {str(definition.get('kind') or 'METHOD').upper()}",
        f"Capability: {definition.get('capability')}",
        f"Signature: {definition.get('signature')}",
    ]
    _add_lines(lines, "Use when", definition.get("use_when") or [])
    _add_lines(lines, "Do not use when", definition.get("do_not_use_when") or [])
    for parameter in definition.get("inputs") or []:
        lines.append(
            "Input: "
            + str(parameter.get("name"))
            + " "
            + _empty(parameter.get("type"))
            + " "
            + _empty(parameter.get("description"))
        )
    for parameter in definition.get("outputs") or []:
        lines.append(
            "Output: "
            + str(parameter.get("name"))
            + " "
            + _empty(parameter.get("type"))
            + " "
            + _empty(parameter.get("description"))
        )
    for error in definition.get("errors") or []:
        lines.append(
            "Error: " + str(error.get("code")) + " " + _empty(error.get("description"))
        )
    _add_lines(lines, "Side effect", definition.get("side_effects") or [])
    if definition.get("auth") is not None:
        lines.append("Authorization: " + str(definition["auth"]))
    if definition.get("idempotency") is not None:
        lines.append("Idempotency: " + str(definition["idempotency"]))
    return hashlib.sha256("\n".join(lines).encode()).hexdigest()


def sync_state(definition: dict, remote_response: dict, *, commit: str | None) -> dict:
    api_id = definition.get("api_id")
    version = definition.get("version")
    if remote_response.get("error"):
        code = remote_response.get("status")
        state = "MISSING" if code == 404 or "not found" in str(
            remote_response.get("error")
        ).lower() else "CONFLICT"
        return {"api_id": api_id, "version": version, "state": state}
    remote = remote_response.get("api") or remote_response
    local_source = definition.get("source") or {}
    remote_source = remote.get("source") or {}
    if remote_source.get("repo") != local_source.get("repo"):
        state = "CONFLICT"
        reasons = ["source repository ownership differs"]
    else:
        reasons = []
        if remote.get("content_hash") != content_hash(definition):
            reasons.append("semantic content hash differs")
        expected_commit = _effective_commit(local_source.get("commit"), commit)
        if expected_commit and remote_source.get("commit") != expected_commit:
            reasons.append("source commit differs")
        if remote_source.get("path") != local_source.get("path"):
            reasons.append("source path differs")
        state = "STALE" if reasons else "SYNCED"
    return {
        "api_id": api_id,
        "version": version,
        "state": state,
        "reasons": reasons,
        "local_content_hash": content_hash(definition),
        "remote_content_hash": remote.get("content_hash"),
    }


def legacy_publish_gate(
    definition: dict,
    *,
    git_root: Path | None,
    registry_repo_path: str,
) -> str | None:
    """Return an error message if a LEGACY_IMPORT block may not be api-sync'd."""
    if str(definition.get("origin") or "NATIVE").upper() != "LEGACY_IMPORT":
        return None
    approval_ref = str(definition.get("approval_ref") or "").strip()
    if not approval_ref:
        return (
            f"{definition.get('api_id')}@{definition.get('version')} is LEGACY_IMPORT "
            "but missing approval_ref — use legacy-api-apply then legacy-api-upload"
        )
    if not definition.get("scan_id"):
        return (
            f"{definition.get('api_id')}@{definition.get('version')} is LEGACY_IMPORT "
            "but missing scan_id"
        )
    if definition.get("discovery_confidence") not in {"HIGH", "MEDIUM", "LOW"}:
        return (
            f"{definition.get('api_id')}@{definition.get('version')} is LEGACY_IMPORT "
            "but discovery_confidence is invalid"
        )
    if git_root is None:
        return "legacy API publish requires a git repository"
    for repo_path in (approval_ref, registry_repo_path):
        error = _require_committed(git_root, repo_path)
        if error:
            return error
    return None


def with_source_revision(definition: dict, *, path: str, commit: str | None) -> dict:
    updated = json.loads(json.dumps(definition))
    source = dict(updated.get("source") or {})
    source["path"] = path
    if commit and (
        not source.get("commit") or str(source.get("commit")).startswith("<")
    ):
        source["commit"] = commit
    updated["source"] = source
    return updated


def _effective_commit(value, commit):
    return commit if commit and (not value or str(value).startswith("<")) else value


def _require_committed(git_root: Path, repo_path: str) -> str | None:
    import subprocess

    tracked = subprocess.run(
        ["git", "ls-files", "--error-unmatch", "--", repo_path],
        cwd=git_root,
        capture_output=True,
        text=True,
    )
    if tracked.returncode != 0:
        return f"legacy API requires committed file: {repo_path}"
    dirty = subprocess.run(
        ["git", "status", "--porcelain", "--", repo_path],
        cwd=git_root,
        capture_output=True,
        text=True,
    )
    if dirty.stdout.strip():
        return f"legacy API requires clean committed file: {repo_path}"
    return None


def _add_lines(lines, label, values):
    for value in values:
        lines.append(f"{label}: {value}")


def _empty(value):
    return "" if value is None else str(value)
