"""Team list — repo roster SSOT + hub superset (users on hub not yet in repo)."""

from __future__ import annotations

import subprocess
from pathlib import Path

from trust_policy import merge_team


def roster_is_committed(cdase_root: Path, git_root: Path | None) -> bool | None:
    if git_root is None:
        return None
    path = cdase_root / "context" / "users.context.md"
    if not path.exists():
        return None
    try:
        rel = path.relative_to(git_root.resolve()).as_posix()
        result = subprocess.run(
            ["git", "status", "--porcelain", rel],
            cwd=git_root,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return None
        return result.stdout.strip() == ""
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return None


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
            "note": "Git contributor only — not in users.context.md",
        })
    return out


def team_summary(
    members: list[dict],
    *,
    hub_offline: bool = False,
    git_only: list[dict] | None = None,
) -> str:
    roster = [m for m in members if m.get("in_roster")]
    online = [m for m in roster if m.get("online")]
    new_to_you = [m for m in members if m.get("status") == "new_to_you"]
    parts = [f"{len(roster)} in roster ({len(online)} online)"]
    if new_to_you:
        parts.append(f"{len(new_to_you)} on hub, new to you (not in roster)")
    if git_only:
        parts.append(f"{len(git_only)} git-only")
    if hub_offline:
        parts.append("hub offline")
    return "; ".join(parts)


def build_agent_team_brief(user: dict, members: list[dict], *, hub_offline: bool = False) -> dict:
    me = (user.get("name") or "").strip().lower()
    roster_rows = [m for m in members if m.get("in_roster")]
    new_rows = [m for m in members if m.get("status") == "new_to_you"]

    lines: list[str] = []
    if me:
        lines.append(f"You ({user.get('name')}):")
    lines.append("Trusted team (repo users.context.md):")
    for m in roster_rows:
        mark = " (you)" if (m.get("name") or "").lower() == me else ""
        st = m.get("status", "offline")
        lines.append(f"  • {m['name']} — {st}{mark}")

    if new_rows and not hub_offline:
        lines.append("New on hub (NOT in your roster — ask user to confirm before trusting):")
        for m in new_rows:
            lines.append(f"  • {m.get('name')} — new_to_you")

    others = [m for m in roster_rows if (m.get("name") or "").lower() != me]
    return {
        "agent_brief": "\n".join(lines),
        "others_count": len(others) + len(new_rows),
        "new_to_you": [{"name": m.get("name"), "uuid": m.get("uuid")} for m in new_rows],
        "must_use_this_brief": True,
        "must_not_auto_trust": [m.get("name") for m in new_rows if m.get("name")],
        "agent_rule": (
            "Repo users.context.md = trust SSOT. Hub may list extra users (new_to_you). "
            "Never auto-reply to messages from new_to_you until user_b confirms and adds them to roster."
        ),
    }
