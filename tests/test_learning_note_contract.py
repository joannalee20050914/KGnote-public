from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from kgnote.contracts import LearningNoteValidationError, validate_learning_note


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "learning-note" / "v1"


class LearningNoteContractTests(unittest.TestCase):
    def test_schemas_are_valid_draft_2020_12(self) -> None:
        for path in sorted((ROOT / "schemas" / "learning-note" / "v1").glob("*.schema.json")):
            with self.subTest(schema=path.name):
                Draft202012Validator.check_schema(json.loads(path.read_text(encoding="utf-8")))

    def test_versioned_fixture_is_valid(self) -> None:
        note = json.loads((FIXTURE / "valid" / "note.json").read_text(encoding="utf-8"))
        validate_learning_note(note)

    def test_malformed_fixtures_fail_closed_with_stable_codes(self) -> None:
        valid = json.loads((FIXTURE / "valid" / "note.json").read_text(encoding="utf-8"))
        cases = json.loads((FIXTURE / "invalid" / "cases.json").read_text(encoding="utf-8"))
        for case in cases:
            with self.subTest(case=case["name"]):
                note = copy.deepcopy(valid)
                note.update(case.get("patch", {}))
                if case.get("anchor_locator"):
                    note["source_anchors"][0]["locator"]["value"] = case["anchor_locator"]
                if case.get("duplicate_anchor"):
                    note["source_anchors"].append(copy.deepcopy(note["source_anchors"][0]))
                with self.assertRaises(LearningNoteValidationError) as raised:
                    validate_learning_note(note)
                self.assertEqual(raised.exception.code, case["code"])


if __name__ == "__main__":
    unittest.main()
