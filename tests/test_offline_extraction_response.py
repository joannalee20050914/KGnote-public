import copy
import hashlib
import json
import socket
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest import mock

from kgnote.contracts.extraction import ExtractionInputValidationError
from kgnote.extraction import replay_extraction_response


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = PROJECT_ROOT / "tests" / "fixtures" / "extraction" / "v1" / "valid"
PHASE0_VAULT = PROJECT_ROOT / "fixtures" / "phase0-obsidian"


def load_json(path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def tree_digest(root):
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        digest.update(str(path.relative_to(root)).encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


class OfflineExtractionResponseTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.extraction_input = load_json(FIXTURE_ROOT / "input.json")
        cls.raw_response = (FIXTURE_ROOT / "raw_response.json").read_text(
            encoding="utf-8"
        )
        cls.expected_output = load_json(FIXTURE_ROOT / "output.json")

    def replay(self, raw_response=None, **overrides):
        arguments = {
            "extraction_input": self.extraction_input,
            "raw_response": self.raw_response if raw_response is None else raw_response,
            "extractor_version": "fixture-replay.v1",
            "generated_at": "2026-09-07T00:00:00+08:00",
        }
        arguments.update(overrides)
        return replay_extraction_response(**arguments)

    def mutated_response(self, mutate):
        body = json.loads(self.raw_response)
        mutate(body)
        return json.dumps(body, ensure_ascii=False)

    def test_valid_response_is_accepted_with_adapter_owned_provenance(self):
        attempt = self.replay()

        self.assertEqual(attempt.status, "accepted")
        self.assertIsNone(attempt.rejection)
        self.assertEqual(attempt.raw_response, self.raw_response)
        self.assertEqual(
            attempt.raw_response_sha256,
            hashlib.sha256(self.raw_response.encode("utf-8")).hexdigest(),
        )
        self.assertEqual(attempt.candidate_result, self.expected_output)
        for evidence in attempt.candidate_result["evidence"]:
            self.assertEqual(evidence["source_id"], self.extraction_input["source"]["id"])
        for event in attempt.candidate_result["learning_events"]:
            self.assertEqual(event["source_id"], self.extraction_input["source"]["id"])

    def test_attempt_is_immutable_and_repr_does_not_expose_raw_response(self):
        attempt = self.replay()
        first_result = attempt.candidate_result
        first_result["concepts"].clear()

        self.assertEqual(attempt.candidate_result, self.expected_output)
        with self.assertRaises(FrozenInstanceError):
            attempt.status = "rejected"
        self.assertNotIn(self.raw_response[:40], repr(attempt))

    def test_accepted_and_rejected_replay_are_deterministic(self):
        self.assertEqual(self.replay(), self.replay())
        invalid = "PRIVATE_RESPONSE_MARKER {"
        self.assertEqual(self.replay(invalid), self.replay(invalid))

    def test_invalid_json_variants_are_rejected_safely(self):
        cases = {
            "syntax": "PRIVATE_RESPONSE_MARKER {",
            "duplicate_key": '{"concepts": [], "concepts": [], "evidence": [], "learning_events": [], "edges": []}',
            "nan": '{"concepts": [], "evidence": [], "learning_events": [], "edges": [], "x": NaN}',
        }
        for name, raw_response in cases.items():
            with self.subTest(case=name):
                attempt = self.replay(raw_response)
                self.assert_rejected(attempt, "invalid_json", (), "json_parse")
                self.assertEqual(attempt.raw_response, raw_response)
                self.assertEqual(
                    attempt.raw_response_sha256,
                    hashlib.sha256(raw_response.encode("utf-8")).hexdigest(),
                )
                self.assertNotIn("PRIVATE_RESPONSE_MARKER", repr(attempt))
                self.assertNotIn("PRIVATE_RESPONSE_MARKER", repr(attempt.rejection))

    def test_root_and_collection_shape_failures_are_rejected(self):
        non_object = self.replay("[]")
        self.assert_rejected(non_object, "non_object_root", (), "type")

        missing = self.replay(
            self.mutated_response(lambda body: body.pop("concepts"))
        )
        self.assert_rejected(
            missing, "missing_candidate_collection", ("concepts",), "required"
        )

        unknown = self.replay(
            self.mutated_response(lambda body: body.update({"prompt": "private"}))
        )
        self.assert_rejected(
            unknown, "unknown_response_field", ("prompt",), "additionalProperties"
        )

    def test_model_cannot_supply_adapter_owned_fields(self):
        cases = [
            (
                "top_level_source_id",
                lambda body: body.update({"source_id": "src_attacker"}),
                ("source_id",),
            ),
            (
                "top_level_schema_version",
                lambda body: body.update(
                    {"schema_version": "kgnote.extraction-output.attacker"}
                ),
                ("schema_version",),
            ),
            (
                "top_level_extractor_version",
                lambda body: body.update({"extractor_version": "attacker"}),
                ("extractor_version",),
            ),
            (
                "top_level_generated_at",
                lambda body: body.update(
                    {"generated_at": "2000-01-01T00:00:00Z"}
                ),
                ("generated_at",),
            ),
            (
                "evidence",
                lambda body: body["evidence"][0].update({"source_id": "src_attacker"}),
                ("evidence", 0, "source_id"),
            ),
            (
                "learning_event",
                lambda body: body["learning_events"][0].update(
                    {"source_id": "src_attacker"}
                ),
                ("learning_events", 0, "source_id"),
            ),
        ]
        for name, mutation, path in cases:
            with self.subTest(case=name):
                attempt = self.replay(self.mutated_response(mutation))
                self.assert_rejected(
                    attempt, "adapter_owned_field", path, "additionalProperties"
                )

    def test_candidate_schema_failures_have_stable_paths(self):
        cases = [
            (
                "unsupported_relation",
                lambda body: body["edges"][0].update({"relation": "teaches"}),
                ("edges", 0, "relation"),
                "enum",
            ),
            (
                "wrong_endpoint_kind",
                lambda body: body["edges"][1].update(
                    {"source_ref": "c_correlation"}
                ),
                ("edges", 1, "source_ref"),
                "pattern",
            ),
            (
                "missing_edge_evidence",
                lambda body: body["edges"][0].update({"evidence_refs": []}),
                ("edges", 0, "evidence_refs"),
                "minItems",
            ),
            (
                "canonical_candidate_id",
                lambda body: body["concepts"][0].update(
                    {"local_ref": "concept_correlation"}
                ),
                ("concepts", 0, "local_ref"),
                "pattern",
            ),
            (
                "understood",
                lambda body: body["learning_events"][0].update(
                    {"understood": True}
                ),
                ("learning_events", 0),
                "additionalProperties",
            ),
            (
                "mastered",
                lambda body: body["concepts"][0].update({"mastered": True}),
                ("concepts", 0),
                "additionalProperties",
            ),
            (
                "numeric_proficiency",
                lambda body: body["concepts"][0].update({"proficiency": 0.73}),
                ("concepts", 0),
                "additionalProperties",
            ),
        ]
        for name, mutation, path, validator in cases:
            with self.subTest(case=name):
                attempt = self.replay(self.mutated_response(mutation))
                self.assert_rejected(
                    attempt, "invalid_candidate_result", path, validator
                )

    def test_invalid_adapter_metadata_is_rejected(self):
        cases = [
            (
                "extractor_version",
                {"extractor_version": "   "},
                "invalid_extractor_version",
                ("extractor_version",),
                "pattern",
            ),
            (
                "generated_at",
                {"generated_at": "yesterday"},
                "invalid_generated_at",
                ("generated_at",),
                "format",
            ),
        ]
        for name, overrides, code, path, validator in cases:
            with self.subTest(case=name):
                attempt = self.replay(**overrides)
                self.assert_rejected(attempt, code, path, validator)

    def test_invalid_trusted_input_raises_contract_error(self):
        invalid_input = copy.deepcopy(self.extraction_input)
        invalid_input["source"]["id"] = "invalid"
        with self.assertRaises(ExtractionInputValidationError):
            self.replay(extraction_input=invalid_input)

    def test_replay_has_no_network_or_vault_writes(self):
        before = tree_digest(PHASE0_VAULT)
        with mock.patch.object(
            socket,
            "socket",
            side_effect=AssertionError("network access attempted"),
        ):
            attempt = self.replay()
        self.assertEqual(attempt.status, "accepted")
        self.assertEqual(tree_digest(PHASE0_VAULT), before)

    def assert_rejected(self, attempt, code, path, validator):
        self.assertEqual(attempt.status, "rejected")
        self.assertIsNone(attempt.candidate_result)
        self.assertIsNotNone(attempt.rejection)
        self.assertEqual(attempt.rejection.code, code)
        self.assertEqual(attempt.rejection.path, path)
        self.assertEqual(attempt.rejection.validator, validator)


if __name__ == "__main__":
    unittest.main()
