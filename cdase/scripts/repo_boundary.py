"""Validate that shared paths and content stay within the repository boundary."""

from __future__ import annotations

import os
from pathlib import Path

# Paths always blocked even if readable (outside repo tree)
FORBIDDEN_PREFIXES = (
    Path.home() / ".cursor" / "cdase",
    Path.home() / ".ssh",
    Path.home() / ".aws",
)

MAX_AUTO_FILE_BYTES = 256 * 1024


def find_git_root(start: Path) -> Path | None:
    current = start.resolve()
    for candidate in [current, *current.parents]:
        if (candidate / ".git").exists():
            return candidate
    return None


def resolve_repo_path(raw: str, cdase_root: Path, git_root: Path | None) -> tuple[Path | None, str | None]:
    """Resolve raw path and ensure it lies under git root (repo boundary)."""
    path = Path(raw).expanduser()
    if not path.is_absolute():
        for base in (Path.cwd(), cdase_root, git_root or cdase_root):
            if base is None:
                continue
            candidate = (base / path).resolve()
            if candidate.exists():
                path = candidate
                break
        else:
            path = (Path.cwd() / path).resolve()

    path = path.resolve()

    for forbidden in FORBIDDEN_PREFIXES:
        try:
            path.relative_to(forbidden.resolve())
            return None, f"path is outside repo boundary (forbidden area: {forbidden})"
        except ValueError:
            pass

    if git_root is None:
        return None, "not a git repository — cannot verify repo boundary for file send"

    try:
        path.relative_to(git_root.resolve())
    except ValueError:
        return None, f"path must be inside repository ({git_root}), got {path}"

    if not path.is_file():
        return None, f"not a file: {path}"

    return path, None


def read_repo_file(path: Path, git_root: Path) -> tuple[str, dict]:
    rel = path.relative_to(git_root.resolve()).as_posix()
    size = path.stat().st_size
    if size > MAX_AUTO_FILE_BYTES:
        return (
            f"[CDASE file reference — too large for auto-send ({size} bytes)]\n"
            f"repo_path: {rel}\n"
            f"Ask the owning user to share explicitly if full content is required.",
            {"repo_path": rel, "size": size, "truncated": True},
        )
    content = path.read_text(encoding="utf-8", errors="replace")
    return content, {"repo_path": rel, "size": size, "truncated": False}


def classify_message_body(body: str, git_root: Path | None) -> str | None:
    """Best-effort warning if body appears to reference outside-repo secrets."""
    if git_root is None:
        return None
    home = str(Path.home())
    if home in body and str(git_root) not in body:
        for marker in ("/.cursor/cdase", "/.ssh/", "/.env", "API_KEY", "SECRET"):
            if marker in body:
                return (
                    f"message may contain out-of-repo sensitive paths or secrets ({marker}); "
                    "get user permission before sending"
                )
    return None
