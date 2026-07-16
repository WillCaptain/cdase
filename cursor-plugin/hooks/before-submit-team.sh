#!/usr/bin/env bash
# When the user asks about team / who else is working, prefetch `team` from cdase-hub
# and inject agent_brief so the agent does not answer from users.context.md alone.

set -euo pipefail

INPUT=$(cat)
CLIENT="${HOME}/.cursor/skills/cdase/scripts/cdase_client.py"

export_json() {
  python3 -c 'import json,sys; print(json.dumps(json.load(sys.stdin)))' <<<"$1"
}

PROMPT=$(python3 - <<'PY' "$INPUT"
import json, sys, re
data = json.loads(sys.argv[1])
prompt = data.get("prompt") or data.get("user_message") or data.get("message") or ""
print(prompt)
PY
)

if ! echo "$PROMPT" | grep -qiE 'who (else|is on|'\''s on)|who.*(working|online)|team member|on this project|anyone else|other people|other user'; then
  echo '{}'
  exit 0
fi

# Workspace root from hook payload (field names vary by Cursor version)
ROOT=$(python3 - <<'PY' "$INPUT"
import json, sys
from pathlib import Path
data = json.loads(sys.argv[1])
for key in ("workspace_roots", "workspaceRoot", "roots", "project_roots"):
    val = data.get(key)
    if isinstance(val, list) and val:
        print(val[0])
        break
    if isinstance(val, str) and val:
        print(val)
        break
else:
    cwd = data.get("cwd") or data.get("workspace_path") or ""
    print(cwd or str(Path.home()))
PY
)

ROOT=$(python3 -c "from pathlib import Path; import sys; print(Path(sys.argv[1]).expanduser().resolve())" "$ROOT")

CDASE_ROOT=""
if [[ -d "$ROOT/cdase/context" ]]; then
  CDASE_ROOT="$ROOT/cdase"
else
  for d in "$ROOT"/*; do
    [[ -d "$d/cdase/context" ]] || continue
    CDASE_ROOT="$d/cdase"
    break
  done
fi

if [[ -z "$CDASE_ROOT" || ! -f "$CLIENT" ]]; then
  echo "$(python3 - <<PY
import json
print(json.dumps({"additional_context": "CDASE team question detected but no cdase/context found. Run discover, set CDASE_ROOT, then: python3 ~/.cursor/skills/cdase/scripts/cdase_client.py team"}))
PY
)"
  exit 0
fi

TEAM_OUT=$(CDASE_ROOT="$CDASE_ROOT" python3 "$CLIENT" team 2>/dev/null || true)
if [[ -z "$TEAM_OUT" ]]; then
  echo '{}'
  exit 0
fi

PAYLOAD=$(python3 - <<'PY' "$TEAM_OUT"
import json, sys
data = json.loads(sys.argv[1])
brief = data.get("agent_brief") or data.get("summary") or "(team command returned no brief)"
rule = data.get("agent_rule") or ""
repo = data.get("repo_id") or "unknown"
warn = ""
hw = data.get("hub_warning")
if hw and hw.get("message"):
    warn = hw["message"]
lines = [
    "CDASE TEAM PREFETCH — answer from this block. Do NOT quote users.context.md alone.",
    f"repo_id: {repo}",
    brief,
]
if warn:
    lines.append("HUB WARNING: " + warn)
if rule:
    lines.append("Rule: " + rule)
print(json.dumps({"additional_context": "\n".join(lines)}))
PY
)

echo "$PAYLOAD"
