"""Load CDASE identity, roster, and settings — global user config + repo SSOT.

Identity model: **machine = user**. Hub/roster uuid is derived from this machine
(`machine_user_id`). Display Name comes from the roster row for this machine, or
from ~/.cdase/user.context.md when joining a repo for the first time.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

DEFAULT_HUB_URL = "https://12th.ai/cdase"

USER_ID_RE = re.compile(r"^[0-9a-fA-F]{8}$")
LEGACY_UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


# Agent-neutral global config (not tied to Cursor or any IDE).
# Windows: %USERPROFILE%\.cdase  (Path.home() / ".cdase")
DEFAULT_GLOBAL_CDASE_DIR = Path.home() / ".cdase"
LEGACY_GLOBAL_CDASE_DIR = Path.home() / ".cursor" / "cdase"
_GLOBAL_MIGRATE_NAMES = ("user.context.md", "setting.context.md")


def migrate_legacy_global_dir(
    preferred: Path | None = None,
    legacy: Path | None = None,
) -> list[str]:
    """Copy missing files from ~/.cursor/cdase → ~/.cdase (one-way, non-destructive).

    Returns list of filenames copied. Never overwrites files already in preferred.
    """
    preferred = (preferred or DEFAULT_GLOBAL_CDASE_DIR).expanduser()
    legacy = (legacy or LEGACY_GLOBAL_CDASE_DIR).expanduser()
    if not legacy.is_dir():
        return []
    copied: list[str] = []
    for name in _GLOBAL_MIGRATE_NAMES:
        src = legacy / name
        dst = preferred / name
        if src.is_file() and not dst.exists():
            preferred.mkdir(parents=True, exist_ok=True)
            dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
            copied.append(name)
    return copied


def global_cdase_dir(*, for_write: bool = False) -> Path:
    """Resolve global CDASE config dir (agent-neutral).

    Priority:
      1. CDASE_GLOBAL env
      2. ~/.cdase (canonical — always used for writes / new installs)
      3. ~/.cursor/cdase (legacy read fallback if ~/.cdase is absent)

    On access, missing files are migrated from legacy → ~/.cdase (never overwrite).
    Windows canonical: %USERPROFILE%\\.cdase
    """
    if env := os.environ.get("CDASE_GLOBAL"):
        return Path(env).expanduser()
    preferred = DEFAULT_GLOBAL_CDASE_DIR.expanduser()
    legacy = LEGACY_GLOBAL_CDASE_DIR.expanduser()
    migrate_legacy_global_dir(preferred, legacy)
    if for_write:
        return preferred
    if preferred.exists() or not legacy.exists():
        return preferred
    return legacy


def is_valid_user_id(value: str) -> bool:
    return bool(USER_ID_RE.match(value) or LEGACY_UUID_RE.match(value))


def normalize_user_id(value: str) -> str:
    if USER_ID_RE.match(value):
        return value.lower()
    return value


def _read_field(text: str, field: str) -> str | None:
    m = re.search(rf"^\s*-\s*{field}:\s*(.+)$", text, re.MULTILINE)
    if not m:
        return None
    value = m.group(1).strip()
    if not value or value.startswith("["):
        return None
    return value


def _read_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in ("true", "yes", "1", "on")


def _parse_setting_sections(text: str) -> dict[str, dict[str, str]]:
    sections: dict[str, dict[str, str]] = {}
    current: str | None = None
    for line in text.splitlines():
        if line.startswith("## "):
            current = line[3:].strip().lower()
            sections.setdefault(current, {})
            continue
        if current is None:
            continue
        m = re.match(r"^\s*-\s*(\w+):\s*(.+)$", line)
        if m:
            sections[current][m.group(1).lower()] = m.group(2).strip()
    return sections


def _apply_settings_sections(settings: dict, sections: dict[str, dict[str, str]]) -> None:
    hub = sections.get("hub", {})
    client = sections.get("client", {})
    messaging = sections.get("messaging", {})
    if hub.get("address"):
        settings["hub_address"] = hub["address"].rstrip("/")
    if "offlineok" in hub:
        settings["hub_offline_ok"] = _read_bool(hub.get("offlineok"), settings["hub_offline_ok"])
    if client.get("path"):
        settings["client_path"] = client["path"]
    if messaging.get("fromactor"):
        settings["messaging_from_actor"] = messaging["fromactor"]
    if messaging.get("agentautonomy"):
        settings["agent_autonomy"] = messaging["agentautonomy"].lower()
    if "autoreplytoagentquestions" in messaging:
        settings["auto_reply_to_agent_questions"] = _read_bool(
            messaging.get("autoreplytoagentquestions"), True
        )
    project = sections.get("project", {})
    if project.get("repoid"):
        settings["repo_id"] = project["repoid"].strip()


def load_settings(cdase_root: Path) -> dict:
    """Merge settings: defaults → global → repo → env."""
    settings = {
        "hub_address": DEFAULT_HUB_URL,
        "hub_offline_ok": True,
        "client_path": "auto",
        "messaging_from_actor": "agent",
        "agent_autonomy": "delegated",
        "auto_reply_to_agent_questions": True,
        "sources": [],
        "global_dir": str(global_cdase_dir()),
    }

    global_path = global_cdase_dir() / "setting.context.md"
    if global_path.exists():
        _apply_settings_sections(settings, _parse_setting_sections(global_path.read_text()))
        settings["sources"].append("global")

    repo_path = cdase_root / "context" / "setting.context.md"
    if repo_path.exists():
        _apply_settings_sections(settings, _parse_setting_sections(repo_path.read_text()))
        settings["sources"].append("repo")

    if not settings["sources"]:
        settings["sources"].append("defaults")

    if env := os.environ.get("CDASE_HUB_URL"):
        settings["hub_address"] = env.rstrip("/")
        settings["sources"].append("CDASE_HUB_URL")
    if env := os.environ.get("CDASE_CLIENT"):
        settings["client_path"] = env
        settings["sources"].append("CDASE_CLIENT")
    if env := os.environ.get("CDASE_HUB_OFFLINE_OK"):
        settings["hub_offline_ok"] = _read_bool(env, settings["hub_offline_ok"])
        settings["sources"].append("CDASE_HUB_OFFLINE_OK")

    settings["source"] = "+".join(settings["sources"])
    return settings


def resolve_hub_url(settings: dict) -> str:
    return settings["hub_address"].rstrip("/")


def hub_url_state(settings: dict) -> dict:
    """Hub tools allowed only when Address is explicitly configured (not built-in default alone)."""
    sources = settings.get("sources", [])
    explicit = (
        "global" in sources
        or "repo" in sources
        or "CDASE_HUB_URL" in sources
    )
    url = (settings.get("hub_address") or "").strip().rstrip("/")
    empty = not url or url.startswith("[")
    configured = explicit and not empty
    return {
        "configured": configured,
        "explicit": explicit,
        "address": url if configured else None,
        "hub_tools_allowed": configured,
        "source": settings.get("source"),
    }


def resolve_client_script(settings: dict, scripts_dir: Path) -> Path:
    path = settings.get("client_path", "auto")
    if not path or path.lower() == "auto":
        return scripts_dir / "cdase_client.py"
    return Path(path).expanduser().resolve()


def _read_user_file(path: Path) -> dict:
    text = path.read_text()
    uuid_raw = _read_field(text, "UUID")
    return {
        "name": _read_field(text, "Name"),
        "uuid": normalize_user_id(uuid_raw) if uuid_raw and is_valid_user_id(uuid_raw) else uuid_raw,
        "role": _read_field(text, "Role"),
        "team": _read_field(text, "Team"),
        "organization": _read_field(text, "Organization"),
    }


def _overlay_user(base: dict, overlay: dict) -> dict:
    merged = dict(base)
    for key, value in overlay.items():
        if value is not None:
            merged[key] = value
    return merged


def global_user_name() -> str | None:
    path = global_cdase_dir() / "user.context.md"
    if not path.exists():
        return None
    return _read_field(path.read_text(encoding="utf-8"), "Name")


def resolve_identity_from_roster(user: dict, roster: list[dict]) -> dict:
    """Resolve by machine-derived user id in roster (not by Name)."""
    from machine_identity import machine_user_id, raw_machine_id

    uid = user.get("uuid") or machine_user_id()
    user["uuid"] = normalize_user_id(uid) if is_valid_user_id(uid) else uid
    user["machine_id"] = raw_machine_id()
    user["uuid_from_machine"] = True

    match = next((m for m in roster if m.get("uuid") == user["uuid"]), None)
    if match is None:
        return user
    # Repo roster Name wins for this project (may differ from global Name)
    user["name"] = match.get("name") or user.get("name")
    if match.get("role"):
        user["role"] = match.get("role")
    user["uuid_from_roster"] = True
    return user


def load_user_context(cdase_root: Path) -> dict:
    """Load identity: machine user id + global Name fallback + roster row for this machine."""
    from machine_identity import machine_user_id, raw_machine_id

    user: dict = {
        "name": None,
        "uuid": machine_user_id(),
        "machine_id": raw_machine_id(),
        "role": None,
        "team": None,
        "organization": None,
        "uuid_from_machine": True,
    }
    identity_sources: list[str] = ["machine"]

    global_path = global_cdase_dir() / "user.context.md"
    if global_path.exists():
        overlay = _read_user_file(global_path)
        # Global Name is display default only — never take a random UUID from global file
        if overlay.get("name"):
            user["name"] = overlay["name"]
        if overlay.get("role"):
            user["role"] = overlay["role"]
        if overlay.get("team"):
            user["team"] = overlay["team"]
        if overlay.get("organization"):
            user["organization"] = overlay["organization"]
        identity_sources.append("global")

    repo_path = cdase_root / "context" / "user.context.md"
    if repo_path.exists():
        overlay = _read_user_file(repo_path)
        if overlay.get("name"):
            user["name"] = overlay["name"]
        if overlay.get("role"):
            user["role"] = overlay["role"]
        identity_sources.append("repo_override")

    if env_name := os.environ.get("CDASE_USER"):
        user["name"] = env_name
        identity_sources.append("CDASE_USER")
    if env_mid := os.environ.get("CDASE_MACHINE_ID"):
        user["machine_id"] = env_mid
        user["uuid"] = machine_user_id(env_mid)
        identity_sources.append("CDASE_MACHINE_ID")

    roster = load_roster(cdase_root)
    user = resolve_identity_from_roster(user, roster)

    user["identity_sources"] = identity_sources or ["none"]
    user["identity_source"] = "+".join(identity_sources) if identity_sources else "none"
    user["global_dir"] = str(global_cdase_dir())
    return user


def load_roster(cdase_root: Path) -> list[dict]:
    path = cdase_root / "context" / "users.context.md"
    if not path.exists():
        return []

    roster: list[dict] = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line.startswith("|") or line.startswith("|--"):
            continue
        if "UUID" in line and "Name" in line:
            continue
        parts = [p.strip() for p in line.strip("|").split("|")]
        if len(parts) < 2:
            continue
        name, user_uuid = parts[0], parts[1]
        if not name or name.startswith("-") or name.lower() == "name":
            continue
        if not is_valid_user_id(user_uuid):
            continue
        role = parts[2] if len(parts) > 2 else None
        roster.append({"name": name, "uuid": normalize_user_id(user_uuid), "role": role})
    return roster


def trusted_uuids(roster: list[dict]) -> list[str]:
    return [m["uuid"] for m in roster]


def trust_csv(roster: list[dict]) -> str:
    return ",".join(trusted_uuids(roster))


def validate_identity(user: dict, roster: list[dict]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    gdir = global_cdase_dir()

    if not roster:
        errors.append("context/users.context.md missing or empty — repo roster is SSOT for trust")

    uid = user.get("uuid")
    if not uid or not is_valid_user_id(uid):
        errors.append("machine user id missing/invalid — check CDASE_MACHINE_ID / machine_identity")
    else:
        match = next((m for m in roster if m.get("uuid") == normalize_user_id(uid)), None)
        if match is None:
            errors.append(
                f"machine user id '{uid}' not in repo roster (users.context.md) — "
                "run boot to add this machine, or set Name globally first"
            )
        elif not match.get("name") and not user.get("name"):
            errors.append("roster row has no Name for this machine")

    if not user.get("name"):
        errors.append(
            f"display Name missing — set Name in {gdir}/user.context.md or roster row for this machine"
        )

    return len(errors) == 0, errors


def resolve_recipient(to: str, roster: list[dict]) -> dict | None:
    if is_valid_user_id(to):
        needle = normalize_user_id(to)
        return next((m for m in roster if m["uuid"] == needle), None)
    return next((m for m in roster if m["name"].lower() == to.lower()), None)
