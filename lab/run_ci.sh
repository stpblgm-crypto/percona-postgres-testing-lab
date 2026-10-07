#!/usr/bin/env bash
set -euo pipefail
[[ $# == 1 && -d "$1" ]]
OUT=$(cd -- "$1" && pwd)
cd -- "$(dirname -- "$0")"
python3 test_gate.py > "$OUT/gate-policy.log" 2>&1
set +e
env -u LAB_DB_ENABLED python3 run.py --mode legacy --receipt "$OUT/no-db-legacy.json" > "$OUT/no-db-legacy.log" 2>&1
LEGACY=$?
env -u LAB_DB_ENABLED python3 run.py --mode gate --receipt "$OUT/no-db-gate.json" > "$OUT/no-db-gate.log" 2>&1
GATE=$?
set -e
[[ "$LEGACY" == 0 && "$GATE" == 1 ]]
python3 - "$OUT" <<'PY'
import json, sys
from pathlib import Path
p=Path(sys.argv[1])
for name,code in [('no-db-legacy',0),('no-db-gate',1)]:
    d=json.loads((p/f'{name}.json').read_text())
    assert d['process_exit_code']==code
    assert d['database']['status']=='NOT_RUN'
    assert len(d['success_ids'])==1 and len(d['skipped'])==1
    assert d['release_gate']=='FAIL'
PY
bash run_local_postgres.sh "$OUT/db" > "$OUT/database-launcher.log" 2>&1
# run_local_postgres verifies before failed for the intended NULL assertion,
# after succeeded, and both connected to the same exact server version.
python3 - "$OUT" <<'PY'
import json, sys
from pathlib import Path
p=Path(sys.argv[1]);b=json.loads((p/'db/before.json').read_text());a=json.loads((p/'db/after.json').read_text())
assert b['failures']==['test_lab.PostgreSQLContract.test_quantity_contract']
assert not b['errors'] and not b['skipped']
assert a['database']['status']=='PASS' and a['release_gate']=='PASS'
assert len(a['success_ids'])==2 and not a['skipped']
(p/'result.json').write_text(json.dumps({'experiment':'synthetic PostgreSQL contract only','before':'FAIL_EXPECTED_NULL_ACCEPTED','after':'PASS','client_server_integration':'PASS','server_version':a['database']['server_version'],'application_driver_integration':'NOT_TESTED','production_release_authorization':False},indent=2)+'\n')
PY
