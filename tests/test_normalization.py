import copy
import hashlib
import json
import socket
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest import mock

from kgnote.normalization import (
    NORMALIZATION_RULESET_VERSION,
    normalize_candidate_result,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
VALID_OUTPUT = (
    PROJECT_ROOT / "tests" / "fixtures" / "extraction" / "v1" / "valid" / "output.json"
)
GOLDEN_OUTPUT = (
    PROJECT_ROOT
    / "tests"
    / "fixtures"
    / "normalization"
    / "v1"
    / "golden.json"
)
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


def rename_refs(candidate_result, replacements):
    renamed = copy.deepcopy(candidate_result)
    reference_fields = {
        "local_ref",
        "source_ref",
        "target_ref",
        "concept_refs",
        "evidence_refs",
    }

    def replace(value, field_name=None):
        if isinstance(value, dict):
            return {key: replace(child, key) for key, child in value.items()}
        if isinstance(value, list):
            return [replace(child, field_name) for child in value]
        if field_name in reference_fields and isinstance(value, str):
            return replacements.get(value, value)
        return value

    return replace(renamed)


class NormalizationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.candidate_result = load_json(VALID_OUTPUT)

    def test_valid_candidate_matches_golden_records_and_ref_map(self):
        result = normalize_candidate_result(self.candidate_result)
        golden = load_json(GOLDEN_OUTPUT)

        self.assertEqual(result.status, "normalized")
        self.assertEqual(result.ruleset_version, NORMALIZATION_RULESET_VERSION)
        self.assertIsNone(result.problem)
        self.assertEqual(result.records, golden["records"])
        self.assertEqual(result.ref_map, golden["ref_map"])

    def test_emitted_references_resolve_or_are_trusted_source(self):
        result = normalize_candidate_result(self.candidate_result)
        records = result.records
        by_id = {
            record["id"]: record
            for collection in records.values()
            for record in collection
        }
        source_id = self.candidate_result["source_id"]

        for concept in records["concepts"]:
            self.assertTrue(all(ref in by_id for ref in concept["evidence_ids"]))
        for evidence in records["evidence"]:
            self.assertEqual(evidence["source_id"], source_id)
        for event in records["learning_events"]:
            self.assertEqual(event["source_ids"], [source_id])
            self.assertTrue(all(ref in by_id for ref in event["concept_ids"]))
            self.assertTrue(all(ref in by_id for ref in event["evidence_ids"]))
        for edge in records["edges"]:
            self.assertIn(edge["source_id"], by_id)
            self.assertIn(edge["target_id"], by_id)
            self.assertTrue(all(ref in by_id for ref in edge["evidence_ids"]))

    def test_repeated_and_permuted_inputs_are_equal(self):
        first = normalize_candidate_result(self.candidate_result)
        self.assertEqual(first, normalize_candidate_result(self.candidate_result))

        permuted = copy.deepcopy(self.candidate_result)
        for collection in ("concepts", "evidence", "learning_events", "edges"):
            permuted[collection].reverse()
        for concept in permuted["concepts"]:
            concept["aliases"].reverse()
            concept["spaces"].reverse()
            concept["evidence_refs"].reverse()
        for event in permuted["learning_events"]:
            event["concept_refs"].reverse()
            event["evidence_refs"].reverse()
        for edge in permuted["edges"]:
            edge["evidence_refs"].reverse()

        self.assertEqual(first, normalize_candidate_result(permuted))

    def test_local_ref_names_do_not_change_canonical_records_or_ids(self):
        replacements = {
            "c_correlation": "c_renamed_a",
            "c_causation": "c_renamed_b",
            "c_causal_inference": "c_renamed_c",
            "c_counterfactual": "c_renamed_d",
            "ev_difference": "ev_renamed_a",
            "ev_counterfactual_unresolved": "ev_renamed_b",
            "le_causality_question": "le_renamed_a",
            "ed_correlation_contrasts_causation": "ed_renamed_a",
            "ed_event_asked_correlation": "ed_renamed_b",
            "ed_causal_inference_counterfactual_unresolved": "ed_renamed_c",
        }
        original = normalize_candidate_result(self.candidate_result)
        renamed = normalize_candidate_result(
            rename_refs(self.candidate_result, replacements)
        )

        self.assertEqual(original.records, renamed.records)
        self.assertEqual(set(original.ref_map.values()), set(renamed.ref_map.values()))

    def test_nfc_whitespace_and_case_have_documented_identity_behavior(self):
        baseline = normalize_candidate_result(self.candidate_result)
        variant = copy.deepcopy(self.candidate_result)
        concept = next(
            item for item in variant["concepts"] if item["local_ref"] == "c_correlation"
        )
        concept["name"] = "  CORRELATION \n"
        concept["spaces"] = ["  CAUSAL-INFERENCE  "]
        concept["aliases"] = ["e\u0301", "é", " É "]
        normalized = normalize_candidate_result(variant)

        self.assertEqual(
            baseline.ref_map["c_correlation"], normalized.ref_map["c_correlation"]
        )
        output_concept = next(
            item
            for item in normalized.records["concepts"]
            if item["id"] == normalized.ref_map["c_correlation"]
        )
        self.assertEqual(output_concept["canonical_name"], "CORRELATION")
        self.assertEqual(output_concept["spaces"], ["causal-inference"])
        self.assertEqual(output_concept["aliases"], ["É"])

    def test_duplicate_and_dangling_local_refs_reject_safely(self):
        cases = []

        duplicate = copy.deepcopy(self.candidate_result)
        duplicate["concepts"].append(copy.deepcopy(duplicate["concepts"][0]))
        cases.append(("duplicate", duplicate, "duplicate_local_ref", "c_correlation"))

        dangling_concept = copy.deepcopy(self.candidate_result)
        dangling_concept["concepts"][0]["evidence_refs"] = ["ev_missing"]
        cases.append(
            ("concept_evidence", dangling_concept, "dangling_local_ref", "ev_missing")
        )

        dangling_event = copy.deepcopy(self.candidate_result)
        dangling_event["learning_events"][0]["concept_refs"] = ["c_missing"]
        cases.append(("event_concept", dangling_event, "dangling_local_ref", "c_missing"))

        dangling_edge = copy.deepcopy(self.candidate_result)
        dangling_edge["edges"][0]["target_ref"] = "c_missing"
        cases.append(("edge_target", dangling_edge, "dangling_local_ref", "c_missing"))

        for name, candidate, code, reference in cases:
            with self.subTest(case=name):
                result = normalize_candidate_result(candidate)
                self.assertEqual(result.status, "rejected")
                self.assertEqual(result.problem.code, code)
                self.assertEqual(result.problem.reference, reference)

    def test_wrong_kind_canonical_id_and_source_mismatch_reject_safely(self):
        wrong_kind = copy.deepcopy(self.candidate_result)
        wrong_kind["concepts"][0]["evidence_refs"] = ["c_causation"]

        canonical_id = copy.deepcopy(self.candidate_result)
        canonical_id["concepts"][0]["local_ref"] = "concept_correlation"

        source_mismatch = copy.deepcopy(self.candidate_result)
        source_mismatch["evidence"][0]["source_id"] = "src_other"

        cases = [
            (wrong_kind, "wrong_reference_kind", "c_causation"),
            (canonical_id, "canonical_id_not_allowed", "concept_correlation"),
            (source_mismatch, "source_id_mismatch", "src_other"),
        ]
        for candidate, code, reference in cases:
            with self.subTest(code=code):
                result = normalize_candidate_result(candidate)
                self.assertEqual(result.status, "rejected")
                self.assertEqual(result.problem.code, code)
                self.assertEqual(result.problem.reference, reference)

    def test_same_identity_candidates_conflict_without_merge(self):
        id_prefixes = {
            "concepts": "concept_",
            "evidence": "evidence_",
            "learning_events": "event_",
            "edges": "edge_",
        }
        cases = []
        for collection, new_ref in (
            ("concepts", "c_duplicate_identity"),
            ("evidence", "ev_duplicate_identity"),
            ("learning_events", "le_duplicate_identity"),
            ("edges", "ed_duplicate_identity"),
        ):
            candidate = copy.deepcopy(self.candidate_result)
            duplicate = copy.deepcopy(candidate[collection][0])
            original_ref = duplicate["local_ref"]
            duplicate["local_ref"] = new_ref
            candidate[collection].append(duplicate)
            cases.append((collection, candidate, tuple(sorted((original_ref, new_ref)))))

        for collection, candidate, expected_refs in cases:
            with self.subTest(collection=collection):
                result = normalize_candidate_result(candidate)
                self.assertEqual(result.status, "conflict")
                self.assertEqual(result.problem.code, "identity_conflict")
                self.assertEqual(result.problem.local_refs, expected_refs)
                self.assertTrue(
                    result.problem.canonical_id.startswith(id_prefixes[collection])
                )
                self.assertIsNone(result.records)

    def test_review_defaults_provenance_and_no_proficiency_claims(self):
        result = normalize_candidate_result(self.candidate_result)
        records = result.records
        self.assertTrue(all(item["status"] == "needs_review" for item in records["concepts"]))
        self.assertTrue(all(item["review_status"] == "unreviewed" for item in records["evidence"]))

        serialized = json.dumps(records, ensure_ascii=False)
        for forbidden in ("understood", "mastered", "proficiency"):
            self.assertNotIn(forbidden, serialized)
        for evidence in records["evidence"]:
            self.assertEqual(evidence["extractor_version"], "fixture-replay.v1")
            self.assertEqual(evidence["extracted_at"], "2026-09-07T00:00:00+08:00")
        for concept in records["concepts"]:
            self.assertEqual(concept["integration_version"], NORMALIZATION_RULESET_VERSION)

    def test_result_is_immutable_and_normalization_has_no_io_or_clock_dependency(self):
        before = tree_digest(PHASE0_VAULT)
        with mock.patch.object(
            socket,
            "socket",
            side_effect=AssertionError("network access attempted"),
        ):
            result = normalize_candidate_result(self.candidate_result)
        records = result.records
        records["concepts"].clear()

        self.assertTrue(result.records["concepts"])
        with self.assertRaises(FrozenInstanceError):
            result.status = "rejected"
        self.assertEqual(tree_digest(PHASE0_VAULT), before)


if __name__ == "__main__":
    unittest.main()
