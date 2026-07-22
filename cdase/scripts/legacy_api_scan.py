"""Host-neutral legacy API scan evidence and isolated-session job contract."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from repo_maturity import IGNORED_DIRS, TEST_DIRS, classify_repo_maturity

SCAN_SCHEMA = "cdase/legacy-api-scan/v1"
CONFIDENCE = {"HIGH", "MEDIUM", "LOW"}
SOURCE_SUFFIXES = {
    ".java", ".kt", ".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".cs",
    ".php", ".rb", ".rs", ".proto", ".graphql", ".gql", ".yaml", ".yml", ".json",
}

ROUTE_PATTERNS = (
    ("http_route", re.compile(
        r"@(?P<verb>Get|Post|Put|Patch|Delete|Request)Mapping"
        r"(?:\s*\(\s*(?:value\s*=\s*)?[\"'](?P<path>[^\"']+)[\"'])?"
    )),
    ("http_route", re.compile(
        r"@(?P<verb>GET|POST|PUT|PATCH|DELETE)\b(?:[\s\S]{0,120}?@Path\([\"'](?P<path>[^\"']+))?"
    )),
    ("http_route", re.compile(
        r"\b(?:app|router)\.(?P<verb>get|post|put|patch|delete)\s*"
        r"\(\s*[\"'`](?P<path>[^\"'`]+)"
    )),
    ("http_route", re.compile(
        r"@\w+\.(?P<verb>get|post|put|patch|delete)\s*\(\s*[\"'](?P<path>[^\"']+)"
    )),
)

PUBLIC_SYMBOL_PATTERNS = (
    re.compile(r"\bpublic\s+(?:static\s+)?(?:[\w<>,.?\[\]]+\s+)+(?P<name>\w+)\s*\("),
    re.compile(r"\bexport\s+(?:default\s+)?(?:async\s+)?function\s+(?P<name>\w+)\s*\("),
    re.compile(r"\bfunc\s+(?P<name>[A-Z]\w*)\s*\("),
)


def collect_legacy_evidence(repo_root: Path) -> dict:
    """Collect deterministic evidence only; never writes files or calls Hub."""
    root = repo_root.resolve()
    maturity = classify_repo_maturity(root)
    evidence: list[dict] = []

    for path in _candidate_files(root):
        rel = path.relative_to(root).as_posix()
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")[:500_000]
        except OSError:
            continue
        lower = text.lower()

        if path.suffix.lower() in {".yaml", ".yml", ".json"}:
            if re.search(r'(?m)^\s*["\']?openapi["\']?\s*:', text):
                evidence.append(_file_evidence("openapi_schema", rel, 1, "OpenAPI contract"))
            elif re.search(r'(?m)^\s*["\']?asyncapi["\']?\s*:', text):
                evidence.append(_file_evidence("asyncapi_schema", rel, 1, "AsyncAPI contract"))

        if path.suffix.lower() == ".proto":
            for match in re.finditer(r"(?m)^\s*rpc\s+(?P<name>\w+)\s*\((?P<input>[^)]*)\)"
                                     r"\s*returns\s*\((?P<output>[^)]*)\)", text):
                evidence.append(_symbol_evidence(
                    "protobuf_rpc", rel, text, match,
                    f"{match.group('name')}({match.group('input')}) -> {match.group('output')}",
                    match.group("name"),
                ))

        if path.suffix.lower() in {".graphql", ".gql"} and (
            "type query" in lower or "type mutation" in lower
        ):
            evidence.append(_file_evidence(
                "graphql_schema", rel, 1, "GraphQL Query/Mutation schema"
            ))

        for kind, pattern in ROUTE_PATTERNS:
            for match in pattern.finditer(text):
                verb = (match.groupdict().get("verb") or "REQUEST").upper()
                route = match.groupdict().get("path") or "<annotation-defined>"
                evidence.append(_symbol_evidence(
                    kind, rel, text, match, f"{verb} {route}", _route_name(verb, route)
                ))

        for pattern in PUBLIC_SYMBOL_PATTERNS:
            for match in pattern.finditer(text):
                evidence.append(_symbol_evidence(
                    "public_symbol", rel, text, match,
                    f"Public symbol {match.group('name')}", match.group("name")
                ))

    return {
        "schema": "cdase/legacy-evidence/v1",
        "repository": str(root),
        "maturity": maturity,
        "evidence": _deduplicate(evidence),
        "mutation_allowed": False,
        "hub_write_allowed": False,
    }


def build_scan_job(repo_root: Path, evidence: dict | None = None) -> dict:
    """Build the prompt packet the host must run in a fresh isolated session."""
    root = repo_root.resolve()
    evidence = evidence or collect_legacy_evidence(root)
    scan_id = _scan_id(root, evidence)
    return {
        "schema": "cdase/legacy-scan-job/v1",
        "scan_id": scan_id,
        "session": {
            "must_be_new": True,
            "isolation": "fresh",
            "read_only": True,
            "fallback": (
                "If the host cannot launch an isolated agent/session, show this job to "
                "the user and ask them to start a new read-only session. Do not scan in "
                "the parent session."
            ),
        },
        "repository": str(root),
        "classification": evidence["maturity"]["codebase_state"],
        "evidence": evidence["evidence"],
        "prompt": legacy_scan_prompt(scan_id, root, evidence["maturity"]["codebase_state"]),
        "required_output_schema": SCAN_SCHEMA,
    }


def legacy_scan_prompt(scan_id: str, repo_root: Path, classification: str) -> str:
    return f"""Mode: CDASE_LEGACY_API_SCAN
