# CDASE Session Gate

> **Agent-neutral**. Applies to any code agent.
> CDASE is never assumed — the user must opt in when the work is software-related.

`<CDASE_CLIENT>` means installed `cdase` after `python -m pip install .`
(Windows: `py -m pip install .`), with the bundled
`python3 <skill-root>/scripts/cdase_client.py` fallback.
`<GLOBAL_CDASE>` means `CDASE_GLOBAL` when set, else `~/.cdase` on
macOS/Linux or `%USERPROFILE%\.cdase` on Windows.

## When to ask (not every chat)

Do **not** open with “Apply CDASE?” on every session.

Ask **Apply CDASE in this session? (yes / no)** only when the user has not already
declared on/off this session, **and** at least one of:

1. **Workspace is a software project** — git repo / source tree / consumer `cdase/` /
   build manifests (`package.json`, `pom.xml`, `Cargo.toml`, `go.mod`, …), or the user
   is joining a code project (“I'm joining the project”).
2. **The question is strongly code-related** — implement, debug, PR, build, test,
   refactor, deploy, project membership, etc.

**Never ask** for clearly non-software work (paper, essay, prose writing, casual chat
with no code context). Be a normal assistant. User may say `cdase on` anytime.

If unsure whether it is code work: **do not ask**; answer normally.

When you ask: run `input-spec session-gate`, then follow the **generic render order**
([protocol/input.md](protocol/input.md)): host choice UI first, plain “yes / no” only if
the host has none. **Stop and wait**. Do not run CDASE tools until they reply.

## No consumer `cdase/` in the target repo → confirmation is MANDATORY (code work only)

**First:** resolve which git repo is the target — not the workspace root, and **not**
the CDASE framework repo (`cdase/SKILL.md` at repo root). Run `discover` when unsure
([protocol/repo-resolution.md](protocol/repo-resolution.md)).

If the **application** repo has **no `cdase/context/`**, and this is code/project work:

- Do **not** silently init. State which repo you detected (or ask if multiple), note
  missing consumer `cdase/`, ask **"Apply CDASE in this session? (yes / no)"** and **stop**.
- On **yes**: `discover` → if multiple app repos need init (**2b**), ask **all repos
  (same user) or none**. Init + commit every non-framework repo on **all**.
- On **no**: normal assistant; do not create consumer `cdase/`.

If workspace is only the **framework** repo, tell the user to open the application project
— do **not** nest another `cdase/` under the framework.

## One-time global setup (not per session)

On first `cdase on`, if `<GLOBAL_CDASE>/user.context.md` is missing, use the
**host-native input flow** — see [protocol/input.md](protocol/input.md):

1. `<CDASE_CLIENT> input-spec user-profile` → global profile (scope implied).
2. Collect values; agent runs `apply-global-user --json '...'`.
3. `boot` writes this machine to
   `context/members/<8-hex-user-id>.context.md`; commit that record before trust.
4. Do **not** invent a random UUID; do not create repo `user.context.md` unless overriding.

### Later: set or update identity (global **or** this repo)

When the user asks to add/change profile and does not say where, ask scope first:

```
<CDASE_CLIENT> input-spec user-scope
```

| Choice | Next |
|--------|------|
| global | `user-profile` → `apply-global-user` |
| this repo | `user-profile-repo` → `apply-repo-user` |

Repo override is gitignored and controls only the current user's Alias/Role.
`boot` writes it into that user's shared member record; commit the record before trust.

If `<GLOBAL_CDASE>/setting.context.md` is missing, **copy** the skill template
`cdase/resources/templates/setting.context.md` there (`boot` or `init-global-setting`).
Default Address is `https://12th.ai/cdase`. Ask `input-spec hub-address` only when the
user wants a different hub. Until a global/repo setting exists, **do not** invoke
sync, team, send, or inbox.

## Zero-to-start journey (after opt-in)

```
<CDASE_CLIENT> discover
<CDASE_CLIENT> check
```

Load the Constitution, discover the application repo, and run `check` first.
Run `boot` only when `check` reports missing state. After identity and an
explicit Hub URL are valid, run `sync` before every user answer. Run `team`
when the user asks to list users.

After boot/`legacy-classify`, treat adoption and maturity as orthogonal:

| `codebase_state` | Agent action |
|---|---|
| `GREENFIELD` | Initialize CDASE normally — do **not** run a legacy scan |
| `LEGACY` / `PARTIAL_LEGACY` | Offer **Legacy Onboarding** (isolated `legacy-scan-spec`) before Feature/Function work |
| `MANAGED` | Proceed with Global API Pool REUSE/EVOLVE/CREATE |

Missing `cdase/context/` is only `CDASE_UNINITIALIZED`. See
[protocol/legacy-scan.md](protocol/legacy-scan.md) and charter §5–§6.

## Interpreting the answer

| User says / choice | Session mode |
|---|---|
| yes, y, cdase, cdase on | **CDASE ON** — load [SKILL.md](../SKILL.md), run [charter boot](charter.md) |
| no, n, skip, cdase off | **CDASE OFF** — normal assistant |

## While the session runs

- **CDASE ON**: Read [../SKILL.md](../SKILL.md), then [charter.md](charter.md).
  Discover the app repo and run `check` first; use `boot` only to create missing
  state. Once identity and
  explicit Hub URL are valid, run `sync` for presence + messages and show
  `hub_warning` if the Hub is down.
- **CDASE OFF**: Do not load CDASE unless user says `cdase on`.
- Toggle: `cdase on` / `cdase off`.

Team / online questions → run `team` (hub `GET /users`); never local files or git alone.
