#!/usr/bin/env python3
"""Fail closed on archive traversal/symlinks, over-large or incomplete export."""
from pathlib import Path, PurePosixPath
import os
import sys
import tarfile


def extract(archive, directory):
    directory = Path(directory)
    with tarfile.open(archive, 'r:') as t:
        members = t.getmembers()
        if len(members) > 200:
            raise ValueError('unexpectedly many evidence entries')
        total = 0
        for m in members:
            p = PurePosixPath(m.name)
            if p.is_absolute() or '..' in p.parts or not (m.isfile() or m.isdir()):
                raise ValueError('archive contains forbidden path or entry type')
            total += m.size
            if total > 8 * 1024 * 1024:
                raise ValueError('evidence exceeds 8 MiB')
        # No symlink/hardlink/special files were admitted; extraction into new private out.
        for m in members:
            dest = directory.joinpath(*PurePosixPath(m.name).parts)
            if m.isdir():
                dest.mkdir(mode=0o700, parents=True, exist_ok=True)
            else:
                dest.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                with t.extractfile(m) as inp, dest.open('xb') as dst:
                    while True:
                        chunk = inp.read(65536)
                        if not chunk: break
                        dst.write(chunk)
                dest.chmod(0o600)
    return len(members)

if __name__ == '__main__':
    if len(sys.argv) != 3:
        raise SystemExit('usage: safe_extract.py TARFILE PRIVATE_OUTPUT_DIR')
    try:
        count = extract(sys.argv[1], sys.argv[2])
        print(f'Evidence export files/dirs checked: {count}', file=sys.stderr)
    except (OSError, tarfile.TarError, ValueError) as err:
        print(f'Unsafe or invalid reader evidence archive: {err}', file=sys.stderr)
        sys.exit(1)
