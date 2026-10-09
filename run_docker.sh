#!/usr/bin/env bash
# Run exclusively inside a disposable, networkless, non-root Docker container.
set -euo pipefail
[[ -f lab/run_ci.sh && -f Dockerfile.pg16 ]] || { echo 'Run from the extracted reader kit root' >&2; exit 2; }
command -v docker >/dev/null || { echo 'Docker is required' >&2; exit 2; }
command -v tar >/dev/null || { echo 'GNU tar is required' >&2; exit 2; }
umask 077
BASE=$(mktemp -d /tmp/percona-reader.XXXXXXXX)
mkdir "$BASE/out"
printf 'Evidence: %s/out\n' "$BASE"
docker build -f Dockerfile.pg16 -t percona-reader-pg16:local .
# Export synthetic evidence as a tar stream. Do not share container-owned files
# through a world-writable host mount or broaden their permissions for the host.
set +e
docker run --rm --network none --user postgres --cap-drop ALL --security-opt no-new-privileges \
  --pids-limit 128 --memory 1g --cpus 2 --read-only \
  --tmpfs /tmp:rw,nosuid,nodev,size=512m \
  --mount "type=bind,source=$PWD,target=/lab,readonly" \
  -w /lab --entrypoint /bin/bash percona-reader-pg16:local -lc '
    set -euo pipefail
    umask 077
    export PATH="/usr/lib/postgresql/16/bin:$PATH"
    OUT=$(mktemp -d /tmp/percona-evidence.XXXXXXXX)
    set +e
    bash lab/run_ci.sh "$OUT" >&2
    rc=$?
    set -e
    tar --create --file=- --directory="$OUT" .
    exit "$rc"
  ' > "$BASE/evidence.tar"
RUN_RC=$?
set -e
# A fresh owner-private output directory receives only this lab's own archive.
# --no-same-owner gives the caller ownership even when container UID/GID differ;
# --no-same-permissions applies the caller's restrictive umask to exported files.
if ! tar --extract --file="$BASE/evidence.tar" --directory="$BASE/out" \
    --no-same-owner --no-same-permissions; then
  echo 'FAIL: could not export the synthetic evidence archive' >&2
  if [[ "$RUN_RC" != 0 ]]; then exit "$RUN_RC"; fi
  exit 1
fi
if [[ "$RUN_RC" == 0 && ! -f "$BASE/out/result.json" ]]; then
  echo 'FAIL: successful container did not export result.json' >&2
  exit 1
fi
# Inspect "$BASE/out/result.json" and raw before/after/cleanup logs.
exit "$RUN_RC"
