"""Trust policy — active project member records are SSOT."""

from __future__ import annotations


def trusted_uuid_set(members: list[dict]) -> set[str]:
    return {
        m["uuid"]
        for m in members
        if m.get("uuid") and m.get("status", "active") == "active"
    }


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
            else "On Hub but not an active project member — ask before trusting"
        ),
    }


def merge_team(roster: list[dict], hub_users: list[dict]) -> list[dict]:
    """Project-member SSOT + Hub superset."""
    trusted = trusted_uuid_set(roster)
    hub_by_uuid = {u.get("uuid"): u for u in hub_users if u.get("uuid")}
    roster_uuids = {m.get("uuid") for m in roster if m.get("uuid")}
    members: list[dict] = []

    for m in roster:
        member_active = m.get("status", "active") == "active"
        member_trusted = member_active and m.get("committed", True)
        hub = hub_by_uuid.get(m["uuid"], {})
        online = member_trusted and bool(hub.get("active"))
        members.append({
            "alias": m.get("alias") or m["name"],
            "name": m["name"],
            "uuid": m["uuid"],
            "role": m.get("role") or hub.get("role"),
            "in_roster": True,
            "trusted": member_trusted,
            "online": online,
            "status": (
                "online" if online
                else "inactive" if not member_active
                else "pending" if not member_trusted
                else "offline"
            ),
            "commit_state": m.get("commit_state"),
            "last_seen": hub.get("last_seen"),
            "source": "member",
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
            f"Sender {msg.get('from') or from_uuid} is not an active project member. "
            "Show the user; do NOT auto-reply until they approve a member record."
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
