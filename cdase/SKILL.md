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

**Zero-to-start journey** (user says "I'm joining the project"):

| Step | Agent |
|------|-------|
| 1 | Code/repo workspace **or** strongly code-related question | Ask "Apply CDASE?" — **stop**. Skip ask for papers / non-code work. |
| 2 | `input-spec user-profile` → `apply-global-user` (Name). `boot` registers **this machine** on `users.context.md` (machine = user id). |
| 3 | Missing `~/.cdase/setting.context.md` → `boot` / `init-global-setting` copies skill `templates/setting.context.md` (default `https://12th.ai/cdase`). Custom URL only if user asks. |
| 4 | `sync` — activate on hub + retrieve messages |
| 5–6 | Still no URL → **no** sync/team/send/inbox until setting exists |
| 7 | User asks to list users → `team` |

Progress: `python3 scripts/cdase_client.py boot`

1. [resources/session-gate.md](resources/session-gate.md) — ask "Apply CDASE?" and **stop** for the answer.
   - Run `discover` when workspace layout is unclear ([protocol/repo-resolution.md](resources/protocol/repo-resolution.md)).
   - **Never** bootstrap consumer `cdase/` in the framework repo (`cdase/SKILL.md`).
   - If no consumer `cdase/context/` in the **app** repo, opt-in is mandatory before any task.
2. On **yes**: read [resources/constitution.md](resources/constitution.md) + [resources/charter.md](resources/charter.md).
   - `discover` → select application repo(s). **2b**: all repos (same user) or none.
     **2c**: confirm identity, then all-or-none for missing repos. Set `CDASE_ROOT` for active work.
3. On **every user question** in CDASE mode (after hub URL is set), run **sync** before answering:
   ```
   python3 scripts/cdase_client.py sync
   ```
   Hub health + **inbox** (messages). Show `hub_warning` if hub is down.
4. Boot once with **`check`** or **`boot`** (identity + hub URL state + next step).
   * `ok: false` with missing global user → `input-spec user-profile`, then `apply-global-user`.
   * `hub_tools_blocked` → run `boot` / `init-global-setting` (copies template). Ask `hub-address` only for a non-default hub.
   * `unread_count > 0` from sync → show messages before answering.

**Hub model:** repo owns **users** (`users.context.md`); hub stores presence + messages.

**Identity:** **machine = user**. Roster/hub id = `sha256(machine_id)[:8]`. Different machine ⇒ different user. Global `Name` is display default when this machine first joins a repo; repo roster Name may differ later.

> Do not open the per-file context docs individually at boot — `check` / `boot` already read them.
> Consumer runtime = `<app-repo>/cdase/` (with `context/`). Skill package = `SKILL.md` + `resources/` + `scripts/` in the framework repo — not the runtime.

## Config layers

```
~/.cdase/                     ← global (all agents on this machine)
                              Windows: %USERPROFILE%\.cdase
  user.context.md             display Name (default when joining a repo)
  setting.context.md          hub Address (seeded from skill template)

my-app/cdase/context/         ← this repo (team)
  users.context.md            Name | machine-user-id | Role  (committed trust SSOT)
  setting.context.md          optional overrides (committed)
  user.context.md             optional override (gitignored)
```

## Standard skill layout

```
SKILL.md
scripts/cdase_client.py
resources/
```

Hub **server** is deployed separately. See [resources/reference.md](resources/reference.md).
