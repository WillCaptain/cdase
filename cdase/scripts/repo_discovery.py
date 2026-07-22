"""Discover git repos in a workspace and locate consumer CDASE runtimes.

Consumer runtime = `<project-repo>/cdase/` with `context/` (team SSOT).
Framework repo = the CDASE methodology repo itself (`cdase/SKILL.md` at repo root).
Never treat the framework repo as the consumer runtime.
"""

from __future__ import annotations

import os
from pathlib import Path

from repo_boundary import find_git_root
from repo_maturity import classify_repo_maturity


def skill_package_dir(repo_root: Path) -> Path:
    return repo_root / "cdase"


def is_framework_repo(repo_root: Path) -> bool:
    """True when this git repo IS the CDASE methodology/framework checkout."""
    return (skill_package_dir(repo_root) / "SKILL.md").is_file()


def consumer_cdase_dir(repo_root: Path) -> Path:
    return repo_root / "cdase"


def has_consumer_cdase(repo_root: Path) -> bool:
    """True when the repo has an initialized consumer runtime (context/ exists)."""
    if is_framework_repo(repo_root):
        return False
    return (consumer_cdase_dir(repo_root) / "context").is_dir()


def needs_consumer_cdase_init(repo_root: Path) -> bool:
    """True for a non-framework git repo that lacks consumer cdase/context/."""
    if is_framework_repo(repo_root):
        return False
    return not (consumer_cdase_dir(repo_root) / "context").is_dir()


def is_git_repo(path: Path) -> bool:
    return (path / ".git").exists()


def is_under(path: Path, ancestor: Path) -> bool:
    """True if path is ancestor or a descendant of ancestor."""
    try:
        path.resolve().relative_to(ancestor.resolve())
        return True
    except ValueError:
        return path.resolve() == ancestor.resolve()


def resolve_workspace_root(start: Path | None = None) -> Path:
    """Best-effort workspace folder (the directory Cursor opened).

    Search stays inside this boundary — never parent folders like a sibling `cdase/`
    framework checkout.
    """
    if env := os.environ.get("CDASE_WORKSPACE"):
        return Path(env).expanduser().resolve()

    start = (start or Path.cwd()).resolve()
    current = start

    for _ in range(12):
        if is_git_repo(current):
            return current
        try:
            child_repos = [
                c for c in current.iterdir()
                if c.is_dir() and not c.name.startswith(".") and is_git_repo(c)
            ]
        except OSError:
            child_repos = []
        if child_repos:
            return current
        parent = current.parent
        if parent == current:
            break
        current = parent

    return start


def discover_git_repos_in_workspace(workspace: Path) -> list[Path]:
    """Git repos whose root lies inside workspace (children or workspace itself)."""
    boundary = workspace.resolve()
    found: list[Path] = []
    seen: set[Path] = set()

    def add(repo: Path) -> None:
        root = repo.resolve()
        if root in seen or not is_git_repo(root):
            return
        if not is_under(root, boundary):
            return
        seen.add(root)
        found.append(root)

    if is_git_repo(boundary):
        add(boundary)
        return found

    for repo in discover_child_git_repos(boundary):
        add(repo)

    # When start path is deep inside a child repo (e.g. workspace/src/), attach that repo
    start = Path.cwd().resolve()
    if is_under(start, boundary):
        git_root = find_git_root(start)
        if git_root and is_under(git_root.resolve(), boundary):
            add(git_root)

    return sorted(found, key=lambda p: p.name.lower())


def discover_child_git_repos(workspace: Path, *, max_depth: int = 2) -> list[Path]:
    """Find git repo roots directly under workspace (shallow scan)."""
    workspace = workspace.resolve()
    found: list[Path] = []
    seen: set[Path] = set()

    def add(repo: Path) -> None:
        root = repo.resolve()
        if root not in seen and is_git_repo(root):
            seen.add(root)
            found.append(root)

    if is_git_repo(workspace):
        add(workspace)
        return found

    try:
        for child in sorted(workspace.iterdir()):
            if not child.is_dir() or child.name.startswith("."):
                continue
            if is_git_repo(child):
                add(child)
            elif max_depth > 1:
                for grand in child.iterdir():
                    if grand.is_dir() and is_git_repo(grand):
                        add(grand)
    except OSError:
        pass

    return sorted(found, key=lambda p: p.name.lower())


def repo_entry(repo_root: Path) -> dict:
    root = repo_root.resolve()
    framework = is_framework_repo(root)
    cdase = consumer_cdase_dir(root)
    initialized = has_consumer_cdase(root)
    entry = {
        "path": str(root),
        "name": root.name,
        "is_framework": framework,
        "has_cdase": initialized,
        "needs_init": needs_consumer_cdase_init(root),
        "cdase_root": str(cdase) if initialized else None,
    }
    if not framework:
        entry.update(classify_repo_maturity(root))
    return entry


