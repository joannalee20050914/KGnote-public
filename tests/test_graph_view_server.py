from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.serve_graph_view import MAX_QUERY_BYTES, execute_query


ROOT = Path(__file__).resolve().parents[1]
STORE = ROOT / "fixtures" / "phase0-obsidian"


class GraphViewServerTests(unittest.TestCase):
    def test_executes_versioned_query_through_application_boundary(self) -> None:
        full = json.loads((ROOT / "web" / "fixtures" / "phase0-graph-view.json").read_text())
        query = {
            "schema_version": "kgnote.graph-view-query.v1",
            "snapshot_sha256": full["view"]["snapshot_sha256"],
            "focus_node_id": "concept_correlation",
            "hop_depth": 1,
            "filters": {"node_kinds": [], "edge_classes": [], "relations": [], "spaces": []},
        }
        status, payload = execute_query(STORE, json.dumps(query).encode())
        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "ready")
        self.assertLess(len(payload["view"]["nodes"]), len(full["view"]["nodes"]))

    def test_invalid_and_oversized_payloads_fail_without_echo(self) -> None:
        status, payload = execute_query(STORE, b'{"private":"do not echo"}')
        self.assertEqual(status, 400)
        self.assertNotIn("do not echo", json.dumps(payload))
        status, payload = execute_query(STORE, b"x" * (MAX_QUERY_BYTES + 1))
        self.assertEqual(status, 413)
        self.assertEqual(payload["problem"]["code"], "query_too_large")

    def test_learning_event_only_returns_one_node_without_server_exception(self) -> None:
        full = json.loads((ROOT / "web" / "fixtures" / "phase0-graph-view.json").read_text())
        query = {
            "schema_version": "kgnote.graph-view-query.v1",
            "snapshot_sha256": full["view"]["snapshot_sha256"],
            "focus_node_id": None,
            "hop_depth": None,
            "filters": {"node_kinds": ["learning_event"], "edge_classes": [], "relations": [], "spaces": []},
        }
        status, payload = execute_query(STORE, json.dumps(query).encode())
        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "ready")
        self.assertEqual([node["kind"] for node in payload["view"]["nodes"]], ["learning_event"])
        self.assertEqual(payload["view"]["links"], [])


if __name__ == "__main__":
    unittest.main()
