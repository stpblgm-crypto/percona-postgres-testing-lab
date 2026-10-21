#!/usr/bin/env python3
"""Check OCI index child descriptors for the platform and lock (stdlib only).

This is registry metadata validation, NOT proof that PostgreSQL E2E passed.
"""
import json
import re
import sys
from pathlib import Path

DIGEST = re.compile(r'sha256:[a-f0-9]{64}\Z')


def verify(lock, indices):
    if lock['platform'] != 'linux/amd64':
        raise ValueError('Only native linux/amd64 reviewed')
    report = {'schema': 'percona.oci.lock_verification.v2', 'platform': lock['platform'],
              'status': 'REGISTRY_MANIFEST_MATCH_ONLY_NOT_E2E', 'images': {}}
    for name in ('python', 'postgres'):
        item = lock['images'][name]
        if not all(DIGEST.fullmatch(item[k]) for k in ('index_digest', 'platform_manifest_digest')):
            raise ValueError('invalid digest syntax')
        if item['reference'] != item['tag'] + '@' + item['index_digest']:
            raise ValueError('lock reference is not tag plus digest')
        entries = indices[name].get('manifests')
        if not isinstance(entries, list):
            raise ValueError(f'{name}: expected multi-architecture index')
        matching = [e.get('digest') for e in entries if
                    e.get('platform', {}).get('os') == 'linux' and
                    e.get('platform', {}).get('architecture') == 'amd64' and
                    not e.get('platform', {}).get('variant')]
        if matching != [item['platform_manifest_digest']]:
            raise ValueError(f'{name}: OCI linux/amd64 child mismatch: {matching}')
        report['images'][name] = {
            'reference': item['reference'], 'index_digest': item['index_digest'],
            'platform_manifest_digest': matching[0],
            'verification': 'PLATFORM_DESCRIPTOR_MATCH'}
    return report


def main():
    if len(sys.argv) != 5:
        raise SystemExit('usage: verify_image_lock.py LOCK PG_INDEX_JSON PY_INDEX_JSON OUTPUT_JSON')
    lock = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
    indices = {'postgres': json.loads(Path(sys.argv[2]).read_text(encoding='utf-8')),
               'python': json.loads(Path(sys.argv[3]).read_text(encoding='utf-8'))}
    result = verify(lock, indices)
    Path(sys.argv[4]).write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print('OCI manifest descriptors: PASS (not a PostgreSQL run)')

if __name__ == '__main__':
    main()
