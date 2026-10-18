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
    def setUp(self) -> None:
        self.authority = {
            "repository": "owner/repo", "pull_request": 23,
            "candidate_commit": "a" * 40,
            "candidate_fingerprint": "b" * 64, "review_round": 1,
        }
        patcher = mock.patch.object(
            HANDOFF.external_review_control,
            "resolve_repository_canonical_authority",
            return_value=self.authority,
        )
        patcher.start()
        self.addCleanup(patcher.stop)

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
            "request_marker": "REQUEST_V2", "max_product_review_rounds": 16,
            "trigger_events": ["issue_comment.created"], "trigger_comment_template": "@kgnote-ai-review {candidate_commit}",
            "delivery_issue_number": 8, "project_owner": "owner", "project_number": 1, "project_id": "project",
            "project_item_id": "item", "project_status_field_id": "status", "project_review_option_id": "review",
        }
        state = {"goal_id": "goal", "candidate_commit": "a" * 40, "candidate_fingerprint": "b" * 64, "review_round": 1,
                 "publication": {"status": "PUBLISHED"}, "external_review": {"status": "PENDING"}}
        (root / ".ai/github-product-reviewer.json").write_text(json.dumps(config))
        (root / ".ai/external-review-state.json").write_text(json.dumps(state))
        (root / ".ai/DECISIONS.md").write_bytes((ROOT / ".ai/DECISIONS.md").read_bytes())
        return config, state

    def test_pass_is_consumed_and_issue_project_receipt_is_read_back(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); _config, state = self.fixture(root)
            decision = {"accepted": True, "verdict": "PASS", "candidate_commit": state["candidate_commit"],
                "candidate_fingerprint": state["candidate_fingerprint"], "review_round": 1, "review_author": "owner",
                "review_source": "pull_request_review", "record_id": 99, "native_ui_observed": False, "findings": []}
            created = False
            review_url = "https://github.com/owner/repo/pull/23#pullrequestreview-99"
            expected_body = HANDOFF.external_review_control.issue_receipt_body(
                _config, state, review_url, canonical_authority=self.authority
            )
            def runner(command, *, cwd):
                nonlocal created
                joined = " ".join(command)
                if "/pulls/23/reviews" in joined: return json.dumps([{"id": 99, "user": {"login": "owner"}, "body": "result", "state": "COMMENTED", "html_url": review_url, "submitted_at": "2026-10-16T00:00:00Z"}])
                if "/issues/23/comments" in joined: return "[]"
                if "/issues/8/comments" in joined and "-f" not in command:
                    return json.dumps([{"id": 101, "user": {"login": "owner"}, "body": expected_body,
                        "html_url": "https://github.com/owner/repo/issues/8#issuecomment-101"}]) if created else "[]"
                if "/issues/8/comments" in joined:
                    created = True
                    return json.dumps({"html_url": "https://github.com/owner/repo/issues/8#issuecomment-101"})
                if command[:3] == ["gh", "project", "item-edit"]: return ""
                if command[:3] == ["gh", "project", "item-list"]: return json.dumps({"items": [{"id": "item", "status": "Review Queue", "content": {"number": 8, "repository": "owner/repo"}}]})
                raise AssertionError(command)
            with mock.patch.object(HANDOFF.external_review_control, "publication_progression_blockers", return_value=[]), \
                 mock.patch.object(HANDOFF.consumer, "consume_records", return_value=decision):
                self.assertEqual(HANDOFF.process(root, runner)["verdict"], "PASS")
            recorded = json.loads((root / ".ai/external-review-state.json").read_text())
            self.assertEqual(recorded["delivery_receipt"]["status"], "VERIFIED")
            self.assertEqual(recorded["delivery_receipt"]["project_status"], "Review Queue")
            self.assertEqual(recorded["external_review"]["repository"], "owner/repo")
            self.assertEqual(recorded["external_review"]["submitted_at"], "2026-10-16T00:00:00Z")
            self.assertEqual(len(recorded["external_review"]["original_body_sha256"]), 64)

    def test_product_decision_projects_protocol_valid_canonical_queue(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); _config, state = self.fixture(root)
            proposal = {
                "decision_id": "D-901", "question": "Choose A or B?",
                "why_existing_authority_is_insufficient": "The approved sources do not choose.",
                "affected_requirements": ["KG-GOV-07"], "available_options": ["A", "B"],
                "observable_consequences": ["Behavior A", "Behavior B"],
                "blocking_scope": ["external publication"], "linked_findings": ["finding-choice"],
            }
            finding = {"id": "finding-choice", "severity": "blocking", "category": "product_intent",
                "observation": "authority gap", "expected_behavior": "human choice",
                "authority_refs": ["PLAN.md"], "candidate_evidence": ["web/example.js"]}
            result = {"protocol": "kgnote.product-review.v1", "repository": "owner/repo",
                "pull_request": 23, "program_id": "program", "goal_id": "goal",
                "candidate_fingerprint": state["candidate_fingerprint"],
                "candidate_commit": state["candidate_commit"], "review_round": 1,
                "verdict": "PRODUCT_DECISION_REQUIRED", "findings": [finding],
                "human_decisions": [proposal], "native_ui_observed": False}
            body = (f"<!-- marker reviewed_head_sha={state['candidate_commit']} -->\n"
                    f"```json\n{json.dumps(result)}\n```")
            request = {"status": "PASS", "review_id": "review-example-001",
                "candidate_revision": state["candidate_commit"] + "+worktree:" + state["candidate_fingerprint"],
                "candidate_fingerprint": state["candidate_fingerprint"]}
            runner = lambda command, cwd: json.dumps([{"id": 99, "user": {"login": "owner"}, "body": body,
                "state": "COMMENTED", "html_url": "https://github.com/owner/repo/pull/23#pullrequestreview-99", "submitted_at": "2026-10-16T00:00:00Z"}]) if "/reviews" in " ".join(command) else "[]"
            with mock.patch.object(HANDOFF.external_review_control, "publication_progression_blockers", return_value=[]), \
                 mock.patch.object(HANDOFF.control, "load_review_artifacts", return_value=(request, {}, {"schema_version": "kgnote.review-decisions.v1", "protocol_version": "kgnote.review-protocol.v1", "decisions": []})):
                self.assertEqual(HANDOFF.process(root, runner)["verdict"], "PRODUCT_DECISION_REQUIRED")
            projected = HANDOFF.control.extract_embedded_json(
                root / ".ai/DECISIONS.md",
                HANDOFF.control.DECISIONS_BEGIN,
                HANDOFF.control.DECISIONS_END,
            )["decisions"][0]
            self.assertEqual(projected["decision_id"], "D-901")
            self.assertEqual(projected["status"], "PENDING_HUMAN")
            self.assertEqual(projected["candidate_fingerprint"], state["candidate_fingerprint"])
            recorded = json.loads((root / ".ai/external-review-state.json").read_text())
            self.assertEqual(recorded["pending_external_decisions"], ["D-901"])

    def test_invalid_record_id_is_durably_rejected_for_both_sources_and_restart_safe(self):
        missing = object()
        for source in ("pull_request_review", "issue_comment"):
            for invalid_id in (missing, None, "99", 0, -1, True):
                with self.subTest(source=source, invalid_id=invalid_id), tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp); _config, state = self.fixture(root)
                    decisions_before = (root / ".ai/DECISIONS.md").read_bytes()
                    result = {"protocol": "kgnote.product-review.v1", "repository": "owner/repo",
                        "pull_request": 23, "program_id": "program", "goal_id": "goal",
                        "candidate_fingerprint": state["candidate_fingerprint"],
                        "candidate_commit": state["candidate_commit"], "review_round": 1,
                        "verdict": "PASS", "findings": [], "native_ui_observed": False}
                    body = (f"<!-- marker reviewed_head_sha={state['candidate_commit']} -->\n"
                            f"```json\n{json.dumps(result)}\n```")
                    record = {"id": 99, "user": {"login": "owner"}, "body": body,
                        "html_url": ("https://github.com/owner/repo/pull/23#pullrequestreview-99"
                            if source == "pull_request_review" else
                            "https://github.com/owner/repo/pull/23#issuecomment-99")}
                    if source == "pull_request_review":
                        record.update(state="COMMENTED", submitted_at="2026-10-16T00:00:00Z")
                    else:
                        record["created_at"] = "2026-10-16T00:00:00Z"
                    if invalid_id is missing:
                        record.pop("id")
                    else:
                        record["id"] = invalid_id

                    def runner(command, *, cwd):
                        endpoint = "/reviews" if source == "pull_request_review" else "/comments"
                        return json.dumps([record]) if endpoint in " ".join(command) else "[]"

                    with mock.patch.object(HANDOFF.external_review_control, "publication_progression_blockers", return_value=[]):
                        first = HANDOFF.process(root, runner)
                        second = HANDOFF.process(root, runner)
                    for decision in (first, second):
                        self.assertEqual(decision["status"], "ADAPTER_REJECTED")
                        self.assertFalse(decision["accepted"])
                        self.assertIn("record_id must be a positive integer", decision["reason"])
                    self.assertEqual((root / ".ai/DECISIONS.md").read_bytes(), decisions_before)
                    recorded = json.loads((root / ".ai/external-review-state.json").read_text())
                    self.assertEqual(recorded["phase"], "EXTERNAL_PRODUCT_REVIEW_REJECTED")
                    self.assertFalse(recorded["external_review"]["consumer_accepted"])
                    self.assertNotIn("pending_external_decisions", recorded)

    def test_invalid_url_or_time_is_durably_rejected_symmetrically(self):
        missing = object()
        for source, time_field in (
            ("pull_request_review", "submitted_at"),
            ("issue_comment", "created_at"),
        ):
            for field in ("html_url", time_field):
                for invalid_value in (missing, None, 17, ""):
                    with self.subTest(source=source, field=field, invalid_value=invalid_value), tempfile.TemporaryDirectory() as tmp:
                        root = Path(tmp); _config, state = self.fixture(root)
                        result = {"protocol": "kgnote.product-review.v1", "repository": "owner/repo",
                            "pull_request": 23, "program_id": "program", "goal_id": "goal",
                            "candidate_fingerprint": state["candidate_fingerprint"],
                            "candidate_commit": state["candidate_commit"], "review_round": 1,
                            "verdict": "PASS", "findings": [], "native_ui_observed": False}
                        body = (f"<!-- marker reviewed_head_sha={state['candidate_commit']} -->\n"
                                f"```json\n{json.dumps(result)}\n```")
                        record = {"id": 99, "user": {"login": "owner"}, "body": body,
                            "html_url": ("https://github.com/owner/repo/pull/23#pullrequestreview-99"
                                if source == "pull_request_review" else
                                "https://github.com/owner/repo/pull/23#issuecomment-99"),
                            time_field: "2026-10-16T00:00:00Z"}
                        if source == "pull_request_review":
                            record["state"] = "COMMENTED"
                        if invalid_value is missing:
                            record.pop(field)
                        else:
                            record[field] = invalid_value

                        def runner(command, *, cwd):
                            endpoint = "/reviews" if source == "pull_request_review" else "/comments"
                            return json.dumps([record]) if endpoint in " ".join(command) else "[]"

                        with mock.patch.object(HANDOFF.external_review_control, "publication_progression_blockers", return_value=[]):
                            decision = HANDOFF.process(root, runner)
                        self.assertEqual(decision["status"], "ADAPTER_REJECTED")
                        self.assertFalse(decision["accepted"])
                        recorded = json.loads((root / ".ai/external-review-state.json").read_text())
                        self.assertFalse(recorded["external_review"]["consumer_accepted"])

    def test_nonexistent_proposal_finding_link_is_durably_rejected_without_queue_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); _config, state = self.fixture(root)
            finding = {"id": "finding-real", "severity": "blocking", "category": "product_intent",
                "observation": "authority gap", "expected_behavior": "human choice",
                "authority_refs": ["PLAN.md"], "candidate_evidence": ["web/example.js"]}
            proposal = {"decision_id": "D-901", "question": "Choose A or B?",
                "why_existing_authority_is_insufficient": "The approved sources do not choose.",
                "affected_requirements": ["KG-GOV-07"], "available_options": ["A", "B"],
                "observable_consequences": ["Behavior A", "Behavior B"],
                "blocking_scope": ["external publication"],
                "linked_findings": ["finding-does-not-exist"]}
            result = {"protocol": "kgnote.product-review.v1", "repository": "owner/repo",
                "pull_request": 23, "program_id": "program", "goal_id": "goal",
                "candidate_fingerprint": state["candidate_fingerprint"],
                "candidate_commit": state["candidate_commit"], "review_round": 1,
                "verdict": "PRODUCT_DECISION_REQUIRED", "findings": [finding],
                "human_decisions": [proposal], "native_ui_observed": False}
            body = (f"<!-- marker reviewed_head_sha={state['candidate_commit']} -->\n"
                    f"```json\n{json.dumps(result)}\n```")
            runner = lambda command, cwd: json.dumps([{"id": 99, "user": {"login": "owner"},
                "body": body, "state": "COMMENTED", "html_url": "https://github.com/owner/repo/pull/23#pullrequestreview-99",
                "submitted_at": "2026-10-16T00:00:00Z"}]) if "/reviews" in " ".join(command) else "[]"
            decisions_before = (root / ".ai/DECISIONS.md").read_bytes()
            with mock.patch.object(HANDOFF.external_review_control, "publication_progression_blockers", return_value=[]):
                decision = HANDOFF.process(root, runner)
            self.assertEqual(decision["status"], "REVIEW_REJECTED")
            self.assertEqual((root / ".ai/DECISIONS.md").read_bytes(), decisions_before)
            recorded = json.loads((root / ".ai/external-review-state.json").read_text())
            self.assertEqual(recorded["phase"], "EXTERNAL_PRODUCT_REVIEW_REJECTED")
            self.assertEqual(recorded["external_review"]["rejected"][0]["reason"], "semantic_invalid")

    def test_decision_projection_rolls_back_queue_when_state_commit_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); _config, state = self.fixture(root)
            proposal = {"decision_id": "D-901", "question": "Choose A or B?",
                "why_existing_authority_is_insufficient": "The approved sources do not choose.",
                "affected_requirements": ["KG-GOV-07"], "available_options": ["A", "B"],
                "observable_consequences": ["Behavior A", "Behavior B"],
                "blocking_scope": ["external publication"], "linked_findings": ["finding-choice"]}
            finding = {"id": "finding-choice", "severity": "blocking", "category": "product_intent",
                "observation": "authority gap", "expected_behavior": "human choice",
                "authority_refs": ["PLAN.md"], "candidate_evidence": ["web/example.js"]}
            result = {"protocol": "kgnote.product-review.v1", "repository": "owner/repo",
                "pull_request": 23, "program_id": "program", "goal_id": "goal",
                "candidate_fingerprint": state["candidate_fingerprint"],
                "candidate_commit": state["candidate_commit"], "review_round": 1,
                "verdict": "PRODUCT_DECISION_REQUIRED", "findings": [finding],
                "human_decisions": [proposal], "native_ui_observed": False}
            body = (f"<!-- marker reviewed_head_sha={state['candidate_commit']} -->\n"
                    f"```json\n{json.dumps(result)}\n```")
            request = {"status": "PASS", "review_id": "review-example-001",
                "candidate_revision": state["candidate_commit"] + "+worktree:" + state["candidate_fingerprint"],
                "candidate_fingerprint": state["candidate_fingerprint"]}
            runner = lambda command, cwd: json.dumps([{"id": 99, "user": {"login": "owner"},
                "body": body, "state": "COMMENTED", "html_url": "https://github.com/owner/repo/pull/23#pullrequestreview-99",
                "submitted_at": "2026-10-16T00:00:00Z"}]) if "/reviews" in " ".join(command) else "[]"
            decisions_before = (root / ".ai/DECISIONS.md").read_bytes()
            real_replace = HANDOFF.os.replace
            failed = False

            def fail_state_commit_once(source, destination):
                nonlocal failed
                if (not failed and Path(source).name == "external-review-state.json.tmp"
                        and Path(destination).name == "external-review-state.json"):
                    failed = True
                    raise OSError("simulated state commit failure")
                return real_replace(source, destination)

            with mock.patch.object(HANDOFF.external_review_control, "publication_progression_blockers", return_value=[]), \
                 mock.patch.object(HANDOFF.control, "load_review_artifacts", return_value=(request, {}, {"schema_version": "kgnote.review-decisions.v1", "protocol_version": "kgnote.review-protocol.v1", "decisions": []})), \
                 mock.patch.object(HANDOFF.os, "replace", side_effect=fail_state_commit_once):
                decision = HANDOFF.process(root, runner)
            self.assertEqual(decision["status"], "ADAPTER_REJECTED")
            self.assertEqual((root / ".ai/DECISIONS.md").read_bytes(), decisions_before)
            recorded = json.loads((root / ".ai/external-review-state.json").read_text())
            self.assertEqual(recorded["phase"], "EXTERNAL_PRODUCT_REVIEW_REJECTED")
            self.assertNotIn("pending_external_decisions", recorded)

    def test_product_decision_without_complete_proposals_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); _config, state = self.fixture(root)
            result = {"protocol": "kgnote.product-review.v1", "repository": "owner/repo",
                "pull_request": 23, "program_id": "program", "goal_id": "goal",
                "candidate_fingerprint": state["candidate_fingerprint"],
                "candidate_commit": state["candidate_commit"], "review_round": 1,
                "verdict": "PRODUCT_DECISION_REQUIRED", "findings": [],
                "native_ui_observed": False}
            body = (f"<!-- marker reviewed_head_sha={state['candidate_commit']} -->\n"
                    f"```json\n{json.dumps(result)}\n```")
            before = (root / ".ai/external-review-state.json").read_bytes()
            runner = lambda command, cwd: json.dumps([{"id": 99, "user": {"login": "owner"}, "body": body,
                "state": "COMMENTED", "html_url": "https://github.com/owner/repo/pull/23#pullrequestreview-99", "submitted_at": "2026-10-16T00:00:00Z"}]) if "/reviews" in " ".join(command) else "[]"
            with mock.patch.object(HANDOFF.external_review_control, "publication_progression_blockers", return_value=[]):
                decision = HANDOFF.process(root, runner)
            self.assertFalse(decision["accepted"])
            self.assertEqual(decision["status"], "REVIEW_REJECTED")
            self.assertNotEqual((root / ".ai/external-review-state.json").read_bytes(), before)
            recorded = json.loads((root / ".ai/external-review-state.json").read_text())
            self.assertEqual(recorded["phase"], "EXTERNAL_PRODUCT_REVIEW_REJECTED")
            self.assertFalse(recorded["external_review"]["consumer_accepted"])

    def test_marker_only_issue_comment_is_not_reused_and_exact_readback_is_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); config, state = self.fixture(root)
            decision = {"accepted": True, "verdict": "PASS", "candidate_commit": state["candidate_commit"],
                "candidate_fingerprint": state["candidate_fingerprint"], "review_round": 1, "review_author": "owner",
                "review_source": "pull_request_review", "record_id": 99, "native_ui_observed": False, "findings": []}
            marker_only = (f"<!-- KGNOTE_ISSUE8_REVIEW_RECEIPT commit={state['candidate_commit']} "
                           f"fingerprint={state['candidate_fingerprint']} round=1 -->")
            def runner(command, *, cwd):
                joined = " ".join(command)
                if "/pulls/23/reviews" in joined: return json.dumps([{"id": 99, "user": {"login": "owner"}, "body": "result", "state": "COMMENTED", "html_url": "https://github.com/owner/repo/pull/23#pullrequestreview-99", "submitted_at": "2026-10-16T00:00:00Z"}])
                if "/issues/23/comments" in joined: return "[]"
                if "/issues/8/comments" in joined and "-f" not in command:
                    return json.dumps([{"id": 1, "user": {"login": "owner"}, "body": marker_only, "html_url": "https://partial"}])
                if "/issues/8/comments" in joined: return json.dumps({"html_url": "https://created"})
                raise AssertionError(command)
            with mock.patch.object(HANDOFF.external_review_control, "publication_progression_blockers", return_value=[]), \
                 mock.patch.object(HANDOFF.consumer, "consume_records", return_value=decision):
                with self.assertRaisesRegex(RuntimeError, "exact read-back"):
                    HANDOFF.process(root, runner)
            self.assertNotIn("delivery_receipt", json.loads((root / ".ai/external-review-state.json").read_text()))

    def test_changes_required_persists_complete_external_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); _config, state = self.fixture(root)
            finding = {"id": "finding-route", "severity": "blocking", "category": "engineering",
                "observation": "broken", "expected_behavior": "repair", "authority_refs": ["PLAN.md"],
                "candidate_evidence": ["evidence"]}
            decision = {"accepted": True, "verdict": "CHANGES_REQUIRED", "candidate_commit": state["candidate_commit"],
                "candidate_fingerprint": state["candidate_fingerprint"], "review_round": 1, "review_author": "owner",
                "review_source": "issue_comment", "record_id": 77, "native_ui_observed": False, "findings": [finding]}
            def runner(command, *, cwd):
                if "/pulls/23/reviews" in " ".join(command): return "[]"
                return json.dumps([{"id": 77, "user": {"login": "owner"}, "body": "full original body",
                    "html_url": "https://github.com/owner/repo/pull/23#issuecomment-77", "created_at": "2026-10-16T01:00:00Z"}])
            with mock.patch.object(HANDOFF.external_review_control, "publication_progression_blockers", return_value=[]), \
                 mock.patch.object(HANDOFF.consumer, "consume_records", return_value=decision):
                HANDOFF.process(root, runner)
            recorded = json.loads((root / ".ai/external-review-state.json").read_text())["external_review"]
            self.assertEqual(recorded["findings"], [finding])
            self.assertEqual(recorded["blocking_findings"], ["finding-route"])
            self.assertEqual(recorded["pull_request"], 23)

    def test_missing_result_remains_waiting_without_fabricating_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); _config, _state = self.fixture(root)
            runner = lambda command, cwd: "[]"
            with mock.patch.object(HANDOFF.external_review_control, "publication_progression_blockers", return_value=[]), \
                 mock.patch.object(HANDOFF.consumer, "consume_records", return_value={"accepted": False, "status": "WAITING_FOR_PRODUCT_REVIEW"}):
                result = HANDOFF.process(root, runner)
            self.assertFalse(result["accepted"])
            self.assertNotIn("delivery_receipt", json.loads((root / ".ai/external-review-state.json").read_text()))

    def test_missing_independent_canonical_authority_is_durably_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); _config, _state = self.fixture(root)
            decisions_before = (root / ".ai/DECISIONS.md").read_bytes()
            with mock.patch.object(
                HANDOFF.external_review_control,
                "resolve_repository_canonical_authority",
                side_effect=HANDOFF.external_review_control.CanonicalAuthorityError(
                    "live PR marker mismatch"
                ),
            ), mock.patch.object(
                HANDOFF.external_review_control,
                "publication_progression_blockers",
                return_value=[],
            ):
                result = HANDOFF.process(root, lambda *_args, **_kwargs: self.fail())
            self.assertEqual("ADAPTER_REJECTED", result["status"])
            self.assertIn("canonical publication authority", result["reason"])
            self.assertEqual(decisions_before, (root / ".ai/DECISIONS.md").read_bytes())
            restored = json.loads(
                (root / ".ai/external-review-state.json").read_text()
            )
            self.assertEqual("EXTERNAL_PRODUCT_REVIEW_REJECTED", restored["phase"])
            self.assertFalse(restored["external_review"]["consumer_accepted"])


if __name__ == "__main__":
    unittest.main()
