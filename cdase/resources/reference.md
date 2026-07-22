# CDASE Reference — Hub & Messaging

> Hub **server** is deployed separately. Hub **client** ships with this skill (`scripts/`).

`<GLOBAL_CDASE>` means `CDASE_GLOBAL` when set, else `~/.cdase` on macOS/Linux
or `%USERPROFILE%\.cdase` on Windows.

Install the portable client from the methodology checkout with
`python -m pip install .` (Windows: `py -m pip install .`). `<CDASE_CLIENT>`
means the installed `cdase` command, falling back to
`python3 <skill-root>/scripts/cdase_client.py` (Windows:
`py <skill-root>\scripts\cdase_client.py`) when it is not installed.

## Config layers

| Layer | Path | Scope |
|---|---|---|
| Global user | `<GLOBAL_CDASE>/user.context.md` | Default Alias/Role, preferences |
| Global settings | `<GLOBAL_CDASE>/setting.context.md` | Default hub address |
| Repo members | `/cdase/context/members/<8-hex-user-id>.context.md` | Membership/trust authority |
| Repo settings | `/cdase/context/setting.context.md` | Optional per-project overrides |
| Repo user override | `/cdase/context/user.context.md` | Optional current-user Alias/Role override; gitignored |

### Settings resolution

```
defaults → global setting.context.md → repo setting.context.md → environment
```

| Section | Field | Purpose |
|---|---|---|
| Hub | Address | Deployed hub URL |
| Hub | OfflineOk | Continue if hub unreachable |
| Client | Path | `auto` or path to `cdase_client.py` |
| Messaging | FromActor | Default `human` or `agent` |
| Messaging | AgentAutonomy | `delegated` \| `blocked` \| `none` |
| Messaging | AutoReplyToAgentQuestions | Auto-answer peer agent questions |

Templates: [setting.context.md](templates/setting.context.md) (global — copy to `<GLOBAL_CDASE>/`),
[setting.md](templates/setting.md) (repo overrides).

Protocol: [protocol/agent-messaging.md](protocol/agent-messaging.md)

### Identity resolution

```
1. Derive user id as sha256(machine_id)[:8]
2. Load global user.context.md (default Alias/Role)
3. Resolve this id in context/members/<user-id>.context.md (shared project identity)
4. Apply optional repo user.context.md Alias/Role override for the current user
5. On boot, write the resolved Alias/Role into the shared member record; commit it
   before it grants trust
```

Templates: [user.global.md](templates/user.global.md), [user.md](templates/user.md) (override only)

Only active member records grant trust. Aliases are display-only and may repeat;
assignments use `user-id (project-alias)`. There is no `users.context.md`
compatibility.

## Hub tools

```bash
<CDASE_CLIENT> discover   # find app repos + cdase/ runtimes (run first)
<CDASE_CLIENT> team       # members + Hub presence — NOT git history
<CDASE_CLIENT> check      # identity/settings + Hub health; no presence mutation
<CDASE_CLIENT> sync       # presence refresh + trusted/unknown inbox
<CDASE_CLIENT> login      # legacy explicit register
<CDASE_CLIENT> ping       # legacy explicit heartbeat
<CDASE_CLIENT> inbox
<CDASE_CLIENT> send <to> "<body>" [--intent question] [--thread-id FUN-xxx]
<CDASE_CLIENT> send-file <to> <repo-path> [--thread-id FUN-xxx]
```

`discover` classifies the workspace (`1_framework_only`, `2b_none_have_cdase`, `2c_mixed`, …).
For `2b`/`2c`, `bootstrap_policy` is `all_or_none` — init every app repo with the same user, or none.
Never bootstrap consumer `cdase/` in the framework repo (`cdase/SKILL.md`).

`check` prints identity/settings/workspace state, Hub health, and **`hub_warning`**
when the Hub is down. It does not register presence.

**Hub presence:** `sync` and `team` automatically ping or login so teammates see
you online. The normal journey does not require explicit `login` or `ping`.

Set `CDASE_ROOT=<app-repo>/cdase` when multiple consumer repos exist. See [protocol/repo-resolution.md](protocol/repo-resolution.md).

## Global API Pool

The client always uses `Hub.Address`. Knowledge storage is configured only on
the Hub:

```
client → Hub → embedded/JDBC/legacy-HTTP provider
```

