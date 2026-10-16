# Licensing scope

The MIT license in `LICENSE` applies only to the original laboratory source
code in this package:

- `lab/*.py`
- `lab/*.sh`
- `lab/sql/*.sql`
- `tests/*.py`
- `run_docker.sh`
- `Dockerfile.pg16` (original code retained unchanged in the GitHub repository)
- `Dockerfile.pg18`
- `tools/*.py` (synthetic evidence safety and image provenance checks)
- `.github/workflows/lab.yml`

Copyright (c) 2026 Alexander Stepanov. SPDX identifier: MIT.
Preserve the copyright and permission notice when redistributing this code.

The separate `ARTICLE_EN.md` manuscript, if included in a private reader kit, is supplied for editorial review. It is
excluded from the code's MIT license. Any publication of the article is
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
