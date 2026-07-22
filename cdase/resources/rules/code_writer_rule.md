You generate code ONLY within allowed boundaries.

Rules:
1. You may only modify files listed in the approved Feature/Function
   `code-plan.md` files.
2. You may NOT change APIs, SPIs, or data structures without explicit permission.
3. You must not break any existing contract tests.
4. If an existing test fails, you must either:
   - fix the implementation
   - or update documentation AND tests together
5. Before coding, verify the Development Gate in `gates.md` and current state in
   `progress.md`.
6. After coding/testing, write evidence to `gates.md` and mutable state only to
   `progress.md`.

Small, safe, reversible changes are mandatory.
