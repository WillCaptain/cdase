#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

if [[ ! -f hub/target/cdase-hub-1.0.0.jar ]]; then
  echo "Building hub jar..."
  (cd hub && mvn -q package)
fi

echo "=== unit: trust policy ==="
python3 cdase/scripts/tests/test_trust_policy.py -v

echo "=== unit: sync banner ==="
python3 cdase/scripts/tests/test_sync_banner.py -v

echo "=== unit: repo id ==="
python3 cdase/scripts/tests/test_repo_id.py -v

echo "=== unit: agent team brief ==="
python3 cdase/scripts/tests/test_agent_team_brief.py -v

echo "=== unit: hub warning ==="
python3 cdase/scripts/tests/test_hub_warning.py -v

echo "=== integration: hub sync ==="
python3 cdase/scripts/tests/test_hub_sync_integration.py -v

echo "=== unit: boot journey + hub URL gate ==="
python3 cdase/scripts/tests/test_boot_journey.py -v

echo "=== unit: global ~/.cdase dir ==="
python3 cdase/scripts/tests/test_global_cdase_dir.py -v

echo "=== unit: user scope (global vs repo) ==="
python3 cdase/scripts/tests/test_user_scope.py -v

echo "=== unit: setting template seed ==="
python3 cdase/scripts/tests/test_setting_template.py -v

echo "=== unit: machine-as-user identity ==="
python3 cdase/scripts/tests/test_machine_identity.py -v

echo "All hub tests passed."
