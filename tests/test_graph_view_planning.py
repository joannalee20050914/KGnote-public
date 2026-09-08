from __future__ import annotations

import copy
import json
import socket
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest import mock

from jsonschema import Draft202012Validator

from kgnote.visualization import plan_graph_view


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class GraphViewPlanningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.model = load(FIXTURES / "graph-read-model" / "v1" / "valid.json")
        cls.query = load(FIXTURES / "graph-view" / "v1" / "query.json")
        cls.golden = load(FIXTURES / "graph-view" / "v1" / "plan.json")

    def test_schemas_are_draft_2020_12_and_golden_is_valid(self) -> None:
        schema_root = ROOT / "schemas" / "graph-view" / "v1"
        query_schema = load(schema_root / "query.schema.json")
        plan_schema = load(schema_root / "plan.schema.json")
        Draft202012Validator.check_schema(query_schema)
        Draft202012Validator.check_schema(plan_schema)
        Draft202012Validator(query_schema).validate(self.query)
        Draft202012Validator(plan_schema).validate(self.golden)

    def test_phase0_one_hop_matches_golden_and_keeps_direction(self) -> None:
        result = plan_graph_view(self.model, self.query)
        self.assertEqual(result.status, "planned")
        self.assertEqual(result.plan, self.golden)
        asked = next(link for link in self.model["links"] if link["id"] == "edge_event_asked_correlation")
        self.assertEqual((asked["source_id"], asked["target_id"]), ("event_causality_question", "concept_correlation"))
        self.assertIn(asked["id"], result.plan["selected"]["link_ids"])

    def test_filters_apply_before_direction_neutral_hop_traversal(self) -> None:
        query = copy.deepcopy(self.query)
        query["filters"]["edge_classes"] = ["canonical"]
        plan = plan_graph_view(self.model, query).plan
        self.assertEqual(plan["selected"]["node_ids"], ["concept_causation", "concept_confounder", "concept_correlation"])
        self.assertEqual(plan["selected"]["link_ids"], ["edge_confounder_related_correlation", "edge_correlation_contrasts_causation"])

    def test_relation_and_space_filters_select_only_matching_subgraphs(self) -> None:
        relation_query = copy.deepcopy(self.query)
        relation_query["filters"]["relations"] = ["asked_about"]
        relation_plan = plan_graph_view(self.model, relation_query).plan
        self.assertEqual(relation_plan["selected"]["node_ids"], ["concept_correlation", "event_causality_question"])
        self.assertEqual(relation_plan["selected"]["link_ids"], ["edge_event_asked_correlation"])

        model = copy.deepcopy(self.model)
        counterfactual = next(node for node in model["nodes"] if node["id"] == "concept_counterfactual")
        counterfactual["spaces"] = ["other-space"]
        model["filter_facets"]["spaces"] = ["causal-inference", "other-space"]
        space_query = copy.deepcopy(self.query)
        space_query["focus_node_id"] = "concept_counterfactual"
        space_query["filters"]["spaces"] = ["other-space"]
        space_plan = plan_graph_view(model, space_query).plan
        self.assertEqual(space_plan["selected"]["node_ids"], ["concept_counterfactual", "event_causality_question"])
        self.assertEqual(space_plan["selected"]["link_ids"], ["edge_event_encountered_counterfactual"])

    def test_two_and_three_hops_expand_monotonically(self) -> None:
        selected = []
        for depth in (1, 2, 3):
            query = copy.deepcopy(self.query)
            query["hop_depth"] = depth
            selected.append(set(plan_graph_view(self.model, query).plan["selected"]["node_ids"]))
        self.assertLess(selected[0], selected[1])
        self.assertLessEqual(selected[1], selected[2])
        self.assertEqual(selected[2], {node["id"] for node in self.model["nodes"]})

    def test_no_focus_selects_filtered_graph_and_support_provenance(self) -> None:
        query = copy.deepcopy(self.query)
        query["focus_node_id"] = None
        query["hop_depth"] = None
        query["filters"]["node_kinds"] = ["learning_event"]
        plan = plan_graph_view(self.model, query).plan
        self.assertEqual(plan["selected"]["node_ids"], ["event_causality_question"])
        self.assertEqual(plan["selected"]["link_ids"], [])
        self.assertEqual(len(plan["selected"]["evidence_ids"]), 4)
        self.assertEqual(plan["selected"]["source_ids"], ["src_synthetic_causality_chat"])

    def test_isolated_focus_is_successful_zero_link_plan(self) -> None:
        query = copy.deepcopy(self.query)
        query["filters"]["node_kinds"] = ["concept"]
        query["filters"]["edge_classes"] = ["learning"]
        result = plan_graph_view(self.model, query)
        self.assertEqual(result.status, "planned")
        self.assertEqual(result.plan["selected"]["node_ids"], ["concept_correlation"])
        self.assertEqual(result.plan["selected"]["link_ids"], [])

    def test_focus_excluded_unknown_and_stale_snapshot_reject(self) -> None:
        cases = []
        excluded = copy.deepcopy(self.query)
        excluded["filters"]["node_kinds"] = ["learning_event"]
        cases.append((excluded, "focus_excluded_by_filters"))
        unknown = copy.deepcopy(self.query)
        unknown["focus_node_id"] = "concept_missing"
        cases.append((unknown, "unknown_focus_node"))
        stale = copy.deepcopy(self.query)
        stale["snapshot_sha256"] = "0" * 64
        cases.append((stale, "snapshot_digest_mismatch"))
        for query, code in cases:
            with self.subTest(code=code):
                result = plan_graph_view(self.model, query)
                self.assertEqual(result.status, "rejected")
                self.assertEqual(result.problem.code, code)
                self.assertIsNone(result.plan)

    def test_malformed_queries_fail_closed_without_echo(self) -> None:
        cases = []
        for field, value, code in (
            ("schema_version", "future", "unsupported_query_version"),
            ("hop_depth", 4, "invalid_hop_depth"),
            ("focus_node_id", 42, "invalid_focus"),
        ):
            query = copy.deepcopy(self.query); query[field] = value; cases.append((query, code))
        unsorted = copy.deepcopy(self.query); unsorted["filters"]["node_kinds"] = ["learning_event", "concept"]; cases.append((unsorted, "invalid_filter_values"))
        unavailable = copy.deepcopy(self.query); unavailable["filters"]["spaces"] = ["private-secret-space"]; cases.append((unavailable, "unavailable_filter_value"))
        extra = copy.deepcopy(self.query); extra["raw_markdown"] = "private-secret"; cases.append((extra, "invalid_query_fields"))
        for query, code in cases:
            with self.subTest(code=code):
                result = plan_graph_view(self.model, query)
                self.assertEqual(result.problem.code, code)
                self.assertNotIn("private-secret", repr(result))

    def test_deterministic_copy_safe_read_only_and_no_io(self) -> None:
        model = copy.deepcopy(self.model); query = copy.deepcopy(self.query)
        with (
            mock.patch("builtins.open", side_effect=AssertionError("file I/O")),
            mock.patch.object(Path, "read_text", side_effect=AssertionError("file I/O")),
            mock.patch.object(Path, "write_text", side_effect=AssertionError("file I/O")),
            mock.patch.object(socket, "create_connection", side_effect=AssertionError("network I/O")),
        ):
            first = plan_graph_view(model, query)
            second = plan_graph_view(model, query)
        self.assertEqual(first, second)
        self.assertEqual(model, self.model); self.assertEqual(query, self.query)
        changed = first.plan; changed["selected"]["node_ids"].clear()
        self.assertEqual(first.plan, self.golden)
        with self.assertRaises(FrozenInstanceError):
            first.status = "rejected"


if __name__ == "__main__":
    unittest.main()
