# CDASE Settings (repo overrides)

> Optional per-project overrides. Omit sections to inherit from global
> `~/.cdase/setting.context.md`.
> Template: [setting.md](setting.md) (this file)

## Project
- RepoId: [stable team key for cdase-hub, e.g. github.com/org/my-app — auto from git remote if omitted]

## Hub
- Address: [only if different from global hub]
- OfflineOk: true

## Client
- Path: auto

## Messaging
- FromActor: agent
- AgentAutonomy: delegated
- AutoReplyToAgentQuestions: true
