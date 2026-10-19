import copy
import json
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from kgnote.extraction import replay_extraction_response
from kgnote.ingestion import SourceMetadata, import_markdown_source
from kgnote.pipeline import build_candidate_import_preview, build_import_review_preview


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "fixtures/phase0-obsidian/raw/synthetic-causality-chat.md"
RAW_RESPONSE = ROOT / "tests/fixtures/extraction/v1/valid/raw_response.json"
SCHEMA = ROOT / "schemas/import-review/v1/preview.schema.json"
DIRECTORIES = ("sources", "concepts", "evidence", "learning-events", "edges", "raw")


class ImportReviewPreviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.extraction_input = import_markdown_source(SOURCE, metadata=SourceMetadata(
            source_id="src_synthetic_causality_chat", source_kind="chatgpt_conversation",
            title="Synthetic causality learning conversation", captured_at=None,
            locator_basis="line_range",
        ))
        attempt = replay_extraction_response(
            extraction_input=cls.extraction_input,
            raw_response=RAW_RESPONSE.read_text(),
            extractor_version="test-extractor.v1",
            generated_at="2026-09-16T12:00:00+08:00",
        )
        cls.candidate = attempt.candidate_result
        cls.schema = json.loads(SCHEMA.read_text())

    def build(self, store, candidate=None):
        preview = build_candidate_import_preview(
            extraction_input=self.extraction_input,
            candidate_result=candidate or self.candidate,
            generated_at="2026-09-16T12:00:00+08:00",
            store_root=store,
        )
        return preview, build_import_review_preview(
            extraction_input=self.extraction_input,
            candidate_result=candidate or self.candidate,
            import_preview=preview,
        )

    def test_schema_names_directions_and_exact_excerpts_are_human_readable(self):
        Draft202012Validator.check_schema(self.schema)
        with tempfile.TemporaryDirectory() as temporary:
            store = Path(temporary)
            for name in DIRECTORIES:
                (store / name).mkdir()
            _, result = self.build(store)
        Draft202012Validator(self.schema).validate(result)
        self.assertEqual(result["summary"], {
            "concepts": 4, "evidence": 2, "relationships": 3, "learning_events": 1,
            "conflicts": 0, "rejects": 0, "apply_blocked": False,
        })
        relation = next(item for item in result["relationships"] if item["relation"] == "contrasts_with")
        self.assertEqual(relation["subject"]["label"], "Correlation")
        self.assertEqual(relation["object"]["label"], "Causation")
        self.assertIsNone(relation["linking_phrase"])
        self.assertEqual(relation["linking_phrase_status"], "not_proposed")
        self.assertEqual(relation["source_excerpts"][0]["locator"], "L5-L7")
        self.assertEqual([line["number"] for line in relation["source_excerpts"][0]["lines"]], [5, 6, 7])

    def test_preview_is_deterministic_copy_safe_and_does_not_invent_mastery(self):
        original_input = copy.deepcopy(self.extraction_input)
        original_candidate = copy.deepcopy(self.candidate)
        with tempfile.TemporaryDirectory() as temporary:
            store = Path(temporary)
            for name in DIRECTORIES:
                (store / name).mkdir()
            _, first = self.build(store)
            _, second = self.build(store)
        self.assertEqual(first, second)
        first["concepts"][0]["name"] = "mutated"
        self.assertNotEqual(first, second)
        self.assertEqual(self.extraction_input, original_input)
        self.assertEqual(self.candidate, original_candidate)
        def keys(value):
            if isinstance(value, dict):
                return set(value) | set().union(*(keys(item) for item in value.values()))
            if isinstance(value, list):
                return set().union(*(keys(item) for item in value)) if value else set()
            return set()
        self.assertNotIn("mastery", keys(second))
        self.assertNotIn("understood", keys(second))

    def test_out_of_bounds_candidate_locator_is_rejected_before_store_read(self):
        candidate = copy.deepcopy(self.candidate)
        candidate["evidence"][0]["locator"]["value"] = "L5-L999"
        with tempfile.TemporaryDirectory() as temporary:
            store = Path(temporary)
            for name in DIRECTORIES:
                (store / name).mkdir()
            preview = build_candidate_import_preview(
                extraction_input=self.extraction_input, candidate_result=candidate,
                generated_at="2026-09-16T12:00:00+08:00", store_root=store,
            )
        self.assertEqual(preview.status, "rejected")
        self.assertEqual(preview.problem_code, "source_locator_out_of_bounds")

    def test_conflicts_are_explicit_and_block_apply_review(self):
        preview = build_candidate_import_preview(
            extraction_input=self.extraction_input, candidate_result=self.candidate,
            generated_at="2026-09-16T12:00:00+08:00",
            store_root=ROOT / "fixtures/phase0-obsidian",
        )
        result = build_import_review_preview(
            extraction_input=self.extraction_input,
            candidate_result=self.candidate,
            import_preview=preview,
        )
        self.assertTrue(result["summary"]["apply_blocked"])
        self.assertGreaterEqual(result["summary"]["conflicts"], 1)
        self.assertTrue(result["blocking_items"])
        self.assertTrue(all(item["operation"] in {"CONFLICT", "REJECT"} for item in result["blocking_items"]))


if __name__ == "__main__":
    unittest.main()
