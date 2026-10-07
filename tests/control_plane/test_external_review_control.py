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

    def test_wrong_repository_publication_fails_closed(self) -> None:
        config = {**self.config, "candidate_repository": "joannalee20050914/KGnote"}
        self.assertIn("must match", " ".join(CONTROL.repository_authority_errors(config)))

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

    def test_exact_external_pass_allows_real_human_checkpoint(self) -> None:
        self.assertEqual([], CONTROL.human_gate_blockers(self.config, self.state))
        self.assertEqual("HUMAN_CHECKPOINT_REQUIRED", CONTROL.next_machine_state(self.config, self.state))


if __name__ == "__main__":
    unittest.main()
