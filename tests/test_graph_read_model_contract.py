from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import unittest

from jsonschema import Draft202012Validator

from kgnote.contracts.graph_read_model import (
    GraphReadModelValidationError,
    SCHEMA_VERSION,
    validate_graph_read_model,
)
from kgnote.storage.canonical_store import read_canonical_store


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "graph-read-model" / "v1" / "valid.json"


def load_fixture() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def canonical_digest(records: list[dict]) -> str:
    copied = copy.deepcopy(records)
    set_like_fields = {
        "concept": ("aliases", "spaces", "evidence_ids"),
        "learning_event": ("source_ids", "concept_ids", "evidence_ids"),
        "edge": ("evidence_ids",),
    }
    for record in copied:
        for field_name in set_like_fields.get(record["type"], ()):
            record[field_name] = sorted(record[field_name])
    copied.sort(key=lambda record: (record["type"], record["id"]))
    content = json.dumps(
        copied, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(content).hexdigest()


def assert_rejected(test: unittest.TestCase, payload: dict, code: str) -> GraphReadModelValidationError:
    with test.assertRaises(GraphReadModelValidationError) as caught:
        validate_graph_read_model(payload)
    test.assertEqual(caught.exception.code, code)
    return caught.exception


class GraphReadModelContractTests(unittest.TestCase):
    def test_schema_is_valid_draft_2020_12(self) -> None:
        schema_path = ROOT / "schemas" / "graph-read-model" / "v1" / "graph-read-model.schema.json"
        Draft202012Validator.check_schema(json.loads(schema_path.read_text(encoding="utf-8")))

    def test_valid_phase0_projection_and_read_back(self) -> None:
        payload = load_fixture()
        validate_graph_read_model(payload)

        snapshot = read_canonical_store(ROOT / "fixtures" / "phase0-obsidian")
        self.assertEqual(snapshot.status, "loaded")
        records = snapshot.records
        expected = {
            record["type"]: {item["id"] for item in records if item["type"] == record["type"]}
            for record in records
        }
        self.assertEqual(payload["schema_version"], SCHEMA_VERSION)
        self.assertEqual(payload["snapshot_sha256"], canonical_digest(records))
        self.assertEqual({node["id"] for node in payload["nodes"] if node["kind"] == "concept"}, expected["concept"])
        self.assertEqual({node["id"] for node in payload["nodes"] if node["kind"] == "learning_event"}, expected["learning_event"])
        self.assertEqual({link["id"] for link in payload["links"]}, expected["edge"])
        self.assertEqual({item["id"] for item in payload["evidence"]}, expected["evidence"])
        self.assertEqual({item["id"] for item in payload["sources"]}, expected["source"])


    def test_identity_is_separate_from_display_label_and_no_raw_location_leaks(self) -> None:
        payload = load_fixture()
        correlation = next(node for node in payload["nodes"] if node["id"] == "concept_correlation")
        self.assertEqual(correlation["label"], "Correlation")
        self.assertNotEqual(correlation["id"], correlation["label"])

        serialized = json.dumps(payload, ensure_ascii=False)
        for forbidden in ("uri_or_path", str(ROOT), "Learner: 我常看到", "provider_response"):
            self.assertNotIn(forbidden, serialized)


    def test_schema_rejects_malformed_or_semantically_unsafe_fields(self) -> None:
        cases = [
        (lambda p: p.update(schema_version="kgnote.graph-read-model.v2"), "invalid_graph_read_model"),
        (lambda p: p.update(raw_markdown="private"), "invalid_graph_read_model"),
        (lambda p: p["sources"][0].update(uri_or_path="/private/user/secret.md"), "invalid_graph_read_model"),
        (lambda p: p["nodes"][0].update(understood=True), "invalid_graph_read_model"),
        (lambda p: p["nodes"][0].update(label="bad [[ label"), "invalid_graph_read_model"),
        (lambda p: p["links"][0].update(relation="related_to"), "invalid_graph_read_model"),
        (lambda p: p["links"][0].update(confidence="low"), "invalid_graph_read_model"),
        (lambda p: p["links"][1].update(relation="asked_about"), "invalid_graph_read_model"),
        ]
        for mutate, code in cases:
            with self.subTest(code=code, mutate=repr(mutate)):
                payload = load_fixture()
                mutate(payload)
                assert_rejected(self, payload, code)


    def test_rejects_duplicate_ids(self) -> None:
        payload = load_fixture()
        payload["evidence"][1]["id"] = payload["evidence"][0]["id"]
        assert_rejected(self, payload, "duplicate_record_id")


    def test_rejects_dangling_evidence_and_source_references(self) -> None:
        payload = load_fixture()
        payload["nodes"][0]["evidence_ids"] = ["evidence_missing"]
        assert_rejected(self, payload, "dangling_evidence_reference")

        payload = load_fixture()
        payload["evidence"][0]["source_id"] = "src_missing"
        assert_rejected(self, payload, "dangling_source_reference")


    def test_rejects_dangling_and_wrong_layer_link_endpoints(self) -> None:
        payload = load_fixture()
        payload["links"][0]["target_id"] = "concept_missing"
        assert_rejected(self, payload, "dangling_link_endpoint")

        payload = load_fixture()
        payload["links"][1]["source_id"] = "event_causality_question"
        assert_rejected(self, payload, "invalid_concept_edge_endpoint")

        payload = load_fixture()
        learning = next(link for link in payload["links"] if link["edge_class"] == "learning")
        learning["source_id"] = "concept_correlation"
        assert_rejected(self, payload, "invalid_learning_edge_endpoint")


    def test_rejects_non_deterministic_order_and_stale_facets(self) -> None:
        payload = load_fixture()
        payload["nodes"].reverse()
        assert_rejected(self, payload, "non_deterministic_order")

        payload = load_fixture()
        payload["filter_facets"]["relations"].remove("applied")
        assert_rejected(self, payload, "facet_values_do_not_match_records")


    def test_validation_is_read_only_and_error_does_not_echo_private_values(self) -> None:
        payload = load_fixture()
        original = copy.deepcopy(payload)
        validate_graph_read_model(payload)
        self.assertEqual(payload, original)

        secret = "do-not-echo-this-private-value"
        payload["sources"][0]["label"] = secret + "#"
        error = assert_rejected(self, payload, "invalid_graph_read_model")
        self.assertNotIn(secret, str(error))


if __name__ == "__main__":
    unittest.main()
