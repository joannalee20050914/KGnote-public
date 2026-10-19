from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import external_review_control as CONTROL  # noqa: E402


class ExternalReviewControlTests(unittest.TestCase):
    def setUp(self) -> None:
        repository = "joannalee20050914/KGnote-public"
        self.config = {
            "enabled": True,
            "canonical_repository": repository,
            "candidate_repository": repository,
            "trigger_repository": repository,
            "review_request_repository": repository,
            "archive_repository": "joannalee20050914/KGnote",
            "review_pr_number": 1,
            "trigger_events": ["pull_request.synchronize", "issue_comment.created"],
            "trigger_comment_template": "@kgnote-ai-review {candidate_commit}",
        }
        self.state = {
            **{field: repository for field in CONTROL.ACTIVE_REPOSITORY_FIELDS},
            "archive_repository": "joannalee20050914/KGnote",
            "pull_request": 1,
            "candidate_commit": "a" * 40,
            "candidate_fingerprint": "b" * 64,
            "internal_review": {"status": "PASS", "artifact": ".ai/REVIEW_RESULT.md"},
            "publication": {"status": "PUBLISHED", "remote_head": "a" * 40},
            "external_review": {
                "status": "PASS",
                "reviewed_commit": "a" * 40,
                "reviewed_fingerprint": "b" * 64,
                "artifact_url": "https://github.example/review/1",
                "blocking_findings": [],
            },
        }
        self.state["publication"].update({
            "repository": repository,
            "pull_request": 1,
            "candidate_fingerprint": "b" * 64,
            "request_marker": "REQUEST_V2",
            "artifact_url": "https://github.example/pr/1",
            "trigger_comment": "@kgnote-ai-review " + "a" * 40,
            "trigger_artifact_url": "https://github.example/pr/1#issuecomment-1",
        })
        self.config["request_marker"] = "REQUEST_V2"

    def final_checkpoint(self) -> dict:
        return {
            "gate_id": CONTROL.FINAL_HUMAN_GATE_ID,
            "status": "READY",
            "candidate_scope": "COMPLETE_PRODUCT_DELIVERY",
            "candidate_commit": "a" * 40,
            "candidate_fingerprint": "b" * 64,
            "approved_required_scope_complete": True,
            "required_features_complete": True,
            "dependencies_complete": True,
            "cross_module_integration_complete": True,
            "required_scenarios_complete": True,
            "delivery_evidence_complete": True,
            "no_known_delivery_blockers": True,
            "rc_evidence_complete": True,
            "independent_review_complete": True,
            "integrated_verification_complete": True,
            "trial_entrypoint": "kgnote://final-candidate",
            "formal_human_acceptance_status": "NOT_EVALUATED",
            "authority_refs": [
                "docs/requirements/PERSONAL_ALPHA_INTEGRATED_STAGE_DIRECTION_20260927.md",
                "https://github.com/joannalee20050914/KGnote-public/issues/21",
            ],
        }

    def test_wrong_repository_publication_fails_closed(self) -> None:
        config = {**self.config, "candidate_repository": "joannalee20050914/KGnote"}
        self.assertIn("must match", " ".join(CONTROL.repository_authority_errors(config)))

    def test_trigger_payload_and_event_must_match_saved_task_contract(self) -> None:
        wrong_payload = {**self.config, "trigger_comment_template": "@kgnote-ai-review {candidate_commit} extra"}
        self.assertIn("trigger comment template", " ".join(CONTROL.repository_authority_errors(wrong_payload)))
        missing_event = {**self.config, "trigger_events": ["pull_request.synchronize"]}
        self.assertIn("issue-comment trigger", " ".join(CONTROL.repository_authority_errors(missing_event)))

    def test_missing_external_review_artifact_blocks_human_gate(self) -> None:
        state = copy.deepcopy(self.state)
        state["external_review"]["artifact_url"] = None
        self.assertIn("artifact is missing", " ".join(CONTROL.human_gate_blockers(self.config, state)))

    def test_internal_pass_without_external_pass_blocks_human_gate(self) -> None:
        state = copy.deepcopy(self.state)
        state["external_review"] = {"status": "PENDING", "artifact_url": None, "blocking_findings": []}
        self.assertNotEqual("HUMAN_CHECKPOINT_REQUIRED", CONTROL.next_machine_state(self.config, state))

    def test_external_changes_required_returns_to_repair(self) -> None:
        state = copy.deepcopy(self.state)
        state["external_review"]["status"] = "CHANGES_REQUIRED"
        state["external_review"]["blocking_findings"] = ["KG-SEM-001"]
        self.assertEqual("REPAIRING_EXTERNAL_FINDINGS", CONTROL.next_machine_state(self.config, state))

    def test_repository_migration_split_brain_is_authority_conflict(self) -> None:
        config = {**self.config, "trigger_repository": "joannalee20050914/KGnote"}
        self.assertEqual("AUTHORITY_CONFLICT", CONTROL.next_machine_state(config, self.state))

    def test_premature_human_transition_requires_exact_external_pass(self) -> None:
        state = copy.deepcopy(self.state)
        state["external_review"]["reviewed_commit"] = "c" * 40
        blockers = CONTROL.human_gate_blockers(self.config, state)
        self.assertTrue(any("exact candidate commit" in blocker for blocker in blockers))
        self.assertNotEqual("HUMAN_CHECKPOINT_REQUIRED", CONTROL.next_machine_state(self.config, state))

    def test_exact_component_pass_does_not_imply_human_checkpoint(self) -> None:
        self.assertEqual([], CONTROL.external_review_blockers(self.config, self.state))
        self.assertTrue(CONTROL.human_gate_blockers(self.config, self.state))
        self.assertEqual("COMPONENT_REVIEW_COMPLETE", CONTROL.next_machine_state(self.config, self.state))

    def test_exact_external_pass_allows_only_complete_final_candidate(self) -> None:
        self.state["human_checkpoint"] = self.final_checkpoint()
        self.assertEqual([], CONTROL.human_gate_blockers(self.config, self.state))
        self.assertEqual(
            "FINAL_HUMAN_ACCEPTANCE_REQUIRED",
            CONTROL.next_machine_state(self.config, self.state),
        )

    def test_legacy_or_partial_checkpoint_is_superseded_and_does_not_stop(self) -> None:
        self.state["human_checkpoint"] = {
            "status": "READY",
            "candidate_scope": "INTEGRATED_CANDIDATE",
            "gate_ids": ["PA-HUMAN-1", "NS-HUMAN-SMOKE"],
            "dependencies_complete": True,
            "required_evidence_complete": True,
            "concentrated_trial_ready": True,
        }
        self.assertEqual("COMPONENT_REVIEW_COMPLETE", CONTROL.next_machine_state(self.config, self.state))

    def test_every_final_prerequisite_and_exact_identity_is_required(self) -> None:
        for field in (
            "required_features_complete",
            "cross_module_integration_complete",
            "required_scenarios_complete",
            "delivery_evidence_complete",
            "no_known_delivery_blockers",
            "rc_evidence_complete",
            "independent_review_complete",
            "integrated_verification_complete",
        ):
            with self.subTest(field=field):
                state = copy.deepcopy(self.state)
                state["human_checkpoint"] = self.final_checkpoint()
                state["human_checkpoint"][field] = False
                self.assertEqual("COMPONENT_REVIEW_COMPLETE", CONTROL.next_machine_state(self.config, state))
        state = copy.deepcopy(self.state)
        state["human_checkpoint"] = self.final_checkpoint()
        state["human_checkpoint"]["formal_human_acceptance_status"] = "PASS"
        self.assertEqual("COMPONENT_REVIEW_COMPLETE", CONTROL.next_machine_state(self.config, state))

    def test_exact_publication_readback_allows_publish_progression(self) -> None:
        self.assertEqual([], CONTROL.publication_progression_blockers(self.config, self.state))

    def test_publication_readback_fails_for_wrong_repo_stale_head_or_missing_marker(self) -> None:
        for field, value in (
            ("repository", "joannalee20050914/KGnote"),
            ("remote_head", "c" * 40),
            ("candidate_fingerprint", "d" * 64),
            ("request_marker", None),
            ("trigger_comment", "@kgnote-ai-review wrong"),
        ):
            with self.subTest(field=field):
                state = copy.deepcopy(self.state)
                state["publication"][field] = value
                blockers = CONTROL.publication_progression_blockers(self.config, state)
                self.assertTrue(any(field in blocker for blocker in blockers))

        state = copy.deepcopy(self.state)
        state["publication"]["trigger_artifact_url"] = None
        self.assertIn(
            "event-trigger artifact URL",
            " ".join(CONTROL.publication_progression_blockers(self.config, state)),
        )

    def test_pending_or_failed_publication_cannot_complete_milestone(self) -> None:
        state = copy.deepcopy(self.state)
        state["publication"]["status"] = "PENDING"
        self.assertIn("not published", " ".join(CONTROL.publication_progression_blockers(self.config, state)))


if __name__ == "__main__":
    unittest.main()
