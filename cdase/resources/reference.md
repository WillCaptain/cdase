# CDASE Reference — Hub & Messaging

> Hub **server** is deployed separately. Hub **client** ships with this skill (`scripts/`).

## Config layers

| Layer | Path | Scope |
|---|---|---|
| Global user | `~/.cdase/user.context.md` | Name, preferences — **set once** |
| Global settings | `~/.cdase/setting.context.md` | Default hub address |
| Repo roster | `/cdase/context/users.context.md` | Trust circle + **UUID SSOT** |
| Repo settings | `/cdase/context/setting.context.md` | Optional per-project overrides |
| Repo user override | `/cdase/context/user.context.md` | Optional different identity |

Override `~/.cdase` with env `CDASE_GLOBAL`. Windows: `%USERPROFILE%\.cdase`.
Legacy `~/.cursor/cdase` is migrated into `~/.cdase` (missing files only; never overwrite).

### Settings resolution

```
env (CDASE_HUB_URL, …) → repo setting.context.md → global setting.context.md → defaults
```

| Section | Field | Purpose |
|---|---|---|
| Hub | Address | Deployed hub URL |
| Hub | OfflineOk | Continue if hub unreachable |
| Client | Path | `auto` or path to `cdase_client.py` |
| Messaging | FromActor | Default `human` or `agent` |
| Messaging | AgentAutonomy | `delegated` \| `blocked` \| `none` |
| Messaging | AutoReplyToAgentQuestions | Auto-answer peer agent questions |

Templates: [setting.context.md](templates/setting.context.md) (global — copy to `~/.cdase/`),
[setting.md](templates/setting.md) (repo overrides),
[setting.global.md](templates/setting.global.md) (legacy pointer)

Protocol: [protocol/agent-messaging.md](protocol/agent-messaging.md)

### Identity resolution

```
1. Global user.context.md (Name)
2. Optional repo user.context.md override
3. env CDASE_USER / CDASE_UUID
4. UUID from repo users.context.md by Name match
```

Templates: [user.global.md](templates/user.global.md), [user.md](templates/user.md) (override only)

**Switching repos:** same global Name; validate against new roster. Prompt only if Name missing from roster.

## Hub tools

```bash
python3 scripts/cdase_client.py discover   # find app repos + cdase/ runtimes (run first)
python3 scripts/cdase_client.py team        # roster + hub online/offline — NOT git history
python3 scripts/cdase_client.py check
python3 scripts/cdase_client.py login       # explicit register (optional — hub tools auto-refresh)
python3 scripts/cdase_client.py ping        # explicit heartbeat (optional — hub tools auto-refresh)
python3 scripts/cdase_client.py inbox
python3 scripts/cdase_client.py send <to> "<body>" [--intent question] [--thread-id FUN-xxx]
python3 scripts/cdase_client.py send-file <to> <repo-path> [--thread-id FUN-xxx]
```

`discover` classifies the workspace (`1_framework_only`, `2b_none_have_cdase`, `2c_mixed`, …).
For `2b`/`2c`, `bootstrap_policy` is `all_or_none` — init every app repo with the same user, or none.
Never bootstrap consumer `cdase/` in the framework repo (`cdase/SKILL.md`).

`check` prints `identity.source`, `settings.source`, `hub_address`, `workspace.scenario`, roster match, `hub_presence`, and **`hub_warning`** when the hub is down (agent must show it in CDASE mode).

**Hub presence:** `check`, `team`, `send`, `inbox`, and other hub commands automatically ping or login so teammates see you online — no separate heartbeat step.

Set `CDASE_ROOT=<app-repo>/cdase` when multiple consumer repos exist. See [protocol/repo-resolution.md](protocol/repo-resolution.md).

### Team discovery

```bash
python3 scripts/cdase_client.py team
```

Merges `users.context.md` (roster SSOT) with hub presence. **Do not** use git log for team names.
See [protocol/agent-messaging.md](protocol/agent-messaging.md) § Team discovery.

## Deploy hub server

```bash
cd <methodology-repo>/hub
mvn -q package
java -jar target/cdase-hub-1.0.0.jar
```

Set global `Hub.Address` once; repo override only for projects on a different hub.

## SSOT trust model

| Path | Role |
|---|---|
| `~/.cdase/user.context.md` | Who I am (global; all agents) |
| `/cdase/context/users.context.md` | Who I trust + UUIDs (repo) |
| `~/.cdase/setting.context.md` | Default hub |
| `/cdase/context/setting.context.md` | Repo hub override |

Roster UUIDs: **8 hex chars** — `python3 -c "import secrets; print(secrets.token_hex(4))"`

## Message checkpoints

1. Session boot (after `check`; hub presence refreshes automatically)
2. Before HARD STOP
3. After Post-Delivery Sync
4. Task discovery

## Messaging protocol

- `@someone` → resolve against `users.context.md`, `from_actor: human`
- Agent peer messages → `--from-actor agent --intent question|answer|file …`
- Repo files → `send-file` (boundary enforced)
- Out-of-repo → user permission + `--user-approved`
- Never invent recipients outside roster

See [protocol/agent-messaging.md](protocol/agent-messaging.md).

## User input (host-native, text fallback)

CDASE emits a declarative input spec; the **agent** renders it with the host's native
input UI (Cursor: multiple-choice / question card) or plain text. No CDASE UI, no browser.

```bash
python3 scripts/cdase_client.py input-spec session-gate
python3 scripts/cdase_client.py input-spec user-profile
python3 scripts/cdase_client.py apply-global-user --json '{"Name":"will","Role":"architect"}'
```

See [protocol/input.md](protocol/input.md).
