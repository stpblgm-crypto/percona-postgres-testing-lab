# Licensing scope

The MIT license in `LICENSE` applies only to the original laboratory source
code in this package:

- `lab/*.py`
- `lab/*.sh`
- `lab/sql/*.sql`
- `tests/*.py`
- `run_docker.sh`
- `Dockerfile.pg16`
- `.github/workflows/lab.yml` (repository CI glue; absent from the reader ZIP)

Copyright (c) 2026 Alexander Stepanov. SPDX identifier: MIT.
Preserve the copyright and permission notice when redistributing this code.

The accompanying article is not included in this repository. It is a separate
manuscript supplied for editorial review and is excluded from the code's MIT license. Any publication of the article is
subject to the separately agreed editorial/publication terms. This package
does not apply MIT to the manuscript, retained evidence, or other prose.

No third-party Python packages or runtime binaries are bundled. The scripts
use Python's standard library and invoke separately installed Bash and
PostgreSQL tools. Docker build instructions reference the public Python and
PostgreSQL images. Those runtimes, images, and their components retain their
own licenses; this package does not relicense them.

License references:

- MIT: https://opensource.org/license/mit
- PostgreSQL: https://www.postgresql.org/about/licence/
- Python: https://docs.python.org/3.12/license.html
