# CDASE Hub

## Monorepo layout

```
<methodology-repo>/
├── cdase/
│   ├── SKILL.md
│   ├── scripts/        ← hub client (canonical)
│   └── resources/
└── hub/                ← this folder (Java server only)
```

Consumer runtime lives in the **application project** at `my-app/cdase/`.

## SSOT

| Path | Role |
|---|---|
| `~/.cdase/user.context.md` | Global identity (Name; all agents) |
| `~/.cdase/setting.context.md` | Default hub address |
| `/cdase/context/users.context.md` | Trusted roster + UUID SSOT |
| `/cdase/context/setting.context.md` | Optional repo hub override |

Set `CDASE_ROOT` to the consumer `cdase/` folder when running the client.

## Build & run server

```bash
cd hub
mvn -q package
java -jar target/cdase-hub-1.0.0.jar
```

Default listen: `http://0.0.0.0:7423` — set `Hub.Address` in `~/.cdase/setting.context.md`.

**Public deploy (12th host):** `https://12th.ai/cdase`  
- Landing (browser HTML / API JSON): `https://12th.ai/cdase/`  
- Health: `https://12th.ai/cdase/health`  
- Version: `https://12th.ai/cdase/version`  

Deploy: `hub/deploy/push.sh` or GitHub Action **Deploy CDASE Hub**.

## Client

Canonical: `cdase/scripts/cdase_client.py` (bundled with skill).

```bash
export CDASE_ROOT=/path/to/my-app/cdase   # if not auto-detected
python3 cdase/scripts/cdase_client.py check
python3 cdase/scripts/cdase_client.py login
python3 cdase/scripts/cdase_client.py inbox
```

Set global `Hub.Address` once; repo override only for projects on a different hub.

## User input (no hub-served UI)

The hub does **not** serve UI. CDASE input is host-native: the client emits a declarative
spec and the agent renders it with the host's native UI (Cursor card) or plain text.

```bash
python3 cdase/scripts/cdase_client.py input-spec user-profile
python3 cdase/scripts/cdase_client.py apply-global-user --json '{"Name":"will","Role":"architect"}'
```

Protocol: `cdase/resources/protocol/input.md`
