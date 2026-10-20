import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import linux_landlock_exec as landlock


class LinuxLandlockExecTest(unittest.TestCase):
    def test_access_masks_cover_read_write_creation_reference_and_truncate(self):
        self.assertEqual(landlock.HANDLED_ACCESS, landlock.READ_ACCESS | landlock.WRITE_ACCESS)
        for required in (
            landlock.ACCESS_READ_FILE,
            landlock.ACCESS_READ_DIR,
            landlock.ACCESS_WRITE_FILE,
            landlock.ACCESS_MAKE_REG,
            landlock.ACCESS_REMOVE_FILE,
            landlock.ACCESS_REFER,
            landlock.ACCESS_TRUNCATE,
        ):
            self.assertEqual(required, landlock.HANDLED_ACCESS & required)

    def test_non_linux_fails_closed(self):
        with mock.patch.object(landlock.platform, "system", return_value="Darwin"):
            with self.assertRaisesRegex(landlock.LandlockError, "only on Linux"):
                landlock.restrict_filesystem([], [])
