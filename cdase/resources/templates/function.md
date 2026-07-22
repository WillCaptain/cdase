# Function: FUN-XXX-YY-ZZ — <Function Title>

> Canonical path:
> `/cdase/requirements/SCN-XXX/FTR-YY/FUN-ZZ/function.md`
> This file is the stable Function contract. Execution state belongs only in
> `progress.md`; gates belong only in `gates.md`. `design.md` is required only
> when the parent Feature design does not fully specify this Function.

## 0. Metadata
- ID: FUN-XXX-YY-ZZ
- Feature: FTR-XXX-YY (`../feature.md`)
- Steward: <8-hex-user-id> (<project-alias>)
- Group/Module: <group>/<module>
- Priority: <P0|P1|P2>
- Version: v0.1
- Stability: <Experimental | Stable | Frozen | Deprecated>
- Last Updated: <YYYY-MM-DD>

## 1. Summary
<One paragraph: single responsibility and caller value.>

## 2. Contract

### API / Method
- Global API Pool ID: `<organization/system/module/operation>`
- Version / Status: `<version>` / `<DEVELOPING | RELEASED | SUPERSEDED | DEPRECATED | RETIRED>`
- Signature: `<module>.<class>.<method>(<params>) -> <return>` or REST/CLI/SDK
- Purpose: ...
- Inputs:
  - `<name>: <type>` — <constraints>
- Output: `<type>` — <meaning>
- Errors:
  - `<error>` — <condition>

### SPI / Dependencies
> Every external dependency MUST be found in the Global API Pool and verified
> against its owning repository contract. Direct and indirect self-dependencies
> are forbidden.

- `<address/signature>` — owner: <FTR/FUN ID>; purpose: ...

## 3. Acceptance Criteria
> These criteria are the Function behavioral contract and remain in `function.md`.
> Each stable AC ID MUST map to at least one executable contract test.

- AC-01: Given ... When ... Then ...
- AC-02: ...

## 4. Error Handling and Edge Cases
- E-01: <condition> → <error/behavior>
- E-02: ...

## 5. Constraints and Invariants
- C-01: ...
- INV-01: <must never happen>; enforced by: <test/assertion>

## 6. Contract Test Index

| AC ID | Test Name | Test Path |
|---|---|---|
| AC-01 | `test_FUN_XXX_YY_ZZ_AC_01_<slug>` | `<repo-relative path>` |

## 7. Trace Links
- Parent Feature Design: `../design.md`
- Function Design: `design.md` or `Covered by ../design.md`
- Gates: `gates.md`
- Progress: `progress.md` (**execution-state SSOT**)
- Code Plan: `code-plan.md`
- Code Entry: `<address + repo-relative path>`
- API registry: `/cdase/api/...`

## 8. Version History

| Version | Change Type | Summary | Changed ACs | Risks |
|---|---|---|---|---|
| v0.1 | Initial | ... | AC-01 | ... |

## 9. Referenced By
- FTR-...


