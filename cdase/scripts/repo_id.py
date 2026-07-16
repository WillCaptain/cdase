"""Resolve repo_id — stable team scope key for cdase-hub."""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from urllib.parse import urlparse

SCP_RE = re.compile(r"^[^@]+@[^:]+:(.+)$")


def normalize_git_remote(url: str) -> str | None:
    """Turn a git remote URL into a stable repo_id (host/org/repo)."""
    url = url.strip()
    if not url:
        return None
    if url.endswith(".git"):
        url = url[:-4]
    m = SCP_RE.match(url)
    if m:
        path = m.group(1).strip("/")
        host = url.split("@", 1)[1].split(":", 1)[0]
        return f"{host}/{path}".lower()
    if "://" not in url:
        return url.lower().strip("/")
    parsed = urlparse(url)
    host = parsed.hostname or ""
    path = parsed.path.strip("/")
    if not host or not path:
        return None
    return f"{host}/{path}".lower()


def git_origin_remote(git_root: Path | None) -> str | None:
    if git_root is None:
        return None
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=git_root,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return None
        return result.stdout.strip() or None
    except (OSError, subprocess.TimeoutExpired):
        return None


def resolve_repo_id(
    cdase_root: Path,
    git_root: Path | None,
    settings: dict | None = None,
) -> tuple[str | None, str]:
    """Return (repo_id, source). repo_id is required for hub team scoping."""
    settings = settings or {}

    if env := os.environ.get("CDASE_REPO_ID"):
        return env.strip(), "CDASE_REPO_ID"

    if rid := settings.get("repo_id"):
        return str(rid).strip(), "setting"

    remote = git_origin_remote(git_root)
    if remote:
        normalized = normalize_git_remote(remote)
        if normalized:
            return normalized, "git_remote_origin"

    if git_root is not None:
        return git_root.name.lower(), "git_dirname"

    return None, "none"
