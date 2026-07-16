#!/usr/bin/env bash
# Block agents from reading users.context.md as a shortcut for team answers.
# Roster file is SSOT for trust/uuids — online team = `cdase_client.py team` (hub).

INPUT=$(cat)
PATH_VAL=$(python3 - <<'PY' "$INPUT"
import json, sys
data = json.loads(sys.argv[1])
for key in ("path", "file_path", "filePath", "target", "file"):
    v = data.get(key)
    if v:
        print(v)
        break
PY
)

if [[ "$PATH_VAL" != *"users.context.md"* ]]; then
  echo '{ "permission": "allow" }'
  exit 0
fi

python3 - <<'PY'
import json
print(json.dumps({
    "permission": "deny",
    "agent_message": (
        "Do not read users.context.md to answer who is on the team or who is online. "
        "That file is trust/uuid SSOT only — not live team presence. "
        "Run: python3 ~/.cursor/skills/cdase/scripts/cdase_client.py team "
        "and reply using agent_brief from the JSON output."
    ),
    "user_message": (
        "CDASE: team answers come from cdase-hub via the team command, not the roster file alone."
    ),
}))
PY
