"""Classify CDASE adoption separately from codebase maturity."""

from __future__ import annotations

import re
from pathlib import Path

IGNORED_DIRS = {
    ".git", ".idea", ".vscode", ".cursor", ".venv", "venv", "node_modules",
    "vendor", "dist", "build", "target", "out", "coverage", "generated",
    "__pycache__", ".pytest_cache", ".mypy_cache",
}
TEST_DIRS = {"test", "tests", "__tests__", "fixtures", "examples", "samples"}
SOURCE_SUFFIXES = {
    ".java", ".kt", ".kts", ".scala", ".py", ".js", ".jsx", ".ts", ".tsx",
    ".go", ".rs", ".cs", ".php", ".rb", ".swift", ".c", ".cc", ".cpp", ".h",
    ".hpp", ".proto", ".graphql", ".gql",
}
PUBLIC_SURFACE_PATTERNS = (
    re.compile(r"(@(?:Get|Post|Put|Patch|Delete|Request)Mapping|@Path|@GET|@POST)\b"),
    re.compile(r"\b(app|router)\.(get|post|put|patch|delete|use)\s*\("),
    re.compile(r"\b(FastAPI|APIRouter|Flask)\s*\("),
    re.compile(r"\b(public\s+(class|interface|[\w<>\[\]]+\s+\w+\s*\())"),
    re.compile(r"\b(export\s+(default\s+)?(class|function|const|interface|type))"),
    re.compile(r"\bfunc\s+[A-Z]\w*\s*\("),
    re.compile(r"\b(command|subcommand|click\.command|typer\.command)\b", re.IGNORECASE),
    re.compile(r"\b(publish|emit|subscribe|consumer|producer)\b", re.IGNORECASE),
)


def classify_repo_maturity(repo_root: Path) -> dict:
    """Return orthogonal CDASE adoption and codebase-state signals."""
    root = repo_root.resolve()
    context = root / "cdase" / "context"
    adoption_state = "CDASE_INITIALIZED" if context.is_dir() else "CDASE_UNINITIALIZED"

    source_files: list[str] = []
    public_surface_files: list[str] = []
    for path in _walk_first_party(root):
        rel = path.relative_to(root)
        source_files.append(rel.as_posix())
        if _contains_public_surface(path):
            public_surface_files.append(rel.as_posix())

    registry_files = sorted(
        p.relative_to(root).as_posix()
        for p in (root / "cdase" / "api" / "modules").glob("*.api.md")
        if p.is_file()
    ) if (root / "cdase" / "api" / "modules").is_dir() else []

    has_implementation = bool(source_files)
    if not has_implementation:
        codebase_state = "GREENFIELD"
    elif adoption_state == "CDASE_UNINITIALIZED":
        codebase_state = "LEGACY"
    elif not registry_files:
        codebase_state = "PARTIAL_LEGACY"
    else:
        codebase_state = "MANAGED"

    return {
        "adoption_state": adoption_state,
        "codebase_state": codebase_state,
        "signals": {
            "first_party_source_count": len(source_files),
            "public_surface_count": len(public_surface_files),
            "api_registry_count": len(registry_files),
            "first_party_sources": source_files[:100],
            "public_surface_files": public_surface_files[:100],
            "api_registry_files": registry_files[:100],
        },
        "legacy_scan_recommended": codebase_state in {"LEGACY", "PARTIAL_LEGACY"},
    }


def _walk_first_party(root: Path):
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in SOURCE_SUFFIXES:
            continue
        rel_parts = path.relative_to(root).parts
        lowered = {part.lower() for part in rel_parts[:-1]}
        if lowered & IGNORED_DIRS or lowered & TEST_DIRS:
            continue
        if rel_parts and rel_parts[0].lower() == "cdase":
            continue
        name = path.name.lower()
        if name.endswith(("_test.py", ".test.js", ".test.ts", ".spec.js", ".spec.ts")):
            continue
        try:
            if path.stat().st_size == 0:
                continue
        except OSError:
            continue
        yield path


def _contains_public_surface(path: Path) -> bool:
    if path.suffix.lower() in {".proto", ".graphql", ".gql"}:
        return True
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")[:250_000]
    except OSError:
        return False
    return any(pattern.search(text) for pattern in PUBLIC_SURFACE_PATTERNS)
