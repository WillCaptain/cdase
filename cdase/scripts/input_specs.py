"""Host-agnostic input specs for CDASE.

CDASE never ships its own UI. It emits a *declarative* input request; the agent
renders it with the host's richest native input UI (e.g. Cursor's multiple-choice /
question card) and falls back to plain text when the host has none. The agent owns
the post-submit action (e.g. `apply-global-user`).
"""

from __future__ import annotations

import copy
from pathlib import Path

from context_loader import global_cdase_dir

_RENDER_HINT = (
    "Render this using your host's richest native input UI "
    "(in Cursor: the multiple-choice / question card). "
    "If the host has no native input UI, ask in plain text using fallback_prompt. "
    "Never open a browser or external page."
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

USER_PROFILE = {
    "preset": "user.profile",
    "kind": "form",
    "title": "Set your CDASE profile (global, once)",
    "description": "UUID is resolved from the repo roster by Name — do not enter it here.",
    "fields": [
        {"key": "Name", "label": "Name", "required": True, "placeholder": "your name"},
        {"key": "Role", "label": "Role", "options": ["architect", "lead", "developer", "reviewer"]},
        {"key": "Team", "label": "Team", "placeholder": "optional"},
        {"key": "Organization", "label": "Organization", "placeholder": "optional"},
    ],
    "fallback_prompt": "Reply with your Name (required), Role, Team, Organization.",
    "on_submit": {
        "handler": "agent",
        "command_hint": "python3 scripts/cdase_client.py apply-global-user --json '<values>'",
    },
}

SPECS: dict[str, dict] = {
    "session.gate": SESSION_GATE,
    "user.profile": USER_PROFILE,
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


def write_global_user_profile(values: dict) -> Path:
    """Agent tool: persist collected identity to the global user.context.md."""
    gdir = global_cdase_dir()
    gdir.mkdir(parents=True, exist_ok=True)
    path = gdir / "user.context.md"

    lines = ["# Global User Profile", "", "## Identity"]
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
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
