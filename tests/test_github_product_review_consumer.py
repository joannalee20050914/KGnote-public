import json
import sys
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from github_product_review_consumer import (  # noqa: E402
    CandidateIdentity,
    ConsumerInputError,
    consume_records,
)


FINGERPRINT = "a" * 64
COMMIT = "b" * 40


class GitHubProductReviewConsumerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = json.loads(
            (REPO / "schemas/product-review/v1/review-result.schema.json").read_text()
        )

    def setUp(self):
        self.config = {
            "enabled": True,
            "result_marker": "KGNOTE_PRODUCT_REVIEW_RESULT_V1",
            "trusted_reviewer_author_login": "trusted-reviewer[bot]",
            "last_reviewed_candidate_fingerprint": None,
        }
        self.identity = CandidateIdentity(
            program_id="program-1",
            goal_id="goal-1",
            candidate_fingerprint=FINGERPRINT,
            candidate_commit=COMMIT,
            review_round=1,
        )

    def result(self, verdict="PASS", findings=None):
        if findings is None:
            findings = []
        return {
            "protocol": "kgnote.product-review.v1",
            "program_id": "program-1",
            "goal_id": "goal-1",
            "candidate_fingerprint": FINGERPRINT,
            "candidate_commit": COMMIT,
            "review_round": 1,
            "verdict": verdict,
            "findings": findings,
            "native_ui_observed": False,
        }

    def record(self, result=None, **overrides):
        if result is None:
            result = self.result()
        record = {
            "source": "pull_request_review",
            "author_login": "trusted-reviewer[bot]",
            "review_state": "APPROVED",
            "record_id": 42,
            "body": (
                "<!-- KGNOTE_PRODUCT_REVIEW_RESULT_V1 -->\n"
                f"```json\n{json.dumps(result)}\n```"
            ),
        }
        record.update(overrides)
        return record

    def consume(self, records, config=None):
        return consume_records(
            config=self.config if config is None else config,
            schema=self.schema,
            identity=self.identity,
            records=records,
        )

    def test_disabled_transport_never_consumes_even_valid_result(self):
        config = {**self.config, "enabled": False}
        decision = self.consume([self.record()], config=config)
        self.assertEqual("DISABLED", decision["status"])
        self.assertFalse(decision["accepted"])

    def test_missing_observed_trusted_author_blocks_consumption(self):
        config = {**self.config, "trusted_reviewer_author_login": None}
        decision = self.consume([self.record()], config=config)
        self.assertEqual("AUTOMATION_BLOCKED", decision["status"])
        self.assertFalse(decision["accepted"])

    def test_accepts_exact_fingerprint_bound_formal_pass(self):
        decision = self.consume([self.record()])
        self.assertEqual("PASS", decision["status"])
        self.assertTrue(decision["accepted"])
        self.assertEqual(FINGERPRINT, decision["candidate_fingerprint"])
        self.assertEqual("trusted-reviewer[bot]", decision["review_author"])
        self.assertEqual(0, decision["finding_count"])

    def test_accepts_comment_fallback_without_formal_state(self):
        decision = self.consume(
            [self.record(source="issue_comment", review_state=None)]
        )
        self.assertEqual("PASS", decision["status"])
        self.assertEqual("issue_comment", decision["review_source"])

    def test_rejects_untrusted_author(self):
        decision = self.consume([self.record(author_login="joannalee20050914")])
        self.assertEqual("WAITING_FOR_PRODUCT_REVIEW", decision["status"])
        self.assertEqual("untrusted_author", decision["rejected"][0]["reason"])

    def test_rejects_stale_candidate_fingerprint(self):
        stale = self.result()
        stale["candidate_fingerprint"] = "c" * 64
        decision = self.consume([self.record(result=stale)])
        self.assertEqual("WAITING_FOR_PRODUCT_REVIEW", decision["status"])
        self.assertIn(
            "candidate_fingerprint", decision["rejected"][0]["fields"]
        )

    def test_rejects_wrong_commit_and_round(self):
        wrong = self.result()
        wrong["candidate_commit"] = "c" * 40
        wrong["review_round"] = 2
        decision = self.consume([self.record(result=wrong)])
        self.assertEqual("WAITING_FOR_PRODUCT_REVIEW", decision["status"])
        self.assertEqual(
            {"candidate_commit", "review_round"},
            set(decision["rejected"][0]["fields"]),
        )

    def test_rejects_schema_invalid_result(self):
        invalid = self.result()
        del invalid["native_ui_observed"]
        decision = self.consume([self.record(result=invalid)])
        self.assertEqual("schema_invalid", decision["rejected"][0]["reason"])

    def test_rejects_multiple_json_fences(self):
        record = self.record()
        record["body"] += "\n```json\n{}\n```"
        decision = self.consume([record])
        self.assertEqual(
            "expected_exactly_one_fenced_json_object",
            decision["rejected"][0]["reason"],
        )

    def test_rejects_duplicate_result_markers(self):
        record = self.record()
        record["body"] += "\n<!-- KGNOTE_PRODUCT_REVIEW_RESULT_V1 -->"
        decision = self.consume([record])
        self.assertEqual(
            "expected_exactly_one_result_marker",
            decision["rejected"][0]["reason"],
        )

    def test_rejects_formal_state_that_disagrees_with_verdict(self):
        revise = self.result(
            verdict="REVISE",
            findings=[
                {
                    "id": "finding-example",
                    "severity": "major",
                    "category": "engineering",
                    "observation": "Observed defect",
                    "expected_behavior": "Correct behavior",
                    "authority_refs": ["docs/PRODUCT_CONTRACT.md"],
                    "candidate_evidence": ["tests/example.py"],
                }
            ],
        )
        decision = self.consume([self.record(result=revise)])
        self.assertEqual(
            "formal_review_state_mismatch", decision["rejected"][0]["reason"]
        )

    def test_accepts_structured_revise_findings(self):
        finding = {
            "id": "finding-example",
            "severity": "blocking",
            "category": "semantic",
            "observation": "Direction is reversed",
            "expected_behavior": "Use the contract direction",
            "authority_refs": ["docs/PRODUCT_CONTRACT.md"],
            "candidate_evidence": ["src/example.py"],
        }
        decision = self.consume(
            [
                self.record(
                    result=self.result(verdict="REVISE", findings=[finding]),
                    review_state="CHANGES_REQUESTED",
                )
            ]
        )
        self.assertEqual("REVISE", decision["status"])
        self.assertEqual([finding], decision["findings"])

    def test_dedupes_already_consumed_candidate(self):
        config = {
            **self.config,
            "last_reviewed_candidate_fingerprint": FINGERPRINT,
        }
        decision = self.consume([self.record()], config=config)
        self.assertEqual("ALREADY_CONSUMED", decision["status"])
        self.assertFalse(decision["accepted"])

    def test_multiple_matching_results_fail_closed(self):
        decision = self.consume([self.record(), self.record(record_id=43)])
        self.assertEqual("AUTOMATION_BLOCKED", decision["status"])
        self.assertEqual(2, decision["matching_record_count"])

    def test_malformed_record_shape_is_input_error(self):
        with self.assertRaises(ConsumerInputError):
            self.consume([{"source": "issue_comment"}])

    def test_invalid_repository_result_schema_is_input_error(self):
        with self.assertRaises(ConsumerInputError):
            consume_records(
                config=self.config,
                schema={"type": 123},
                identity=self.identity,
                records=[self.record()],
            )


if __name__ == "__main__":
    unittest.main()
