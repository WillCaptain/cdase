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
  native input UI (else plain text), then `apply-global-user --json '<values>'`
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
inside the project git repository so it is committed and pushed:

```
<project-repo>/
└── cdase/                         ← create here, at the repo root, and COMMIT
    ├── context/
    │   ├── users.context.md       roster + UUID SSOT — COMMITTED
    │   ├── setting.context.md      optional repo hub override — COMMITTED
    │   ├── convention.context.md   COMMITTED
    │   └── user.context.md         optional personal override — GITIGNORED
    ├── requirements/  api/  design/  run_log/   ← all COMMITTED
```

Rules the AI MUST follow:

* **If `<repo>/cdase/` does not exist, CDASE is uninitialized.** Do not start any
  requested task first — confirm the CDASE opt-in ([session-gate.md](session-gate.md)),
  and on **yes** create + commit `cdase/` before proceeding, so the work is CDASE-based.
* When creating the runtime, place `cdase/` at the **project repo root** (same repo
  as the code), never outside it. Verify with `git rev-parse --show-toplevel`.
* Add `cdase/context/user.context.md` to the repo `.gitignore` (personal identity only).
* **Commit** `cdase/` (roster + artifacts) so teammates share the same base. Without
  a committed `cdase/`, there is no team SSOT.
* Personal, per-machine files live in `~/.cursor/cdase/` (global identity + hub
  address) and are **never** committed — this is separate from the repo runtime.

### Hub is lazy — connect only when needed

Hub `login` / `inbox` are **not** boot steps. Perform them only when:

* the user asks about messages / collaboration, or
* the first engineering task begins (task discovery, §4).

If the hub is unreachable and `Hub.OfflineOk` is true, continue in offline mode
silently; if false, report when a hub action is actually attempted.

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
