"""Load CDASE identity, project members, and settings.

Identity model: **machine = user**. The Hub/member id is derived from this
machine (`machine_user_id`). The global profile supplies defaults, a committed
member record publishes the project identity, and an optional repo-local
`user.context.md` overrides the current user's alias/role.
"""

from __future__ import annotations

import os
import re
import subprocess
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


def resolve_identity_from_members(user: dict, members: list[dict]) -> dict:
    """Resolve the committed project identity by machine-derived user id."""
    from machine_identity import machine_user_id, raw_machine_id

    uid = user.get("uuid") or machine_user_id()
    user["uuid"] = normalize_user_id(uid) if is_valid_user_id(uid) else uid
    user["machine_id"] = raw_machine_id()
    user["uuid_from_machine"] = True

    match = next((m for m in members if m.get("uuid") == user["uuid"]), None)
    if match is None:
        return user
    # The committed project alias is the shared default for this repository.
    user["name"] = match.get("name") or user.get("name")
    if match.get("role"):
        user["role"] = match.get("role")
    user["status"] = match.get("status")
    user["uuid_from_members"] = True
    return user


def load_user_context(cdase_root: Path) -> dict:
    """Load identity with global → committed member → local override precedence."""
    from machine_identity import machine_user_id, raw_machine_id

    machine_raw = os.environ.get("CDASE_MACHINE_ID") or raw_machine_id()
    user: dict = {
        "name": None,
        "uuid": machine_user_id(machine_raw),
        "machine_id": machine_raw,
        "role": None,
        "team": None,
        "organization": None,
        "uuid_from_machine": True,
    }
    identity_sources: list[str] = ["machine"]
    if os.environ.get("CDASE_MACHINE_ID"):
        identity_sources.append("CDASE_MACHINE_ID")

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

    members = load_members(cdase_root)
    user = resolve_identity_from_members(user, members)
    if user.get("uuid_from_members"):
        identity_sources.append("member")

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

    user["identity_sources"] = identity_sources or ["none"]
    user["identity_source"] = "+".join(identity_sources) if identity_sources else "none"
    user["alias"] = user.get("name")
    user["global_dir"] = str(global_cdase_dir())
    return user


def load_members(cdase_root: Path) -> list[dict]:
    """Load committed project member records, one file per immutable user id."""
    members_dir = cdase_root / "context" / "members"
    if not members_dir.is_dir():
        return []

    members: list[dict] = []
    for path in sorted(members_dir.glob("*.context.md")):
        file_id = path.name.removesuffix(".context.md")
        if not USER_ID_RE.fullmatch(file_id):
            raise ValueError(f"invalid member filename (expected 8-hex id): {path}")
        text = path.read_text(encoding="utf-8")
        declared_id = _read_field(text, "User ID")
        if not declared_id or not USER_ID_RE.fullmatch(declared_id):
            raise ValueError(f"member record has missing/invalid User ID: {path}")
        uid = normalize_user_id(declared_id)
        if uid != normalize_user_id(file_id):
            raise ValueError(f"member filename/id mismatch: {path} declares {declared_id}")
        alias = _read_field(text, "Alias")
        if not alias:
            raise ValueError(f"member record has no Alias: {path}")
        status = (_read_field(text, "Status") or "active").lower()
        if status not in {"active", "inactive"}:
            raise ValueError(f"member record has invalid Status: {path}")
        commit_state = member_commit_state(path)
        members.append({
            "alias": alias,
            "name": alias,
            "uuid": uid,
            "role": _read_field(text, "Role"),
            "status": status,
            "path": str(path),
            "commit_state": commit_state,
            "committed": commit_state in {"committed", "not_applicable"},
        })
    return members


def member_commit_state(path: Path, git_root: Path | None = None) -> str:
    """Return committed|staged|modified|staged_modified|untracked|ignored|unknown."""
    if (
        os.environ.get("CDASE_TESTING") == "1"
        and os.environ.get("CDASE_TEST_MEMBER_STATE")
    ):
        return os.environ["CDASE_TEST_MEMBER_STATE"]

    path = path.resolve()
    if git_root is None:
        probe = _run_git(["git", "-C", str(path.parent), "rev-parse", "--show-toplevel"])
        if probe is None or probe.returncode != 0:
            return "not_applicable"
        git_root = Path(probe.stdout.strip()).resolve()
    else:
        git_root = git_root.resolve()

    try:
        rel = path.relative_to(git_root).as_posix()
    except ValueError:
        return "unknown"

    status = _run_git(
        [
            "git", "status", "--porcelain=v1", "--ignored",
            "--untracked-files=all", "--", rel,
        ],
        cwd=git_root,
    )
    if status is None or status.returncode != 0:
        return "unknown"
    line = next((item for item in status.stdout.splitlines() if item), "")
    if line:
        code = line[:2]
        if code == "!!":
            return "ignored"
        if code == "??":
            return "untracked"
        staged = code[0] not in {" ", "?"}
        modified = code[1] not in {" ", "?"}
        if staged and modified:
            return "staged_modified"
        if staged:
            return "staged"
        if modified:
            return "modified"
        return "unknown"

    tracked = _run_git(
        ["git", "ls-files", "--error-unmatch", "--", rel],
        cwd=git_root,
    )
    if tracked is None or tracked.returncode != 0:
        return "untracked"
    in_head = _run_git(
        ["git", "cat-file", "-e", f"HEAD:{rel}"],
        cwd=git_root,
    )
    return "committed" if in_head is not None and in_head.returncode == 0 else "staged"


def _run_git(args: list[str], *, cwd: Path | None = None):
    try:
        return subprocess.run(
            args,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None


def trusted_uuids(members: list[dict]) -> list[str]:
    return [
        m["uuid"] for m in members
        if m.get("status", "active") == "active" and m.get("committed", True)
    ]


def trust_csv(members: list[dict]) -> str:
    return ",".join(trusted_uuids(members))


def validate_identity(user: dict, members: list[dict]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    gdir = global_cdase_dir()

    if not members:
        errors.append("context/members/ missing or empty — project members are the trust SSOT")

    uid = user.get("uuid")
    if not uid or not is_valid_user_id(uid):
        errors.append("machine user id missing/invalid — check CDASE_MACHINE_ID / machine_identity")
    else:
        match = next((m for m in members if m.get("uuid") == normalize_user_id(uid)), None)
        if match is None:
            errors.append(
                f"machine user id '{uid}' has no project member record — "
                "run boot to create one, or set Alias globally first"
            )
        elif match.get("status") != "active":
            errors.append(f"project member '{uid}' is inactive")
        elif not match.get("committed", True):
            errors.append(
                f"project member '{uid}' is pending ({match.get('commit_state')}); "
                "commit the member record before Hub actions"
            )
        elif not match.get("name") and not user.get("name"):
            errors.append("member record has no Alias for this machine")

    if not user.get("name"):
        errors.append(
            f"display Alias missing — set Name in {gdir}/user.context.md or this machine's member record"
        )

    return len(errors) == 0, errors


def resolve_recipient(to: str, members: list[dict]) -> dict | None:
    active = [
        m for m in members
        if m.get("status", "active") == "active" and m.get("committed", True)
    ]
    if is_valid_user_id(to):
        needle = normalize_user_id(to)
        return next((m for m in active if m["uuid"] == needle), None)
    matches = [m for m in active if m["name"].lower() == to.lower()]
    return matches[0] if len(matches) == 1 else None
