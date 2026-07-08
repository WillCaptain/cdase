"""Load CDASE identity, roster, and settings — global user config + repo SSOT."""

from __future__ import annotations

import os
import re
from pathlib import Path

DEFAULT_HUB_URL = "http://127.0.0.1:7423"

USER_ID_RE = re.compile(r"^[0-9a-fA-F]{8}$")
LEGACY_UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


def global_cdase_dir() -> Path:
    return Path(os.environ.get("CDASE_GLOBAL", Path.home() / ".cursor" / "cdase")).expanduser()


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


def resolve_identity_from_roster(user: dict, roster: list[dict]) -> dict:
    """UUID SSOT is repo roster — resolve by Name (option B)."""
    if not user.get("name") or not roster:
        return user
    match = next((m for m in roster if m["name"].lower() == user["name"].lower()), None)
    if match is None:
        return user
    if not user.get("role"):
        user["role"] = match.get("role")
    explicit = user.get("uuid")
    if explicit and is_valid_user_id(explicit):
        user["uuid_explicit"] = True
        return user
    user["uuid"] = match["uuid"]
    user["uuid_from_roster"] = True
    return user


def load_user_context(cdase_root: Path) -> dict:
    """Load identity: global profile → optional repo override → env → roster UUID."""
    user: dict = {"name": None, "uuid": None, "role": None, "team": None, "organization": None}
    identity_sources: list[str] = []

    global_path = global_cdase_dir() / "user.context.md"
    if global_path.exists():
        user = _overlay_user(user, _read_user_file(global_path))
        identity_sources.append("global")

    repo_path = cdase_root / "context" / "user.context.md"
    if repo_path.exists():
        user = _overlay_user(user, _read_user_file(repo_path))
        identity_sources.append("repo_override")

    if env_name := os.environ.get("CDASE_USER"):
        user["name"] = env_name
        identity_sources.append("CDASE_USER")
    if env_uuid := os.environ.get("CDASE_UUID"):
        if is_valid_user_id(env_uuid):
            user["uuid"] = normalize_user_id(env_uuid)
            user["uuid_explicit"] = True
            identity_sources.append("CDASE_UUID")

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
        if not line.startswith("|") or line.startswith("|--") or "UUID" in line:
            continue
        parts = [p.strip() for p in line.strip("|").split("|")]
        if len(parts) < 2:
            continue
        name, user_uuid = parts[0], parts[1]
        if not name or name.startswith("-"):
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

    if not user.get("name"):
        errors.append(
            f"identity name missing — set Name in {gdir}/user.context.md (once, global) "
            "or CDASE_USER"
        )

    if user.get("name") and roster:
        match = next((m for m in roster if m["name"].lower() == user["name"].lower()), None)
        if match is None:
            errors.append(
                f"name '{user['name']}' not in repo roster (users.context.md) — add them or use a repo override"
            )
        else:
            if not user.get("uuid"):
                errors.append(
                    f"uuid not resolved for '{user['name']}' — roster entry required in users.context.md"
                )
            elif not is_valid_user_id(user["uuid"]):
                errors.append(f"identity uuid invalid format: {user['uuid']}")
            elif normalize_user_id(user["uuid"]) != match["uuid"]:
                errors.append(
                    f"uuid mismatch for '{user['name']}': resolved={user['uuid']} roster={match['uuid']}"
                )

    return len(errors) == 0, errors


def resolve_recipient(to: str, roster: list[dict]) -> dict | None:
    if is_valid_user_id(to):
        needle = normalize_user_id(to)
        return next((m for m in roster if m["uuid"] == needle), None)
    return next((m for m in roster if m["name"].lower() == to.lower()), None)
