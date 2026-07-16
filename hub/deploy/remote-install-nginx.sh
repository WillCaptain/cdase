#!/usr/bin/env bash
# Run ON the server as root. Installs /cdase/ proxy into the main site nginx config.
set -euo pipefail
HUB_DIR="${1:-/cdase-hub}"

# Prefer the real site config (same as 12th/anna), never misc port stubs.
ELSA=""
for candidate in \
  /etc/nginx/conf.d/elsa.conf \
  /etc/nginx/conf.d/12th.conf \
  /etc/nginx/sites-enabled/default
do
  if [[ -f "$candidate" ]]; then ELSA="$candidate"; break; fi
done
if [[ -z "$ELSA" ]]; then
  ELSA="$(grep -rl 'location /anna/' /etc/nginx/conf.d /etc/nginx/sites-enabled 2>/dev/null | head -1 || true)"
fi
if [[ -z "$ELSA" ]]; then
  ELSA="$(grep -rl 'proxy_pass.*8080' /etc/nginx/conf.d /etc/nginx/sites-enabled 2>/dev/null | head -1 || true)"
fi
if [[ -z "$ELSA" || ! -f "$ELSA" ]]; then
  echo "ERROR: could not find main nginx site config" >&2
  exit 1
fi
echo "using nginx config: $ELSA"

# Undo a bad include from an earlier deploy attempt (wrong file).
BAD="/etc/nginx/conf.d/antisuger-ports.conf"
if [[ -f "$BAD" ]] && grep -q 'nginx-cdase.conf\|location /cdase' "$BAD" 2>/dev/null; then
  sed -i '/nginx-cdase.conf/d;/location \/cdase/d' "$BAD" || true
  echo "cleaned stale cdase lines from $BAD"
fi

if grep -q 'location /cdase/' "$ELSA" 2>/dev/null; then
  echo "nginx already has /cdase/ in $ELSA"
else
  # Strip any prior include line then inject location blocks before /anna/ or before last }
  sed -i '/nginx-cdase.conf/d' "$ELSA" || true
  MARKER_FILE=$(mktemp)
  cat >"$MARKER_FILE" <<'BLOCK'
    location = /cdase {
        return 301 /cdase/;
    }
    location /cdase/ {
        proxy_pass http://127.0.0.1:7423/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 10;
        proxy_send_timeout 60;
        proxy_read_timeout 60;
    }
BLOCK
  if grep -q 'location /anna/' "$ELSA"; then
    # insert before first /anna/ location
    awk -v blockfile="$MARKER_FILE" '
      !done && /location \/anna\// {
        while ((getline line < blockfile) > 0) print line
        close(blockfile)
        done=1
      }
      { print }
    ' "$ELSA" >"${ELSA}.tmp" && mv "${ELSA}.tmp" "$ELSA"
  else
    awk -v blockfile="$MARKER_FILE" '
      BEGIN{done=0}
      /^[[:space:]]*}[[:space:]]*$/ && !done {
        while ((getline line < blockfile) > 0) print line
        close(blockfile)
        done=1
      }
      { print }
    ' "$ELSA" >"${ELSA}.tmp" && mv "${ELSA}.tmp" "$ELSA"
  fi
  rm -f "$MARKER_FILE"
  echo "inserted /cdase/ into $ELSA"
fi

nginx -t
nginx -s reload
echo "nginx reloaded — /cdase/ → 127.0.0.1:7423"
