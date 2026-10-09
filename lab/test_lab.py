"""Application mock + psql-only SQL contract; no Python PG driver is tested."""
import os
from pathlib import Path
import re
import stat
import subprocess
import unittest
from unittest.mock import Mock

from app import SQL, add_line

ROOT = Path(__file__).resolve().parent
DB_META = {'status': 'NOT_RUN', 'server_version': None, 'psql_version': None}
LAB_PATTERN = re.compile(r'^/tmp/percona-lab\.[A-Za-z0-9]{8}$')


def validate_lab_paths(base_text, socket_text, passfile_text):
    """Refuse untrusted paths before making any database connection or writes."""
    base = Path(base_text)
    socket = Path(socket_text)
    passfile = Path(passfile_text)
    if not LAB_PATTERN.fullmatch(str(base)):
        raise ValueError('not a launcher-created /tmp/percona-lab.XXXXXXXX directory')
    if base.is_symlink() or socket.is_symlink() or passfile.is_symlink():
        raise ValueError('lab paths must not be symlinks')
    if not base.is_dir() or not socket.is_dir() or not passfile.is_file():
        raise ValueError('required private cluster/socket/password paths missing')
    if socket != base / 'socket' or passfile != base / 'pgpass':
        raise ValueError('socket and empty password file must belong to lab base')
    for path, expected in ((base, 0o700), (socket, 0o700), (passfile, 0o600)):
        st = path.stat()
        if st.st_uid != os.geteuid() or stat.S_IMODE(st.st_mode) != expected:
            raise ValueError(f'owner or permissions invalid: {path}')
    if passfile.stat().st_size != 0:
        raise ValueError('lab password file must be empty')
    return base, socket, passfile


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
        DB_META['status'] = 'PREFLIGHT'
        try:
            base, socket, passfile = validate_lab_paths(
                os.environ['LAB_CLUSTER_BASE'], os.environ['LAB_PG_SOCKET'],
                os.environ['LAB_PGPASSFILE'])
            psql = Path(os.environ['LAB_PSQL'])
            if not psql.is_absolute() or not psql.is_file() or not os.access(psql, os.X_OK):
                raise ValueError('LAB_PSQL must be an absolute executable path')
        except (KeyError, ValueError, OSError) as exc:
            self.fail(f'Unsafe or incomplete isolated lab configuration: {exc}')

        # Strip all ambient libpq settings, including service, password and host.
        env = {k: v for k, v in os.environ.items() if not k.startswith('PG')}
        env.update(PGHOST=str(socket), PGPORT='55439', PGUSER='lab', PGDATABASE='postgres',
                   PGCONNECT_TIMEOUT='3', PGPASSFILE=str(passfile),
                   PGSERVICEFILE=str(base / 'service.conf'),
                   PGOPTIONS='-c statement_timeout=5000')
        cmd = [str(psql), '-X', '-w', '-qAt', '-v', 'ON_ERROR_STOP=1',
               '-v', 'VERBOSITY=verbose']
        DB_META['status'] = 'ATTEMPTED'
        DB_META['psql_version'] = subprocess.check_output(
            [str(psql), '--version'], text=True, env=env, timeout=5).strip()

        # This query is READ ONLY. Verify the actual server's data and socket
        # directories before creating even TEMP objects in the SQL probe.
        def show(key):
            response = subprocess.run(cmd + ['-c', f'SHOW {key}'], env=env,
                                      text=True, capture_output=True, timeout=10)
            self.assertEqual(response.returncode, 0, response.stderr)
            return response.stdout.strip()

        actual_data = show('data_directory')
        actual_socket = show('unix_socket_directories')
        DB_META.update(data_directory=actual_data, unix_socket_directories=actual_socket)
        self.assertEqual(actual_data, str(base / 'data'), 'Refuse a foreign database')
        self.assertEqual(actual_socket, str(socket), 'Refuse a foreign socket')
        DB_META['server_version'] = show('server_version')
        schema = os.environ.get('LAB_SCHEMA', 'after')
        self.assertIn(schema, ('before', 'after'))
        sql = (ROOT / 'sql' / f'{schema}.sql').read_text(encoding='utf-8') + '\n' + (
            ROOT / 'sql' / 'contract.sql').read_text(encoding='utf-8')
        result = subprocess.run(cmd, input=sql, env=env, text=True,
                                capture_output=True, timeout=15)
        DB_META.update(schema=schema, sql_exit_code=result.returncode,
                       stdout=result.stdout, stderr=result.stderr)
        if result.returncode != 0:
            DB_META['status'] = 'FAIL_SQL'
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines(), ['CONTRACT_OK'])
        DB_META['status'] = 'PASS'
