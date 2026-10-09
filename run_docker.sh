#!/usr/bin/env bash
# Run exclusively inside a disposable, networkless, non-root Docker container.
set -euo pipefail
[[ -f lab/run_ci.sh && -f Dockerfile.pg16 ]] || { echo 'Run from the extracted reader kit root' >&2; exit 2; }
command -v docker >/dev/null || { echo 'Docker is required' >&2; exit 2; }
BASE=$(mktemp -d /tmp/percona-reader.XXXXXXXX)
chmod 700 "$BASE"
mkdir "$BASE/out"
chmod 777 "$BASE/out"  # only the nested output, parent remains owner-private
printf 'Evidence: %s/out\n' "$BASE"
docker build -f Dockerfile.pg16 -t percona-reader-pg16:local .
# No host PG service or published network access, source mounted read-only.
docker run --rm --network none --user postgres --cap-drop ALL --security-opt no-new-privileges \
  --pids-limit 128 --memory 1g --cpus 2 --read-only \
  --tmpfs /tmp:rw,nosuid,nodev,size=512m \
  --mount "type=bind,source=$PWD,target=/lab,readonly" \
  --mount "type=bind,source=$BASE/out,target=/out" \
  -w /lab --entrypoint /bin/bash percona-reader-pg16:local -lc '
    export PATH="/usr/lib/postgresql/16/bin:$PATH"
    set +e
    bash lab/run_ci.sh /out
    rc=$?
    set -e
    if [[ -d /out/db ]]; then chmod o+rx /out/db || true; fi
    find /out -type f -exec chmod o+r {} + 2>/dev/null || true
    exit "$rc"
  '
# Inspect "$BASE/out/result.json" and raw before/after/cleanup logs.
