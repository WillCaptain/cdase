# Feature: FTR-XXX-YY — <Feature Title>

> Canonical path: `/cdase/requirements/SCN-XXX/FTR-YY/feature.md`
> This file is the stable feature definition. Execution state belongs only in
> `progress.md`; gate criteria/evidence belong only in `gates.md`; implementation
> design and all diagrams belong only in `design.md`.

## 0. Metadata
- ID: FTR-XXX-YY
- Scenario: SCN-XXX (`../scenario.md`)
- Steward: <8-hex-user-id> (<project-alias>)
- Group/Module: <group>/<module>
- Priority: <P0|P1|P2>
- Version: v0.1
- Stability: <Draft | Stable | Frozen | Deprecated>
- Last Updated: <YYYY-MM-DD>

## 1. Summary
<One paragraph: user problem, capability, and value.>

## 2. Scope

### In Scope
- ...

### Out of Scope
- ...

## 3. User Journey
> Number every observable step. Reference a Function ID when that Function
> owns the behavior. `design.md` MUST cover every step.

1. <step> `[FUN-XXX-YY-ZZ]`
2. ...

## 4. Feature Inputs and Outputs
- Inputs: ...
- Outputs: ...
- Observable side effects: ...

## 5. Functional Composition

| Resolution | Function ID | Folder | Responsibility | Version |
|---|---|---|---|---|
| REUSE / NEW / EVOLVE | FUN-XXX-YY-ZZ | `FUN-ZZ/` | ... | v0.1 |

## 6. API and SPI Boundary
> Search the Global API Pool before defining a capability, then verify candidate
> contracts in their owning repositories. Record REUSE / EVOLVE / CREATE and
> Global Pool API IDs/versions. CREATE/EVOLVE MUST be reserved as `DEVELOPING`.

### Provided API
- `<global-api-id>@<version>` — `<address/signature>` — <purpose/status>

### Required SPI / External API
- `<address/signature>` — <purpose>; owner: <FTR/FUN ID>

## 7. Acceptance Criteria
> These criteria are the Feature behavioral contract and remain in `feature.md`.
> Each stable FAC ID MUST map to executable acceptance tests and Design coverage.

- FAC-01: Given ... When ... Then ...
- FAC-02: ...

## 8. Constraints and Invariants
- C-01: ...
- INV-01: ...

## 9. Trace Links
- Design: `design.md` (**required**)
- Gates: `gates.md`
- Progress: `progress.md` (**execution-state SSOT**)
- Code Plan: `code-plan.md`
- Feature tests: `<repo-relative test path>`
- API registry: `/cdase/api/...`
- ADRs: <paths or `None`>

## 10. Modification Requests (Optional)

| From | Requested By | Description | Resolution |
|---|---|---|---|
| FTR-... | <user> | ... | Open / Accepted / Rejected |


