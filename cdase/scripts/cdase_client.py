#!/usr/bin/env python3
"""CDASE Client — agent tool surface for the Hub.

SSOT layers:
  ~/.cdase/user.context.md            — global identity (Name, set once; all agents)
  ~/.cdase/setting.context.md         — global hub defaults
  /cdase/context/members/*.context.md — project members + trust SSOT (committed)
  /cdase/context/user.context.md      — optional repo identity override (gitignored)
  /cdase/context/setting.context.md   — optional repo settings override

  Override dir with CDASE_GLOBAL. Legacy ~/.cursor/cdase → ~/.cdase (copy missing files).

Hub URL: env → repo setting → global setting → template default
User id: sha256(machine_id)[:8] — different machine = different user
Display Alias: repo override → member record → global profile default

Commands:
  boot                        zero-to-start journey — what step is next (steps 1–7)
  check                       validate identity + hub health (no hub user list)
  sync                        login + inbox (blocked until hub URL explicitly set)
  discover                    scan workspace for git repos and consumer cdase/ locations
  legacy-classify             classify CDASE adoption separately from code maturity
  legacy-scan-spec            emit an isolated read-only scan job
  legacy-scan-save            validate and persist the isolated report
  legacy-approval-spec        emit host-native multi-select approval
  legacy-api-apply            generate contracts for selected candidates only
  legacy-api-upload           upload approved committed imports, then release
  team                        project members + Hub presence
  send TO BODY                send to active member (TO = alias or user id)
  send-file TO PATH           send repo file (--intent file); repo boundary enforced
  inbox [--all] [--keep]      trusted messages from hub
  login / ping / users        legacy presence (deprecated — hub has no user list)
  whoami                      resolved identity + settings
  input-spec PRESET           print a host-agnostic input spec for the agent to render
  apply-global-user           create/update ~/.cdase/user.context.md (all projects)
  apply-repo-user             create/update <repo>/cdase/context/user.context.md (override)
  apply-global-setting        write hub Address to ~/.cdase/setting.context.md
  init-global-setting         copy skill templates/setting.context.md → ~/.cdase/ (once)

Input model (no CDASE-owned UI, no browser):
  CDASE emits a declarative input spec (input-spec PRESET). The AGENT maps it to
  that host's input UI first; plain text only if the host has none. Widget chrome
  is host-specific — never assumed. The agent then applies the result.
  Presets: session.gate, user.scope, user.profile, user.profile.repo, hub.address.

  Identity scope (mandatory when user asks to set/update profile and global already exists):
    1. input-spec user-scope → global | this-repo
    2. then user-profile + apply-global-user, OR user-profile-repo + apply-repo-user
  First-time boot with missing global profile → user-profile only (global implied).

Hub URL gate: sync/team/send/inbox/users require an explicit Address in global/repo
settings or CDASE_HUB_URL — built-in localhost default alone does NOT enable hub tools.
On first boot, missing ~/.cdase/setting.context.md is seeded by copying
cdase/resources/templates/setting.context.md (default https://12th.ai/cdase).
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from cdase_runtime import find_cdase_root
from context_loader import (
    hub_url_state,
    load_members,
    load_settings,
    load_user_context,
    resolve_client_script,
    resolve_hub_url,
    resolve_recipient,
    trust_csv,
    trusted_uuids,
    validate_identity,
)
from repo_boundary import (
    classify_message_body,
    find_git_root,
    read_repo_file,
    resolve_repo_path,
)
from repo_discovery import classify_workspace, is_framework_repo
from repo_id import resolve_repo_id
from input_specs import (
    resolve_input_spec,
    write_global_user_profile,
    write_repo_user_profile,
    write_global_hub_setting,
    ensure_global_setting_from_template,
)
from boot_journey import build_boot_journey
from team import (
    build_agent_team_brief,
    git_contributors,
    member_commit_states,
    members_are_committed,
    team_summary,
)
from trust_policy import merge_team, split_messages, classify_hub_user
from hub_presence import refresh_hub_presence
from hub_warning import build_hub_warning
from hub_sync import build_sync_result
from machine_identity import raw_machine_id, machine_user_id, ensure_machine_member
from legacy_api_scan import (
    build_scan_job,
    collect_legacy_evidence,
    validate_scan_report,
)
from legacy_api_approval import (
    apply_approved_candidates,
    build_approval_spec,
    load_json,
    save_scan_report,
)
from repo_maturity import classify_repo_maturity
from api_registry import (
    content_hash,
    find_api_definition,
    legacy_publish_gate,
    parse_api_blocks,
    sync_state,
    with_source_revision,
)


def machine_id() -> str:
    return raw_machine_id()


def hub_call(hub_url: str, method, path, payload=None, params=None, headers=None):
    url = hub_url + path
    if params:
        from urllib.parse import urlencode
        url += "?" + urlencode(params)
    data = json.dumps(payload).encode() if payload is not None else None
    request_headers = {"Content-Type": "application/json"}
    if headers:
        request_headers.update(headers)
    req = Request(url, data=data, method=method, headers=request_headers)
    try:
        with urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except HTTPError as e:
        try:
            body = json.loads(e.read())
            if isinstance(body, dict):
                body.setdefault("status", e.code)
            return body
        except Exception:
            return {"error": f"HTTP {e.code}", "status": e.code}
    except URLError as e:
        return {
            "error": f"hub unreachable at {hub_url} ({e.reason}). "
                     f"Check setting.context.md Hub.Address or deploy: "
                     f"cd hub && mvn -q package && java -jar target/cdase-hub-1.1.0.jar",
            "offline_ok": True,
        }


def out(obj, code=0):
    print(json.dumps(obj, indent=2, ensure_ascii=False))
    sys.exit(code)


def load_context():
    cdase_root = find_cdase_root(SCRIPT_DIR)
    settings = load_settings(cdase_root)
    hub_url = resolve_hub_url(settings)
    user = load_user_context(cdase_root)
    roster = load_members(cdase_root)
    ok, errors = validate_identity(user, roster)
    client_script = resolve_client_script(settings, SCRIPT_DIR)
    git_root = find_git_root(cdase_root)
    repo_id, repo_id_source = resolve_repo_id(cdase_root, git_root, settings)
    return user, roster, ok, errors, cdase_root, settings, hub_url, client_script, git_root, repo_id, repo_id_source


def require_valid(user, roster, ok, errors):
    if not ok:
        out({"ok": False, "errors": errors}, 1)


def hub_error_is_offline(res: dict, settings: dict) -> bool:
    return bool(res.get("error")) and settings.get("hub_offline_ok", True)


def fetch_inbox(
    hub_url: str,
    user: dict,
    roster: list[dict],
    *,
    keep: bool = False,
    all_msgs: bool = False,
    include_unknown: bool = True,
) -> dict:
    """Fetch inbox; when include_unknown, get all senders and classify against roster."""
    params = {
        "uuid": user["uuid"],
        "all": "1" if all_msgs else "0",
    }
    if include_unknown:
        params["trust"] = "all"
    else:
        params["trust"] = trust_csv(roster)
    res = hub_call(hub_url, "GET", "/messages", params=params)
    if res.get("error"):
        return res
    split = split_messages(res.get("messages") or [], roster)
    # Only ack trusted unread unless user explicitly keeps
    if not keep:
        trusted_unread_ids = [m["id"] for m in split["trusted"] if not m.get("read")]
        if trusted_unread_ids:
            hub_call(hub_url, "POST", "/messages/ack",
                     {"uuid": user["uuid"], "ids": trusted_unread_ids})
    res["messages"] = split["messages"]
    res["trusted"] = split["trusted"]
    res["unknown"] = split["unknown"]
    res["trusted_unread_count"] = split["trusted_unread_count"]
    res["unknown_unread_count"] = split["unknown_unread_count"]
    return res


def hub_login(hub_url: str, user: dict, roster: list, repo_id: str | None) -> dict:
    return refresh_hub_presence(hub_url, user, roster, hub_call, machine_id(), repo_id)


def hub_tools_blocked_response(settings: dict, cmd: str) -> None:
    hub = hub_url_state(settings)
    if hub["hub_tools_allowed"]:
        return
    out({
        "ok": False,
        "hub_tools_blocked": True,
        "reason": "hub_url_not_configured",
        "command": cmd,
        "agent_rule": (
            "Hub URL not set. Run boot or init-global-setting to copy "
            "skill templates/setting.context.md → ~/.cdase/ (default https://12th.ai/cdase). "
            "Ask hub-address only if the user wants a different URL. "
            "Do NOT call sync/team/send/inbox until configured."
        ),
        "next_step": {
            "action": "cdase init-global-setting",
            "then": "boot → sync",
        },
    }, 1)


def main():
    p = argparse.ArgumentParser(description="CDASE Hub client")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("discover", help="scan workspace for git repos and cdase/ runtimes")
    sp.add_argument("--workspace", default=None, help="workspace folder (default: auto-detect from cwd)")
    sp = sub.add_parser("legacy-classify", help="classify CDASE adoption and codebase maturity")
    sp.add_argument("--repo", default=None)
    sp = sub.add_parser("legacy-scan-spec", help="emit a fresh isolated read-only scan job")
    sp.add_argument("--repo", default=None)
    sp = sub.add_parser("legacy-scan-save", help="validate and persist an isolated scan report")
    sp.add_argument("--json", required=True)
    sp = sub.add_parser("legacy-approval-spec", help="render confidence-grouped API approval")
    sp.add_argument("--report", required=True)
    sp = sub.add_parser("legacy-api-apply", help="write only user-approved legacy API contracts")
    sp.add_argument("--report", required=True)
    sp.add_argument("--selection-json", required=True)
    sub.add_parser("boot", help="initialize missing profile defaults and project member state")
    sub.add_parser("check", help="validate identity + hub health")
    sub.add_parser("sync", help="login + inbox (requires explicit hub URL + identity)")
    sub.add_parser(
        "init-global-setting",
        help="copy the packaged setting template to <GLOBAL_CDASE> (no overwrite)",
    )
    sub.add_parser("login", help="register on hub (also runs in sync)")
    sub.add_parser("ping", help="heartbeat on hub")
    sub.add_parser("team", help="project members + Hub presence (new_to_you if not a member)")
    sub.add_parser("users", help="hub user list (informational)")
    sub.add_parser("whoami")

    sp = sub.add_parser("input-spec", help="print a host-agnostic input spec (agent renders it natively)")
    sp.add_argument(
        "preset",
        choices=["user-profile", "user-profile-repo", "user-scope", "session-gate", "hub-address"],
        help="input preset id",
    )

    sp = sub.add_parser("apply-global-user", help="create/update <GLOBAL_CDASE>/user.context.md")
    sp.add_argument("--json", required=True, help='JSON e.g. {"Name":"will"}')

    sp = sub.add_parser("apply-repo-user", help="create/update repo cdase/context/user.context.md (gitignored)")
    sp.add_argument("--json", required=True, help='JSON e.g. {"Name":"will"}')

    sp = sub.add_parser("apply-global-setting")
    sp.add_argument("--json", required=True, help='JSON e.g. {"Address":"http://127.0.0.1:7423"}')

    sp = sub.add_parser("send")
    sp.add_argument("to")
    sp.add_argument("body")
    sp.add_argument("--type", default="message", choices=["message", "task"])
    sp.add_argument("--subject", default=None)
    sp.add_argument("--intent", default="message",
                    choices=["message", "question", "answer", "notify", "task", "handoff", "file"])
    sp.add_argument("--thread-id", default=None)
    sp.add_argument("--from-actor", default=None, choices=["human", "agent"])
    sp.add_argument("--user-approved", action="store_true",
                    help="user explicitly approved out-of-repo content")

    sp = sub.add_parser("send-file")
    sp.add_argument("to")
    sp.add_argument("path", help="repo-relative or absolute path under git root")
    sp.add_argument("--subject", default=None)
    sp.add_argument("--thread-id", default=None)
    sp.add_argument("--from-actor", default=None, choices=["human", "agent"])
    sp.add_argument("--note", default="", help="optional message prepended to file content")

    sp = sub.add_parser("inbox")
    sp.add_argument("--all", action="store_true")
    sp.add_argument("--keep", action="store_true")

    sp = sub.add_parser("kb-save")
    sp.add_argument("key")
    sp.add_argument("content")
    sp.add_argument("--tags", default="")

    sp = sub.add_parser("kb-find")
    sp.add_argument("query")

    sp = sub.add_parser("api-search", help="search the global API pool before REUSE/EVOLVE/CREATE")
    sp.add_argument("query")
    sp.add_argument("--system")
    sp.add_argument("--module")
    sp.add_argument("--status")
    sp.add_argument("--kind")
    sp.add_argument("--context-system", help="soft reranking context; does not restrict global search")
    sp.add_argument("--context-module", help="soft reranking context; does not restrict global search")
    sp.add_argument("--limit", type=int, default=20)

    sp = sub.add_parser("api-publish", help="reserve or update one API version")
    sp.add_argument("--json", required=True, help="structured API definition JSON")

    sp = sub.add_parser("api-sync", help="publish all ```json cdase-api blocks in a repo file")
    sp.add_argument("path", help="repo-local module API registry")
    sp.add_argument("--check", action="store_true", help="verify Hub state without writing")

    sp = sub.add_parser("api-get")
    sp.add_argument("api_id")
    sp.add_argument("--version")

    sp = sub.add_parser("api-transition")
    sp.add_argument("api_id")
    sp.add_argument("version")
    sp.add_argument(
        "status",
        choices=["DEVELOPING", "RELEASED", "SUPERSEDED", "DEPRECATED", "RETIRED"],
    )
    sp.add_argument("--note")
    sp.add_argument("--superseded-by-version")

    sp = sub.add_parser("api-graph")
    sp.add_argument("--system")
    sp = sub.add_parser(
        "legacy-api-upload",
        help="publish approved committed legacy contracts and release them",
    )
    sp.add_argument("--approval", required=True)

    sp = sub.add_parser("watch")
    sp.add_argument("--interval", type=int, default=60)

    args = p.parse_args()
    if args.cmd == "discover":
        ws = Path(args.workspace).resolve() if args.workspace else None
        info = classify_workspace(ws)
        info["cdase_root_env"] = os.environ.get("CDASE_ROOT")
        if info["scenario"] == "1_framework_only":
            info["warning"] = (
                "Do NOT initialize consumer cdase/ in the CDASE framework repo. "
                "Open the target application repo or parent workspace."
            )
        out(info)

    try:
        user, roster, ok, errors, cdase_root, settings, hub_url, client_script, git_root, repo_id, repo_id_source = load_context()
    except RuntimeError as exc:
        out({"ok": False, "error": str(exc), "next_step": "cdase discover"}, 1)
    trust = trust_csv(roster)
    default_actor = settings.get("messaging_from_actor", "agent")

    if args.cmd == "legacy-classify":
        target = Path(args.repo).resolve() if args.repo else (git_root or Path.cwd())
        out({"ok": True, "repository": str(target), **classify_repo_maturity(target)})

    if args.cmd == "legacy-scan-spec":
        target = Path(args.repo).resolve() if args.repo else (git_root or Path.cwd())
        evidence = collect_legacy_evidence(target)
        if evidence["maturity"]["codebase_state"] not in {"LEGACY", "PARTIAL_LEGACY"}:
            out({
                "ok": False,
                "error": "legacy scan is only valid for LEGACY or PARTIAL_LEGACY",
                "maturity": evidence["maturity"],
            }, 1)
        out({"ok": True, "job": build_scan_job(target, evidence)})

    if args.cmd == "legacy-scan-save":
        try:
            report = validate_scan_report(json.loads(args.json))
            paths = save_scan_report(cdase_root, report)
        except (ValueError, json.JSONDecodeError) as exc:
            out({"ok": False, "error": str(exc)}, 1)
        out({"ok": True, "scan_id": report["scan_id"], "artifacts": paths})

    if args.cmd == "legacy-approval-spec":
        path, path_error = resolve_repo_path(args.report, cdase_root, git_root)
        if path_error:
            out({"ok": False, "error": path_error}, 1)
        try:
            spec = build_approval_spec(load_json(path))
        except (ValueError, json.JSONDecodeError) as exc:
            out({"ok": False, "error": str(exc)}, 1)
        out(spec)

    if args.cmd == "legacy-api-apply":
        path, path_error = resolve_repo_path(args.report, cdase_root, git_root)
        if path_error:
            out({"ok": False, "error": path_error}, 1)
        try:
            selection = json.loads(args.selection_json)
            name = user.get("name")
            if not name:
                raise ValueError("user Name is required before approving legacy APIs")
            if not repo_id:
                raise ValueError("repository id is required before approving legacy APIs")
            result = apply_approved_candidates(
                cdase_root,
                load_json(path),
                selection,
                repo_id=repo_id,
                owner=name,
            )
        except (ValueError, json.JSONDecodeError) as exc:
            out({"ok": False, "error": str(exc)}, 1)
        out(result)

    if args.cmd == "check":
        discovery = classify_workspace()
        health = hub_call(hub_url, "GET", "/health")
        out({
            "ok": ok,
            "identity": {
                "alias": user.get("alias"),
                "name": user.get("name"),
                "uuid": user.get("uuid"),
                "source": user.get("identity_source"),
                "uuid_from_members": user.get("uuid_from_members", False),
            },
            "member_count": len(roster),
            "trusted_uuids": trusted_uuids(roster),
            "members": roster,
            "workspace": {
                "path": discovery["workspace"],
                "scenario": discovery["scenario"],
                "hint": discovery["hint"],
                "bootstrap_policy": discovery.get("bootstrap_policy"),
                "repos_to_bootstrap": [r["path"] for r in discovery.get("repos_to_bootstrap", [])],
                "active_cdase_root": discovery.get("active_cdase_root"),
                "framework_repos": [r["path"] for r in discovery["framework_repos"]],
                "consumer_without_cdase": [r["path"] for r in discovery["consumer_repos_without_cdase"]],
            },
            "settings": {
                "hub_address": hub_url,
                "hub_offline_ok": settings.get("hub_offline_ok"),
                "client_path": str(client_script),
                "client_command": "cdase",
                "messaging_from_actor": default_actor,
                "agent_autonomy": settings.get("agent_autonomy"),
                "auto_reply_to_agent_questions": settings.get("auto_reply_to_agent_questions"),
                "source": settings.get("source"),
                "global_dir": settings.get("global_dir"),
                "cdase_root": str(cdase_root),
                "cdase_root_env": os.environ.get("CDASE_ROOT"),
            },
            "hub_health": health if not health.get("error") else {"error": health["error"]},
            "hub_warning": build_hub_warning(
                hub_url, health, offline_ok=settings.get("hub_offline_ok", True), context="check"
            ),
            "repo_id": repo_id,
            "repo_id_source": repo_id_source,
            "hub_model": "active committed members=trust SSOT; Hub=presence/messages superset",
            "hub_url": hub_url_state(settings),
            "errors": errors,
        }, 0 if ok else 1)

    if args.cmd == "init-global-setting":
        try:
            seed = ensure_global_setting_from_template()
        except FileNotFoundError as e:
            out({"ok": False, "error": str(e)}, 1)
        out({
            **seed,
            "agent_rule": (
                "Global setting seeded from skill template (https://12th.ai/cdase). "
                "If user wants a different hub, run input-spec hub-address → apply-global-setting."
            ),
            "next_step": "cdase boot",
        })

    if args.cmd == "boot":
        # First boot: copy skill templates/setting.context.md → ~/.cdase/ (no overwrite)
        try:
            seed = ensure_global_setting_from_template()
        except FileNotFoundError:
            seed = {"ok": False, "copied": False, "note": "template missing"}
        if seed.get("copied"):
            settings = load_settings(cdase_root)
            hub_url = resolve_hub_url(settings)
        member_ensure = ensure_machine_member(cdase_root)
        user = load_user_context(cdase_root)
        roster = load_members(cdase_root)
        ok, errors = validate_identity(user, roster)
        journey = build_boot_journey(
            identity_ok=ok,
            settings=settings,
            cdase_root=cdase_root,
            errors=errors,
        )
        maturity = None
        if git_root and not is_framework_repo(git_root):
            maturity = classify_repo_maturity(git_root)
        out({
            "ok": True,
            "global_setting_seed": seed,
            "member_ensure": member_ensure,
            "identity": {
                "alias": user.get("alias"),
                "name": user.get("name"),
                "user_id": user.get("uuid"),
                "machine_id": user.get("machine_id") or machine_id(),
                "model": "machine_as_user",
            },
            "maturity": maturity,
            "legacy_onboarding": (
                {
                    "recommended": True,
                    "next": "legacy-scan-spec",
                    "agent_rule": (
                        "codebase is LEGACY or PARTIAL_LEGACY — offer Legacy Onboarding "
                        "before Feature/Function work; scan in a fresh isolated session"
                    ),
                }
                if maturity and maturity.get("legacy_scan_recommended")
                else {"recommended": False}
            ),
            **journey,
        })

    if args.cmd == "sync":
        hub_tools_blocked_response(settings, "sync")
        health = hub_call(hub_url, "GET", "/health")
        hwarn = build_hub_warning(
            hub_url, health, offline_ok=settings.get("hub_offline_ok", True), context="sync"
        )
        presence = None
        inbox_res = None
        if ok and not health.get("error"):
            presence = hub_login(hub_url, user, roster, repo_id)
            inbox_res = fetch_inbox(hub_url, user, roster, keep=True, include_unknown=True)
            if hub_error_is_offline(inbox_res, settings):
                inbox_res = {"error": inbox_res["error"]}
        out(build_sync_result(
            hub_health=health if not health.get("error") else {"error": health.get("error")},
            hub_warning=hwarn,
            inbox_raw=inbox_res,
            roster=roster,
            presence=presence,
            identity_ok=ok,
            errors=errors,
        ), 0 if ok or settings.get("hub_offline_ok") else 1)

    if args.cmd == "team":
        hub_tools_blocked_response(settings, "team")
        members_path = cdase_root / "context" / "members"
        hub_res = hub_call(hub_url, "GET", "/users", params={"repo_id": repo_id} if repo_id else None)
        hub_offline = bool(hub_res.get("error"))
        hub_users = [] if hub_offline else hub_res.get("users", [])
        if ok and not hub_offline:
            hub_login(hub_url, user, roster, repo_id)
        members = merge_team(roster, hub_users)
        known_names = {m.get("name") for m in roster} | {m.get("name") for m in members}
        git_only = git_contributors(git_root, known_names)
        committed = members_are_committed(cdase_root, git_root)
        commit_states = member_commit_states(cdase_root, git_root)
        brief = build_agent_team_brief(user, members, hub_offline=hub_offline)
        out({
            "ok": True,
            "agent_rule": brief["agent_rule"],
            "agent_brief": brief["agent_brief"],
            "others_count": brief["others_count"],
            "new_to_you": brief.get("new_to_you", []),
            "must_not_auto_trust": brief.get("must_not_auto_trust", []),
            "must_use_agent_brief": brief["must_use_this_brief"],
            "repo_id": repo_id,
            "members_path": str(members_path),
            "members_committed": committed,
            "member_commit_states": commit_states,
            "summary": team_summary(members, hub_offline=hub_offline, git_only=git_only),
            "members": members,
            "git_contributors": git_only,
            "hub_online": not hub_offline,
            "trust_model": "active committed member records = trust; hub may include new_to_you",
        })

    if args.cmd == "whoami":
        out({
            "name": user.get("name"),
            "uuid": user.get("uuid"),
            "machine_id": machine_id(),
            "hub": hub_url,
            "identity_source": user.get("identity_source"),
            "global_dir": user.get("global_dir"),
            "settings_source": settings.get("source"),
            "hub_offline_ok": settings.get("hub_offline_ok"),
            "client": str(client_script),
            "cdase_root": str(cdase_root),
            "member_count": len(roster),
            "identity_valid": ok,
            "errors": errors if not ok else [],
        })

    if args.cmd == "input-spec":
        preset_map = {
            "user-profile": "user.profile",
            "user-profile-repo": "user.profile.repo",
            "user-scope": "user.scope",
            "session-gate": "session.gate",
            "hub-address": "hub.address",
        }
        preset_id = preset_map.get(args.preset, args.preset.replace("-", "."))
        initial = None
        if preset_id in ("user.profile", "user.profile.repo"):
            # Prefill from resolved identity so updates are easy
            initial = {k: user.get(k.lower()) for k in ("Name", "Role", "Team", "Organization")
                       if user.get(k.lower())}
        if preset_id == "hub.address":
            initial = {"Address": settings.get("hub_address")} if hub_url_state(settings)["explicit"] else None
        spec = resolve_input_spec(preset_id, initial=initial)
        if preset_id == "user.profile":
            spec["scope"] = "global"
            spec["apply_command"] = "cdase apply-global-user --json '<values>'"
        if preset_id == "user.profile.repo":
            spec["scope"] = "repo"
            spec["apply_command"] = "cdase apply-repo-user --json '<values>'"
        if preset_id == "user.scope":
            spec["agent_rule"] = (
                "Ask scope BEFORE collecting fields. "
                "global → input-spec user-profile → apply-global-user. "
                "repo → input-spec user-profile-repo → apply-repo-user. "
                "First boot with missing global profile: skip scope, use user-profile (global)."
            )
        if preset_id == "hub.address":
            spec["apply_command"] = "cdase apply-global-setting --json '{\"Address\":\"...\"}'"
        out(spec)

    if args.cmd == "apply-global-user":
        try:
            values = json.loads(args.json)
        except json.JSONDecodeError as e:
            out({"ok": False, "error": f"invalid JSON: {e}"}, 1)
        if not values.get("Name"):
            out({"ok": False, "error": "Name is required"}, 1)
        path = write_global_user_profile(values)
        member_ensure = ensure_machine_member(cdase_root)
        out({
            "ok": True,
            "scope": "global",
            "path": str(path),
            "values": values,
            "member_ensure": member_ensure,
            "user_id": machine_user_id(),
            "next_step": "boot then sync",
            "agent_rule": (
                "Global Name saved. boot/apply-global-user adds this machine to "
                "members/<user-id>.context.md when missing. Commit the member record when ready."
            ),
        })

    if args.cmd == "apply-repo-user":
        try:
            values = json.loads(args.json)
        except json.JSONDecodeError as e:
            out({"ok": False, "error": f"invalid JSON: {e}"}, 1)
        try:
            path = write_repo_user_profile(cdase_root, values)
            member_ensure = ensure_machine_member(cdase_root)
        except ValueError as e:
            out({"ok": False, "error": str(e)}, 1)
        out({
            "ok": True,
            "scope": "repo",
            "path": str(path),
            "values": values,
            "member_ensure": member_ensure,
            "agent_rule": (
                "Repo override written (gitignored). "
                "The project Alias is published to this machine's member record. Run check/boot next."
            ),
            "next_step": "cdase check",
        })

    if args.cmd == "apply-global-setting":
        try:
            values = json.loads(args.json)
        except json.JSONDecodeError as e:
            out({"ok": False, "error": f"invalid JSON: {e}"}, 1)
        try:
            path = write_global_hub_setting(values)
        except ValueError as e:
            out({"ok": False, "error": str(e)}, 1)
        out({
            "ok": True,
            "path": str(path),
            "values": values,
            "next_step": "cdase boot, then cdase sync",
            "agent_rule": "Hub URL saved. Run boot, then sync to activate and retrieve messages.",
        })

    if args.cmd == "users":
        hub_tools_blocked_response(settings, "users")
        params = {"repo_id": repo_id} if repo_id else None
        res = hub_call(hub_url, "GET", "/users", params=params)
        if hub_error_is_offline(res, settings):
            out({"offline": True, "error": res["error"], "hub_offline_ok": True})
        trusted = set(trusted_uuids(roster))
        users = [classify_hub_user(u, trusted) for u in res.get("users", [])]
        out({"users": users, "repo_id": repo_id, "note": "Compare each user to local member records"})

    read_only_api_check = args.cmd == "api-sync" and args.check
    if not read_only_api_check:
        require_valid(user, roster, ok, errors)

    hub_tools_blocked_response(settings, args.cmd)

    mid = machine_id()
    base = {
        "uuid": user.get("uuid"),
        "name": user.get("name"),
        "machine_id": mid,
        "trust": trust,
    }
    if repo_id:
        base["repo_id"] = repo_id
    extra = {k: user[k] for k in ("role", "team", "organization") if user.get(k)}

    if args.cmd == "login":
        res = hub_call(hub_url, "POST", "/login", {**base, **extra})
        if hub_error_is_offline(res, settings):
            out({"offline": True, "error": res["error"], "hub_offline_ok": True})
        out(res)

    if args.cmd == "ping":
        res = hub_call(hub_url, "POST", "/ping", base)
        if hub_error_is_offline(res, settings):
            out({"offline": True, "error": res["error"], "hub_offline_ok": True})
        out(res)

    if args.cmd == "send":
        recipient = resolve_recipient(args.to, roster)
        if recipient is None:
            out({"error": f"recipient '{args.to}' is not a unique active project member"}, 1)
        from_actor = args.from_actor or default_actor
        git_root = find_git_root(cdase_root)
        boundary_warn = classify_message_body(args.body, git_root)
        if boundary_warn and from_actor == "agent" and not args.user_approved:
            out({"ok": False, "error": boundary_warn, "hint": "get user permission or pass --user-approved"}, 1)
        payload = {
            "from_uuid": user["uuid"],
            "to_uuid": recipient["uuid"],
            "from": user["name"],
            "to": recipient["name"],
            "body": args.body,
            "type": args.type,
            "subject": args.subject,
            "from_actor": from_actor,
            "intent": args.intent,
        }
        if args.thread_id:
            payload["thread_id"] = args.thread_id
        res = hub_call(hub_url, "POST", "/messages", payload)
        if hub_error_is_offline(res, settings):
            out({"offline": True, "error": res["error"], "hub_offline_ok": True})
        if boundary_warn:
            res["boundary_warning"] = boundary_warn
        out(res)

    if args.cmd == "send-file":
        recipient = resolve_recipient(args.to, roster)
        if recipient is None:
            out({"error": f"recipient '{args.to}' is not a unique active project member"}, 1)
        git_root = find_git_root(cdase_root)
        file_path, err = resolve_repo_path(args.path, cdase_root, git_root)
        if err:
            out({"ok": False, "error": err, "hint": "only files inside the git repository may be sent autonomously"}, 1)
        content, meta = read_repo_file(file_path, git_root)
        body = args.note.strip()
        if body:
            body += "\n\n---\n\n"
        body += content
        from_actor = args.from_actor or default_actor
        subject = args.subject or meta["repo_path"]
        payload = {
            "from_uuid": user["uuid"],
            "to_uuid": recipient["uuid"],
            "from": user["name"],
            "to": recipient["name"],
            "body": body,
            "type": "message",
            "subject": subject,
            "from_actor": from_actor,
            "intent": "file",
            "thread_id": args.thread_id,
        }
        if not payload["thread_id"]:
            del payload["thread_id"]
        res = hub_call(hub_url, "POST", "/messages", payload)
        if hub_error_is_offline(res, settings):
            out({"offline": True, "error": res["error"], "hub_offline_ok": True})
        res["file"] = meta
        out(res)

    if args.cmd == "inbox":
        res = fetch_inbox(hub_url, user, roster, keep=args.keep, all_msgs=args.all)
        if hub_error_is_offline(res, settings):
            out({"offline": True, "error": res["error"], "hub_offline_ok": True})
        out(res)

    if args.cmd == "kb-save":
        tags = [t.strip() for t in args.tags.split(",") if t.strip()]
        res = hub_call(hub_url, "POST", "/kb", {"key": args.key, "content": args.content,
                                                 "tags": tags, "author": user["name"]})
        if hub_error_is_offline(res, settings):
            out({"offline": True, "error": res["error"], "hub_offline_ok": True})
        out(res)

    if args.cmd == "kb-find":
        res = hub_call(hub_url, "GET", "/kb", params={"query": args.query})
        if hub_error_is_offline(res, settings):
            out({"offline": True, "error": res["error"], "hub_offline_ok": True})
        out(res)

    if args.cmd == "api-search":
        hub_tools_blocked_response(settings, "api-search")
        filters = {
            key: value
            for key, value in {
                "system": args.system,
                "module": args.module,
                "status": args.status,
                "kind": args.kind,
                "context_system": args.context_system,
                "context_module": args.context_module,
            }.items()
            if value
        }
        res = hub_call(
            hub_url,
            "POST",
            "/api-pool/search",
            {"query": args.query, "filters": filters, "limit": args.limit},
        )
        out(res, 1 if res.get("error") else 0)

    if args.cmd == "api-publish":
        hub_tools_blocked_response(settings, "api-publish")
        try:
            definition = json.loads(args.json)
        except json.JSONDecodeError as exc:
            out({"ok": False, "error": f"invalid JSON: {exc}"}, 1)
        token = os.environ.get("CDASE_KB_WRITE_TOKEN")
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        res = hub_call(
            hub_url,
            "POST",
            "/api-pool/apis",
            definition,
            headers=headers,
        )
        out(res, 1 if res.get("error") else 0)

    if args.cmd == "api-sync":
        hub_tools_blocked_response(settings, "api-sync")
        path, path_error = resolve_repo_path(args.path, cdase_root, git_root)
        if path_error:
            out({"ok": False, "error": path_error}, 1)
        text, meta = read_repo_file(path, git_root)
        try:
            definitions = parse_api_blocks(text)
        except ValueError as exc:
            out({"ok": False, "error": str(exc), "file": meta}, 1)
        if not definitions:
            out({
                "ok": False,
                "error": "no ```json cdase-api blocks found",
                "file": meta,
            }, 1)
        try:
            commit = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=git_root,
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
        except (OSError, subprocess.CalledProcessError):
            commit = None
        dirty = ""
        if commit:
            try:
                dirty = subprocess.run(
                    ["git", "status", "--porcelain", "--", meta["repo_path"]],
                    cwd=git_root,
                    capture_output=True,
                    text=True,
                    check=True,
                ).stdout.strip()
                if dirty and not args.check:
                    commit += "+dirty"
            except (OSError, subprocess.CalledProcessError):
                pass
        prepared = [
            with_source_revision(
                definition,
                path=meta["repo_path"],
                commit=commit,
            )
            for definition in definitions
        ]
        if args.check:
            verify_payload = {
                "apis": [
                    {
                        **definition,
                        "content_hash": content_hash(definition),
                    }
                    for definition in prepared
                ]
            }
            verified = hub_call(
                hub_url,
                "POST",
                "/api-pool/verify",
                verify_payload,
            )
            if verified.get("error") and not verified.get("states"):
                # Fallback for older hubs without /api-pool/verify
                states = []
                for definition in prepared:
                    remote = hub_call(
                        hub_url,
                        "GET",
                        "/api-pool/apis",
                        params={
                            "api_id": definition.get("api_id"),
                            "version": definition.get("version"),
                        },
                    )
                    state = sync_state(definition, remote, commit=commit)
                    if dirty and state["state"] == "SYNCED":
                        state["state"] = "STALE"
                        state["reasons"] = ["registry file has uncommitted changes"]
                    states.append(state)
                ok_states = all(item["state"] == "SYNCED" for item in states)
                out({
                    "ok": ok_states,
                    "mode": "check",
                    "verify_mode": "client",
                    "states": states,
                    "counts": {
                        state: sum(1 for item in states if item["state"] == state)
                        for state in ("SYNCED", "STALE", "MISSING", "CONFLICT")
                    },
                    "file": meta,
                }, 0 if ok_states else 1)
            states = list(verified.get("states") or [])
            if dirty:
                for state in states:
                    if state.get("state") == "SYNCED":
                        state["state"] = "STALE"
                        state["reasons"] = ["registry file has uncommitted changes"]
            counts = verified.get("counts") or {
                state: sum(1 for item in states if item.get("state") == state)
                for state in ("SYNCED", "STALE", "MISSING", "CONFLICT")
            }
            if dirty:
                counts = {
                    state: sum(1 for item in states if item.get("state") == state)
                    for state in ("SYNCED", "STALE", "MISSING", "CONFLICT")
                }
            ok_states = all(item.get("state") == "SYNCED" for item in states) and bool(states)
            out({
                "ok": ok_states,
                "mode": "check",
                "verify_mode": "hub",
                "states": states,
                "counts": counts,
                "file": meta,
            }, 0 if ok_states else 1)
        for definition in prepared:
            gate_error = legacy_publish_gate(
                definition,
                git_root=git_root,
                registry_repo_path=meta["repo_path"],
            )
            if gate_error:
                out({
                    "ok": False,
                    "error": gate_error,
                    "hint": "use legacy-api-upload for approved committed legacy imports",
                    "file": meta,
                }, 1)
        token = os.environ.get("CDASE_KB_WRITE_TOKEN")
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        results = []
        for index, definition in enumerate(prepared, start=1):
            result = hub_call(
                hub_url,
                "POST",
                "/api-pool/apis",
                definition,
                headers=headers,
            )
            results.append(result)
            if result.get("error"):
                out({
                    "ok": False,
                    "error": f"block {index} failed: {result['error']}",
                    "published": index - 1,
                    "results": results,
                    "file": meta,
                }, 1)
        out({
            "ok": True,
            "published": len(results),
            "results": results,
            "file": meta,
        })

    if args.cmd == "api-get":
        hub_tools_blocked_response(settings, "api-get")
        params = {"api_id": args.api_id}
        if args.version:
            params["version"] = args.version
        res = hub_call(hub_url, "GET", "/api-pool/apis", params=params)
        out(res, 1 if res.get("error") else 0)

    if args.cmd == "api-transition":
        hub_tools_blocked_response(settings, "api-transition")
        token = os.environ.get("CDASE_KB_WRITE_TOKEN")
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        payload = {
            "api_id": args.api_id,
            "version": args.version,
            "status": args.status,
            "actor": user.get("name"),
            "note": args.note,
            "superseded_by_version": args.superseded_by_version,
        }
        res = hub_call(
            hub_url,
            "POST",
            "/api-pool/transition",
            payload,
            headers=headers,
        )
        out(res, 1 if res.get("error") else 0)

    if args.cmd == "api-graph":
        hub_tools_blocked_response(settings, "api-graph")
        params = {"system": args.system} if args.system else None
        res = hub_call(hub_url, "GET", "/api-pool/graph", params=params)
        out(res, 1 if res.get("error") else 0)

    if args.cmd == "legacy-api-upload":
        hub_tools_blocked_response(settings, "legacy-api-upload")
        approval_path, path_error = resolve_repo_path(
            args.approval, cdase_root, git_root
        )
        if path_error:
            out({"ok": False, "error": path_error}, 1)
        try:
            approval = load_json(approval_path)
        except (OSError, json.JSONDecodeError) as exc:
            out({"ok": False, "error": f"invalid approval manifest: {exc}"}, 1)
        if approval.get("schema") != "cdase/legacy-api-approval/v1":
            out({"ok": False, "error": "invalid legacy API approval schema"}, 1)
        entries = approval.get("apis")
        if not isinstance(entries, list):
            out({"ok": False, "error": "approval manifest requires apis"}, 1)
        repo_paths = [str(approval_path.relative_to(git_root))]
        repo_paths.extend(str(item.get("registry")) for item in entries)
        for repo_path in repo_paths:
            file_path, error = resolve_repo_path(repo_path, cdase_root, git_root)
            if error:
                out({"ok": False, "error": error}, 1)
            tracked = subprocess.run(
                ["git", "ls-files", "--error-unmatch", "--", repo_path],
                cwd=git_root,
                capture_output=True,
                text=True,
            )
            dirty = subprocess.run(
                ["git", "status", "--porcelain", "--", repo_path],
                cwd=git_root,
                capture_output=True,
                text=True,
            )
            if tracked.returncode != 0 or dirty.stdout.strip():
                out({
                    "ok": False,
                    "error": "legacy upload requires committed approval and registry files",
                    "path": repo_path,
                }, 1)
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=git_root,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        token = os.environ.get("CDASE_KB_WRITE_TOKEN")
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        results = []
        for entry in entries:
            registry_path, error = resolve_repo_path(
                entry.get("registry"), cdase_root, git_root
            )
            if error:
                out({"ok": False, "error": error}, 1)
            try:
                local = find_api_definition(
                    registry_path,
                    entry.get("api_id"),
                    entry.get("version"),
                )
            except ValueError as exc:
                out({"ok": False, "error": str(exc)}, 1)
            if (
                local.get("origin") != "LEGACY_IMPORT"
                or local.get("scan_id") != approval.get("scan_id")
                or local.get("discovery_confidence") not in {"HIGH", "MEDIUM", "LOW"}
            ):
                out({
                    "ok": False,
                    "error": f"invalid legacy provenance for {entry.get('api_id')}",
                }, 1)
            local = with_source_revision(
                local,
                path=entry.get("registry"),
                commit=commit,
            )
            desired_status = local.get("status")
            remote = hub_call(
                hub_url,
                "GET",
                "/api-pool/apis",
                params={
                    "api_id": local.get("api_id"),
                    "version": local.get("version"),
                },
            )
            state = sync_state(local, remote, commit=commit)
            remote_api = remote.get("api") or {}
            if state["state"] == "CONFLICT":
                out({
                    "ok": False,
                    "error": f"API ownership conflict: {local.get('api_id')}",
                    "state": state,
                }, 1)
            if state["state"] == "SYNCED" and remote_api.get("status") == desired_status:
                results.append({"api_id": local["api_id"], "result": "already_synced"})
                continue
            if remote_api.get("status") in {
                "RELEASED", "SUPERSEDED", "DEPRECATED", "RETIRED"
            }:
                out({
                    "ok": False,
                    "error": f"immutable released API differs: {local.get('api_id')}",
                    "state": state,
                }, 1)
            publish = dict(local)
            publish["status"] = "DEVELOPING"
            published = hub_call(
                hub_url,
                "POST",
                "/api-pool/apis",
                publish,
                headers=headers,
            )
            if published.get("error"):
                out({"ok": False, "error": published["error"], "results": results}, 1)
            transition = None
            if desired_status == "RELEASED":
                transition = hub_call(
                    hub_url,
                    "POST",
                    "/api-pool/transition",
                    {
                        "api_id": local["api_id"],
                        "version": local["version"],
                        "status": "RELEASED",
                        "actor": user.get("name"),
                        "note": (
                            "Approved legacy import "
                            + str(approval.get("scan_id"))
                        ),
                    },
                    headers=headers,
                )
                if transition.get("error"):
                    out({
                        "ok": False,
                        "error": transition["error"],
                        "results": results,
                    }, 1)
            results.append({
                "api_id": local["api_id"],
                "published": published,
                "transition": transition,
            })
        out({
            "ok": True,
            "scan_id": approval.get("scan_id"),
            "uploaded": len(results),
            "results": results,
            "commit": commit,
        })

    if args.cmd == "watch":
        print(json.dumps({
            "watching": user["name"], "uuid": user["uuid"], "hub": hub_url,
            "interval": args.interval, "trust_count": len(trusted_uuids(roster)),
        }))
        while True:
            res = hub_call(hub_url, "POST", "/ping", base)
            unread = res.get("unread", 0)
            if res.get("error"):
                print(json.dumps({"ts": time.time(), "error": res["error"]}), flush=True)
            elif unread:
                print(
                    f"CDASE-NOTIFY: {unread} trusted unread message(s) for {user['name']}. "
                    "Run: cdase inbox",
                    flush=True,
                )
            time.sleep(args.interval)


if __name__ == "__main__":
    main()
