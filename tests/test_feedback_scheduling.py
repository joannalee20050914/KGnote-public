from __future__ import annotations

import copy
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import json
from jsonschema import Draft202012Validator, FormatChecker

from kgnote.review import append_feedback, act_on_due, due_exposure_signal, due_identity, list_attempts, list_due, milestone_due_at, save_attempt, schedule_after_feedback
from tests.test_attempt_store import request as attempt_request


def feedback(attempt_id: str, *, assessment_id: str = "assessment_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa") -> dict:
    return {
        "schema_version": "kgnote.attempt-feedback-request.v1", "assessment_id": assessment_id,
        "attempt_id": attempt_id, "outcome": "PARTIAL", "disagrees": False, "correction": None,
        "occurred_at": "2026-09-20T01:03:00Z",
    }


class FeedbackSchedulingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.attempt = attempt_request(state="submitted", response="我先這樣理解")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_feedback_is_append_only_idempotent_and_requires_correction_for_dispute(self) -> None:
        first = append_feedback(self.root, feedback(self.attempt["attempt_id"]), self.attempt)
        self.assertEqual(first.status, "recorded")
        self.assertEqual(append_feedback(self.root, feedback(self.attempt["attempt_id"]), self.attempt).status, "unchanged")
        disputed = feedback(self.attempt["attempt_id"], assessment_id="assessment_bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb")
        disputed.update(disagrees=True, correction="")
        self.assertEqual(append_feedback(self.root, disputed, self.attempt).problem_code, "missing_correction")

    def test_calendar_milestones_and_actions_do_not_create_attempts(self) -> None:
        self.assertEqual(milestone_due_at("2026-09-20T23:30:00+08:00", 0), "2026-09-21T15:30:00Z")
        event = append_feedback(self.root, feedback(self.attempt["attempt_id"]), self.attempt).payload["event"]
        scheduled = schedule_after_feedback(self.root, self.attempt, event)
        due = scheduled.payload["due"]
        self.assertEqual(due["milestone_index"], 0)
        action = {
            "schema_version": "kgnote.due-action.v1", "action_id": "action_snooze_1", "due_id": due["due_id"],
            "action": "snooze", "occurred_at": "2026-09-21T15:31:00Z", "snooze_until": "2026-09-22T03:00:00Z",
        }
        self.assertEqual(act_on_due(self.root, action).status, "saved")
        self.assertFalse((self.root / "attempts").exists())
        listed = list_due(self.root, now="2026-09-22T04:00:00Z").payload["items"]
        self.assertEqual(listed[0]["category"], "due_now")

    def test_voluntary_retry_does_not_advance_but_matching_scheduled_attempt_does(self) -> None:
        event = feedback(self.attempt["attempt_id"])
        first = schedule_after_feedback(self.root, self.attempt, event).payload["due"]
        voluntary = copy.deepcopy(self.attempt)
        voluntary["attempt_id"] = "attempt_bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
        self.assertEqual(schedule_after_feedback(self.root, voluntary, event).payload["due"]["milestone_index"], 0)
        scheduled = copy.deepcopy(self.attempt)
        scheduled["attempt_id"] = "attempt_cccccccccccccccccccccccccccccccc"
        scheduled["entry_context"] = {"route": "/practice.html", "from_route": "/review.html", "entry_kind": "scheduled_review", "due_id": first["due_id"]}
        advanced = schedule_after_feedback(self.root, scheduled, event).payload["due"]
        self.assertEqual(advanced["milestone_index"], 1)
        self.assertEqual(first["due_id"], due_identity(self.attempt["learning_unit_id"], self.attempt["review_item_id"]))

    def test_feedback_and_due_action_schemas_accept_runtime_requests(self) -> None:
        repository = Path(__file__).resolve().parents[1]
        pairs = [
            ("schemas/attempt-feedback/v1/save-request.schema.json", feedback(self.attempt["attempt_id"])),
            ("schemas/due/v1/action-request.schema.json", {"schema_version": "kgnote.due-action.v1", "action_id": "action_1", "due_id": due_identity(self.attempt["learning_unit_id"], self.attempt["review_item_id"]), "action": "stop", "occurred_at": "2026-09-20T01:00:00Z", "snooze_until": None}),
        ]
        for relative, value in pairs:
            schema = json.loads((repository / relative).read_text()); Draft202012Validator.check_schema(schema)
            self.assertEqual(list(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(value)), [])

    def test_due_path_traversal_and_corrupted_record_fail_safely(self) -> None:
        self.assertEqual(save_attempt(self.root, self.attempt).status, "saved")
        unsafe = {"schema_version": "kgnote.due-action.v1", "action_id": "action_safe", "due_id": "../../outside", "action": "stop", "occurred_at": "2026-09-20T01:00:00Z", "snooze_until": None}
        self.assertEqual(act_on_due(self.root, unsafe).problem_code, "invalid_due_action_identity")
        directory = self.root / "due-items"; directory.mkdir(); (directory / f"{due_identity('unit', 'item')}.json").write_text("not-json")
        self.assertEqual(list_due(self.root, now="2026-09-20T01:00:00Z").problem_code, "corrupted_due_item")
        self.assertEqual(len(list_attempts(self.root, self.attempt["learning_unit_id"]).payload["attempts"]), 1)

    def test_concurrent_feedback_appends_and_due_actions_do_not_lose_events(self) -> None:
        requests = [feedback(self.attempt["attempt_id"], assessment_id=f"assessment_{index:032x}") for index in range(12)]
        with ThreadPoolExecutor(max_workers=12) as pool:
            statuses = list(pool.map(lambda value: append_feedback(self.root, value, self.attempt).status, requests))
        self.assertEqual(statuses, ["recorded"] * 12)
        from kgnote.review import read_feedback
        self.assertEqual(len(read_feedback(self.root, self.attempt["attempt_id"]).payload["events"]), 12)
        due = schedule_after_feedback(self.root, self.attempt, requests[0]).payload["due"]
        actions = [{"schema_version":"kgnote.due-action.v1","action_id":f"action_snooze_{index}","due_id":due["due_id"],"action":"snooze","occurred_at":"2026-09-21T01:00:00Z","snooze_until":f"2026-09-22T{index:02d}:00:00Z"} for index in range(12)]
        with ThreadPoolExecutor(max_workers=12) as pool:
            action_statuses = list(pool.map(lambda value: act_on_due(self.root, value).status, actions))
        self.assertEqual(action_statuses, ["saved"] * 12)
        self.assertEqual(len(list_due(self.root, now="2026-09-22T13:00:00Z").payload["items"][0]["actions"]), 12)

    def test_sc24_natural_exposure_is_visible_to_scheduler_without_advancing_or_scoring_due(self) -> None:
        due = schedule_after_feedback(self.root, self.attempt, feedback(self.attempt["attempt_id"])).payload["due"]
        event = {"event_id":"exposure_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","learning_unit_id":due["learning_unit_id"],"kind":"applied","occurred_at":"2026-09-21T02:00:00Z"}
        signal = due_exposure_signal(due, [event])
        self.assertEqual(signal["recommendation"], "consider_snooze_or_changed_context")
        self.assertFalse(signal["counts_as_retrieval_success"])
        self.assertEqual((due["milestone_index"], due["state"], due["last_outcome"]), (0, "active", "PARTIAL"))
        self.assertIsNone(due_exposure_signal(due, [{**event, "kind":"answer_revealed"}]))


if __name__ == "__main__":
    unittest.main()
