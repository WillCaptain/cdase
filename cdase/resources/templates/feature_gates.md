# Gates: FTR-XXX-YY

> Copy to `/cdase/requirements/SCN-XXX/FTR-YY/gates.md`.
> This is the only Feature gate checklist. Checkboxes are criteria; the Evidence
> tables prove completion. Current stage/status/owner belong only in `progress.md`.
> A gate passes only when every required item is checked and evidence is linked.

## Requirement Gate
- [ ] `feature.md` conforms to the Feature template.
- [ ] Scope, numbered journey, inputs, outputs, and invariants are explicit.
- [ ] Function resolution is complete (REUSE / NEW / EVOLVE with full IDs).
- [ ] Global API Pool was searched with capability, synonyms, and proposed signature.
- [ ] Search query, candidates, scores, lifecycle states, and source links are recorded below.
- [ ] Candidate contracts were verified in their owning repositories.
- [ ] Every capability resolves to REUSE, EVOLVE, or CREATE; no duplicate exists.
- [ ] Every CREATE/EVOLVE API is globally reserved as `DEVELOPING` via `api-sync`.
- [ ] For `LEGACY_IMPORT`: isolated scan, confidence, explicit approval,
      committed provenance, and selected-only registry generation are verified.
- [ ] Every FAC is stable, numbered, and testable.

### Evidence
| Criterion | Artifact / Section | Result |
|---|---|---|
| Feature contract | `feature.md` | ... |
| Global API search | `api-search "<query>"` | candidates + REUSE/EVOLVE/CREATE |
| API reservation | `<module>.api.md` + Global API Pool ID/version | ... |
| Legacy import (conditional) | scan ID + approval ref + discovery evidence | ... |

## Design Gate
- [ ] Mandatory `design.md` conforms to the Feature Design template.
- [ ] `design.md` covers every journey step and Function.
- [ ] All relevant diagrams are included in `design.md`.
- [ ] Main, error, and edge flows are designed.
- [ ] Every FAC maps to a design section and verification target.
- [ ] API/SPI boundaries are explicit and frozen for implementation.
- [ ] Decisions, risks, trade-offs, and open questions are resolved or explicitly blocked.

### Evidence
| Criterion | Artifact / Section | Result |
|---|---|---|
| Design | `design.md` | ... |

## Development Gate
- [ ] `code-plan.md` is approved and limits allowed files.
- [ ] Every impacted Function has passing Requirement and Design gates.
- [ ] Contract/acceptance tests exist for the implementation segment.
- [ ] No implementation step changes a frozen contract without returning to Requirement.

### Evidence
| Criterion | Artifact / Section | Result |
|---|---|---|
| Approved plan | `code-plan.md` | ... |

## Test Gate
- [ ] Every FAC maps to at least one executable test.
- [ ] All impacted Function contract tests pass.
- [ ] Feature acceptance/integration tests pass.
- [ ] Regression risks have test evidence.

### Evidence
| FAC / Risk | Test | Result |
|---|---|---|
| FAC-01 | `<test>` | Pass / Fail |

## Acceptance Gate
- [ ] All FACs are verified.
- [ ] Documentation, API registry, tests, design, and code are synchronized.
- [ ] Delivered APIs are `RELEASED`; replaced versions are `SUPERSEDED`.
- [ ] Global Pool content hashes/source revisions match owning registries.
- [ ] All child Function progress files are closed or explicitly excluded.
- [ ] User approval is recorded.
- [ ] `progress.md` and `/cdase/requirements/index.md` are updated.

### Evidence
| Criterion | Artifact / Decision | Result |
|---|---|---|
| User approval | <reference> | ... |
