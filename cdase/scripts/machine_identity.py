"""Machine-as-user identity and conflict-free project member records."""

from __future__ import annotations

import hashlib
import os
import platform
import uuid as uuid_lib
from pathlib import Path


def _member_field(label: str, value: str | None, *, default: str | None = None) -> str:
    normalized = str(value if value is not None else default or "").strip()
    if not normalized:
        raise ValueError(f"member {label} is required")
    if normalized.startswith("[") or any(ord(char) < 32 or ord(char) == 127 for char in normalized):
        raise ValueError(f"member {label} contains invalid control characters")
    return normalized


def raw_machine_id() -> str:
    """Host-local machine string (not secret; not the hub user uuid)."""
    return os.environ.get("CDASE_MACHINE_ID") or f"{platform.node()}-{uuid_lib.getnode():x}"


def machine_user_id(raw: str | None = None) -> str:
    """Stable 8-hex user id derived from this machine (roster + hub uuid)."""
    material = (raw or raw_machine_id()).encode("utf-8")
    return hashlib.sha256(material).hexdigest()[:8]


def find_member(members: list[dict], user_id: str) -> dict | None:
    from context_loader import normalize_user_id

    needle = normalize_user_id(user_id)
    return next((m for m in members if m.get("uuid") == needle), None)


def write_member_record(
    cdase_root: Path,
    *,
    name: str,
    user_id: str,
    role: str | None = None,
    status: str = "active",
) -> Path:
    """Create or update this user's independent committed member record."""
    from context_loader import USER_ID_RE, normalize_user_id

    uid = normalize_user_id(user_id)
    if not USER_ID_RE.fullmatch(uid):
        raise ValueError(f"member user id must be 8 lowercase hex: {user_id}")
    if status not in {"active", "inactive"}:
        raise ValueError(f"invalid member status: {status}")
    alias = _member_field("Alias", name)
    member_role = _member_field("Role", role, default="developer")
    members_dir = cdase_root / "context" / "members"
    members_dir.mkdir(parents=True, exist_ok=True)
    path = members_dir / f"{uid}.context.md"
    path.write_text(
        "\n".join([
            "# Project Member",
            "",
            f"- User ID: {uid}",
            f"- Alias: {alias}",
            f"- Role: {member_role}",
            f"- Status: {status}",
            "",
        ]),
        encoding="utf-8",
    )
    return path


def ensure_machine_member(cdase_root: Path) -> dict:
    """Ensure this machine has a committed project member record.

    Returns action: found | added | updated | need_name.
    """
    from context_loader import load_members, load_user_context

    raw = raw_machine_id()
    uid = machine_user_id(raw)
    members = load_members(cdase_root)
    match = find_member(members, uid)
    user = load_user_context(cdase_root)
    name = user.get("name")
    role = user.get("role") or "developer"
    if match:
        changed = match.get("name") != name or (match.get("role") or "developer") != role
        path = Path(match["path"])
        if changed and name:
            path = write_member_record(
                cdase_root, name=name, user_id=uid, role=role, status=match.get("status", "active")
            )
        return {
            "ok": True,
            "action": "updated" if changed and name else "found",
            "user_id": uid,
            "machine_id": raw,
            "name": name or match.get("name"),
            "role": role,
            "member_path": str(path),
            "agent_rule": "Machine member record resolved; use its id for assignments and Hub login.",
        }

    if not name:
        return {
            "ok": False,
            "action": "need_name",
            "user_id": uid,
            "machine_id": raw,
            "agent_rule": (
                "Machine has no member record and no global/repo Alias. "
                "Run input-spec user-profile → apply-global-user, then boot again "
                "(boot will create this machine's member file)."
            ),
            "next_step": "cdase input-spec user-profile",
        }

    path = write_member_record(cdase_root, name=name, user_id=uid, role=role)
    return {
        "ok": True,
        "action": "added",
        "user_id": uid,
        "machine_id": raw,
        "name": name,
        "role": role,
        "member_path": str(path),
        "agent_rule": (
            f"Created member '{name}' ({uid}). Commit {path.name}; "
            "a repo-local profile may publish a project-specific Alias."
        ),
    }
