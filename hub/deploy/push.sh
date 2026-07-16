#!/usr/bin/env bash
# Local one-shot deploy to 12th host (same credentials style as 12th/deploy).
# Uses hub/deploy/.env (gitignored) OR env REMOTE_*.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
ENV_FILE="$SCRIPT_DIR/.env"

if [[ -f "$ENV_FILE" ]]; then
  # shellcheck source=/dev/null
  source "$ENV_FILE"
elif [[ -f "$REPO_ROOT/../12th/deploy/.env" ]]; then
  # shellcheck source=/dev/null
  source "$REPO_ROOT/../12th/deploy/.env"
fi

: "${REMOTE_HOST:?set REMOTE_HOST}"
: "${REMOTE_USER:?set REMOTE_USER}"
: "${REMOTE_PASS:?set REMOTE_PASS}"
REMOTE_DIR="${REMOTE_DIR:-/cdase-hub}"

if ! command -v sshpass >/dev/null 2>&1; then
  echo "Install sshpass: brew install hudochenkov/sshpass/sshpass" >&2
  exit 1
fi

SSH_OPTS=(-o StrictHostKeyChecking=accept-new -o ConnectTimeout=30)
SSH() { sshpass -p "$REMOTE_PASS" ssh "${SSH_OPTS[@]}" "${REMOTE_USER}@${REMOTE_HOST}" "$@"; }
SCP() { sshpass -p "$REMOTE_PASS" scp "${SSH_OPTS[@]}" "$@"; }

echo "▶ build hub jar"
(cd "$REPO_ROOT/hub" && mvn -q package -DskipTests)
JAR="$REPO_ROOT/hub/target/cdase-hub-1.0.0.jar"
[[ -f "$JAR" ]] || { echo "missing $JAR" >&2; exit 1; }

echo "▶ prepare $REMOTE_DIR"
SSH "mkdir -p $REMOTE_DIR/data $REMOTE_DIR/logs"

echo "▶ upload"
SCP "$JAR" "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_DIR}/cdase-hub.jar"
SCP \
  "$SCRIPT_DIR/start.sh" \
  "$SCRIPT_DIR/stop.sh" \
  "$SCRIPT_DIR/nginx-cdase.conf" \
  "$SCRIPT_DIR/remote-install-nginx.sh" \
  "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_DIR}/"

SSH "chmod +x $REMOTE_DIR/start.sh $REMOTE_DIR/stop.sh $REMOTE_DIR/remote-install-nginx.sh"

echo "▶ nginx /cdase/"
SSH "bash $REMOTE_DIR/remote-install-nginx.sh $REMOTE_DIR"

echo "▶ restart hub"
SSH "cd $REMOTE_DIR && ./stop.sh; ./start.sh; sleep 2; curl -sS http://127.0.0.1:7423/health; echo; curl -sS -o /dev/null -w 'nginx:%{http_code}\n' http://127.0.0.1/cdase/health || true"

echo "Done. Public health: http://${REMOTE_HOST}/cdase/health  (and https://12th.ai/cdase/health after TLS fix)"
