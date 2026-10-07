#!/usr/bin/env bash
set -euo pipefail
[[ $# == 1 ]]
OUT=$1
if [[ ! -f "$OUT/cluster-path.txt" ]]; then
  echo 'No owned cluster path recorded; nothing to stop.'
  exit 0
fi
BASE=$(cat "$OUT/cluster-path.txt")
[[ "$BASE" =~ ^/tmp/percona-lab\.[A-Za-z0-9]{8}$ && -d "$BASE" && -O "$BASE" ]]
[[ "$(realpath -- "$BASE")" == "$BASE" ]]
[[ "$(stat -c %a -- "$BASE")" == 700 ]]
PGCTL=/usr/lib/postgresql/16/bin/pg_ctl
set +e
"$PGCTL" -D "$BASE/data" status > "$OUT/cleanup-status.log" 2>&1
STATUS=$?
set -e
if [[ "$STATUS" == 0 ]]; then
  "$PGCTL" -D "$BASE/data" -m fast -w stop >> "$OUT/cleanup-status.log" 2>&1
  set +e
  "$PGCTL" -D "$BASE/data" status >> "$OUT/cleanup-status.log" 2>&1
  STATUS=$?
  set -e
fi
[[ "$STATUS" == 3 && ! -e "$BASE/data/postmaster.pid" ]]
printf 'cleanup=PASS\ncluster_retained_until_runner_teardown=true\n' >> "$OUT/cleanup-status.log"
