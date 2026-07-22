---
name: cdase
description: >-
  Context-Driven AI Software Engineering (CDASE) — document-governed methodology
  where the repository is the system and the AI is the executor. Load when user
  opts in (yes / cdase on). Covers scenarios, features, functions, stage gates,
  HARD STOPs, and Hub collaboration.
---

# CDASE

> **Agent-neutral.** Not tied to Cursor or any IDE.
> **Activation**: [resources/session-gate.md](resources/session-gate.md) — user must opt in.

You are the **engineering execution system** of a document-governed repository.

## Boot (lean — reach the user fast)

`<GLOBAL_CDASE>` means `CDASE_GLOBAL` when set, otherwise `~/.cdase` on
macOS/Linux or `%USERPROFILE%\.cdase` on Windows. `<CDASE_CLIENT>` means the
installed `cdase` command (`python -m pip install .`; Windows:
`py -m pip install .`), with `python3 <skill-root>/scripts/cdase_client.py`
as the bundled fallback.

**Zero-to-start journey** (user says "I'm joining the project"):

| Step | Agent |
|------|-------|
| 1 | Code/repo workspace **or** strongly code-related question | `input-spec session-gate` → host choice UI first, text fallback (any agent). Stop. Skip ask for papers / non-code work. |
| 2 | `input-spec user-profile` → `apply-global-user`. `boot` publishes this machine to `context/members/<user-id>.context.md`. |
| 3 | Missing `<GLOBAL_CDASE>/setting.context.md` → `boot` / `init-global-setting` copies the settings template (default `https://12th.ai/cdase`). Custom URL only if user asks. |
| 4 | `sync` — activate on hub + retrieve messages |
| 5–6 | Still no URL → **no** sync/team/send/inbox until setting exists |
| 7 | User asks to list users → `team` |

Progress: `<CDASE_CLIENT> check`; run `<CDASE_CLIENT> boot` only to create missing state.

1. [resources/session-gate.md](resources/session-gate.md) — ask "Apply CDASE?" and **stop** for the answer.
   - Run `discover` when workspace layout is unclear ([protocol/repo-resolution.md](resources/protocol/repo-resolution.md)).
   - **Never** bootstrap consumer `cdase/` in the framework repo (`cdase/SKILL.md`).
   - If no consumer `cdase/context/` in the **app** repo, opt-in is mandatory before any task.
2. On **yes**: read [resources/constitution.md](resources/constitution.md) + [resources/charter.md](resources/charter.md).
   - `discover` → select application repo(s). **2b**: all repos (same user) or none.
     **2c**: confirm identity, then all-or-none for missing repos. Set `CDASE_ROOT` for active work.
   - Run `check` first. Use `boot` only when `check` reports missing state.
3. On **every user question** in CDASE mode (after hub URL is set), run **sync** before answering:
   ```
   <CDASE_CLIENT> sync
   ```
   Hub health + **inbox** (messages). Show `hub_warning` if hub is down.
4. Validate with **`check`** (identity + Hub URL state + next step).
   * `ok: false` with missing global user → `input-spec user-profile`, then `apply-global-user`.
   * `hub_tools_blocked` → run `boot` / `init-global-setting` (copies template). Ask `hub-address` only for a non-default hub.
   * `unread_count > 0` from sync → show messages before answering.

**Hub model:** active committed `context/members/*.context.md` records are the
membership/trust authority. Hub stores presence/messages as a superset and
gateways the Global API Pool discovery index.

**Identity:** **machine = user**. Member/Hub id = `sha256(machine_id)[:8]`.
Global profile supplies the default Alias/Role. Optional gitignored repo
`user.context.md` overrides Alias/Role; `boot` publishes it to the member record.

> Do not open the per-file context docs individually at boot — `check` / `boot` already read them.
> Consumer runtime = `<app-repo>/cdase/` (with `context/`). Skill package = `SKILL.md` + `resources/` + `scripts/` in the framework repo — not the runtime.

## Config layers

```
<GLOBAL_CDASE>/               ← global (all agents on this machine)
  user.context.md             default Alias/Role when joining a repo
  setting.context.md          hub Address (seeded from skill template)

my-app/cdase/context/         ← this repo (team)
  members/
    <8-hex-user-id>.context.md
                              User ID | Alias | Role | Status (committed trust SSOT)
  setting.context.md          optional overrides (committed)
  user.context.md             optional current-user Alias/Role override (gitignored)
```

Settings precedence is **defaults → global → repo → environment**.
Aliases are display-only. Steward and Owner references use
`user-id (project-alias)`; duplicate aliases require the id.

## Requirement artifact layout

```
my-app/cdase/requirements/
  index.md
  SCN-XXX/
    scenario.md
    FTR-YY/
      feature.md
      design.md                mandatory; contains every Feature diagram
      code-plan.md
      gates.md                 gate criteria + evidence only
      progress.md              mutable execution state SSOT
      FUN-ZZ/
        function.md
        design.md              conditional; all Function diagrams when present
        code-plan.md
        gates.md
        progress.md
```

Full IDs stay in document metadata (`FTR-XXX-YY`, `FUN-XXX-YY-ZZ`); folders use
local suffixes. Acceptance Criteria stay in `feature.md` / `function.md`.
Never duplicate Stage, Status, Owner, timestamps, or blockers outside
`progress.md`, and never duplicate gate checklists outside `gates.md`.

## Global API Pool (mandatory anti-duplication gate)

Before resolving or creating a Function:

1. `api-search "<capability + inputs + outputs + side effects>"`.
2. Verify candidate contracts in their source-linked repositories.
3. Record candidates/scores and resolve REUSE | EVOLVE | CREATE in `gates.md`.
4. CREATE/EVOLVE → add/update a `cdase-api` block in the owning
   `/cdase/api/modules/*.api.md`, then `api-sync` it as `DEVELOPING`.
5. Acceptance → transition delivered version to `RELEASED`; mark replaced
   versions `SUPERSEDED`.

Repository registry is contract authority. Hub Global API Pool is discovery
authority. Clients know only the Hub Address; the Hub server chooses direct
relational or legacy HTTP knowledge storage.

## Legacy API onboarding

Run `legacy-classify`; do not equate missing CDASE context with legacy code.
Only `LEGACY` and `PARTIAL_LEGACY` enter onboarding:

1. `legacy-scan-spec` emits deterministic evidence and a fresh-session job.
2. Delegate that job to a new isolated, read-only agent/session. The parent
   MUST NOT perform the scan.
3. `legacy-scan-save --json '<report>'` validates and stores the result.
4. `legacy-approval-spec --report <report>` MUST be rendered with host-native
   multi-select first; user chooses any HIGH/MEDIUM/LOW candidates.
5. `legacy-api-apply` writes only selected contracts and an approval manifest.
6. After those files are committed, `legacy-api-upload --approval <manifest>`
   publishes `DEVELOPING` and transitions approved imports to `RELEASED`.
7. `api-sync <registry> --check` verifies `SYNCED | STALE | MISSING | CONFLICT`.

`LEGACY_IMPORT` is provenance, not lifecycle. See
[resources/protocol/legacy-scan.md](resources/protocol/legacy-scan.md).

## Standard skill layout

```
SKILL.md
scripts/cdase_client.py
resources/
```

Hub **server** is deployed separately. See [resources/reference.md](resources/reference.md).
