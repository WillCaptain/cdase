#!/usr/bin/env python3
"""Resolve CDASE runtime root (consumer project's cdase/ folder with context/)."""

from __future__ import annotations

import os
from pathlib import Path


def _inside_hub_dir(path: Path, methodology_root: Path) -> bool:
    hub_dir = (methodology_root / "hub").resolve()
    try:
        path.resolve().relative_to(hub_dir)
        return True
    except ValueError:
        return False


def find_cdase_root(scripts_dir: Path) -> Path:
    """Find the cdase runtime folder containing context/ (or consumer cdase/).

    Search order:
    1. CDASE_ROOT environment variable
    2. ./cdase, cwd, parents (consumer project layout)
    3. methodology repo cdase/ (skill package parent)
    4. default: cwd/cdase (may not exist yet — bootstrap will create context/)
    """
    if env := os.environ.get("CDASE_ROOT"):
        return Path(env).resolve()

    skill_root = scripts_dir.parent
    methodology_root = skill_root.parent

    candidates: list[Path] = [
        Path.cwd() / "cdase",
        Path.cwd(),
        methodology_root / "cdase",
        methodology_root,
    ]
    for parent in Path.cwd().parents:
        candidates.extend([parent / "cdase", parent])

    seen: set[Path] = set()
    for path in candidates:
        p = path.resolve()
        if p in seen:
            continue
        seen.add(p)
        if _inside_hub_dir(p, methodology_root) and not (p / "context").is_dir():
            continue
        if (p / "context").is_dir():
            return p

    fallback = (Path.cwd() / "cdase").resolve()
    if _inside_hub_dir(fallback, methodology_root):
        return (methodology_root / "cdase").resolve()
    return fallback
