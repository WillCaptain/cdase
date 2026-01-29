> NOTE:
> The Stage Ownership table is the single source of truth
> for execution state, ownership, and task discovery.
> AI MUST NOT infer stage state from any other fields.
> all information should be short, concise, accurate

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
- Depends On: 
  - Only APIs defined outside the current Feature scope.
  - Each dependency MUST be an explicit API address (e.g., package.Class.method) suitable for direct code reference.
  - Belong Function/Feature Id followed the API address.
  - **VERY IMPORTANT: Self-dependencies (direct or indirect) are strictly forbidden.**

-----------------------------------------------------------------------------------------
## 1. Summary (One Paragraph)
<What user problem it solves and what value it provides.>

## 2. API / SPI Contract (Frozen Boundary)
> API is what callers use. SPI is interface to be implemented for calling back.
> MUST not duplicate existing apis in `\api\`
### API (Provided)
- `<module>.<class>.<method>(<params>) -> <return>` or REST/CLI/SDK
  - description: simply but accurate
  - Params: ...
  - Returns: ...
  - Throws: ...


### SPI (For Implementation)
- `<module>.<class>.<interface>(...) -> ...` or REST/CLI/SDK event
  - description: ...
  - Params: ...
  - Returns: ...
  - Throws: ...
  - Trigger Condition: ...
-----------------------------------------------------------------------------------------

## 3. Stage Ownership and Execution State

> This table is the single source of truth for Feature execution state.

| Stage        | Status       | Owner        | Assigned At        | Last Updated       | Completed At       | Blocked Reason |
|--------------|--------------|--------------|--------------------|--------------------|--------------------|----------------|
| Requirement  | Done         | Alice        | 2025-01-15 09:00   | 2025-01-15 10:00   | 2025-01-15 10:00   | -              |
| Design       | InProgress   | Bob          | 2025-01-15 10:01   | 2025-01-15 11:30   | -                  | -              |
| Development  | NotStarted   | -            | -                  | -                  | -                  | -              |
| Test         | NotStarted   | -            | -                  | -                  | -                  | -              |
| Acceptance   | NotStarted   | -            | -                  | -                  | -                  | -              |

## 4. User Journey / Flow (Text)
> Describe the feature as an ordered flow. Later it must match the sequence diagram.
> if a step matches a function, put [FUN-XXX] in the step for reference
1. Step 1 ...
2. Step 2 ...
3. Step 3 ...

## 5. Functional Composition (Functions)
> The feature is composed by Functions in a flow order. these functions need to be modified in this feature

| Type | ID | Title | Description | Version |
|------|----|-------|-------------|--------|
| [REUSE] | FUN-001 | ... | ... | ...|
| [NEW] | FUN-002 | .. | .. | .. |

## 6. Acceptance Criteria (Feature-level)
> Feature-level ACs verify end-to-end behavior, short but accurate
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
- [ ] Required APIs discovered in `/api/modules/*.api.md`.
- [ ] No duplicate logic exists in current API Registries.

### Requirement Gate
- [ ] Flow written and numbered
- [ ] Feature-level I/O explicit
- [ ] Functions list complete (IDs)
- [ ] FACs are testable and numbered

### Design Gate
- [ ] Sequence diagram covers all steps
- [ ] Class/package diagram exists (if needed)
- [ ] All Functions have frozen API/SPI

### Development Gate
- [ ] Each Function has contract tests indexed
- [ ] Code plans exist for impacted Functions

### Test Gate
- [ ] All Function contract tests pass
- [ ] All Feature contract tests pass

### Acceptance Gate
- [ ] FACs verified by executable tests

## 12. Modification Requests
> don't add this section if there is not Modification Requests
- From: FTR-***
- Requested by: <user>
- Description: ...
- Status: Open | Accepted | Rejected


