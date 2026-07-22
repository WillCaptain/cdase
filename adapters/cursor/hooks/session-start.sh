#!/usr/bin/env bash
cat >/dev/null 2>&1 || true
cat <<'JSON'
{
  "additional_context": "CDASE: Ask Apply CDASE? (yes/no) first unless already declared. On CDASE ON: load Constitution, discover the app repo, run `cdase check` first, and use boot only for missing state. After identity + explicit Hub URL are valid, run `cdase sync` before EVERY user answer. If `cdase` is unavailable, fall back to `python3 ~/.cursor/skills/cdase/scripts/cdase_client.py`. Active committed context/members/*.context.md records are trust authority; Hub adds presence/superset. Unknown senders get no auto-reply. Team → `team`. Never bootstrap cdase/ in framework repo."
}
JSON
