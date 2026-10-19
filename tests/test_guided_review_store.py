from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from kgnote.review import append_guided_review, build_guided_review_prompt, validate_guided_review_record


ROOT = Path(__file__).resolve().parents[1]
MODEL = json.loads((ROOT / "tests/fixtures/guided-map/v1/bitepacer-golden.json").read_text())
EDGE_ID = "edge_80042c4f448d92b2d8311f064b6189e7259615ff1c0babd38bb817adcf561c4a"


class GuidedReviewStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "guided-reviews"
        self.root.mkdir()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def request(self, response: str = "主動送出") -> dict:
        return {
            "schema_version": "kgnote.guided-review-request.v1",
            "learning_unit_id": MODEL["learning_unit"]["id"],
            "source_id": MODEL["source"]["id"],
            "graph_snapshot_sha256": MODEL["graph_snapshot_sha256"],
            "edge_id": EDGE_ID,
            "response": response,
            "hint_used": False,
        }

    def test_schemas_prompt_append_read_back_and_idempotency(self) -> None:
        for filename in ("request.schema.json", "record.schema.json"):
            schema = json.loads((ROOT / "schemas/guided-review/v1" / filename).read_text())
            Draft202012Validator.check_schema(schema)
        prompt = build_guided_review_prompt(MODEL, EDGE_ID)
        self.assertEqual(prompt.status, "ready")
        self.assertEqual(prompt.payload["canonical_sentence"], "用戶端 主動送出 HTTP 請求")
        self.assertEqual(len(prompt.payload["evidence"]), 2)
        timestamp = "2026-09-16T20:00:00+08:00"
        first = append_guided_review(self.root, MODEL, self.request(), recorded_at=timestamp)
        second = append_guided_review(self.root, MODEL, self.request(), recorded_at=timestamp)
        self.assertEqual((first.status, second.status), ("recorded", "unchanged"))
        path = self.root / "reviews" / f"{first.payload['review_id']}.md"
        record = yaml.safe_load(path.read_text().split("---\n", 2)[1])
        self.assertTrue(validate_guided_review_record(record))
        self.assertEqual(record["comparison"], "matched_reviewed_phrase")
        self.assertEqual(record["prompt_stage"], "linking_phrase_retrieval")
        self.assertEqual(record["edge_ids"], [EDGE_ID])
        self.assertEqual(len(record["evidence_ids"]), 2)
        self.assertEqual(len(record["evidence_locators"]), 2)
        self.assertEqual(record["canonical_proposition"]["linking_phrase"], "主動送出")
        self.assertNotIn("understood", path.read_text().lower())
        self.assertNotIn("mastery", path.read_text().lower())

    def test_different_phrase_is_observed_without_mastery_claim(self) -> None:
        result = append_guided_review(self.root, MODEL, self.request("傳送"), recorded_at="2026-09-16T20:01:00+08:00")
        self.assertEqual(result.status, "recorded")
        self.assertEqual(result.payload["comparison"], "different_from_reviewed_phrase")

    def test_malformed_stale_unknown_and_unsafe_roots_do_not_write(self) -> None:
        cases = []
        extra = self.request(); extra["private"] = "do not echo"; cases.append(extra)
        stale = self.request(); stale["graph_snapshot_sha256"] = "0" * 64; cases.append(stale)
        unknown = self.request(); unknown["edge_id"] = "edge_missing"; cases.append(unknown)
        empty = self.request(); empty["response"] = "  "; cases.append(empty)
        for request in cases:
            result = append_guided_review(self.root, MODEL, request)
            self.assertEqual(result.status, "rejected")
            self.assertNotIn("private", json.dumps(result.payload))
        self.assertFalse((self.root / "reviews").exists())

        missing = self.root.parent / "missing"
        self.assertEqual(append_guided_review(missing, MODEL, self.request()).problem_code, "unsafe_review_root")
        target = self.root.parent / "real"; target.mkdir()
        symlink = self.root.parent / "linked"; symlink.symlink_to(target, target_is_directory=True)
        self.assertEqual(append_guided_review(symlink, MODEL, self.request()).problem_code, "unsafe_review_root")

    def test_invalid_map_and_record_fail_closed(self) -> None:
        drift = json.loads(json.dumps(MODEL))
        drift["propositions"][0]["subject_label"] = "不同名稱"
        self.assertEqual(build_guided_review_prompt(drift, EDGE_ID).problem_code, "invalid_guided_map")
        self.assertFalse(validate_guided_review_record({"private": "value"}))


if __name__ == "__main__":
    unittest.main()
