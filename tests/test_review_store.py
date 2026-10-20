from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

import yaml

from kgnote.review import append_review, build_review_prompt


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures" / "phase0-obsidian"


class ReviewStoreTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.store = Path(self.temporary.name) / "store"
        shutil.copytree(FIXTURE, self.store)

    def tearDown(self):
        self.temporary.cleanup()

    def test_prompt_is_grounded_and_append_is_readable_and_idempotent(self):
        prompt = build_review_prompt(self.store, "concept_correlation")
        self.assertEqual(prompt.status, "ready")
        payload = prompt.payload
        self.assertEqual(payload["concept_label"], "Correlation")
        self.assertEqual(payload["activity_type"], "free_recall")
        self.assertIsNone(payload["confusion_pair"])
        self.assertGreater(len(payload["evidence_ids"]), 0)
        request = {
            "concept_id": payload["concept_id"], "question": payload["question"],
            "response": "Correlation describes co-variation; it can suggest what to investigate but cannot establish causation.",
            "hint_used": False, "outcome": "CORRECT",
            "snapshot_sha256": payload["snapshot_sha256"], "evidence_ids": payload["evidence_ids"],
        }
        timestamp = "2026-09-14T10:00:00+08:00"
        first = append_review(self.store, request, recorded_at=timestamp)
        second = append_review(self.store, request, recorded_at=timestamp)
        self.assertEqual((first.status, second.status), ("recorded", "unchanged"))
        path = self.store / "reviews" / f"{first.payload['review_id']}.md"
        text = path.read_text()
        record = yaml.safe_load(text.split("---\n", 2)[1])
        self.assertEqual(record["type"], "review_interaction")
        self.assertEqual(record["outcome"], "correct")
        self.assertFalse(record["hint_used"])
        self.assertEqual(record["evidence_ids"], payload["evidence_ids"])
        self.assertNotIn("understood", text.lower())
        reopened = build_review_prompt(self.store, "concept_correlation").payload["previous_reviews"]
        self.assertEqual(len(reopened), 1)
        self.assertEqual(reopened[0]["response"], request["response"])

    def test_stale_malformed_and_non_concept_requests_do_not_write(self):
        prompt = build_review_prompt(self.store, "concept_correlation").payload
        request = {
            "concept_id": prompt["concept_id"], "question": prompt["question"], "response": "answer",
            "hint_used": True, "outcome": "CORRECT", "snapshot_sha256": "0" * 64,
            "evidence_ids": prompt["evidence_ids"],
        }
        self.assertEqual(append_review(self.store, request).problem_code, "stale_review")
        request["snapshot_sha256"] = prompt["snapshot_sha256"]
        request["outcome"] = "UNDERSTOOD"
        self.assertEqual(append_review(self.store, request).problem_code, "invalid_assessment")
        self.assertFalse((self.store / "reviews").exists())
        self.assertEqual(build_review_prompt(self.store, "event_causality_question").status, "rejected")


if __name__ == "__main__":
    unittest.main()
