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

Instead, all engineering truth exists as **versioned text files inside a single repository**, managed by Git.

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

A typical structure looks like:

```
/requirements
  /scenarios
    SCN-001-*.md
  /features
    FTR-001-*.md
  /functions
    FUN-034-*.md

/design
  /uml
    FTR-001.sequence.puml
    FTR-001.class.puml
  /adr
    ADR-005.md

/tests
  /contract
    FUN-034_test.py

/context
  module.context.md
  user.context.md
```

Each artifact is:

* Identified by a stable ID
* Governed by a template
* Indexed for relevance
* Traceable across requirements, design, tests, and code

---

## 4. Context Index Layer

To enable scalable AI reasoning, CDASE introduces a **Context Index Layer**.

Index files provide a compact, structured overview of:

* Scenarios
* Features
* Functions

The AI must consult index files *before* loading detailed artifacts, enabling:

* Relevance-based context expansion
* Token-efficient reasoning
* Deterministic artifact discovery

Indexes are derived assets and are automatically maintained by the AI.

---

## 5. Documentation-First Reasoning

CDASE enforces a strict reasoning order:

1. Context files (`/context/*.context.md`)
2. Scenario index
3. Feature index
4. Function index
5. Scenario documents
6. Feature documents
7. Function documents
8. Design artifacts
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
