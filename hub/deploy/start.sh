#!/usr/bin/env bash
# Start cdase-hub on 127.0.0.1:7423 (proxied by nginx at /cdase/).
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

JAVA_BIN="${JAVA_BIN:-}"
if [[ -z "$JAVA_BIN" ]]; then
  for c in \
    /opt/jdk/current/bin/java \
    /usr/lib/jvm/java-21-openjdk/bin/java \
    /usr/bin/java
  do
    if [[ -x "$c" ]]; then JAVA_BIN="$c"; break; fi
  done
fi
: "${JAVA_BIN:?java not found}"

mkdir -p "$DIR/data" "$DIR/logs"
PID_FILE="$DIR/hub.pid"
LOG_FILE="$DIR/logs/hub.log"
JAR="$DIR/cdase-hub.jar"

if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
  echo "hub already running pid=$(cat "$PID_FILE")"
  exit 0
fi

nohup "$JAVA_BIN" -jar "$JAR" --host 127.0.0.1 --port 7423 --data "$DIR/data" \
  >>"$LOG_FILE" 2>&1 &
echo $! >"$PID_FILE"
echo "started hub pid=$(cat "$PID_FILE") log=$LOG_FILE"
