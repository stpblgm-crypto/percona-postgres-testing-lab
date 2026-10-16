#!/usr/bin/env bash
# From a freshly extracted reader kit. NEVER points to a host database.
set -euo pipefail
[[ -f lab/run_ci.sh && -f Dockerfile.pg18 && -f IMAGE_LOCK.json ]] || {
  echo 'Run from the freshly extracted reader kit root' >&2; exit 2;
}
for tool in docker tar python3 awk df stat sha256sum; do
  command -v "$tool" >/dev/null || { echo "NOT_RUN: missing $tool" >&2; exit 2; }
done
if [[ "${PYTHONOPTIMIZE:-0}" != 0 ]]; then
  echo 'NOT_RUN: do not run Python with PYTHONOPTIMIZE (receipt assertions)' >&2; exit 2
fi
umask 077
# Verify the reviewed package before any Docker activity.
sha256sum -c SHA256SUMS > /dev/null || { echo 'FAIL: kit SHA256SUMS mismatch' >&2; exit 1; }
PLATFORM=$(python3 -c 'import json; print(json.load(open("IMAGE_LOCK.json"))["platform"])')
PG_REF=$(python3 -c 'import json; print(json.load(open("IMAGE_LOCK.json"))["images"]["postgres"]["reference"])')
PY_REF=$(python3 -c 'import json; print(json.load(open("IMAGE_LOCK.json"))["images"]["python"]["reference"])')
[[ "$PLATFORM" == linux/amd64 && "$(uname -m)" == x86_64 ]] || {
  echo 'NOT_RUN: host architecture is not the reviewed native linux/amd64' >&2; exit 2;
}
# Fail closed before pulling or building if the shared host has insufficient headroom.
MEM_KB=$(awk '/^MemAvailable:/ {print $2}' /proc/meminfo)
CPU=$(getconf _NPROCESSORS_ONLN)
[[ "$MEM_KB" =~ ^[0-9]+$ && "$MEM_KB" -ge 2097152 && "$CPU" -ge 2 ]] || {
  echo 'NOT_RUN: require >=2 GiB MemAvailable and >=2 online CPU' >&2; exit 2;
}
DOCKER_ROOT=$(docker info --format '{{.DockerRootDir}}') || {
  echo 'NOT_RUN: Docker daemon unavailable' >&2; exit 2;
}
[[ -d "$DOCKER_ROOT" ]] || { echo 'NOT_RUN: Docker root cannot be inspected' >&2; exit 2; }
DISK_KB=$(df -Pk "$DOCKER_ROOT" | awk 'END {print $4}')
[[ "$DISK_KB" =~ ^[0-9]+$ && "$DISK_KB" -ge 6291456 ]] || {
  echo 'NOT_RUN: require >=6 GiB free on Docker filesystem' >&2; exit 2;
}
# Do not acquire, restart, or configure Docker; never touch other containers.
BASE=$(mktemp -d /tmp/percona-reader.XXXXXXXX)
mkdir "$BASE/out"
printf 'Evidence: %s/out\n' "$BASE"
# Everything under BASE is new. The host evidence directory persists for collection.
printf '%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$BASE/out/host-observed-utc.txt"
cp SHA256SUMS "$BASE/out/source-sha256.txt"
{ printf 'os='; uname -s; printf 'kernel='; uname -r;
  printf 'arch='; uname -m; docker --version; docker version --format 'docker_server_version={{.Server.Version}}';
  printf 'observed_running_containers='; docker ps -q | wc -l; printf 'free_memory_kib=%s\nonline_cpus=%s\nfree_docker_disk_kib=%s\n' "$MEM_KB" "$CPU" "$DISK_KB";
} > "$BASE/out/host-environment.txt"
# Resolve multi-arch OCI index descriptors directly from the pinned references.
docker manifest inspect "$PG_REF" > "$BASE/postgres-index.json"
docker manifest inspect "$PY_REF" > "$BASE/python-index.json"
python3 tools/verify_image_lock.py IMAGE_LOCK.json "$BASE/postgres-index.json" \
  "$BASE/python-index.json" "$BASE/out/oci-lock-check.json"
# Preserve verbatim OCI index descriptors as evidence independent of summaries.
cp -- "$BASE/postgres-index.json" "$BASE/out/oci-postgres-index.raw.json"
cp -- "$BASE/python-index.json" "$BASE/out/oci-python-index.raw.json"
# Pull by pinned content digest. A version tag alone is never used as a source.
docker pull --platform="$PLATFORM" "$PG_REF" >&2
docker pull --platform="$PLATFORM" "$PY_REF" >&2
IMAGE_TAG="percona-reader-pg18:lab-$(basename "$BASE" | cut -d. -f2 | tr '[:upper:]' '[:lower:]')"
# A lab-exclusive image tag is removed on exit; base images are shared cache and
# deliberately not pruned. There are no named or anonymous persisted volumes.
CREATED_IMAGE=0
cleanup_image() {
  local original_rc=$?
  trap - EXIT
  if [[ "$CREATED_IMAGE" == 1 ]]; then
    if docker image rm "$IMAGE_TAG" >> "$BASE/out/image-cleanup.log" 2>&1; then
      echo 'image_cleanup=PASS' >> "$BASE/out/image-cleanup.log"
    else
      echo 'image_cleanup=FAIL' >> "$BASE/out/image-cleanup.log"
      [[ "$original_rc" != 0 ]] || original_rc=1
    fi
  fi
  exit "$original_rc"
}
trap cleanup_image EXIT
docker build --pull --platform "$PLATFORM" -f Dockerfile.pg18 \
  --build-arg "TARGETPLATFORM=$PLATFORM" --build-arg "PG_BASE=$PG_REF" \
  --build-arg "PY_BASE=$PY_REF" -t "$IMAGE_TAG" . >&2
