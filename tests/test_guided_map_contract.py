from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from jsonschema import Draft202012Validator

from kgnote.contracts.guided_map import (
    GuidedMapValidationError,
    READ_MODEL_SCHEMA_VERSION,
    SPEC_SCHEMA_VERSION,
    validate_guided_map_read_model,
    validate_guided_map_spec,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "guided-map" / "v1"


def load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def assert_rejected(
    test: unittest.TestCase, function, payload: dict, code: str
) -> GuidedMapValidationError:
    with test.assertRaises(GuidedMapValidationError) as caught:
        function(payload)
    test.assertEqual(caught.exception.code, code)
    return caught.exception


class GuidedMapContractTests(unittest.TestCase):
    def test_both_schemas_are_valid_draft_2020_12(self) -> None:
        for name in ("guided-map-spec.schema.json", "guided-map-read-model.schema.json"):
            with self.subTest(name=name):
                schema = json.loads(
                    (ROOT / "schemas" / "guided-map" / "v1" / name).read_text(encoding="utf-8")
                )
                Draft202012Validator.check_schema(schema)

    def test_bitepacer_spec_and_golden_validate(self) -> None:
        spec = load("bitepacer-spec.json")
        golden = load("bitepacer-golden.json")
        validate_guided_map_spec(spec)
        validate_guided_map_read_model(golden)
        self.assertEqual(spec["schema_version"], SPEC_SCHEMA_VERSION)
        self.assertEqual(golden["schema_version"], READ_MODEL_SCHEMA_VERSION)
        self.assertEqual(len(golden["groups"]), 5)
        self.assertEqual(len(golden["concepts"]), 9)
        self.assertEqual(len(golden["propositions"]), 7)
        self.assertEqual(len(golden["evidence"]), 5)
        serialized = json.dumps(golden, ensure_ascii=False)
        for forbidden in ("uri_or_path", "raw_markdown", "/private/user/", "understood"):
            self.assertNotIn(forbidden, serialized)

    def test_spec_rejects_duplicate_grouping_generic_phrases_and_unstable_order(self) -> None:
        spec = load("bitepacer-spec.json")
        spec["groups"][1]["concept_ids"].append(spec["groups"][0]["concept_ids"][0])
        spec["groups"][1]["concept_ids"].sort()
        assert_rejected(self, validate_guided_map_spec, spec, "concept_in_multiple_groups")

        spec = load("bitepacer-spec.json")
        spec["teaching_propositions"][0]["linking_phrase"] = "相關"
        assert_rejected(self, validate_guided_map_spec, spec, "generic_linking_phrase")

        spec = load("bitepacer-spec.json")
        spec["teaching_propositions"].reverse()
        assert_rejected(self, validate_guided_map_spec, spec, "non_deterministic_order")

    def test_read_model_rejects_group_nodes_label_drift_and_extra_evidence(self) -> None:
        golden = load("bitepacer-golden.json")
        golden["concepts"][0]["id"] = golden["groups"][0]["id"]
        assert_rejected(self, validate_guided_map_read_model, golden, "invalid_guided_map_read_model")

        golden = load("bitepacer-golden.json")
        golden["propositions"][0]["subject_label"] = "另一個名稱"
        assert_rejected(self, validate_guided_map_read_model, golden, "proposition_label_mismatch")

        golden = load("bitepacer-golden.json")
        golden["propositions"][0]["linking_phrase"] = "related_to"
        assert_rejected(self, validate_guided_map_read_model, golden, "generic_linking_phrase")

        golden = load("bitepacer-golden.json")
        golden["propositions"][0]["projection_version"] = "manual.other.v1"
        assert_rejected(self, validate_guided_map_read_model, golden, "projection_version_mismatch")

        golden = load("bitepacer-golden.json")
        extra = copy.deepcopy(golden["evidence"][0])
        extra["id"] = "evidence_unused"
        golden["evidence"].append(extra)
        assert_rejected(self, validate_guided_map_read_model, golden, "evidence_set_does_not_match_propositions")

    def test_validation_is_read_only_and_errors_do_not_echo_content(self) -> None:
        spec = load("bitepacer-spec.json")
        original = copy.deepcopy(spec)
        validate_guided_map_spec(spec)
        self.assertEqual(spec, original)

        secret = "do-not-echo-private-teaching-content"
        spec["focus_question"] = secret
        spec["unexpected"] = secret
        error = assert_rejected(self, validate_guided_map_spec, spec, "invalid_guided_map_spec")
        self.assertNotIn(secret, str(error))


if __name__ == "__main__":
    unittest.main()
