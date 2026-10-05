from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from jsonschema import Draft202012Validator

from kgnote.contracts.reader import (
    APPLICATION_VERSION,
    QUERY_VERSION,
    ReaderValidationError,
    validate_reader_application_result,
    validate_reader_query,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "reader" / "v1"


def load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def assert_rejected(test: unittest.TestCase, function, payload, code: str) -> ReaderValidationError:
    with test.assertRaises(ReaderValidationError) as caught:
        function(payload)
    test.assertEqual(caught.exception.code, code)
    return caught.exception


class ReaderContractTests(unittest.TestCase):
    def test_schemas_are_valid_draft_2020_12(self) -> None:
        for name in ("query.schema.json", "application-result.schema.json"):
            schema = json.loads(
                (ROOT / "schemas" / "reader" / "v1" / name).read_text(encoding="utf-8")
            )
            Draft202012Validator.check_schema(schema)

    def test_bitepacer_query_and_golden_validate(self) -> None:
        query = load("bitepacer-query.json")
        golden = load("bitepacer-golden.json")
        validate_reader_query(query)
        validate_reader_application_result(golden)
        self.assertEqual(query["schema_version"], QUERY_VERSION)
        self.assertEqual(golden["schema_version"], APPLICATION_VERSION)
        self.assertEqual(golden["document"]["line_count"], 84)
        self.assertEqual(golden["document"]["byte_length"], 2141)

    def test_query_rejects_reversed_ranges_paths_and_extra_fields(self) -> None:
        query = load("bitepacer-query.json")
        query["locator"]["value"] = "L18-L3"
        assert_rejected(self, validate_reader_query, query, "reversed_line_range")

        query = load("bitepacer-query.json")
        query["path"] = "local-source-withheld"
        error = assert_rejected(self, validate_reader_query, query, "invalid_reader_query")
        self.assertNotIn("private.md", str(error))

    def test_result_detects_content_excerpt_and_reference_drift(self) -> None:
        golden = load("bitepacer-golden.json")
        golden["document"]["content"] += "changed"
        assert_rejected(self, validate_reader_application_result, golden, "byte_length_mismatch")

        golden = load("bitepacer-golden.json")
        golden["document"]["focus"]["excerpt"] = "rewritten summary"
        assert_rejected(self, validate_reader_application_result, golden, "focus_excerpt_mismatch")

        golden = load("bitepacer-golden.json")
        golden["document"]["focus"]["concept_ids"] = []
        assert_rejected(self, validate_reader_application_result, golden, "focus_reference_mismatch")

    def test_result_cannot_expose_registered_or_absolute_paths(self) -> None:
        golden = load("bitepacer-golden.json")
        original = copy.deepcopy(golden)
        validate_reader_application_result(golden)
        self.assertEqual(golden, original)
        serialized = json.dumps(golden, ensure_ascii=False)
        for forbidden in ("uri_or_path", "/private/user/", "raw/bitepacer", "file://"):
            self.assertNotIn(forbidden, serialized)


if __name__ == "__main__":
    unittest.main()
