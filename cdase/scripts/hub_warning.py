"""Build agent-facing hub-down warnings for CDASE mode."""

from __future__ import annotations


def build_hub_warning(
    hub_url: str,
    hub_health: dict,
    *,
    offline_ok: bool,
    context: str = "check",
) -> dict | None:
    """Return a warning payload when the hub is unreachable; None when hub is up."""
    if hub_health.get("ok") is True:
        return None

    error = hub_health.get("error") or "hub unreachable"
    if offline_ok:
        impact = (
            "Team online status and agent messaging are unavailable until the hub is back. "
            "Local CDASE work can continue (Hub.OfflineOk=true)."
        )
    else:
        impact = (
            "Hub actions are blocked until the hub is running (Hub.OfflineOk=false)."
        )

    message = (
        f"CDASE Hub is unreachable at {hub_url}.\n"
        f"{error}\n"
        f"Start locally: cd hub && mvn -q package && java -jar target/cdase-hub-1.0.0.jar\n"
        f"{impact}"
    )

    return {
        "show_to_user": True,
        "message": message,
        "short_message": f"hub offline ({hub_url})",
        "hub_address": hub_url,
        "offline_ok": offline_ok,
        "context": context,
        "agent_rule": (
            "CDASE mode: show hub_warning.message to the user — do not ignore a down hub. "
            "Then continue local work only if offline_ok is true."
        ),
    }
