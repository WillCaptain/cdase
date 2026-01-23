# Submodule API Registry (eg:auth)

| Signature (The Reference String) | Description | Source ID | Status(Proposed, in_progress, Materialized, Frozen) |
| :--- | :--- | :--- | :--- |
| `auth.service.verify(token: str)` | Validates JWT & returns User object | FUN-001 | Frozen |
| `auth.service.get_perms(uid: UUID)` | Returns list of user permission strings | FUN-008 | Proposed |

### Details
- **auth.service.verify**:
  - *Returns*: `User { id: UUID, roles: list }`
  - *Exceptions*: `ExpiredTokenError`, `InvalidSignatureError`