# Global User Profile

> Set once at `~/.cdase/user.context.md` (or `$CDASE_GLOBAL/user.context.md`).
> Windows: `%USERPROFILE%\.cdase\user.context.md`. Legacy: `~/.cursor/cdase` if `~/.cdase` absent.
> Template: [user.global.md](user.global.md) (this file)
>
> **User id = this machine** (`sha256(machine_id)[:8]` in each repo roster).
> `Name` here is the default display name when this machine first joins a repo.
> Per-repo Name in `users.context.md` may differ without changing this file.

## Identity
- Name: [your name]
- Role: [optional default role]
- Team: [optional]
- Organization: [optional]

## Capabilities
- CanApprove: true
- CanAssign: true
- CanClaim: true

## Preferences (Optional)
- WorkingHours: 09:00-18:00
- PrimaryLanguage: en
