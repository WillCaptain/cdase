# Code Plan: FUN-XXX

## 0. Plan Metadata
- Function ID: FUN-XXX
- Plan Version: v0.1
- Author: AI
- Frozen Contracts: [AC-01, AC-02, ...]
- Approved By: <engineer>
- Date: <YYYY-MM-DD>


## 1. Change Scope (STRICT)
### Allowed Files
- <file1>
- <file2>

### Forbidden Areas (DO NOT TOUCH)
- <core domain>
- <shared libs>
- <anything not listed>
- Any file not listed above
- Any API/SPI marked as frozen in Function documentation

## 2. Implementation Steps (Small Diffs)
1. ...
2. ...
3. ...

## 3. Risk Points
- RP-01: ...
- RP-02: ...

## 4. Test Plan
- Must run:
  - `/tests/contract/test_FUN_XXX.py::test_FUN_XXX_AC_01_*`
  - regression: ...

## 5. Rollback Strategy
- Revert commits: ...
- Feature flags: ...
