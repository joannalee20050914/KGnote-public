from __future__ import annotations

import importlib.util
import json
import os
import plistlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock


ROOT = Path(__file__).resolve().parents[2]


def load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ENTRYPOINT = load("collaboration_goal_entrypoint", "scripts/collaboration_goal_entrypoint.py")
INSTALLER = load(
    "install_collaboration_goal_entrypoint",
    "scripts/install_collaboration_goal_entrypoint.py",
)


class CollaborationGoalEntrypointTests(unittest.TestCase):
    def repository(self, root: Path) -> tuple[Path, str]:
        repo = root / "repo"
        repo.mkdir()
        subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=repo, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
        (repo / "scripts").mkdir()
        for name in (
            "collaboration_goal_entrypoint.py",
            "collaboration_goal_dispatch.py",
        ):
            (repo / "scripts" / name).write_bytes((ROOT / "scripts" / name).read_bytes())
        (repo / ".ai").mkdir()
        (repo / "goal.json").write_text("{}\n", encoding="utf-8")
        (repo / "state.json").write_text("{}\n", encoding="utf-8")
        (repo / "ledger.jsonl").write_text("", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=repo, check=True)
        subprocess.run(["git", "commit", "-m", "seed"], cwd=repo, check=True, capture_output=True)
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
        subprocess.run(["git", "checkout", "--detach", commit], cwd=repo, check=True, capture_output=True)
        return repo, commit

    @staticmethod
    def unloaded(command, **_kwargs):
        return subprocess.CompletedProcess(command, 3, "", "not loaded")

    def install(self, root: Path, repo: Path, commit: str, runner=None):
        return INSTALLER.install_disabled(
            repo=repo,
            expected_commit=commit,
            python=Path(sys.executable),
            launch_agents=root / "LaunchAgents",
            config_path=root / "runtime/entrypoint.json",
            receipt_path=root / "evidence/install.json",
            command_runner=runner or self.unloaded,
        )

    def test_disabled_install_never_bootstraps_and_entrypoint_stays_stopped(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo, commit = self.repository(root)
            runner = Mock(side_effect=self.unloaded)
            receipt = self.install(root, repo, commit, runner)
            commands = [call.args[0] for call in runner.call_args_list]
            self.assertTrue(all("bootstrap" not in command for command in commands))
            self.assertTrue(all("enable" not in command for command in commands))
            plist = plistlib.loads(Path(receipt["plist_path"]).read_bytes())
            self.assertEqual(INSTALLER.LABEL, plist["Label"])
            self.assertTrue(plist["Disabled"])
            self.assertFalse(plist["RunAtLoad"])
            self.assertFalse(plist["KeepAlive"])
            result = ENTRYPOINT.run_once(Path(receipt["config_path"]))
            self.assertEqual("STOPPED", result["status"])
            self.assertFalse(result["model_launch_started"])
            status = INSTALLER.read_status(
                Path(receipt["receipt_path"]), command_runner=self.unloaded,
            )
            self.assertEqual("STOPPED", status["status"])

    def test_install_fails_closed_when_legacy_o2_runner_is_loaded(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo, commit = self.repository(root)

            def loaded(command, **_kwargs):
                if command[-1].endswith(INSTALLER.LEGACY_O2_LABEL):
                    return subprocess.CompletedProcess(command, 0, "loaded", "")
                return subprocess.CompletedProcess(command, 3, "", "not loaded")

            with self.assertRaisesRegex(INSTALLER.EntrypointInstallError, "legacy O2"):
                self.install(root, repo, commit, loaded)
            self.assertFalse((root / "LaunchAgents").exists())

    def test_rollback_latches_stop_removes_only_new_activation_and_preserves_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo, commit = self.repository(root)
            receipt = self.install(root, repo, commit)
            marker = repo / ".ai/ORCHESTRATOR_STOP"
            marker.write_text("manual stop must be preserved\n", encoding="utf-8")
            marker_before = marker.read_bytes()
            preserved = {
                path.name: path.read_bytes()
                for path in (repo / "goal.json", repo / "state.json", repo / "ledger.jsonl")
            }
            loaded = {INSTALLER.LABEL: True, INSTALLER.LEGACY_O2_LABEL: False}
            calls = []

            def launchctl(command, **_kwargs):
                calls.append(command)
                label = command[-1].rsplit("/", 1)[-1]
                if command[1] == "print":
                    return subprocess.CompletedProcess(
                        command, 0 if loaded.get(label, False) else 3, "", "",
                    )
                if command[1] == "bootout" and label == INSTALLER.LABEL:
                    loaded[label] = False
                    return subprocess.CompletedProcess(command, 0, "", "")
                return subprocess.CompletedProcess(command, 2, "", "unexpected")

            rollback_receipt = root / "evidence/rollback.json"
            result = INSTALLER.rollback(
                Path(receipt["receipt_path"]),
                rollback_receipt_path=rollback_receipt,
                command_runner=launchctl,
            )
            self.assertEqual("STOPPED", result["status"])
            self.assertTrue(marker.is_file())
            self.assertEqual(marker_before, marker.read_bytes())
            self.assertTrue(result["stop_marker_preexisting"])
            self.assertFalse(Path(receipt["config_path"]).exists())
            self.assertFalse(Path(receipt["plist_path"]).exists())
            self.assertTrue(Path(receipt["receipt_path"]).is_file())
            self.assertTrue(rollback_receipt.is_file())
            for name, contents in preserved.items():
                self.assertEqual(contents, (repo / name).read_bytes())
            bootouts = [command for command in calls if command[1] == "bootout"]
            self.assertEqual(1, len(bootouts))
            self.assertTrue(bootouts[0][-1].endswith(INSTALLER.LABEL))
            self.assertFalse(any(INSTALLER.LEGACY_O2_LABEL in command[-1] for command in bootouts))


if __name__ == "__main__":
    unittest.main()
