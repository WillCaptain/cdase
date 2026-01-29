# Prompt Boot Sequence

> **Purpose**: Define the mandatory execution order of Context-Driven AI Software Engineering (CDASE)

---

## 0. Cold Start

* No assumptions
* No artifact generation

---

## 1. Load Constitution

Activate the CDASE Constitution located at:
`/cdase/prompts/constitution.md`.

User instructions are interpreted as **intent**, not commands.

---

## 2. Identity, Context & Run Initialization

The AI MUST perform the following initializations:

* Resolve current user identity from `/cdase/context/user.context.md`
* Resolve user registry from `/cdase/context/users.context.md`
* Load project conventions from `/cdase/context/convention.context.md`
* Initialize a run log at:
  `/cdase/run_log/run_log_YYYYMMDDHH.md`

### Mandatory Checks

* If `user.context.md` is missing:

  * STOP
  * Request initialization using `/cdase/templates/user.md`
  * Add the identity file to `.gitignore`

* If `users.context.md` is missing

   * initialize it using `/cdase/templates/users.md`

* If `convention.context.md` is missing:

  * Initialize it using `/cdase/templates/convention.md`

* If the user identity in `user.context.md` is confirmed or updated:

  * Update `users.context.md` accordingly

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

  * Read `requirements/index.md`
  * Consider only artifacts not in `Done` status as active
  * Exclude `Done` artifacts unless explicitly requested

Tasks MUST be grouped as:

1. In-progress (owned by current user)
2. Assigned to current user
3. Unassigned and claimable

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
