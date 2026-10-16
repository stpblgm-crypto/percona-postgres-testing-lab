# What a green PostgreSQL test job proves: synthetic laboratory

This MIT-licensed educational laboratory separates three claims:

1. A Python mock verifies the call made to a cursor-shaped application boundary.
2. A real `psql`/PostgreSQL connection verifies a synthetic SQL constraint.
3. A release gate requires both named tests to execute and pass. A skipped database test is `NOT_RUN`, not release evidence.

The experiment uses a temporary `order_line` table. `CHECK (quantity > 0)` alone accepts `NULL`; `NOT NULL` plus `CHECK` enforces the intended rule. It is **not** an application-driver test, a production migration rehearsal, or production release approval.

## Evidence status (16 October 2026)

- Historical PostgreSQL **16.15** host and Docker reader run: **PASS**, at source tree `2ffd5bdbe6bdf524542162bef1de96b665913a34` (commit `d75040991a09888f523ed7867bf17eec550bd946`). The retained `example_live_evidence/` and [October 9 GitHub workflow](https://github.com/stpblgm-crypto/percona-postgres-testing-lab/actions/runs/37974256714) refer **only** to PostgreSQL 16.15.
- PostgreSQL **18.6** digest-pinned reader candidate: **E2E NOT_RUN**. Neither source code, an offline mock, nor image manifest metadata establishes a PostgreSQL 18 client/server PASS. PostgreSQL 18 logs/receipts have not yet been captured from any authorized runtime.

The complete English manuscript is held separately in the owner's private editorial package, not in this public code repository. MIT applies to lab source, **not** to that manuscript or historical raw records. See `LICENSING.md`.

## Immutable base image selection

`IMAGE_LOCK.json` records the tag plus **multi-platform OCI index digest** and corresponding **linux/amd64 child manifest digest** for both Docker Official Images:

- PostgreSQL image: `postgres:18.6-bookworm`, `PGDATA=/var/lib/postgresql/18/docker` and image-declared `VOLUME /var/lib/postgresql`.
- Python image: `python:3.12.15-bookworm`.

These references were obtained from Docker Hub's public image metadata but **have not been pulled or run by this revision**. The wrapper checks live OCI index descriptors against the pinned child manifests before pulling. A missing digest, mismatched architecture, stale registry reference, or Docker error fails closed. At runtime it additionally records the built **local image ID**, which is not interchangeable with the registry's index or platform manifest digest.

The reader uses the explicit `linux/amd64` build/run platform and requires native x86_64 (no architecture emulation). A PostgreSQL 18 lab server is initialised only at `/tmp/percona-lab.XXXXXXXX/data`, not at the image's default PGDATA. `--entrypoint /bin/bash` bypasses the stock Docker entrypoint. An explicit tmpfs at `/var/lib/postgresql` overrides the inherited image `VOLUME` to prevent an anonymous persistent Docker volume.

## Requirements and resource safety

Use a **non-production**, authorized native x86_64 Linux Docker Engine, Bash, GNU tar, Python 3.12+, and standard Linux tools (`sha256sum`, `getconf`, `df`, `awk`). Do not install/change Docker or change groups, ACLs, firewall or daemon settings as part of this experiment. Do not use an existing database or real volume. The preflight requires ≥2 GiB currently available RAM, ≥2 online CPUs and ≥6 GiB available on the Docker filesystem before any image pull/build; if unavailable it reports `NOT_RUN`.

Run from a **freshly extracted** ZIP or source checkout:

```bash
sha256sum -c SHA256SUMS
bash run_docker.sh
```

The wrapper obtains the locked base images during build (network permitted for retrieval), then runs the test container with `--network none`, no port publication, `--user postgres`, `--read-only`, one read-only source bind, private tmpfs for `/tmp` and `/var/lib/postgresql`, `--cap-drop ALL`, `no-new-privileges`, 128 PIDs, 1 GiB memory, and 2 CPUs. The `.dockerignore` transmits no local source, article, or evidence into the image build context; the code is mounted read-only only in the network-disabled test container. It does not mount Docker socket, secrets, database volumes, or external credentials. It does not touch any existing service/container. It uses a unique lab-only image tag, records its container ID via `--cidfile`, verifies the container is gone after `--rm`, and reports lab-tag removal; shared base-image cache is not pruned. `docker run --rm` removes its test container. No global prune commands are executed.

The caller-private evidence location is printed as `Evidence: /tmp/percona-reader.XXXXXXXX/out`. After the container stops, inspect it and copy the complete private logs to approved storage **before** deleting this exact lab-owned directory. Do not delete arbitrary host paths. A failing test/export cannot be reported as PASS.

## Expected contract (requires a real PostgreSQL 18 run)

| Step | Required observation |
|---|---|
| Offline gate and safety | All tests pass; export unit tests use fake Docker, not the server |
| NoDB legacy | exit `0`, named database test skipped and `NOT_RUN` |
| NoDB strict gate | exit `1`, named database test skipped and `NOT_RUN` |
| BEFORE | NULL passes the faulty `CHECK` constraint, dedicated `ZX001` diagnostic, `psql=3`, gate `1` |
| AFTER | `NOT NULL`+`CHECK`, `CONTRACT_OK`, `psql=0`, gate `0`, both required test IDs passed and no skips |
| Cleanup | owned lab `pg_ctl status=3`, no live postmaster.pid, `cleanup=PASS` |

`out/` must contain original no-DB, BEFORE, AFTER and cleanup logs and JSON receipts, source hashes, OCI descriptor verification and runtime versions (PostgreSQL **server**, `psql`, installed `libpq5`, Python). Host environment and final image ID and lab-container ID/cleanup are recorded separately. Raw unredacted environment/server evidence belongs in private storage; only sanitized synthetic data may enter this repository.

Offline checks, without any database:

```bash
python3 lab/test_gate.py
python3 lab/test_validation.py
python3 tests/test_reader_export.py
```

The offline export suite uses a stub and **fictional fixture receipts**. Even a green result is not evidence that PostgreSQL 18 ran. Do not invoke Python with `-O` or `PYTHONOPTIMIZE`: some receipt assertions use Python `assert`.

## Manual GitHub Actions

The workflow is **workflow_dispatch only** and has no push/PR/schedule/deployment trigger. It restricts the repository name and ID, public visibility, read-only permissions, standard `ubuntu-24.04` Linux runner and 15-minute timeout. `expected_sha` must equal the checked-out revision; `free_quota_confirmed` must be explicitly true based on a fresh verification that the selected runner is free and applicable quotas allow the run. Do not dispatch when billing/quota status is unknown. No CI run in this repository should be interpreted as a PG18 PASS unless the full reader wrapper and exported receipts are verified at that exact SHA.

## License and scope

Only original lab/CI code is MIT-licensed. See `LICENSE`, `LICENSING.md`. PostgreSQL/Python/runtime artifacts retain their own licenses. The lab does not verify Python driver binding/adaptation, pooling, application transactions, migrations, concurrency, locks, replication, recovery or performance.
