"""Negative validation tests. No PostgreSQL installation or networking needed."""
import unittest

from test_lab import validate_lab_paths
from verify_receipts import EXPECTED_BEFORE


class SQLStatePolicy(unittest.TestCase):
    def test_expected_specific_error(self):
        s = 'ERROR:  ZX001:  contract failure: NULL quantity was accepted\n'
        self.assertTrue(EXPECTED_BEFORE.search(s))

    def test_wrong_sqlstate_rejected(self):
        self.assertFalse(EXPECTED_BEFORE.search(
            'ERROR:  42601:  contract failure: NULL quantity was accepted\n'))

    def test_unrelated_message_rejected(self):
        self.assertFalse(EXPECTED_BEFORE.search('ERROR:  ZX001: other failure'))

    def test_generic_connection_error_rejected(self):
        self.assertFalse(EXPECTED_BEFORE.search('psql: connection refused'))


class SocketSafety(unittest.TestCase):
    def test_arbitrary_socket_rejected(self):
        with self.assertRaises(ValueError):
            validate_lab_paths('/var/lib/postgresql/main', '/var/run/postgresql', '/dev/null')

    def test_missing_cluster_rejected(self):
        with self.assertRaises(ValueError):
            validate_lab_paths('/tmp/percona-lab.AbcD1234',
                               '/tmp/percona-lab.AbcD1234/socket',
                               '/tmp/percona-lab.AbcD1234/pgpass')




if __name__ == '__main__':
    unittest.main(verbosity=2)
