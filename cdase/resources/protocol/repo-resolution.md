# CDASE Repo Resolution

> All CDASE operations target **`<project-repo>/cdase/`** — never the workspace root
> when multiple repos exist, and **never the CDASE framework repo** (the methodology
> checkout that contains `cdase/SKILL.md`).

`<CDASE_CLIENT>` means installed `cdase` after `python -m pip install .`
(Windows: `py -m pip install .`), with the bundled
`python3 <skill-root>/scripts/cdase_client.py` fallback.

## Two different `cdase/` folders

| Location | What it is | Consumer runtime? |
|---|---|---|
| `<framework-repo>/cdase/SKILL.md` | CDASE skill package (methodology source) | **No** — do not bootstrap team artifacts here |
| `<app-repo>/cdase/context/` | Team runtime (members, requirements, run_log) | **Yes** — this is the SSOT for that project |

Detection: a repo with `cdase/SKILL.md` at its root is the **framework repo**.

## Step 0 — discover before you bootstrap

**Workspace** = the folder you opened in Cursor (e.g. `/user-2`). `discover` scans
**only inside that folder** — child git repos and the workspace itself if it is a repo.
It **never** walks up to parent folders (so a `cdase/` framework repo sitting beside
`/user-2` on disk is **not** listed).

Override explicitly if needed:

```bash
export CDASE_WORKSPACE=/path/to/user-2
<CDASE_CLIENT> discover
```

```bash
<CDASE_CLIENT> discover
```

Returns `scenario`, `repos`, `framework_repos`, `consumer_repos_with_cdase`,
`consumer_repos_without_cdase`, and `hint`. Run this **before** creating `cdase/` or
running `check` when the workspace layout is unclear.

Set the active runtime explicitly when needed:

```bash
export CDASE_ROOT=/path/to/app-repo/cdase
```

All client commands (`check`, `send`, `inbox`, …) use `CDASE_ROOT` when set.

## Workspace rules (agent MUST follow)

### 1. Workspace **is** a single git repo

| Condition | Action |
|---|---|
| Repo is **framework** (`cdase/SKILL.md` exists) | **Stop.** Tell user to open the **application** repo (or parent folder). Do **not** create consumer `cdase/` here. |
| Repo is **app**, has `cdase/context/` | Use `<repo>/cdase/` as `CDASE_ROOT`. Proceed. |
| Repo is **app**, no `cdase/context/` | After CDASE opt-in, create `<repo>/cdase/` from templates and **commit**. |

### 2. Workspace is a **parent folder** of repos

Scan child directories for git repos (`discover` does this).

| Scenario | Code | Action |
|---|---|---|
| **2a** No git repos found | `1_no_git` | Treat like step 1 only if workspace itself is git; else ask user to open a project repo. |
| **2b** Repos found, **none** have consumer `cdase/` | `2b_none_have_cdase` | **All or none.** Ask: apply CDASE to **all** application repos (same user), or **none**? On **all** → collect user profile once, init + commit `<app>/cdase/` in **every** non-framework repo with the same member record. On **none** → do not init any repo. Never framework. |
| **2c** **Some** have `cdase/`, some don't | `2c_mixed` | Show identities from repos that already have `cdase/`. Ask user to **confirm existing** or **enter new** profile. Then **all or none** for the repos still missing `cdase/`: init **all** missing repos with that same user, or init **none** of them. |
| All non-framework repos already have `cdase/` | `2_all_have_cdase` | Ask which repo to work in if ambiguous; set `CDASE_ROOT` accordingly. |

### 3. Bootstrap scope vs active work

**Bootstrap (initialization)** — when multiple application repos need `cdase/`:

* Ask the user: apply to **all** repos with the **same** user identity, or **none**.
* **All** → one profile collection, then init + commit `<repo>/cdase/` in every
  non-framework repo that needs it (same user id and profile defaults in each
  member record).
* **None** → do not create consumer `cdase/` anywhere; treat as CDASE OFF for init.

**Active engineering** — during a session, CDASE still operates on **one** repo at a time:

* Set `CDASE_ROOT=<app-repo>/cdase` for the repo you are working in now.
* Switch `CDASE_ROOT` when moving to another repo's task — never use workspace root.
* Never write team artifacts into the framework repo.

## Adoption vs maturity (orthogonal)

`discover` / `boot` / `legacy-classify` emit:

| Field | Values |
|---|---|
| `adoption_state` | `CDASE_UNINITIALIZED` \| `CDASE_INITIALIZED` |
| `codebase_state` | `GREENFIELD` \| `LEGACY` \| `PARTIAL_LEGACY` \| `MANAGED` |

Missing `cdase/context/` is **only** uninitialized. Legacy is inferred from first-party
production surfaces (excluding generated/vendor/build/fixture/test-only trees).

- `GREENFIELD` → init CDASE; do **not** scan
- `LEGACY` / `PARTIAL_LEGACY` → Legacy Onboarding ([legacy-scan.md](legacy-scan.md))
- `MANAGED` → Global API Pool for REUSE/EVOLVE/CREATE

## Bootstrap checklist (after user says CDASE ON)

1. `discover` → interpret `scenario` and each repo's maturity fields.
2. If `1_framework_only` → stop and redirect.
3. If **2b** (multiple app repos, none have cdase) → ask **all or none** (same user for all).
4. If **2c** (mixed) → confirm identity, then ask **all or none** for repos still missing cdase.
5. On **all**: collect profile once → for each target app repo: create `cdase/context/`,
   seed `context/members/<user-id>.context.md` with the same user, add
   `user.context.md` to `.gitignore`, **commit**.
6. Set `CDASE_ROOT=<app-repo>/cdase` for the repo you are working in now.
7. Run `check` first; use `boot` only to create missing identity/member/settings
   state, then re-run `check`.
8. Offer Legacy Onboarding only for `LEGACY` or `PARTIAL_LEGACY`. Do **not** scan `GREENFIELD`.

## Mixed workspace example

```
workspace/
├── cdase/          ← framework repo (SKILL.md) — skip
├── user_1/app-a/   ← has cdase/context/ — member: alice
└── user_2/app-b/   ← no cdase/ — needs init
```

Agent: show alice from app-a, ask confirm or new identity. Ask: init app-b (and any other
missing repos) with that same user, or none? If all → bootstrap app-b with
alice's committed member record.
For engineering, set `CDASE_ROOT` to whichever repo the user is working in.
