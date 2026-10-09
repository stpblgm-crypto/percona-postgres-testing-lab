#!/usr/bin/env bash
set -euo pipefail
if [[ $# != 1 || ! -d "$1" ]]; then
  echo 'usage: bash lab/run_ci.sh EMPTY_EXISTING_OUTPUT_DIR' >&2; exit 2
fi
OUT=$(cd -- "$1" && pwd -P)
if [[ -n "$(find "$OUT" -mindepth 1 -maxdepth 1 -print -quit)" ]]; then
  echo 'Output directory is not empty: refuse evidence replacement' >&2; exit 2
fi
cd -- "$(dirname -- "$0")"
python3 test_gate.py > "$OUT/gate-policy.log" 2>&1
python3 test_validation.py > "$OUT/validation-policy.log" 2>&1
set +e
env -u LAB_DB_ENABLED python3 run.py --mode legacy --receipt "$OUT/no-db-legacy.json" > "$OUT/no-db-legacy.log" 2>&1
LEGACY=$?
env -u LAB_DB_ENABLED python3 run.py --mode gate --receipt "$OUT/no-db-gate.json" > "$OUT/no-db-gate.log" 2>&1
GATE=$?
set -e
[[ "$LEGACY" == 0 && "$GATE" == 1 ]] || { echo 'Mock-only exit mismatch' >&2; exit 1; }
python3 verify_receipts.py no-db "$OUT"
bash run_local_postgres.sh "$OUT/db" > "$OUT/database-launcher.log" 2>&1
bash verify_cleanup.sh "$OUT/db" > "$OUT/cleanup-verifier.log" 2>&1
python3 verify_receipts.py db "$OUT/db"
python3 - "$OUT" <<'PY'
import json, sys
from pathlib import Path
p=Path(sys.argv[1]);a=json.loads((p/'db/after.json').read_text())
(p/'result.json').write_text(json.dumps({
    'experiment':'isolated synthetic SQL contract',
    'before':'FAIL_EXPECTED_ZX001_NULL_ACCEPTED', 'after':'PASS',
    'client_server_integration':'PASS',
    'server_version':a['database']['server_version'],
    'application_driver_integration':'NOT_TESTED',
    'production_release_authorization':False
}, indent=2)+'\n', encoding='utf-8')
PY
