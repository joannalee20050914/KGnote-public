from __future__ import annotations

import copy
import json
import socket
import unittest
from pathlib import Path
from unittest import mock

from jsonschema import Draft202012Validator

from kgnote.review import (
    build_assessment_prompt,
    load_reviewer_context,
    replay_assessment_response,
)


ROOT = Path(__file__).resolve().parents[1]
STORE = ROOT / "fixtures/phase0-obsidian"


class ReviewAssessmentTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.context = load_reviewer_context(STORE, "concept_correlation").response["context"]

    def test_exact_prompt_contains_only_bounded_context_one_question_and_answer(self):
        original = copy.deepcopy(self.context)
        first = build_assessment_prompt(
            context=self.context,
            question="Does correlation alone establish causation?",
            answer="No. A third variable may explain both observations.",
            hint_used=False,
            reviewer_version="mock-reviewer.v1",
        )
        second = build_assessment_prompt(
            context=copy.deepcopy(self.context),
            question="Does correlation alone establish causation?",
            answer="No. A third variable may explain both observations.",
            hint_used=False,
            reviewer_version="mock-reviewer.v1",
        )
        self.assertEqual(first, second)
        self.assertEqual(self.context, original)
        self.assertEqual(first.envelope["context"], self.context)
        self.assertEqual(first.envelope["response_contract"]["max_correction_sentences"], 2)
        serialized = json.dumps(first.envelope)
        self.assertNotIn("uri_or_path", serialized)
        self.assertNotIn("understood", serialized.lower())
        changed = first.envelope
        changed["context"]["evidence"].clear()
        self.assertTrue(first.envelope["context"]["evidence"])

    def test_mock_responses_accept_only_four_outcomes_and_two_sentences(self):
        for outcome in ("CORRECT", "PARTIAL", "INCORRECT", "INSUFFICIENT_EVIDENCE"):
            with self.subTest(outcome=outcome):
                raw = json.dumps({"outcome": outcome, "correction": "First sentence. Second sentence."})
                result = replay_assessment_response(raw)
                self.assertEqual(result.status, "accepted")
                self.assertEqual(result.assessment["outcome"], outcome)
        too_long = replay_assessment_response(json.dumps({
            "outcome": "PARTIAL", "correction": "One. Two. Three."
        }))
        self.assertEqual(too_long.problem.code, "invalid_correction")

    def test_malformed_extra_fields_and_mastery_outcome_fail_closed(self):
        cases = (
            ("{bad", "invalid_json"),
            (json.dumps({"outcome": "CORRECT"}), "invalid_response_fields"),
            (json.dumps({"outcome": "CORRECT", "correction": "", "mastery": 0.9}), "invalid_response_fields"),
            (json.dumps({"outcome": "UNDERSTOOD", "correction": "Looks good."}), "invalid_outcome"),
            (b"\xff", "invalid_json"),
        )
        for raw, code in cases:
            with self.subTest(code=code):
                result = replay_assessment_response(raw)
                self.assertEqual(result.status, "rejected")
                self.assertEqual(result.problem.code, code)
                self.assertNotIn("mastery", repr(result))

    def test_prompt_validation_and_replay_have_no_io(self):
        with mock.patch.object(Path, "read_text", side_effect=AssertionError("read forbidden")), \
             mock.patch.object(Path, "write_text", side_effect=AssertionError("write forbidden")), \
             mock.patch.object(socket, "create_connection", side_effect=AssertionError("network forbidden")), \
             mock.patch("urllib.request.urlopen", side_effect=AssertionError("network forbidden")):
            prompt = build_assessment_prompt(
                context=self.context, question="Question?", answer="Answer.",
                hint_used=True, reviewer_version="mock-reviewer.v1",
            )
            result = replay_assessment_response('{"outcome":"CORRECT","correction":""}')
        self.assertEqual(result.status, "accepted")
        self.assertEqual(len(prompt.prompt_sha256), 64)
        for kwargs, code in (
            ({"question": ""}, "invalid_question"),
            ({"answer": ""}, "invalid_answer"),
            ({"hint_used": "no"}, "invalid_hint_used"),
        ):
            values = {"context": self.context, "question": "Q?", "answer": "A.", "hint_used": False, "reviewer_version": "mock.v1"}
            values.update(kwargs)
            with self.subTest(code=code), self.assertRaisesRegex(ValueError, code):
                build_assessment_prompt(**values)

    def test_response_json_schema_matches_runtime_shape(self):
        schema = json.loads((ROOT / "schemas/review-assessment/v1/response.schema.json").read_text())
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate({"outcome": "PARTIAL", "correction": "Add the missing confounder."})


if __name__ == "__main__":
    unittest.main()
