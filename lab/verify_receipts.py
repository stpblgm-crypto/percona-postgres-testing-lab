"""Validate observed receipts. Historical originals use their own old format."""
import json
from pathlib import Path
import re
import sys

MOCK_ID = 'test_lab.MockBoundary.test_call_contract'
DB_ID = 'test_lab.PostgreSQLContract.test_quantity_contract'
# The complete verbose psql error line must contain the probe-specific SQLSTATE.
EXPECTED_BEFORE = re.compile(
    r'(?m)^ERROR:\s+ZX001:\s+contract failure: NULL quantity was accepted\s*$')


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def verify_no_db(directory):
    directory = Path(directory)
    for name, exit_code, mode in [('no-db-legacy', 0, 'legacy'),
                                  ('no-db-gate', 1, 'gate')]:
        d = load(directory / f'{name}.json')
        assert d['mode'] == mode and d['process_exit_code'] == exit_code
        assert d['tests_run'] == 2 and d['success_ids'] == [MOCK_ID]
        assert [x['id'] for x in d['skipped']] == [DB_ID]
        assert d['database']['status'] == 'NOT_RUN'
        assert d['framework_success'] and d['release_gate'] == 'FAIL'
        assert not any(d[k] for k in ('failures', 'errors', 'expected_failures',
                                       'unexpected_successes'))


def verify_db(directory):
    directory = Path(directory)
    before = load(directory / 'before.json')
    after = load(directory / 'after.json')
    assert before['process_exit_code'] == 1
    assert before['tests_run'] == 2 and before['success_ids'] == [MOCK_ID]
    assert before['failures'] == [DB_ID] and not before['errors']
    assert not any(before[k] for k in ('skipped', 'expected_failures',
                                        'unexpected_successes'))
    assert before['database']['status'] == 'FAIL_SQL'
    assert before['database']['sql_exit_code'] == 3
    assert EXPECTED_BEFORE.search(before['database']['stderr']), before['database']['stderr']
    assert 'CONTRACT_OK' not in before['database']['stdout']
    assert before['release_gate'] == 'FAIL'
    assert after['process_exit_code'] == 0 and after['framework_success']
    assert after['tests_run'] == 2 and after['success_ids'] == [MOCK_ID, DB_ID]
    assert not any(after[k] for k in ('failures', 'errors', 'skipped',
                                       'expected_failures', 'unexpected_successes'))
    assert after['database']['status'] == 'PASS' and after['release_gate'] == 'PASS'
    assert after['database']['sql_exit_code'] == 0
    assert after['database']['stdout'].splitlines() == ['CONTRACT_OK']
    for key in ('server_version', 'data_directory', 'unix_socket_directories'):
        assert before['database'][key] and before['database'][key] == after['database'][key]
    assert before['source_sha256'] == after['source_sha256']


def main():
    if len(sys.argv) != 3 or sys.argv[1] not in ('no-db', 'db'):
        raise SystemExit('usage: python3 verify_receipts.py no-db|db PATH')
    {'no-db': verify_no_db, 'db': verify_db}[sys.argv[1]](sys.argv[2])
    print(f'verified {sys.argv[1]} receipts')


if __name__ == '__main__':
    main()
