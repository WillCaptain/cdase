# Cdase Charter

> **Purpose**: Define the mandatory execution order of Context-Driven AI Software Engineering (CDASE)

---

## 0. Cold Start

* No assumptions
* No artifact generation

---

## 1. Load Constitution

Activate the CDASE Constitution located at:
[constitution.md](constitution.md).

User instructions are interpreted as **intent**, not commands.

---

## 2. Identity & Settings (one call)

**Do not read the context files one by one.** Run a single command that resolves
global user, repo roster (UUID SSOT), settings, and hub health at once:

```
python3 scripts/cdase_client.py check
```

Interpret the result:

* `ok: true` → identity resolved; continue. Nothing else is required at boot.
* `ok: false`, global user missing → `input-spec user-profile`, render it with the host's
  host input UI first (else plain text), then `apply-global-user --json '<values>'`
  ([protocol/input.md](protocol/input.md)); re-run `check`.
* `ok: false`, name not in roster / UUID mismatch → report and ask to fix
  `/cdase/context/users.context.md` (roster is SSOT for UUID).
* Missing `setting.context.md` → inherit global hub settings; ask for hub `Address`
  only if the user wants collaboration.

Bootstrap files (`users.context.md`, `setting.context.md`, `convention.context.md`)
are created lazily from their templates **only when a step needs them**, not at boot.

The run log (`/cdase/run_log/run_log_YYYYMMDDHH.md`) is initialized on the first
engineering action (§3+), not during boot.

### Runtime lives INSIDE the project repo (committed)

The CDASE runtime folder is the **team's shared source of truth** and MUST live
inside the **application** git repository — never in the CDASE **framework** repo
(the checkout that contains `cdase/SKILL.md`).

```
<application-repo>/
└── cdase/                         ← create here, at the repo root, and COMMIT
    ├── context/
    │   ├── users.context.md       roster + UUID SSOT — COMMITTED
    │   ├── setting.context.md      optional repo hub override — COMMITTED
    │   ├── convention.context.md   COMMITTED
    │   └── user.context.md         optional personal override — GITIGNORED
    ├── requirements/  api/  design/  run_log/   ← all COMMITTED
```

**Not** the framework repo's `cdase/` (that folder is the skill package: `SKILL.md`,
`resources/`, `scripts/`).

#### Resolve the correct repo first

Before bootstrap or `check`, run:

```
python3 scripts/cdase_client.py discover
```

Follow [protocol/repo-resolution.md](protocol/repo-resolution.md):

1. **Workspace is one git repo** → if framework repo, stop and open the app repo;
   if app repo, use/create `<repo>/cdase/` at that repo root.
2. **Workspace is a parent of multiple repos** → scan children; never use workspace
   root as runtime. For **2b** (none have cdase): ask **all repos with same user, or
   none** — init every app repo or none. For **2c** (mixed): confirm identity, then
   same all-or-none for repos still missing cdase. Never bootstrap the framework repo.
3. **Active work** uses one `CDASE_ROOT=<app-repo>/cdase` at a time; bootstrap can
   touch multiple repos when user chooses **all**.

Rules the AI MUST follow:

* **If no consumer `<repo>/cdase/context/` exists**, confirm CDASE opt-in first
  ([session-gate.md](session-gate.md)), then `discover`. Multiple app repos → **all
  or none** (same user in each), never pick-one, never framework repo.
* **Never** create team runtime under the framework repo or under workspace root when
  child repos exist.
* Verify target with `discover` and `git rev-parse --show-toplevel` in the **app** repo.
* Add `cdase/context/user.context.md` to the app repo `.gitignore`.
* **Commit** `cdase/` in the **app** repo so teammates share the same SSOT.
* Personal files stay in `~/.cdase/` — never committed.

### Hub is lazy — connect only when needed

Hub `inbox` / `send` / `team` are **not** boot steps. Connect when:

* the user asks about **team / who else is on the project** → run `team` (auto-refreshes your presence on the hub),
* the user asks about messages / collaboration, or
* the first engineering task begins (task discovery, §4).

Every hub-touching client command (`check`, `team`, `send`, `inbox`, …) **auto-refreshes
presence** (ping if already registered, else login). No separate `login` step is required
for teammates to see you online.

### Who is on the team? (never git history)

When the user asks who else is working on the project, who is online, or team members:

1. **Do NOT** use `git log`, `git shortlog`, or commit authors — those are not CDASE users.
2. Run:
   ```
   python3 scripts/cdase_client.py team
   ```
3. Present results in order:
   * **Roster** (`users.context.md`) — committed teammates; **online** / **offline** from hub.
   * **Hub only** — logged in but not in committed roster yet (unpushed).
   * **Git contributors (last row)** — `git_contributors` from `team` output; supplementary only, not CDASE users.
