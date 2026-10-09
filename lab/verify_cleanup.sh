#!/usr/bin/env bash
# READ-ONLY verifier. Never stop a cluster based on a user-provided path.
set -euo pipefail
if [[ $# != 1 ]]; then echo 'usage: bash lab/verify_cleanup.sh EVIDENCE_DB_DIR' >&2; exit 2; fi
OUT=$1
if [[ ! -f "$OUT/cluster-path.txt" || -L "$OUT/cluster-path.txt" ]]; then
  echo 'NOT_RUN: no owned cluster path recorded; cannot attest cleanup' >&2; exit 2
fi
BASE=$(cat "$OUT/cluster-path.txt")
if ! [[ "$BASE" =~ ^/tmp/percona-lab\.[A-Za-z0-9]{8}$ && -d "$BASE" && -O "$BASE" ]]; then
  echo 'FAIL: cluster path does not belong to this synthetic lab' >&2; exit 1
fi
if [[ -L "$BASE" || "$(realpath -- "$BASE")" != "$BASE" || "$(stat -c %a -- "$BASE")" != 700 ]]; then
  echo 'FAIL: cluster directory owner / mode / symlink safety check failed' >&2; exit 1
fi
PGCTL=$(command -v pg_ctl || true)
if [[ -z "$PGCTL" ]]; then echo 'NOT_RUN: pg_ctl missing' >&2; exit 2; fi
set +e
"$PGCTL" -D "$BASE/data" status > "$OUT/cleanup-status.log" 2>&1
STATUS=$?
set -e
if [[ "$STATUS" == 3 && ! -e "$BASE/data/postmaster.pid" ]]; then
  printf 'cleanup=PASS\nno_mutating_cleanup_verifier=true\ncluster_retained=true\n' >> "$OUT/cleanup-status.log"
else
  printf 'cleanup=FAIL\npg_ctl_status=%s\n' "$STATUS" >> "$OUT/cleanup-status.log"
  echo 'FAIL: server still running or status could not be verified; NOT stopping it automatically' >&2
  exit 1
fi
