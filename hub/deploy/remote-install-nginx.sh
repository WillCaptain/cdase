#!/usr/bin/env bash
# Run ON the server as root. Installs /cdase/ proxy into nginx.
set -euo pipefail
HUB_DIR="${1:-/cdase-hub}"
SNIPPET="$HUB_DIR/nginx-cdase.conf"

if [[ ! -f "$SNIPPET" ]]; then
  echo "ERROR: missing $SNIPPET" >&2
  exit 1
fi

ELSA="$(grep -rl 'listen' /etc/nginx/conf.d/*.conf 2>/dev/null | head -1 || true)"
if [[ -z "${ELSA:-}" ]]; then
  ELSA="/etc/nginx/conf.d/elsa.conf"
fi

if grep -q 'location /cdase/' "$ELSA" 2>/dev/null; then
  echo "nginx already has /cdase/ in $ELSA"
elif grep -q "include $HUB_DIR/nginx-cdase.conf" "$ELSA" 2>/dev/null; then
  echo "include already present in $ELSA"
else
  if grep -q 'location /anna/' "$ELSA"; then
    sed -i "/location \/anna\//i\\    include $HUB_DIR/nginx-cdase.conf;" "$ELSA"
  else
    awk -v inc="    include $HUB_DIR/nginx-cdase.conf;" '
      BEGIN{done=0}
      /^[[:space:]]*}[[:space:]]*$/ && !done { print inc; done=1 }
      { print }
    ' "$ELSA" >"${ELSA}.tmp" && mv "${ELSA}.tmp" "$ELSA"
  fi
  echo "added include to $ELSA"
fi

nginx -t
nginx -s reload
echo "nginx reloaded — /cdase/ → 127.0.0.1:7423"