Scan ID: {scan_id}
Repository: {repo_root}
Classification: {classification}

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

Return strict JSON only using schema {SCAN_SCHEMA}. Do not include Markdown."""


def validate_scan_report(report: dict, *, expected_scan_id: str | None = None) -> dict:
    if report.get("schema") != SCAN_SCHEMA:
        raise ValueError(f"scan report schema must be {SCAN_SCHEMA}")
    scan_id = str(report.get("scan_id") or "")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", scan_id):
        raise ValueError("scan_id must be a safe 1-128 character identifier")
    if expected_scan_id and report.get("scan_id") != expected_scan_id:
        raise ValueError("scan_id does not match the isolated scan job")
    candidates = report.get("candidates")
    if not isinstance(candidates, list):
        raise ValueError("candidates must be a list")
    seen: set[str] = set()
    for index, candidate in enumerate(candidates, start=1):
        if not isinstance(candidate, dict):
            raise ValueError(f"candidate {index} must be an object")
        candidate_id = str(candidate.get("candidate_id") or "").strip()
        if not candidate_id or candidate_id in seen:
            raise ValueError(f"candidate {index} has missing/duplicate candidate_id")
        seen.add(candidate_id)
        if candidate.get("discovery_confidence") not in CONFIDENCE:
            raise ValueError(f"candidate {candidate_id} has invalid discovery_confidence")
        if not isinstance(candidate.get("api"), dict):
            raise ValueError(f"candidate {candidate_id} is missing api")
        if not isinstance(candidate.get("evidence"), list) or not candidate["evidence"]:
            raise ValueError(f"candidate {candidate_id} requires evidence")
        for item in candidate["evidence"]:
            if not isinstance(item, dict) or not item.get("path") or not item.get("kind"):
                raise ValueError(f"candidate {candidate_id} has invalid evidence")
        candidate.setdefault("uncertainties", [])
    report.setdefault("excluded", [])
    return report


def render_scan_summary(report: dict) -> str:
    validated = validate_scan_report(report)
    lines = [
        "# Legacy API Scan",
        "",
        f"- Scan ID: {validated['scan_id']}",
        f"- Classification: {validated.get('classification', 'LEGACY')}",
        "",
    ]
    for confidence in ("HIGH", "MEDIUM", "LOW"):
        group = [
            item for item in validated["candidates"]
            if item["discovery_confidence"] == confidence
        ]
        lines.extend([f"## {confidence} ({len(group)})", ""])
        for item in group:
            api = item["api"]
            label = api.get("signature") or api.get("name") or item["candidate_id"]
            lines.append(f"- [{item['candidate_id']}] {label}")
        lines.append("")
    return "\n".join(lines)


def _candidate_files(root: Path):
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in SOURCE_SUFFIXES:
            continue
        relative_parts = path.relative_to(root).parts
        parts = {part.lower() for part in relative_parts[:-1]}
        if (
            parts & IGNORED_DIRS
            or parts & TEST_DIRS
            or (relative_parts and relative_parts[0].lower() == "cdase")
        ):
            continue
        yield path


def _file_evidence(kind: str, path: str, line: int, detail: str) -> dict:
    return {
        "evidence_id": _id(kind, path, str(line), detail),
        "kind": kind,
        "path": path,
        "line": line,
        "symbol": None,
        "detail": detail,
    }


def _symbol_evidence(kind, path, text, match, detail, symbol):
    return {
        "evidence_id": _id(kind, path, symbol, detail),
        "kind": kind,
        "path": path,
        "line": text.count("\n", 0, match.start()) + 1,
        "symbol": symbol,
        "detail": detail,
    }


def _deduplicate(evidence: list[dict]) -> list[dict]:
    return list({item["evidence_id"]: item for item in evidence}.values())


def _route_name(verb: str, route: str) -> str:
    parts = re.findall(r"[A-Za-z0-9]+", route)
    return verb.lower() + "".join(part.title() for part in parts)


def _scan_id(root: Path, evidence: dict) -> str:
    payload = json.dumps(evidence["evidence"], sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256((str(root) + payload).encode()).hexdigest()[:10]
    now = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"legacy-scan-{now}-{digest}"


def _id(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:12]
