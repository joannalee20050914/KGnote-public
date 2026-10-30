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

    def successor_verification(self, *, created_at: str) -> dict[str, object]:
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
        value: dict[str, object] = {
            "schema_version": "kgnote.verification-evidence.v1",
            "created_at": created_at,
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
            row for row in value["gates"]
            if row["name"] == "control_plane_negative_tests"
        )
        control["details"] = {
            "deferred_gate": "trusted_remote_publication_identity",
            "deferred_tests": list(
                RECOVERY.codex_control.O2_DEFERRED_REMOTE_PUBLICATION_TESTS
            ),
        }
        return value

    def formal_like_state_and_ledger(
        self,
    ) -> tuple[dict[str, object], dict[str, object], list[dict[str, object]], dict[str, object]]:
        spec = json.loads(
            (ROOT / "docs/control-plane/O2_BOUNDED_TRIAL_GOAL_SPEC_v2026-10-29.4.json").read_text()
        )
        carryover = spec["history_carryover"]
        receipts = []
        for dependency_id in spec["dependencies"]:
            receipt = {
                "dependency_id": dependency_id,
                "source_kind": "EXTERNAL_DECISION_RESOLVED",
                "status": "CLOSED",
                "goal_version": None,
                "goal_spec_sha256": None,
                "evidence_sha256": "a" * 64,
                "verified_at": "2026-10-29T15:03:12+08:00",
            }
            if dependency_id == carryover["dependency_id"]:
                receipt.update(
                    goal_version=carryover["source_goal"]["goal_version"],
                    goal_spec_sha256=carryover["source_goal"]["goal_spec_sha256"],
                    evidence_sha256=carryover["evidence_sha256"],
                )
            receipts.append(receipt)
        state = goal_continuity.initial_runner_state(
            spec,
            now="2026-10-29T15:00:00+08:00",
            dependency_receipts=receipts,
        )
        authority_record = {
            "schema_version": "kgnote.product-goal-authority.v1",
            "identity_kind": "KGNOTE_PRODUCT_GOAL",
            "authority_kind": "GITHUB_OWNER_APPROVAL",
            "repository": "joannalee20050914/KGnote-public",
            "issue": 9,
            "comment_id": RECOVERY.OWNER_COMMENT_ID,
            "comment_url": (
                "https://github.com/joannalee20050914/KGnote-public/"
                "issues/9#issuecomment-6490692466"
            ),
            "author_login": "joannalee20050914",
            "author_association": "OWNER",
            "created_at": "2026-10-29T07:28:09Z",
            "expires_at": None,
            "action": "APPROVE",
            "goal_id": RECOVERY.GOAL_ID,
            "goal_version": RECOVERY.GOAL_VERSION,
            "goal_spec_sha256": RECOVERY.GOAL_SPEC_SHA256,
            "permissions": ["activate_runner", "commit", "push", "draft_pr", "review", "verify"],
            "body_sha256": RECOVERY.OWNER_BODY_SHA256,
        }
        state.update(
            lifecycle={
                "state": "ACTIVE",
                "revision": 2,
                "changed_at": "2026-10-29T07:28:09Z",
                "reason": "Runner activated the approved Goal",
            },
            authority_lease="ACTIVE",
            authority_record=authority_record,
            go_live_authorized=True,
            candidate_identity={
                "commit": RECOVERY.ORIGINAL_COMMIT,
                "fingerprint": RECOVERY.ORIGINAL_FINGERPRINT,
                "branch": RECOVERY.PRODUCT_BRANCH,
                "pull_request": None,
            },
            resource_accounting={
                "codex": {
                    "last_launch_at": "2026-10-30T09:00:34+08:00",
                    "launches_in_window": 1,
                    "total_launches": 4,
                    "window_id": "2026-10-30@09:00-18:00",
                }
            },
        )
        work = next(
            row for row in state["work_items"]
            if row["work_item_id"] == RECOVERY.WORK_ITEM_ID
        )
        work.update(
            status="PLANNED",
            attempts=1,
            active_attempt_id=None,
            failure_counts={"DETERMINISTIC_WORKER_FAILURE": 1},
            dispatch_binding={
                "order_event_id": "o2-wi-o2-a-implement-codex-5b4a173c9ac48566",
                "order_path": "output/control-plane/product-goal/orders/order.json",
                "order_sha256": "b" * 64,
            },
            dispatch_binding_cursor={"DISPATCH_IMPLEMENTATION": 1},
        )
        events: list[dict[str, object]] = []

        def add(event_id: str, event_type: str, payload: dict[str, object], *, attempt: bool = False) -> None:
            events.append(
                goal_continuity.prepare_ledger_event(
                    events,
                    event_id=event_id,
                    event_type=event_type,
                    occurred_at=f"2026-10-30T09:0{len(events)}:00+08:00",
                    goal_id=RECOVERY.GOAL_ID,
                    goal_version=RECOVERY.GOAL_VERSION,
                    logical_work_id=RECOVERY.WORK_ITEM_ID if attempt else None,
                    attempt_id=RECOVERY.ATTEMPT_ID if attempt else None,
                    payload=payload,
                )
            )

        add(
            "goal-authority-6490692466-accepted",
            "GOAL_AUTHORITY_VERIFIED",
            {
                "accepted": True,
                "action": "APPROVE",
                "authority_comment_id": RECOVERY.OWNER_COMMENT_ID,
                "authority_body_sha256": RECOVERY.OWNER_BODY_SHA256,
                "activation_observed_at": "2026-10-29T15:28:36+08:00",
                "go_live_authorized": True,
                "goal_spec_sha256": RECOVERY.GOAL_SPEC_SHA256,
            },
        )
        add("goal-lifecycle-approved", "GOAL_LIFECYCLE_TRANSITION", {"state": "APPROVED"})
        add("goal-lifecycle-active", "GOAL_LIFECYCLE_TRANSITION", {"state": "ACTIVE"})
        add(
            f"{RECOVERY.ATTEMPT_ID}-reserved",
            "MODEL_ATTEMPT_STARTED",
            {"operation": "DISPATCH_RESERVED", "provider": "codex"},
            attempt=True,
        )
        add(
            f"{RECOVERY.ATTEMPT_ID}-finished",
            "MODEL_ATTEMPT_FINISHED",
            {"failure_class": "DETERMINISTIC_WORKER_FAILURE", "outcome": "WORK_FAILED"},
            attempt=True,
        )
        add(
            f"{RECOVERY.ATTEMPT_ID}-usage",
            "USAGE_OBSERVED",
            {"status": "UNKNOWN", "source": "worker_evidence"},
            attempt=True,
        )
        add(
            f"{RECOVERY.ATTEMPT_ID}-checkpoint-reconciled",
            "CHECKPOINT_RECONCILED",
            {
                "operation": "DISPATCH_RECONCILED",
                "outcome": "DETERMINISTIC_WORKER_FAILURE",
                "checkpoint_sha256": RECOVERY.CHECKPOINT_SHA256,
            },
            attempt=True,
        )
        add(
            f"{RECOVERY.ATTEMPT_ID}-failure-released",
            "WORK_STATE_TRANSITION",
            {
                "operation": "RECOVERABLE_RUNTIME_BLOCK_RELEASED",
                "failure_class": "DETERMINISTIC_WORKER_FAILURE",
                "state_patch": RECOVERY.goal_runner_adapter._state_patch(state),
            },
            attempt=True,
        )
        state["event_cursor"] = {
            "sequence": 8,
            "event_sha256": events[-1]["event_sha256"],
        }
        authority = {"record": authority_record, "valid_records": [authority_record]}
        return spec, state, events, authority

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
        value = self.successor_verification(created_at="2026-10-30T12:01:00+08:00")
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
                "successor_verification": self.successor_verification(
                    created_at="2026-10-30T12:01:00+08:00"
                ),
                "acceptance": {
                    "schema_version": "kgnote.o2-successor-recovery-no-model-acceptance.v1",
                    "status": "PASS",
                    "model_launches": 0,
                    "product_model_started": False,
                    "runner_loaded": False,
                    "candidate_commit": RECOVERY.SUCCESSOR_COMMIT,
                    "candidate_fingerprint": RECOVERY.SUCCESSOR_FINGERPRINT,
                    "infrastructure_merged_revision": merged,
                    "runtime_generation_id": merged,
                    "runtime_manifest_sha256": hashlib.sha256(
                        manifest.read_bytes()
                    ).hexdigest(),
                    "successor_verification_created_at": "2026-10-30T12:01:00+08:00",
                    "accepted_at": "2026-10-30T12:02:00+08:00",
                },
            }
            referenced = {}
            for name, payload in reference_payloads.items():
                item = root / f"{name}.json"
                item.write_text(json.dumps(payload) + "\n")
                referenced[name] = (item, hashlib.sha256(item.read_bytes()).hexdigest())
            reference_payloads["acceptance"]["successor_verification_sha256"] = (
                referenced["successor_verification"][1]
            )
            referenced["acceptance"][0].write_text(
                json.dumps(reference_payloads["acceptance"]) + "\n"
            )
            referenced["acceptance"] = (
                referenced["acceptance"][0],
                hashlib.sha256(referenced["acceptance"][0].read_bytes()).hexdigest(),
            )
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
                "deployed_at": "2026-10-30T12:00:00+08:00",
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
                "successor_verification_path": str(
                    referenced["successor_verification"][0]
                ),
                "successor_verification_sha256": referenced["successor_verification"][1],
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
                evidence["deployed_at"] = "2026-10-30T12:01:30+08:00"
                evidence_path.write_text(json.dumps(evidence))
                with self.assertRaisesRegex(RECOVERY.RecoveryError, "incomplete or stale"):
                    RECOVERY.validate_recovery_deployment_evidence(
                        evidence_path,
                        ubuntu_fetcher=lambda: ubuntu,
                        github_fetcher=lambda _number: pull_request,
                    )
                evidence["deployed_at"] = "2026-10-30T12:00:00+08:00"
                evidence_path.write_text(json.dumps(evidence))
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
            verification_path = root / "verification.json"
            spec, state, original_events, authority = self.formal_like_state_and_ledger()
            goal_continuity.atomic_write_json(spec_path, spec)
            goal_continuity.atomic_write_json(state_path, state)
            ledger_path.write_bytes(
                b"".join(
                    goal_continuity.canonical_json_bytes(event) + b"\n"
                    for event in original_events
                )
            )
            verification_path.write_text("{}\n")
            original_prefix = ledger_path.read_bytes()
            formal_hashes = {
                "FORMAL_SPEC_FILE_SHA256": hashlib.sha256(spec_path.read_bytes()).hexdigest(),
                "FORMAL_STATE_SHA256": hashlib.sha256(state_path.read_bytes()).hexdigest(),
                "FORMAL_LEDGER_SHA256": hashlib.sha256(ledger_path.read_bytes()).hexdigest(),
            }
            verification_sha = "5" * 64
            deployment = {
                "infrastructure": {"merged_revision": "6" * 40},
                "successor_verification_path": str(verification_path.resolve()),
                "successor_verification_sha256": verification_sha,
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
                patch.object(
                    RECOVERY,
                    "validate_verification_evidence",
                    return_value=({}, verification_sha),
                ),
                patch.object(
                    RECOVERY,
                    "validate_recovery_deployment_evidence",
                    return_value=(deployment, "7" * 64),
                ),
                patch.object(
                    RECOVERY,
                    "resolve_live_authority",
                    return_value=authority,
                ),
                patch.object(RECOVERY.goal_runner_adapter, "_go_live_receipt", return_value={}),
            ])
            for item in patches:
                item.start()
            try:
                first = RECOVERY.recover_successor(
                    spec_path=spec_path,
                    state_path=state_path,
                    ledger_path=ledger_path,
                    evidence_root=root / "evidence",
                    verification_path=verification_path,
                    deployment_evidence_path=root / "deployment.json",
                    apply=True,
                    occurred_at=datetime(2026, 10, 30, 12, tzinfo=ZoneInfo("Asia/Taipei")),
                    runner_stopped_checker=lambda: True,
                )
                self.assertEqual("SUCCESSOR_RECOVERED", first["status"])
                recovered_events = goal_continuity.read_ledger(ledger_path)
                self.assertEqual(9, len(recovered_events))
                self.assertEqual(original_events, recovered_events[:8])
                self.assertTrue(ledger_path.read_bytes().startswith(original_prefix))
                projection = goal_continuity.reduce_ledger(recovered_events)
                self.assertEqual(
                    "DETERMINISTIC_WORKER_FAILURE",
                    projection["model_attempts"][RECOVERY.ATTEMPT_ID]["failure_class"],
                )
                second = RECOVERY.recover_successor(
                    spec_path=spec_path,
                    state_path=state_path,
                    ledger_path=ledger_path,
                    evidence_root=root / "evidence",
                    verification_path=verification_path,
                    deployment_evidence_path=root / "deployment.json",
                    apply=True,
                    occurred_at=datetime(2026, 10, 30, 12, 1, tzinfo=ZoneInfo("Asia/Taipei")),
                    runner_stopped_checker=lambda: True,
                )
                self.assertEqual("SUCCESSOR_ALREADY_RECOVERED", second["status"])
                self.assertEqual(9, len(goal_continuity.read_ledger(ledger_path)))
                recovered = json.loads(state_path.read_text())
                self.assertEqual(RECOVERY.SUCCESSOR_COMMIT, recovered["candidate_identity"]["commit"])
                self.assertEqual(4, recovered["resource_accounting"]["codex"]["total_launches"])
                by_id = {row["work_item_id"]: row for row in recovered["work_items"]}
                self.assertEqual("VERIFIED", by_id[RECOVERY.WORK_ITEM_ID]["status"])
                self.assertEqual("PLANNED", by_id[RECOVERY.NEXT_WORK_ITEM_ID]["status"])

                tampered = goal_continuity.read_ledger(ledger_path)
                tampered[-1]["payload"]["pre_recovery_ledger_cursor"] = 7
                tampered[-1]["event_sha256"] = goal_continuity.event_sha256(tampered[-1])
                ledger_path.write_bytes(
                    b"".join(
                        goal_continuity.canonical_json_bytes(event) + b"\n"
                        for event in tampered
                    )
                )
                with self.assertRaisesRegex(RECOVERY.RecoveryError, "exact recovery identity"):
                    RECOVERY.recover_successor(
                        spec_path=spec_path,
                        state_path=state_path,
                        ledger_path=ledger_path,
                        evidence_root=root / "evidence",
                        verification_path=verification_path,
                        deployment_evidence_path=root / "deployment.json",
                        apply=True,
                        occurred_at=datetime(
                            2026, 10, 30, 12, 2, tzinfo=ZoneInfo("Asia/Taipei")
                        ),
                        runner_stopped_checker=lambda: True,
                    )
            finally:
                for item in reversed(patches):
                    item.stop()


if __name__ == "__main__":
    unittest.main()
