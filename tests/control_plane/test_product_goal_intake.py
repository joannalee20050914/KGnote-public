from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
MODULE = importlib.util.spec_from_file_location(
    "product_goal_intake", ROOT / "scripts/product_goal_intake.py"
)
INTAKE = importlib.util.module_from_spec(MODULE)
sys.modules[MODULE.name] = INTAKE
MODULE.loader.exec_module(INTAKE)

from tests.control_plane.test_goal_continuity import product_goal_spec
from tests.control_plane.test_github_product_goal_control import comment

NOW = datetime(2026, 11, 2, 9, 30, tzinfo=ZoneInfo("Asia/Taipei"))


def write(path: Path, value: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")
    return path


def pin(path: Path) -> dict[str, str]:
    return {"path": str(path.resolve()), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


class GenericProductGoalIntakeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        root = Path(self.temporary.name)
        self.repo = root / "repo"
        self.repo.mkdir()
        self.private = root / "private"
        self.private.mkdir()
        self.spec = product_goal_spec()
        self.spec["dependencies"] = ["O2-ISOLATION-RECEIPT"]
        self.spec_path = write(self.repo / "goal.json", self.spec)
        self.stop_marker = self.repo / "stop-marker"
        self.source = self.private / "selected.md"
        self.source.write_text("Private original retained locally.\n", encoding="utf-8")
        self.source_receipt = write(self.private / "source-selection.json", {
            "goal_id": self.spec["goal_id"],
            "goal_spec_sha256": INTAKE.goal.goal_spec_sha256(self.spec),
            "selected_by_owner": True,
            "source": pin(self.source),
        })
        self.o2_state = write(self.private / "o2-state.json", {"status": "ACTIVE"})
        self.o2_ledger = self.private / "o2-ledger.jsonl"
        self.o2_ledger.write_text('{"event":"preserved"}\n', encoding="utf-8")
        self.dependency = write(self.private / "dependency.json", {
            "dependency_id": "O2-ISOLATION-RECEIPT", "status": "PASS",
        })
        self.lock = self.private / "global-writer.lock"
        self.lock.write_bytes(b"")
        self.guard = {
            "schema_version": "kgnote.product-goal-isolation-guard.v1",
            "goal_id": self.spec["goal_id"],
            "goal_spec_sha256": INTAKE.goal.goal_spec_sha256(self.spec),
            "legacy_o2": {"state": pin(self.o2_state), "ledger": pin(self.o2_ledger)},
            "private_source_selection": {"receipt": pin(self.source_receipt)},
            "dependencies": {"O2-ISOLATION-RECEIPT": pin(self.dependency)},
            "product_runtime": {
                "state": str(self.private / "new-state.json"),
                "ledger": str(self.private / "new-ledger.jsonl"),
                "writer_lock": str(self.lock),
            },
        }
        self.guard_path = write(self.private / "guard.json", self.guard)
        self.commands = []
        self.o2_loaded = False
        self.comments = [comment(self.spec)]

    def runner(self, cmd, **kwargs):
        self.commands.append(cmd)
        if cmd[:1] == ["git"]:
            return subprocess.CompletedProcess(
                cmd, 0, stdout="https://github.com/owner/repo.git\n", stderr=""
            )
        if cmd[:2] == ["/bin/launchctl", "print"]:
            return subprocess.CompletedProcess(
                cmd, 0 if self.o2_loaded else 113, stdout="", stderr=""
            )
        raise AssertionError("unexpected subprocess (possibly model dispatch)")

    def inspect(self, *, now=NOW):
        return INTAKE.inspect(
            repo=self.repo, spec_relative="goal.json", guard_path=self.guard_path,
            guard_sha256=pin(self.guard_path)["sha256"], stop_marker=self.stop_marker,
            now=now, comments_fetcher=lambda spec: deepcopy(self.comments),
            runner=self.runner,
        )

    def test_valid_owner_private_selection_o2_isolation_without_model(self):
        before = (self.o2_state.read_bytes(), self.o2_ledger.read_bytes(),
                  self.guard_path.read_bytes())
        first = self.inspect()
        second = self.inspect()
        self.assertEqual("ADMISSION_ELIGIBLE_NO_MODEL_ONLY", first["status"])
        self.assertEqual(first, second)
        self.assertTrue(first["no_model_gate"])
        self.assertFalse(first["model_launch_started"])
        self.assertFalse(first["model_reservation_created"])
        self.assertFalse(first["product_goal_dispatched"])
        self.assertFalse(first["paid_api_used"])
        self.assertEqual(before, (self.o2_state.read_bytes(),
                                  self.o2_ledger.read_bytes(),
                                  self.guard_path.read_bytes()))
        self.assertEqual(0, len(list(self.repo.glob("output/**/*"))))
        self.assertFalse(any("codex" in " ".join(cmd).lower() or
                             "claude" in " ".join(cmd).lower()
                             for cmd in self.commands))

    def test_no_owner_approval_means_no_isolation_or_model_work(self):
        self.comments = []
        self.guard_path.unlink()
        result = self.inspect()
        self.assertEqual("WAITING_AUTHORIZATION", result["status"])
        self.assertFalse(result["product_goal_dispatched"])

    def test_wrong_owner_and_digest_fail_closed(self):
        self.comments = [comment(self.spec, author_association="CONTRIBUTOR")]
        with self.assertRaises(INTAKE.IntakeBlocked):
            self.inspect()
        self.comments = [comment(self.spec, payload={"goal_spec_sha256": "f" * 64})]
        with self.assertRaises(INTAKE.IntakeBlocked):
            self.inspect()

    def test_work_window_and_stop_marker_precede_external_checks(self):
        self.assertEqual(
            "WAITING_WORK_WINDOW",
            self.inspect(now=datetime(2026, 11, 1, 9, 30, tzinfo=ZoneInfo("Asia/Taipei")))["status"]
        )
        self.commands.clear()
        self.stop_marker.write_text("STOP\n", encoding="utf-8")
        self.assertEqual("STOPPED", self.inspect()["status"])
        self.assertEqual([], self.commands)

    def test_tampered_o2_bytes_and_source_are_rejected(self):
        self.o2_state.write_text('{"status":"tampered"}', encoding="utf-8")
        with self.assertRaises(INTAKE.IntakeBlocked):
            self.inspect()
        self.o2_state.write_text('{"status":"ACTIVE"}', encoding="utf-8")
        self.source.write_text("different private bytes", encoding="utf-8")
        with self.assertRaises(INTAKE.IntakeBlocked):
            self.inspect()

    def test_missing_selection_or_dependency_fails_closed(self):
        self.guard["private_source_selection"] = {}
        write(self.guard_path, self.guard)
        self.assertEqual("WAITING_ISOLATION_OR_SOURCE", self.inspect()["status"])
        self.guard["private_source_selection"] = {"receipt": pin(self.source_receipt)}
        self.guard["dependencies"] = {}
        write(self.guard_path, self.guard)
        self.assertEqual("WAITING_ISOLATION_OR_SOURCE", self.inspect()["status"])

    def test_o2_loaded_and_competing_global_writer_are_refused(self):
        self.o2_loaded = True
        self.assertEqual("WAITING_ISOLATION_OR_SOURCE", self.inspect()["status"])
        self.o2_loaded = False
        self.guard["product_runtime"]["state"] = str(self.o2_state)
        write(self.guard_path, self.guard)
        with self.assertRaises(INTAKE.IntakeBlocked):
            self.inspect()

    def test_public_checkout_cannot_hold_private_isolation_guard(self):
        self.guard_path = write(self.repo / "public-guard.json", self.guard)
        with self.assertRaises(INTAKE.IntakeBlocked):
            self.inspect()

    def test_untrusted_repo_and_symlink_are_rejected(self):
        original = self.runner

        def wrong_remote(cmd, **kwargs):
            if cmd[:1] == ["git"]:
                return subprocess.CompletedProcess(cmd, 0, stdout="https://github.com/other/repo.git\n")
            return original(cmd, **kwargs)

        with self.assertRaises(INTAKE.IntakeBlocked):
            INTAKE.inspect(
                repo=self.repo, spec_relative="goal.json", guard_path=self.guard_path,
                guard_sha256=pin(self.guard_path)["sha256"],
                stop_marker=self.stop_marker, now=NOW,
                comments_fetcher=lambda _: deepcopy(self.comments),
                runner=wrong_remote,
            )
        link = self.repo / "linked-goal.json"
        link.symlink_to(self.spec_path)
        with self.assertRaises(INTAKE.IntakeBlocked):
            INTAKE.inspect(
                repo=self.repo, spec_relative="linked-goal.json",
                guard_path=self.guard_path, guard_sha256=pin(self.guard_path)["sha256"],
                stop_marker=self.stop_marker, now=NOW,
                comments_fetcher=lambda _: deepcopy(self.comments),
                runner=self.runner,
            )


if __name__ == "__main__":
    unittest.main()
