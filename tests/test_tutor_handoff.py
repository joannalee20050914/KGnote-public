from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from kgnote.learning import (
    build_manual_tutor_handoff, import_manual_tutor_delta, make_manual_tutor_delta,
    render_manual_tutor_handoff, validate_manual_tutor_delta,
)


def resume_context() -> dict:
    return {
        "learning_unit_id": "unit_git", "source_scope": {"source_id": "src_git_basics", "locator": "L10-L18"},
        "structural_breadcrumb": [{"node_id": "git", "title": "Git"}, {"node_id": "worktree", "title": "worktree"}],
        "selected": {"kind": "structure", "id": "worktree", "label": "worktree"},
        "unresolved_question": "branch 和 worktree 在這個操作中各自負責什麼？",
    }


class TutorHandoffTests(unittest.TestCase):
    def test_copy_safe_manual_handoff_and_delta_round_trip_deduplicates(self) -> None:
        handoff_result = build_manual_tutor_handoff(
            resume_context=resume_context(),
            evidence=[{"source_id": "src_git_basics", "locator": "L10-L18", "proposition": "Learner asked about branch and worktree; the exact distinction remains unresolved."}],
        )
        self.assertEqual(handoff_result.status, "ready")
        handoff = handoff_result.payload["handoff"]
        copied = render_manual_tutor_handoff(handoff)
        self.assertTrue(copied.startswith("```kgnote-manual-tutor-handoff\n"))
        self.assertNotIn("cookie", copied.lower())
        self.assertNotIn("api_key", copied.lower())
        self.assertIn("not_requested", copied)

        delta_result = make_manual_tutor_delta(
            handoff_id=handoff["handoff_id"], recorded_at="2026-10-19T08:00:00Z",
            observations=[{"kind": "clarification", "text": "A branch names a line of development; a worktree is a separate checkout.", "evidence_refs": ["src_git_basics:L10-L18"]}],
        )
        self.assertEqual(delta_result.status, "ready")
        delta = json.loads(json.dumps(delta_result.payload["delta"]))  # exact manual copy/paste round trip
        self.assertIsNone(validate_manual_tutor_delta(delta))
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.assertEqual(import_manual_tutor_delta(root, delta).status, "imported")
            self.assertEqual(import_manual_tutor_delta(root, delta).status, "unchanged")
            paths = list((root / "manual-tutor-deltas").glob("*.json"))
            self.assertEqual(len(paths), 1)
            self.assertEqual(json.loads(paths[0].read_text()), delta)

    def test_tampered_delta_and_automatic_provider_claim_are_rejected(self) -> None:
        handoff = build_manual_tutor_handoff(resume_context=resume_context(), evidence=[{"source_id": "src_git_basics", "locator": "L10-L18", "proposition": "Unresolved distinction."}]).payload["handoff"]
        delta = make_manual_tutor_delta(handoff_id=handoff["handoff_id"], recorded_at="2026-10-19T08:00:00Z", observations=[{"kind": "question", "text": "How does this affect a shared repository?", "evidence_refs": ["src_git_basics:L10-L18"]}]).payload["delta"]
        delta["imported_via"] = "automatic_provider"
        with tempfile.TemporaryDirectory() as temporary:
            rejected = import_manual_tutor_delta(temporary, delta)
        self.assertEqual((rejected.status, rejected.problem_code), ("rejected", "invalid_delta_identity"))


if __name__ == "__main__":
    unittest.main()
