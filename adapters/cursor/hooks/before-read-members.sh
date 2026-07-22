#!/usr/bin/env bash
# Block agents from reading member records as a shortcut for live team answers.
# Active committed records are trust SSOT; online state comes from `cdase team`.

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

if [[ ! "$PATH_VAL" =~ context[/\\]members[/\\][0-9a-f]{8}\.context\.md$ ]]; then
  echo '{ "permission": "allow" }'
  exit 0
fi

if command -v cdase >/dev/null 2>&1; then
  TEAM_COMMAND="cdase team"
else
  TEAM_COMMAND="python3 ~/.cursor/skills/cdase/scripts/cdase_client.py team"
fi

TEAM_COMMAND="$TEAM_COMMAND" python3 - <<'PY'
import json
import os
print(json.dumps({
    "permission": "deny",
    "agent_message": (
        "Do not read an individual member record to answer who is on the team or online. "
        "Active committed member records are trust authority, but Hub adds presence. "
        f"Run: {os.environ['TEAM_COMMAND']} "
        "and reply using agent_brief from the JSON output."
    ),
    "user_message": (
        "CDASE: team answers merge committed members with Hub presence."
    ),
}))
PY
