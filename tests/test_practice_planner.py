from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from kgnote.review import build_practice_set, reveal_practice_answer, validate_attempt_against_practice_set


ROOT = Path(__file__).resolve().parents[1]
MODEL = json.loads((ROOT / "web/fixtures/os-overview-guided-map.json").read_text())
OVERLAY = json.loads((ROOT / "web/fixtures/os-overview-claim-review-overlay.json").read_text())


class PracticePlannerTests(unittest.TestCase):
    def test_claim_review_overlay_schema_and_fixture_validate(self) -> None:
        schema = json.loads((ROOT / "schemas/claim-review-overlay/v1/overlay.schema.json").read_text())
        Draft202012Validator.check_schema(schema)
        self.assertEqual(list(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(OVERLAY)), [])

    def test_disputed_interrupt_driver_claim_remains_readable_but_never_becomes_item(self) -> None:
        result = build_practice_set(MODEL, OVERLAY)
        self.assertEqual(result.status, "ready")
        self.assertEqual(len(result.payload["items"]), 18)
        self.assertFalse(any("interrupt_driver" in item["item_id"] for item in result.payload["items"]))
        self.assertEqual(result.payload["blocked_claims"][0]["claim_id"], "edge_os_interrupt_driver")
        source_before = (ROOT / "web/fixtures/os-overview-review.md").read_bytes()
        self.assertIn("evidence_os_interrupt", {item["id"] for item in MODEL["evidence"]})
        self.assertEqual(source_before, (ROOT / "web/fixtures/os-overview-review.md").read_bytes())

    def test_pre_submit_items_contain_no_answers_evidence_or_source_excerpt(self) -> None:
        result = build_practice_set(MODEL, OVERLAY)
        serialized = json.dumps(result.payload["items"], ensure_ascii=False)
        for forbidden in ("canonical_answer", "canonical_sentence", "source_excerpt", "linking_phrase", "向核心提出"):
            self.assertNotIn(forbidden, serialized)
        reveal = reveal_practice_answer(MODEL, OVERLAY, "item_relation_edge_os_application_system_call")
        self.assertEqual(reveal.status, "ready")
        self.assertIn("向核心提出", reveal.payload["canonical_answer"])
        self.assertEqual(reveal.payload["evidence"][0]["locator"]["value"], "L22-L26")

    def test_stale_or_malformed_overlay_blocks_planning_without_blocking_source(self) -> None:
        stale = copy.deepcopy(OVERLAY)
        stale["graph_snapshot_sha256"] = "0" * 64
        self.assertEqual(build_practice_set(MODEL, stale).problem_code, "invalid_or_stale_claim_review_overlay")
        malformed = copy.deepcopy(OVERLAY)
        malformed["reviews"][0]["factual_status"] = "accepted"
        self.assertEqual(build_practice_set(MODEL, malformed).status, "rejected")
        self.assertTrue((ROOT / "web/fixtures/os-overview-review.md").is_file())

    def test_attempt_refs_must_match_current_item_revision_and_provenance(self) -> None:
        item = build_practice_set(MODEL, OVERLAY).payload["items"][0]
        request = {
            "review_item_id": item["item_id"], "item_revision": item["revision"],
            "learning_unit_id": item["learning_unit_id"], "activity_type": item["activity_type"],
            "source_refs": item["source_refs"], "claim_refs": [item["claim_ref"]], "evidence_refs": item["evidence_refs"],
        }
        self.assertIsNone(validate_attempt_against_practice_set(MODEL, OVERLAY, request))
        request["evidence_refs"] = ["stale_evidence"]
        self.assertEqual(validate_attempt_against_practice_set(MODEL, OVERLAY, request), "stale_practice_item")


if __name__ == "__main__":
    unittest.main()
