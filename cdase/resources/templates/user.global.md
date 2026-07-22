# Global User Profile

> Set once at `<GLOBAL_CDASE>/user.context.md`.
> `<GLOBAL_CDASE>` is `CDASE_GLOBAL` when set, otherwise `~/.cdase` on
> macOS/Linux or `%USERPROFILE%\.cdase` on Windows.
> Template: [user.global.md](user.global.md) (this file)
>
> **User id = this machine** (`sha256(machine_id)[:8]`).
> Alias/Role here are defaults. A gitignored repo `user.context.md` may override
> them; `boot` writes the result into that repo's shared member record, which
> must be committed before it grants trust.

## Identity
- Name: [your default display name; published as member Alias]
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
