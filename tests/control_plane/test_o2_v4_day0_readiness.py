from __future__ import annotations

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

import github_product_goal_control as CONTROL
import goal_continuity as GOAL
import goal_runner_adapter as ADAPTER
import product_goal_worker_identity as IDENTITY
from tests.control_plane.runtime_admission_fixtures import (
    activation_dependency_receipts,
    product_goal_spec,
    runtime_identity,
    write_reservation_receipt,
)
from tests.control_plane.test_github_product_goal_control import comment


NOW = datetime(2026, 10, 30, 10, 0, tzinfo=ZoneInfo("Asia/Taipei"))


class O2V4Day0ReadinessTest(unittest.TestCase):
    def setUp(self):
        self.spec = product_goal_spec()

    def activated_fixture(self, root: Path):
        state_path = root / "state.json"
        ledger_path = root / "ledger.jsonl"
        state = GOAL.initial_runner_state(
            self.spec,
            now="2026-10-29T16:00:00+08:00",
            dependency_receipts=activation_dependency_receipts(self.spec),
        )
        GOAL.atomic_write_json(state_path, state)
        approval = comment(self.spec, login="joannalee20050914")
        approval["html_url"] = (
            "https://github.com/joannalee20050914/KGnote-public/"
            "issues/9#issuecomment-100"
        )
        approval["issue_url"] = (
            "https://api.github.com/repos/joannalee20050914/"
            "KGnote-public/issues/9"
        )
        authority = CONTROL.resolve_authority([approval], self.spec)
        state = ADAPTER.reconcile_owner_authority(
            self.spec, state, authority,
            state_path=state_path, ledger_path=ledger_path,
            observed_at=datetime(2026, 10, 29, 16, 0, tzinfo=ZoneInfo("Asia/Taipei")),
        )["state"]
        state["candidate_identity"] = deepcopy(
            self.spec["history_carryover"]["candidate_identity"]
        )
        GOAL.atomic_write_json(state_path, state)
        return state, authority, state_path, ledger_path

    def prepared_order(self, root: Path):
        state, authority, state_path, ledger_path = self.activated_fixture(root)
        action = ADAPTER.next_action(
            self.spec, state, GOAL.read_ledger(ledger_path), authority,
            now=NOW, trial=False,
        )
        self.assertEqual("ACTION_READY", action["status"])
        self.assertEqual(3, action["total_launches_before"])
        bound, order_path, order, attempt_id = ADAPTER.ensure_bound_order(
            self.spec, state, action, repo=root, state_path=state_path,
            ledger_path=ledger_path, occurred_at=NOW.isoformat(),
            runtime_identity=runtime_identity(), persist_binding=False,
        )
        receipt_path = write_reservation_receipt(
            root, order_path, observed_at=NOW,
        )
        return (
            bound, authority, state_path, ledger_path, action,
            order_path, order, attempt_id, receipt_path,
        )

    def test_exact_spec_identity_carryover_and_worker_context_are_bound(self):
        GOAL.validate_goal_spec(self.spec)
        GOAL.validate_history_carryover_evidence(
            self.spec, repository_root=ROOT,
        )
        self.assertEqual(IDENTITY.PRODUCT_GOAL_VERSION, self.spec["goal_version"])
        self.assertEqual(
            IDENTITY.PRODUCT_GOAL_SPEC_SHA256,
            GOAL.goal_spec_sha256(self.spec),
        )
        carryover = self.spec["history_carryover"]
        self.assertEqual(3, GOAL.carried_provider_charges(self.spec, "codex"))
        self.assertEqual(2, carryover["actual_model_processes"]["codex"])
        self.assertEqual(5, self.spec["resource_policy"]["providers"]["codex"]["fallback"]["max_total_launches"])
        schedule = self.spec["trial_schedule"]
        self.assertEqual("2026-10-29", schedule["day_zero_date"])
        self.assertFalse(schedule["day_zero_counts_as_full_observation_day"])
        self.assertEqual(
            "COUNTS_AGAINST_PROVIDER_CEILINGS",
            schedule["day_zero_model_usage_accounting"],
        )
        self.assertEqual(
            ["2026-10-30", "2026-11-02", "2026-11-03", "2026-11-04", "2026-11-05"],
            schedule["observation_work_dates"],
        )
        self.assertEqual(10, len(schedule["goal_work_dates"]))
        self.assertEqual("2026-11-11", schedule["goal_work_dates"][-1])
        self.assertEqual(10, schedule["hard_stop_goal_workday_ordinal"])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (
                _state, _authority, _state_path, _ledger_path, _action,
                _order_path, order, _attempt_id, receipt_path,
            ) = self.prepared_order(root)
            identity = IDENTITY.validate_product_goal_identity(
                order["bootstrap_identity"], event_id=order["event_id"],
                stage=order["stage"],
                working_directory=Path(order["working_directory"]),
                worktree_root=Path("/home/kgnote/.local/share/kgnote"),
            )
            context = IDENTITY.validate_product_goal_runtime_context(
                order["execution_context"], identity=identity,
            )
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            self.assertEqual(context["goal_version"], receipt["goal_version"])
            self.assertEqual(
                context["runtime_identity"]["generation_id"],
                receipt["runtime_identity"]["generation_id"],
            )
            self.assertFalse(receipt["model_process_started"])
            self.assertEqual(0, receipt["model_launches"])

    def test_wrong_version_and_wrong_digest_cannot_fall_back_to_legacy_dispatch(self):
        for provider in ("codex", "claude"):
            self.assertTrue(ADAPTER.requires_runtime_admission(
                self.spec, {"requires_model": True, "provider": provider},
            ))
        action = {"requires_model": True, "provider": "claude"}
        wrong_version = deepcopy(self.spec)
        wrong_version["goal_version"] = "2026-10-29.4-wrong"
        with self.assertRaisesRegex(ADAPTER.GoalRunnerError, "exact supported version and digest"):
            ADAPTER.requires_runtime_admission(wrong_version, action)

        wrong_digest = deepcopy(self.spec)
        wrong_digest["trial_schedule"]["late_activation_rule"] += " changed"
        self.assertNotEqual(
            GOAL.goal_spec_sha256(self.spec), GOAL.goal_spec_sha256(wrong_digest),
        )
        with self.assertRaisesRegex(ADAPTER.GoalRunnerError, "exact supported version and digest"):
            ADAPTER.requires_runtime_admission(wrong_digest, action)

    def test_wrong_checkout_and_stale_receipt_fail_before_reservation_bytes_change(self):
        for failure in ("wrong_checkout", "wrong_runtime", "stale"):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (
                    state, _authority, state_path, ledger_path, action,
                    order_path, _order, _attempt_id, receipt_path,
                ) = self.prepared_order(root)
                receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
                if failure == "wrong_checkout":
                    receipt["candidate"]["commit"] = "f" * 40
                elif failure == "wrong_runtime":
                    receipt["runtime_identity"]["generation_id"] = "f" * 40
                else:
                    receipt["issued_at"] = "2026-10-30T09:00:00+08:00"
                    receipt["expires_at"] = "2026-10-30T09:02:00+08:00"
                receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
                before_state = hashlib.sha256(state_path.read_bytes()).hexdigest()
                before_ledger = hashlib.sha256(ledger_path.read_bytes()).hexdigest()
                with self.assertRaises(ADAPTER.GoalRunnerError):
                    ADAPTER.reserve_dispatch(
                        self.spec, state, action,
                        state_path=state_path, ledger_path=ledger_path, repo=root,
                        occurred_at=NOW.isoformat(),
                        prepared_order_path=order_path,
                        admission_receipt_path=receipt_path,
                    )
                self.assertEqual(
                    before_state, hashlib.sha256(state_path.read_bytes()).hexdigest(),
                )
                self.assertEqual(
                    before_ledger, hashlib.sha256(ledger_path.read_bytes()).hexdigest(),
                )

    def test_late_owner_approval_or_late_dependency_keeps_goal_paused(self):
        cases = ("late_approval", "late_dependency", "late_reconciliation")
        for case in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                verified_at = (
                    "2026-10-29T17:00:00+08:00"
                    if case == "late_dependency"
                    else "2026-10-29T16:00:00+08:00"
                )
                state = GOAL.initial_runner_state(
                    self.spec, now="2026-10-29T16:00:00+08:00",
                    dependency_receipts=activation_dependency_receipts(
                        self.spec, verified_at=verified_at,
                    ),
                )
                state_path, ledger_path = root / "state.json", root / "ledger.jsonl"
                GOAL.atomic_write_json(state_path, state)
                approval = comment(self.spec, login="joannalee20050914")
                if case == "late_approval":
                    approval["created_at"] = "2026-10-29T09:00:00Z"
                approval["html_url"] = (
                    "https://github.com/joannalee20050914/KGnote-public/"
                    "issues/9#issuecomment-100"
                )
                approval["issue_url"] = (
                    "https://api.github.com/repos/joannalee20050914/"
                    "KGnote-public/issues/9"
                )
                authority = CONTROL.resolve_authority([approval], self.spec)
                result = ADAPTER.reconcile_owner_authority(
                    self.spec, state, authority,
                    state_path=state_path, ledger_path=ledger_path,
                    observed_at=(
                        datetime(2026, 10, 29, 17, 0, tzinfo=ZoneInfo("Asia/Taipei"))
                        if case == "late_reconciliation"
                        else datetime(2026, 10, 29, 16, 0, tzinfo=ZoneInfo("Asia/Taipei"))
                    ),
                )
                self.assertEqual("APPROVAL_REQUIRED", result["state"]["lifecycle"]["state"])
                self.assertEqual("PAUSED", result["state"]["authority_lease"])
                self.assertFalse(result["state"]["go_live_authorized"])
                self.assertIn("TRIAL_ACTIVATION_MISSED", result["rejected_transitions"][0]["reason"])
                projection = GOAL.reduce_ledger(GOAL.read_ledger(ledger_path))
                self.assertEqual({}, projection["dispatch_reservations"])
                self.assertEqual({}, projection["model_attempts"])

    def test_day_zero_codex_attempts_count_and_exhaust_cross_version_ceiling(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state, authority, _state_path, ledger_path = self.activated_fixture(root)
            for index, occurred_at in enumerate(
                ("2026-10-29T17:10:00+08:00", "2026-10-29T17:20:00+08:00"),
                start=1,
            ):
                GOAL.append_ledger_event(
                    ledger_path,
                    event_id=f"isolated-new-version-model-attempt-{index}",
                    event_type="MODEL_ATTEMPT_STARTED",
                    occurred_at=occurred_at,
                    goal_id=self.spec["goal_id"],
                    goal_version=self.spec["goal_version"],
                    logical_work_id="WI-O2-A-IMPLEMENT",
                    attempt_id=f"isolated-attempt-{index}",
                    payload={"provider": "codex", "operation": "ISOLATED_TEST_EVIDENCE"},
                )
            decision = ADAPTER.next_action(
                self.spec, state, GOAL.read_ledger(ledger_path), authority,
                now=NOW, trial=False,
            )
            self.assertEqual("WAIT_GOAL_RESOURCE_LIMIT", decision["status"])
            self.assertEqual(5, decision["total_launches"])
            self.assertEqual(5, decision["max_total_launches"])


if __name__ == "__main__":
    unittest.main()
