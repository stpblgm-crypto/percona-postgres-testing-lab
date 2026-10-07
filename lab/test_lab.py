import os
from pathlib import Path
import subprocess
import unittest
from unittest.mock import Mock
from app import SQL, add_line

ROOT = Path(__file__).resolve().parent
DB_META = {'status': 'NOT_RUN', 'server_version': None, 'psql_version': None}

class MockBoundary(unittest.TestCase):
    def test_call_contract(self):
        cursor = Mock()
        cursor.fetchone.return_value = (42,)
        self.assertEqual(add_line(cursor, None), 42)
        cursor.execute.assert_called_once_with(SQL, (None,))

class PostgreSQLContract(unittest.TestCase):
    def test_quantity_contract(self):
        if os.environ.get('LAB_DB_ENABLED') != '1':
            self.skipTest('NOT_RUN: isolated PostgreSQL lab was not enabled')
        # The companion launcher supplies a fresh local Unix socket and role.
        # Never inherit ambient database credentials or libpq defaults.
        socket = os.environ['LAB_PG_SOCKET']
        if not Path(socket).is_absolute():
            self.fail('LAB_PG_SOCKET must be an absolute lab socket path')
        psql = os.environ['LAB_PSQL']
        if not Path(psql).is_absolute():
            self.fail('LAB_PSQL must be an absolute executable path')
        env = {k:v for k,v in os.environ.items() if not k.startswith('PG')}
        env.update(PGHOST=socket, PGPORT='55439', PGUSER='lab', PGDATABASE='postgres',
                   PGCONNECT_TIMEOUT='3', PGPASSFILE='/dev/null',
                   PGSERVICEFILE='/dev/null', PGOPTIONS='-c statement_timeout=5000')
        cmd = [psql, '-X', '-w', '-qAt', '-v', 'ON_ERROR_STOP=1']
        DB_META['status'] = 'ATTEMPTED'
        DB_META['psql_version'] = subprocess.check_output([psql, '--version'], text=True, env=env).strip()
        version = subprocess.run(cmd + ['-c', 'SHOW server_version'], env=env, text=True,
                                 capture_output=True, timeout=10)
        self.assertEqual(version.returncode, 0, version.stderr)
        DB_META['server_version'] = version.stdout.strip()
        schema = os.environ.get('LAB_SCHEMA', 'after')
        self.assertIn(schema, ('before', 'after'))
        sql = (ROOT/'sql'/f'{schema}.sql').read_text() + '\n' + (ROOT/'sql'/'contract.sql').read_text()
        result = subprocess.run(cmd, input=sql, env=env, text=True,
                                capture_output=True, timeout=15)
        DB_META.update(sql_exit_code=result.returncode, stdout=result.stdout, stderr=result.stderr)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('CONTRACT_OK', result.stdout.splitlines())
        DB_META['status'] = 'PASS'