def classify_workspace(workspace: Path | None = None) -> dict:
    """Classify workspace and list repos for agent repo-selection logic."""
    start = (workspace or Path.cwd()).resolve()
    ws = resolve_workspace_root(start)
    repos = discover_git_repos_in_workspace(ws)

    entries = [repo_entry(r) for r in repos]

    framework = [e for e in entries if e["is_framework"]]
    consumer_with = [e for e in entries if not e["is_framework"] and e["has_cdase"]]
    consumer_without = [e for e in entries if not e["is_framework"] and e["needs_init"]]

    workspace_is_git = is_git_repo(ws)

    bootstrap_policy = None
    if not entries:
        scenario = "1_no_git"
        hint = (
            "Workspace is not a git repo and no child repos found. "
            "Initialize git first, or open the target project repo directly."
        )
    elif len(entries) == 1:
        only = entries[0]
        if only["is_framework"]:
            scenario = "1_framework_only"
            hint = (
                "Workspace IS (or is inside) the CDASE framework repo — do NOT create "
                "consumer cdase/ here. Open the target application repo (or a parent "
                "folder containing it) and run discover again."
            )
        elif only["has_cdase"]:
            scenario = "1_ready"
            hint = f"Use CDASE_ROOT={only['cdase_root']} for all CDASE operations."
        else:
            scenario = "1_needs_init"
            hint = f"Initialize consumer cdase/ at {only['path']}/cdase/ and commit it."
    elif not consumer_with and not consumer_without and framework:
        scenario = "1_framework_only"
        hint = (
            "Only the CDASE framework repo is in scope — do NOT create consumer cdase/ "
            "here. Open the application project repo."
        )
    elif consumer_with and consumer_without:
        scenario = "2c_mixed"
        hint = (
            "Some repos have cdase/, some do not. Show existing identities from repos "
            "that have cdase/. Ask user to confirm or enter new profile. Then ask: init "
            "ALL repos still missing cdase/ with that same user, or NONE of them?"
        )
    elif consumer_without and not consumer_with:
        scenario = "2b_none_have_cdase"
        hint = (
            "Multiple application repos, none have consumer cdase/. Ask user: apply CDASE "
            "to ALL repos with the same user identity, or to NONE? On all: collect profile "
            "once, init + commit cdase/ in every non-framework repo. On none: do not init. "
            "Never initialize the framework repo."
        )
    elif consumer_with and not consumer_without:
        scenario = "2_all_have_cdase"
        hint = (
            "All non-framework repos already have cdase/. Ask which repo to work in if "
            "ambiguous; set CDASE_ROOT to that repo's cdase/."
        )
    else:
        scenario = "2a_no_consumer_repos"
        hint = "Only framework repo(s) detected. Switch workspace to the application project."

    if scenario in ("2b_none_have_cdase", "2c_mixed"):
        bootstrap_policy = "all_or_none"

    active = None
    if len(consumer_with) == 1 and not consumer_without:
        active = consumer_with[0]["cdase_root"]
    elif workspace_is_git and len(entries) == 1 and entries[0]["has_cdase"]:
        active = entries[0]["cdase_root"]

    return {
        "workspace": str(ws),
        "workspace_resolved_from": str(start),
        "workspace_is_git_repo": workspace_is_git,
        "scenario": scenario,
        "hint": hint,
        "bootstrap_policy": bootstrap_policy,
        "active_cdase_root": active,
        "repos": entries,
        "framework_repos": framework,
        "consumer_repos_with_cdase": consumer_with,
        "consumer_repos_without_cdase": consumer_without,
        "repos_to_bootstrap": consumer_without if bootstrap_policy == "all_or_none" else [],
        "note": "Only repos inside the workspace folder are listed — parent folders are never scanned.",
    }


def resolve_consumer_cdase_root(
    scripts_dir: Path,
    *,
    workspace: Path | None = None,
) -> Path | None:
    """Best-effort resolve consumer cdase/ root; None if ambiguous or framework-only."""
    if env := os.environ.get("CDASE_ROOT"):
        p = Path(env).resolve()
        if (p / "context").is_dir() and not (p / "SKILL.md").is_file():
            return p
        # Explicit override even before context/ exists (bootstrap)
        if not (p / "SKILL.md").is_file():
            return p

    info = classify_workspace(workspace)
    if info["active_cdase_root"]:
        return Path(info["active_cdase_root"]).resolve()

    without = info["consumer_repos_without_cdase"]
    if len(without) == 1 and not info["consumer_repos_with_cdase"]:
        return Path(without[0]["path"]) / "cdase"

    if info["workspace_is_git_repo"] and len(info["repos"]) == 1:
        only = info["repos"][0]
        if not only["is_framework"]:
            return Path(only["path"]) / "cdase"

    return None


def methodology_roots(scripts_dir: Path) -> set[Path]:
    """Paths that belong to the CDASE skill/framework checkout — never consumer runtime."""
    skill_root = scripts_dir.parent.resolve()
    methodology_root = skill_root.parent.resolve()
    roots = {skill_root, methodology_root}
    if is_framework_repo(methodology_root):
        roots.add(consumer_cdase_dir(methodology_root).resolve())
    return roots
