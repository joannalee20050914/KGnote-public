import copy
import hashlib
import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_ROOT = PROJECT_ROOT / "schemas" / "extraction" / "v1"
FIXTURE_ROOT = PROJECT_ROOT / "tests" / "fixtures" / "extraction" / "v1"
PHASE0_SOURCE = (
    PROJECT_ROOT
    / "fixtures"
    / "phase0-obsidian"
    / "raw"
    / "synthetic-causality-chat.md"
)


def load_json(path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def assign_at_path(document, path, value):
    parent = document
    for component in path[:-1]:
        parent = parent[component]
    parent[path[-1]] = value


def delete_at_path(document, path):
    parent = document
    for component in path[:-1]:
        parent = parent[component]
    del parent[path[-1]]


def apply_mutation(document, mutation):
    if mutation["op"] == "set":
        assign_at_path(document, mutation["path"], mutation["value"])
    elif mutation["op"] == "delete":
        delete_at_path(document, mutation["path"])
    else:
        raise AssertionError(f"Unknown fixture mutation: {mutation['op']}")


class ExtractionContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        definitions = load_json(SCHEMA_ROOT / "definitions.schema.json")
        cls.schemas = {
            "input": load_json(SCHEMA_ROOT / "input.schema.json"),
            "output": load_json(SCHEMA_ROOT / "output.schema.json"),
        }
        registry = Registry().with_resource(
            definitions["$id"], Resource.from_contents(definitions)
        )
        cls.validators = {
            name: Draft202012Validator(
                schema,
                registry=registry,
                format_checker=FormatChecker(),
            )
            for name, schema in cls.schemas.items()
        }
        cls.valid_payloads = {
            "input": load_json(FIXTURE_ROOT / "valid" / "input.json"),
            "output": load_json(FIXTURE_ROOT / "valid" / "output.json"),
        }

    def test_schema_documents_are_valid_draft_2020_12(self):
        definitions = load_json(SCHEMA_ROOT / "definitions.schema.json")
        Draft202012Validator.check_schema(definitions)
        for schema in self.schemas.values():
            Draft202012Validator.check_schema(schema)

    def test_valid_fixtures_match_exact_schemas(self):
        for name, payload in self.valid_payloads.items():
            with self.subTest(schema=name):
                self.validators[name].validate(payload)

    def test_malformed_cases_fail_at_expected_path_and_keyword(self):
        cases = load_json(FIXTURE_ROOT / "invalid" / "cases.json")
        self.assertGreaterEqual(len(cases), 18)

        for case in cases:
            with self.subTest(case=case["name"]):
                payload = copy.deepcopy(self.valid_payloads[case["schema"]])
                mutations = case.get("mutations", [case.get("mutation")])
                for mutation in mutations:
                    apply_mutation(payload, mutation)

                errors = list(self.validators[case["schema"]].iter_errors(payload))
                expected = case["expected"]
                matching = [
                    error
                    for error in errors
                    if error.validator == expected["validator"]
                    and list(error.absolute_path) == expected["path"]
                ]
                self.assertTrue(
                    matching,
                    msg=(
                        f"{case['name']} did not fail as expected; got "
                        f"{[(error.validator, list(error.absolute_path)) for error in errors]}"
                    ),
                )

    def test_valid_output_refs_resolve_within_payload(self):
        output = self.valid_payloads["output"]
        refs_by_kind = {
            "concept": {item["local_ref"] for item in output["concepts"]},
            "evidence": {item["local_ref"] for item in output["evidence"]},
            "learning_event": {
                item["local_ref"] for item in output["learning_events"]
            },
        }

        for concept in output["concepts"]:
            self.assertLessEqual(set(concept["evidence_refs"]), refs_by_kind["evidence"])
        for event in output["learning_events"]:
            self.assertLessEqual(set(event["concept_refs"]), refs_by_kind["concept"])
            self.assertLessEqual(set(event["evidence_refs"]), refs_by_kind["evidence"])
        for edge in output["edges"]:
            self.assertLessEqual(set(edge["evidence_refs"]), refs_by_kind["evidence"])

    def test_input_output_preserve_source_and_locator_provenance(self):
        extraction_input = self.valid_payloads["input"]
        output = self.valid_payloads["output"]
        source_id = extraction_input["source"]["id"]

        self.assertEqual(output["source_id"], source_id)
        self.assertTrue(PHASE0_SOURCE.is_file())
        self.assertEqual(
            extraction_input["source"]["content"],
            PHASE0_SOURCE.read_text(encoding="utf-8"),
        )
        self.assertEqual(
            extraction_input["source"]["content_sha256"],
            hashlib.sha256(
                extraction_input["source"]["content"].encode("utf-8")
            ).hexdigest(),
        )
        for evidence in output["evidence"]:
            self.assertEqual(evidence["source_id"], source_id)
            self.assertEqual(evidence["locator"]["kind"], "line_range")
            self.assertRegex(evidence["locator"]["value"], r"^L\d+(?:-L\d+)?$")
        for event in output["learning_events"]:
            self.assertEqual(event["source_id"], source_id)

    def test_candidate_output_has_no_canonical_or_proficiency_fields(self):
        output = self.valid_payloads["output"]
        forbidden_fields = {"understood", "mastered", "proficiency"}
        candidate_ref_fields = {
            "local_ref",
            "source_ref",
            "target_ref",
            "concept_refs",
            "evidence_refs",
        }
        canonical_prefixes = ("concept_", "evidence_", "event_", "edge_")

        def inspect(value, field_name=None):
            if isinstance(value, dict):
                self.assertTrue(forbidden_fields.isdisjoint(value))
                for key, child in value.items():
                    inspect(child, key)
            elif isinstance(value, list):
                for child in value:
                    inspect(child, field_name)
            elif field_name in candidate_ref_fields and isinstance(value, str):
                self.assertFalse(value.startswith(canonical_prefixes), value)

        inspect(output)


if __name__ == "__main__":
    unittest.main()
