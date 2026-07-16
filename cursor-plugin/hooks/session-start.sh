#!/usr/bin/env bash
cat >/dev/null 2>&1 || true
cat <<'JSON'
{
  "additional_context": "CDASE: Ask Apply CDASE? (yes/no) first. On CDASE ON: run `python3 ~/.cursor/skills/cdase/scripts/cdase_client.py sync` before EVERY user answer (login + inbox). Repo users.context.md = trust SSOT. Hub = all users + messages; new_to_you / unknown_sender = show but NO auto-reply until user confirms. Team → `team`. Never bootstrap cdase/ in framework repo."
}
JSON
