# Context-Driven AI Software Engineering (CDASE)

Context-Driven AI Software Engineering (CDASE) is a **document-governed software engineering methodology** in which a large language model (LLM) acts as the primary execution engine for engineering processes.

Instead of relying on external workflow tools (e.g., requirement trackers, CI gate systems, test management platforms), CDASE encodes **engineering intent, constraints, and execution rules directly into structured textual artifacts**, and assigns the responsibility of enforcement to the AI system itself.

In CDASE, **context is the system**, and **AI is the executor**.

---

## 1. Motivation

Modern software engineering depends on a growing ecosystem of process-oriented tools—issue trackers, workflow engines, architecture governance systems, CI/CD pipelines—not because they produce software artifacts, but because they enforce *process consistency*.

With the emergence of large language models capable of reasoning over structured text, much of this enforcement logic can be internalized by the AI itself.

CDASE is built on the hypothesis that:

> If engineering context is **explicit, structured, complete, and consistent**, then an AI system can reliably replace most traditional software engineering workflow systems.

The goal of CDASE is **not speed**, but **controlled, traceable, and auditable software evolution** under human authority.

---

## Framework Repository Layout

```text
cdase/                 agent-neutral skill, resources, and Python client
adapters/cursor/       Cursor-specific rules and hooks
hub/                   shared collaboration and Global API Pool service
docs/                  human-facing architecture and concepts
tests/fixtures/app/    consumer application fixture
pyproject.toml         installable `cdase` CLI package
```

Host adapters translate CDASE into agent-specific hooks and UI capabilities;
they do not fork the canonical methodology under `cdase/`.

---

## 2. Core Principles

### P1. Everything Is a Template

All engineering artifacts are defined by **strict templates** that act as schemas, not prose documentation.

Examples include:

* Scenarios
* Features
* Functions
* Design artifacts
* Test specifications
* Code plans
* Pull request plans

Human engineers modify **content only**, never structure.

Templates define:

* Required sections
* Stable identifiers
* Traceability rules
* Stage-gate requirements

---

### P2. Everything Is a File Asset

There is no external system of record.

CDASE deliberately avoids:

* Issue trackers (e.g., Jira)
* Test management tools
* Architecture modeling tools
* Workflow engines

Exact engineering contracts and execution state exist as **versioned text files
inside their owning repository**, managed by Git. The Hub Global API Pool is the
source-linked discovery index across repositories; it does not replace those contracts.

The repository is:

* The requirement system
* The design system
* The test management system
* The execution log

---

### P3. AI as the Engineering Execution System

In CDASE, AI is not a coding assistant.

AI acts as an **engineering execution system**, assuming responsibility for:

| Traditional System      | CDASE Equivalent             |
| ----------------------- | ---------------------------- |
| Requirement management  | Scenario / Feature documents |
| Architecture governance | Design constraints + ADRs    |
| Test management         | Executable contract tests    |
| CI gate enforcement     | AI gate checking             |
| Consistency validation  | AI self-check and repair     |

Humans retain authority over **intent, approval, and irreversible decisions**.

---

## 3. Repository as System

In CDASE, the repository *is* the system.

A canonical requirement structure looks like:

```
cdase/
  requirements/
    index.md
    SCN-001/
      scenario.md
      FTR-01/
        feature.md
        design.md
        code-plan.md
        gates.md
        progress.md
        FUN-01/
          function.md
          design.md        # conditional
          code-plan.md
          gates.md
          progress.md
  api/
  context/
  run_log/
```

Each artifact is:

* Identified by a stable ID
* Governed by a template and colocated with its related artifacts
* Indexed for relevance
* Traceable across requirements, design, tests, and code

`feature.md` and `function.md` own stable contracts and Acceptance Criteria.
`design.md` owns design reasoning and all diagrams. `gates.md` owns gate criteria
and evidence. `progress.md` is the only mutable execution-state source.

