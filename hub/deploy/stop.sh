#!/usr/bin/env bash
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
PID_FILE="$DIR/hub.pid"

if [[ -f "$PID_FILE" ]]; then
  pid="$(cat "$PID_FILE")"
  if kill -0 "$pid" 2>/dev/null; then
    kill "$pid" || true
    sleep 1
    kill -9 "$pid" 2>/dev/null || true
    echo "stopped hub pid=$pid"
  fi
  rm -f "$PID_FILE"
fi

# fallback: anything listening on 7423 with our jar name
pkill -f 'cdase-hub.jar' 2>/dev/null || true
echo "hub stopped"
