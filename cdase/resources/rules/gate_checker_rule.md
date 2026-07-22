You are responsible for enforcing stage gates.

Before performing ANY action (design, coding, testing),
you MUST:

1. Resolve the canonical artifact folder from `/cdase/requirements/index.md`.
2. Read `progress.md` for the current Stage, Status, Owner, and blockers.
3. Read `gates.md` for the applicable checklist and linked evidence.
4. Read the applicable Feature/Function definition and `design.md`.

Never infer execution state from `feature.md`, `function.md`, `design.md`, a
conversation, or source code. Never duplicate a gate checklist outside `gates.md`.

For each stage, required artifacts are:

REQUIREMENT:
- Inputs/Outputs fully enumerated
- Acceptance Criteria defined and testable in `feature.md` / `function.md`
- Global API Pool search evidence is complete
- Candidate source contracts are verified
- REUSE / EVOLVE / CREATE is explicit
- CREATE/EVOLVE API versions are globally reserved as `DEVELOPING`

DESIGN:
- Feature `design.md` exists (mandatory)
- Function design is covered by the parent, or Function `design.md` exists
- API/SPI explicitly defined
- Every relevant diagram is included in the applicable `design.md`
- AC-to-design coverage is complete

DEVELOPMENT:
- Contract tests exist
- Applicable Feature/Function `code-plan.md` exists and is approved

TEST:
- All acceptance criteria mapped to test cases
- Regression risks documented
- Required tests pass

ACCEPTANCE:
- Definitions, design, APIs, tests, and code are synchronized
- Delivered APIs are `RELEASED`; replaced versions are `SUPERSEDED`
- Global Pool source revision/content hash matches the owning registry
- Gate evidence and explicit approval are recorded

If any artifact is missing or incomplete:
- DO NOT proceed
- Generate the missing artifact
- Record evidence in `gates.md`
- Update mutable state only in `progress.md`
- Ask for confirmation before continuing
