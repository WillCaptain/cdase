"""Host-agnostic input specs for CDASE.

CDASE never ships its own UI. It emits a *declarative* input request. Every code
agent maps that spec onto its host's input UI (order: host UI → plain text).
Product-specific widgets are never prescribed. The agent owns the post-submit
action (e.g. `apply-global-user`).
"""

from __future__ import annotations

import copy
from pathlib import Path

from context_loader import global_cdase_dir

_RENDER_HINT = (
    "Generic order (all hosts): (1) map this spec to your host's richest matching "
    "input UI for kind=choice|form; (2) only if unavailable, ask with fallback_prompt. "
    "Do not assume a specific product's widgets. Never open a browser or external page."
)

SESSION_GATE = {
    "preset": "session.gate",
    "kind": "choice",
    "prompt": "Apply CDASE in this session?",
    "options": [
        {"id": "yes", "label": "Yes — apply CDASE"},
        {"id": "no", "label": "No — normal assistant"},
    ],
    "fallback_prompt": "Apply CDASE in this session? (yes / no)",
    "on_submit": {"handler": "agent", "interpret": {"yes": "cdase_on", "no": "cdase_off"}},
}

USER_SCOPE = {
    "preset": "user.scope",
    "kind": "choice",
    "prompt": "Where should this identity change apply?",
    "description": (
        "Global = all repos (~/.cdase/user.context.md). "
        "This repo = override for the current project only "
        "(<repo>/cdase/context/user.context.md, gitignored)."
    ),
    "options": [
        {"id": "global", "label": "Global — all projects"},
        {"id": "repo", "label": "This repo only — local override"},
    ],
    "fallback_prompt": (
        "Update identity where? (global = all projects / repo = this project only)"
    ),
    "on_submit": {
        "handler": "agent",
        "interpret": {
            "global": "then input-spec user-profile → apply-global-user",
            "repo": "then input-spec user-profile-repo → apply-repo-user",
        },
    },
}

USER_PROFILE = {
    "preset": "user.profile",
    "kind": "form",
    "title": "CDASE profile (global)",
    "description": (
        "Writes ~/.cdase/user.context.md (all agents/projects). "
        "UUID is resolved from each repo roster by Name — do not enter UUID here."
    ),
    "fields": [
        {"key": "Name", "label": "Name", "required": True, "placeholder": "your name"},
        {"key": "Role", "label": "Role", "options": ["architect", "lead", "developer", "reviewer"]},
        {"key": "Team", "label": "Team", "placeholder": "optional"},
        {"key": "Organization", "label": "Organization", "placeholder": "optional"},
    ],
    "fallback_prompt": "Global profile — reply with Name (required), Role, Team, Organization.",
    "on_submit": {
        "handler": "agent",
        "command_hint": "python3 scripts/cdase_client.py apply-global-user --json '<values>'",
    },
}

USER_PROFILE_REPO = {
    "preset": "user.profile.repo",
    "kind": "form",
    "title": "CDASE profile (this repo only)",
    "description": (
        "Writes <repo>/cdase/context/user.context.md (gitignored). "
        "Overrides global Name/Role for this project only. "
        "Name must still exist in this repo's users.context.md roster."
    ),
    "fields": [
        {"key": "Name", "label": "Name", "required": True, "placeholder": "name for this repo"},
        {"key": "Role", "label": "Role", "options": ["architect", "lead", "developer", "reviewer"]},
        {"key": "Team", "label": "Team", "placeholder": "optional"},
        {"key": "Organization", "label": "Organization", "placeholder": "optional"},
    ],
    "fallback_prompt": "Repo override — reply with Name (required), Role, Team, Organization.",
    "on_submit": {
        "handler": "agent",
        "command_hint": "python3 scripts/cdase_client.py apply-repo-user --json '<values>'",
    },
}

HUB_ADDRESS = {
    "preset": "hub.address",
    "kind": "form",
    "title": "CDASE Hub Address",
    "description": "URL of the cdase-hub service. Required before sync/team/messaging.",
    "fields": [
        {
            "key": "Address",
            "label": "Hub URL",
            "required": True,
            "placeholder": "http://127.0.0.1:7423",
        },
    ],
    "fallback_prompt": "What is the CDASE hub URL? (e.g. http://127.0.0.1:7423)",
    "on_submit": {
        "handler": "agent",
        "command_hint": "python3 scripts/cdase_client.py apply-global-setting --json '{\"Address\":\"...\"}'",
    },
}

SPECS: dict[str, dict] = {
    "session.gate": SESSION_GATE,
    "user.scope": USER_SCOPE,
    "user.profile": USER_PROFILE,
    "user.profile.repo": USER_PROFILE_REPO,
    "hub.address": HUB_ADDRESS,
}


