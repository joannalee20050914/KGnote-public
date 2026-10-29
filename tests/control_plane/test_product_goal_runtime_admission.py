from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import linux_worker_router as ROUTER
import product_goal_runtime_admission as ADMISSION
from tests.control_plane.runtime_admission_fixtures import runtime_identity


NOW = datetime(2026, 10, 29, 10, 0, tzinfo=ZoneInfo("Asia/Taipei"))


class Process:
    def __init__(self, stdout: str, stderr: str, returncode: int):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode

    def communicate(self, timeout=None):
        return self.stdout, self.stderr

    def terminate(self):
        return None

    def kill(self):
        return None


class ProductGoalRuntimeAdmissionTest(unittest.TestCase):
    def runtime(self, root: Path) -> tuple[dict, Path, Path]:
        revision = "9" * 40
        generation = root / ADMISSION.RUNTIME_RELEASES / revision
        generation.mkdir(parents=True)
        files = {}
        for name in sorted(ADMISSION.REQUIRED_GENERATION_FILES):
            path = generation / name
            path.write_text(f"reviewed:{name}\n", encoding="utf-8")
            files[name] = hashlib.sha256(path.read_bytes()).hexdigest()
        current = root / ADMISSION.RUNTIME_CURRENT
        current.symlink_to(Path(ADMISSION.RUNTIME_RELEASES) / revision)
        receipt = {
            "schema_version": ADMISSION.DEPLOYMENT_RECEIPT_SCHEMA,
            "status": "PASS",
            "model_launches": 0,
            "worker_runtime": {
                "reviewed_revision": revision,
                "reviewed_source": {
                    "head": revision,
                    "tree": "8" * 40,
                },
                "manifest_sha256": "7" * 64,
                "files": files,
            },
        }
        receipt_path = root / ADMISSION.DEPLOYMENT_RECEIPT
        receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
        return receipt, generation, receipt_path

    def deployment_request(self) -> dict:
        return ADMISSION.build_deployment_request(
            runtime_identity=runtime_identity(),
            challenge="5" * 64,
            candidate_commit="a" * 40,
            candidate_fingerprint="b" * 64,
            candidate_branch="codex/o2-runtime-receipt-pre-reservation-20261029",
            candidate_tree="c" * 40,
        )

    def test_runtime_discovery_binds_current_generation_receipt_lock_and_hashes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _receipt, generation, receipt_path = self.runtime(root)
            identity = ADMISSION.discover_runtime(root)
            self.assertEqual(str(generation.resolve()), identity["generation"])
            self.assertEqual(
                hashlib.sha256(receipt_path.read_bytes()).hexdigest(),
                identity["deployment_receipt_sha256"],
            )
            self.assertEqual(
                identity["files"]["requirements-runtime.lock"],
                identity["requirements_lock_sha256"],
            )
            self.assertEqual(0, identity["deployment_model_launches"])

    def test_runtime_discovery_rejects_missing_module_missing_lock_and_hash_drift(self):
        cases = (
            ("missing module", "linux_worker_guard.py", None, "file is absent"),
            ("missing lock", "requirements-runtime.lock", None, "file is absent"),
            ("hash drift", "product_goal_worker_lane.py", "tampered\n", "hash drifted"),
        )
        for label, name, replacement, error in cases:
            with self.subTest(label=label), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                _receipt, generation, _receipt_path = self.runtime(root)
                path = generation / name
                if replacement is None:
                    path.unlink()
                else:
                    path.write_text(replacement, encoding="utf-8")
                with self.assertRaisesRegex(ADMISSION.RuntimeAdmissionError, error):
                    ADMISSION.discover_runtime(root)

    def test_live_runtime_generation_drift_rejects_previously_admitted_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            receipt, generation, receipt_path = self.runtime(root)
            admitted = ADMISSION.discover_runtime(root)
            replacement_revision = "d" * 40
            replacement = generation.parent / replacement_revision
            replacement.mkdir()
            for name in admitted["files"]:
                (replacement / name).write_bytes((generation / name).read_bytes())
            current = root / ADMISSION.RUNTIME_CURRENT
            current.unlink()
            current.symlink_to(
                Path(ADMISSION.RUNTIME_RELEASES) / replacement_revision,
            )
            receipt["worker_runtime"]["reviewed_revision"] = replacement_revision
            receipt["worker_runtime"]["reviewed_source"]["head"] = replacement_revision
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            with self.assertRaisesRegex(
                ADMISSION.RuntimeAdmissionError, "differs from the admitted identity",
            ):
                ADMISSION.require_live_runtime_identity(admitted, runtime_root=root)

    def test_deployment_admission_is_paused_separate_and_never_model_bearing(self):
        with tempfile.TemporaryDirectory() as directory:
            receipt_path = Path(directory) / "deployment-admission.json"
            request = self.deployment_request()
            order = ROUTER.admission_order_for_deployment(
                request, receipt_path=receipt_path,
            )
            identity = order.bootstrap_identity
            self.assertEqual("PAUSED", identity["authority_lease"])
            self.assertFalse(identity["go_live_authorized"])
            self.assertFalse(identity["formal_dispatch_authorized"])
            self.assertIsNone(identity["product_goal_identity"])
            self.assertIsNone(identity["product_goal_context"])
            self.assertEqual("admission", order.stage)
            self.assertFalse(any(
                Path(token).name in {"codex", "claude", "codex.js"}
                for token in order.command
            ))
            for field, value in (
                ("authority_lease", "ACTIVE"),
                ("go_live_authorized", True),
                ("formal_dispatch_authorized", True),
            ):
                invalid = {**request, field: value}
                with self.assertRaisesRegex(
                    ADMISSION.RuntimeAdmissionError, "PAUSE boundary",
                ):
                    ADMISSION.validate_deployment_request(invalid)

    def test_ssh_and_bootstrap_fail_before_worker_or_model_process(self):
        calls = []
        with self.assertRaisesRegex(ROUTER.RoutingError, "discovery failed"):
            ROUTER.discover_runtime_via_guest(
                run=lambda command, **kwargs: subprocess.CompletedProcess(
                    command, 255, "", "ssh unavailable",
                )
            )
        with tempfile.TemporaryDirectory() as directory:
            receipt_path = Path(directory) / "receipt.json"
            order = ROUTER.admission_order_for_deployment(
                self.deployment_request(), receipt_path=receipt_path,
            )
            popen = Mock()

            def bootstrap_failure(command, **kwargs):
                calls.append(command)
                return subprocess.CompletedProcess(command, 2, "", "bootstrap failed")

            with self.assertRaisesRegex(ROUTER.RoutingError, "did not complete"):
                ROUTER.route_admission(
                    order, receipt_path=receipt_path,
                    run=bootstrap_failure, popen=popen, now=lambda: NOW,
                )
            popen.assert_not_called()
            self.assertEqual(1, len(calls))

    def test_landlock_worker_failure_cannot_fall_back_or_start_model(self):
        with tempfile.TemporaryDirectory() as directory:
            receipt_path = Path(directory) / "receipt.json"
            order = ROUTER.admission_order_for_deployment(
                self.deployment_request(), receipt_path=receipt_path,
            )
            launched = []

            def run(command, **kwargs):
                if "linux_worker_bootstrap.py" in command[-1]:
                    return subprocess.CompletedProcess(command, 0, json.dumps({
                        "status": "READY",
                        "development_environment": {
                            "status": "DEVELOPMENT_ENVIRONMENT_READY",
                        },
                    }), "")
                return subprocess.CompletedProcess(command, 0, "", "")

            def popen(command, **kwargs):
                launched.append(command)
                return Process("", "landlock denied", 1)

            with self.assertRaisesRegex(ROUTER.RoutingError, "did not complete"):
                ROUTER.route_admission(
                    order, receipt_path=receipt_path,
                    run=run, popen=popen, now=lambda: NOW,
                )
            self.assertEqual(1, len(launched))
            remote = launched[0][-1]
            self.assertIn("linux_landlock_exec.py", remote)
            self.assertIn("product_goal_worker_lane.py", remote)
            self.assertNotIn("kgnote-successor-codex", remote)
            self.assertNotIn("claude_reviewer_adapter", remote)
            checkpoint = json.loads(order.checkpoint_path.read_text())
            self.assertFalse(checkpoint["host_fallback_used"])
            self.assertEqual("FAILED_CLOSED", checkpoint["status"])


if __name__ == "__main__":
    unittest.main()
