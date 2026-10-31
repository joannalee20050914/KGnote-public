from __future__ import annotations

import importlib.util
import hashlib
import json
import sys
import tempfile
import unittest
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from tests.control_plane.test_goal_continuity import product_goal_spec
from tests.control_plane.test_github_product_goal_control import comment
from tests.control_plane.runtime_admission_fixtures import (
    prepare_model_reservation,
    runtime_identity,
    write_reservation_receipt,
)

SPEC = importlib.util.spec_from_file_location(
    "goal_runner_adapter", ROOT / "scripts/goal_runner_adapter.py"
)
ADAPTER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ADAPTER)
import github_product_goal_control as CONTROL
import goal_continuity as GOAL
import linux_worker_router as ROUTER


NOW = datetime(2026, 10, 22, 10, 0, tzinfo=ZoneInfo("Asia/Taipei"))


class GoalRunnerAdapterTests(unittest.TestCase):
    def setUp(self):
        self.spec = product_goal_spec()
        self.comments = [comment(self.spec, action="APPROVE")]
        self.authority = CONTROL.resolve_authority(self.comments, self.spec)
        self.state = GOAL.initial_runner_state(
            self.spec, now=NOW.isoformat(),
            codex_app_goal_provenance={"goal_id": "APP-GOAL", "status": "completed"},
        )

    def append(self, rows, event_id, event_type, payload, attempt_id=None):
        rows.append(GOAL.prepare_ledger_event(
            rows, event_id=event_id, event_type=event_type,
            occurred_at=NOW.isoformat(), goal_id=self.spec["goal_id"],
            goal_version=self.spec["goal_version"],
            logical_work_id="WI-O2-IMPLEMENT", attempt_id=attempt_id, payload=payload,
        ))

    def activate(self):
        record = self.authority["record"]
        self.state["authority_record"] = deepcopy(record)
        self.state["authority_lease"] = "ACTIVE"
        self.state["lifecycle"] = {
            "state": "ACTIVE", "revision": 1, "changed_at": NOW.isoformat(),
            "reason": "exact Owner authority and go-live receipt verified",
        }
        self.state["go_live_authorized"] = True
        ledger = []
        self.append(ledger, "authority-live", "GOAL_AUTHORITY_VERIFIED", {
            "go_live_authorized": True,
            "authority_comment_id": record["comment_id"],
            "authority_body_sha256": record["body_sha256"],
            "goal_spec_sha256": GOAL.goal_spec_sha256(self.spec),
        })
        return ledger

    def write_order(self, repo, state, *, event_id="product-goal-attempt", stage="codex"):
        order_path = repo / "output" / f"{event_id}.json"
        order_path.parent.mkdir(parents=True, exist_ok=True)
        order = {
            "schema_version": "kgnote.linux-worker-order.v1",
            "event_id": event_id, "stage": stage,
            "working_directory": f"/home/kgnote/.local/share/kgnote/work-items/{event_id}",
            "command": ["/usr/bin/true"],
            "checkpoint_path": str(repo / "output" / f"{event_id}-checkpoint.json"),
        }
        order_path.write_text(json.dumps(order), encoding="utf-8")
        state["work_items"][0]["dispatch_binding"] = {
            "order_path": str(order_path.relative_to(repo)),
            "order_sha256": hashlib.sha256(order_path.read_bytes()).hexdigest(),
            "order_event_id": event_id,
        }
        return order_path, order

    def write_state_and_ledger(self, repo, state, ledger=()):
        state_path, ledger_path = repo / "state.json", repo / "ledger.jsonl"
        GOAL.atomic_write_json(state_path, state)
        for event in ledger:
            GOAL.append_ledger_event(
                ledger_path,
                **{key: event[key] for key in (
                    "event_id", "event_type", "occurred_at", "goal_id",
                    "goal_version", "logical_work_id", "attempt_id", "payload",
                )},
            )
        return state_path, ledger_path

    def reserve_model(
        self, repo, state, action, *, state_path, ledger_path,
        occurred_at=NOW,
    ):
        synchronized = ADAPTER.synchronize_state_from_ledger(
            self.spec, state, GOAL.read_ledger(ledger_path),
            state_path=state_path,
        )
        state.clear()
        state.update(synchronized)
        if not ADAPTER.requires_runtime_admission(self.spec, action):
            return ADAPTER.reserve_dispatch(
                self.spec, state, action, state_path=state_path,
                ledger_path=ledger_path, repo=repo,
                occurred_at=occurred_at.isoformat(),
            )
        order_path, receipt_path = prepare_model_reservation(
            repo, state, action, observed_at=occurred_at,
        )
        return ADAPTER.reserve_dispatch(
            self.spec, state, action, state_path=state_path,
            ledger_path=ledger_path, repo=repo,
            occurred_at=occurred_at.isoformat(),
            prepared_order_path=order_path,
            admission_receipt_path=receipt_path,
        )

    def test_completed_app_goal_does_not_authorize_product_goal(self):
        result = ADAPTER.next_action(
            self.spec, self.state, [],
            {"authority_lease": "PAUSED", "status": "APPROVAL_REQUIRED", "record": None},
            now=NOW, trial=False,
        )
        self.assertEqual("WAIT_AUTHORITY", result["status"])

    def test_foreign_goal_event_and_invalid_state_cursor_fail_closed(self):
        ledger = self.activate()
        foreign = deepcopy(ledger[0])
        foreign["goal_id"] = "GOAL-KGNOTE-FOREIGN"
        foreign["event_sha256"] = GOAL.event_sha256(foreign)
        with self.assertRaisesRegex(GOAL.GoalContractError, "different Goal identity"):
            ADAPTER.next_action(
                self.spec, self.state, [foreign], self.authority, now=NOW, trial=False,
            )
        state = deepcopy(self.state)
        state["event_cursor"] = {"sequence": 1, "event_sha256": "0" * 64}
        with self.assertRaisesRegex(GOAL.GoalContractError, "valid ledger prefix"):
            ADAPTER.next_action(
                self.spec, state, ledger, self.authority, now=NOW, trial=False,
            )

    def test_owner_approval_without_exact_go_live_receipt_stays_dormant(self):
        result = ADAPTER.next_action(
            self.spec, self.state, [], self.authority, now=NOW, trial=True,
        )
        self.assertEqual("TRIAL_ONLY", result["status"])
        result = ADAPTER.next_action(
            self.spec, self.state, [], self.authority, now=NOW, trial=False,
        )
        self.assertEqual("GO_LIVE_NOT_AUTHORIZED", result["status"])

    def test_owner_authority_is_durably_reconciled_and_app_goal_is_irrelevant(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            state_path, ledger_path = self.write_state_and_ledger(repo, self.state)
            result = ADAPTER.reconcile_owner_authority(
                self.spec, self.state, self.authority,
                state_path=state_path, ledger_path=ledger_path,
            )
            active = result["state"]
            self.assertEqual("ACTIVE", active["lifecycle"]["state"])
            self.assertEqual("ACTIVE", active["authority_lease"])
            self.assertTrue(active["go_live_authorized"])
            self.assertEqual("APPROVE", active["authority_record"]["action"])
            types = [row["event_type"] for row in GOAL.read_ledger(ledger_path)]
            self.assertEqual(
                ["GOAL_AUTHORITY_VERIFIED", "GOAL_LIFECYCLE_TRANSITION", "GOAL_LIFECYCLE_TRANSITION"],
                types,
            )
            before = ledger_path.read_bytes()
            replay = ADAPTER.reconcile_owner_authority(
                self.spec, active, self.authority,
                state_path=state_path, ledger_path=ledger_path,
            )
            self.assertEqual([], replay["rejected_transitions"])
            self.assertEqual(before, ledger_path.read_bytes())

    def test_owner_approval_cannot_bypass_goal_dependency_closure_receipt(self):
        self.spec["dependencies"] = ["GOAL-KGNOTE-O1-PRIOR"]
        state = GOAL.initial_runner_state(self.spec, now=NOW.isoformat())
        authority = CONTROL.resolve_authority([comment(self.spec)], self.spec)
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            state_path, ledger_path = self.write_state_and_ledger(repo, state)
            rejected = ADAPTER.reconcile_owner_authority(
                self.spec, state, authority,
                state_path=state_path, ledger_path=ledger_path,
            )
            self.assertEqual("APPROVAL_REQUIRED", rejected["state"]["lifecycle"]["state"])
            self.assertIn("dependency", rejected["rejected_transitions"][0]["reason"])

        receipt = {
            "dependency_id": "GOAL-KGNOTE-O1-PRIOR", "status": "CLOSED",
            "source_kind": "PRODUCT_GOAL_CLOSED", "goal_version": "prior-v1",
            "goal_spec_sha256": "a" * 64, "evidence_sha256": "b" * 64,
        }
        state = GOAL.initial_runner_state(
            self.spec, now=NOW.isoformat(), dependency_receipts=[receipt]
        )
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            state_path, ledger_path = self.write_state_and_ledger(repo, state)
            active = ADAPTER.reconcile_owner_authority(
                self.spec, state, authority,
                state_path=state_path, ledger_path=ledger_path,
            )
            self.assertEqual("ACTIVE", active["state"]["lifecycle"]["state"])

    def test_premature_accept_is_recorded_rejected_and_cannot_close_goal(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            state_path, ledger_path = self.write_state_and_ledger(repo, self.state)
            comments = [
                comment(self.spec, action="APPROVE", comment_id=100),
                comment(self.spec, action="ACCEPT", comment_id=101),
            ]
            authority = CONTROL.resolve_authority(comments, self.spec)
            result = ADAPTER.reconcile_owner_authority(
                self.spec, self.state, authority,
                state_path=state_path, ledger_path=ledger_path,
            )
            self.assertEqual("ACTIVE", result["state"]["lifecycle"]["state"])
            self.assertEqual(1, len(result["rejected_transitions"]))
            history = GOAL.reduce_ledger(GOAL.read_ledger(ledger_path))["authority_history"]
            self.assertFalse(history[-1]["accepted"])
            repeated = ADAPTER.reconcile_owner_authority(
                self.spec, result["state"], authority,
                state_path=state_path, ledger_path=ledger_path,
            )
            self.assertEqual(1, len(repeated["rejected_transitions"]))

    def test_authority_reconciliation_resumes_after_ledger_fsync_before_state_write(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            state_path, ledger_path = self.write_state_and_ledger(repo, self.state)
            record = self.authority["record"]
            GOAL.append_ledger_event(
                ledger_path,
                **ADAPTER._authority_event_fields(
                    self.spec, record, suffix="accepted",
                    event_type="GOAL_AUTHORITY_VERIFIED",
                    payload={
                        "accepted": True, "action": "APPROVE",
                        "authority_comment_id": record["comment_id"],
                        "authority_body_sha256": record["body_sha256"],
                        "goal_spec_sha256": GOAL.goal_spec_sha256(self.spec),
                        "go_live_authorized": True,
                    },
                ),
            )
            recovered = ADAPTER.reconcile_owner_authority(
                self.spec, self.state, self.authority,
                state_path=state_path, ledger_path=ledger_path,
            )
            self.assertEqual("ACTIVE", recovered["state"]["lifecycle"]["state"])
            self.assertEqual(3, len(GOAL.read_ledger(ledger_path)))

    def test_path_a_quota_recovery_then_changes_required_repair(self):
        ledger = self.activate()
        self.state["runtime_block"] = {"failure_class": "USAGE_LIMIT_REACHED"}
        result = ADAPTER.next_action(
            self.spec, self.state, ledger, self.authority, now=NOW, trial=False,
        )
        self.assertEqual("WAIT_QUOTA_BACKOFF", result["status"])
        self.state["runtime_block"] = {"failure_class": "CHANGES_REQUIRED"}
        self.state["work_items"][0]["status"] = "REPAIR_REQUIRED"
        result = ADAPTER.next_action(
            self.spec, self.state, ledger, self.authority, now=NOW, trial=False,
        )
        self.assertEqual("RECOVERY_READY", result["status"])
        self.assertEqual("DISPATCH_REPAIR", result["action"])
        self.assertFalse(result["requires_model"])

    def test_overnight_window_uses_the_weekday_on_which_the_window_started(self):
        spec = deepcopy(self.spec)
        spec["work_window"] = {
            "timezone": "Asia/Taipei", "weekdays": [0],
            "start": "22:00", "end": "02:00",
        }
        monday_late = datetime(2026, 10, 26, 23, 0, tzinfo=ZoneInfo("Asia/Taipei"))
        tuesday_early = datetime(2026, 10, 27, 1, 0, tzinfo=ZoneInfo("Asia/Taipei"))
        monday_early = datetime(2026, 10, 26, 1, 0, tzinfo=ZoneInfo("Asia/Taipei"))
        tuesday_end = datetime(2026, 10, 27, 2, 0, tzinfo=ZoneInfo("Asia/Taipei"))

        self.assertTrue(ADAPTER.in_work_window(spec, monday_late))
        self.assertTrue(ADAPTER.in_work_window(spec, tuesday_early))
        self.assertFalse(ADAPTER.in_work_window(spec, monday_early))
        self.assertFalse(ADAPTER.in_work_window(spec, tuesday_end))
        self.assertEqual(
            "2026-10-26@22:00-02:00",
            ADAPTER.resource_window_id(spec, monday_late),
        )
        self.assertEqual(
            ADAPTER.resource_window_id(spec, monday_late),
            ADAPTER.resource_window_id(spec, tuesday_early),
        )

    def test_path_b_valid_verdict_publication_and_completion_recovery_do_not_launch_model(self):
        ledger = self.activate()
        self.append(ledger, "review-pass", "REVIEW_VERDICT_ACCEPTED", {
            "review_id": "round-7", "verdict": "PASS",
        }, "review-round-7")
        self.state["runtime_block"] = {"failure_class": "GITHUB_WRITEBACK_FAILED"}
        result = ADAPTER.next_action(
            self.spec, self.state, ledger, self.authority, now=NOW, trial=False,
        )
        self.assertEqual("RETRY_PUBLICATION", result["action"])
        self.assertFalse(result["requires_model"])
        self.state["runtime_block"] = {"failure_class": "COMPLETION_GATE_FAILED"}
        result = ADAPTER.next_action(
            self.spec, self.state, ledger, self.authority, now=NOW, trial=False,
        )
        self.assertEqual("RETRY_COMPLETION_GATE", result["action"])
        self.assertFalse(result["requires_model"])
        projection = GOAL.reduce_ledger(ledger)
        self.assertEqual(1, len(projection["review_verdicts"]))

    def test_strategy_exhaustion_blocks_only_affected_subgraph(self):
        second_spec = {
            "work_item_id": "WI-O2-INDEPENDENT", "milestone_id": "O2-M2",
            "kind": "VERIFY", "dependencies": [],
            "obligation_ids": ["OBL-O2-INDEPENDENT"],
            "allowed_operations": ["review"], "provider": "NONE",
        }
        self.spec["obligations"].append({
            "obligation_id": "OBL-O2-INDEPENDENT", "semantic_key": "b" * 64,
            "authority_refs": ["KG-GOV-04"], "description": "Independent evidence.",
        })
        self.spec["work_items"].extend([
            second_spec,
            {
                "work_item_id": "WI-O2-INDEPENDENT-REVIEW", "milestone_id": "O2-M2",
                "kind": "REVIEW", "dependencies": ["WI-O2-INDEPENDENT"],
                "obligation_ids": ["OBL-O2-INDEPENDENT"],
                "allowed_operations": ["review"], "provider": "claude",
            },
            {
                "work_item_id": "WI-O2-INDEPENDENT-REPAIR", "milestone_id": "O2-M2",
                "kind": "REPAIR", "dependencies": ["WI-O2-INDEPENDENT-REVIEW"],
                "obligation_ids": ["OBL-O2-INDEPENDENT"],
                "allowed_operations": ["commit"], "provider": "codex",
            },
        ])
        self.state = GOAL.initial_runner_state(self.spec, now=NOW.isoformat())
        self.authority = CONTROL.resolve_authority(
            [comment(self.spec, action="APPROVE")], self.spec
        )
        ledger = self.activate()
        self.state["work_items"][0]["status"] = "BLOCKED"
        self.state["work_items"][0]["block"] = {
            "failure_class": "PRODUCT_DECISION_REQUIRED",
            "reason": "product WHAT conflict",
            "release_condition": "Owner approves a revised exact Goal",
        }
        independent = next(
            row for row in self.state["work_items"]
            if row["work_item_id"] == "WI-O2-INDEPENDENT"
        )
        independent["status"] = "VERIFY_REQUIRED"
        result = ADAPTER.next_action(
            self.spec, self.state, ledger, self.authority, now=NOW, trial=False,
        )
        self.assertEqual("WI-O2-INDEPENDENT", result["work_item_id"])
        self.assertEqual("RUN_DETERMINISTIC_VERIFICATION", result["action"])
        self.assertFalse(result["requires_model"])

    def test_product_decision_checkpoint_blocks_only_affected_subgraph(self):
        self.spec["obligations"].append({
            "obligation_id": "OBL-O2-INDEPENDENT", "semantic_key": "b" * 64,
            "authority_refs": ["KG-GOV-04"], "description": "Independent evidence.",
        })
        self.spec["work_items"].extend([
            {
                "work_item_id": "WI-O2-INDEPENDENT", "milestone_id": "O2-M2",
                "kind": "VERIFY", "dependencies": [],
                "obligation_ids": ["OBL-O2-INDEPENDENT"],
                "allowed_operations": ["review"], "provider": "NONE",
            },
            {
                "work_item_id": "WI-O2-INDEPENDENT-REVIEW", "milestone_id": "O2-M2",
                "kind": "REVIEW", "dependencies": ["WI-O2-INDEPENDENT"],
                "obligation_ids": ["OBL-O2-INDEPENDENT"],
                "allowed_operations": ["review"], "provider": "claude",
            },
            {
                "work_item_id": "WI-O2-INDEPENDENT-REPAIR", "milestone_id": "O2-M2",
                "kind": "REPAIR", "dependencies": ["WI-O2-INDEPENDENT-REVIEW"],
                "obligation_ids": ["OBL-O2-INDEPENDENT"],
                "allowed_operations": ["commit"], "provider": "codex",
            },
        ])
        self.state = GOAL.initial_runner_state(self.spec, now=NOW.isoformat())
        self.authority = CONTROL.resolve_authority(
            [comment(self.spec, action="APPROVE")], self.spec
        )
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            self.write_order(repo, self.state, event_id="product-decision", stage="codex")
            state_path, ledger_path = self.write_state_and_ledger(repo, self.state)
            active = ADAPTER.reconcile_owner_authority(
                self.spec, self.state, self.authority,
                state_path=state_path, ledger_path=ledger_path,
            )["state"]
            action = ADAPTER.next_action(
                self.spec, active, GOAL.read_ledger(ledger_path), self.authority,
                now=NOW, trial=False,
            )
            reserved, _, attempt_id = self.reserve_model(
                repo, active, action, state_path=state_path,
                ledger_path=ledger_path,
            )
            order = json.loads((repo / "output" / "product-decision.json").read_text())
            result = {
                "schema_version": "kgnote.product-goal-worker-result.v1",
                "goal_id": self.spec["goal_id"],
                "goal_version": self.spec["goal_version"],
                "goal_spec_sha256": GOAL.goal_spec_sha256(self.spec),
                "work_item_id": "WI-O2-IMPLEMENT",
                "order_event_id": order["event_id"],
                "outcome": "PRODUCT_DECISION_REQUIRED",
                "obligation_evaluations": [{
                    "obligation_id": "OBL-O2-CORE",
                    "progress_class": "EVIDENCE_INSUFFICIENT",
                    "evidence_sha256": "c" * 64,
                }],
                "usage": {
                    "status": "OBSERVED", "input_tokens": 10,
                    "output_tokens": 5, "source": "worker_checkpoint",
                },
                "review_verdict": None,
                "publication": None,
            }
            checkpoint = {
                "schema_version": "kgnote.linux-worker-route.v1",
                "status": "COMPLETED", "event_id": order["event_id"],
                "command_digest": ROUTER.command_digest(
                    ROUTER.WorkerOrder.from_dict(order)
                ),
                "execution_evidence": {"product_goal_result": result},
            }
            Path(order["checkpoint_path"]).write_text(json.dumps(checkpoint))
            reconciled = ADAPTER.reconcile_dispatch_checkpoint(
                self.spec, reserved, state_path=state_path, ledger_path=ledger_path,
                repo=repo, attempt_id=attempt_id, occurred_at=NOW.isoformat(),
            )
            self.assertEqual("PRODUCT_DECISION_REQUIRED", reconciled["outcome"])
            saved = GOAL.load_json(state_path)
            affected = next(
                row for row in saved["work_items"]
                if row["work_item_id"] == "WI-O2-IMPLEMENT"
            )
            self.assertEqual("BLOCKED", affected["status"])
            self.assertEqual(
                "PRODUCT_DECISION_REQUIRED", affected["block"]["failure_class"]
            )
            self.assertNotIn("runtime_block", saved)
            projected = GOAL.reduce_ledger(GOAL.read_ledger(ledger_path))
            self.assertEqual(1, len(projected["notifications"]))
            notice = next(iter(projected["notifications"].values()))
            self.assertEqual("PRODUCT_WHAT_CONFLICT", notice["event_kind"])
            next_work = ADAPTER.next_action(
                self.spec, saved, GOAL.read_ledger(ledger_path), self.authority,
                now=NOW, trial=False,
            )
            self.assertEqual("WI-O2-INDEPENDENT", next_work["work_item_id"])
            self.assertEqual("RUN_DETERMINISTIC_VERIFICATION", next_work["action"])

    def test_two_no_progress_cycles_adjust_then_block_affected_work(self):
        for _ in range(6):
            self.state = ADAPTER.apply_obligation_progress(
                self.state, self.spec, work_item_id="WI-O2-IMPLEMENT",
                obligation_id="OBL-O2-CORE", progress_class="NO_OBLIGATION_PROGRESS",
            )
        self.assertEqual(3, self.state["work_items"][0]["strategy_adjustments"])
        self.assertEqual("BLOCKED", self.state["work_items"][0]["status"])
        self.assertEqual(
            "STRATEGY_EXHAUSTED", self.state["work_items"][0]["block"]["failure_class"]
        )
        ledger = self.activate()
        decision = ADAPTER.next_action(
            self.spec, self.state, ledger, self.authority, now=NOW, trial=False,
        )
        self.assertEqual("HUMAN_DECISION_REQUIRED", decision["status"])
        with tempfile.TemporaryDirectory() as directory:
            ledger_path = Path(directory) / "ledger.jsonl"
            for event in ledger:
                GOAL.append_ledger_event(
                    ledger_path,
                    **{key: event[key] for key in (
                        "event_id", "event_type", "occurred_at", "goal_id",
                        "goal_version", "logical_work_id", "attempt_id", "payload",
                    )},
                )
            first = ADAPTER.queue_human_decision_notifications(
                self.spec, self.state, ledger_path=ledger_path,
                occurred_at=NOW.isoformat(),
            )
            second = ADAPTER.queue_human_decision_notifications(
                self.spec, self.state, ledger_path=ledger_path,
                occurred_at=NOW.isoformat(),
            )
            self.assertEqual(first[0]["notification_id"], second[0]["notification_id"])
            projection = GOAL.reduce_ledger(GOAL.read_ledger(ledger_path))
            self.assertEqual(1, len(projection["notifications"]))

    def test_durable_reservation_forces_reconciliation_before_redispatch(self):
        ledger = self.activate()
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            order_path = repo / "output" / "sealed-order.json"
            order_path.parent.mkdir(parents=True)
            order = {
                "schema_version": "kgnote.linux-worker-order.v1",
                "event_id": "o2-codex-attempt-1",
                "stage": "codex",
                "working_directory": "/home/kgnote/.local/share/kgnote/work-items/o2-test",
                "command": ["/usr/bin/true"],
                "checkpoint_path": str(repo / "checkpoint.json"),
            }
            order_path.write_text(json.dumps(order), encoding="utf-8")
            self.state["work_items"][0]["dispatch_binding"] = {
                "order_path": "output/sealed-order.json",
                "order_sha256": hashlib.sha256(order_path.read_bytes()).hexdigest(),
                "order_event_id": order["event_id"],
            }
            state_path = repo / "state.json"
            ledger_path = repo / "ledger.jsonl"
            GOAL.atomic_write_json(state_path, self.state)
            for event in ledger:
                GOAL.append_ledger_event(
                    ledger_path,
                    **{
                        key: event[key]
                        for key in (
                            "event_id", "event_type", "occurred_at", "goal_id",
                            "goal_version", "logical_work_id", "attempt_id", "payload",
                        )
                    },
                )
            action = ADAPTER.next_action(
                self.spec, self.state, ledger, self.authority, now=NOW, trial=False,
            )
            reserved, selected_order, attempt_id = self.reserve_model(
                repo, self.state, action, state_path=state_path,
                ledger_path=ledger_path,
            )
            self.assertEqual(order_path, selected_order)
            self.assertEqual("DISPATCHING", reserved["work_items"][0]["status"])
            self.assertEqual(1, reserved["work_items"][0]["attempts"])
            restarted = ADAPTER.next_action(
                self.spec, reserved, GOAL.read_ledger(ledger_path), self.authority,
                now=NOW, trial=False,
            )
            self.assertEqual("RECOVERY_READY", restarted["status"])
            self.assertEqual("RECONCILE_CHECKPOINT", restarted["action"])
            self.assertEqual(attempt_id, restarted["attempt_id"])
            for lease in ("PAUSED", "REVOKED"):
                stopped = deepcopy(reserved)
                stopped["authority_lease"] = lease
                stopped["go_live_authorized"] = False
                stopped["lifecycle"] = {
                    "state": "BLOCKED", "revision": 2,
                    "changed_at": NOW.isoformat(), "reason": f"Owner {lease.lower()}",
                }
                stopped_authority = {
                    **self.authority, "authority_lease": lease, "status": "BLOCKED",
                }
                recovery = ADAPTER.next_action(
                    self.spec, stopped, GOAL.read_ledger(ledger_path), stopped_authority,
                    now=NOW, trial=False,
                )
                self.assertEqual("RECONCILE_CHECKPOINT", recovery["action"])
                self.assertFalse(recovery["requires_model"])

    def test_dispatch_reservation_recovers_after_ledger_fsync_before_state_write(self):
        ledger = self.activate()
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            self.write_order(repo, self.state, event_id="crash-window", stage="codex")
            state_path, ledger_path = self.write_state_and_ledger(
                repo, self.state, ledger
            )
            state = ADAPTER.synchronize_state_from_ledger(
                self.spec, self.state, ledger, state_path=state_path,
            )
            action = ADAPTER.next_action(
                self.spec, state, ledger, self.authority,
                now=NOW, trial=False,
            )
            wrong_provider = {**action, "provider": "claude"}
            with self.assertRaisesRegex(ADAPTER.GoalRunnerError, "provider codex"):
                ADAPTER.validated_bound_order(
                    self.spec, state, wrong_provider, repo=repo
                )

            with patch.object(
                ADAPTER.goal_continuity, "atomic_write_json",
                side_effect=OSError("injected state replacement crash"),
            ):
                with self.assertRaisesRegex(OSError, "injected"):
                    self.reserve_model(
                        repo, state, action,
                        state_path=state_path, ledger_path=ledger_path,
                    )

            rows = GOAL.read_ledger(ledger_path)
            reservation = rows[-1]
            self.assertEqual("DISPATCH_RESERVED", reservation["payload"]["operation"])
            recovered = ADAPTER.synchronize_state_from_ledger(
                self.spec, state, rows, state_path=None,
            )
            work = recovered["work_items"][0]
            self.assertEqual("DISPATCHING", work["status"])
            self.assertEqual(reservation["attempt_id"], work["active_attempt_id"])
            self.assertEqual(1, work["attempts"])
            self.assertEqual(1, recovered["resource_accounting"]["codex"]["total_launches"])
            restart = ADAPTER.next_action(
                self.spec, recovered, rows, self.authority,
                now=NOW, trial=False,
            )
            self.assertEqual("RECOVERY_READY", restart["status"])
            self.assertEqual("RECONCILE_CHECKPOINT", restart["action"])

    def test_reservation_rechecks_window_and_goal_total_after_planning(self):
        ledger = self.activate()
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            self.write_order(repo, self.state, event_id="stale-plan", stage="codex")
            state_path, ledger_path = self.write_state_and_ledger(
                repo, self.state, ledger
            )
            action = ADAPTER.next_action(
                self.spec, self.state, ledger, self.authority,
                now=NOW, trial=False,
            )
            outside = datetime(
                2026, 10, 22, 23, 0, tzinfo=ZoneInfo("Asia/Taipei")
            )
            with self.assertRaisesRegex(
                ADAPTER.GoalRunnerError, "outside the authorized work window"
            ):
                ADAPTER.reserve_dispatch(
                    self.spec, self.state, action,
                    state_path=state_path, ledger_path=ledger_path, repo=repo,
                    occurred_at=outside.isoformat(),
                )

            for index in range(12):
                GOAL.append_ledger_event(
                    ledger_path,
                    event_id=f"codex-prior-{index}",
                    event_type="MODEL_ATTEMPT_STARTED",
                    occurred_at=(NOW - ADAPTER.timedelta(days=1)).isoformat(),
                    goal_id=self.spec["goal_id"],
                    goal_version=self.spec["goal_version"],
                    logical_work_id="WI-O2-IMPLEMENT",
                    attempt_id=f"codex-prior-{index}",
                    payload={"provider": "codex"},
                )
            current_state = GOAL.load_json(state_path)
            with self.assertRaisesRegex(
                ADAPTER.GoalRunnerError, "WAIT_GOAL_RESOURCE_LIMIT"
            ):
                ADAPTER.reserve_dispatch(
                    self.spec, current_state, action,
                    state_path=state_path, ledger_path=ledger_path, repo=repo,
                    occurred_at=NOW.isoformat(),
                )

    def test_reservation_rejects_stale_state_and_runtime_recovery_bypass(self):
        ledger = self.activate()
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            self.write_order(repo, self.state, event_id="runtime-block", stage="codex")
            state_path, ledger_path = self.write_state_and_ledger(
                repo, self.state, ledger
            )
            action = ADAPTER.next_action(
                self.spec, self.state, ledger, self.authority,
                now=NOW, trial=False,
            )
            blocked = deepcopy(self.state)
            blocked["runtime_block"] = {
                "failure_class": "USAGE_LIMIT_REACHED",
                "retry_at": (NOW + ADAPTER.timedelta(hours=1)).isoformat(),
            }
            GOAL.atomic_write_json(state_path, blocked)
            with self.assertRaisesRegex(
                ADAPTER.GoalRunnerError, "in-memory Runner state is stale"
            ):
                ADAPTER.reserve_dispatch(
                    self.spec, self.state, action,
                    state_path=state_path, ledger_path=ledger_path, repo=repo,
                    occurred_at=NOW.isoformat(),
                )
            with self.assertRaisesRegex(
                ADAPTER.GoalRunnerError, "durable runtime recovery condition"
            ):
                ADAPTER.reserve_dispatch(
                    self.spec, blocked, action,
                    state_path=state_path, ledger_path=ledger_path, repo=repo,
                    occurred_at=NOW.isoformat(),
                )

    def test_checkpoint_result_separates_usage_verdict_obligation_and_acceptance(self):
        self.spec["work_items"] = [self.spec["work_items"][0]]
        self.spec["work_items"][0]["kind"] = "REVIEW"
        self.spec["work_items"][0]["provider"] = "claude"
        self.spec["work_items"][0]["allowed_operations"] = ["review"]
        self.spec["work_items"].append({
            "work_item_id": "WI-O2-REPAIR", "milestone_id": "O2-M1",
            "kind": "REPAIR", "dependencies": ["WI-O2-IMPLEMENT"],
            "obligation_ids": ["OBL-O2-CORE"],
            "allowed_operations": ["commit", "push"], "provider": "codex",
        })
        self.state = GOAL.initial_runner_state(self.spec, now=NOW.isoformat())
        self.authority = CONTROL.resolve_authority([comment(self.spec)], self.spec)
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            self.write_order(repo, self.state, event_id="review-result", stage="claude")
            state_path, ledger_path = self.write_state_and_ledger(repo, self.state)
            active = ADAPTER.reconcile_owner_authority(
                self.spec, self.state, self.authority,
                state_path=state_path, ledger_path=ledger_path,
            )["state"]
            action = ADAPTER.next_action(
                self.spec, active, GOAL.read_ledger(ledger_path), self.authority,
                now=NOW, trial=False,
            )
            reserved, _, attempt_id = self.reserve_model(
                repo, active, action, state_path=state_path,
                ledger_path=ledger_path,
            )
            order = json.loads((repo / "output" / "review-result.json").read_text())
            parsed = ROUTER.WorkerOrder.from_dict(order)
            result = {
                "schema_version": "kgnote.product-goal-worker-result.v1",
                "goal_id": self.spec["goal_id"], "goal_version": self.spec["goal_version"],
                "goal_spec_sha256": GOAL.goal_spec_sha256(self.spec),
                "work_item_id": "WI-O2-IMPLEMENT", "order_event_id": order["event_id"],
                "outcome": "REVIEW_PASS",
                "obligation_evaluations": [{
                    "obligation_id": "OBL-O2-CORE", "progress_class": "VERIFIED_RESOLVED",
                    "evidence_sha256": "c" * 64,
                }],
                "usage": {"status": "OBSERVED", "input_tokens": 120, "output_tokens": 30, "source": "claude_result"},
                "review_verdict": {"review_id": "review-1", "verdict": "PASS", "candidate_identity_sha256": "d" * 64},
                "publication": None,
            }
            checkpoint = {
                "schema_version": "kgnote.linux-worker-route.v1", "status": "COMPLETED",
                "event_id": order["event_id"], "command_digest": ROUTER.command_digest(parsed),
                "execution_evidence": {"product_goal_result": result},
            }
            Path(order["checkpoint_path"]).write_text(json.dumps(checkpoint), encoding="utf-8")
            reconciled = ADAPTER.reconcile_dispatch_checkpoint(
                self.spec, reserved, state_path=state_path, ledger_path=ledger_path,
                repo=repo, attempt_id=attempt_id, occurred_at=NOW.isoformat(),
            )
            self.assertEqual("ACCEPTANCE_REQUIRED", reconciled["lifecycle"])
            projection = GOAL.reduce_ledger(GOAL.read_ledger(ledger_path))
            self.assertTrue(projection["model_attempts"][attempt_id]["finished"])
            self.assertEqual(150, projection["usage"][attempt_id]["input_tokens"] + projection["usage"][attempt_id]["output_tokens"])
            self.assertEqual("PASS", projection["review_verdicts"][0]["verdict"])
            self.assertEqual("VERIFIED_RESOLVED", projection["obligations"]["OBL-O2-CORE"]["progress_class"])
            self.assertEqual(1, len(projection["notifications"]))

            # Simulate a crash after ledger fsync but before state replacement.
            GOAL.atomic_write_json(state_path, reserved)
            recovered = ADAPTER.synchronize_state_from_ledger(
                self.spec, reserved, GOAL.read_ledger(ledger_path), state_path=state_path,
            )
            self.assertEqual("ACCEPTANCE_REQUIRED", recovered["lifecycle"]["state"])
            self.assertEqual("VERIFIED", recovered["work_items"][0]["status"])

            accepted_comments = [
                comment(self.spec, action="APPROVE", comment_id=100),
                comment(self.spec, action="ACCEPT", comment_id=101),
            ]
            accepted = ADAPTER.reconcile_owner_authority(
                self.spec, recovered, CONTROL.resolve_authority(accepted_comments, self.spec),
                state_path=state_path, ledger_path=ledger_path,
            )
            self.assertEqual("CLOSED", accepted["state"]["lifecycle"]["state"])
            self.assertFalse(accepted["state"]["go_live_authorized"])

    def test_generic_review_changes_required_reconciles_to_pre_authorized_repair(self):
        review = deepcopy(self.spec["work_items"][0])
        review.update({"kind": "REVIEW", "provider": "claude", "allowed_operations": ["review"]})
        repair = deepcopy(self.spec["work_items"][2])
        repair["dependencies"] = [review["work_item_id"]]
        self.spec["work_items"] = [review, repair]
        self.state = GOAL.initial_runner_state(self.spec, now=NOW.isoformat())
        self.state["candidate_identity"] = {
            "commit": "1" * 40, "fingerprint": "2" * 64,
            "branch": "codex/generic-review-repair", "pull_request": 47,
        }
        self.authority = CONTROL.resolve_authority([comment(self.spec)], self.spec)
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            state_path, ledger_path = self.write_state_and_ledger(repo, self.state)
            active = ADAPTER.reconcile_owner_authority(
                self.spec, self.state, self.authority,
                state_path=state_path, ledger_path=ledger_path,
            )["state"]
            action = ADAPTER.next_action(
                self.spec, active, GOAL.read_ledger(ledger_path), self.authority,
                now=NOW, trial=False,
            )
            runtime = runtime_identity()
            _, order_path, order, attempt_id = ADAPTER.ensure_bound_order(
                self.spec, active, action, repo=repo, state_path=state_path,
                ledger_path=ledger_path, occurred_at=NOW.isoformat(),
                runtime_identity=runtime, persist_binding=False,
            )
            receipt_path = write_reservation_receipt(
                repo, order_path, observed_at=NOW,
            )
            reserved, _, reserved_attempt = ADAPTER.reserve_dispatch(
                self.spec, active, action, state_path=state_path,
                ledger_path=ledger_path, repo=repo, occurred_at=NOW.isoformat(),
                prepared_order_path=order_path,
                admission_receipt_path=receipt_path,
            )
            self.assertEqual(attempt_id, reserved_attempt)
            context = order["execution_context"]
            result = {
                "schema_version": "kgnote.product-goal-worker-result.v1",
                "goal_id": self.spec["goal_id"],
                "goal_version": self.spec["goal_version"],
                "goal_spec_sha256": GOAL.goal_spec_sha256(self.spec),
                "work_item_id": review["work_item_id"],
                "order_event_id": order["event_id"],
                "attempt_id": attempt_id, "stage": "claude", "provider": "claude",
                "result_state": "COMPLETED", "failure_class": None,
                "outcome": "REVIEW_CHANGES_REQUIRED",
                "candidate": deepcopy(active["candidate_identity"]),
                "obligation_evaluations": [{
                    "obligation_id": "OBL-O2-CORE",
                    "progress_class": "EVIDENCE_INSUFFICIENT",
                    "evidence_sha256": "3" * 64,
                }],
                "usage": {
                    "status": "OBSERVED", "input_tokens": 20,
                    "output_tokens": 5, "source": "claude_result",
                },
                "review_verdict": {
                    "review_id": context["review"]["review_id"],
                    "verdict": "CHANGES_REQUIRED",
                    "candidate_identity_sha256": context["review"]["candidate_identity_sha256"],
                },
                "review_findings": [{"id": "F-1", "summary": "repair required"}],
                "publication": None,
                "execution": {"exit_code": 0},
                "dispatch_envelope_sha256": context["dispatch_envelope_sha256"],
            }
            checkpoint = {
                "schema_version": "kgnote.linux-worker-route.v1",
                "status": "COMPLETED", "event_id": order["event_id"],
                "command_digest": ROUTER.command_digest(ROUTER.WorkerOrder.from_dict(order)),
                "execution_evidence": {"product_goal_result": result},
            }
            Path(order["checkpoint_path"]).parent.mkdir(parents=True, exist_ok=True)
            Path(order["checkpoint_path"]).write_text(json.dumps(checkpoint), encoding="utf-8")
            routed = ADAPTER.record_route_outcome(
                self.spec, reserved, state_path=state_path,
                work_item_id=review["work_item_id"], attempt_id=attempt_id,
                route_exit_code=0, occurred_at=NOW.isoformat(),
            )
            reconciled = ADAPTER.reconcile_dispatch_checkpoint(
                self.spec, routed, state_path=state_path, ledger_path=ledger_path,
                repo=repo, attempt_id=attempt_id, occurred_at=NOW.isoformat(),
            )
            self.assertEqual("REVIEW_CHANGES_REQUIRED", reconciled["outcome"])
            saved = GOAL.load_json(state_path)
            self.assertEqual("VERIFIED", saved["work_items"][0]["status"])
            self.assertEqual("READY", saved["work_items"][1]["status"])
            repair_action = ADAPTER.next_action(
                self.spec, saved, GOAL.read_ledger(ledger_path), self.authority,
                now=NOW, trial=False,
            )
            self.assertEqual("DISPATCH_REPAIR", repair_action["action"])
            projection = GOAL.reduce_ledger(GOAL.read_ledger(ledger_path))
            self.assertEqual("CHANGES_REQUIRED", projection["review_verdicts"][-1]["verdict"])

    def test_429_checkpoint_is_attempt_not_verdict_and_resumes_after_backoff(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            self.write_order(repo, self.state, event_id="quota-result", stage="codex")
            state_path, ledger_path = self.write_state_and_ledger(repo, self.state)
            active = ADAPTER.reconcile_owner_authority(
                self.spec, self.state, self.authority,
                state_path=state_path, ledger_path=ledger_path,
            )["state"]
            action = ADAPTER.next_action(
                self.spec, active, GOAL.read_ledger(ledger_path), self.authority,
                now=NOW, trial=False,
            )
            reserved, _, attempt_id = self.reserve_model(
                repo, active, action, state_path=state_path,
                ledger_path=ledger_path,
            )
            order = json.loads((repo / "output" / "quota-result.json").read_text())
            checkpoint = {
                "schema_version": "kgnote.linux-worker-route.v1", "status": "FAILED_CLOSED",
                "reason": "guest_worker_failed", "event_id": order["event_id"],
                "command_digest": ROUTER.command_digest(ROUTER.WorkerOrder.from_dict(order)),
                "execution_evidence": {
                    "failure_class": "USAGE_LIMIT_REACHED",
                    "token_usage": {"input_tokens": 0, "output_tokens": 0, "source": "provider_checkpoint"},
                },
            }
            Path(order["checkpoint_path"]).write_text(json.dumps(checkpoint), encoding="utf-8")
            outcome = ADAPTER.reconcile_dispatch_checkpoint(
                self.spec, reserved, state_path=state_path, ledger_path=ledger_path,
                repo=repo, attempt_id=attempt_id, occurred_at=NOW.isoformat(),
            )
            self.assertEqual("USAGE_LIMIT_REACHED", outcome["outcome"])
            saved = GOAL.load_json(state_path)
            wait = ADAPTER.next_action(
                self.spec, saved, GOAL.read_ledger(ledger_path), self.authority,
                now=NOW, trial=False,
            )
            self.assertEqual("WAIT_QUOTA_BACKOFF", wait["status"])
            resumed = ADAPTER.next_action(
                self.spec, saved, GOAL.read_ledger(ledger_path), self.authority,
                now=NOW + ADAPTER.timedelta(seconds=3601), trial=False,
            )
            self.assertEqual("RECOVERY_READY", resumed["status"])
            self.assertEqual("RESUME_AFTER_QUOTA", resumed["action"])
            durable_resume = ADAPTER.resume_after_quota_backoff(
                self.spec, saved, state_path=state_path, ledger_path=ledger_path,
                now=NOW + ADAPTER.timedelta(seconds=3601),
            )
            self.assertEqual("QUOTA_BACKOFF_RESUMED", durable_resume["status"])
            after_resume = GOAL.load_json(state_path)
            self.assertNotIn("runtime_block", after_resume)
            self.assertNotIn(
                "quota_retry_at",
                after_resume["resource_accounting"]["codex"],
            )
            ready = ADAPTER.next_action(
                self.spec, after_resume, GOAL.read_ledger(ledger_path), self.authority,
                now=NOW + ADAPTER.timedelta(seconds=3601), trial=False,
            )
            self.assertEqual("ACTION_READY", ready["status"])
            projection = GOAL.reduce_ledger(GOAL.read_ledger(ledger_path))
            self.assertEqual([], projection["review_verdicts"])
            self.assertTrue(projection["model_attempts"][attempt_id]["finished"])
            self.assertEqual("OBSERVED", projection["usage"][attempt_id]["status"])
            self.assertEqual(0, projection["usage"][attempt_id]["input_tokens"])

    def test_reconciled_operational_failures_release_durably_before_replan(self):
        expected_actions = {
            "DETERMINISTIC_WORKER_FAILURE": "RETRY_FAILED_WORK",
            "GITHUB_WRITEBACK_FAILED": "RETRY_PUBLICATION",
            "COMPLETION_GATE_FAILED": "RETRY_COMPLETION_GATE",
        }
        for failure_class, recovery_action in expected_actions.items():
            with self.subTest(failure_class=failure_class), tempfile.TemporaryDirectory() as directory:
                repo = Path(directory)
                self.state = GOAL.initial_runner_state(self.spec, now=NOW.isoformat())
                event_id = f"recover-{failure_class.lower().replace('_', '-')}"
                self.write_order(repo, self.state, event_id=event_id, stage="codex")
                state_path, ledger_path = self.write_state_and_ledger(repo, self.state)
                active = ADAPTER.reconcile_owner_authority(
                    self.spec, self.state, self.authority,
                    state_path=state_path, ledger_path=ledger_path,
                )["state"]
                action = ADAPTER.next_action(
                    self.spec, active, GOAL.read_ledger(ledger_path), self.authority,
                    now=NOW, trial=False,
                )
                reserved, _, attempt_id = self.reserve_model(
                    repo, active, action, state_path=state_path,
                    ledger_path=ledger_path,
                )
                order = json.loads((repo / "output" / f"{event_id}.json").read_text())
                checkpoint = {
                    "schema_version": "kgnote.linux-worker-route.v1",
                    "status": "FAILED_CLOSED", "reason": "guest_worker_failed",
                    "event_id": order["event_id"],
                    "command_digest": ROUTER.command_digest(ROUTER.WorkerOrder.from_dict(order)),
                    "execution_evidence": {"failure_class": failure_class},
                }
                Path(order["checkpoint_path"]).write_text(json.dumps(checkpoint), encoding="utf-8")
                routed = ADAPTER.record_route_outcome(
                    self.spec, reserved, state_path=state_path,
                    work_item_id=action["work_item_id"], attempt_id=attempt_id,
                    route_exit_code=2, occurred_at=NOW.isoformat(),
                )
                ADAPTER.reconcile_dispatch_checkpoint(
                    self.spec, routed, state_path=state_path, ledger_path=ledger_path,
                    repo=repo, attempt_id=attempt_id, occurred_at=NOW.isoformat(),
                )
                blocked = GOAL.load_json(state_path)
                recovery = ADAPTER.next_action(
                    self.spec, blocked, GOAL.read_ledger(ledger_path), self.authority,
                    now=NOW, trial=False,
                )
                self.assertEqual("RECOVERY_READY", recovery["status"])
                self.assertEqual(recovery_action, recovery["action"])
                released = ADAPTER.resume_recoverable_runtime_block(
                    self.spec, blocked, state_path=state_path, ledger_path=ledger_path,
                    now=NOW,
                )
                self.assertEqual("RECOVERABLE_RUNTIME_BLOCK_RELEASED", released["status"])
                recovered = GOAL.load_json(state_path)
                self.assertNotIn("runtime_block", recovered)
                replanned = ADAPTER.next_action(
                    self.spec, recovered, GOAL.read_ledger(ledger_path), self.authority,
                    now=NOW + ADAPTER.timedelta(seconds=301), trial=False,
                )
                self.assertEqual("ACTION_READY", replanned["status"])
                operations = [
                    row["payload"].get("operation")
                    for row in GOAL.read_ledger(ledger_path)
                ]
                self.assertEqual(1, operations.count("RECOVERABLE_RUNTIME_BLOCK_RELEASED"))

    def test_work_window_failure_releases_only_in_a_later_authorized_window(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            self.write_order(repo, self.state, event_id="window-deadline", stage="codex")
            state_path, ledger_path = self.write_state_and_ledger(repo, self.state)
            active = ADAPTER.reconcile_owner_authority(
                self.spec, self.state, self.authority,
                state_path=state_path, ledger_path=ledger_path,
            )["state"]
            action = ADAPTER.next_action(
                self.spec, active, GOAL.read_ledger(ledger_path), self.authority,
                now=NOW, trial=False,
            )
            reserved, _, attempt_id = self.reserve_model(
                repo, active, action, state_path=state_path, ledger_path=ledger_path,
            )
            order = json.loads((repo / "output" / "window-deadline.json").read_text())
            checkpoint = {
                "schema_version": "kgnote.linux-worker-route.v1",
                "status": "DEADLINE_STOPPED", "reason": "work_window_deadline",
                "event_id": order["event_id"],
                "command_digest": ROUTER.command_digest(ROUTER.WorkerOrder.from_dict(order)),
            }
            Path(order["checkpoint_path"]).write_text(json.dumps(checkpoint), encoding="utf-8")
            routed = ADAPTER.record_route_outcome(
                self.spec, reserved, state_path=state_path,
                work_item_id=action["work_item_id"], attempt_id=attempt_id,
                route_exit_code=2, occurred_at=NOW.isoformat(),
            )
            ADAPTER.reconcile_dispatch_checkpoint(
                self.spec, routed, state_path=state_path, ledger_path=ledger_path,
                repo=repo, attempt_id=attempt_id, occurred_at=NOW.isoformat(),
            )
            blocked = GOAL.load_json(state_path)
            next_morning = datetime(2026, 10, 23, 8, 0, tzinfo=ZoneInfo("Asia/Taipei"))
            self.assertEqual(
                "WAIT_WORK_WINDOW",
                ADAPTER.next_action(
                    self.spec, blocked, GOAL.read_ledger(ledger_path), self.authority,
                    now=next_morning, trial=False,
                )["status"],
            )
            reopened = datetime(2026, 10, 23, 10, 0, tzinfo=ZoneInfo("Asia/Taipei"))
            ready = ADAPTER.next_action(
                self.spec, blocked, GOAL.read_ledger(ledger_path), self.authority,
                now=reopened, trial=False,
            )
            self.assertEqual("RESUME_AFTER_WORK_WINDOW", ready["action"])
            resumed = ADAPTER.resume_recoverable_runtime_block(
                self.spec, blocked, state_path=state_path, ledger_path=ledger_path,
                now=reopened,
            )
            self.assertEqual("RECOVERABLE_RUNTIME_BLOCK_RELEASED", resumed["status"])
            self.assertEqual("RESUME_AFTER_WORK_WINDOW", resumed["recovery_action"])

    def test_unknown_checkpoint_remains_unreconciled_and_probe_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            self.write_order(repo, self.state, event_id="unknown-outcome", stage="codex")
            state_path, ledger_path = self.write_state_and_ledger(repo, self.state)
            active = ADAPTER.reconcile_owner_authority(
                self.spec, self.state, self.authority,
                state_path=state_path, ledger_path=ledger_path,
            )["state"]
            action = ADAPTER.next_action(
                self.spec, active, GOAL.read_ledger(ledger_path), self.authority,
                now=NOW, trial=False,
            )
            reserved, _, attempt_id = self.reserve_model(
                repo, active, action, state_path=state_path, ledger_path=ledger_path,
            )
            order = json.loads((repo / "output" / "unknown-outcome.json").read_text())
            checkpoint = {
                "schema_version": "kgnote.linux-worker-route.v1",
                "status": "FAILED_CLOSED", "reason": "controller_interrupted",
                "event_id": order["event_id"],
                "command_digest": ROUTER.command_digest(ROUTER.WorkerOrder.from_dict(order)),
            }
            Path(order["checkpoint_path"]).write_text(json.dumps(checkpoint), encoding="utf-8")
            routed = ADAPTER.record_route_outcome(
                self.spec, reserved, state_path=state_path,
                work_item_id=action["work_item_id"], attempt_id=attempt_id,
                route_exit_code=2, occurred_at=NOW.isoformat(),
            )
            first = ADAPTER.reconcile_dispatch_checkpoint(
                self.spec, routed, state_path=state_path, ledger_path=ledger_path,
                repo=repo, attempt_id=attempt_id, occurred_at=NOW.isoformat(),
            )
            self.assertEqual("CHECKPOINT_UNRESOLVED", first["status"])
            before = ledger_path.read_bytes()
            current = GOAL.load_json(state_path)
            second = ADAPTER.reconcile_dispatch_checkpoint(
                self.spec, current, state_path=state_path, ledger_path=ledger_path,
                repo=repo, attempt_id=attempt_id, occurred_at=(NOW + ADAPTER.timedelta(minutes=1)).isoformat(),
            )
            self.assertEqual("CHECKPOINT_UNRESOLVED", second["status"])
            self.assertEqual(before, ledger_path.read_bytes())
            projection = GOAL.reduce_ledger(GOAL.read_ledger(ledger_path))
            self.assertFalse(projection["dispatch_reservations"][attempt_id].get("reconciled", False))
            self.assertFalse(projection["model_attempts"][attempt_id].get("finished", False))

    def test_window_budget_resets_but_goal_total_is_ledger_bound(self):
        ledger = self.activate()
        for index in range(3):
            self.append(
                ledger, f"claude-day-one-{index}", "MODEL_ATTEMPT_STARTED",
                {"provider": "claude"}, f"claude-day-one-{index}",
            )
        # Select the review lane directly so this test exercises Claude's
        # independent provider budget rather than the preceding implementation.
        self.state["work_items"][0]["status"] = "VERIFIED"
        self.state["work_items"][1]["status"] = "READY"
        next_window = ADAPTER.next_action(
            self.spec, self.state, ledger, self.authority,
            now=NOW + ADAPTER.timedelta(days=1), trial=False,
        )
        self.assertEqual("ACTION_READY", next_window["status"])
        self.assertEqual(0, next_window["launches_in_window_before"])
        self.assertEqual(3, next_window["total_launches_before"])

        for index in range(3, 12):
            self.append(
                ledger, f"claude-total-{index}", "MODEL_ATTEMPT_STARTED",
                {"provider": "claude"}, f"claude-total-{index}",
            )
        # Editing the mutable convenience counters cannot reset the immutable
        # Goal-version ceiling reconstructed from the ledger.
        self.state["resource_accounting"] = {
            "claude": {"launches_in_window": 0, "total_launches": 0}
        }
        exhausted = ADAPTER.next_action(
            self.spec, self.state, ledger, self.authority,
            now=NOW + ADAPTER.timedelta(days=4), trial=False,
        )
        self.assertEqual("WAIT_GOAL_RESOURCE_LIMIT", exhausted["status"])
        self.assertEqual(12, exhausted["total_launches"])


if __name__ == "__main__":
    unittest.main()
