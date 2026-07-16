#!/usr/bin/env python3
"""Resolve CDASE consumer runtime root (<project-repo>/cdase/, not the framework repo)."""

from __future__ import annotations

import os
from pathlib import Path

from repo_discovery import methodology_roots, resolve_consumer_cdase_root


def find_cdase_root(scripts_dir: Path) -> Path:
    """Find consumer cdase/ folder for the active project repo.

    Never returns the CDASE framework/methodology repo's skill package as runtime.
    Set CDASE_ROOT explicitly when multiple consumer repos exist in the workspace.
    """
    if env := os.environ.get("CDASE_ROOT"):
        return Path(env).resolve()

    resolved = resolve_consumer_cdase_root(scripts_dir)
    if resolved is not None:
        blocked = methodology_roots(scripts_dir)
        if resolved.resolve() not in blocked and not (resolved / "SKILL.md").is_file():
            return resolved.resolve()

    # Last resort: use repos discovered inside workspace boundary only (no parent walk)
    from repo_discovery import classify_workspace, consumer_cdase_dir

    info = classify_workspace()
    repos = [r for r in info["repos"] if not r["is_framework"]]
    if len(repos) == 1:
        return consumer_cdase_dir(Path(repos[0]["path"])).resolve()
    if info["consumer_repos_without_cdase"]:
        return consumer_cdase_dir(Path(info["consumer_repos_without_cdase"][0]["path"])).resolve()

    return (Path.cwd() / "cdase").resolve()
