import json
import sys
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))

from github_product_review_consumer import CandidateIdentity, consume_records  # noqa: E402


class ProductReviewConsumerSchemaContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = json.loads(
            (REPO / "schemas/product-review/v1/review-result.schema.json").read_text()
        )
        cls.identity = CandidateIdentity(
            repository="joannalee20050914/KGnote-public",
            pull_request=33,
            program_id="program-schema-contract",
            goal_id="goal-schema-contract",
            candidate_fingerprint="a" * 64,
            candidate_commit="b" * 40,
            review_round=1,
        )

    def result(self, verdict="PASS", findings=None):
        return {
            "protocol": "kgnote.product-review.v1",
            "repository": self.identity.repository,
            "pull_request": self.identity.pull_request,
            "program_id": self.identity.program_id,
            "goal_id": self.identity.goal_id,
            "candidate_fingerprint": self.identity.candidate_fingerprint,
            "candidate_commit": self.identity.candidate_commit,
            "review_round": self.identity.review_round,
            "verdict": verdict,
            "findings": [] if findings is None else findings,
            "native_ui_observed": False,
        }

    def consume(self, result):
        record = {
            "source": "pull_request_review",
            "author_login": "trusted-reviewer[bot]",
            "review_state": "COMMENTED",
            "record_id": 42,
            "body": (
                "<!-- kgnote-ai-product-review:v1 "
                f"reviewed_head_sha={self.identity.candidate_commit} -->\n"
                f"```json\n{json.dumps(result)}\n```"
            ),
        }
        return consume_records(
            config={
                "enabled": True,
                "result_marker": "kgnote-ai-product-review:v1",
                "trusted_reviewer_author_login": "trusted-reviewer[bot]",
                "last_reviewed_candidate_fingerprint": None,
            },
            schema=self.schema,
            identity=self.identity,
            records=[record],
        )

    def test_rejects_finding_missing_formal_required_fields(self):
        decision = self.consume(
            self.result(
                verdict="CHANGES_REQUIRED",
                findings=[{
                    "id": "finding-incomplete",
                    "severity": "major",
                    "category": "engineering",
                    "observation": "A defect exists.",
                }],
            )
        )
        self.assertFalse(decision["accepted"])
        self.assertEqual("schema_invalid", decision["rejected"][0]["reason"])

    def test_rejects_non_decision_verdict_with_human_decisions(self):
        result = self.result(verdict="PASS")
        result["human_decisions"] = [{
            "decision_id": "D-901",
            "question": "Choose A or B?",
            "why_existing_authority_is_insufficient": "The sources do not choose.",
            "affected_requirements": ["KG-GOV-07"],
            "available_options": ["A", "B"],
            "observable_consequences": ["Behavior A", "Behavior B"],
            "blocking_scope": ["external review"],
            "linked_findings": ["finding-choice"],
        }]
        decision = self.consume(result)
        self.assertFalse(decision["accepted"])
        self.assertEqual("schema_invalid", decision["rejected"][0]["reason"])


if __name__ == "__main__":
    unittest.main()
