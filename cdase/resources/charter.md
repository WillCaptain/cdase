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

### Portable client invocation

Install the CDASE package once from the methodology checkout:

```bash
python -m pip install .
# Windows
py -m pip install .
```

In this Charter and all linked procedures, `<CDASE_CLIENT>` means:

1. the installed `cdase` command when it is available on `PATH`; otherwise
2. the bundled client, invoked as `python3 <skill-root>/scripts/cdase_client.py`
   (Windows: `py <skill-root>\scripts\cdase_client.py`).

---

## 2. Resolve Repository, Then Identity and Settings

Run `<CDASE_CLIENT> discover` and follow
[protocol/repo-resolution.md](protocol/repo-resolution.md) before checking or
creating state. Select the application repository, never the methodology
framework repository, and set `CDASE_ROOT=<app-repo>/cdase` when discovery is
ambiguous.

**Do not read the context files one by one.** Run a single command that resolves
global profile, committed member records, settings, and hub health:

```
<CDASE_CLIENT> check
```

Interpret the result:

* `ok: true` → identity resolved; continue. Nothing else is required at boot.
* `ok: false`, global user missing → `input-spec user-profile`, render it with the host's
  host input UI first (else plain text), then `apply-global-user --json '<values>'`
  ([protocol/input.md](protocol/input.md)); re-run `check`.
* `ok: false`, machine-derived user id missing from members → run `boot`; if the
  global profile is missing, collect `user-profile` first.
* Missing `setting.context.md` → `boot` copies the skill template to
  `<GLOBAL_CDASE>/setting.context.md`; ask for `hub-address` only for a custom URL.

`<GLOBAL_CDASE>` is `CDASE_GLOBAL` when set; otherwise it is `~/.cdase` on
macOS/Linux and `%USERPROFILE%\.cdase` on Windows. Global
`<GLOBAL_CDASE>/setting.context.md` is seeded from the skill template by `boot`
(no overwrite). Repo bootstrap files (`context/members/`, optional
`setting.context.md`, `convention.context.md`) are created only when the repo
initialization step needs them.

Settings resolve in this order, with later layers overriding earlier ones:
**defaults → global → repo → environment**.

The run log (`/cdase/run_log/run_log_YYYYMMDDHH.md`) is initialized on the first
engineering action (§3+), not during boot.

### Shared project state lives inside the application repository

The CDASE runtime folder is the **team's shared source of truth** and MUST live
inside the **application** git repository — never in the CDASE **framework** repo
(the checkout that contains `cdase/SKILL.md`).

```
<application-repo>/
└── cdase/                         ← create here, at the repo root, and COMMIT
    ├── context/
    │   ├── members/
    │   │   └── <8-hex-user-id>.context.md
    │   │                              membership + trust SSOT — COMMITTED
    │   ├── setting.context.md      optional repo hub override — COMMITTED
    │   ├── convention.context.md   COMMITTED
    │   └── user.context.md         optional alias/role override — GITIGNORED
    ├── requirements/                 ← all requirement/design/workflow artifacts
    │   ├── index.md
    │   └── SCN-XXX/
    │       ├── scenario.md
    │       └── FTR-YY/
    │           ├── feature.md  design.md  code-plan.md
    │           ├── gates.md    progress.md
    │           └── FUN-ZZ/
    │               ├── function.md  code-plan.md
    │               ├── gates.md     progress.md
    │               └── design.md    # conditional
    ├── api/
    └── run_log/                     ← all COMMITTED
```

**Not** the framework repo's `cdase/` (that folder is the skill package: `SKILL.md`,
`resources/`, `scripts/`).

#### Resolve the correct repo first

Before bootstrap or `check`, run:

