import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from claude_review_ingestion import (
    IngestionError,
    event_from_adapter_checkpoint,
    ingest,
    publish_validated_review,
)


class ClaudeReviewIngestionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = json.loads((ROOT / "schemas/product-review/v1/review-result.schema.json").read_text())
        cls.config = {"enabled": True, "result_marker": "kgnote-ai-product-review:v1",
                      "trusted_reviewer_author_login": "claude-code-local",
                      "trusted_reviewer_identities": ["claude-code:fixture"],
                      "product_contract_review_scope": "KGNOTE_PRODUCT_CONTRACT",
                      "last_reviewed_candidate_fingerprint": None}

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.checkpoint = Path(self.temp.name) / "state.json"
        self.event = {
            "event_id": "event-1", "status": "REVIEW_SUBMITTED", "repository": "example/repo",
            "issue": 7, "pull_request": 9, "program_id": "program", "goal_id": "goal",
            "candidate_commit": "a" * 40, "candidate_fingerprint": "b" * 64,
            "review_round": 2, "cumulative_round_limit": 5, "reviewer_identity": "claude-code:fixture",
            "review_scope": "KGNOTE_PRODUCT_CONTRACT",
            "record_id": 1, "review": {"verdict": "PASS", "findings": [], "native_ui_observed": False},
        }

    def tearDown(self): self.temp.cleanup()

    def test_local_validation_is_not_canonical_product_acceptance(self):
        first = ingest(event=self.event, config=self.config, schema=self.schema, checkpoint_path=self.checkpoint)
        second = ingest(event=self.event, config=self.config, schema=self.schema, checkpoint_path=self.checkpoint)
        self.assertEqual("VALIDATED_PENDING_GITHUB_WRITEBACK", first["status"])
        self.assertEqual("PASS", first["validated_verdict"])
        self.assertFalse(first["product_review_accepted"])
        self.assertEqual(first, second)

    def github_config(self):
        return {**self.config, "trusted_reviewer_author_login": "owner",
                "github_writeback_enabled": True,
                "github_writeback_authorized_reviewer_identities": ["claude-code:fixture"]}

    def github_runner(self, *, existing=False, fail_write=False, bad_id=False, wrong_author=False):
        comments = []
        calls = []
        def run(command, cwd):
            calls.append(command)
            if command[:3] == ["gh", "pr", "view"]:
                return json.dumps({"headRefOid": "a" * 40})
            if "--paginate" in command:
                return json.dumps(comments)
            if fail_write:
                raise IngestionError("write failed")
            body = command[-1][5:]
            comments.append({"id": "wrong" if bad_id else 987,
                             "html_url": "https://github.test/pull/9#issuecomment-987",
                             "created_at": "2026-10-20T03:00:00Z", "body": body,
                             "user": {"login": "intruder" if wrong_author else "owner"}})
            return "{}"
        if existing:
            # Capture the canonical bytes by allowing one first publication.
            publish_validated_review(event=self.event, config=self.github_config(), schema=self.schema,
                                     checkpoint_path=self.checkpoint, cwd=Path(self.temp.name), runner=run)
            calls.clear()
        return run, calls

    def test_github_writeback_requires_separate_authority_and_does_not_write(self):
        calls = []
        with self.assertRaisesRegex(IngestionError, "not authorized"):
            publish_validated_review(event=self.event, config=self.config, schema=self.schema,
                                     checkpoint_path=self.checkpoint, cwd=Path(self.temp.name),
                                     runner=lambda command, cwd: calls.append(command))
        self.assertEqual([], calls)

    def test_github_write_failure_does_not_accept(self):
        runner, _ = self.github_runner(fail_write=True)
        with self.assertRaisesRegex(IngestionError, "write failed"):
            publish_validated_review(event=self.event, config=self.github_config(), schema=self.schema,
                                     checkpoint_path=self.checkpoint, cwd=Path(self.temp.name), runner=runner)
        self.assertFalse(json.loads(self.checkpoint.read_text())["product_review_accepted"])

    def test_canonical_writeback_readback_and_restart_are_idempotent(self):
        runner, calls = self.github_runner()
        first = publish_validated_review(event=self.event, config=self.github_config(), schema=self.schema,
                                         checkpoint_path=self.checkpoint, cwd=Path(self.temp.name), runner=runner)
        second = publish_validated_review(event=self.event, config=self.github_config(), schema=self.schema,
                                          checkpoint_path=self.checkpoint, cwd=Path(self.temp.name), runner=runner)
        self.assertTrue(first["product_review_accepted"])
        self.assertEqual(987, first["canonical_record"]["record_id"])
        self.assertEqual("claude-code:fixture", first["canonical_record"]["reviewer_identity"])
        self.assertEqual("owner", first["canonical_record"]["publisher_identity"])
        self.assertEqual("ALREADY_CONSUMED", second["status"])
        self.assertEqual(1, sum("-f" in command for command in calls))

    def test_unknown_write_result_is_recovered_by_canonical_readback(self):
        comments = []
        post_count = 0
        fail_after_write = True

        def run(command, cwd):
            nonlocal post_count, fail_after_write
            if command[:3] == ["gh", "pr", "view"]:
                return json.dumps({"headRefOid": "a" * 40})
            if "--paginate" in command:
                return json.dumps(comments)
            post_count += 1
            body = command[-1][5:]
            comments.append({
                "id": 988, "html_url": "https://github.test/pull/9#issuecomment-988",
                "created_at": "2026-10-20T03:00:00Z", "body": body,
                "user": {"login": "owner"},
            })
            if fail_after_write:
                fail_after_write = False
                raise IngestionError("write result unknown")
            return "{}"

        with self.assertRaisesRegex(IngestionError, "unknown"):
            publish_validated_review(
                event=self.event, config=self.github_config(), schema=self.schema,
                checkpoint_path=self.checkpoint, cwd=Path(self.temp.name), runner=run,
            )
        recovered = publish_validated_review(
            event=self.event, config=self.github_config(), schema=self.schema,
            checkpoint_path=self.checkpoint, cwd=Path(self.temp.name), runner=run,
        )
        self.assertTrue(recovered["product_review_accepted"])
        self.assertEqual(988, recovered["canonical_record"]["record_id"])
        self.assertEqual(1, post_count)

    def test_invalid_github_record_id_and_identity_are_rejected(self):
        for kwargs, message in (({"bad_id": True}, "metadata is invalid"),
                                ({"wrong_author": True}, "Consumer rejected")):
            with self.subTest(kwargs=kwargs), tempfile.TemporaryDirectory() as directory:
                runner, _ = self.github_runner(**kwargs)
                with self.assertRaisesRegex(IngestionError, message):
                    publish_validated_review(event=self.event, config=self.github_config(), schema=self.schema,
                                             checkpoint_path=Path(directory) / "state.json",
                                             cwd=Path(directory), runner=runner)

    def test_stale_identity_is_rejected(self):
        self.event["review"]["candidate_commit"] = "c" * 40
        with self.assertRaisesRegex(IngestionError, "identity mismatch"):
            ingest(event=self.event, config=self.config, schema=self.schema, checkpoint_path=self.checkpoint)

    def test_code_review_pass_does_not_become_product_pass(self):
        self.event["review_scope"] = "CODE_ONLY"
        result = ingest(event=self.event, config=self.config, schema=self.schema, checkpoint_path=self.checkpoint)
        self.assertEqual("CODE_REVIEW_ONLY", result["status"])
        self.assertFalse(result["product_review_accepted"])

    def test_exact_config_bound_descriptive_scope_is_product_review(self):
        descriptive = "Review exact PR #33 Review 004 and preserve every owner gate."
        self.event["review_scope"] = descriptive
        config = {**self.config, "product_contract_review_scope": descriptive}
        result = ingest(
            event=self.event, config=config, schema=self.schema,
            checkpoint_path=self.checkpoint,
        )
        self.assertEqual("VALIDATED_PENDING_GITHUB_WRITEBACK", result["status"])
        self.assertEqual(descriptive, result["review_scope"])

    def test_adapter_checkpoint_bridge_preserves_exact_identity_and_scope(self):
        descriptive = "Review exact PR #33 Review 004 and preserve every owner gate."
        order = {
            "goal_id": self.event["goal_id"], "repository": self.event["repository"],
            "issue": self.event["issue"], "pull_request": self.event["pull_request"],
            "candidate_commit": self.event["candidate_commit"],
            "candidate_fingerprint": self.event["candidate_fingerprint"],
            "review_round_used": self.event["review_round"] - 1,
            "review_round_limit": self.event["cumulative_round_limit"],
            "program_id": self.event["program_id"], "review_scope": descriptive,
        }
        import hashlib
        identity_key = hashlib.sha256(
            (
                f"{order['repository']}\0{order['pull_request']}\0"
                f"{order['candidate_commit']}\0{order['candidate_fingerprint']}\0"
                f"{self.event['review_round']}"
            ).encode()
        ).hexdigest()
        checkpoint = {
            "schema_version": "kgnote.claude-reviewer-adapter-checkpoint.v1",
            "status": "COMPLETED", "identity_key": identity_key,
            "goal_id": order["goal_id"], "repository": order["repository"],
            "issue": order["issue"], "pull_request": order["pull_request"],
            "program_id": order["program_id"], "review_scope": descriptive,
            "candidate_commit": order["candidate_commit"],
            "candidate_fingerprint": order["candidate_fingerprint"],
            "review_round": self.event["review_round"],
            "review_round_limit": order["review_round_limit"],
            "review_result": self.event["review"],
            "execution_evidence": {"effective_status": "EFFECTIVE_CONFIRMED"},
        }
        event = event_from_adapter_checkpoint(
            reviewer_checkpoint=checkpoint, work_order=order,
            config={**self.config, "product_contract_review_scope": descriptive},
        )
        self.assertEqual("REVIEW_SUBMITTED", event["status"])
        self.assertEqual(descriptive, event["review_scope"])
        self.assertEqual(self.event["candidate_commit"], event["candidate_commit"])
        self.assertEqual("claude-code:fixture", event["reviewer_identity"])

    def test_untrusted_reviewer_identity_is_rejected(self):
        self.event["reviewer_identity"] = "claude-code:unknown"
        with self.assertRaisesRegex(IngestionError, "allow-listed"):
            ingest(event=self.event, config=self.config, schema=self.schema, checkpoint_path=self.checkpoint)

    def test_malformed_review_is_rejected(self):
        del self.event["review"]["native_ui_observed"]
        with self.assertRaisesRegex(IngestionError, "Consumer rejected"):
            ingest(event=self.event, config=self.config, schema=self.schema, checkpoint_path=self.checkpoint)

    def test_failure_classes_checkpoint_without_product_acceptance(self):
        for index, status in enumerate(("TIMEOUT", "QUOTA_EXHAUSTED", "PROVIDER_FAILURE", "CRASHED"), 1):
            event = {**self.event, "event_id": f"failure-{index}", "status": status}
            result = ingest(event=event, config=self.config, schema=self.schema, checkpoint_path=self.checkpoint)
            self.assertEqual("FAILED_CLOSED", result["status"]); self.assertFalse(result["product_review_accepted"])

    def test_resume_cannot_regress_round(self):
        ingest(event=self.event, config=self.config, schema=self.schema, checkpoint_path=self.checkpoint)
        later = {**self.event, "event_id": "event-2", "review_round": 1}
        with self.assertRaisesRegex(IngestionError, "regressed"):
            ingest(event=later, config=self.config, schema=self.schema, checkpoint_path=self.checkpoint)

    def test_round_beyond_cumulative_budget_is_rejected(self):
        self.event["review_round"] = 6
        self.event["cumulative_round_limit"] = 5
        with self.assertRaisesRegex(IngestionError, "outside the cumulative budget"):
            ingest(event=self.event, config=self.config, schema=self.schema, checkpoint_path=self.checkpoint)
