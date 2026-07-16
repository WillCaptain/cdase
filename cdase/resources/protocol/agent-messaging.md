# CDASE Agent Messaging Protocol

> **How** agents communicate peer-to-peer via Hub.  
> **Law**: [constitution.md](../constitution.md) §XVI · **Procedure**: [charter.md](../charter.md) §2

## Identity (no separate agent UUID)

Every message uses a **roster human UUID** as `from_uuid` / `to_uuid`.

| Field | Meaning |
|---|---|
| `from_uuid` | Human owner of the sending side (e.g. user_b) |
| `to_uuid` | Human recipient (e.g. user_a) |
| `from_actor` | `human` — user typed/sent · `agent` — agent composed autonomously |

Accountability stays with the human on the roster. `from_actor` marks **who engaged**, not a separate agent identity.

## Repo boundary (hard rule)

| Content | Agent may send autonomously? |
|---|---|
| Files under git repository root (committed **or** local unpushed) | **Yes** |
| `/cdase/**` artifacts, API docs, requirements, design | **Yes** |
| Environment secrets, `~/.cdase` (or legacy `~/.cursor/cdase`), paths outside repo, private notes | **No** — STOP, ask user |

`send-file` enforces repo boundary in the client. Free-text `send` runs a best-effort secret/path scan; blocked unless user approves (`--user-approved`).

## Message envelope

```json
{
  "from_uuid": "400edd13",
  "to_uuid": "a227ca54",
  "from_actor": "agent",
  "type": "message",
  "intent": "question",
  "thread_id": "FUN-002-01-01",
  "subject": "API dependency: OrderService.create",
  "body": "Blocked on FUN-002-01-01. Need API for OrderService.create. Not in /cdase/api/ or repo search."
}
```

### `intent` values

| intent | Use |
|---|---|
| `question` | Blocked; need info from peer |
| `answer` | Reply to `question` |
| `file` | Repo file shared (`send-file`) |
| `notify` | FYI, no reply expected |
| `task` | Action item |
| `handoff` | Work transfer |
| `message` | General |

`thread_id` SHOULD be the active artifact ID (e.g. `FUN-002-01-01`) so the exchange stays traceable.

## Scenario: missing API (unpushed local work)

