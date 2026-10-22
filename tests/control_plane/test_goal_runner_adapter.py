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
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from tests.control_plane.test_goal_continuity import product_goal_spec
from tests.control_plane.test_github_product_goal_control import comment

SPEC = importlib.util.spec_from_file_location(
    "goal_runner_adapter", ROOT / "scripts/goal_runner_adapter.py"
)
ADAPTER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ADAPTER)
import github_product_goal_control as CONTROL
import goal_continuity as GOAL


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
        self.assertEqual("ACTION_READY", result["status"])
        self.assertEqual("DISPATCH_REPAIR", result["action"])
        self.assertEqual("PERCENTAGE_UNOBSERVABLE_FALLBACK", result["capacity_basis"])

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
        self.spec["work_items"].append(second_spec)
        self.state = GOAL.initial_runner_state(self.spec, now=NOW.isoformat())
        self.authority = CONTROL.resolve_authority(
            [comment(self.spec, action="APPROVE")], self.spec
        )
        ledger = self.activate()
        self.state["work_items"][0]["status"] = "BLOCKED"
        self.state["work_items"][1]["status"] = "VERIFY_REQUIRED"
        result = ADAPTER.next_action(
            self.spec, self.state, ledger, self.authority, now=NOW, trial=False,
        )
        self.assertEqual("WI-O2-INDEPENDENT", result["work_item_id"])
        self.assertEqual("RUN_DETERMINISTIC_VERIFICATION", result["action"])
        self.assertFalse(result["requires_model"])

    def test_two_no_progress_cycles_adjust_then_block_affected_work(self):
        for _ in range(6):
            self.state = ADAPTER.apply_obligation_progress(
                self.state, self.spec, work_item_id="WI-O2-IMPLEMENT",
                obligation_id="OBL-O2-CORE", progress_class="NO_OBLIGATION_PROGRESS",
            )
        self.assertEqual(3, self.state["work_items"][0]["strategy_adjustments"])
        self.assertEqual("BLOCKED", self.state["work_items"][0]["status"])

    def test_durable_reservation_forces_reconciliation_before_redispatch(self):
        ledger = self.activate()
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            order_path = repo / "output" / "sealed-order.json"
            order_path.parent.mkdir(parents=True)
            order = {
                "schema_version": "kgnote.linux-worker-order.v1",
                "event_id": "o2-codex-attempt-1",
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
            reserved, selected_order, attempt_id = ADAPTER.reserve_dispatch(
                self.spec, self.state, action, state_path=state_path,
                ledger_path=ledger_path, repo=repo, occurred_at=NOW.isoformat(),
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


if __name__ == "__main__":
    unittest.main()
