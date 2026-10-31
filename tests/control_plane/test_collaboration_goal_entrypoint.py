from __future__ import annotations

import importlib.util
import fcntl
import hashlib
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
        if command[:2] == ["/bin/ps", "-axo"]:
            return subprocess.CompletedProcess(command, 0, "", "")
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

    def activate(self, receipt: dict[str, object]) -> tuple[Path, Path]:
        config_path = Path(str(receipt["config_path"]))
        plist_path = Path(str(receipt["plist_path"]))
        activation_path = Path(str(receipt["activation_record_path"]))
        config = json.loads(config_path.read_text(encoding="utf-8"))
        config.update({
            "status": ENTRYPOINT.ENABLED_STATUS,
            "product_goal": {
                "spec": "goal.json", "state": "state.json", "ledger": "ledger.jsonl",
            },
            "activation_authority": {
                "status": "APPROVED",
                "authorization_comment_id": 6537070839,
                "goal_spec_sha256": "8" * 64,
            },
        })
        config_path.write_text(
            json.dumps(config, indent=2, sort_keys=True) + "\n", encoding="utf-8",
        )
        plist = plistlib.loads(plist_path.read_bytes())
        plist["Disabled"] = False
        plist_path.write_bytes(plistlib.dumps(plist, fmt=plistlib.FMT_XML))
        activation = {
            "schema_version": ENTRYPOINT.ACTIVATION_SCHEMA,
            "status": ENTRYPOINT.ENABLED_STATUS,
            "engineering_goal_id": ENTRYPOINT.ENGINEERING_GOAL_ID,
            "install_receipt": str(receipt["receipt_path"]),
            "install_receipt_sha256": hashlib.sha256(
                Path(str(receipt["receipt_path"])).read_bytes()
            ).hexdigest(),
            "enabled_config_sha256": hashlib.sha256(config_path.read_bytes()).hexdigest(),
            "enabled_plist_sha256": hashlib.sha256(plist_path.read_bytes()).hexdigest(),
            "deployment": receipt["deployment"],
            "entrypoint_sha256": receipt["entrypoint_sha256"],
            "dispatcher_sha256": receipt["dispatcher_sha256"],
            "product_goal": config["product_goal"],
            "activation_authority": config["activation_authority"],
        }
        activation_path.write_text(
            json.dumps(activation, indent=2, sort_keys=True) + "\n", encoding="utf-8",
        )
        return config_path, activation_path

    @staticmethod
    def enabled_runner(command, **_kwargs):
        if command[:2] == ["/bin/ps", "-axo"]:
            return subprocess.CompletedProcess(command, 0, "", "")
        if command[:2] == ["/bin/launchctl", "print"]:
            return subprocess.CompletedProcess(command, 3, "", "not loaded")
        return subprocess.CompletedProcess(
            command, 0,
            json.dumps({
                "status": "DISPATCHED",
                "safety": {"model_launch_started": False},
            }),
            "",
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
                if command[:2] == ["/bin/ps", "-axo"]:
                    return subprocess.CompletedProcess(command, 0, "", "")
                if command[-1].endswith(INSTALLER.LEGACY_O2_LABEL):
                    return subprocess.CompletedProcess(command, 0, "loaded", "")
                return subprocess.CompletedProcess(command, 3, "", "not loaded")

            with self.assertRaisesRegex(INSTALLER.EntrypointInstallError, "legacy O2"):
                self.install(root, repo, commit, loaded)
            self.assertFalse((root / "LaunchAgents").exists())

    def test_install_rejects_already_loaded_new_service(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo, commit = self.repository(root)

            def loaded(command, **_kwargs):
                if command[:2] == ["/bin/ps", "-axo"]:
                    return subprocess.CompletedProcess(command, 0, "", "")
                if command[-1].endswith(INSTALLER.LABEL):
                    return subprocess.CompletedProcess(command, 0, "loaded", "")
                return subprocess.CompletedProcess(command, 3, "", "not loaded")

            with self.assertRaisesRegex(
                INSTALLER.EntrypointInstallError, "already loaded",
            ):
                self.install(root, repo, commit, loaded)

    def test_install_rejects_unexpected_model_process(self):
        commands = (
            "/home/kgnote/.local/bin/claude -p review",
            "/home/kgnote/.local/bin/codex exec --ephemeral",
        )
        for observed in commands:
            with self.subTest(observed=observed), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                repo, commit = self.repository(root)

                def process_present(command, **_kwargs):
                    if command[:2] == ["/bin/ps", "-axo"]:
                        return subprocess.CompletedProcess(
                            command, 0, f" 991 {observed}\n", "",
                        )
                    return subprocess.CompletedProcess(command, 3, "", "not loaded")

                with self.assertRaisesRegex(
                    INSTALLER.EntrypointInstallError, "unexpected model process",
                ):
                    self.install(root, repo, commit, process_present)

    def test_status_rejects_competing_writer(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo, commit = self.repository(root)
            receipt = self.install(root, repo, commit)
            lock_path = repo / "output/control-plane/collaboration-goal/writer.lock"
            lock_path.parent.mkdir(parents=True)
            with lock_path.open("a+", encoding="utf-8") as lock:
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                with self.assertRaisesRegex(
                    INSTALLER.EntrypointInstallError, "another collaboration Goal writer",
                ):
                    INSTALLER.read_status(
                        Path(str(receipt["receipt_path"])), command_runner=self.unloaded,
                    )

    def test_exact_activation_runs_only_receipt_bound_reviewed_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo, commit = self.repository(root)
            receipt = self.install(root, repo, commit)
            config_path, _ = self.activate(receipt)
            status = INSTALLER.read_status(
                Path(str(receipt["receipt_path"])), command_runner=self.unloaded,
            )
            self.assertEqual("ENABLED_NOT_LOADED", status["status"])
            result = ENTRYPOINT.run_once(
                config_path, now="2026-11-02T09:00:00+08:00",
                command_runner=self.enabled_runner,
            )
            self.assertEqual("DISPATCHED", result["status"])
            self.assertFalse(result["model_launch_started"])

    def test_enabled_path_rejects_activation_and_deployed_byte_drift(self):
        drift_cases = (
            ("activation", "activation record mismatch"),
            ("entrypoint", "clean|entrypoint bytes drifted"),
            ("dispatcher", "clean|dispatcher bytes drifted"),
        )
        for target, message in drift_cases:
            with self.subTest(target=target), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                repo, commit = self.repository(root)
                receipt = self.install(root, repo, commit)
                config_path, activation_path = self.activate(receipt)
                if target == "activation":
                    activation = json.loads(activation_path.read_text(encoding="utf-8"))
                    activation["dispatcher_sha256"] = "0" * 64
                    activation_path.write_text(json.dumps(activation), encoding="utf-8")
                else:
                    filename = {
                        "entrypoint": "collaboration_goal_entrypoint.py",
                        "dispatcher": "collaboration_goal_dispatch.py",
                    }[target]
                    path = repo / "scripts" / filename
                    path.write_text(path.read_text(encoding="utf-8") + "# drift\n", encoding="utf-8")
                with self.assertRaisesRegex(ENTRYPOINT.EntrypointError, message):
                    ENTRYPOINT.run_once(config_path, command_runner=self.enabled_runner)

    def test_status_and_enabled_run_reject_deployment_head_drift(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo, commit = self.repository(root)
            receipt = self.install(root, repo, commit)
            config_path, _ = self.activate(receipt)
            (repo / "drift.txt").write_text("different tree\n", encoding="utf-8")
            subprocess.run(["git", "add", "drift.txt"], cwd=repo, check=True)
            subprocess.run(
                ["git", "commit", "-m", "drift"], cwd=repo,
                check=True, capture_output=True,
            )
            with self.assertRaisesRegex(
                INSTALLER.EntrypointInstallError, "HEAD differs",
            ):
                INSTALLER.read_status(
                    Path(str(receipt["receipt_path"])), command_runner=self.unloaded,
                )
            with self.assertRaisesRegex(ENTRYPOINT.EntrypointError, "HEAD differs"):
                ENTRYPOINT.run_once(config_path, command_runner=self.enabled_runner)

    def test_status_rejects_reviewed_dispatcher_byte_drift(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo, commit = self.repository(root)
            receipt = self.install(root, repo, commit)
            dispatcher = repo / "scripts/collaboration_goal_dispatch.py"
            dispatcher.write_text(
                dispatcher.read_text(encoding="utf-8") + "# drift\n", encoding="utf-8",
            )
            with self.assertRaisesRegex(
                INSTALLER.EntrypointInstallError, "clean|dispatcher bytes drifted",
            ):
                INSTALLER.read_status(
                    Path(str(receipt["receipt_path"])), command_runner=self.unloaded,
                )

    def test_stop_marker_blocks_enabled_restart_without_dispatch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo, commit = self.repository(root)
            receipt = self.install(root, repo, commit)
            config_path, _ = self.activate(receipt)
            marker = repo / ".ai/ORCHESTRATOR_STOP"
            marker.write_text("manual stop\n", encoding="utf-8")
            runner = Mock(side_effect=self.enabled_runner)
            first = ENTRYPOINT.run_once(config_path, command_runner=runner)
            second = ENTRYPOINT.run_once(
                config_path, now="2026-11-03T09:00:00+08:00", command_runner=runner,
            )
            self.assertEqual("STOPPED", first["status"])
            self.assertEqual("STOPPED", second["status"])
            runner.assert_not_called()

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
            with self.assertRaisesRegex(ENTRYPOINT.EntrypointError, "config is absent"):
                ENTRYPOINT.run_once(Path(str(receipt["config_path"])))
            self.assertTrue(marker.is_file())
            for name, contents in preserved.items():
                self.assertEqual(contents, (repo / name).read_bytes())
            bootouts = [command for command in calls if command[1] == "bootout"]
            self.assertEqual(1, len(bootouts))
            self.assertTrue(bootouts[0][-1].endswith(INSTALLER.LABEL))
            self.assertFalse(any(INSTALLER.LEGACY_O2_LABEL in command[-1] for command in bootouts))

    def test_enabled_rollback_removes_activation_and_cannot_resurrect(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo, commit = self.repository(root)
            receipt = self.install(root, repo, commit)
            config_path, activation_path = self.activate(receipt)
            rollback_receipt = root / "evidence/rollback-enabled.json"
            result = INSTALLER.rollback(
                Path(str(receipt["receipt_path"])),
                rollback_receipt_path=rollback_receipt,
                command_runner=self.unloaded,
            )
            self.assertEqual("STOPPED", result["status"])
            self.assertFalse(config_path.exists())
            self.assertFalse(activation_path.exists())
            self.assertTrue((repo / ".ai/ORCHESTRATOR_STOP").is_file())
            with self.assertRaisesRegex(ENTRYPOINT.EntrypointError, "config is absent"):
                ENTRYPOINT.run_once(config_path, command_runner=self.enabled_runner)

    def test_rollback_latches_stop_before_refusing_drifted_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo, commit = self.repository(root)
            receipt = self.install(root, repo, commit)
            config_path = Path(str(receipt["config_path"]))
            config_path.write_text("{}\n", encoding="utf-8")
            with self.assertRaises(INSTALLER.EntrypointInstallError):
                INSTALLER.rollback(
                    Path(str(receipt["receipt_path"])),
                    rollback_receipt_path=root / "evidence/rollback-drift.json",
                    command_runner=self.unloaded,
                )
            self.assertTrue((repo / ".ai/ORCHESTRATOR_STOP").is_file())
            self.assertTrue(config_path.is_file())


if __name__ == "__main__":
    unittest.main()
