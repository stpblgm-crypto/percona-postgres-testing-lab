# What a green PostgreSQL test job actually proves

This MIT-licensed synthetic lab separates a mock call assertion, a real `psql`/PostgreSQL constraint check, and the release decision. `CHECK (quantity > 0)` accepts NULL; adding `NOT NULL` makes the three-input contract pass. It is not a production case study or a Python database-driver test.

## Verified evidence

On **16 October 2026, 17:29:55–17:30:33 UTC**, `bash run_docker.sh` completed with **exit 0** on an authorized native x86_64 Linux Docker host. Runtime: PostgreSQL server and psql **18.6 (Debian 18.6-1.pgdg12+2)**, libpq5 **18.6-1.pgdg12+2**, Python **3.12.15**, Docker Engine **29.7.2**.

| Observation | Actual result |
|---|---|
| No database | Legacy 0 / strict gate 1; database NOT_RUN |
| BEFORE | Expected NULL-acceptance contract failure; SQLSTATE ZX001, psql 3, gate 1 |
| AFTER | CONTRACT_OK; psql 0, gate 0; both required identities passed, no skips |
| Cleanup | Own PostgreSQL stopped; container and lab-only image tag removed |

`PG18_VERIFICATION.json` records the exact tested source and image lock at historical revision `4e49d34429f49628a165f0b18672cd96a2c46bb8`. The hosted workflow correction described below was prepared after that experiment; its new bytes are not part of the historical run. `evidence/pg18-20261016/receipts.redacted.json` contains actual receipts with only the random temporary data/socket paths redacted and identical source/required-ID maps stored once. Full original logs and unsuccessful predecessor runs are retained privately.

The executed v06 ZIP SHA256 is `0e5f70d1e14c89265bff65ff0b0111e20c90cb7c30dfba04806bbf9a8db9e7db`. The database launcher, SQL, gate, image lock, Docker wrapper and tests retain those executed bytes. The hosted workflow has a separate post-execution output-directory correction, so 20 of the historical 21 technical-input files remain byte-identical. This README and verification record were prepared after execution. Do not claim that a later commit or a repackaged archive was itself executed. The fields marked pre-execution in immutable `IMAGE_LOCK.json` describe its assembly time; the external verification record describes the completed run.

