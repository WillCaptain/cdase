#!/usr/bin/env bash
# Run ON the server as root. Installs /cdase/ proxy into nginx.
set -euo pipefail
HUB_DIR="${1:-/cdase-hub}"
SNIPPET="$HUB_DIR/nginx-cdase.conf"
CONF="/etc/nginx/conf.d/cdase-hub.conf"

# Standalone server-agnostic include: put location in a dedicated file under conf.d
# by wrapping in a map-less snippet file that nginx can include from http context
# only if we use a separate server — simplest: drop full server-less locations
# into conf.d doesn't work. So patch elsa.conf or write include into it.

ELSA="$(grep -rl 'listen' /etc/nginx/conf.d/*.conf 2>/dev/null | head -1 || true)"
if [[ -z "${ELSA:-}" ]]; then
  ELSA="/etc/nginx/conf.d/elsa.conf"
fi

cp -f "$SNIPPET" "$HUB_DIR/nginx-cdase.conf"

if grep -q 'location /cdase/' "$ELSA" 2>/dev/null; then
  echo "nginx already has /cdase/ in $ELSA"
else
  # Insert include before the last closing brace of the first server block
  if grep -q "include $HUB_DIR/nginx-cdase.conf" "$ELSA" 2>/dev/null; then
    echo "include already present"
  else
    # Prefer inserting near other location blocks
    if grep -q 'location /anna/' "$ELSA"; then
      sed -i "/location \/anna\//i\\    include $HUB_DIR/nginx-cdase.conf;" "$ELSA"
    else
      # insert before final }
      awk -v inc="    include $HUB_DIR/nginx-cdase.conf;" '
        BEGIN{done=0}
        /^[[:space:]]*}[[:space:]]*$/ && !done { print inc; done=1 }
        { print }
      ' "$ELSA" >"${ELSA}.tmp" && mv "${ELSA}.tmp" "$ELSA"
    fi
    echo "added include to $ELSA"
  fi
fi

nginx -t
nginx -s reload
echo "nginx reloaded — /cdase/ → 127.0.0.1:7423"
