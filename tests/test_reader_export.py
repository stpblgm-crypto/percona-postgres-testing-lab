"""Offline export regressions using a Docker stub; not a real Docker/DB run."""
import io
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import tarfile
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ReaderExport(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="percona-export-test-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.bin = self.base / "bin"
        self.bin.mkdir()
        self.archive = self.base / "fixture.tar"
        self.args_log = self.base / "docker-args.json"
        stub = self.bin / "docker"
        stub.write_text("""#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
if sys.argv[1] == 'build':
    sys.exit(0)
if sys.argv[1] != 'run':
    sys.exit(97)
Path(os.environ['TEST_ARGS_LOG']).write_text(json.dumps(sys.argv[1:]))
sys.stdout.buffer.write(Path(os.environ['TEST_ARCHIVE']).read_bytes())
sys.exit(int(os.environ.get('TEST_CONTAINER_EXIT', '0')))
""")
        stub.chmod(0o700)

    def make_archive(self, include_result=True):
        with tarfile.open(self.archive, "w") as archive:
            directory = tarfile.TarInfo("./db")
            directory.type = tarfile.DIRTYPE
            directory.mode = 0o700
            directory.uid = 999
            directory.gid = os.getgid()
            archive.addfile(directory)
            files = {"./db/server.log": b"synthetic PostgreSQL log\n"}
            if include_result:
                files["./result.json"] = b'{"fixture_only": true}\n'
            for name, content in files.items():
                info = tarfile.TarInfo(name)
                info.size = len(content)
                info.mode = 0o600
                info.uid = 999
                info.gid = os.getgid()
                archive.addfile(info, io.BytesIO(content))

    def invoke(self, container_exit=0):
        env = dict(os.environ)
        env.update(PATH=str(self.bin) + os.pathsep + env["PATH"],
                   TEST_ARCHIVE=str(self.archive), TEST_ARGS_LOG=str(self.args_log),
                   TEST_CONTAINER_EXIT=str(container_exit), PYTHONDONTWRITEBYTECODE="1")
        result = subprocess.run(["bash", "run_docker.sh"], cwd=ROOT, env=env,
                                text=True, capture_output=True, timeout=15)
        match = re.search(r"(?m)^Evidence: (/tmp/percona-reader\.[A-Za-z0-9]{8}/out)$",
                          result.stdout)
        self.assertIsNotNone(match, result.stdout + result.stderr)
        out = Path(match.group(1))
        self.addCleanup(shutil.rmtree, out.parent)
        return result, out

    def test_private_log_export_is_owned_by_caller(self):
        self.make_archive()
        result, out = self.invoke()
        self.assertEqual(result.returncode, 0, result.stderr)
        logfile = out / "db/server.log"
        self.assertEqual(logfile.read_bytes(), b"synthetic PostgreSQL log\n")
        self.assertEqual(logfile.stat().st_uid, os.getuid())
        self.assertEqual(stat.S_IMODE(logfile.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(out.stat().st_mode), 0o700)
        args = json.loads(self.args_log.read_text())
        self.assertEqual(args[args.index("--network") + 1], "none")
        self.assertEqual(args[args.index("--user") + 1], "postgres")
        self.assertEqual(args[args.index("--cap-drop") + 1], "ALL")
        self.assertIn("--read-only", args)
        self.assertEqual(sum(x == "--mount" for x in args), 1)
        self.assertTrue(args[args.index("--mount") + 1].endswith("target=/lab,readonly"))

    def test_container_failure_preserves_evidence_and_status(self):
        self.make_archive()
        result, out = self.invoke(container_exit=7)
        self.assertEqual(result.returncode, 7, result.stderr)
        self.assertEqual((out / "db/server.log").read_bytes(), b"synthetic PostgreSQL log\n")

    def test_invalid_archive_is_not_success(self):
        self.archive.write_bytes(b"not a tar archive")
        result, _ = self.invoke()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("could not export", result.stderr)

    def test_missing_result_is_not_success(self):
        self.make_archive(include_result=False)
        result, _ = self.invoke()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("did not export result.json", result.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
