from __future__ import annotations

import copy
import json
import os
import socket
import tempfile
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest import mock

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from kgnote.contracts import validate_graph_read_model
from kgnote.visualization import load_graph_view


ROOT = Path(__file__).resolve().parents[1]
STORE = ROOT / "fixtures" / "phase0-obsidian"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def tree_digest(root: Path) -> tuple[tuple[str, bytes], ...]:
    return tuple((path.relative_to(root).as_posix(), path.read_bytes()) for path in sorted(root.rglob("*")) if path.is_file())


class GraphViewApplicationTests(unittest.TestCase):
    def test_schema_and_phase0_default_full_graph_read_back(self) -> None:
        schema = load_json(ROOT / "schemas" / "graph-view-application" / "v1" / "application-result.schema.json")
        read_model_schema = load_json(ROOT / "schemas" / "graph-read-model" / "v1" / "graph-read-model.schema.json")
        plan_schema = load_json(ROOT / "schemas" / "graph-view" / "v1" / "plan.schema.json")
        registry = Registry().with_resources([
            (read_model_schema["$id"], Resource.from_contents(read_model_schema)),
            (plan_schema["$id"], Resource.from_contents(plan_schema)),
        ])
        Draft202012Validator.check_schema(schema)

        result = load_graph_view(STORE)
        self.assertEqual(result.status, "ready")
        response = result.response
        Draft202012Validator(schema, registry=registry).validate(response)
        validate_graph_read_model(response["view"])
        self.assertEqual(len(response["view"]["nodes"]), 7)
        self.assertEqual(len(response["view"]["links"]), 8)
        self.assertEqual(len(response["view"]["evidence"]), 4)
        self.assertEqual(len(response["view"]["sources"]), 1)
        self.assertEqual(response["plan"]["selected"]["node_ids"], [node["id"] for node in response["view"]["nodes"]])
        self.assertEqual(response["plan"]["snapshot_sha256"], response["view"]["snapshot_sha256"])
        web_fixture = load_json(ROOT / "web" / "fixtures" / "phase0-graph-view.json")
        self.assertEqual(web_fixture, response)

    def test_explicit_query_materializes_only_selected_records(self) -> None:
        full = load_graph_view(STORE).response
        query = {
            "schema_version": "kgnote.graph-view-query.v1",
            "snapshot_sha256": full["view"]["snapshot_sha256"],
            "focus_node_id": "concept_correlation",
            "hop_depth": 1,
            "filters": {"node_kinds": [], "edge_classes": [], "relations": [], "spaces": []},
        }
        original_query = copy.deepcopy(query)
        result = load_graph_view(STORE, query)
        self.assertEqual(query, original_query)
        self.assertEqual(result.status, "ready")
        response = result.response
        selected = response["plan"]["selected"]
        self.assertEqual([item["id"] for item in response["view"]["nodes"]], selected["node_ids"])
        self.assertEqual([item["id"] for item in response["view"]["links"]], selected["link_ids"])
        self.assertEqual([item["id"] for item in response["view"]["evidence"]], selected["evidence_ids"])
        self.assertEqual([item["id"] for item in response["view"]["sources"]], selected["source_ids"])
        self.assertLess(len(response["view"]["nodes"]), len(full["view"]["nodes"]))
        validate_graph_read_model(response["view"])

    def test_isolated_focus_is_ready_with_zero_links(self) -> None:
        digest = load_graph_view(STORE).response["view"]["snapshot_sha256"]
        query = {
            "schema_version": "kgnote.graph-view-query.v1",
            "snapshot_sha256": digest,
            "focus_node_id": "concept_correlation",
            "hop_depth": 1,
            "filters": {"node_kinds": ["concept"], "edge_classes": ["learning"], "relations": [], "spaces": []},
        }
        response = load_graph_view(STORE, query).response
        self.assertEqual(response["status"], "ready")
        self.assertEqual([node["id"] for node in response["view"]["nodes"]], ["concept_correlation"])
        self.assertEqual(response["view"]["links"], [])
        self.assertEqual(response["view"]["filter_facets"]["edge_classes"], [])

    def test_stale_and_malformed_queries_map_to_safe_planner_problems(self) -> None:
        digest = load_graph_view(STORE).response["view"]["snapshot_sha256"]
        base = {
            "schema_version": "kgnote.graph-view-query.v1",
            "snapshot_sha256": digest,
            "focus_node_id": None,
            "hop_depth": None,
            "filters": {"node_kinds": [], "edge_classes": [], "relations": [], "spaces": []},
        }
        cases = [
            ({**base, "snapshot_sha256": "0" * 64}, "snapshot_digest_mismatch", ["snapshot_sha256"]),
            ({**base, "private_markdown": "do not echo"}, "invalid_query_fields", []),
        ]
        for query, code, path in cases:
            with self.subTest(code=code):
                result = load_graph_view(STORE, query)
                self.assertEqual(result.status, "rejected")
                self.assertEqual(result.response["problem"], {"component": "planner", "code": code, "path": path})
                self.assertNotIn("do not echo", repr(result))
                self.assertNotIn("do not echo", json.dumps(result.response))

    def test_store_failures_hide_absolute_root_and_content(self) -> None:
        secret_root = Path(tempfile.gettempdir()) / "private-learning-vault-that-does-not-exist"
        result = load_graph_view(secret_root)
        self.assertEqual(result.status, "rejected")
        self.assertEqual(result.response["problem"]["component"], "store")
        serialized = json.dumps(result.response)
        self.assertNotIn(str(secret_root), serialized)
        self.assertNotIn("private-learning", repr(result))
        self.assertEqual(load_graph_view(None).response["problem"]["code"], "invalid_store_root")

    def test_dangling_store_reference_is_rejected_before_projection(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            copied = Path(directory) / "vault"
            import shutil
            shutil.copytree(STORE, copied)
            concept = next(path for path in (copied / "concepts").glob("*.md") if "evidence_ids: [" in path.read_text(encoding="utf-8"))
            original = concept.read_text(encoding="utf-8")
            concept.write_text(original.replace("evidence_ids: [", "evidence_ids: [evidence_missing, ", 1), encoding="utf-8")
            result = load_graph_view(copied)
        self.assertEqual(result.status, "rejected")
        self.assertEqual(result.problem.component, "store")
        self.assertTrue(result.problem.code.startswith("snapshot_"))
        self.assertFalse(any(os.path.isabs(str(part)) for part in result.problem.path))

    def test_result_is_deterministic_frozen_and_copy_safe(self) -> None:
        first = load_graph_view(STORE)
        second = load_graph_view(STORE)
        self.assertEqual(first, second)
        mutated = first.response
        mutated["view"]["nodes"].clear()
        self.assertEqual(len(first.response["view"]["nodes"]), 7)
        with self.assertRaises(FrozenInstanceError):
            first.status = "rejected"

    def test_boundary_is_read_only_without_network_model_ui_or_clock(self) -> None:
        before = tree_digest(STORE)
        with mock.patch.object(Path, "write_text", side_effect=AssertionError("write forbidden")), \
             mock.patch.object(Path, "write_bytes", side_effect=AssertionError("write forbidden")), \
             mock.patch.object(socket, "create_connection", side_effect=AssertionError("network forbidden")), \
             mock.patch("urllib.request.urlopen", side_effect=AssertionError("network forbidden")), \
             mock.patch("subprocess.run", side_effect=AssertionError("UI/process forbidden")), \
             mock.patch("time.time", side_effect=AssertionError("clock forbidden")):
            result = load_graph_view(STORE)
        self.assertEqual(result.status, "ready")
        self.assertEqual(before, tree_digest(STORE))

    def test_component_failures_are_mapped_without_exception_or_payload_echo(self) -> None:
        fake_problem = mock.Mock(code="unsafe_private_value", path=("records", 0))
        fake_projection = mock.Mock(status="rejected", problem=fake_problem)
        with mock.patch("kgnote.visualization.application.project_graph_read_model", return_value=fake_projection):
            result = load_graph_view(STORE)
        self.assertEqual(result.response["problem"], {
            "component": "projector", "code": "unsafe_private_value", "path": ["records", 0]
        })


if __name__ == "__main__":
    unittest.main()
