# Code Plan: FUN-XXX-YY-ZZ

> Copy to `/cdase/requirements/SCN-XXX/FTR-YY/FUN-ZZ/code-plan.md`.
> This is the approved, file-bounded implementation plan for one Function.

## 0. Plan Metadata
- Function: FUN-XXX-YY-ZZ (`function.md`)
- Design Coverage: `../design.md` or `design.md`
- Plan Version: v0.1
- Frozen Contracts: [AC-01, AC-02, ...]
- Approved By: <engineer>
- Approved At: <YYYY-MM-DD HH:mm>

## 1. Change Scope

### Allowed Files
- <repo-relative file>

### Forbidden Areas
- Any file not listed above
- Frozen APIs/SPIs and ACs unless execution returns to Requirement

## 2. Implementation Steps
1. <small, reversible change>
2. ...

## 3. Risk Controls
- RP-01: <risk> → <control>

## 4. Test Plan
- Contract: `<test path>::test_FUN_XXX_YY_ZZ_AC_01_*`
- Integration: ...
- Regression: ...

## 5. Rollback Strategy
- ...

## 6. Completion Evidence
- Commit/PR: ...
- Test run: ...
- Gate evidence: `gates.md`
