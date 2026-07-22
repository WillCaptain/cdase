"""CDASE zero-to-start boot journey — ordered steps before hub tools run."""

from __future__ import annotations

from pathlib import Path

from context_loader import global_cdase_dir, hub_url_state


def global_user_exists() -> bool:
    path = global_cdase_dir() / "user.context.md"
    if not path.exists():
        return False
    text = path.read_text()
    return "Name:" in text and "- Name:" in text and not "- Name: [" in text


def global_setting_exists() -> bool:
    return (global_cdase_dir() / "setting.context.md").exists()


def consumer_cdase_ready(cdase_root: Path) -> bool:
    members = cdase_root / "context" / "members"
    return members.is_dir() and any(members.glob("*.context.md"))


def build_boot_journey(
    *,
    identity_ok: bool,
    settings: dict,
    cdase_root: Path,
    errors: list[str],
) -> dict:
    """Return journey state for agent — what step is next."""
    hub = hub_url_state(settings)
    has_user_file = global_user_exists()
    has_members = consumer_cdase_ready(cdase_root)

    steps = []

    # Step 1 — CDASE opt-in (agent handles before boot; mark assumed done when boot runs)
    steps.append({
        "step": 1,
        "id": "cdase_opt_in",
        "label": "Apply CDASE in this session?",
        "status": "done",
        "note": "Agent asked yes/no before boot",
    })

    # Step 2 — user profile
    if has_user_file and identity_ok:
        steps.append({"step": 2, "id": "user_profile", "label": "Global user profile", "status": "done"})
    else:
        steps.append({
            "step": 2,
            "id": "user_profile",
            "label": "Global user profile",
            "status": "needed",
            "action": "cdase input-spec user-profile",
            "then": "apply-global-user --json '<values>'",
        })

    # Step 3 — hub URL (seeded from skill template on boot; required before hub tools)
    if hub["hub_tools_allowed"]:
        steps.append({
            "step": 3,
            "id": "hub_url",
            "label": "Hub Address",
            "status": "done",
            "address": hub["address"],
            "note": "From ~/.cdase/setting.context.md (skill template default: https://12th.ai/cdase)",
        })
    else:
        steps.append({
            "step": 3,
            "id": "hub_url",
            "label": "Hub Address",
            "status": "needed",
            "action": "cdase init-global-setting",
            "then": "or input-spec hub-address → apply-global-setting for a custom URL",
            "note": (
                "Copy skill templates/setting.context.md → ~/.cdase/ "
                "(boot does this automatically). Do NOT sync until set."
            ),
        })

    # Step 4 — activate + messages (sync)
    can_sync = identity_ok and hub["hub_tools_allowed"]
    if can_sync:
        steps.append({
            "step": 4,
            "id": "sync",
            "label": "Activate on hub + retrieve messages",
            "status": "ready",
            "action": "cdase sync",
        })
    else:
        steps.append({
            "step": 4,
            "id": "sync",
            "label": "Activate on hub + retrieve messages",
            "status": "blocked",
            "blocked_by": _block_reason(has_user_file, identity_ok, hub),
        })

    # Step 7 — list users (team) — user asks when ready
    if can_sync and has_members:
        steps.append({
            "step": 7,
            "id": "team",
            "label": "List team (members + Hub new_to_you)",
            "status": "ready",
            "action": "cdase team",
            "trigger": "User asks who is on the project / list users",
        })
    else:
        steps.append({
            "step": 7,
            "id": "team",
            "label": "List team",
            "status": "blocked",
            "blocked_by": "complete steps 2–4 first",
        })

    next_step = _next_action(steps)
    hub_blocked = not hub["hub_tools_allowed"]

    return {
        "journey": steps,
        "next_step": next_step,
        "hub_tools_allowed": hub["hub_tools_allowed"],
        "hub_tools_blocked": hub_blocked,
        "hub_url": hub,
        "identity_ok": identity_ok,
        "has_user_profile": has_user_file,
        "has_members": has_members,
        "errors": errors,
        "agent_rule": _agent_rule(hub_blocked, next_step),
    }


def _block_reason(has_user: bool, identity_ok: bool, hub: dict) -> str:
    if not has_user or not identity_ok:
        return "user_profile_incomplete"
    if not hub["hub_tools_allowed"]:
        return "hub_url_not_configured"
    return "unknown"


def _next_action(steps: list[dict]) -> dict | None:
    for s in steps:
        if s["status"] == "needed":
            return {"step": s["step"], "id": s["id"], "action": s.get("action"), "then": s.get("then")}
        if s["status"] == "ready" and s["id"] == "sync":
            return {"step": s["step"], "id": s["id"], "action": s.get("action")}
    return None


def _agent_rule(hub_blocked: bool, next_step: dict | None) -> str:
    if hub_blocked:
        return (
            "Hub URL not configured. Run boot (or init-global-setting) to copy "
            "skill templates/setting.context.md → ~/.cdase/setting.context.md "
            "(default https://12th.ai/cdase). Only ask hub-address if the user wants a different URL. "
            "Do NOT invoke sync/team/send/inbox until the file exists."
        )
    if next_step and next_step.get("id") == "user_profile":
        return "Collect user profile (input-spec user-profile), then apply-global-user."
    if next_step and next_step.get("id") == "sync":
        return "Run sync to login on hub and retrieve messages. Then user may ask to list team (team)."
    return "Boot complete. Run sync before each answer; run team when user asks to list users."
