> NOTE:
> The Stage Ownership table is the single source of truth
> for execution state, ownership, and task discovery.
> AI MUST NOT infer stage state from any other fields.

# Feature: FTR-XXX <Feature Title>

## 0. Metadata
- ID: FTR-XXX
- SCN ID: SCN-XXX
- Steward: <name/team>   # long-term product/tech owner, NOT stage executor
- Group/Module: <group>/<module>
- Priority: <P0|P1|P2>
- Version: v0.1
- Last Updated: <YYYY-MM-DD>
- Resolution Status: <Draft | Stable | Deprecated>
- Depends On: [FTR-???], [FUN-???]
- Users / Stakeholders: <who benefits>
-----------------------------------------------------------------------------------------
## 1. API / SPI Contract (Frozen Boundary)
> API is what callers use. SPI is interface to be implemented for calling back.

### API (Provided)
- `<module>.<class>.<method>(<params>) -> <return>` or REST/CLI/SDK
  - Params: ...
  - Returns: ...
  - Throws: ...
  - Notes: ...

### SPI (For Implementation)
- `<module>.<class>.<interface>(...) -> ...` or REST/CLI/SDK event
  - Params: ...
  - Returns: ...
  - Throws: ...
  - Notes: ...
  - Trigger Condition: ...
-----------------------------------------------------------------------------------------

## 2. Stage Ownership and Execution State

> This table is the single source of truth for Feature execution state.

| Stage        | Status       | Owner        | Assigned At        | Last Updated       | Completed At       | Blocked Reason |
|--------------|--------------|--------------|--------------------|--------------------|--------------------|----------------|
| Requirement  | Done         | Alice        | 2025-01-15 09:00   | 2025-01-15 10:00   | 2025-01-15 10:00   | -              |
| Design       | InProgress   | Bob          | 2025-01-15 10:01   | 2025-01-15 11:30   | -                  | -              |
| Development  | NotStarted   | -            | -                  | -                  | -                  | -              |
| Test         | NotStarted   | -            | -                  | -                  | -                  | -              |
| Acceptance   | NotStarted   | -            | -                  | -                  | -                  | -              |


## 3. Summary (One Paragraph)
<What user problem it solves and what value it provides.>

## 4. Scope
### In Scope
- ...

### Out of Scope
- ...

## 5. User Journey / Flow (Text)
> Describe the feature as an ordered flow. Later it must match the sequence diagram.
1. Step 1 ...
2. Step 2 ...
3. Step 3 ...

## 6. Inputs / Outputs (Feature-level)
> Feature-level I/O can be higher-level than Function I/O, but must be explicit.
### Inputs
- ...

### Outputs
- ...

## 7. Functional Composition (Functions)
> The feature is composed by Functions in a flow order.
- FUN-001: <title> (role in flow: ...)
- FUN-002: ...

## 8. Acceptance Criteria (Feature-level)
> Feature-level ACs verify end-to-end behavior.
- FAC-01: Given ... When ... Then ...
- FAC-02: ...

## 9. Design Artifacts Index
- Sequence Diagram: `/design/uml/FTR-XXX.sequence.puml`
- Package/Class Diagram: `/design/uml/FTR-XXX.class.puml`
- ADRs: `/design/adr/ADR-???.md`

## 10. Test & Acceptance Index
- Feature-level acceptance tests: `/tests/feature/test_FTR-XXX_*.py`
- Related Function tests: see individual Function documents

## 11. Gate Checklist (AI MUST enforce)
### Requirement Gate
- [ ] Flow written and numbered
- [ ] Feature-level I/O explicit
- [ ] Functions list complete (IDs)
- [ ] FACs are testable and numbered

### Design Gate
- [ ] Sequence diagram covers all steps
- [ ] Class/package diagram exists (if needed)
- [ ] All Functions have frozen API/SPI
- [ ] Trace links valid

### Development Gate
- [ ] Each Function has contract tests indexed
- [ ] Code plans exist for impacted Functions

### Test Gate
- [ ] All Function contract tests pass
- [ ] All Feature contract tests pass

### Acceptance Gate
- [ ] FACs verified by executable tests
- [ ] Trace links valid and complete

## 12. Capability Resolution Log

| Step | Capability | Resolution | Function | Version | Notes |

