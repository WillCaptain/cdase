#!/usr/bin/env python3
"""CDASE Client — agent tool surface for the Hub.

SSOT layers:
  ~/.cursor/cdase/user.context.md     — global identity (Name, set once)
  ~/.cursor/cdase/setting.context.md  — global hub defaults
  /cdase/context/users.context.md     — repo roster (UUID SSOT, committed)
  /cdase/context/user.context.md      — optional repo identity override
  /cdase/context/setting.context.md   — optional repo settings override

Hub URL: env → repo setting → global setting → localhost default
UUID: resolved from repo roster by Name (unless explicit override/env)

Commands:
  check                       validate identity + print resolved settings
  login                       register uuid+name+machine on hub
  ping                        heartbeat; unread count from trusted senders only
  users                       list hub presence (informational only)
  send TO BODY                send to roster member (TO = name or uuid)
  send-file TO PATH           send repo file (--intent file); repo boundary enforced
  inbox [--all] [--keep]      trusted messages only
  kb-save / kb-find           knowledge base (optional cache)
  watch                       background notifier
  whoami                      resolved identity + settings
  input-spec PRESET           print a host-agnostic input spec for the agent to render
  apply-global-user           write collected identity to ~/.cursor/cdase/user.context.md

Input model (no CDASE-owned UI, no browser):
  CDASE emits a declarative input spec (input-spec PRESET). The AGENT renders it with
  the host's native input UI (Cursor: the multiple-choice / question card) and demotes
  to plain text when the host has none. The agent then applies the result
  (e.g. apply-global-user). Presets: session.gate, user.profile.
"""
import argparse
import json
import os
import sys
import time
import uuid as uuid_lib
import platform
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from cdase_runtime import find_cdase_root
from context_loader import (
    load_roster,
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
from input_specs import (
    resolve_input_spec,
    write_global_user_profile,
)


def machine_id() -> str:
    return os.environ.get("CDASE_MACHINE_ID") or f"{platform.node()}-{uuid_lib.getnode():x}"


def hub_call(hub_url: str, method, path, payload=None, params=None):
    url = hub_url + path
    if params:
        from urllib.parse import urlencode
        url += "?" + urlencode(params)
    data = json.dumps(payload).encode() if payload is not None else None
    req = Request(url, data=data, method=method,
                  headers={"Content-Type": "application/json"})
    try:
        with urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except HTTPError as e:
        try:
            return json.loads(e.read())
        except Exception:
            return {"error": f"HTTP {e.code}"}
    except URLError as e:
        return {
            "error": f"hub unreachable at {hub_url} ({e.reason}). "
                     f"Check setting.context.md Hub.Address or deploy: "
                     f"cd hub && mvn -q package && java -jar target/cdase-hub-1.0.0.jar",
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
    roster = load_roster(cdase_root)
    ok, errors = validate_identity(user, roster)
    client_script = resolve_client_script(settings, SCRIPT_DIR)
    return user, roster, ok, errors, cdase_root, settings, hub_url, client_script


def require_valid(user, roster, ok, errors):
    if not ok:
        out({"ok": False, "errors": errors}, 1)


def hub_error_is_offline(res: dict, settings: dict) -> bool:
    return bool(res.get("error")) and settings.get("hub_offline_ok", True)


def main():
    p = argparse.ArgumentParser(description="CDASE Hub client")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("check", help="validate identity vs repo roster (SSOT check)")
    sub.add_parser("login")
    sub.add_parser("ping")
    sub.add_parser("users")
    sub.add_parser("whoami")

    sp = sub.add_parser("input-spec", help="print a host-agnostic input spec (agent renders it natively)")
    sp.add_argument("preset", choices=["user-profile", "session-gate"], help="input preset id")

    sp = sub.add_parser("apply-global-user")
    sp.add_argument("--json", required=True, help='JSON object of field values, e.g. {"Name":"will"}')

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

    sp = sub.add_parser("watch")
    sp.add_argument("--interval", type=int, default=60)

    args = p.parse_args()
    user, roster, ok, errors, cdase_root, settings, hub_url, client_script = load_context()
    trust = trust_csv(roster)
    default_actor = settings.get("messaging_from_actor", "agent")

    if args.cmd == "check":
        health = hub_call(hub_url, "GET", "/health")
        out({
            "ok": ok,
            "identity": {
                "name": user.get("name"),
                "uuid": user.get("uuid"),
                "source": user.get("identity_source"),
                "uuid_from_roster": user.get("uuid_from_roster", False),
            },
            "roster_size": len(roster),
            "trusted_uuids": trusted_uuids(roster),
            "roster": roster,
            "settings": {
                "hub_address": hub_url,
                "hub_offline_ok": settings.get("hub_offline_ok"),
                "client_path": str(client_script),
                "messaging_from_actor": default_actor,
                "agent_autonomy": settings.get("agent_autonomy"),
                "auto_reply_to_agent_questions": settings.get("auto_reply_to_agent_questions"),
                "source": settings.get("source"),
                "global_dir": settings.get("global_dir"),
                "cdase_root": str(cdase_root),
            },
            "hub_health": health if not health.get("error") else {"error": health["error"]},
            "errors": errors,
        }, 0 if ok else 1)

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
            "roster_size": len(roster),
            "identity_valid": ok,
            "errors": errors if not ok else [],
        })

    if args.cmd == "input-spec":
        preset_map = {"user-profile": "user.profile", "session-gate": "session.gate"}
        preset_id = preset_map.get(args.preset, args.preset.replace("-", "."))
        initial = None
        if preset_id == "user.profile":
            initial = {k: user.get(k.lower()) for k in ("Name", "Role", "Team", "Organization")
                       if user.get(k.lower())}
        spec = resolve_input_spec(preset_id, initial=initial)
        if preset_id == "user.profile":
            spec["apply_command"] = f"python3 {client_script} apply-global-user --json '<values>'"
        out(spec)

    if args.cmd == "apply-global-user":
        try:
            values = json.loads(args.json)
        except json.JSONDecodeError as e:
            out({"ok": False, "error": f"invalid JSON: {e}"}, 1)
        if not values.get("Name"):
            out({"ok": False, "error": "Name is required"}, 1)
        path = write_global_user_profile(values)
        out({"ok": True, "path": str(path), "values": values})

    if args.cmd == "users":
        res = hub_call(hub_url, "GET", "/users")
        if hub_error_is_offline(res, settings):
            out({"offline": True, "error": res["error"], "hub_offline_ok": True})
        out(res)

    require_valid(user, roster, ok, errors)

    mid = machine_id()
    base = {
        "uuid": user["uuid"],
        "name": user["name"],
        "machine_id": mid,
        "trust": trust,
    }
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
            out({"error": f"recipient '{args.to}' not in repo roster (context/users.context.md)"}, 1)
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
            out({"error": f"recipient '{args.to}' not in repo roster (context/users.context.md)"}, 1)
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
        res = hub_call(hub_url, "GET", "/messages", params={
            "uuid": user["uuid"],
            "trust": trust,
            "all": "1" if args.all else "0",
        })
        if hub_error_is_offline(res, settings):
            out({"offline": True, "error": res["error"], "hub_offline_ok": True})
        msgs = res.get("messages", [])
        unread_ids = [m["id"] for m in msgs if not m.get("read")]
        if unread_ids and not args.keep:
            hub_call(hub_url, "POST", "/messages/ack", {"uuid": user["uuid"], "ids": unread_ids})
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

    if args.cmd == "watch":
        print(json.dumps({
            "watching": user["name"], "uuid": user["uuid"], "hub": hub_url,
            "interval": args.interval, "trust_count": len(roster),
        }))
        while True:
            res = hub_call(hub_url, "POST", "/ping", base)
            unread = res.get("unread", 0)
            if res.get("error"):
                print(json.dumps({"ts": time.time(), "error": res["error"]}), flush=True)
            elif unread:
                print(
                    f"CDASE-NOTIFY: {unread} trusted unread message(s) for {user['name']}. "
                    f"Run: python3 {client_script} inbox",
                    flush=True,
                )
            time.sleep(args.interval)


if __name__ == "__main__":
    main()
