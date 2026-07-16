# CDASE Input Protocol (host-native, text-fallback)

> CDASE **never ships its own UI** and never opens a browser. When it needs input, it
> emits a **declarative input spec**; the **agent** renders it with the host's richest
> native input UI and demotes to plain text when the host has none. The agent owns the
> post-submit action.

## Why (the hard constraint)

There is **no cross-agent way to render custom HTML inside a chat**:

- **Cursor** chat renders only markdown + Cursor's own components — no third-party HTML injection.
- **CLI agents** (e.g. Claude Code) are terminal-only — no HTML at all.

So the portable design is **instruction-level, not API-level**: describe the input,
let each host draw it with what it has.

## Rendering tiers (agent picks the best available)

| Tier | Host example | How the spec is shown |
|---|---|---|
| Native structured UI | Cursor multiple-choice / question card | inline, clickable options; free-text via "Other" |
| Plain text | any CLI / minimal host | the `fallback_prompt` string |

Text is the universal floor — functionality is never lost, only the richer card is.

## Get an input spec

```bash
python3 scripts/cdase_client.py input-spec session-gate
python3 scripts/cdase_client.py input-spec user-scope
python3 scripts/cdase_client.py input-spec user-profile
python3 scripts/cdase_client.py input-spec user-profile-repo
python3 scripts/cdase_client.py input-spec hub-address
```

## Identity: global vs this-repo (mandatory clarity)

Identity can live in two places. The agent MUST NOT guess.

| Scope | File | When |
|---|---|---|
| **global** | `~/.cdase/user.context.md` | First boot (missing global), or user wants all projects |
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

## Bootstrap flow (identity)

1. Global `~/.cdase/user.context.md` missing → `input-spec user-profile`.
2. Render natively (Cursor card) or ask in text.
3. `apply-global-user --json '...'` writes `~/.cdase/user.context.md` (or `$CDASE_GLOBAL`).
4. Continue charter boot (`check`, roster UUID lookup, lazy `login`).

> The session gate itself is text-first by default (it must be instant and hub-independent);
> a host MAY render it as a native yes/no card, but plain text is always sufficient.
