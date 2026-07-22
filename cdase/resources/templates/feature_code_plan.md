# Code Plan: FTR-XXX-YY

> Copy to `/cdase/requirements/SCN-XXX/FTR-YY/code-plan.md`.
> This plan coordinates the Feature-level integration segment. Detailed internal
> changes belong in each impacted Function's `code-plan.md`.

## 0. Plan Metadata
- Feature: FTR-XXX-YY (`feature.md`)
- Design: `design.md`
- Plan Version: v0.1
- Frozen Contracts: [FAC-01, FAC-02, ...]
- Impacted Functions: [FUN-XXX-YY-ZZ, ...]
- Approved By: <engineer>
- Approved At: <YYYY-MM-DD HH:mm>

## 1. Change Scope

### Allowed Files
- <repo-relative file>

### Forbidden Areas
- Any file not listed above
- Frozen APIs/SPIs and ACs unless execution returns to Requirement

## 2. Function Plan Index

| Function ID | Plan | Responsibility |
|---|---|---|
| FUN-XXX-YY-ZZ | `FUN-ZZ/code-plan.md` | ... |

## 3. Integration Steps
1. ...
2. ...

## 4. Test Plan
- Feature acceptance tests: ...
- Function contract tests: ...
- Integration/regression tests: ...

## 5. Risk Controls
- RP-01: <risk> → <control>

## 6. Rollback Strategy
- ...

## 7. Completion Evidence
- Commit/PR: ...
- Test run: ...
- Gate evidence: `gates.md`
