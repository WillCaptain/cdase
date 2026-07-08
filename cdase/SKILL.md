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

1. [resources/session-gate.md](resources/session-gate.md) — ask "Apply CDASE?" and **stop** for the answer.
   - If the repo has **no `cdase/` folder**, this opt-in is mandatory and cannot be skipped —
     ask it even if the user's first message is a task request, so the work is CDASE-based.
2. On **yes**: read [resources/constitution.md](resources/constitution.md) + [resources/charter.md](resources/charter.md).
   - If `<repo>/cdase/` is absent, initialize and commit it (charter §2) before the task.
3. Run **one** command — it resolves identity, roster, settings, and hub health in a single call:
   ```
   python3 scripts/cdase_client.py check
   ```
   * `ok: false` with missing global user → `input-spec user-profile`, render natively (Cursor card) or text, then `apply-global-user` ([protocol/input.md](resources/protocol/input.md)).
   * `ok: true` → continue.

**Defer everything else until it's actually needed** (do NOT do at boot):
- `login` / `inbox` — only when the user collaborates or on first engineering task.
- Reference and protocol docs ([reference.md](resources/reference.md), [protocol/](resources/protocol/)) — read on demand.
- Run log, repo sync, task discovery — start when engineering intent appears (charter §3+).

> Do not open the per-file context docs individually at boot — `check` already reads them.
> `/cdase/` = consumer project's cdase folder (runtime). Skill = `SKILL.md` + `resources/` + `scripts/`.

## Config layers

```
~/.cursor/cdase/              ← you (global, set once)
  user.context.md             Name, preferences
  setting.context.md          default hub address

my-app/cdase/context/         ← this repo
  users.context.md            roster + UUID SSOT (committed)
  setting.context.md          optional overrides (committed)
  user.context.md             optional identity override (gitignored)
```

## Standard skill layout

```
SKILL.md
scripts/cdase_client.py
resources/
```

Hub **server** is deployed separately. See [resources/reference.md](resources/reference.md).
