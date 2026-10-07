#!/usr/bin/env bash
# Optional FUTURE integration run. Needs an already-installed PostgreSQL toolchain.
# No installs, Docker, network listener, existing database, or persistent data.
set -euo pipefail
cd -- "$(dirname -- "$0")"
if [[ $# != 1 ]]; then echo 'usage: bash run_local_postgres.sh NEW_OUTPUT_DIRECTORY' >&2; exit 2; fi
mkdir -- "$1" # fail if output already exists
OUT=$(cd -- "$1" && pwd)
for tool in initdb pg_ctl psql; do
  command -v "$tool" > /dev/null || { echo "NOT_RUN: missing $tool" | tee "$OUT/NOT_RUN.txt"; exit 2; }
done
if [[ $(id -u) == 0 ]]; then echo 'NOT_RUN: initdb requires a non-root user' | tee "$OUT/NOT_RUN.txt"; exit 2; fi
BASE=$(mktemp -d /tmp/percona-lab.XXXXXXXX)
chmod 700 "$BASE"
printf '%s\n' "$BASE" > "$OUT/cluster-path.txt"
mkdir "$BASE/socket"
STARTED=0
cleanup() {
  if [[ $STARTED == 1 ]]; then pg_ctl -D "$BASE/data" -m fast -w stop >> "$OUT/cluster.log" 2>&1 || true; fi
  # Retain the private temp directory for manual inspection. No broad rm command.
  printf '%s\n' "Temporary lab retained at $BASE" >> "$OUT/cluster.log"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
initdb -D "$BASE/data" --username=lab --auth-local=trust --auth-host=reject --no-locale --encoding=UTF8 > "$OUT/cluster.log" 2>&1
STARTED=1 # Attempt cleanup even if startup partially succeeds and pg_ctl reports failure.
pg_ctl -D "$BASE/data" -l "$OUT/server.log" -o "-k $BASE/socket -p 55439 -c listen_addresses=''" -w start >> "$OUT/cluster.log" 2>&1
export LAB_DB_ENABLED=1 LAB_PG_SOCKET="$BASE/socket" LAB_PSQL="$(command -v psql)"
psql --version > "$OUT/versions.txt"
initdb --version >> "$OUT/versions.txt"
pg_ctl --version >> "$OUT/versions.txt"
set +e
LAB_SCHEMA=before python3 run.py --mode gate --receipt "$OUT/before.json" > "$OUT/before.log" 2>&1
BEFORE=$?
LAB_SCHEMA=after python3 run.py --mode gate --receipt "$OUT/after.json" > "$OUT/after.log" 2>&1
AFTER=$?
set -e
printf 'before_exit=%s\nafter_exit=%s\n' "$BEFORE" "$AFTER" | tee "$OUT/exit_codes.txt"
# before must fail, after must pass. Preserve both raw receipts.
[[ "$BEFORE" == 1 && "$AFTER" == 0 ]]
python3 - "$OUT" <<'PYVERIFY'
import json, sys
from pathlib import Path
p = Path(sys.argv[1])
before = json.loads((p/'before.json').read_text())
after = json.loads((p/'after.json').read_text())
assert before['database']['sql_exit_code'] == 3, before
assert 'contract failure: NULL quantity was accepted' in before['database']['stderr'], before
assert before['release_gate'] == 'FAIL', before
assert after['database']['status'] == 'PASS' and after['release_gate'] == 'PASS', after
assert before['database']['server_version'] == after['database']['server_version'], (before, after)
print('Verified expected NULL-contract failure and after-schema success')
PYVERIFY