Shared membership and trust use one committed record per user:
`cdase/context/members/<8-hex-user-id>.context.md`, containing `User ID`,
`Alias`, `Role`, and `Status: active | inactive`. Only active committed records grant
trust; Hub presence is a superset, not membership authority. There is no
`users.context.md` compatibility.

The global profile is `<GLOBAL_CDASE>/user.context.md`, where
`<GLOBAL_CDASE>` is `CDASE_GLOBAL` when set, else `~/.cdase` on macOS/Linux or
`%USERPROFILE%\.cdase` on Windows. Optional repo `context/user.context.md` is a
gitignored Alias/Role override that `boot` writes into the current user's
shared member record; commit it before trust. Settings precedence is defaults → global → repo →
environment.

Install the client with `python -m pip install .` (Windows:
`py -m pip install .`) and invoke it as `cdase ...`; use the bundled
`python3 <skill-root>/scripts/cdase_client.py ...` only as a fallback.

---

## 4. API Index Layer

To enable scalable AI reasoning, CDASE uses repository API registries plus a
Hub-backed **Global API Pool**.

**APIs are the primary coordination and discovery mechanism of the system.**

Each owning repository is authoritative for its exact contracts. The Global API
Pool is authoritative for discovering capabilities across all systems and their
source locations. It is used for:

* Legacy onboarding
* Feature planning
* Cross-team collaboration
* Anti-duplication enforcement

Every capability is searched globally before REUSE | EVOLVE | CREATE. New APIs
are reserved as `DEVELOPING`, accepted versions become `RELEASED`, and upgrades
create new versions rather than rewriting released contracts.

---

## 5. Documentation-First Reasoning

CDASE enforces a strict reasoning order:

1. Context files (`/context/*.context.md`)
2. Global API Pool search and source-linked API contracts
3. Requirements index
4. Scenario document
5. Feature definition, progress, and gates
6. Feature design
7. Function definition, progress, gates, and applicable design
8. Approved code plans
9. Tests
10. Source code (last resort)

Documentation defines **intent**.

Source code is treated strictly as an **implementation artifact**, never as a knowledge source.

---

## 6. Scenario-Driven Engineering

Humans do not describe functions.

Humans describe **scenarios, use cases, and capabilities**.

CDASE enforces:

* Scenario → Feature resolution
* Feature → Function resolution

The AI is responsible for:

* Reusing existing functions
* Creating new functions when necessary
* Versioning functions when semantics change

All resolution decisions are explicitly documented and traceable.

---

## 7. Stage Gates and Human Authority

CDASE enforces **mandatory stage gates** across the engineering lifecycle:

* Requirement
* Design
* Development
* Test
* Acceptance

Progress is blocked unless the current gate is satisfied.

At defined **HARD STOP** points, human users must explicitly choose one action:

* Approve and proceed
* Approve and stop
* Assign to a person or role
* Request changes
* Pause execution

AI autonomy is **strictly bounded** by these approvals.

---

## 8. Tests as Contracts

Acceptance criteria are treated as **behavioral contracts**.

For every Feature and Function:

* Each acceptance criterion must map to executable test code
* Textual descriptions are insufficient
* Failing tests block gate progression

Tests are not documentation—they are enforcement mechanisms.

---

## 9. Controlled Code Generation

Code generation is considered an **irreversible execution step**.

CDASE enforces:

* Explicit approval before any executable artifact is generated
* Strict file-level scope control via Code Plans
* Atomic execution of tests and code generation after approval

Unapproved or speculative code generation is forbidden.

---

## 10. Scope and Non-Goals

CDASE does **not** claim to:

* Replace human intent or decision-making
* Optimize algorithms or code quality automatically
* Eliminate design trade-offs
* Enable fully autonomous software creation

CDASE focuses exclusively on:

* Process control
* Traceability
* Safety
* Maintainability

---

## 11. Summary

CDASE reframes software engineering as a **context-governed execution problem**.

By making structured documentation the single source of truth and assigning enforcement responsibility to AI, CDASE removes the need for external workflow systems while preserving human authority and auditability.

CDASE is not a faster way to code.

It is a safer way to evolve software with AI.
