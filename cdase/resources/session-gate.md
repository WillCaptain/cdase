# CDASE Session Gate

> **Agent-neutral**. Applies to any code agent.
> CDASE is never assumed — the user must opt in each session.

## First turn (before any other work)

If the user has **not** yet declared CDASE on/off this session, ask in **plain text**:

> **Apply CDASE in this session?** (yes / no)

Then **stop and wait**. Do not read files, call the hub, or run tools yet — the
opt-in must be instant.

**Optional** (only if the host has a native input UI and it adds no latency): render the
question as your host's native yes/no card (in Cursor, the multiple-choice card). The
plain-text prompt above is always sufficient and is the default. CDASE never opens a
browser. See [protocol/input.md](protocol/input.md).

## No `cdase/` folder in the repo → confirmation is MANDATORY

If the project repo has **no `cdase/` folder at its root**, CDASE is not yet
initialized here. In that case the opt-in is **not skippable**:

- **Whatever the user's first message is** — even a direct task request — do **not**
  silently start the work. First state that there is no `cdase/` folder in the repo,
  then ask **"Apply CDASE in this session? (yes / no)"** and **stop for the answer**.
  This guarantees the following job is CDASE-based (or explicitly not).
- On **yes**: initialize CDASE — create `<repo>/cdase/` at the repo root and **commit
  it** ([charter.md](charter.md) §2) — *before* doing the requested task, so the work
  is grounded in CDASE from the start.
- On **no**: proceed as a normal assistant; do not create `cdase/`.

If a `cdase/` folder already exists, use the normal gate above (a plain yes/no is enough).

## One-time global setup (not per session)

On first `cdase on`, if `~/.cursor/cdase/user.context.md` is missing, use the
**host-native input flow** (works on any agent) — see [protocol/input.md](protocol/input.md):

1. `python3 scripts/cdase_client.py input-spec user-profile` → declarative field spec.
2. **Render it natively**: in Cursor, present the fields as multiple-choice / question
   cards (pick-list for Role, "Other"/text for Name/Team). No native UI → ask in plain text.
3. Collect the values; **agent** runs `apply-global-user --json '...'`.
4. This never opens a browser and does not need the hub.

If `~/.cursor/cdase/setting.context.md` is missing, ask for the hub Address once (plain text).

## Interpreting the answer

| User says / choice | Session mode |
|---|---|
| yes, y, cdase, cdase on | **CDASE ON** — load [SKILL.md](../SKILL.md), run [charter boot](charter.md) |
| no, n, skip, cdase off | **CDASE OFF** — normal assistant |

## While the session runs

- **CDASE ON**: Read [../SKILL.md](../SKILL.md), then [charter.md](charter.md) (`check` → lazy `login`/`inbox`).
- **CDASE OFF**: Do not load CDASE unless user says `cdase on`.
- Toggle: `cdase on` / `cdase off`.