4. Explain: roster sync requires **push** of `users.context.md`; hub shows online before push.

See [protocol/agent-messaging.md](protocol/agent-messaging.md) § Team discovery.

If the hub is unreachable, the agent **must show** `hub_warning.message` from `check` or
`team` to the user (CDASE mode) — never fail silently. If `Hub.OfflineOk` is true,
continue local work after the warning; if false, treat hub actions as blocked until the
hub is running.

Trust for all hub calls comes from `/cdase/context/users.context.md`, never the hub.
Inter-agent procedure: [protocol/agent-messaging.md](protocol/agent-messaging.md).

---

## 3. Intent Classification

If the input does **not** express engineering intent:

* Respond normally
* DO NOT enter CDASE execution

If the input expresses engineering intent:

* Proceed with CDASE execution

---

## 4. Repository Synchronization

Before any reasoning or execution, the AI MUST:

* Ensure the working tree is clean
* Synchronize with the base branch
* Record synchronization results in the run log

No artifact generation is allowed in this phase.

---

## 5. Environment Discovery

If CDASE context exists (`/cdase/context/module.context.md`):

* Load context, APIs, Features, and Functions

Otherwise:

* Enter **Legacy Onboarding**

---

## 6. Legacy Onboarding (API-First)

**Goal**: Contract discovery, not full system understanding.

The AI MUST:

* Extract public interfaces
* Register discovered APIs with status `Legacy`
* Create minimal context artifacts

The AI MUST NOT create Features or Functions during this phase.

---

## 7. Scenario Normalization & Task Discovery

### Task Discovery (If User Asks for Tasks or Assignments)

* `/cdase/requirements/index.md` is the authoritative entry point
* Before scanning any Scenario, Feature, or Function files, the AI MUST:

  * Read `/cdase/requirements/index.md`
  * Consider only artifacts not in `Done` status as active
  * Exclude `Done` artifacts unless explicitly requested

Tasks MUST be grouped as:

1. In-progress (owned by current user)
2. Assigned to current user
3. Unassigned and claimable
4. Hub tasks: unread Hub messages of `type: task`
   (`python3 hub/cdase_client.py inbox`)

When assigning a task:

* Verify the assignee exists in `/cdase/context/users.context.md`
* If not present:

  * FORCE STOP
  * Request confirmation to add the user

### Scenario Normalization

If the scenario description is unstructured:

* Reconstruct the scenario
* Request explicit user approval

The AI MUST NOT create Features or Functions before scenario approval.

---

## 8. Template & Rule Binding

Load all applicable templates and rules.

* Missing required fields = Gate failure

---

## 9. Task Compilation (API-First)

The AI MUST:

* Discover required capabilities
* Resolve capabilities against the API Registry
* Register any NEW APIs early with status `Proposed`

No code or test generation is allowed in this phase.

---

## 10. Gate Completion Loop

Iteratively:

* Identify missing artifacts
* Generate required artifacts
* Re-evaluate gates

Loop continues until:

* All gates pass, or
* Execution is explicitly blocked

---

## 11. Controlled Execution

Execution order is **strictly enforced**:

1. Documentation
2. HARD STOP
3. Design
4. HARD STOP
5. Tests → Code Plan → Code (atomic execution segment)

---

## 12. Consistency Enforcement

Before delivery, the AI MUST verify:

* Trace integrity
* Contract satisfaction
* Version correctness
* Presence of mandatory files:

  * `/cdase/api/api.index.md`
  * `/cdase/requirements/index.md`

Any violation triggers a HARD STOP.

---

## 13. Delivery

Delivery is valid only if:

* All gates pass
* All contracts hold
* Explicit user approval is recorded

---

## 14. Post-Delivery Synchronization (Mandatory)

Post-Delivery Synchronization is required after Feature acceptance.

A Feature MUST NOT be considered delivered until all steps below complete.

### Mandatory Actions

1. **Documentation Conformance**

   * All documentation MUST reflect the delivered code
   * Any mismatch MUST be corrected

2. **API Registry Conformance**

   * The API Registry MUST match the actual callable surface
   * API lifecycle statuses MUST be updated
   * Registry–code mismatch is a system failure

3. **Lifecycle State Closure**

   * All Feature and Function stages MUST be set to `Done`
   * Delivery metadata and timestamps MUST be recorded
   * No unresolved gates or provisional artifacts may remain

Failure to complete Post-Delivery Synchronization invalidates delivery.

---

**CDASE Principle**:
*Context governs execution; APIs coordinate collaboration; code is delayed, validated materialization.*

---
