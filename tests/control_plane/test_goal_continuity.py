from __future__ import annotations

import importlib.util
import json
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location(
    "goal_continuity", ROOT / "scripts/goal_continuity.py"
)
GOAL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GOAL)


def product_goal_spec() -> dict:
    return {
        "schema_version": "kgnote.product-goal-spec.v1",
        "identity_kind": "KGNOTE_PRODUCT_GOAL",
        "authority_kind": "GITHUB_OWNER_APPROVAL",
        "lifecycle_owner": "MAC_RUNNER",
        "goal_id": "GOAL-KGNOTE-O2-CONTINUATION",
        "active_goal": "Complete O2 without substituting adjacent features",
        "goal_version": "2026-10-22.1",
        "title": "O2 completion",
        "outcome": "Close the stable Product Goal obligations with exact evidence.",
        "repository": "owner/repo",
        "github_issue": 42,
        "owner_logins": ["owner"],
        "requirements": ["KG-GOV-04"],
        "rcs": ["RC-27"],
        "fds": ["FD-12"],
        "dependencies": [],
        "allowed_operations": ["activate_runner", "commit", "push", "draft_pr", "review"],
        "forbidden_operations": ["merge", "paid_api", "delete_evidence"],
        "work_window": {
            "timezone": "Asia/Taipei", "weekdays": [0, 1, 2, 3, 4],
            "start": "09:00", "end": "18:00",
        },
        "resource_policy": {
            "max_model_concurrency": 1,
            "providers": {
                name: {
                    "subscription_only": True,
                    "paid_api_fallback": False,
                    "reserve_percent": 10,
                    "capacity_observation": {
                        "status": "PERCENTAGE_UNOBSERVABLE",
                        "remaining_percent": None,
                        "source_kind": None,
                        "observed_at": None,
                        "max_age_seconds": 300,
                    },
                    "fallback": {
                        "min_launch_interval_seconds": 300,
                        "max_launches_per_window": 3,
                        "quota_backoff_seconds": 3600,
                    },
                }
                for name in ("codex", "claude")
            },
        },
        "recovery_policy": {
            "max_same_failure_attempts": 3,
            "no_progress_before_strategy_adjustment": 2,
            "max_strategy_adjustments": 3,
        },
        "review_policy": {
            "reviewer": "UBUNTU_CLAUDE", "independent": True,
            "completion_gate_required": True, "round_has_hidden_fixed_limit": False,
        },
        "completion_conditions": ["all obligations VERIFIED_RESOLVED"],
        "human_acceptance_required": True,
        "obligations": [{
            "obligation_id": "OBL-O2-CORE",
            "semantic_key": "a" * 64,
            "authority_refs": ["KG-GOV-04", "RC-27", "FD-12"],
            "description": "Complete the stable O2 obligation.",
        }],
        "work_items": [{
            "work_item_id": "WI-O2-IMPLEMENT",
            "milestone_id": "O2-M1",
            "kind": "IMPLEMENT",
            "dependencies": [],
            "obligation_ids": ["OBL-O2-CORE"],
            "allowed_operations": ["commit", "push", "draft_pr"],
            "provider": "codex",
        }],
    }


