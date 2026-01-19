# Function: FUN-XXX <Function Title>

## 0. Metadata
- ID: FUN-XXX
- Owner: <name/team>
- Group/Module: <group>/<module>
- Stage: <Requirement|Design|Development|Test|Acceptance>
- Status: <NotStarted|InProgress|Done|Blocked>
- Stability: <Experimental | Stable | Frozen>
- Priority: <P0|P1|P2>
- Version: v0.1
- Last Updated: <YYYY-MM-DD>
- Depends On: [FUN-???], [FTR-???]
- Affects: <modules/files list or TBD>

## 1. Summary (One Paragraph)
<What capability this function provides, and why it exists.>

## 2. Scope
### In Scope
- ...

### Out of Scope
- ...

## 3. Inputs (Enumerated)
> Each input must be explicit, typed, constrained, and exemplified.

| Name | Type | Required | Constraints | Example |
|------|------|----------|-------------|---------|
|      |      |          |             |         |

## 4. Outputs (Enumerated)
| Name | Type | Guaranteed | Constraints | Example |
|------|------|------------|-------------|---------|
|      |      |            |             |         |

## 5. Preconditions & Postconditions
### Preconditions
- ...

### Postconditions
- ...

## 6. Acceptance Criteria (Testable Contract)
> MUST be testable. Each AC has stable ID: AC-01, AC-02...

- AC-01: <Given/When/Then style>
- AC-02: ...
- AC-03: ...

## 7. Error Handling & Edge Cases
- E-01: <condition> -> <error/behavior>
- E-02: ...

## 8. API / SPI Contract (Frozen Boundary)
> API is what callers use. SPI is what this function calls/relies on.

### API (Provided)
- `<module>.<class>.<method>(<params>) -> <return>`
  - Params: ...
  - Returns: ...
  - Throws: ...
  - Notes: ...

### SPI (Required/Called)
- `<module>.<class>.<method>(...) -> ...`
  - Why needed: ...
  - Failure strategy: ...

## 9. Design Notes (Optional, but required after Design gate)
- Data model notes: ...
- Sequence notes: ...

## 10. Contract Tests Index (MUST be synced with /tests)
> Tests are derived from Acceptance Criteria. Test names MUST be stable:
> `test_FUN_XXX_AC_01_<slug>`

### Test File
- Path: `/tests/contract/test_FUN_XXX.py` (or language equivalent)

### Test Cases
| AC ID | Test Name | Description | Input Set | Expected Output |
|------|-----------|-------------|-----------|-----------------|
| AC-01 | test_FUN_XXX_AC_01_<slug> | ... | ... | ... |
| AC-02 | test_FUN_XXX_AC_02_<slug> | ... | ... | ... |

## 11. Gate Checklist (AI MUST enforce)
### Requirement Gate
- [ ] Inputs/Outputs complete
- [ ] ACs are testable and numbered
- [ ] Edge cases listed

### Design Gate
- [ ] API/SPI frozen and explicit
- [ ] Linked sequence diagram exists (if belongs to a Feature flow)
- [ ] Risks documented

### Development Gate
- [ ] Contract tests generated and indexed here

### Test Gate
- [ ] All contract tests pass
- [ ] Regression checklist pass (if exists)

### Acceptance Gate
- [ ] All contract tests pass
- [ ] Trace links complete

## 12. Trace Links (Repo-local, MUST stay valid)
- Feature: `/requirements/feature/FTR-???.md`
- Sequence: `/design/uml/FTR-???.sequence.puml`
- Tests: `/tests/contract/test_FUN_XXX.py`
- Code Entry: `<module>.<class>.<method>` + file path
- Code Plan: `/requirements/function/FUN-XXX.plan.md`
- ADR (if any): `/design/adr/ADR-???.md`

## 13. Risks & Non-Breakable Invariants
- R-01: <risk> (how to detect: <test/log/assert>)
- INV-01: <must never happen> (how enforced: <test/assert>)

### 14. Version History
- v0.1
  - Type: Initial | Extension | Breaking
  - Summary:
  - Changed ACs:
  - Introduced Risks:

## 15. Referenced By

