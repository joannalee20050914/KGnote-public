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
from unittest.mock import Mock
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

SPEC = importlib.util.spec_from_file_location(
    "collaboration_goal_dispatch", ROOT / "scripts/collaboration_goal_dispatch.py"
)
DISPATCH = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DISPATCH)

import goal_continuity as GOAL
from tests.control_plane.test_goal_continuity import product_goal_spec
from tests.control_plane.test_github_product_goal_control import comment
from tests.control_plane.runtime_admission_fixtures import (
    reservation_receipt,
    runtime_identity,
)


NOW = datetime(2026, 10, 22, 10, 0, tzinfo=ZoneInfo("Asia/Taipei"))


class CollaborationGoalDispatchTests(unittest.TestCase):
    def setUp(self):
        self.spec = product_goal_spec()

    def repository(self, root: Path) -> Path:
        repo = root / "repo"
        repo.mkdir()
        subprocess.run(
            ["git", "init", "-b", "codex/test-goal"],
            cwd=repo, check=True, capture_output=True,
        )
        subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=repo, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
        (repo / "seed.txt").write_text("seed\n", encoding="utf-8")
        subprocess.run(["git", "add", "seed.txt"], cwd=repo, check=True)
        subprocess.run(["git", "commit", "-m", "seed"], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "remote", "add", "origin", "https://github.com/owner/repo.git"],
            cwd=repo, check=True,
        )
        (repo / ".ai").mkdir()
        (repo / ".ai/epoch.json").write_text("{}\n", encoding="utf-8")
        scripts = repo / "scripts"
        scripts.mkdir()
        (scripts / "router.py").write_text("# test router\n", encoding="utf-8")
        (scripts / "admission.py").write_text("# test admission\n", encoding="utf-8")
        return repo

    def inputs(
        self, repo: Path, *, protected: bool = False, model: bool = False,
        dynamic: bool = False,
    ):
        spec = deepcopy(self.spec)
        if not model:
            spec["work_items"][0]["kind"] = "PUBLISH"
            spec["work_items"][0]["provider"] = "NONE"
            spec["work_items"][0]["allowed_operations"] = ["push"]
        if protected:
            spec["goal_id"] = "GOAL-KGNOTE-O2-READING-EXPERIENCE"
            spec["active_goal"] = spec["goal_id"]
        state = GOAL.initial_runner_state(
            spec, now=NOW.isoformat(),
            codex_app_goal_provenance={"goal_id": "ISSUE47", "status": "active"},
        )
        if dynamic:
            head = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=repo, text=True,
            ).strip()
            state["candidate_identity"] = {
                "commit": head, "fingerprint": "2" * 64,
                "branch": "codex/test-goal", "pull_request": 47,
            }
        order_path = repo / "output/control-plane/orders/implement.json"
        order = {
            "schema_version": "kgnote.linux-worker-order.v1",
            "event_id": "issue47-test-implementation",
            "stage": "codex" if model else "publisher",
            "working_directory": "/home/kgnote/.local/share/kgnote/work-items/issue47-test",
            "command": ["/usr/bin/true"],
            "checkpoint_path": str(repo / "output/control-plane/checkpoints/implement.json"),
            "product_goal_admission": {
                "repository": spec["repository"],
                "goal_id": spec["goal_id"],
                "goal_version": spec["goal_version"],
                "goal_spec_sha256": GOAL.goal_spec_sha256(spec),
                "work_item_id": spec["work_items"][0]["work_item_id"],
                "stage": "codex" if model else "publisher",
                "provider": "codex" if model else "NONE",
                "order_event_id": "issue47-test-implementation",
                "candidate": {"commit": "1" * 40, "fingerprint": "2" * 64},
                "authority_status": "APPROVED", "go_live_authorized": True,
                "stop_marker_clear": True, "requires_model": model,
                "total_launches_before": 0, "max_total_launches": 12,
            },
            "bootstrap_identity": {
                "goal_id": spec["goal_id"], "goal_version": spec["goal_version"],
                "goal_spec_sha256": GOAL.goal_spec_sha256(spec),
                "work_item_id": spec["work_items"][0]["work_item_id"],
                "provider": "codex" if model else "NONE",
            },
        }
        if not dynamic:
            order_path.parent.mkdir(parents=True)
            order_path.write_text(json.dumps(order), encoding="utf-8")
            state["work_items"][0]["dispatch_binding"] = {
                "order_path": str(order_path.relative_to(repo)),
                "order_sha256": hashlib.sha256(order_path.read_bytes()).hexdigest(),
                "order_event_id": order["event_id"],
            }
        spec_path = repo / "goal.json"
        state_path = repo / "state.json"
        ledger_path = repo / "ledger.jsonl"
        GOAL.atomic_write_json(spec_path, spec)
        GOAL.atomic_write_json(state_path, state)
        ledger_path.write_text("", encoding="utf-8")
        return spec, spec_path, state_path, ledger_path

    def call(self, repo: Path, spec_path: Path, state_path: Path, ledger_path: Path, **changes):
        return DISPATCH.dispatch_once(
            repo=repo, spec_path=spec_path, state_path=state_path,
            ledger_path=ledger_path, now=NOW,
            router=repo / "scripts/router.py",
            epoch_record=repo / ".ai/epoch.json",
            scope_admission=repo / "scripts/admission.py",
            **changes,
        )

    def test_missing_owner_authority_never_reserves_or_routes(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = self.repository(Path(directory))
            _, spec_path, state_path, ledger_path = self.inputs(repo)
            before_state = state_path.read_bytes()
            runner = Mock()
            result = self.call(
                repo, spec_path, state_path, ledger_path,
                comments_fetcher=lambda _spec: [], command_runner=runner,
            )
            self.assertEqual("WAITING_AUTHORIZATION", result["status"])
            self.assertEqual("WAIT_AUTHORITY", result["decision"]["status"])
            self.assertEqual(before_state, state_path.read_bytes())
            self.assertEqual(b"", ledger_path.read_bytes())
            runner.assert_not_called()

    def test_single_writer_conflict_fails_before_github_or_goal_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = self.repository(Path(directory))
            _, spec_path, state_path, ledger_path = self.inputs(repo)
            fetcher = Mock()
            before = (state_path.read_bytes(), ledger_path.read_bytes())
            with DISPATCH.writer_lock(repo):
                with self.assertRaisesRegex(
                    DISPATCH.CollaborationDispatchError, "another collaboration Goal writer",
                ):
                    self.call(
                        repo, spec_path, state_path, ledger_path,
                        comments_fetcher=fetcher,
                    )
            fetcher.assert_not_called()
            self.assertEqual(before, (state_path.read_bytes(), ledger_path.read_bytes()))

    def test_wrong_repository_and_candidate_commit_drift_fail_before_github(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = self.repository(Path(directory))
            _, spec_path, state_path, ledger_path = self.inputs(repo, dynamic=True)
            fetcher = Mock()
            subprocess.run(
                ["git", "remote", "set-url", "origin", "https://github.com/other/repo.git"],
                cwd=repo, check=True,
            )
            with self.assertRaisesRegex(
                DISPATCH.CollaborationDispatchError, "repository differs",
            ):
                self.call(
                    repo, spec_path, state_path, ledger_path,
                    comments_fetcher=fetcher,
                )
            fetcher.assert_not_called()

            subprocess.run(
                ["git", "remote", "set-url", "origin", "https://github.com/owner/repo.git"],
                cwd=repo, check=True,
            )
            state = GOAL.load_json(state_path)
            state["candidate_identity"]["commit"] = "0" * 40
            GOAL.atomic_write_json(state_path, state)
            with self.assertRaisesRegex(
                DISPATCH.readiness.CollaborationWakeupError, "candidate commit differs",
            ):
                self.call(
                    repo, spec_path, state_path, ledger_path,
                    comments_fetcher=fetcher,
                )
            fetcher.assert_not_called()

    def test_stale_owner_goal_version_cannot_create_reservation(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = self.repository(Path(directory))
            spec, spec_path, state_path, ledger_path = self.inputs(repo)
            stale = comment(spec, payload={"goal_version": "stale"})
            result = self.call(
                repo, spec_path, state_path, ledger_path,
                comments_fetcher=lambda _spec: [stale],
            )
            self.assertEqual("WAITING_AUTHORIZATION", result["status"])
            self.assertEqual([], [
                row for row in GOAL.read_ledger(ledger_path)
                if row["payload"].get("operation") == "DISPATCH_RESERVED"
            ])

    def test_exact_owner_authority_reserves_and_routes_one_bound_order(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = self.repository(Path(directory))
            spec, spec_path, state_path, ledger_path = self.inputs(repo)
            runner = Mock(side_effect=[
                subprocess.CompletedProcess([], 0, "", ""),
                subprocess.CompletedProcess([], 0, "{}", ""),
            ])
            result = self.call(
                repo, spec_path, state_path, ledger_path,
                comments_fetcher=lambda _spec: [comment(spec)],
                command_runner=runner,
            )
            self.assertEqual("DISPATCHED", result["status"])
            self.assertEqual("RETRY_PUBLICATION", result["decision"]["action"])
            self.assertEqual(2, runner.call_count)
            calls = [row.args[0] for row in runner.call_args_list]
            self.assertIn("--epoch", calls[0])
            self.assertIn("--order", calls[1])
            ledger = GOAL.read_ledger(ledger_path)
            reservations = [
                row for row in ledger
                if row["payload"].get("operation") == "DISPATCH_RESERVED"
            ]
            self.assertEqual(1, len(reservations))
            state = GOAL.load_json(state_path)
            self.assertEqual("DISPATCHED", state["work_items"][0]["status"])
            self.assertEqual(
                0,
                state.get("resource_accounting", {}).get("codex", {}).get(
                    "total_launches", 0
                ),
            )
            self.assertFalse(result["safety"]["legacy_o2_runner_used"])

    def test_generic_model_order_is_denied_before_reservation_when_live_runtime_is_unavailable(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = self.repository(Path(directory))
            spec, spec_path, state_path, ledger_path = self.inputs(repo, model=True)
            runner = Mock()
            with self.assertRaisesRegex(
                DISPATCH.CollaborationDispatchError,
                "Ubuntu runtime identity discovery failed",
            ):
                self.call(
                    repo, spec_path, state_path, ledger_path,
                    comments_fetcher=lambda _spec: [comment(spec)],
                    command_runner=runner,
                )
            self.assertEqual(1, runner.call_count)
            self.assertIn("--discover-runtime", runner.call_args.args[0])
            reservations = [
                row for row in GOAL.read_ledger(ledger_path)
                if row["payload"].get("operation") == "DISPATCH_RESERVED"
            ]
            self.assertEqual([], reservations)

    def test_generic_model_one_shot_crosses_zero_model_admission_before_reservation(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = self.repository(Path(directory))
            spec, spec_path, state_path, ledger_path = self.inputs(
                repo, model=True, dynamic=True,
            )
            runtime = runtime_identity()
            calls = []

            def run(command, **_kwargs):
                calls.append(command)
                if "--discover-runtime" in command:
                    return subprocess.CompletedProcess(command, 0, json.dumps(runtime), "")
                if "--admit-order" in command:
                    order_path = Path(command[command.index("--admit-order") + 1])
                    receipt_path = Path(command[command.index("--admission-receipt") + 1])
                    order = json.loads(order_path.read_text(encoding="utf-8"))
                    receipt = reservation_receipt(
                        order["execution_context"],
                        order_sha256=hashlib.sha256(order_path.read_bytes()).hexdigest(),
                        observed_at=NOW,
                        router_checkpoint_path=(
                            repo / "output/control-plane/test-admission-router.json"
                        ),
                    )
                    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
                    return subprocess.CompletedProcess(command, 0, json.dumps(receipt), "")
                return subprocess.CompletedProcess(command, 0, "{}", "")

            result = self.call(
                repo, spec_path, state_path, ledger_path,
                comments_fetcher=lambda _spec: [comment(spec)],
                command_runner=run,
            )
            self.assertEqual("DISPATCHED", result["status"])
            self.assertTrue(result["decision"]["requires_model"])
            self.assertEqual(4, len(calls))
            self.assertIn("--discover-runtime", calls[0])
            self.assertIn("--epoch", calls[1])
            self.assertIn("--admit-order", calls[2])
            self.assertIn("--order", calls[3])
            order = json.loads((repo / result["order"]["path"]).read_text(encoding="utf-8"))
            self.assertEqual("kgnote.product-goal-worker-context.v3", order["execution_context"]["schema_version"])
            reservations = [
                row for row in GOAL.read_ledger(ledger_path)
                if row["payload"].get("operation") == "DISPATCH_RESERVED"
            ]
            self.assertEqual(1, len(reservations))
            self.assertEqual(
                0,
                reservations[0]["payload"]["runtime_admission"]["model_launches"],
            )

    def test_changes_required_dispatches_receipt_bound_repair_and_preserves_usage_on_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = self.repository(Path(directory))
            spec = deepcopy(self.spec)
            review = deepcopy(spec["work_items"][0])
            review.update({
                "kind": "REVIEW", "provider": "claude",
                "allowed_operations": ["review"],
            })
            repair = deepcopy(spec["work_items"][2])
            repair["dependencies"] = [review["work_item_id"]]
            spec["work_items"] = [review, repair]
            state = GOAL.initial_runner_state(
                spec, now=NOW.isoformat(),
                codex_app_goal_provenance={"goal_id": "ISSUE47", "status": "active"},
            )
            head = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=repo, text=True,
            ).strip()
            state["candidate_identity"] = {
                "commit": head, "fingerprint": "2" * 64,
                "branch": "codex/test-goal", "pull_request": 47,
            }
            spec_path = repo / "goal.json"
            state_path = repo / "state.json"
            ledger_path = repo / "ledger.jsonl"
            GOAL.atomic_write_json(spec_path, spec)
            GOAL.atomic_write_json(state_path, state)
            ledger_path.write_text("", encoding="utf-8")
            authority_comment = comment(spec)
            authority = DISPATCH.github_control.resolve_authority(
                [authority_comment], spec,
            )
            active = DISPATCH.goal_runner_adapter.reconcile_owner_authority(
                spec, state, authority, state_path=state_path,
                ledger_path=ledger_path, observed_at=NOW,
            )["state"]

            prior_codex_time = NOW.replace(hour=9, minute=0).isoformat()
            for suffix, event_type, payload in (
                ("started", "MODEL_ATTEMPT_STARTED", {"provider": "codex"}),
                ("finished", "MODEL_ATTEMPT_FINISHED", {"outcome": "WORK_COMPLETED"}),
            ):
                GOAL.append_ledger_event(
                    ledger_path,
                    event_id=f"prior-codex-{suffix}", event_type=event_type,
                    occurred_at=prior_codex_time,
                    goal_id=spec["goal_id"], goal_version=spec["goal_version"],
                    logical_work_id=repair["work_item_id"],
                    attempt_id="prior-codex-attempt",
                    payload=payload,
                )
            active["work_items"][0]["status"] = "VERIFIED"
            active["work_items"][0]["attempts"] = 1
            active["work_items"][0]["active_attempt_id"] = None
            active["work_items"][1]["status"] = "READY"
            active["resource_accounting"] = {
                "codex": {
                    "window_id": DISPATCH.goal_runner_adapter.resource_window_id(spec, NOW),
                    "launches_in_window": 1, "total_launches": 1,
                    "last_launch_at": prior_codex_time,
                }
            }
            candidate_digest = hashlib.sha256(
                GOAL.canonical_json_bytes(active["candidate_identity"])
            ).hexdigest()
            review_event, _ = GOAL.append_ledger_event(
                ledger_path,
                event_id="accepted-review-round-2",
                event_type="REVIEW_VERDICT_ACCEPTED",
                occurred_at=NOW.replace(hour=9, minute=30).isoformat(),
                goal_id=spec["goal_id"], goal_version=spec["goal_version"],
                logical_work_id=review["work_item_id"],
                attempt_id="review-attempt-2",
                payload={
                    "review_id": "review-round-2",
                    "verdict": "CHANGES_REQUIRED",
                    "candidate_identity_sha256": candidate_digest,
                    "findings": ["finding-repair-required"],
                    "state_patch": DISPATCH.goal_runner_adapter._state_patch(active),
                },
            )
            active["event_cursor"] = {
                "sequence": review_event["sequence"],
                "event_sha256": review_event["event_sha256"],
            }
            GOAL.atomic_write_json(state_path, active)
            runtime = runtime_identity()
            calls = []

            def run(command, **_kwargs):
                calls.append(command)
                if "--discover-runtime" in command:
                    return subprocess.CompletedProcess(command, 0, json.dumps(runtime), "")
                if "--admit-order" in command:
                    order_path = Path(command[command.index("--admit-order") + 1])
                    receipt_path = Path(command[command.index("--admission-receipt") + 1])
                    order = json.loads(order_path.read_text(encoding="utf-8"))
                    receipt = reservation_receipt(
                        order["execution_context"],
                        order_sha256=hashlib.sha256(order_path.read_bytes()).hexdigest(),
                        observed_at=NOW,
                        router_checkpoint_path=(
                            repo / "output/control-plane/repair-admission-router.json"
                        ),
                    )
                    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
                    return subprocess.CompletedProcess(command, 0, json.dumps(receipt), "")
                return subprocess.CompletedProcess(command, 0, "{}", "")

            result = DISPATCH.dispatch_once(
                repo=repo, spec_path=spec_path, state_path=state_path,
                ledger_path=ledger_path, now=NOW,
                router=repo / "scripts/router.py",
                epoch_record=repo / ".ai/epoch.json",
                scope_admission=repo / "scripts/admission.py",
                comments_fetcher=lambda _spec: [authority_comment],
                command_runner=run,
            )
            self.assertEqual("DISPATCHED", result["status"])
            self.assertEqual("DISPATCH_REPAIR", result["decision"]["action"])
            self.assertEqual(1, result["decision"]["total_launches_before"])
            self.assertEqual(4, len(calls))
            self.assertIn("--discover-runtime", calls[0])
            self.assertIn("--admit-order", calls[2])
            order = json.loads((repo / result["order"]["path"]).read_text(encoding="utf-8"))
            self.assertEqual("review-round-2", order["execution_context"]["review"]["review_id"])
            self.assertEqual("CHANGES_REQUIRED", order["execution_context"]["review"]["state"])
            saved = GOAL.load_json(state_path)
            self.assertEqual(2, saved["resource_accounting"]["codex"]["total_launches"])

            restart_runner = Mock()
            restarted = DISPATCH.dispatch_once(
                repo=repo, spec_path=spec_path, state_path=state_path,
                ledger_path=ledger_path, now=NOW.replace(hour=11),
                router=repo / "scripts/router.py",
                epoch_record=repo / ".ai/epoch.json",
                scope_admission=repo / "scripts/admission.py",
                comments_fetcher=lambda _spec: [authority_comment],
                command_runner=restart_runner,
            )
            self.assertEqual("CHECKPOINT_PENDING", restarted["status"])
            restart_runner.assert_not_called()
            self.assertEqual(
                2,
                GOAL.load_json(state_path)["resource_accounting"]["codex"]["total_launches"],
            )
            reservations = [
                row for row in GOAL.read_ledger(ledger_path)
                if row["payload"].get("operation") == "DISPATCH_RESERVED"
            ]
            self.assertEqual(1, len(reservations))
            self.assertEqual(0, reservations[0]["payload"]["runtime_admission"]["model_launches"])

    def test_restart_reconciles_existing_reservation_without_redispatch(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = self.repository(Path(directory))
            spec, spec_path, state_path, ledger_path = self.inputs(repo)
            first_runner = Mock(side_effect=[
                subprocess.CompletedProcess([], 0, "", ""),
                subprocess.CompletedProcess([], 0, "{}", ""),
            ])
            self.call(
                repo, spec_path, state_path, ledger_path,
                comments_fetcher=lambda _spec: [comment(spec)],
                command_runner=first_runner,
            )
            second_runner = Mock()
            result = self.call(
                repo, spec_path, state_path, ledger_path,
                comments_fetcher=lambda _spec: [comment(spec)],
                command_runner=second_runner,
            )
            self.assertEqual("CHECKPOINT_PENDING", result["status"])
            second_runner.assert_not_called()
            reservations = [
                row for row in GOAL.read_ledger(ledger_path)
                if row["payload"].get("operation") == "DISPATCH_RESERVED"
            ]
            self.assertEqual(1, len(reservations))

    def test_stop_marker_prevents_github_read_and_every_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = self.repository(Path(directory))
            _, spec_path, state_path, ledger_path = self.inputs(repo)
            marker = repo / ".ai/ORCHESTRATOR_STOP"
            marker.write_text("stop\n", encoding="utf-8")
            fetcher = Mock()
            before = (state_path.read_bytes(), ledger_path.read_bytes())
            result = self.call(
                repo, spec_path, state_path, ledger_path,
                comments_fetcher=fetcher,
            )
            self.assertEqual("STOPPED", result["status"])
            fetcher.assert_not_called()
            self.assertEqual(before, (state_path.read_bytes(), ledger_path.read_bytes()))
            self.assertTrue(marker.is_file())

            next_day = NOW.replace(day=23)
            restarted = DISPATCH.dispatch_once(
                repo=repo, spec_path=spec_path, state_path=state_path,
                ledger_path=ledger_path, now=next_day,
                router=repo / "scripts/router.py",
                epoch_record=repo / ".ai/epoch.json",
                scope_admission=repo / "scripts/admission.py",
                comments_fetcher=fetcher,
            )
            self.assertEqual("STOPPED", restarted["status"])
            fetcher.assert_not_called()
            self.assertEqual(before, (state_path.read_bytes(), ledger_path.read_bytes()))

    def test_draft_pr_write_is_bound_only_after_exact_github_readback(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = self.repository(Path(directory))
            spec = deepcopy(self.spec)
            spec["work_items"][0]["kind"] = "PUBLISH"
            spec["work_items"][0]["provider"] = "NONE"
            state = GOAL.initial_runner_state(spec, now=NOW.isoformat())
            head = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=repo, text=True,
            ).strip()
            state["candidate_identity"] = {
                "commit": head, "fingerprint": "f" * 64,
                "branch": "codex/test-goal", "pull_request": None,
            }
            state["work_items"][0]["status"] = "VERIFIED"
            state_path = repo / "state.json"
            ledger_path = repo / "ledger.jsonl"
            publication, _ = GOAL.append_ledger_event(
                ledger_path, event_id="publication-readback",
                event_type="RESULT_PUBLICATION_RECORDED",
                occurred_at=NOW.isoformat(), goal_id=spec["goal_id"],
                goal_version=spec["goal_version"],
                logical_work_id=spec["work_items"][0]["work_item_id"],
                attempt_id="attempt-publish",
                payload={"status": "READ_BACK_VERIFIED", "receipt_sha256": "e" * 64},
            )
            state["event_cursor"] = {
                "sequence": publication["sequence"],
                "event_sha256": publication["event_sha256"],
            }
            GOAL.atomic_write_json(state_path, state)
            marker = (
                f"<!-- {DISPATCH.PR_MARKER} goal_id={spec['goal_id']} "
                f"candidate_commit={head} candidate_fingerprint={'f' * 64} -->"
            )
            observed = {
                "number": 61, "headRefOid": head,
                "headRefName": "codex/test-goal", "state": "OPEN",
                "isDraft": True, "url": "https://github.com/owner/repo/pull/61",
                "body": marker,
            }
            runner = Mock(side_effect=[
                subprocess.CompletedProcess([], 0, "[]", ""),
                subprocess.CompletedProcess([], 0, "https://github.com/owner/repo/pull/61\n", ""),
                subprocess.CompletedProcess([], 0, json.dumps(observed), ""),
            ])
            updated = DISPATCH.ensure_candidate_pull_request(
                repo=repo, spec=spec, state=state, state_path=state_path,
                ledger_path=ledger_path, occurred_at=NOW.isoformat(),
                command_runner=runner,
            )
            self.assertEqual(61, updated["candidate_identity"]["pull_request"])
            self.assertEqual(3, runner.call_count)
            self.assertEqual("create", runner.call_args_list[1].args[0][2])
            event = GOAL.read_ledger(ledger_path)[-1]
            self.assertEqual("CANDIDATE_PULL_REQUEST_BOUND", event["payload"]["operation"])
            self.assertEqual("e" * 64, event["payload"]["publication_receipt_sha256"])

    def test_protected_o2_goal_is_rejected_before_github_read(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = self.repository(Path(directory))
            _, spec_path, state_path, ledger_path = self.inputs(repo, protected=True)
            fetcher = Mock()
            with self.assertRaises(DISPATCH.readiness.ProtectedGoalError):
                self.call(
                    repo, spec_path, state_path, ledger_path,
                    comments_fetcher=fetcher,
                )
            fetcher.assert_not_called()


if __name__ == "__main__":
    unittest.main()
