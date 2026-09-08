from __future__ import annotations

import copy
import json
import socket
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest import mock

from kgnote.storage import read_canonical_store
from kgnote.visualization import (
    GRAPH_PROJECTOR_VERSION,
    GraphProjectionProblem,
    project_graph_read_model,
)


ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "tests" / "fixtures" / "graph-read-model" / "v1" / "valid.json"


class GraphReadModelProjectorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        snapshot = read_canonical_store(ROOT / "fixtures" / "phase0-obsidian")
        if snapshot.status != "loaded":
            raise AssertionError(snapshot.problem)
        cls.records = snapshot.records
        cls.golden = json.loads(GOLDEN.read_text(encoding="utf-8"))

    def test_phase0_projection_matches_complete_golden(self) -> None:
        result = project_graph_read_model(self.records)
        self.assertEqual(result.status, "projected")
        self.assertEqual(result.projector_version, GRAPH_PROJECTOR_VERSION)
        self.assertIsNone(result.problem)
        self.assertEqual(result.model, self.golden)

    def test_record_and_set_like_array_permutations_are_deterministic(self) -> None:
        permuted = copy.deepcopy(self.records)
        permuted.reverse()
        for record in permuted:
            for field_name in ("aliases", "spaces", "source_ids", "concept_ids", "evidence_ids"):
                if field_name in record:
                    record[field_name].reverse()
        self.assertEqual(
            project_graph_read_model(self.records),
            project_graph_read_model(permuted),
        )

    def test_result_is_immutable_and_model_access_is_copy_safe(self) -> None:
        source = copy.deepcopy(self.records)
        original = copy.deepcopy(source)
        result = project_graph_read_model(source)
        self.assertEqual(source, original)
        with self.assertRaises(FrozenInstanceError):
            result.status = "rejected"

        first = result.model
        first["nodes"][0]["label"] = "changed"
        first["nodes"].clear()
        self.assertEqual(result.model, self.golden)

    def test_labels_are_sanitized_truncated_fallback_and_collision_safe(self) -> None:
        records = copy.deepcopy(self.records)
        concepts = [record for record in records if record["type"] == "concept"]
        concepts[0]["canonical_name"] = "Same [[unsafe# title^ " + "x" * 100
        concepts[1]["canonical_name"] = "Same [[unsafe# title^ " + "x" * 100
        concepts[2]["canonical_name"] = "   [[|#^   "

        result = project_graph_read_model(records)
        self.assertEqual(result.status, "projected")
        labels = [
            node["label"] for node in result.model["nodes"]
            if node["id"] in {concept["id"] for concept in concepts[:3]}
        ]
        self.assertEqual(len(labels), len(set(label.casefold() for label in labels)))
        self.assertTrue(all(0 < len(label) <= 64 for label in labels))
        self.assertTrue(all(not set("[]|#^\r\n") & set(label) for label in labels))
        self.assertTrue(any(label.startswith("Record ") for label in labels))

    def test_rejects_malformed_duplicate_and_dangling_snapshots_safely(self) -> None:
        cases = []
        malformed = copy.deepcopy(self.records)
        malformed[0]["private_body"] = "do-not-echo-secret"
        cases.append((malformed, "snapshot_unexpected_record_field"))

        duplicate = copy.deepcopy(self.records)
        duplicate.append(copy.deepcopy(duplicate[0]))
        cases.append((duplicate, "snapshot_duplicate_existing_id"))

        dangling = copy.deepcopy(self.records)
        concept = next(record for record in dangling if record["type"] == "concept")
        concept["evidence_ids"] = ["evidence_missing"]
        cases.append((dangling, "snapshot_unresolved_projected_reference"))

        for records, expected_code in cases:
            with self.subTest(code=expected_code):
                result = project_graph_read_model(records)
                self.assertEqual(result.status, "rejected")
                self.assertEqual(result.problem.code, expected_code)
                self.assertIsNone(result.model)
                self.assertNotIn("do-not-echo-secret", repr(result))

    def test_projection_has_no_filesystem_network_or_clock_io(self) -> None:
        with (
            mock.patch("builtins.open", side_effect=AssertionError("unexpected file I/O")),
            mock.patch.object(Path, "read_text", side_effect=AssertionError("unexpected file I/O")),
            mock.patch.object(Path, "write_text", side_effect=AssertionError("unexpected file I/O")),
            mock.patch.object(socket, "create_connection", side_effect=AssertionError("unexpected network I/O")),
        ):
            result = project_graph_read_model(self.records)
        self.assertEqual(result.status, "projected")

    def test_problem_value_object_is_frozen(self) -> None:
        problem = GraphProjectionProblem("example")
        with self.assertRaises(FrozenInstanceError):
            problem.code = "changed"


if __name__ == "__main__":
    unittest.main()
