import os
import sys
import tempfile
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from linux_worker_guard import run_guarded


class LinuxWorkerGuardTest(unittest.TestCase):
    def test_stale_lease_terminates_worker_group(self):
        with tempfile.TemporaryDirectory() as directory:
            lease = Path(directory) / "lease"; lease.touch()
            old = time.time() - 10; os.utime(lease, (old, old))
            started = time.monotonic()
            result = run_guarded(["/bin/sleep", "30"], lease, 3)
            self.assertLess(time.monotonic() - started, 6)
            self.assertLess(result, 0)

    def test_rejects_unapproved_executable(self):
        with tempfile.TemporaryDirectory() as directory:
            lease = Path(directory) / "lease"; lease.touch()
            with self.assertRaises(ValueError):
                run_guarded(["relative-command"], lease, 3)