In the GitHub repository, earlier PostgreSQL **16.15** evidence under `example_live_evidence/` and `READER_VALIDATION.json` is historical. The [9 October workflow](https://github.com/stpblgm-crypto/percona-postgres-testing-lab/actions/runs/37974256714) ran commit `03f3dc8d3b4324bb31a3cdfda3228564efff2c80`, later merged at `d75040991a09888f523ed7867bf17eec550bd946`. It is not PG18 CI evidence and is not bundled in the minimal current reader ZIP. `OFFLINE_VERIFICATION.json` also remains a historical v04 record.

## Reader prerequisites and entry point

Use an already-authorized, non-production native x86_64 Linux Docker Engine, Bash, Python 3.12+ and GNU tar. The host also needs `awk`, `basename`, `cat`, `cp`, `cut`, `date`, `df`, `find`, `getconf`, `grep`, `mkdir`, `mktemp`, `sha256sum`, `stat`, `tr`, `uname` and `wc`. Git is needed only for the checkout path below. The invoking process must be able to inspect the daemon's reported DockerRootDir on that same host for the disk-space check. The wrapper requires at least 2 GiB MemAvailable, two online CPUs and 6 GiB free on the Docker filesystem. Never point it at a real database. No Docker installation, daemon reconfiguration, network changes or permission expansion is part of this lab.

Use a new directory for the checkout and select the immutable reviewed source snapshot:

```bash
git clone https://github.com/stpblgm-crypto/percona-postgres-testing-lab.git
cd percona-postgres-testing-lab
git checkout --detach 4e49d34429f49628a165f0b18672cd96a2c46bb8
sha256sum -c SHA256SUMS
bash run_docker.sh
```

The detached checkout above reproduces that historical source revision and its original documentation. An already-extracted reader kit can start with the final two commands from its own root. `SHA256SUMS` covers the reader files, including README and the verification records; it does not hash itself. A documentation-only revision must update the changed documentation entries in that manifest. It must leave the historical runtime receipts and their source maps unchanged.

Docker must be usable by the invoking process. The tested service-account invocation used a temporary adapter to existing `sudo docker`, not a newly granted Docker-group membership. Because `sudo docker run --cidfile` creates a root-owned CID file, that adapter returned ownership of only that newly-created lab CID file to its caller before the wrapper exported it. This host-specific adapter was not copied into the product wrapper. A direct authorized CLI user does not need that ownership repair, but that variant was not separately executed in the recorded run.

The non-root container must be able to traverse the bind-mount root and read `lab/`. Normal checkout files are readable; forced 0600 extraction caused an earlier access failure. Keep private files outside a reader checkout. Do not fix this by opening the Docker socket, making a home directory public, or changing existing service permissions. The test retained private evidence under its caller-owned directory and granted temporary source access only within its new scratch area.

## Isolation and images

`IMAGE_LOCK.json` pins both official image tags and OCI index digests, with the exact `linux/amd64` child manifests. A read-only recheck on 17 October verified the SHA256 of all four raw OCI objects. The successful run pulled by these immutable references.

PostgreSQL 18 declares PGDATA `/var/lib/postgresql/18/docker` and VOLUME `/var/lib/postgresql`. The lab bypasses the stock entrypoint, uses **non-login `bash -c`**, initializes its own disposable cluster under `/tmp`, and covers the declared volume with tmpfs. Using a login shell caused an unrelated PostgreSQL-home logout error; the source now prevents that regression.

During the database experiment the container runs non-root, network none, read-only root filesystem and source mount, cap-drop ALL, no-new-privileges, 128 PIDs, 1 GiB RAM and two CPUs. There are no host ports, host Docker socket, real database volumes or secrets. Image retrieval/build precedes the network-disabled test. A unique lab image tag and container ID delimit cleanup; shared base-image cache is deliberately not pruned.

Docker IDs must be interpreted as observed. In this Docker 29 image store, the reported image IDs equal OCI index digests; platform manifest and config digests are distinct records. See `PG18_VERIFICATION.json`. The raw log field names are preserved, not retroactively rewritten.

## Read the receipts

The generated output directory is printed as `Evidence: .../out`. Inspect and retain it before deleting only that exact owned directory. Required files include `no-db-legacy.json`, `no-db-gate.json`, `db/before.json`, `db/after.json`, `db/cleanup-status.log`, `db/versions.txt`, `result.json`, image IDs and OCI descriptors.

```bash
python3 lab/verify_receipts.py no-db /path/to/the/generated/out
python3 lab/verify_receipts.py db /path/to/the/generated/out/db
```

The paths above are placeholders for the wrapper's actual output. NoDB strict exit 1 and BEFORE exit 1 are expected negative cases; AFTER and the complete comparison must succeed. SQLSTATE ZX001 is mandatory: connection or syntax errors are not substitutes. PostgreSQL cleanup, evidence export and container cleanup are all required.

## Inspect the intentionally disabled database check

NoDB means the database test is deliberately not enabled; it does not prove that PostgreSQL is absent or unreachable. The full wrapper already exercises both NoDB policies. To inspect them separately without starting Docker, run these commands from the reader root:

```bash
OUT=$(mktemp -d /tmp/percona-nodb.XXXXXXXX)
LEGACY=0
env -u LAB_DB_ENABLED PYTHONOPTIMIZE=0 python3 lab/run.py --mode legacy --receipt "$OUT/no-db-legacy.json" || LEGACY=$?
GATE=0
env -u LAB_DB_ENABLED PYTHONOPTIMIZE=0 python3 lab/run.py --mode gate --receipt "$OUT/no-db-gate.json" || GATE=$?
printf 'legacy_exit=%s\ngate_exit=%s\n' "$LEGACY" "$GATE"
PYTHONOPTIMIZE=0 python3 lab/verify_receipts.py no-db "$OUT"
```

Expected exits are legacy `0` and gate `1`. Each receipt path must be new. The `||` assignments preserve the expected negative result even in a shell using `set -e`; they do not turn a verifier failure into a pass.

## Offline tests and CI

```bash
python3 lab/test_gate.py
python3 lab/test_validation.py
python3 tests/test_image_lock.py
python3 tests/test_reader_export.py
```

Historical v06 recorded results: 13/13, 6/6, 4/4 and 8/8 PASS. Fake-Docker fixtures are not PostgreSQL evidence. The stub uses Python `-S`, not `-O`; assertions and the 20-second wrapper deadline remain enabled. Never run receipt checks with Python optimization.

Hosted PG18 CI remains **NOT_RUN**. The hosted workflow uses `mkdir -p evidence` so its output-directory step works with the tracked `evidence/` directory. This one-line correction was prepared after the recorded v06 run; its local directory behavior was checked, but the changed workflow has not run on a hosted runner. The original 21-entry technical map and receipts remain historical records for revision `4e49d34429f49628a165f0b18672cd96a2c46bb8`, not fresh evidence for this workflow. The workflow is manual-only, checks the exact expected SHA, repository name/ID/public visibility, and requires truthful `free_quota_confirmed`. It uses standard Ubuntu 24.04, read-only contents permissions, a 15-minute timeout and a bounded one-day artifact. The applicable quota has not been confirmed, so the guard has not been disabled or bypassed. Local Docker PASS and hosted CI PASS are separate statements.

## License and boundaries

MIT applies to original lab code; see `LICENSE` and `LICENSING.md`. The manuscript, author profile and private correspondence are not in this repository. Their publication is a separate decision. This lab does not verify an application driver, migrations, concurrency, replication, crash recovery or production release readiness.
