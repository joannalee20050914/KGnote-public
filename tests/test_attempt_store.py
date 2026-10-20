from __future__ import annotations

import copy
import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest import mock

from jsonschema import Draft202012Validator, FormatChecker

from kgnote.review import list_attempts, save_attempt


def request(*, state: str = "draft", response: str = "我的草稿", attempt_id: str = "attempt_0123456789abcdef0123456789abcdef") -> dict:
    submitted = state == "submitted"
    return {
        "schema_version": "kgnote.attempt-save-request.v1",
        "attempt_id": attempt_id,
        "review_item_id": "item_relation_edge_os_application_system_call",
        "item_revision": 1,
        "learning_unit_id": "guided_map_os_safety_efficiency_review",
        "activity_type": "relation_recall",
        "state": state,
        "started_at": "2026-09-20T01:00:00+00:00",
        "submitted_at": "2026-09-20T01:02:00+00:00" if submitted else None,
        "raw_response": response,
        "confidence": None,
        "hint_events": [],
        "support_state": "unassisted",
        "answer_exposure_state": "revealed_after_submission" if submitted else "hidden",
        "outcome": "INCORRECT" if submitted else None,
        "correction_feedback": "人工對照 rubric。" if submitted else None,
        "entry_context": {"route": "/practice.html", "from_route": "/learn.html", "entry_kind": "voluntary_practice", "due_id": None},
        "source_refs": ["src_os_overview_review"],
        "claim_refs": [{"claim_id": "edge_os_application_system_call", "revision": 1}],
        "evidence_refs": ["evidence_os_protection"],
    }


class AttemptStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_draft_updates_then_submission_persists_raw_wrong_answer(self) -> None:
        first = save_attempt(self.root, request(response="還在想"), recorded_at="2026-09-20T01:00:01+00:00")
        self.assertEqual(first.status, "saved")
        updated = request(response="完全錯的回答")
        self.assertEqual(save_attempt(self.root, updated, recorded_at="2026-09-20T01:00:02+00:00").status, "saved")
        submitted = request(state="submitted", response="完全錯的回答")
        result = save_attempt(self.root, submitted, recorded_at="2026-09-20T01:02:01+00:00")
        self.assertEqual(result.status, "saved")
        self.assertEqual(result.payload["attempt"]["raw_response"], "完全錯的回答")
        self.assertEqual(result.payload["attempt"]["outcome"], "INCORRECT")
        read_back = list_attempts(self.root, submitted["learning_unit_id"])
        self.assertEqual(read_back.status, "ready")
        self.assertEqual(read_back.payload["attempts"][0]["attempt_id"], submitted["attempt_id"])

    def test_same_submitted_payload_is_idempotent_but_different_response_conflicts(self) -> None:
        submitted = request(state="submitted", response="不知道")
        self.assertEqual(save_attempt(self.root, submitted, recorded_at="2026-09-20T01:02:01+00:00").status, "saved")
        self.assertEqual(save_attempt(self.root, copy.deepcopy(submitted), recorded_at="2026-09-20T01:04:00+00:00").status, "unchanged")
        changed = copy.deepcopy(submitted)
        changed["raw_response"] = "網路重送卻變成另一個答案"
        conflict = save_attempt(self.root, changed, recorded_at="2026-09-20T01:05:00+00:00")
        self.assertEqual(conflict.status, "conflict")
        self.assertEqual(conflict.problem_code, "submitted_attempt_conflict")
        stored = json.loads((self.root / "attempts" / f"{submitted['attempt_id']}.json").read_text())
        self.assertEqual(stored["raw_response"], "不知道")

    def test_retry_requires_and_preserves_a_new_attempt_identity(self) -> None:
        first = request(state="submitted", response="不知道")
        second = request(state="submitted", response="向核心請求", attempt_id="attempt_fedcba9876543210fedcba9876543210")
        self.assertEqual(save_attempt(self.root, first).status, "saved")
        self.assertEqual(save_attempt(self.root, second).status, "saved")
        attempts = list_attempts(self.root, first["learning_unit_id"]).payload["attempts"]
        self.assertEqual({item["attempt_id"] for item in attempts}, {first["attempt_id"], second["attempt_id"]})

    def test_malformed_values_and_write_failure_fail_safely(self) -> None:
        malformed = request()
        malformed["submitted_at"] = "not-a-time"
        self.assertEqual(save_attempt(self.root, malformed).problem_code, "invalid_submitted_at")
        good = request()
        with mock.patch("kgnote.review.attempts.os.replace", side_effect=OSError("disk full")):
            failed = save_attempt(self.root, good)
        self.assertEqual(failed.status, "failed")
        self.assertFalse((self.root / "attempts" / f"{good['attempt_id']}.json").exists())

    def test_attempt_request_schema_is_valid_and_matches_runtime_request(self) -> None:
        schema_path = Path(__file__).resolve().parents[1] / "schemas/attempt/v1/save-request.schema.json"
        schema = json.loads(schema_path.read_text())
        Draft202012Validator.check_schema(schema)
        self.assertEqual(list(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(request(state="submitted", response="不知道"))), [])

    def test_concurrent_first_write_preserves_one_submitted_payload(self) -> None:
        values = [request(state="submitted", response="same immutable submission") for _ in range(12)]
        with ThreadPoolExecutor(max_workers=12) as pool:
            statuses = list(pool.map(lambda value: save_attempt(self.root, value).status, values))
        self.assertEqual(statuses.count("saved"), 1)
        self.assertEqual(statuses.count("unchanged"), 11)
        changed = request(state="submitted", response="late conflicting submission")
        self.assertEqual(save_attempt(self.root, changed).status, "conflict")
        self.assertEqual(list_attempts(self.root, values[0]["learning_unit_id"]).payload["attempts"][0]["raw_response"], "same immutable submission")


if __name__ == "__main__":
    unittest.main()
