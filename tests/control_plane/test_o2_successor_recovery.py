from __future__ import annotations

import hashlib
import json
import plistlib
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import codex_control
import goal_continuity
import o2_successor_recovery as RECOVERY
import o2_prepublication_control_tests as PREPUBLICATION_TESTS
from tests.control_plane.test_github_product_goal_control import comment
from tests.control_plane.runtime_admission_fixtures import runtime_identity


class O2SuccessorRecoveryTest(unittest.TestCase):
    def test_deferred_remote_identity_test_set_is_exact_and_shared(self):
        self.assertEqual(
            RECOVERY.codex_control.O2_DEFERRED_REMOTE_PUBLICATION_TESTS,
            PREPUBLICATION_TESTS.DEFERRED_REMOTE_PUBLICATION_TESTS,
        )

    def make_bundle(self, root: Path) -> tuple[Path, dict[str, str]]:
        repo = root / "repo"
        subprocess.run(
            ["git", "init", "-b", RECOVERY.PRODUCT_BRANCH, str(repo)],
            check=True,
            capture_output=True,
        )
        subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@example.invalid"], check=True)
        subprocess.run(["git", "-C", str(repo), "config", "user.name", "KGnote Test"], check=True)
        (repo / "seed.txt").write_text("seed\n")
        subprocess.run(["git", "-C", str(repo), "add", "seed.txt"], check=True)
        subprocess.run(["git", "-C", str(repo), "commit", "-qm", "parent"], check=True)
        parent = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
        (repo / "candidate.txt").write_text("candidate\n")
        subprocess.run(["git", "-C", str(repo), "add", "candidate.txt"], check=True)
        subprocess.run(["git", "-C", str(repo), "commit", "-qm", "successor"], check=True)
        commit = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
        tree = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD^{tree}"], text=True).strip()
        fingerprint = codex_control.repository_fingerprint(repo)["value"]
        bundle = root / "successor.bundle"
        subprocess.run(["git", "-C", str(repo), "bundle", "create", str(bundle), "HEAD"], check=True)
        return bundle, {
            "commit": commit,
            "parent": parent,
            "tree": tree,
            "fingerprint": fingerprint,
            "bundle_sha256": hashlib.sha256(bundle.read_bytes()).hexdigest(),
        }

    def test_bundle_accepts_exact_identity_and_rejects_wrong_commit_parent_tree_or_fingerprint(self):
        with tempfile.TemporaryDirectory() as directory:
            bundle, identity = self.make_bundle(Path(directory))
            exact = {
                "BUNDLE_SHA256": identity["bundle_sha256"],
                "SUCCESSOR_COMMIT": identity["commit"],
                "ORIGINAL_COMMIT": identity["parent"],
                "SUCCESSOR_TREE": identity["tree"],
                "SUCCESSOR_FINGERPRINT": identity["fingerprint"],
            }
            patches = [patch.object(RECOVERY, name, value) for name, value in exact.items()]
            for item in patches:
                item.start()
            try:
                self.assertEqual(identity["commit"], RECOVERY.validate_bundle(bundle)["commit"])
                for name, wrong in (
                    ("SUCCESSOR_COMMIT", "0" * 40),
                    ("ORIGINAL_COMMIT", "1" * 40),
                    ("SUCCESSOR_TREE", "2" * 40),
                    ("SUCCESSOR_FINGERPRINT", "3" * 64),
                ):
                    with self.subTest(name=name), patch.object(RECOVERY, name, wrong):
                        with self.assertRaisesRegex(RECOVERY.RecoveryError, "mismatch"):
                            RECOVERY.validate_bundle(bundle)
            finally:
                for item in reversed(patches):
                    item.stop()

    def test_bundle_tamper_and_missing_checkpoint_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle, identity = self.make_bundle(root)
            with bundle.open("ab") as handle:
                handle.write(b"tamper")
            with patch.object(RECOVERY, "BUNDLE_SHA256", identity["bundle_sha256"]):
                with self.assertRaisesRegex(RECOVERY.RecoveryError, "SHA-256 drift"):
                    RECOVERY.validate_bundle(bundle)
            with patch.object(
                RECOVERY,
                "RECOVERY_EVIDENCE_SHA256",
                {"missing-checkpoint.json": "0" * 64},
            ):
                with self.assertRaisesRegex(RECOVERY.RecoveryError, "missing"):
                    RECOVERY.validate_preserved_evidence(root)

    def test_live_owner_authority_body_drift_is_rejected(self):
        spec = json.loads(
            (ROOT / "docs/control-plane/O2_BOUNDED_TRIAL_GOAL_SPEC_v2026-10-29.4.json").read_text()
        )
        authority_comment = comment(spec, login="joannalee20050914")
        authority_comment["html_url"] = (
            "https://github.com/joannalee20050914/KGnote-public/"
            "issues/9#issuecomment-100"
        )
        authority_comment["issue_url"] = (
            "https://api.github.com/repos/joannalee20050914/KGnote-public/issues/9"
        )
        body_sha = hashlib.sha256(authority_comment["body"].encode()).hexdigest()
        with patch.object(RECOVERY, "OWNER_COMMENT_ID", authority_comment["id"]), patch.object(
            RECOVERY, "OWNER_BODY_SHA256", body_sha
        ):
            accepted = RECOVERY.resolve_live_authority(
                spec, comments_fetcher=lambda _spec: [authority_comment]
            )
            self.assertEqual("ACTIVE", accepted["authority_lease"])
            drifted = {**authority_comment, "body": authority_comment["body"] + "\n"}
            with self.assertRaisesRegex(RECOVERY.RecoveryError, "drifted"):
                RECOVERY.resolve_live_authority(
                    spec, comments_fetcher=lambda _spec: [drifted]
                )

    def test_ledger_cursor_drift_is_rejected_before_recovery(self):
        spec = {"goal_id": RECOVERY.GOAL_ID, "goal_version": RECOVERY.GOAL_VERSION}
        state = {
            "event_cursor": {"sequence": RECOVERY.FORMAL_LEDGER_CURSOR - 1},
            "authority_lease": "ACTIVE",
            "lifecycle": {"state": "ACTIVE"},
        }
        ledger = [{} for _ in range(RECOVERY.FORMAL_LEDGER_CURSOR)]
        with patch.object(RECOVERY.goal_continuity, "goal_spec_sha256", return_value=RECOVERY.GOAL_SPEC_SHA256), patch.object(
            RECOVERY.goal_continuity, "validate_runner_state"
        ), patch.object(RECOVERY.goal_continuity, "validate_ledger_binding"):
            with self.assertRaisesRegex(RECOVERY.RecoveryError, "cursor drift"):
                RECOVERY._validate_formal_preconditions(spec, state, ledger, {})

    def test_verification_failure_never_appends(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec = root / "spec.json"
            state = root / "state.json"
            ledger = root / "ledger.jsonl"
            evidence = root / "evidence"
            verification = root / "verification.json"
            spec.write_text("{}")
            state.write_text("{}")
            ledger.write_text("")
            before = hashlib.sha256(ledger.read_bytes()).hexdigest()
            with patch.object(
                RECOVERY,
                "validate_recovery_deployment_evidence",
                return_value=({"infrastructure": {"merged_revision": "6" * 40}}, "7" * 64),
            ), patch.object(RECOVERY, "resolve_live_authority", return_value={}), patch.object(
                RECOVERY, "validate_preserved_evidence", return_value={}
            ), patch.object(RECOVERY, "validate_bundle", return_value={}), patch.object(
                RECOVERY, "validate_verification_evidence", side_effect=RECOVERY.RecoveryError("verification failed")
            ):
                with self.assertRaisesRegex(RECOVERY.RecoveryError, "verification failed"):
                    RECOVERY.recover_successor(
                        spec_path=spec,
                        state_path=state,
                        ledger_path=ledger,
                        evidence_root=evidence,
                        verification_path=verification,
                        deployment_evidence_path=root / "deployment.json",
                        apply=True,
                        occurred_at=datetime.now(ZoneInfo("Asia/Taipei")),
                        runner_stopped_checker=lambda: True,
                    )
            self.assertEqual(before, hashlib.sha256(ledger.read_bytes()).hexdigest())

    def test_verification_requires_exact_deferred_remote_identity_set(self):
        required = {
            "requirements_guard", "requirements_guard_tests",
            "control_plane_negative_tests", "python_product_tests", "node_tests",
            "strict_git_diff_check", "o2_product_completion_gate",
            "review_completion_gate", "public_safety_scan", "untracked_whitespace",
        }
        identity = {
            "head": RECOVERY.SUCCESSOR_COMMIT,
            "value": RECOVERY.SUCCESSOR_FINGERPRINT,
        }
        value = {
            "schema_version": "kgnote.verification-evidence.v1",
            "result": "pass",
            "evidence_readback": True,
            "fingerprint_stable": True,
            "verification_profile": RECOVERY.codex_control.O2_PREPUBLICATION_PROFILE,
            "fingerprint_before": identity,
            "fingerprint_after": identity,
            "remote_publication_identity": {"required": True, "verified": False},
            "preflight": {
                "status": "pass",
                "verification_profile": RECOVERY.codex_control.O2_PREPUBLICATION_PROFILE,
            },
            "gates": [{"name": name, "passed": True} for name in sorted(required)],
        }
        control = next(
            row for row in value["gates"] if row["name"] == "control_plane_negative_tests"
        )
        control["details"] = {
            "deferred_gate": "trusted_remote_publication_identity",
            "deferred_tests": list(
                RECOVERY.codex_control.O2_DEFERRED_REMOTE_PUBLICATION_TESTS
            ),
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "verification.json"
            path.write_text(json.dumps(value))
            RECOVERY.validate_verification_evidence(path)
            control["details"]["deferred_tests"].append("unexpected.test")
            path.write_text(json.dumps(value))
            with self.assertRaisesRegex(RECOVERY.RecoveryError, "deferred remote-identity"):
                RECOVERY.validate_verification_evidence(path)

    def test_running_runner_blocks_before_any_recovery_read(self):
        with self.assertRaisesRegex(RECOVERY.RecoveryError, "Runner must remain unloaded"):
            RECOVERY.recover_successor(
                spec_path=Path("missing-spec"),
                state_path=Path("missing-state"),
                ledger_path=Path("missing-ledger"),
                evidence_root=Path("missing-evidence"),
                verification_path=Path("missing-verification"),
                deployment_evidence_path=Path("missing-deployment"),
                apply=True,
                occurred_at=datetime.now(ZoneInfo("Asia/Taipei")),
                runner_stopped_checker=lambda: False,
            )

    def test_deployment_evidence_requires_live_exact_mac_ubuntu_and_merged_pr(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            checkout = root / "runner"
            (checkout / "config").mkdir(parents=True)
            manifest = checkout / "config/ubuntu-worker-runtime-manifest.json"
            manifest.write_text("{}\n")
            runtime_destination = root / "runtime"
            plist_path = root / "runner.plist"
            plist_path.write_bytes(
                plistlib.dumps(
                    {
                        "Label": "com.kgnote.local-autonomy-runner",
                        "ProgramArguments": [
                            str(runtime_destination / "bin/python"),
                            str(checkout / "scripts/local_autonomy_runner.py"),
                        ],
                    }
                )
            )
            merged = "a" * 40
            reviewed = "b" * 40
            reviewed_fingerprint = "d" * 64
            merged_tree = "c" * 40
            reference_payloads = {
                "verification": {
                    "result": "pass",
                    "evidence_readback": True,
                    "fingerprint_stable": True,
                    "fingerprint_before": {
                        "head": reviewed,
                        "value": reviewed_fingerprint,
                    },
                    "fingerprint_after": {
                        "head": reviewed,
                        "value": reviewed_fingerprint,
                    },
                },
                "claude": {
                    "schema_version": "kgnote.o2-successor-recovery-infrastructure-review.v1",
                    "verdict": "PASS",
                    "reviewer_role": "UBUNTU_CLAUDE_REVIEWER",
                    "reviewed_revision": reviewed,
                    "reviewed_fingerprint": reviewed_fingerprint,
                    "product_goal_review": False,
                },
                "acceptance": {
                    "schema_version": "kgnote.o2-successor-recovery-no-model-acceptance.v1",
                    "status": "PASS",
                    "model_launches": 0,
                    "product_model_started": False,
                    "runner_loaded": False,
                    "candidate_commit": RECOVERY.SUCCESSOR_COMMIT,
                    "candidate_fingerprint": RECOVERY.SUCCESSOR_FINGERPRINT,
                    "infrastructure_merged_revision": merged,
                },
            }
            referenced = {}
            for name, payload in reference_payloads.items():
                item = root / f"{name}.json"
                item.write_text(json.dumps(payload) + "\n")
                referenced[name] = (item, hashlib.sha256(item.read_bytes()).hexdigest())
            identity = runtime_identity()
            identity.update(
                {
                    "generation": str(
                        Path(identity["runtime_root"])
                        / RECOVERY.product_goal_runtime_admission.RUNTIME_RELEASES
                        / merged
                    ),
                    "generation_id": merged,
                    "reviewed_revision": merged,
                    "reviewed_tree": merged_tree,
                    "manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
                }
            )
            receipt = {
                "schema_version": RECOVERY.product_goal_runtime_admission.DEPLOYMENT_RECEIPT_SCHEMA,
                "status": "PASS",
                "model_launches": 0,
                "checkout": {
                    "branch": RECOVERY.PRODUCT_BRANCH,
                    "head": RECOVERY.SUCCESSOR_COMMIT,
                    "tree": RECOVERY.SUCCESSOR_TREE,
                },
                "worker_runtime": {
                    "reviewed_revision": merged,
                    "reviewed_source": {"tree": merged_tree},
                },
            }
            ubuntu = {"identity": identity, "receipt": receipt}
            pull_request = {
                "number": 55,
                "state": "MERGED",
                "headRefOid": reviewed,
                "headRefName": "codex/o2-successor-recovery-20261030",
                "baseRefName": "main",
                "mergeCommit": {"oid": merged},
                "url": "https://example.invalid/pr/55",
            }
            evidence = {
                "schema_version": RECOVERY.DEPLOYMENT_EVIDENCE_SCHEMA,
                "status": "PASS",
                "model_launches": 0,
                "infrastructure": {
                    "base_revision": RECOVERY.INFRASTRUCTURE_BASE,
                    "reviewed_revision": reviewed,
                    "reviewed_fingerprint": reviewed_fingerprint,
                    "merged_revision": merged,
                    "merged_tree": merged_tree,
                    "pull_request": 55,
                    "github_pull_request": pull_request,
                    "claude_verdict_sha256": referenced["claude"][1],
                },
                "mac": {
                    "runner_checkout": str(checkout),
                    "runner_python_destination": str(runtime_destination),
                    "forbidden_prefixes": [],
                    "runtime_receipt_sha256": "e" * 64,
                    "launchagent_plist": str(plist_path),
                    "launchagent_plist_sha256": hashlib.sha256(
                        plist_path.read_bytes()
                    ).hexdigest(),
                },
                "ubuntu": ubuntu,
                "infrastructure_verification_path": str(referenced["verification"][0]),
                "infrastructure_verification_sha256": referenced["verification"][1],
                "claude_verdict_path": str(referenced["claude"][0]),
                "claude_verdict_sha256": referenced["claude"][1],
                "no_model_acceptance_path": str(referenced["acceptance"][0]),
                "no_model_acceptance_sha256": referenced["acceptance"][1],
            }
            evidence_path = root / "deployment.json"
            evidence_path.write_text(json.dumps(evidence))

            def git_value(_repo, *args):
                return {
                    ("rev-parse", "HEAD"): merged,
                    ("rev-parse", "HEAD^{tree}"): merged_tree,
                    ("status", "--porcelain=v1", "--untracked-files=all"): "",
                }[args]

            with patch.object(RECOVERY, "_git_value", side_effect=git_value), patch.object(
                RECOVERY.subprocess,
                "run",
                return_value=subprocess.CompletedProcess([], 0, "", ""),
            ), patch.object(
                RECOVERY.install_runner_python_runtime,
                "check_runtime",
                return_value={"receipt_sha256": "e" * 64},
            ), patch.object(
                RECOVERY.codex_control,
                "repository_fingerprint",
                return_value={"head": merged, "value": "f" * 64},
            ):
                RECOVERY.validate_recovery_deployment_evidence(
                    evidence_path,
                    ubuntu_fetcher=lambda: ubuntu,
                    github_fetcher=lambda _number: pull_request,
                )
                drifted = json.loads(json.dumps(ubuntu))
                drifted["receipt"]["checkout"]["head"] = "0" * 40
                with self.assertRaisesRegex(RECOVERY.RecoveryError, "live Ubuntu runtime differs"):
                    RECOVERY.validate_recovery_deployment_evidence(
                        evidence_path,
                        ubuntu_fetcher=lambda: drifted,
                        github_fetcher=lambda _number: pull_request,
                    )

    def test_writer_appends_once_and_duplicate_execution_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec_path = root / "spec.json"
            state_path = root / "state.json"
            ledger_path = root / "ledger.jsonl"
            spec = {"goal_id": RECOVERY.GOAL_ID, "goal_version": RECOVERY.GOAL_VERSION}
            state = {
                "candidate_identity": {
                    "commit": RECOVERY.ORIGINAL_COMMIT,
                    "fingerprint": RECOVERY.ORIGINAL_FINGERPRINT,
                    "branch": RECOVERY.PRODUCT_BRANCH,
                    "pull_request": None,
                },
                "work_items": [
                    {
                        "work_item_id": RECOVERY.WORK_ITEM_ID,
                        "status": "PLANNED",
                        "attempts": 1,
                        "active_attempt_id": None,
                        "failure_counts": {"DETERMINISTIC_WORKER_FAILURE": 1},
                    },
                    {"work_item_id": RECOVERY.NEXT_WORK_ITEM_ID, "status": "PLANNED"},
                ],
                "resource_accounting": {"codex": {"total_launches": 4}},
                "event_cursor": {"sequence": 0, "event_sha256": None},
            }
            spec_path.write_text(json.dumps(spec))
            state_path.write_text(json.dumps(state))
            ledger_path.write_text("")
            formal_hashes = {
                "FORMAL_SPEC_FILE_SHA256": hashlib.sha256(spec_path.read_bytes()).hexdigest(),
                "FORMAL_STATE_SHA256": hashlib.sha256(state_path.read_bytes()).hexdigest(),
                "FORMAL_LEDGER_SHA256": hashlib.sha256(ledger_path.read_bytes()).hexdigest(),
            }
            patches = [patch.object(RECOVERY, name, value) for name, value in formal_hashes.items()]
            patches.extend([
                patch.object(RECOVERY, "validate_preserved_evidence", return_value={"checkpoint": RECOVERY.CHECKPOINT_SHA256}),
                patch.object(RECOVERY, "validate_bundle", return_value={
                    "commit": RECOVERY.SUCCESSOR_COMMIT,
                    "parent": RECOVERY.ORIGINAL_COMMIT,
                    "tree": RECOVERY.SUCCESSOR_TREE,
                    "fingerprint": RECOVERY.SUCCESSOR_FINGERPRINT,
                }),
                patch.object(RECOVERY, "validate_verification_evidence", return_value=({}, "5" * 64)),
                patch.object(
                    RECOVERY,
                    "validate_recovery_deployment_evidence",
                    return_value=({"infrastructure": {"merged_revision": "6" * 40}}, "7" * 64),
                ),
                patch.object(RECOVERY, "resolve_live_authority", return_value={"record": {"comment_id": RECOVERY.OWNER_COMMENT_ID}}),
                patch.object(RECOVERY, "_validate_formal_preconditions"),
                patch.object(RECOVERY.goal_continuity, "validate_runner_state"),
                patch.object(
                    RECOVERY.goal_runner_adapter,
                    "synchronize_state_from_ledger",
                    side_effect=lambda _spec, current, _ledger, **_kwargs: current,
                ),
            ])
            for item in patches:
                item.start()
            try:
                first = RECOVERY.recover_successor(
                    spec_path=spec_path,
                    state_path=state_path,
                    ledger_path=ledger_path,
                    evidence_root=root / "evidence",
                    verification_path=root / "verification.json",
                    deployment_evidence_path=root / "deployment.json",
                    apply=True,
                    occurred_at=datetime(2026, 10, 30, 12, tzinfo=ZoneInfo("Asia/Taipei")),
                    runner_stopped_checker=lambda: True,
                )
                self.assertEqual("SUCCESSOR_RECOVERED", first["status"])
                self.assertEqual(1, len(goal_continuity.read_ledger(ledger_path)))
                second = RECOVERY.recover_successor(
                    spec_path=spec_path,
                    state_path=state_path,
                    ledger_path=ledger_path,
                    evidence_root=root / "evidence",
                    verification_path=root / "verification.json",
                    deployment_evidence_path=root / "deployment.json",
                    apply=True,
                    occurred_at=datetime(2026, 10, 30, 12, 1, tzinfo=ZoneInfo("Asia/Taipei")),
                    runner_stopped_checker=lambda: True,
                )
                self.assertEqual("SUCCESSOR_ALREADY_RECOVERED", second["status"])
                self.assertEqual(1, len(goal_continuity.read_ledger(ledger_path)))
                recovered = json.loads(state_path.read_text())
                self.assertEqual(RECOVERY.SUCCESSOR_COMMIT, recovered["candidate_identity"]["commit"])
                self.assertEqual(4, recovered["resource_accounting"]["codex"]["total_launches"])
            finally:
                for item in reversed(patches):
                    item.stop()


if __name__ == "__main__":
    unittest.main()
