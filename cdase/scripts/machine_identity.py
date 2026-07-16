"""Machine-as-user identity: this PC is this roster/hub user id."""

from __future__ import annotations

import hashlib
import os
import platform
import uuid as uuid_lib
from pathlib import Path


def raw_machine_id() -> str:
    """Host-local machine string (not secret; not the hub user uuid)."""
    return os.environ.get("CDASE_MACHINE_ID") or f"{platform.node()}-{uuid_lib.getnode():x}"


def machine_user_id(raw: str | None = None) -> str:
    """Stable 8-hex user id derived from this machine (roster + hub uuid)."""
    material = (raw or raw_machine_id()).encode("utf-8")
    return hashlib.sha256(material).hexdigest()[:8]


def find_roster_member(roster: list[dict], user_id: str) -> dict | None:
    from context_loader import normalize_user_id

    needle = normalize_user_id(user_id)
    return next((m for m in roster if m.get("uuid") == needle), None)


def append_roster_member(
    cdase_root: Path,
    *,
    name: str,
    user_id: str,
    role: str | None = None,
) -> Path:
    """Append Name|UUID|Role to users.context.md (UUID column = machine_user_id)."""
    from context_loader import is_valid_user_id, normalize_user_id

    path = cdase_root / "context" / "users.context.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    uid = normalize_user_id(user_id)
    if not is_valid_user_id(uid):
        raise ValueError(f"invalid user id: {user_id}")
    role_cell = role or "developer"
    row = f"| {name} | {uid} | {role_cell} |"

    if not path.exists():
        path.write_text(
            "# Team Roster (SSOT)\n\n"
            "> UUID column = machine-derived user id (8 hex). Different machine = different user.\n\n"
            "| Name | UUID | Role |\n"
            "|------|------|------|\n"
            f"{row}\n",
            encoding="utf-8",
        )
        return path

    text = path.read_text(encoding="utf-8")
    if f"| {uid} |" in text or f"|{uid}|" in text:
        return path

    lines = text.splitlines()
    insert_at = None
    in_table = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("|") and ("UUID" in stripped or "Name" in stripped) and "---" not in stripped:
            in_table = True
            continue
        if in_table and stripped.startswith("|--"):
            continue
        if in_table and stripped.startswith("|"):
            insert_at = i + 1
            continue
        if in_table and not stripped.startswith("|"):
            insert_at = i
            break
    if insert_at is None:
        if not any("UUID" in ln and "Name" in ln for ln in lines):
            lines.extend(["", "| Name | UUID | Role |", "|------|------|------|", row])
        else:
            lines.append(row)
    else:
        lines.insert(insert_at, row)
    ending = "\n" if text.endswith("\n") else ""
    path.write_text("\n".join(lines) + ending, encoding="utf-8")
    return path


def ensure_machine_on_roster(cdase_root: Path) -> dict:
    """Ensure this machine has a roster row; add from global Name if needed.

    Returns action: found | added | need_name
    """
    from context_loader import global_user_name, load_roster, load_user_context

    raw = raw_machine_id()
    uid = machine_user_id(raw)
    roster = load_roster(cdase_root)
    match = find_roster_member(roster, uid)
    if match:
        return {
            "ok": True,
            "action": "found",
            "user_id": uid,
            "machine_id": raw,
            "name": match.get("name"),
            "role": match.get("role"),
            "roster_path": str(cdase_root / "context" / "users.context.md"),
            "agent_rule": "Machine id already on roster — use that Name; login hub with user_id.",
        }

    global_name = global_user_name()
    user = load_user_context(cdase_root)
    name = global_name
    if not name:
        return {
            "ok": False,
            "action": "need_name",
            "user_id": uid,
            "machine_id": raw,
            "agent_rule": (
                "Machine id not on roster and global Name missing. "
                "Run input-spec user-profile → apply-global-user, then boot again "
                "(boot will append this machine to users.context.md)."
            ),
            "next_step": "python3 scripts/cdase_client.py input-spec user-profile",
        }

    role = user.get("role") or "developer"
    path = append_roster_member(cdase_root, name=name, user_id=uid, role=role)
    return {
        "ok": True,
        "action": "added",
        "user_id": uid,
        "machine_id": raw,
        "name": name,
        "role": role,
        "roster_path": str(path),
        "agent_rule": (
            f"Added '{name}' ({uid}) to users.context.md for this machine. "
            "Commit the roster when ready. Repo Name can later differ from global Name."
        ),
    }