class GoalContinuityTests(unittest.TestCase):
    def setUp(self):
        self.spec = product_goal_spec()
        GOAL.validate_goal_spec(self.spec)

    def event(self, existing, event_id, event_type, payload, attempt_id=None):
        return GOAL.prepare_ledger_event(
            existing,
            event_id=event_id,
            event_type=event_type,
            occurred_at="2026-10-22T10:00:00+08:00",
            goal_id=self.spec["goal_id"],
            goal_version=self.spec["goal_version"],
            logical_work_id="WI-O2-IMPLEMENT",
            attempt_id=attempt_id,
            payload=payload,
        )

    def test_app_goal_is_provenance_not_product_authority(self):
        state = GOAL.initial_runner_state(
            self.spec,
            now="2026-10-22T10:00:00+08:00",
            codex_app_goal_provenance={
                "goal_id": "CODEX-APP-GOAL-B-CONTINUOUS-DELEGATION-20261022",
                "status": "active", "budget_status": "available",
            },
        )
        self.assertEqual(self.spec["goal_id"], state["goal_id"])
        self.assertEqual(self.spec["active_goal"], state["active_goal"])
        self.assertEqual("O2-M1", state["milestone_id"])
        self.assertEqual("APPROVAL_REQUIRED", state["lifecycle"]["state"])
        self.assertEqual("PAUSED", state["authority_lease"])
        self.assertIsNone(state["authority_record"])
        self.assertFalse(state["go_live_authorized"])
        GOAL.validate_runner_state(state, self.spec)

    def test_hash_chain_detects_mutation_and_append_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ledger.jsonl"
            fields = dict(
                event_id="attempt-1-start",
                event_type="MODEL_ATTEMPT_STARTED",
                occurred_at="2026-10-22T10:00:00+08:00",
                goal_id=self.spec["goal_id"], goal_version=self.spec["goal_version"],
                logical_work_id="WI-O2-IMPLEMENT", attempt_id="attempt-1",
                payload={"provider": "claude"},
            )
            first, appended = GOAL.append_ledger_event(path, **fields)
            replay, appended_again = GOAL.append_ledger_event(path, **fields)
            self.assertTrue(appended)
            self.assertFalse(appended_again)
            self.assertEqual(first, replay)
            changed = dict(fields)
            changed["payload"] = {"provider": "codex"}
            with self.assertRaisesRegex(GOAL.GoalContractError, "changed payload"):
                GOAL.append_ledger_event(path, **changed)
            value = json.loads(path.read_text().strip())
            value["payload"] = {"provider": "tampered"}
            path.write_text(json.dumps(value) + "\n")
            with self.assertRaisesRegex(GOAL.GoalContractError, "digest mismatch"):
                GOAL.read_ledger(path)

    def test_concurrent_appends_remain_a_single_valid_chain(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ledger.jsonl"

            def append(index):
                return GOAL.append_ledger_event(
                    path,
                    event_id=f"event-{index}",
                    event_type="WORK_STATE_TRANSITION",
                    occurred_at="2026-10-22T10:00:00+08:00",
                    goal_id=self.spec["goal_id"],
                    goal_version=self.spec["goal_version"],
                    logical_work_id="WI-O2-IMPLEMENT",
                    attempt_id=None,
                    payload={"index": index},
                )

            with ThreadPoolExecutor(max_workers=8) as pool:
                results = list(pool.map(append, range(32)))
            self.assertTrue(all(appended for _, appended in results))
            events = GOAL.read_ledger(path)
            self.assertEqual(32, len(events))
            self.assertEqual(list(range(1, 33)), [row["sequence"] for row in events])

    def test_429_zero_tokens_no_verdict_is_attempt_not_review(self):
        events = []
        events.append(self.event(events, "a-start", "MODEL_ATTEMPT_STARTED", {"provider": "claude"}, "a"))
        events.append(self.event(events, "a-finish", "MODEL_ATTEMPT_FINISHED", {
            "outcome": "QUOTA_EXHAUSTED", "exit_code": 1,
        }, "a"))
        events.append(self.event(events, "a-usage", "USAGE_OBSERVED", {
            "input_tokens": 0, "output_tokens": 0, "source": "provider_checkpoint",
        }, "a"))
        projection = GOAL.reduce_ledger(events)
        self.assertEqual(1, len(projection["model_attempts"]))
        self.assertEqual(0, len(projection["review_verdicts"]))
        self.assertEqual(0, projection["usage"]["a"]["input_tokens"])

    def test_verdict_survives_later_publication_failure(self):
        events = []
        events.append(self.event(events, "verdict", "REVIEW_VERDICT_ACCEPTED", {
            "verdict": "CHANGES_REQUIRED", "review_id": "round-4",
        }, "review-4"))
        events.append(self.event(events, "publish", "RESULT_PUBLICATION_RECORDED", {
            "status": "FAILED", "reason": "writeback unavailable",
        }, None))
        projection = GOAL.reduce_ledger(events)
        self.assertEqual("CHANGES_REQUIRED", projection["review_verdicts"][0]["verdict"])
        self.assertEqual("FAILED", projection["publications"]["WI-O2-IMPLEMENT"]["status"])
        self.assertEqual(1, len(projection["review_verdicts"]))

    def test_unobservable_percentage_uses_bounded_fallback(self):
        policy = self.spec["resource_policy"]["providers"]["claude"]
        now = datetime(2026, 10, 22, 10, tzinfo=timezone.utc)
        decision = GOAL.capacity_decision(
            policy, now=now, last_launch_at=now - timedelta(seconds=100),
            launches_in_window=0,
        )
        self.assertEqual("WAIT_LAUNCH_INTERVAL", decision["status"])
        decision = GOAL.capacity_decision(
            policy, now=now, last_launch_at=now - timedelta(seconds=400),
            launches_in_window=0,
        )
        self.assertEqual("PERCENTAGE_UNOBSERVABLE_FALLBACK", decision["basis"])

    def test_trusted_percentage_requires_source_time_and_fresh_observation(self):
        policy = deepcopy(self.spec["resource_policy"]["providers"]["claude"])
        now = datetime(2026, 10, 22, 10, tzinfo=timezone.utc)
        policy["capacity_observation"] = {
            "status": "TRUSTED", "remaining_percent": 9,
            "source_kind": "provider-account-ui-readback",
            "observed_at": now.isoformat(), "max_age_seconds": 300,
        }
        decision = GOAL.capacity_decision(
            policy, now=now, last_launch_at=None, launches_in_window=0,
        )
        self.assertEqual("WAIT_RESERVE", decision["status"])
        policy["capacity_observation"]["observed_at"] = (
            now + timedelta(seconds=1)
        ).isoformat()
        with self.assertRaisesRegex(GOAL.GoalContractError, "future"):
            GOAL.capacity_decision(
                policy, now=now, last_launch_at=None, launches_in_window=0,
            )

    def test_two_no_progress_events_require_strategy_change(self):
        first = GOAL.progress_transition(None, "NO_OBLIGATION_PROGRESS")
        second = GOAL.progress_transition(
            first["consecutive_no_progress"], "EVIDENCE_INSUFFICIENT"
        )
        self.assertFalse(first["strategy_adjustment_required"])
        self.assertTrue(second["strategy_adjustment_required"])


if __name__ == "__main__":
    unittest.main()
