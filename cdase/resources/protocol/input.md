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
python3 scripts/cdase_client.py input-spec user-profile
```

Returns a host-agnostic spec, e.g. `user.profile`:

```json
{
  "preset": "user.profile",
  "kind": "form",
  "title": "Set your CDASE profile (global, once)",
  "fields": [
    { "key": "Name", "label": "Name", "required": true },
    { "key": "Role", "label": "Role", "options": ["architect","lead","developer","reviewer"] },
    { "key": "Team", "label": "Team" },
    { "key": "Organization", "label": "Organization" }
  ],
  "fallback_prompt": "Reply with your Name (required), Role, Team, Organization.",
  "render_hint": "Render with your host's native input UI; else ask in text. Never open a browser.",
  "apply_command": "python3 scripts/cdase_client.py apply-global-user --json '<values>'"
}
```

`kind` is `"choice"` (options) or `"form"` (fields). Fields with `options` are pick-lists;
others are free-text. No `hub` call is needed to get a spec — it works offline.

## Agent responsibilities

1. Run `input-spec PRESET`.
2. **Render natively**: in Cursor, present it as the multiple-choice / question card
   (one question per field; use the option list for pick-lists; "Other" for free text).
   On a host with no native input UI, ask the `fallback_prompt` in plain text.
3. Collect the user's values.
4. **Apply** the result yourself — CDASE input never writes files or changes state:
   - `session.gate` → interpret choice: `yes` → CDASE ON, `no` → CDASE OFF.
   - `user.profile` → `python3 scripts/cdase_client.py apply-global-user --json '<values>'`.

## Presets

| Preset | kind | CLI | Result the agent applies |
|---|---|---|---|
| `session.gate` | choice | `input-spec session-gate` | `yes`/`no` → CDASE on/off |
| `user.profile` | form | `input-spec user-profile` | `apply-global-user --json '{...}'` |

## Bootstrap flow (identity)

1. Global `~/.cursor/cdase/user.context.md` missing → `input-spec user-profile`.
2. Render natively (Cursor card) or ask in text.
3. `apply-global-user --json '...'` writes the global profile.
4. Continue charter boot (`check`, roster UUID lookup, lazy `login`).

> The session gate itself is text-first by default (it must be instant and hub-independent);
> a host MAY render it as a native yes/no card, but plain text is always sufficient.
