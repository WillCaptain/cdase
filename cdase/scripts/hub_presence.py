"""Refresh user presence on the CDASE hub ('I'm here') before hub tool calls."""

from __future__ import annotations

from context_loader import trust_csv


def refresh_hub_presence(
    hub_url: str,
    user: dict,
    roster: list[dict],
    hub_call,
    machine_id: str,
    repo_id: str | None = None,
) -> dict:
    """Update hub last_seen for this user. ping if registered; else login (upsert).

    Called automatically before hub-touching client commands so teammates see
    online status without a separate ping step.
    """
    if not user.get("uuid") or not user.get("name"):
        return {"skipped": True, "reason": "identity incomplete"}

    trust = trust_csv(roster)
    base = {"uuid": user["uuid"], "machine_id": machine_id, "trust": trust}
    if repo_id:
        base["repo_id"] = repo_id
    ping = hub_call(hub_url, "POST", "/ping", base)
    if ping.get("ok"):
        return {"ok": True, "method": "ping", "unread": ping.get("unread", 0)}

    login_payload = {**base, "name": user["name"]}
    for key in ("role", "team", "organization"):
        if user.get(key):
            login_payload[key] = user[key]
    login = hub_call(hub_url, "POST", "/login", login_payload)
    if login.get("ok"):
        return {"ok": True, "method": "login", "unread": login.get("unread", 0)}
    if login.get("error"):
        return {"ok": False, "method": "login", "error": login["error"]}
    if ping.get("error"):
        return {"ok": False, "method": "ping", "error": ping["error"]}
    return {"ok": False, "error": "presence refresh failed"}
