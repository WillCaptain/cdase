# Function Resolution Rule

For each capability implied by a Feature:

- Search the Global API Pool by semantics, exact identifiers, proposed
  signatures, synonyms, inputs, outputs, and side effects.
- Verify candidate contracts in their source-linked owning repositories.
- Search existing local Function documents by semantics, not names.
- Decide exactly one:
  - Reuse
  - New
  - Version Evolution

Partial semantic mismatch REQUIRES version evolution.

NEW MUST be globally reserved as `DEVELOPING` before implementation. Version
Evolution MUST create a new version and must not rewrite a released contract.

All queries, candidates, scores, source links, and decisions MUST be logged in
Feature `gates.md`.
