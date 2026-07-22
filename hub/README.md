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
| `<GLOBAL_CDASE>/user.context.md` | Global profile defaults |
| `<GLOBAL_CDASE>/setting.context.md` | Default hub address |
| `/cdase/context/members/<8-hex-user-id>.context.md` | Active membership/trust authority |
| `/cdase/context/setting.context.md` | Optional repo hub override |

`<GLOBAL_CDASE>` is `CDASE_GLOBAL` when set, otherwise `~/.cdase` on
macOS/Linux or `%USERPROFILE%\.cdase` on Windows. Settings precedence is
defaults → global → repo → environment.

Set `CDASE_ROOT` to the consumer `cdase/` folder when running the client.

## Build & run server

```bash
cd hub
mvn -q package
java -jar target/cdase-hub-1.1.0.jar
```

Default listen: `http://0.0.0.0:7423` — set `Hub.Address` in
`<GLOBAL_CDASE>/setting.context.md`.

**Public deploy (12th host):** `https://12th.ai/cdase`  
- Landing (browser HTML / API JSON): `https://12th.ai/cdase/`  
- Health: `https://12th.ai/cdase/health`  
- Version: `https://12th.ai/cdase/version`  

Deploy: `hub/deploy/push.sh` or GitHub Action **Deploy CDASE Hub**.

## Client

Install from the methodology checkout:

```bash
python -m pip install .
# Windows
py -m pip install .
```

`<CDASE_CLIENT>` means installed `cdase`, with
`python3 cdase/scripts/cdase_client.py` as the bundled fallback.

```bash
export CDASE_ROOT=/path/to/my-app/cdase   # if not auto-detected
<CDASE_CLIENT> check
<CDASE_CLIENT> login
<CDASE_CLIENT> inbox
```

Set global `Hub.Address` once; repo override only for projects on a different hub.

## Global API Pool

The Hub is the only API-pool address known to clients:

```
CDASE client → CDASE Hub → embedded/JDBC/legacy-HTTP knowledge provider
```

Repository module registries own exact contracts. The API Pool is the global
discovery authority used to prevent duplicate APIs.

### Server-only configuration

Copy `deploy/hub.env.example` to `/cdase-hub/hub.env`. `deploy/start.sh` loads
that file. Do **not** put knowledge-database URLs in client
`setting.context.md`.

Internal PostgreSQL + pgvector:

```bash
CDASE_KB_PROVIDER=postgres
CDASE_KB_JDBC_URL=jdbc:postgresql://127.0.0.1:5432/cdase_api_pool
CDASE_KB_JDBC_USER=cdase
CDASE_KB_JDBC_PASSWORD=...
CDASE_KB_WRITE_TOKEN=...
```

Relocate to an existing HTTP knowledge database:

```bash
CDASE_KB_PROVIDER=http
CDASE_KB_HTTP_URL=https://legacy.example/knowledge
CDASE_KB_HTTP_TOKEN=...
CDASE_KB_WRITE_TOKEN=...
```

Lightweight semantic matching uses an OpenAI-compatible local embedding service:

```bash
CDASE_EMBEDDING_URL=http://127.0.0.1:8081/v1/embeddings
CDASE_EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
```

The model emits one normalized 384-dimensional vector per API version. API
documents are embedded without an instruction; search queries use BGE's
`Represent this sentence for searching relevant passages:` prefix. Without an
embedding URL, the Hub remains operational with relational/lexical search and
reports semantic search as disabled.

### API-pool endpoints

```text
POST /api-pool/search                    public read
POST /api-pool/apis                      authenticated reserve/upsert
GET  /api-pool/apis?api_id=&version=     public read
POST /api-pool/transition                authenticated lifecycle transition
GET  /api-pool/graph?system=             public read
GET  /api-pool/health                    public health/capabilities
```

Write endpoints require `Authorization: Bearer $CDASE_KB_WRITE_TOKEN` and are
disabled when the server token is not configured.

New versions can only be published as `DEVELOPING`. Re-publishing updates the
contract/source and re-embeds only when semantic content or the embedding model
changes. Lifecycle status changes are accepted only through
`POST /api-pool/transition`, so `SUPERSEDED` cannot bypass successor validation.
The legacy `GET|POST /kb` endpoint remains temporarily for compatibility.

### Tests

```bash
mvn test
python3 -m unittest discover -s ../cdase/scripts/tests -p "test_*.py"
```

The normal suite covers lifecycle, relational persistence, hybrid ranking,
graph context, source ownership, HTTP relocation, embedding protocol, write
authorization, registry sync, and end-to-end client operations.

To exercise the real PostgreSQL/pgvector dialect against a disposable database:

```bash
CDASE_TEST_POSTGRES_URL=jdbc:postgresql://127.0.0.1:5432/cdase_test \
CDASE_TEST_POSTGRES_USER=cdase \
CDASE_TEST_POSTGRES_PASSWORD=... \
mvn test
```

## User input (no hub-served UI)

The hub does **not** serve UI. CDASE input is host-native: the client emits a declarative
spec and the agent renders it with the host's native UI (Cursor card) or plain text.

```bash
<CDASE_CLIENT> input-spec user-profile
<CDASE_CLIENT> apply-global-user --json '{"Name":"will","Role":"architect"}'
```

Protocol: `cdase/resources/protocol/input.md`