```
<CDASE_CLIENT> discover
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
* `boot` writes that optional override into the current user's shared
  `context/members/<user-id>.context.md` record; commit it before it grants trust.
* **Commit** `cdase/` in the **app** repo so teammates share the same SSOT.
* Personal files stay in `<GLOBAL_CDASE>/` — never committed.

### Sync before every user answer

After identity and an explicit Hub URL are valid, run
`<CDASE_CLIENT> sync` before **every user answer**. Before those prerequisites
are valid, do not call `sync`, `team`, `send`, or `inbox`.

`sync` and `team` refresh presence (ping if already registered, else login).
`check` validates identity/settings and Hub health without changing presence.
No separate `login` step is required in the normal journey.

### Who is on the team? (never git history)

When the user asks who else is working on the project, who is online, or team members:

1. **Do NOT** use `git log`, `git shortlog`, or commit authors — those are not CDASE users.
2. Run:
   ```
   <CDASE_CLIENT> team
   ```
3. Present results in order:
   * **Members** (`context/members/*.context.md`) — active committed teammates;
     **online** / **offline** comes from Hub presence.
   * **Hub only** — present on Hub but not an active committed member.
   * **Git contributors (last row)** — `git_contributors` from `team` output; supplementary only, not CDASE users.
4. Explain: membership sync requires **push** of member records; Hub may show
   presence before the record is pushed.

See [protocol/agent-messaging.md](protocol/agent-messaging.md) § Team discovery.

If the hub is unreachable, the agent **must show** `hub_warning.message` from `check` or
`team` to the user (CDASE mode) — never fail silently. If `Hub.OfflineOk` is true,
continue local work after the warning; if false, treat hub actions as blocked until the
hub is running.

Trust for all Hub calls comes from active committed
`/cdase/context/members/<8-hex-user-id>.context.md` records, never the Hub.
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

Classify adoption and maturity independently:

`<CDASE_CLIENT> legacy-classify`

* `CDASE_UNINITIALIZED` describes adoption only; it does not mean legacy.
* `GREENFIELD` has no first-party production implementation.
* `LEGACY` has implementation but no CDASE context.
* `PARTIAL_LEGACY` has CDASE context but incomplete API registry coverage.
* `MANAGED` has CDASE context and API registry coverage.

For `LEGACY` or `PARTIAL_LEGACY`, offer **Legacy Onboarding**. For
`GREENFIELD`, initialize CDASE normally; do not scan an empty/new repository.

---

## 6. Legacy Onboarding (API-First)

**Goal**: Contract discovery, not full system understanding.

The AI MUST:

1. Run `legacy-scan-spec`.
2. Launch the returned prompt in a **new isolated, read-only session/agent**
   (HARD STOP: never perform the scan in the parent session).
3. Validate and persist the returned strict JSON with `legacy-scan-save`.
4. Show all candidates grouped by `HIGH | MEDIUM | LOW` using
   `legacy-approval-spec`; use host-native multi-select first.
5. Apply only explicit user selections with `legacy-api-apply`.
6. Commit the scan approval and generated `*.api.md` contracts.
7. Run `legacy-api-upload --approval <approval.json>`.
8. Verify each registry with `api-sync <file> --check`.

Approved legacy APIs use normal lifecycle status: publish as `DEVELOPING`, then
transition to `RELEASED` after committed-source verification. `LEGACY` is
provenance (`origin: LEGACY_IMPORT`), never a lifecycle status.

The scan session MUST NOT write files, upload to Hub, or create Features or
Functions. The parent may write only the validated report, explicit approval,
and selected registry blocks. See `resources/protocol/legacy-scan.md`.

---

## 7. Scenario Normalization & Task Discovery

### Task Discovery (If User Asks for Tasks or Assignments)

* `/cdase/requirements/index.md` is the authoritative entry point
* Before scanning any Scenario, Feature, or Function files, the AI MUST:

  * Read `/cdase/requirements/index.md`
  * Verify indexed Feature/Function state against each artifact's `progress.md`
  * Consider only Features/Functions whose `progress.md` Status is not `Done`
    as active execution tasks
  * Exclude `Done` Features/Functions unless explicitly requested

Tasks MUST be grouped as:

1. In-progress (owned by current user)
2. Assigned to current user
3. Unassigned and claimable
4. Hub tasks: unread Hub messages of `type: task`
   (`<CDASE_CLIENT> inbox`)

When assigning a task:

* Parse the assignee as `user-id (project-alias)`; the user id is authoritative
* Verify that id has an active committed record in `/cdase/context/members/`
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
* Copy templates to generic canonical filenames:

| Output | Template |
|---|---|
| `SCN-XXX/scenario.md` | `templates/scenario.md` |
| `FTR-YY/feature.md` | `templates/feature.md` |
| `FTR-YY/design.md` | `templates/feature_design.md` |
| `FTR-YY/code-plan.md` | `templates/feature_code_plan.md` |
| `FTR-YY/gates.md` | `templates/feature_gates.md` |
| `FTR-YY/progress.md` | `templates/feature_progress.md` |
| `FUN-ZZ/function.md` | `templates/function.md` |
| `FUN-ZZ/design.md` (conditional) | `templates/function_design.md` |
| `FUN-ZZ/code-plan.md` | `templates/function_code_plan.md` |
| `FUN-ZZ/gates.md` | `templates/function_gates.md` |
| `FUN-ZZ/progress.md` | `templates/function_progress.md` |

Do not copy template filenames such as `feature_design.md` into the consumer
runtime; the canonical output is always `design.md`.

---

## 9. Task Compilation (API-First)

The AI MUST:

* Discover required capabilities
* Search the Global API Pool before local design:
  `<CDASE_CLIENT> api-search "<capability>"`
* Record query, candidates, scores, and source links in the target `gates.md`
* Read candidate contracts from their owning repositories/registries
* Resolve exactly one: REUSE | EVOLVE | CREATE
* On CREATE, add the canonical `cdase-api` block to the owning module registry
  and run `api-sync` to reserve it globally as `DEVELOPING`
* On EVOLVE, add a new version; never rewrite a released contract

No code or test generation is allowed in this phase.

---

## 10. Gate Completion Loop

Iteratively:

* Identify missing artifacts
* Generate required definition/design/plan artifacts from the applicable templates
* Record criteria and evidence only in `gates.md`
* Record Stage, Status, Owner, assignment, timestamps, and blockers only in `progress.md`
* Re-evaluate gates against evidence

Loop continues until:

* All gates pass, or
* Execution is explicitly blocked

---

## 11. Controlled Execution

Execution order is **strictly enforced**:

1. Scenario/Feature/Function definitions (ACs remain in `feature.md` / `function.md`)
2. HARD STOP
3. Feature `design.md` (mandatory) and Function `design.md` (conditional);
   all diagrams are included in the applicable design document
4. HARD STOP
5. Tests → approved Feature/Function `code-plan.md` → Code (atomic execution segment)

---

## 12. Consistency Enforcement

Before delivery, the AI MUST verify:

* Trace integrity
* Contract satisfaction
* Version correctness
* Presence of mandatory files:

  * `/cdase/api/api.index.md`
  * `/cdase/requirements/index.md`
  * Feature: `feature.md`, `design.md`, `code-plan.md`, `gates.md`, `progress.md`
  * Function: `function.md`, `code-plan.md`, `gates.md`, `progress.md`
  * Function `design.md` when parent Feature design is insufficient

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
   * The Global API Pool entry MUST match the source registry content hash
   * Accepted APIs MUST transition from `DEVELOPING` to `RELEASED`
   * Replaced versions MUST transition to `SUPERSEDED`
   * Registry–code mismatch is a system failure

3. **Lifecycle State Closure**

   * All Feature and Function `progress.md` files MUST be set to `Done`
   * Delivery metadata and timestamps MUST be recorded
   * No unresolved items in `gates.md` or provisional artifacts may remain

Failure to complete Post-Delivery Synchronization invalidates delivery.

---

**CDASE Principle**:
*Context governs execution; APIs coordinate collaboration; code is delayed, validated materialization.*

---