1. **user_b** agent works on `FUN-002-01-01`, needs API from `FUN-001-01-01`.
2. API not in repo (only on **user_a**'s machine).
3. **agent_b** sends to **user_a**'s UUID:

```bash
python3 scripts/cdase_client.py send user_a \
  "Blocked on FUN-002-01-01. Need invokeable API for OrderService.create. Searched /cdase/api/ — not found." \
  --from-actor agent --intent question --thread-id FUN-002-01-01
```

4. **user_a**'s agent reads inbox, finds answer locally (unpushed file OK), replies:

```bash
python3 scripts/cdase_client.py send-file user_b src/order/OrderService.java \
  --from-actor agent --thread-id FUN-002-01-01 \
  --note "API for FUN-001-01-01 — local unpushed"
```

Or text answer:

```bash
python3 scripts/cdase_client.py send user_b \
  "OrderService.create(orderId): Order — see FUN-001-01-01" \
  --from-actor agent --intent answer --thread-id FUN-002-01-01
```

5. **agent_b** continues `FUN-002-01-01`.
6. Both agents **summarize** the exchange to their human.

## Inbound rules (receiving agent)

When inbox message has `from_actor: agent`:

| intent | Agent action |
|---|---|
| `question` | Attempt answer from repo + local tree; reply with `intent: answer` or `file` if `AutoReplyToAgentQuestions` is true |
| `file` | Apply content to local context; inform user what was received |
| `task` | Merge into task discovery; user confirms before starting |
| `notify` | Summarize to user |

Always surface agent traffic to the human (sender name, from_actor, thread_id, summary).

## Outbound rules (sending agent)

Agents MAY autonomously message roster peers when `AgentAutonomy: delegated` (default).

Before send:

1. Recipient in `users.context.md`
2. Content is repo-safe (or user approved)
3. Message is self-contained (artifact IDs, what was searched, what is needed)
4. Set `from_actor: agent` and appropriate `intent` + `thread_id`

Human `@someone` or "tell X …" → `from_actor: human`.

## Team discovery ("who is on this project?")

**Never use git history** for CDASE team identity. Git authors ≠ roster users.

### Procedure (agent)

1. `python3 scripts/cdase_client.py team` — also auto-refreshes your hub presence (ping or login).
2. Present merged list (**primary**):

| `status` | Meaning |
|---|---|
| `online` | In committed roster **and** active on hub (recent `login`/`ping`) |
| `offline` | In roster but not active on hub |
| `hub_only` | On hub but **not** in committed `users.context.md` — often unpushed roster |

3. **Last (supplementary):** `git_contributors` — git authors **not** in roster. FYI only; **not** CDASE team members. Show after CDASE members.

## Trust model (repo SSOT + hub superset)

| Layer | Role |
|---|---|
| **`users.context.md`** (repo) | **Trust SSOT** — who user_b accepts; UUIDs for send/inbox trust |
| **Hub users** (login) | **Superset** — anyone active on hub, including users not yet in repo |
| **Hub messages** | All stored; client fetches with `trust=all` and classifies |

### User list (`team`)

| `status` | Meaning |
|---|---|
| `online` / `offline` | In **your** roster |
| `new_to_you` | On hub, **not** in your `users.context.md` — ask user to confirm before trusting |

### Messages (`sync` / `inbox`)

| `status` | Agent may auto-reply? |
|---|---|
| `trusted` | Yes (if `AgentAutonomy: delegated`) |
| `unknown_sender` | **No** — show message; user must confirm sender is safe and add to roster |

**Rule:** If **will** messages **evan** but will is not in evan's roster yet → evan's agent shows the message and asks evan to confirm — **no automatic reply** to will's agent until evan adds will to `users.context.md`.

### Sources

### `repo_id` resolution (client)

1. `Project.RepoId` in `cdase/context/setting.context.md` (committed, preferred)
2. `CDASE_REPO_ID` env override
3. Normalized `git remote get-url origin` (e.g. `github.com/org/aintegration`)
4. Git repo directory name (fallback)

Every `login` / `ping` / `team` sends `repo_id` so hub presence is **per project**, not global.

```bash
# hub API (client wraps this)
GET /users?repo_id=github.com/org/aintegration
POST /login  { "uuid", "name", "machine_id", "repo_id", "trust" }
```

### Sources (roster vs hub)

Example: **will** works locally in repo A but has not pushed `users.context.md`.
**even** in repo B runs `team`:

* will is **not** in even's roster file (not pushed),
* will **may** appear as `hub_only` + `online` if will used any hub command on the same hub (presence auto-refreshes).

After will pushes roster, both machines see will in roster.

```bash
python3 scripts/cdase_client.py team   # refreshes your presence automatically
```

Hub-touching commands (`check`, `team`, `send`, `inbox`, …) ping or login before the main
action so teammates see you online without a separate heartbeat step.

## CLI reference

```bash
python3 scripts/cdase_client.py send <to> "<body>" \
  [--from-actor agent|human] [--intent question|answer|file|...] [--thread-id FUN-xxx]

python3 scripts/cdase_client.py send-file <to> <repo-path> \
  [--note "..."] [--thread-id FUN-xxx] [--from-actor agent]

# Out-of-repo content (user explicitly approved):
python3 scripts/cdase_client.py send <to> "<body>" --user-approved
```

## Settings (`setting.context.md` → Messaging)

| Field | Default | Purpose |
|---|---|---|
| FromActor | agent | Default for agent-composed sends |
| AgentAutonomy | delegated | `none` \| `blocked` \| `delegated` |
| AutoReplyToAgentQuestions | true | Auto-answer peer agent questions from repo |
