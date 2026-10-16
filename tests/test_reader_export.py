"""Offline fake-Docker regressions; fixture receipts are NOT real PostgreSQL evidence."""
import io
import json
import os
from pathlib import Path
import re
import shutil
import stat
import sys
import subprocess
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
MOCK = 'test_lab.MockBoundary.test_call_contract'
DB = 'test_lab.PostgreSQLContract.test_quantity_contract'


class ReaderExport(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='percona-export-test-')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.bin = self.base / 'bin'
        self.bin.mkdir()
        self.archive = self.base / 'fixture.tar'
        self.args_log = self.base / 'docker-args.json'
        stub = self.bin / 'docker'
        # Fake Docker needs only stdlib. Do not repeatedly load host sitecustomize
        # or installed packages; keep the existing 20-second budget and all checks.
        stub.write_text('#!' + sys.executable + ' -S\n' + '''"""Offline fake Docker CLI, never talks to daemon or database."""
import json, os, sys
from pathlib import Path
assert sys.flags.no_site == 1 and sys.flags.optimize == 0
args=sys.argv[1:]
if args[0]=='--version':
    print('Docker CLI STUB_ONLY (offline test)')
    sys.exit(0)
if args[0]=='version':
    print('docker_server_version=STUB')
    sys.exit(0)
if args[0]=='info':
    print('/tmp')  # DockerRootDir for host-space test
    sys.exit(0)
if args[:2]==['manifest','inspect']:
    lock=json.loads(Path('IMAGE_LOCK.json').read_text())
    item=lock['images']['postgres' if args[2].startswith('postgres:') else 'python']
    child=item['platform_manifest_digest']
    if os.environ.get('TEST_BAD_MANIFEST')=='1' and args[2].startswith('postgres:'):
        child='sha256:'+'0'*64
    print(json.dumps({'schemaVersion':2,'manifests':[
        {'digest': child,'platform':{'os':'linux','architecture':'amd64'}},
        {'digest':'sha256:'+'e'*64,'platform':{'os':'linux','architecture':'arm64'}}]}))
    sys.exit(0)
if args[0]=='ps':
    sys.exit(0)  # no pre-existing Docker containers in the offline fixture
if args[0]=='pull':
    sys.exit(0)
if args[0]=='build':
    Path(os.environ['TEST_BUILD_ARGS']).write_text(json.dumps(args))
    sys.exit(int(os.environ.get('TEST_BUILD_EXIT','0')))
if args[:2]==['image','inspect']:
    if '{{.Id}}' in args:
        print('sha256:'+'a'*64)
    else:
        print('linux/amd64')
    sys.exit(0)
if args[:2]==['image','rm']:
    Path(os.environ['TEST_IMAGE_CLEANUP']).write_text(json.dumps(args))
    sys.exit(0)
if args[:2]==['container','inspect']:
    sys.exit(1)  # the simulated --rm already removed the lab container
if args[0]=='run':
    if '--cidfile' in args:
        Path(args[args.index('--cidfile')+1]).write_text('a'*64 + '\\n')
    Path(os.environ['TEST_ARGS_LOG']).write_text(json.dumps(args))
    sys.stdout.buffer.write(Path(os.environ['TEST_ARCHIVE']).read_bytes())
    sys.exit(int(os.environ.get('TEST_CONTAINER_EXIT','0')))
sys.exit(97)
''')
        stub.chmod(0o700)

    def make_archive(self, include_result=True, include_evidence=True):
        """Create clearly synthetic fixtures to test wrapper validation, not SQL."""
        files = {'./db/server.log': b'STUB_ONLY_NOT_DB_EVIDENCE\n'}
        if include_result:
            files['./result.json'] = b'{"fixture_only": true, "NOT_REAL_DB": true}\n'
        if include_evidence:
            for mode, code in [('legacy', 0), ('gate', 1)]:
                record = dict(mode=mode, process_exit_code=code, tests_run=2,
                              success_ids=[MOCK], skipped=[{'id': DB, 'reason': 'NOT_RUN'}],
                              database={'status': 'NOT_RUN'}, framework_success=True,
                              release_gate='FAIL', failures=[], errors=[],
                              expected_failures=[], unexpected_successes=[])
                files[f'./no-db-{mode}.json'] = json.dumps(record).encode()
            base = dict(process_exit_code=1, framework_success=False, tests_run=2,
                        success_ids=[MOCK], failures=[DB], errors=[], skipped=[],
                        expected_failures=[], unexpected_successes=[], release_gate='FAIL',
                        source_sha256={'test_lab.py':'fictional-offline-fixture'},
                        database={'status':'FAIL_SQL', 'server_version':'18.6',
                                  'psql_version':'psql (PostgreSQL) 18.6',
                                  'sql_exit_code':3,
                                  'stderr':'ERROR:  ZX001: contract failure: NULL quantity was accepted\n',
                                  'stdout':'', 'data_directory':'/tmp/percona-lab.FIXTURE1/data',
                                  'unix_socket_directories':'/tmp/percona-lab.FIXTURE1/socket'})
            files['./db/before.json'] = json.dumps(base).encode()
            after = json.loads(json.dumps(base))
            after.update(process_exit_code=0, framework_success=True, success_ids=[MOCK, DB],
                         failures=[], release_gate='PASS')
            after['database'].update(status='PASS', sql_exit_code=0, stdout='CONTRACT_OK\n',
                                     stderr='')
            files['./db/after.json'] = json.dumps(after).encode()
            files['./db/cleanup-status.log'] = b'pg_ctl: no server running\ncleanup=PASS\n'
            files['./db/versions.txt'] = b'installed_libpq5=18.6-1.pgdg12+2\n'
        with tarfile.open(self.archive, 'w') as archive:
            entry = tarfile.TarInfo('./db')
            entry.type = tarfile.DIRTYPE
            entry.mode = 0o700
            archive.addfile(entry)
            for name, content in files.items():
                info=tarfile.TarInfo(name)
                info.size=len(content)
                info.mode=0o600
                info.uid=999
                info.gid=os.getgid()
                archive.addfile(info, io.BytesIO(content))

    def invoke(self, *, container_exit=0, bad_manifest=False, build_exit=0):
        env = dict(os.environ)
        env.update(PATH=str(self.bin) + os.pathsep + env['PATH'],
                   TEST_ARCHIVE=str(self.archive), TEST_ARGS_LOG=str(self.args_log),
                   TEST_IMAGE_CLEANUP=str(self.base/'image_cleanup.json'),
                   TEST_BUILD_ARGS=str(self.base/'build_args.json'),
                   TEST_BAD_MANIFEST=str(int(bad_manifest)),
                   TEST_BUILD_EXIT=str(build_exit),
                   TEST_CONTAINER_EXIT=str(container_exit), PYTHONDONTWRITEBYTECODE='1',
                   PYTHONOPTIMIZE='0')
        result = subprocess.run(['bash', 'run_docker.sh'], cwd=ROOT, env=env,
                                text=True, capture_output=True, timeout=20)
        match = re.search(r'(?m)^Evidence: (/tmp/percona-reader\.[A-Za-z0-9]{8}/out)$',
                          result.stdout)
        if match:
            out=Path(match.group(1))
            self.addCleanup(shutil.rmtree, out.parent)
        else:
            out=None
        return result, out

    def test_private_export_and_runtime_isolation(self):
        self.make_archive()
        result, out = self.invoke()
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        logfile=out/'db/server.log'
        self.assertEqual(logfile.read_bytes(), b'STUB_ONLY_NOT_DB_EVIDENCE\n')
        self.assertEqual(logfile.stat().st_uid, os.getuid())
        self.assertEqual(stat.S_IMODE(logfile.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(out.stat().st_mode), 0o700)
        args=json.loads(self.args_log.read_text())
        self.assertEqual(args[args.index('--network')+1], 'none')
        self.assertEqual(args[args.index('--user')+1], 'postgres')
        self.assertEqual(args[args.index('--platform')+1], 'linux/amd64')
        self.assertTrue((out/'lab-container-id.txt').read_text().strip() == 'a'*64)
        self.assertIn('lab_container_removed=PASS', (out/'container-cleanup.txt').read_text())
        self.assertEqual(args[args.index('--cap-drop')+1], 'ALL')
        self.assertEqual(args[args.index('--pids-limit')+1], '128')
        self.assertIn('--read-only', args)
        self.assertIn('--security-opt', args)
        self.assertIn('no-new-privileges', args)
        self.assertEqual(sum(x == '--mount' for x in args), 1)
        self.assertTrue(args[args.index('--mount')+1].endswith('target=/lab,readonly'))
        tmpfs = [args[i+1] for i,x in enumerate(args) if x=='--tmpfs']
        self.assertEqual(len(tmpfs),2)
        self.assertTrue(any(x.startswith('/tmp:') for x in tmpfs))
        self.assertTrue(any(x.startswith('/var/lib/postgresql:') for x in tmpfs))
        self.assertTrue((self.base/'image_cleanup.json').exists())
        self.assertIn('cleanup', (out/'image-cleanup.log').name)
        build_args=json.loads((self.base/'build_args.json').read_text())
        self.assertIn('--platform', build_args)
        self.assertIn('linux/amd64', build_args)
        self.assertIn('PG_BASE='+json.loads((ROOT/'IMAGE_LOCK.json').read_text())['images']['postgres']['reference'], build_args)
        self.assertIn('PY_BASE='+json.loads((ROOT/'IMAGE_LOCK.json').read_text())['images']['python']['reference'], build_args)

    def test_failing_container_preserves_status_and_raw_log(self):
        self.make_archive()
        result, out = self.invoke(container_exit=7)
        self.assertEqual(result.returncode, 7, result.stderr)
        self.assertEqual((out/'db/server.log').read_bytes(), b'STUB_ONLY_NOT_DB_EVIDENCE\n')

    def test_invalid_tar_is_failure(self):
        self.archive.write_bytes(b'not a tar archive')
        result, _ = self.invoke()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('could not export', result.stderr)

    def test_missing_result_is_failure(self):
        self.make_archive(include_result=False)
        result, _ = self.invoke()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('missing reader evidence: result.json', result.stderr)

    def test_missing_receipts_are_failure(self):
        self.make_archive(include_evidence=False)
        result, _ = self.invoke()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('missing reader evidence', result.stderr)

    def test_wrong_oci_child_digest_blocks_before_pull_build_run(self):
        self.make_archive()
        result, out = self.invoke(bad_manifest=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('OCI linux/amd64 child mismatch', result.stderr)
        self.assertIsNotNone(out)
        self.assertFalse(self.args_log.exists())
        self.assertFalse((self.base/'build_args.json').exists())

    def test_build_failure_is_not_success(self):
        self.make_archive()
        result, out = self.invoke(build_exit=19)
        self.assertEqual(result.returncode, 19, result.stderr)
        self.assertIsNotNone(out)
        self.assertFalse(self.args_log.exists())

    def test_tar_symlink_path_is_rejected(self):
        with tarfile.open(self.archive, 'w') as archive:
            sym=tarfile.TarInfo('./db/escape')
            sym.type=tarfile.SYMTYPE
            sym.linkname='../../etc/passwd'
            archive.addfile(sym)
        result, _ = self.invoke()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('could not export', result.stderr)


if __name__ == '__main__':
    unittest.main(verbosity=2)
