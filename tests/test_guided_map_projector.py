from __future__ import annotations

import copy
import json
import socket
from dataclasses import FrozenInstanceError
from pathlib import Path
import unittest
from unittest import mock

from kgnote.visualization import (
    GUIDED_MAP_PROJECTOR_VERSION,
    GuidedMapProjectionProblem,
    project_guided_map,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "guided-map" / "v1"


def load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class GuidedMapProjectorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.graph = load("bitepacer-graph.json")
        self.spec = load("bitepacer-spec.json")
        self.golden = load("bitepacer-golden.json")

    def test_bitepacer_projection_matches_complete_golden(self) -> None:
        result = project_guided_map(self.graph, self.spec)
        self.assertEqual(result.status, "projected")
        self.assertEqual(result.projector_version, GUIDED_MAP_PROJECTOR_VERSION)
        self.assertIsNone(result.problem)
        self.assertEqual(result.model, self.golden)

    def test_names_directions_relations_and_evidence_come_from_graph(self) -> None:
        model = project_guided_map(self.graph, self.spec).model
        graph_nodes = {node["id"]: node for node in self.graph["nodes"]}
        graph_links = {link["id"]: link for link in self.graph["links"]}
        for proposition in model["propositions"]:
            link = graph_links[proposition["edge_id"]]
            self.assertEqual(proposition["subject_concept_id"], link["source_id"])
            self.assertEqual(proposition["object_concept_id"], link["target_id"])
            self.assertEqual(proposition["canonical_relation"], link["relation"])
            self.assertEqual(proposition["evidence_ids"], link["evidence_ids"])
            self.assertEqual(proposition["subject_label"], graph_nodes[link["source_id"]]["label"])
            self.assertEqual(proposition["object_label"], graph_nodes[link["target_id"]]["label"])
        self.assertFalse({group["id"] for group in model["groups"]} & set(graph_nodes))

    def test_stale_snapshot_and_evidence_drift_fail_closed(self) -> None:
        spec = copy.deepcopy(self.spec)
        spec["graph_snapshot_sha256"] = "0" * 64
        result = project_guided_map(self.graph, spec)
        self.assertEqual(result.status, "rejected")
        self.assertEqual(result.problem.code, "stale_graph_snapshot")

        spec = copy.deepcopy(self.spec)
        spec["teaching_propositions"][0]["evidence_ids"].pop()
        result = project_guided_map(self.graph, spec)
        self.assertEqual(result.status, "rejected")
        self.assertEqual(result.problem.code, "teaching_evidence_drift")

    def test_learning_or_soft_edges_cannot_become_teaching_propositions(self) -> None:
        graph = copy.deepcopy(self.graph)
        graph["links"][0]["edge_class"] = "soft_association"
        graph["links"][0]["relation"] = None
        graph["links"][0]["confidence"] = "unresolved"
        graph["filter_facets"]["edge_classes"] = ["canonical", "soft_association"]
        result = project_guided_map(graph, self.spec)
        self.assertEqual(result.status, "rejected")
        self.assertEqual(result.problem.code, "non_canonical_teaching_edge")

    def test_unreviewed_evidence_cannot_support_the_guided_map(self) -> None:
        graph = copy.deepcopy(self.graph)
        graph["evidence"][0]["review_status"] = "unreviewed"
        result = project_guided_map(graph, self.spec)
        self.assertEqual(result.status, "rejected")
        self.assertEqual(result.problem.code, "unreviewed_teaching_evidence")

    def test_result_and_inputs_are_copy_safe(self) -> None:
        graph = copy.deepcopy(self.graph)
        spec = copy.deepcopy(self.spec)
        original_graph = copy.deepcopy(graph)
        original_spec = copy.deepcopy(spec)
        result = project_guided_map(graph, spec)
        self.assertEqual(graph, original_graph)
        self.assertEqual(spec, original_spec)
        with self.assertRaises(FrozenInstanceError):
            result.status = "rejected"
        first = result.model
        first["groups"].clear()
        self.assertEqual(result.model, self.golden)

    def test_projection_has_no_filesystem_network_or_clock_io(self) -> None:
        with (
            mock.patch("builtins.open", side_effect=AssertionError("unexpected file I/O")),
            mock.patch.object(Path, "read_text", side_effect=AssertionError("unexpected file I/O")),
            mock.patch.object(Path, "write_text", side_effect=AssertionError("unexpected file I/O")),
            mock.patch.object(socket, "create_connection", side_effect=AssertionError("unexpected network I/O")),
        ):
            result = project_guided_map(self.graph, self.spec)
        self.assertEqual(result.status, "projected")

    def test_problem_value_object_is_frozen(self) -> None:
        problem = GuidedMapProjectionProblem("example")
        with self.assertRaises(FrozenInstanceError):
            problem.code = "changed"


if __name__ == "__main__":
    unittest.main()
