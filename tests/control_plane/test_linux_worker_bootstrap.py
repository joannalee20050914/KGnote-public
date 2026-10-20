import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("bootstrap", ROOT / "scripts/linux_worker_bootstrap.py")
BOOTSTRAP = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(BOOTSTRAP)


class LinuxWorkerBootstrapTest(unittest.TestCase):
    def generic_identity(self):
        return {
            "schema_version":"kgnote.authorized-work-identity.v1",
            "repository":"joannalee20050914/KGnote-public", "issue":14,
            "goal_id":"GOAL-KGNOTE-D2-T07-TUTOR-HANDOFF-20261019", "work_item_id":"D2-T07",
            "branch":"codex/issue-14-tutor-handoff-feasibility", "worktree_slug":"issue-14-d2-t07",
            "authority_record":"https://github.com/joannalee20050914/KGnote-public/issues/14",
            "authority_sha256":"a"*64,
        }

    def test_generic_identity_creates_only_its_exact_private_leaf(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); generic=root/"work-items"; target=generic/"issue-14-d2-t07"
            with patch.object(BOOTSTRAP,"WORKTREE_ROOT",root), patch.object(BOOTSTRAP,"GENERIC_ROOT",generic):
                result=BOOTSTRAP.prepare("issue-14-d2-t07-codex-20261019","codex",target,self.generic_identity())
                self.assertEqual("READY",result["status"]); self.assertTrue(target.is_dir())
                changed=self.generic_identity(); changed["issue"]=15
                with self.assertRaisesRegex(BOOTSTRAP.BootstrapError,"inconsistent|identity-bound"):
                    BOOTSTRAP.prepare("issue-14-d2-t07-codex-20261019","codex",target,changed)
    def test_missing_directory_is_created_once_and_existing_content_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); target = root / "successor"
            with patch.object(BOOTSTRAP, "WORKTREE_ROOT", root), patch.object(BOOTSTRAP, "AUTHORIZED_WORKTREE", target):
                first = BOOTSTRAP.prepare("source-library-successor-codex-20261019", "codex", target)
                (target / "owned.txt").write_text("preserve\n")
                second = BOOTSTRAP.prepare("source-library-successor-codex-20261019", "codex", target)
            self.assertTrue(first["created"]); self.assertFalse(second["created"])
            self.assertEqual("preserve\n", (target / "owned.txt").read_text())

    def test_wrong_path_and_symlink_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); target = root / "successor"; elsewhere = root / "elsewhere"; elsewhere.mkdir()
            with patch.object(BOOTSTRAP, "WORKTREE_ROOT", root), patch.object(BOOTSTRAP, "AUTHORIZED_WORKTREE", target):
                with self.assertRaisesRegex(BOOTSTRAP.BootstrapError, "not authorized"):
                    BOOTSTRAP.prepare("source-library-successor-codex-20261019", "codex", elsewhere)
                target.symlink_to(elsewhere, target_is_directory=True)
                with self.assertRaisesRegex(BOOTSTRAP.BootstrapError, "symbolic link"):
                    BOOTSTRAP.prepare("source-library-successor-codex-20261019", "codex", target)

if __name__ == "__main__": unittest.main()
