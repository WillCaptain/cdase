# Global CDASE Settings

> Copied once to `<GLOBAL_CDASE>/setting.context.md`.
> `<GLOBAL_CDASE>` is `CDASE_GLOBAL` when set, otherwise `~/.cdase` on
> macOS/Linux or `%USERPROFILE%\.cdase` on Windows.
> Skill template: `cdase/resources/templates/setting.context.md` — agent copies this file on first boot.
> Repo `cdase/context/setting.context.md` may override per project.
> Resolution order: defaults → global → repo → environment.
> Knowledge-database provider/URL is configured on CDASE Hub only. Never add it
> to this client setting.

## Hub
- Address: https://12th.ai/cdase
- OfflineOk: true

## Client
- Path: auto

## Messaging
- FromActor: agent
- AgentAutonomy: delegated
- AutoReplyToAgentQuestions: true
