#!/usr/bin/env python3
"""Two process policies over the same, deliberately small test suite."""
import argparse
import datetime as dt
import hashlib
import json
import platform
import sys
import unittest
from pathlib import Path

import test_lab

REQUIRED = frozenset({
    'test_lab.MockBoundary.test_call_contract',
    'test_lab.PostgreSQLContract.test_quantity_contract',
})


class EvidenceResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.success_ids = []

    def addSuccess(self, test):
        self.success_ids.append(test.id())
        super().addSuccess(test)


def gate_pass(success_ids, failures, errors, skips, expected_failures,
              unexpected_successes, tests_run):
    """Fail closed: every discovered test must be one of the required successes."""
    return (
        isinstance(tests_run, int) and not isinstance(tests_run, bool)
        and tests_run == len(REQUIRED)
        and len(success_ids) == len(REQUIRED)
        and len(set(success_ids)) == len(REQUIRED)
        and set(success_ids) == REQUIRED
        and not any((failures, errors, skips, expected_failures, unexpected_successes))
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['legacy', 'gate'], required=True)
    parser.add_argument('--receipt', type=Path, required=True)
    args = parser.parse_args()
    # Exclusive creation; a duplicate or bad path must not replace prior evidence.
    with args.receipt.open('x', encoding='utf-8') as receipt:
        result = unittest.TextTestRunner(verbosity=2, resultclass=EvidenceResult).run(
            unittest.defaultTestLoader.loadTestsFromModule(test_lab))
        strict = gate_pass(
            result.success_ids, result.failures, result.errors, result.skipped,
            result.expectedFailures, result.unexpectedSuccesses, result.testsRun)
        sources = sorted(p for p in Path(__file__).parent.rglob('*')
                         if p.is_file() and p.suffix in {'.py', '.sql', '.sh'})
        evidence = {
            'created_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
            'mode': args.mode, 'python': platform.python_version(),
            'platform': platform.platform(), 'tests_run': result.testsRun,
            'success_ids': result.success_ids,
            'skipped': [{'id': t.id(), 'reason': r} for t, r in result.skipped],
            'failures': [t.id() for t, _ in result.failures],
            'errors': [t.id() for t, _ in result.errors],
            'expected_failures': [t.id() for t, _ in result.expectedFailures],
            'unexpected_successes': [t.id() for t in result.unexpectedSuccesses],
            'required_ids': sorted(REQUIRED),
            'framework_success': result.wasSuccessful(),
            'release_gate': 'PASS' if strict else 'FAIL',
            'database': test_lab.DB_META,
            'source_sha256': {
                str(p.relative_to(Path(__file__).parent)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sources
            },
        }
        exit_code = 0 if (result.wasSuccessful() if args.mode == 'legacy' else strict) else 1
        evidence['process_exit_code'] = exit_code
        json.dump(evidence, receipt, ensure_ascii=False, indent=2)
        receipt.write('\n')
    print(json.dumps({k: evidence[k] for k in
                      ['mode', 'framework_success', 'release_gate', 'process_exit_code']}))
    return exit_code


if __name__ == '__main__':
    sys.exit(main())