CREATED_IMAGE=1
# Exact local image IDs differ from index/child manifest digests.
{
  printf 'final_image_id='; docker image inspect "$IMAGE_TAG" --format '{{.Id}}';
  printf 'final_platform='; docker image inspect "$IMAGE_TAG" --format '{{.Os}}/{{.Architecture}}';
  printf 'postgres_base_image_id='; docker image inspect "$PG_REF" --format '{{.Id}}';
  printf 'python_base_image_id='; docker image inspect "$PY_REF" --format '{{.Id}}';
} > "$BASE/out/image-ids.txt"
grep -Fx 'final_platform=linux/amd64' "$BASE/out/image-ids.txt" > /dev/null || {
  echo 'FAIL: final image platform mismatch' >&2; exit 1;
}
# Default PG18 VOLUME /var/lib/postgresql must NOT create an anonymous volume.
# Explicit tmpfs at that exact destination overrides the image-declared VOLUME.
# There are no ports, external network, host socket, secrets, privileged flags.
set +e
docker run --rm --cidfile "$BASE/lab-container.cid" --platform "$PLATFORM" --network none --user postgres \
  --cap-drop ALL --security-opt no-new-privileges --pids-limit 128 \
  --memory 1g --cpus 2 --read-only \
  --tmpfs /tmp:rw,nosuid,nodev,size=512m,mode=1777 \
  --tmpfs /var/lib/postgresql:rw,nosuid,nodev,size=16m,mode=0700 \
  --mount "type=bind,source=$PWD,target=/lab,readonly" \
  -w /lab --entrypoint /bin/bash "$IMAGE_TAG" -lc '
    set -euo pipefail
    [[ "$(id -u)" != 0 ]] || { echo "NOT_RUN: root in container" >&2; exit 2; }
    umask 077
    export PATH="/usr/lib/postgresql/18/bin:$PATH"
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
printf 'container_exit=%s\n' "$RUN_RC" > "$BASE/out/docker-exit.txt"
# The unique container ID is private evidence. --rm should have removed it.
if [[ -f "$BASE/lab-container.cid" ]]; then
  cp -- "$BASE/lab-container.cid" "$BASE/out/lab-container-id.txt"
  CID=$(cat "$BASE/lab-container.cid")
  if docker container inspect "$CID" >/dev/null 2>&1; then
    printf 'lab_container_removed=FAIL\n' > "$BASE/out/container-cleanup.txt"
    echo 'FAIL: our lab container still exists after Docker run --rm' >&2
    exit 1
  fi
  printf 'lab_container_removed=PASS\n' > "$BASE/out/container-cleanup.txt"
else
  printf 'lab_container_removed=NOT_CONFIRMED\n' > "$BASE/out/container-cleanup.txt"
  if [[ "$RUN_RC" == 0 ]]; then
    echo 'FAIL: no container-id evidence returned for successful run' >&2
    exit 1
  fi
fi
# Check the tar is regular-file-only / directory-only, no traversals or links.
if ! python3 tools/safe_extract.py "$BASE/evidence.tar" "$BASE/out"; then
  echo 'FAIL: could not export the synthetic evidence archive' >&2
  [[ "$RUN_RC" != 0 ]] && exit "$RUN_RC"
  exit 1
fi
if [[ "$RUN_RC" == 0 ]]; then
  for f in result.json no-db-legacy.json no-db-gate.json db/before.json db/after.json \
           db/cleanup-status.log db/server.log db/versions.txt; do
    [[ -f "$BASE/out/$f" ]] || { echo "FAIL: missing reader evidence: $f" >&2; exit 1; }
  done
  python3 lab/verify_receipts.py no-db "$BASE/out"
  python3 lab/verify_receipts.py db "$BASE/out/db"
  grep -Fx 'cleanup=PASS' "$BASE/out/db/cleanup-status.log" > /dev/null
  [[ "$(find "$BASE/out" -type f -perm -0002 | wc -l)" == 0 ]] || {
    echo 'FAIL: world-writable evidence file' >&2; exit 1;
  }
fi
# Container --rm handles its own container; lab-only image tag is removed by trap.
exit "$RUN_RC"
