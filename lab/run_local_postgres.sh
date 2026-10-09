#!/usr/bin/env bash
# Create and use only our own disposable isolated cluster. Non-root Linux only.
set -euo pipefail
if [[ $# != 1 ]]; then echo 'usage: bash lab/run_local_postgres.sh NEW_OUTPUT_DIRECTORY' >&2; exit 2; fi
# Resolve output relative to the CALLER, not to the script's directory.
mkdir -- "$1" || { echo 'Output already exists or parent missing: refuse overwrite' >&2; exit 2; }
OUT=$(cd -- "$1" && pwd -P)
cd -- "$(dirname -- "$0")"
for tool in initdb pg_ctl psql; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    printf 'NOT_RUN: missing installed tool: %s\n' "$tool" | tee "$OUT/NOT_RUN.txt"; exit 2
  fi
done
if [[ $(id -u) == 0 ]]; then
  echo 'NOT_RUN: PostgreSQL initdb requires a non-root user' | tee "$OUT/NOT_RUN.txt"; exit 2
fi
BASE=$(mktemp -d /tmp/percona-lab.XXXXXXXX)
chmod 700 "$BASE"
printf '%s\n' "$BASE" > "$OUT/cluster-path.txt"
mkdir -m 700 "$BASE/socket"
: > "$BASE/pgpass"
chmod 600 "$BASE/pgpass"
: > "$BASE/service.conf"
chmod 600 "$BASE/service.conf"
STARTED=0
cleanup() {
  if [[ $STARTED == 1 ]]; then
    pg_ctl -D "$BASE/data" -m fast -w -t 15 stop >> "$OUT/cluster.log" 2>&1 || \
      echo 'WARNING: pg_ctl stop not confirmed; inspect cluster safely' >> "$OUT/cluster.log"
  fi
  # No rm -rf. Preserve the private synthetic cluster for manual inspection.
  printf '%s\n' "Temporary synthetic lab retained at $BASE" >> "$OUT/cluster.log"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
initdb -D "$BASE/data" --username=lab --auth-local=trust --auth-host=reject \
  --no-locale --encoding=UTF8 > "$OUT/cluster.log" 2>&1
STARTED=1
pg_ctl -D "$BASE/data" -l "$OUT/server.log" \
  -o "-k $BASE/socket -p 55439 -c listen_addresses='' -c unix_socket_permissions=0700" \
  -w -t 15 start >> "$OUT/cluster.log" 2>&1
export LAB_DB_ENABLED=1 LAB_CLUSTER_BASE="$BASE" LAB_PG_SOCKET="$BASE/socket" \
       LAB_PGPASSFILE="$BASE/pgpass" LAB_PSQL="$(command -v psql)"
{
  date -u +'%Y-%m-%dT%H:%M:%SZ'
  psql --version
  initdb --version
  pg_ctl --version
} > "$OUT/versions.txt"
set +e
LAB_SCHEMA=before python3 run.py --mode gate --receipt "$OUT/before.json" > "$OUT/before.log" 2>&1
BEFORE=$?
LAB_SCHEMA=after python3 run.py --mode gate --receipt "$OUT/after.json" > "$OUT/after.log" 2>&1
AFTER=$?
set -e
printf 'before_exit=%s\nafter_exit=%s\n' "$BEFORE" "$AFTER" | tee "$OUT/exit_codes.txt"
[[ "$BEFORE" == 1 && "$AFTER" == 0 ]] || { echo 'Expected BEFORE=1, AFTER=0 not met' >&2; exit 1; }
python3 verify_receipts.py db "$OUT"
