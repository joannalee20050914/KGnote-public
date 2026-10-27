import importlib.util
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("bootstrap", ROOT / "scripts/linux_worker_bootstrap.py")
BOOTSTRAP = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(BOOTSTRAP)


class LinuxWorkerBootstrapTest(unittest.TestCase):
    def product_identity(self, event, *, work_item="WI-O2-B-REVIEW", provider="claude", stage="claude", commit="1" * 40):
        return {
            "schema_version":"kgnote.authorized-product-goal-work-identity.v1",
            "identity_kind":"KGNOTE_PRODUCT_GOAL", "authority_kind":"GITHUB_OWNER_APPROVAL",
            "repository":"joannalee20050914/KGnote-public", "issue":9,
            "goal_id":"GOAL-KGNOTE-O2-READING-EXPERIENCE",
            "goal_version":"2026-10-23.2-s0-s2-proposal",
            "goal_spec_sha256":"82716b31f004f108c935169493f2fa918e5144f12419302ba2c9fdcec91b6604",
            "work_item_id":work_item, "provider":provider, "stage":stage,
            "order_event_id":event, "branch":"codex/o2-reading-experience",
            "candidate_commit":commit, "candidate_fingerprint":"2"*64,
            "worktree_slug":"goal-o2-reading-experience",
            "authority_record":"https://github.com/joannalee20050914/KGnote-public/issues/9",
            "authority_sha256":"d"*64, "authority_status":"APPROVED",
            "authority_action":"APPROVE", "go_live_authorized":True,
        }

    def test_o2_bootstrap_creates_only_exact_product_goal_leaf(self):
        event = "o2-wi-o2-b-review-claude-0123456789abcdef"
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); generic=root/"work-items"; target=generic/"goal-o2-reading-experience"
            identity=self.product_identity(event)
            checkout={"status":"CHECKOUT_READY","cloned":False}
            with patch.object(BOOTSTRAP,"WORKTREE_ROOT",root), patch.object(BOOTSTRAP,"GENERIC_ROOT",generic), patch.object(BOOTSTRAP,"_prepare_product_checkout",return_value=checkout):
                result=BOOTSTRAP.prepare(event,"claude",target,identity)
                self.assertEqual("READY",result["status"])
                self.assertEqual(checkout,result["checkout"])
                with self.assertRaisesRegex(BOOTSTRAP.BootstrapError,"outside the exact authorized path"):
                    BOOTSTRAP.prepare(event,"claude",generic/"escape",identity)

    def _seed_repository(self, root: Path):
        source=root/"source"; origin=root/"origin.git"; source.mkdir()
        subprocess.run(["git","init","-b","codex/o2-reading-experience"],cwd=source,check=True,capture_output=True)
        subprocess.run(["git","config","user.email","test@example.invalid"],cwd=source,check=True)
        subprocess.run(["git","config","user.name","Test"],cwd=source,check=True)
        (source/"seed.txt").write_text("seed\n")
        subprocess.run(["git","add","seed.txt"],cwd=source,check=True)
        subprocess.run(["git","commit","-m","seed"],cwd=source,check=True,capture_output=True)
        commit=subprocess.check_output(["git","rev-parse","HEAD"],cwd=source,text=True).strip()
        subprocess.run(["git","clone","--bare",str(source),str(origin)],check=True,capture_output=True)
        return source,origin,commit

    def test_product_checkout_is_cloned_once_reused_and_dirty_bytes_fail_closed(self):
        event="o2-wi-o2-a-implement-codex-0123456789abcdef"
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); source,origin,commit=self._seed_repository(root)
            generic=root/"work-items"; target=generic/"goal-o2-reading-experience"
            identity=self.product_identity(
                event,work_item="WI-O2-A-IMPLEMENT",provider="codex",stage="codex",commit=commit,
            )
            with patch.object(BOOTSTRAP,"WORKTREE_ROOT",root), patch.object(BOOTSTRAP,"GENERIC_ROOT",generic), patch.object(BOOTSTRAP,"PRODUCT_REPOSITORY_URL",str(origin)):
                first=BOOTSTRAP.prepare(event,"codex",target,identity)
                second=BOOTSTRAP.prepare(event,"codex",target,identity)
                self.assertTrue(first["checkout"]["cloned"])
                self.assertFalse(second["checkout"]["cloned"])
                self.assertEqual(commit,second["checkout"]["commit"])
                self.assertEqual(str((target/".git").resolve()),second["checkout"]["git_common_dir"])
                (target/"dirty.txt").write_text("do not overwrite\n")
                with self.assertRaisesRegex(BOOTSTRAP.BootstrapError,"dirty"):
                    BOOTSTRAP.prepare(event,"codex",target,identity)
                self.assertEqual("do not overwrite\n",(target/"dirty.txt").read_text())

    def test_product_checkout_rejects_linked_worktree_common_directory(self):
        event="o2-wi-o2-a-implement-codex-0123456789abcdef"
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); source,origin,commit=self._seed_repository(root)
            generic=root/"work-items"; generic.mkdir(); target=generic/"goal-o2-reading-experience"
            subprocess.run(["git","worktree","add","--detach",str(target),commit],cwd=source,check=True,capture_output=True)
            identity=self.product_identity(
                event,work_item="WI-O2-A-IMPLEMENT",provider="codex",stage="codex",commit=commit,
            )
            with patch.object(BOOTSTRAP,"WORKTREE_ROOT",root), patch.object(BOOTSTRAP,"GENERIC_ROOT",generic), patch.object(BOOTSTRAP,"PRODUCT_REPOSITORY_URL",str(origin)):
                with self.assertRaisesRegex(BOOTSTRAP.BootstrapError,"common directory"):
                    BOOTSTRAP.prepare(event,"codex",target,identity)

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