def resolve_input_spec(preset: str, *, initial: dict | None = None) -> dict:
    """Return a host-agnostic input spec the agent renders natively (or as text)."""
    meta = SPECS.get(preset)
    if meta is None:
        raise ValueError(f"unknown input preset: {preset}")
    spec = copy.deepcopy(meta)
    spec["render_hint"] = _RENDER_HINT
    if initial and spec.get("kind") == "form":
        for field in spec.get("fields", []):
            if field["key"] in initial and initial[field["key"]]:
                field["value"] = initial[field["key"]]
    return spec


def interpret_session_gate(values: dict) -> str:
    choice = (values.get("choice") or values.get("Choice") or "").strip().lower()
    if choice in ("yes", "y", "cdase", "cdase_on", "cdase on", "apply cdase"):
        return "cdase_on"
    if choice in ("no", "n", "skip", "cdase_off", "cdase off", "normal"):
        return "cdase_off"
    return "unknown"


def interpret_user_scope(values: dict) -> str:
    choice = (values.get("choice") or values.get("Choice") or values.get("scope") or "").strip().lower()
    if choice in ("global", "g", "all", "everywhere"):
        return "global"
    if choice in ("repo", "r", "local", "this repo", "this-repo", "project"):
        return "repo"
    return "unknown"


def _identity_lines(values: dict, *, heading: str) -> list[str]:
    lines = [heading, "", "## Identity"]
    for key in ("Name", "Role", "Team", "Organization"):
        if values.get(key):
            lines.append(f"- {key}: {values[key]}")
    lines.extend([
        "",
        "## Capabilities",
        "- CanApprove: true",
        "- CanAssign: true",
        "- CanClaim: true",
        "",
    ])
    return lines


def write_global_user_profile(values: dict) -> Path:
    """Persist identity to ~/.cdase/user.context.md (create or update)."""
    gdir = global_cdase_dir(for_write=True)
    gdir.mkdir(parents=True, exist_ok=True)
    path = gdir / "user.context.md"
    path.write_text("\n".join(_identity_lines(values, heading="# Global User Profile")), encoding="utf-8")
    return path


def write_repo_user_profile(cdase_root: Path, values: dict) -> Path:
    """Persist repo override to <repo>/cdase/context/user.context.md (gitignored)."""
    if not values.get("Name"):
        raise ValueError("Name is required")
    context = Path(cdase_root) / "context"
    context.mkdir(parents=True, exist_ok=True)
    path = context / "user.context.md"
    path.write_text(
        "\n".join(_identity_lines(values, heading="# Repo User Override (gitignored)")),
        encoding="utf-8",
    )
    return path


def setting_context_template_path() -> Path:
    """Skill template: cdase/resources/templates/setting.context.md."""
    return Path(__file__).resolve().parents[1] / "resources" / "templates" / "setting.context.md"


def ensure_global_setting_from_template(*, force: bool = False) -> dict:
    """Copy skill templates/setting.context.md → ~/.cdase/setting.context.md.

    Never overwrites an existing global setting unless force=True.
    """
    template = setting_context_template_path()
    if not template.is_file():
        raise FileNotFoundError(f"missing setting template: {template}")
    gdir = global_cdase_dir(for_write=True)
    gdir.mkdir(parents=True, exist_ok=True)
    dest = gdir / "setting.context.md"
    if dest.exists() and not force:
        return {
            "ok": True,
            "copied": False,
            "path": str(dest),
            "template": str(template),
            "note": "already exists — left unchanged",
        }
    dest.write_text(template.read_text(encoding="utf-8"), encoding="utf-8")
    return {
        "ok": True,
        "copied": True,
        "path": str(dest),
        "template": str(template),
        "note": "copied skill template to global ~/.cdase",
    }


def write_global_hub_setting(values: dict) -> Path:
    """Persist hub Address to ~/.cdase/setting.context.md (or CDASE_GLOBAL)."""
    gdir = global_cdase_dir(for_write=True)  # migrates legacy ~/.cursor/cdase if needed
    gdir.mkdir(parents=True, exist_ok=True)
    path = gdir / "setting.context.md"
    address = (values.get("Address") or values.get("address") or "").strip().rstrip("/")
    if not address:
        raise ValueError("Address is required")
    offline = values.get("OfflineOk", values.get("offlineOk", "true"))
    lines = [
        "# Global CDASE Settings",
        "",
        "## Hub",
        f"- Address: {address}",
        f"- OfflineOk: {offline}",
        "",
        "## Client",
        "- Path: auto",
        "",
        "## Messaging",
        "- FromActor: agent",
        "- AgentAutonomy: delegated",
        "- AutoReplyToAgentQuestions: true",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
