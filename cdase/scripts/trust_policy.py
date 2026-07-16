"""Trust policy — repo roster is SSOT; hub may have extra users/messages."""

from __future__ import annotations


def trusted_uuid_set(roster: list[dict]) -> set[str]:
    return {m["uuid"] for m in roster if m.get("uuid")}


def classify_hub_user(hub_user: dict, trusted: set[str]) -> dict:
    uid = hub_user.get("uuid")
    in_roster = uid in trusted if uid else False
    return {
        **hub_user,
        "in_roster": in_roster,
        "trusted": in_roster,
        "status": "roster" if in_roster else "new_to_you",
        "source": "hub",
        "note": (
            None
            if in_roster
            else "On hub but not in your users.context.md — ask user to confirm before trusting"
        ),
    }


def merge_team(roster: list[dict], hub_users: list[dict]) -> list[dict]:
    """Roster SSOT + hub superset (hub may have users not yet in repo)."""
    trusted = trusted_uuid_set(roster)
    hub_by_uuid = {u.get("uuid"): u for u in hub_users if u.get("uuid")}
    roster_uuids = trusted
    members: list[dict] = []

    for m in roster:
        hub = hub_by_uuid.get(m["uuid"], {})
        active = bool(hub.get("active"))
        members.append({
            "name": m["name"],
            "uuid": m["uuid"],
            "role": m.get("role") or hub.get("role"),
            "in_roster": True,
            "trusted": True,
            "online": active,
            "status": "online" if active else "offline",
            "last_seen": hub.get("last_seen"),
            "source": "roster",
        })

    for hu in hub_users:
        uid = hu.get("uuid")
        if not uid or uid in roster_uuids:
            continue
        active = bool(hu.get("active"))
        row = classify_hub_user(hu, trusted)
        row["online"] = active
        row["status"] = "new_to_you"
        members.append(row)

    members.sort(key=lambda x: (
        0 if x.get("in_roster") else 1,
        0 if x.get("online") else 1,
        (x.get("name") or "").lower(),
    ))
    return members


def classify_message(msg: dict, trusted: set[str]) -> dict:
    from_uuid = msg.get("from_uuid")
    trusted_sender = from_uuid in trusted if from_uuid else False
    out = dict(msg)
    out["trusted_sender"] = trusted_sender
    out["auto_reply_allowed"] = trusted_sender
    if not trusted_sender:
        out["status"] = "unknown_sender"
        out["note"] = (
            f"Sender {msg.get('from') or from_uuid} is not in your users.context.md. "
            "Show to user; do NOT auto-reply until user confirms they are safe to trust."
        )
    else:
        out["status"] = "trusted"
    return out


def split_messages(messages: list[dict], roster: list[dict]) -> dict:
    trusted = trusted_uuid_set(roster)
    classified = [classify_message(m, trusted) for m in messages]
    trusted_msgs = [m for m in classified if m["trusted_sender"]]
    unknown_msgs = [m for m in classified if not m["trusted_sender"]]
    return {
        "messages": classified,
        "trusted": trusted_msgs,
        "unknown": unknown_msgs,
        "trusted_unread_count": sum(1 for m in trusted_msgs if not m.get("read")),
        "unknown_unread_count": sum(1 for m in unknown_msgs if not m.get("read")),
    }
