# Root API Index

> **Authority**: Constitution §III.2
> **Purpose**: Map this repository's systems/modules to canonical API registries.
> The Global API Pool aggregates these registries for cross-system discovery.

| System | Module | Responsibility | Registry Path |
|---|---|---|---|
| billing | invoice | Invoice creation and lifecycle | `/cdase/api/modules/invoice.api.md` |

## Global Pool Rules

- Before Feature/Function resolution, run `api-search` globally.
- Every CREATE decision adds a `DEVELOPING` API block to its module registry and
  runs `api-sync` before implementation.
- Contract changes update the block and run `api-sync`; released contracts
  require a new version.
- Acceptance transitions the new version to `RELEASED`.
- Repository registry = contract authority; Global API Pool = discovery authority.