# Gates: FUN-XXX-YY-ZZ

> Copy to `/cdase/requirements/SCN-XXX/FTR-YY/FUN-ZZ/gates.md`.
> This is the only Function gate checklist. Current stage/status/owner belong
> only in `progress.md`.

## Requirement Gate
- [ ] `function.md` conforms to the Function template.
- [ ] Single responsibility, inputs, output, errors, and invariants are explicit.
- [ ] Global API Pool was searched with capability, synonyms, and proposed signature.
- [ ] Search query, candidates, scores, lifecycle states, and source links are recorded below.
- [ ] Candidate contracts were verified in their owning repositories.
- [ ] Resolution is REUSE, EVOLVE, or CREATE; no duplicate capability exists.
- [ ] CREATE/EVOLVE is globally reserved as `DEVELOPING` via `api-sync`.
- [ ] For `LEGACY_IMPORT`: isolated scan, confidence, explicit approval,
      committed provenance, and selected-only registry generation are verified.
- [ ] Every AC is stable, numbered, and testable.

### Evidence
| Criterion | Artifact / Section | Result |
|---|---|---|
| Function contract | `function.md` | ... |
| Global API search | `api-search "<query>"` | candidates + decision |
| API reservation | `<module>.api.md` + Global API Pool ID/version | ... |
| Legacy import (conditional) | scan ID + approval ref + discovery evidence | ... |

## Design Gate
- [ ] Function is mapped in parent `../design.md`.
- [ ] Parent design fully covers the Function, **or** a justified `design.md` exists.
- [ ] If Function `design.md` exists, all Function diagrams are included there.
- [ ] API/SPI boundary is explicit and frozen.
- [ ] Every AC maps to a design section and test target.
- [ ] Error, state, concurrency, and security concerns are covered when relevant.

### Evidence
| Criterion | Artifact / Section | Result |
|---|---|---|
| Design coverage | `../design.md` or `design.md` | ... |

## Development Gate
- [ ] `code-plan.md` is approved and limits allowed files.
- [ ] Contract tests exist for every AC.
- [ ] Implementation does not alter frozen contracts.

### Evidence
| Criterion | Artifact / Section | Result |
|---|---|---|
| Approved plan | `code-plan.md` | ... |

## Test Gate
- [ ] Every AC maps to at least one executable test.
- [ ] All Function contract tests pass.
- [ ] Regression risks have test evidence.

### Evidence
| AC / Risk | Test | Result |
|---|---|---|
| AC-01 | `<test>` | Pass / Fail |

## Acceptance Gate
- [ ] All ACs are verified.
- [ ] Contract, tests, code, design, and API registry are synchronized.
- [ ] Delivered API version is `RELEASED`; replaced version is `SUPERSEDED`.
- [ ] Global Pool content hash/source revision matches the owning registry.
- [ ] User/Feature approval is recorded when required.
- [ ] `progress.md` and `/cdase/requirements/index.md` are updated.

### Evidence
| Criterion | Artifact / Decision | Result |
|---|---|---|
| Approval | <reference> | ... |
