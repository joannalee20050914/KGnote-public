from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import external_review_handoff as HANDOFF  # noqa: E402


class ExternalReviewHandoffTests(unittest.TestCase):
    def fixture(self, root: Path) -> tuple[dict, dict]:
        (root / ".ai").mkdir(parents=True)
        (root / "schemas/product-review/v1").mkdir(parents=True)
        (root / "schemas/product-review/v1/review-result.schema.json").write_text(
            (ROOT / "schemas/product-review/v1/review-result.schema.json").read_text()
        )
        config = {
            "enabled": True, "canonical_repository": "owner/repo", "candidate_repository": "owner/repo",
            "trigger_repository": "owner/repo", "review_request_repository": "owner/repo", "archive_repository": "owner/archive",
            "review_pr_number": 23, "program_id": "program", "result_marker": "marker", "trusted_reviewer_author_login": "owner",
            "trigger_events": ["issue_comment.created"], "trigger_comment_template": "@kgnote-ai-review {candidate_commit}",
            "delivery_issue_number": 8, "project_owner": "owner", "project_number": 1, "project_id": "project",
            "project_item_id": "item", "project_status_field_id": "status", "project_review_option_id": "review",
        }
        state = {"goal_id": "goal", "candidate_commit": "a" * 40, "candidate_fingerprint": "b" * 64, "review_round": 1,
                 "publication": {"status": "PUBLISHED"}, "external_review": {"status": "PENDING"}}
        (root / ".ai/github-product-reviewer.json").write_text(json.dumps(config))
        (root / ".ai/external-review-state.json").write_text(json.dumps(state))
        return config, state

    def test_pass_is_consumed_and_issue_project_receipt_is_read_back(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); _config, state = self.fixture(root)
            decision = {"accepted": True, "verdict": "PASS", "candidate_commit": state["candidate_commit"],
                "candidate_fingerprint": state["candidate_fingerprint"], "review_round": 1, "review_author": "owner",
                "review_source": "pull_request_review", "record_id": 99, "native_ui_observed": False, "findings": []}
            def runner(command, *, cwd):
                joined = " ".join(command)
                if "/pulls/23/reviews" in joined: return json.dumps([{"id": 99, "user": {"login": "owner"}, "body": "result", "state": "COMMENTED", "html_url": "https://review"}])
                if "/issues/23/comments" in joined or ("/issues/8/comments" in joined and "-f" not in command): return "[]"
                if "/issues/8/comments" in joined: return json.dumps({"html_url": "https://issue-comment"})
                if command[:3] == ["gh", "project", "item-edit"]: return ""
                if command[:3] == ["gh", "project", "item-list"]: return json.dumps({"items": [{"id": "item", "status": "Review Queue"}]})
                raise AssertionError(command)
            with mock.patch.object(HANDOFF.external_review_control, "publication_progression_blockers", return_value=[]), \
                 mock.patch.object(HANDOFF.consumer, "consume_records", return_value=decision):
                self.assertEqual(HANDOFF.process(root, runner)["verdict"], "PASS")
            recorded = json.loads((root / ".ai/external-review-state.json").read_text())
            self.assertEqual(recorded["delivery_receipt"]["status"], "VERIFIED")
            self.assertEqual(recorded["delivery_receipt"]["project_status"], "Review Queue")

    def test_missing_result_remains_waiting_without_fabricating_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); _config, _state = self.fixture(root)
            runner = lambda command, cwd: "[]"
            with mock.patch.object(HANDOFF.external_review_control, "publication_progression_blockers", return_value=[]), \
                 mock.patch.object(HANDOFF.consumer, "consume_records", return_value={"accepted": False, "status": "WAITING_FOR_PRODUCT_REVIEW"}):
                result = HANDOFF.process(root, runner)
            self.assertFalse(result["accepted"])
            self.assertNotIn("delivery_receipt", json.loads((root / ".ai/external-review-state.json").read_text()))

    def test_goal_specific_paths_and_no_delivery_side_effect_are_supported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); config, state = self.fixture(root)
            config["delivery_issue_number"] = None
            custom = root / "goal-review"
            custom.mkdir()
            config_path, state_path = custom / "config.json", custom / "state.json"
            config_path.write_text(json.dumps(config))
            state_path.write_text(json.dumps(state))
            decision = {
                "accepted": True, "verdict": "PASS",
                "candidate_commit": state["candidate_commit"],
                "candidate_fingerprint": state["candidate_fingerprint"],
                "review_round": 1, "review_author": "owner",
                "review_source": "issue_comment", "record_id": 100,
                "native_ui_observed": False, "findings": [],
            }
            calls = []
            def runner(command, *, cwd):
                calls.append(command)
                if "/pulls/23/reviews" in " ".join(command): return "[]"
                if "/issues/23/comments" in " ".join(command):
                    return json.dumps([{"id":100,"user":{"login":"owner"},"body":"result","html_url":"https://review"}])
                raise AssertionError(command)
            with mock.patch.object(HANDOFF.external_review_control, "publication_progression_blockers", return_value=[]), \
                 mock.patch.object(HANDOFF.consumer, "consume_records", return_value=decision):
                result = HANDOFF.process(
                    root, runner, config_path=config_path, state_path=state_path,
                )
            self.assertEqual("PASS", result["verdict"])
            self.assertNotIn("delivery_receipt", json.loads(state_path.read_text()))
            self.assertFalse(any("/issues/8/comments" in " ".join(call) for call in calls))


if __name__ == "__main__":
    unittest.main()
