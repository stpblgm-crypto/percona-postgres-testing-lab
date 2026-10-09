# PostgreSQL test evidence: synthetic laboratory

This repository demonstrates the difference between a mocked application
boundary, a real PostgreSQL SQL-contract check, and an explicit release gate.
The inputs are synthetic. It is an educational lab, not a production release
policy. The accompanying unpublished article is supplied separately for
editorial review and is not included in this repository.

## Requirements

For the installed-toolchain route, use Linux, Bash, Python 3.12 or newer,
and PostgreSQL 16 server/client tools (`initdb`, `pg_ctl`, `psql`) on PATH.
Run as a non-root user. No third-party Python packages are required.
Do not use Python `-O` or `PYTHONOPTIMIZE`: receipt validation uses assertions.
Never point the lab at an existing database.

For the Docker route, use a compatible Linux Docker Engine, GNU tar, and
permission to pull the official Python and PostgreSQL images. From the repository root:

```bash
bash run_docker.sh
```

The build uses `python:3.12-bookworm` and `postgres:16.15-bookworm`. The test
container runs with network disabled, no published ports, a non-root user,
read-only source, and disposable `/tmp`. Image tags can change: retain your
exact runtime versions and image digest. No host PostgreSQL service is created.
Synthetic evidence is produced inside the container's private tmpfs, streamed
as a tar archive, and extracted into an owner-private host directory without
preserving container ownership. No world-writable host evidence mount is used.
Evidence-export errors remain failures; a failing lab keeps its nonzero exit
status even when its diagnostic evidence is successfully exported.

For the installed-toolchain route, start at the repository root with a fresh
empty evidence directory:

```bash
OUT=$(mktemp -d /tmp/percona-reader-manual.XXXXXXXX)
export PATH="/usr/lib/postgresql/16/bin:$PATH"  # adapt to the installed version
bash lab/run_ci.sh "$OUT"
```

## Expected observations

- Gate-policy tests: 13/13 pass; validation-policy tests: 6/6 pass
- No database: legacy exit 0, strict exit 1, database status `NOT_RUN`
- BEFORE schema: SQLSTATE `ZX001`, `psql` exit 3, gate exit 1 because NULL was accepted
- AFTER schema: `CONTRACT_OK`, `psql` exit 0, gate exit 0, both required tests pass
- Cleanup: `db/cleanup-status.log` records `pg_ctl: no server running` and `cleanup=PASS`

Inspect the JSON receipts and raw logs under the printed evidence path.
A missing tool, connection error, timeout, or missing receipt is an incomplete
experiment, not a passing database test. On a normal host the stopped,
mode-0700 synthetic cluster is retained for inspection; inside the Docker
wrapper it is held in tmpfs and disappears with the container.

## What has been verified

The 12 `lab/` files match the hashes from two separately retained PostgreSQL
16.15 client/server runs on October 8, 2026, using Python 3.12.15 in Debian 12.
`example_live_evidence/` contains the original synthetic JSON and selected
logs from one of those runs. The empty `cleanup-verifier.log` and temporary
`cluster-path.txt` were omitted; `db/cleanup-status.log` contains the result.
No customer data, private correspondence, or credentials are included.

At the October 9 packaging checkpoint, the Python-only policy, validation,
no-database receipt, article-mock, and syntax checks passed. The reader Docker
wrapper end-to-end test was `NOT_RUN`: Docker was unavailable in that review
environment. Those earlier database runs used a separately controlled Docker
invocation, not the reader wrapper. `READER_VALIDATION.json` preserves this
checkpoint. It is not proof of a later workflow result; verify any subsequent
GitHub Actions run against its exact commit SHA and underlying receipts.

The first hosted attempt on October 9 ran the database checks but failed when
collecting a container-owned `server.log`. That attempt is not a complete PASS.
The revised exporter has focused offline regressions, including mode-0600
logs, preserved failure status, malformed archives, and missing results. Run
them with `python3 tests/test_reader_export.py`. These stub-based checks do not
replace the mandatory full Linux and real Docker workflow.

The direct `psql` probe does not test a Python database driver, parameter
adaptation, pooling, production migrations, concurrency, crash recovery,
or performance. The two-test gate is an instructional example.

Check `sha256sum -c SHA256SUMS` after checkout. The manifest verifies file
integrity; it is not a cryptographic author signature.

## Manual GitHub Actions check

The workflow has no push, pull-request, schedule, deployment, or credential
write trigger. It is restricted to this repository's exact name and ID and
requires public visibility, explicit free-runner/quota confirmation, and the
exact reviewed commit SHA. It uses the standard `ubuntu-24.04` runner with a
15-minute maximum job duration and read-only repository permissions.

An authorized operator must verify that the standard public-repository runner
is free and that applicable included-usage limits remain below the approved
threshold before dispatch. The job first runs the installed-toolchain lab,
then the Docker reader wrapper, and retains their evidence separately.
Creating this branch or pull request does not start the workflow. At the
packaging checkpoint, no new hosted workflow had been dispatched.

## License

The original lab code and CI glue are MIT-licensed; see `LICENSE` and
`LICENSING.md`. The separate article is not licensed by this code grant.
PostgreSQL, Python, Bash, Docker images, and their components retain their
own licenses. No runtime binaries or third-party Python packages are bundled.
