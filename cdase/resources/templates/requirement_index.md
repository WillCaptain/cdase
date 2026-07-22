# Requirements Index

> Canonical path: `/cdase/requirements/index.md`
> This is the discovery index, not an independent workflow database.
> Feature/Function Stage, Status, and Owner MUST be copied from their
> `progress.md`; any mismatch is a gate failure.

Only Features/Functions whose indexed `progress.md` Status is not `Done` are
active execution tasks. Scenarios provide grouping and intent.

---

## Scenarios

| Scenario ID | Description | Resolution | Path |
|---|---|---|---|
| SCN-001 | one sentence | Stable | `SCN-001/scenario.md` |

---

## Features

| Feature ID | Description | Stage | Status | Owner | Path |
|---|---|---|---|---|---|
| FTR-001-01 | one sentence | Design | InProgress | a1b2c3d4 (will) | `SCN-001/FTR-01/` |

---

## Functions

| Function ID | Description | Stage | Status | Owner | Path |
|---|---|---|---|---|---|
| FUN-001-01-01 | one sentence | Requirement | NotStarted | - | `SCN-001/FTR-01/FUN-01/` |

## Consistency Rules
- Full IDs remain globally unambiguous; folders use local suffixes (`FTR-YY`, `FUN-ZZ`).
- Every Feature folder contains `feature.md`, `design.md`, `code-plan.md`,
  `gates.md`, and `progress.md`.
- Every Function folder contains `function.md`, `code-plan.md`, `gates.md`, and
  `progress.md`; `design.md` is conditional.
- Update this index atomically whenever an artifact is created or its
  `progress.md` current state changes.