No knowledge-database URL belongs in global or repo `setting.context.md`.

```bash
<CDASE_CLIENT> api-search "create payable invoice" \
  --context-system billing --context-module checkout
<CDASE_CLIENT> api-sync cdase/api/modules/invoice.api.md
<CDASE_CLIENT> api-get organization/system/module/operation --version v1
<CDASE_CLIENT> api-transition <api-id> v1 RELEASED
<CDASE_CLIENT> api-graph --system billing
```

`api-sync` publishes every `cdase-api` JSON fenced block and supplies its
repo-relative source path/revision. Writes require `CDASE_KB_WRITE_TOKEN` in the
invoking environment; this is authorization, not backend location.

API lifecycle: `DEVELOPING → RELEASED → SUPERSEDED | DEPRECATED | RETIRED`.
Released contracts are immutable; upgrades create a new version.
Context system/module are soft graph reranking signals; search remains global.

### Legacy API onboarding

```bash
<CDASE_CLIENT> legacy-classify
<CDASE_CLIENT> legacy-scan-spec
# Delegate job.prompt to a fresh isolated read-only session.
<CDASE_CLIENT> legacy-scan-save --json '<strict scan JSON>'
<CDASE_CLIENT> legacy-approval-spec \
  --report cdase/run_log/<scan-id>.json
<CDASE_CLIENT> legacy-api-apply \
  --report cdase/run_log/<scan-id>.json \
  --selection-json '{"selected":["candidate-id"]}'
# Commit approval + generated registry files first.
<CDASE_CLIENT> legacy-api-upload \
  --approval cdase/run_log/legacy_api_approval_<scan-id>.json
<CDASE_CLIENT> api-sync cdase/api/modules/<module>.api.md --check
```

`legacy-approval-spec` is a `multi_choice` input: use host-native multi-select
first. HIGH candidates are defaults, but the user may select any HIGH, MEDIUM,
or LOW candidates. `LEGACY_IMPORT` provenance is stored relationally and does
not affect the semantic content hash.

`api-sync --check` calls Hub `POST /api-pool/verify` and returns
`SYNCED | STALE | MISSING | CONFLICT`. Ordinary `api-sync` rejects unapproved or
uncommitted `LEGACY_IMPORT` blocks; use `legacy-api-upload` after commit.

### Team discovery

```bash
<CDASE_CLIENT> team
```

Merges active committed member records with Hub presence. **Do not** use git log
for team identity.
See [protocol/agent-messaging.md](protocol/agent-messaging.md) § Team discovery.

## Deploy hub server

```bash
cd <methodology-repo>/hub
mvn -q package
java -jar target/cdase-hub-1.1.0.jar
```

Set global `Hub.Address` once; repo override only for projects on a different hub.

## SSOT trust model

| Path | Role |
|---|---|
| `<GLOBAL_CDASE>/user.context.md` | Global profile defaults |
| `/cdase/context/members/<user-id>.context.md` | Active membership/trust authority |
| `<GLOBAL_CDASE>/setting.context.md` | Default hub |
| `/cdase/context/setting.context.md` | Repo hub override |

Member IDs are stable **8 lowercase hex** machine-user IDs:
`sha256(machine_id)[:8]`. Never generate them randomly.

## Message checkpoints

1. Session boot (`sync` after identity and Hub URL validation)
2. Before HARD STOP
3. After Post-Delivery Sync
4. Task discovery

## Messaging protocol

- `@someone` → resolve against active member records, `from_actor: human`;
  duplicate aliases require an id
- Agent peer messages → `--from-actor agent --intent question|answer|file …`
- Repo files → `send-file` (boundary enforced)
- Out-of-repo → user permission + `--user-approved`
- Never invent recipients outside active committed membership

See [protocol/agent-messaging.md](protocol/agent-messaging.md).

## User input (host-native, text fallback)

CDASE emits a declarative input spec; the **agent** renders it with the host's native
input UI (host-specific) or plain text. Same generic order on every agent. No CDASE UI, no browser.

```bash
<CDASE_CLIENT> input-spec session-gate
<CDASE_CLIENT> input-spec user-profile
<CDASE_CLIENT> apply-global-user --json '{"Name":"will","Role":"architect"}'
```

See [protocol/input.md](protocol/input.md).
