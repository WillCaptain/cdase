"""Team list — committed project members plus Hub presence."""

from __future__ import annotations

import subprocess
from pathlib import Path

from context_loader import member_commit_state
from trust_policy import merge_team


def member_commit_states(cdase_root: Path, git_root: Path | None) -> dict[str, str]:
    if git_root is None:
        return {}
    members_dir = cdase_root / "context" / "members"
    if not members_dir.is_dir():
        return {}
    states: dict[str, str] = {}
    for path in sorted(members_dir.glob("*.context.md")):
        try:
            rel = path.resolve().relative_to(git_root.resolve()).as_posix()
            states[rel] = member_commit_state(path, git_root)
        except (OSError, ValueError):
            states[str(path)] = "unknown"
    return states


def members_are_committed(cdase_root: Path, git_root: Path | None) -> bool | None:
    states = member_commit_states(cdase_root, git_root)
    if not states:
        return None
    return all(state == "committed" for state in states.values())


def git_contributors(git_root: Path | None, known_names: set[str]) -> list[dict]:
    if git_root is None:
        return []
    try:
        result = subprocess.run(
            ["git", "shortlog", "-sn", "--all"],
            cwd=git_root,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return []
    except (OSError, subprocess.TimeoutExpired):
        return []

    known = {n.strip().lower() for n in known_names if n}
    out: list[dict] = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split(None, 1)
        if len(parts) != 2:
            continue
        try:
            commits = int(parts[0])
        except ValueError:
            continue
        name = parts[1].strip()
        if name.lower() in known:
            continue
        out.append({
            "name": name,
            "commits": commits,
            "status": "git_only",
            "source": "git",
            "in_roster": False,
            "note": "Git contributor only — not an active project member",
        })
    return out


def team_summary(
    members: list[dict],
    *,
    hub_offline: bool = False,
    git_only: list[dict] | None = None,
) -> str:
    project_members = [m for m in members if m.get("in_roster")]
    trusted = [m for m in project_members if m.get("trusted")]
    online = [m for m in trusted if m.get("online")]
    inactive = [m for m in project_members if m.get("status") == "inactive"]
    pending = [m for m in project_members if m.get("status") == "pending"]
    new_to_you = [m for m in members if m.get("status") == "new_to_you"]
    parts = [f"{len(trusted)} active members ({len(online)} online)"]
    if inactive:
        parts.append(f"{len(inactive)} inactive")
    if pending:
        parts.append(f"{len(pending)} pending commit")
    if new_to_you:
        parts.append(f"{len(new_to_you)} on Hub, new to you")
    if git_only:
        parts.append(f"{len(git_only)} git-only")
    if hub_offline:
        parts.append("hub offline")
    return "; ".join(parts)


def build_agent_team_brief(user: dict, members: list[dict], *, hub_offline: bool = False) -> dict:
    me = (user.get("name") or "").strip().lower()
    trusted_rows = [m for m in members if m.get("trusted")]
    inactive_rows = [m for m in members if m.get("status") == "inactive"]
    pending_rows = [m for m in members if m.get("status") == "pending"]
    new_rows = [m for m in members if m.get("status") == "new_to_you"]

    lines: list[str] = []
    if me:
        lines.append(f"You ({user.get('name')}):")
    lines.append("Trusted team (committed project member records):")
    for m in trusted_rows:
        mark = " (you)" if (m.get("name") or "").lower() == me else ""
        st = m.get("status", "offline")
        lines.append(f"  • {m['name']} — {st}{mark}")

    if new_rows and not hub_offline:
        lines.append("New on Hub (no active member record — confirm before trusting):")
        for m in new_rows:
            lines.append(f"  • {m.get('name')} — new_to_you")

    if inactive_rows:
        lines.append("Inactive project members:")
        for m in inactive_rows:
            lines.append(f"  • {m.get('name')} — inactive")
    if pending_rows:
        lines.append("Pending member records (commit required):")
        for m in pending_rows:
            lines.append(f"  • {m.get('name')} — {m.get('commit_state') or 'pending'}")

    others = [m for m in trusted_rows if (m.get("name") or "").lower() != me]
    return {
        "agent_brief": "\n".join(lines),
        "others_count": len(others) + len(new_rows),
        "new_to_you": [{"name": m.get("name"), "uuid": m.get("uuid")} for m in new_rows],
        "must_use_this_brief": True,
        "must_not_auto_trust": [m.get("name") for m in new_rows if m.get("name")],
        "agent_rule": (
            "Active committed member records are the trust SSOT. Hub may list extra users "
            "(new_to_you). Never auto-reply until the user confirms and adds a member record."
        ),
    }
