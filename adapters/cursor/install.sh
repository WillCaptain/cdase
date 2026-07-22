#!/usr/bin/env bash
# Install/update the local Cursor CDASE plugin from repo SSOT.
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)"
DEST="${CURSOR_CDASE_PLUGIN_DIR:-$HOME/.cursor/plugins/local/cdase}"

mkdir -p "$DEST"
cp -R "$SRC/.cursor-plugin" "$DEST/"
cp -R "$SRC/hooks" "$DEST/"
cp -R "$SRC/rules" "$DEST/"
chmod +x "$DEST/hooks/session-start.sh"

echo "Installed CDASE Cursor plugin v$(jq -r .version "$DEST/.cursor-plugin/plugin.json") → $DEST"
echo "Reload Cursor window to pick up rule/hook changes."
