# CDASE Input Protocol (host-native first, text fallback)

> CDASE **never ships its own UI** and never opens a browser. When it needs input, it
> emits a **declarative input spec**. The **agent** maps that spec onto **whatever input
> UI its host provides**. Order is always the same; the concrete widget differs by agent.

`<CDASE_CLIENT>` means installed `cdase` after `python -m pip install .`
(Windows: `py -m pip install .`), with the bundled
`python3 <skill-root>/scripts/cdase_client.py` fallback.
`<GLOBAL_CDASE>` means `CDASE_GLOBAL` when set, else `~/.cdase` on
macOS/Linux or `%USERPROFILE%\.cdase` on Windows.

## Generic render order (mandatory for every host)

1. Run `input-spec PRESET` → get `kind`, `options` / `fields`, `fallback_prompt`, `render_hint`.
2. **Use the host’s richest matching input UI** for that `kind`
   (choice → options UI; multi_choice → multi-select UI; form → fields UI).
3. If that UI is missing or fails → **plain text** using `fallback_prompt`.
4. Never open a browser; never invent a CDASE-owned HTML page.

CDASE does **not** prescribe Cursor cards, Claude prompts, Codex forms, etc. Each agent
implements step 2 with its own primitives.

## Why (portable by design)

There is no one cross-agent widget API. So CDASE stays **instruction-level**:

- Spec = what to ask (`choice` / `multi_choice` / `form` + options/fields).
- Host = how to show it (that product’s buttons, pickers, slash UI, TUI, …).
- Text = universal floor when the host has no structured input.

## Kind → intent (host maps to its own UI)

| Spec `kind` | Intent | Host maps to (examples — not exhaustive) |
|---|---|---|
| `choice` | Pick one option | yes/no buttons, multiple-choice, select list, numbered menu |
| `multi_choice` | Pick zero or more options | checkbox list, multi-select, grouped numbered menu |
| `form` | Collect fields | multi-step questions, native form, pick-list for `options` fields |

Illustrative only: Cursor may use question cards; a CLI may use a TUI select; another IDE
may use its own picker. **Same order, different chrome.**

## Get an input spec

```bash
<CDASE_CLIENT> input-spec session-gate
<CDASE_CLIENT> input-spec user-scope
<CDASE_CLIENT> input-spec user-profile
<CDASE_CLIENT> input-spec user-profile-repo
<CDASE_CLIENT> input-spec hub-address
```

## Identity: global vs this-repo (mandatory clarity)

Identity can live in two places. The agent MUST NOT guess.

| Scope | File | When |
|---|---|---|
| **global** | `<GLOBAL_CDASE>/user.context.md` | First boot (missing global), or user wants all projects |
| **repo** | `<repo>/cdase/context/user.context.md` (gitignored) | Override for this project only |

### Agent rule

1. **First boot**, global missing → `input-spec user-profile` → `apply-global-user` (scope implied: global). Do **not** create repo `user.context.md`.
2. User later says “update my profile / add user info / change name” and does **not** say where → **`input-spec user-scope` first**:
   - `global` → `user-profile` → `apply-global-user` (create **or** update)
   - `repo` → `user-profile-repo` → `apply-repo-user` (create **or** update)
3. User already says “globally” / “only in this repo” → skip scope; go straight to the matching form.

## Presets

| Preset | kind | CLI | Result the agent applies |
|---|---|---|---|
| `session.gate` | choice | `input-spec session-gate` | `yes`/`no` → CDASE on/off |
| `user.scope` | choice | `input-spec user-scope` | `global` / `repo` → next form |
| `user.profile` | form | `input-spec user-profile` | `apply-global-user --json '{...}'` |
| `user.profile.repo` | form | `input-spec user-profile-repo` | `apply-repo-user --json '{...}'` |
| `hub.address` | form | `input-spec hub-address` | `apply-global-setting --json '{...}'` |
| `legacy.api.approval` | multi_choice | `legacy-approval-spec --report …` | `legacy-api-apply --selection-json '{...}'` |

## Bootstrap flow (identity)

1. Global `<GLOBAL_CDASE>/user.context.md` missing → `input-spec user-profile`.
2. Render with **host UI first** (generic order above); text only if unavailable.
3. `apply-global-user --json '...'` writes `<GLOBAL_CDASE>/user.context.md`.
4. Continue with `check`; run `boot` only when state is missing. Boot publishes
   the optional repo Alias/Role override to the machine's committed member record.
   Then run `sync` after
   identity and explicit Hub URL are valid.

> Session gate (`input-spec session-gate`) uses the same generic order: host choice UI
> if any; else plain “yes / no”.
