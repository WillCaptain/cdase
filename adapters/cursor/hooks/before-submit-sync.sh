#!/usr/bin/env bash
# CDASE user-turn hook: run sync; inject a compact one-line banner only when needed.

set -euo pipefail

INPUT=$(cat)
BUNDLED_CLIENT="${HOME}/.cursor/skills/cdase/scripts/cdase_client.py"
SCRIPT_DIR="$(dirname "$BUNDLED_CLIENT")"
if command -v cdase >/dev/null 2>&1; then
  CLIENT=(cdase)
elif [[ -f "$BUNDLED_CLIENT" ]]; then
  CLIENT=(python3 "$BUNDLED_CLIENT")
else
  CLIENT=()
fi

PROMPT=$(python3 - <<'PY' "$INPUT"
import json, sys
data = json.loads(sys.argv[1])
print(data.get("prompt") or data.get("user_message") or data.get("message") or "")
PY
)

if [[ ${#PROMPT} -lt 2 ]]; then
  echo '{}'
  exit 0
fi

ROOT=$(python3 - <<'PY' "$INPUT"
import json, sys
from pathlib import Path
data = json.loads(sys.argv[1])
for key in ("workspace_roots", "workspaceRoot", "roots"):
    val = data.get(key)
    if isinstance(val, list) and val:
        print(val[0]); break
    if isinstance(val, str) and val:
        print(val); break
else:
    print(data.get("cwd") or data.get("workspace_path") or str(Path.home()))
PY
)

ROOT=$(python3 -c "from pathlib import Path; import sys; print(Path(sys.argv[1]).expanduser().resolve())" "$ROOT")
WS_SHORT=$(basename "$ROOT")
WS_FULL="$ROOT"

CDASE_ROOT=""
if [[ -d "$ROOT/cdase/context" ]]; then
  CDASE_ROOT="$ROOT/cdase"
else
  for d in "$ROOT"/*; do
    [[ -d "$d/cdase/context" ]] || continue
    CDASE_ROOT="$d/cdase"
    WS_SHORT=$(basename "$d")
    WS_FULL="$d"
    break
  done
fi

if [[ -z "$CDASE_ROOT" || ${#CLIENT[@]} -eq 0 ]]; then
  echo '{}'
  exit 0
fi

CHECK_OUT=$(CDASE_ROOT="$CDASE_ROOT" "${CLIENT[@]}" check 2>/dev/null || true)
if [[ -z "$CHECK_OUT" ]]; then
  echo '{}'
  exit 0
fi

BLOCKED=$(python3 - <<'PY' "$CHECK_OUT"
import json, sys
try:
    data = json.loads(sys.argv[1])
    print("1" if not data.get("ok") or data.get("hub_tools_blocked") else "0")
except Exception:
    print("0")
PY
)
if [[ "$BLOCKED" == "1" ]]; then
  echo '{}'
  exit 0
fi

SYNC_OUT=$(CDASE_ROOT="$CDASE_ROOT" "${CLIENT[@]}" sync 2>/dev/null || true)
if [[ -z "$SYNC_OUT" ]]; then
  echo '{}'
  exit 0
fi

export SYNC_OUT WS_SHORT WS_FULL SCRIPT_DIR
python3 - <<'PY'
import json, importlib.util, os, sys
from pathlib import Path

sync = json.loads(os.environ["SYNC_OUT"])
if sync.get("hub_tools_blocked"):
    print("{}")
    sys.exit(0)
script_dir = Path(os.environ["SCRIPT_DIR"])
spec = importlib.util.spec_from_file_location("hub_sync", script_dir / "hub_sync.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

banner = mod.build_sync_banner(
    sync,
    workspace_short=os.environ["WS_SHORT"],
    workspace_full=os.environ["WS_FULL"],
)
if not banner:
    print("{}")
else:
    print(json.dumps({"additional_context": banner}))
PY
