from __future__ import annotations

import json
import http.client
import subprocess
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

from http.server import ThreadingHTTPServer

from scripts.serve_graph_view import MAX_QUERY_BYTES, SECURITY_HEADERS, execute_guided_review, execute_query, handler_for, safe_static_path


ROOT = Path(__file__).resolve().parents[1]
STORE = ROOT / "fixtures" / "phase0-obsidian"


def tree_bytes(root: Path) -> tuple[tuple[str, bytes], ...]:
    return tuple((path.relative_to(root).as_posix(), path.read_bytes()) for path in sorted(root.rglob("*")) if path.is_file())


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
        status, payload = execute_query(STORE, b"\xff")
        self.assertEqual(status, 400)
        self.assertEqual(payload["problem"]["code"], "invalid_json")
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

    def test_internal_failure_is_safe_and_does_not_raise(self) -> None:
        with mock.patch("scripts.serve_graph_view.load_graph_view", side_effect=RuntimeError("private traceback value")):
            status, payload = execute_query(STORE, b"{}")
        self.assertEqual(status, 500)
        self.assertEqual(payload["problem"]["code"], "internal_error")
        self.assertNotIn("private", json.dumps(payload))

    def test_static_path_rejects_traversal_and_symlinks(self) -> None:
        self.assertIsNotNone(safe_static_path("/index.html", ROOT / "web"))
        for path in ("/../index.html", "/%2e%2e/index.html", "/..%2findex.html", "/%00index.html"):
            self.assertIsNone(safe_static_path(path, ROOT / "web"))


class GraphViewHttpBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), handler_for(STORE))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.port = cls.server.server_address[1]

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def request(self, method: str, path: str, body: bytes | None = None, headers: dict[str, str] | None = None) -> tuple[int, dict[str, str], bytes]:
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=3)
        connection.request(method, path, body=body, headers=headers or {})
        response = connection.getresponse()
        result = response.status, {key: value for key, value in response.getheaders()}, response.read()
        connection.close()
        return result

    def test_full_http_matrix_is_byte_for_byte_read_only(self) -> None:
        before = tree_bytes(STORE)
        full = json.loads((ROOT / "web" / "fixtures" / "phase0-graph-view.json").read_text())
        base = {
            "schema_version": "kgnote.graph-view-query.v1",
            "snapshot_sha256": full["view"]["snapshot_sha256"],
            "focus_node_id": None,
            "hop_depth": None,
            "filters": {"node_kinds": [], "edge_classes": [], "relations": [], "spaces": []},
        }
        queries = [base]
        for hops in (1, 2, 3):
            queries.append({**base, "focus_node_id": "concept_correlation", "hop_depth": hops})
        for name, value in (("node_kinds", "learning_event"), ("edge_classes", "canonical"), ("relations", "asked_about"), ("spaces", "causal-inference")):
            query = json.loads(json.dumps(base))
            query["filters"][name] = [value]
            queries.append(query)

        with mock.patch.object(Path, "write_text", side_effect=AssertionError("write forbidden")), \
             mock.patch.object(Path, "write_bytes", side_effect=AssertionError("write forbidden")), \
             mock.patch.object(Path, "unlink", side_effect=AssertionError("delete forbidden")), \
             mock.patch.object(Path, "rename", side_effect=AssertionError("rename forbidden")), \
             mock.patch.object(subprocess, "run", side_effect=AssertionError("process forbidden")), \
             mock.patch.object(time, "time", side_effect=AssertionError("clock forbidden")), \
             mock.patch("kgnote.storage.canonical_store.apply_approved_plan", side_effect=AssertionError("apply forbidden")):
            for query in queries:
                status, headers, body = self.request("POST", "/api/graph-view", json.dumps(query).encode(), {"Content-Type": "application/json"})
                self.assertEqual(status, 200, body)
                self.assertEqual(json.loads(body)["status"], "ready")
                for name in SECURITY_HEADERS:
                    self.assertIn(name, headers)
            rejected_queries = [
                {**base, "snapshot_sha256": "0" * 64},
                {**base, "focus_node_id": "concept_missing", "hop_depth": 1},
                {**base, "focus_node_id": "concept_correlation", "hop_depth": 1, "filters": {**base["filters"], "node_kinds": ["learning_event"]}},
                {**base, "focus_node_id": "concept_correlation", "hop_depth": 4},
                {**base, "filters": {**base["filters"], "spaces": ["private-space"]}},
            ]
            for query in rejected_queries:
                status, _, body = self.request("POST", "/api/graph-view", json.dumps(query).encode(), {"Content-Type": "application/json"})
                self.assertEqual(status, 400, body)
                self.assertEqual(json.loads(body)["status"], "rejected")
                self.assertNotIn(b"private-space", body)
            status, _, body = self.request("POST", "/api/graph-view", b"\xff", {"Content-Type": "application/json"})
            self.assertEqual(status, 400)
            self.assertEqual(json.loads(body)["problem"]["code"], "invalid_json")
            status, _, body = self.request("POST", "/api/graph-view", b"x" * (MAX_QUERY_BYTES + 1), {"Content-Type": "application/json"})
            self.assertEqual(status, 413)
            self.assertEqual(json.loads(body)["problem"]["code"], "query_too_large")

        self.assertEqual(before, tree_bytes(STORE))

    def test_static_exposure_methods_and_bad_requests_fail_closed(self) -> None:
        status, headers, _ = self.request("GET", "/")
        self.assertEqual(status, 200)
        self.assertNotIn("Server", headers)
        self.assertNotIn("Date", headers)
        for path in ("/../AGENTS.md", "/%2e%2e/AGENTS.md", "/.git/config", "/schemas/graph-view/v1/query.schema.json", "/fixtures/phase0-obsidian/concepts/concept_correlation.md", "/"):
            if path == "/":
                continue
            status, _, body = self.request("GET", path)
            self.assertEqual(status, 404)
            self.assertEqual(json.loads(body)["problem"]["code"], "not_found")
        for method in ("PUT", "PATCH", "DELETE", "OPTIONS", "TRACE", "CONNECT"):
            status, _, body = self.request(method, "/api/graph-view", b"{}", {"Content-Type": "application/json"})
            self.assertEqual(status, 405)
            self.assertEqual(json.loads(body)["problem"]["code"], "method_not_allowed")
        status, _, body = self.request("POST", "/api/graph-view", b"{}", {"Content-Type": "text/plain"})
        self.assertEqual(status, 415)
        self.assertEqual(json.loads(body)["problem"]["code"], "json_content_type_required")
        status, _, body = self.request("POST", "/wrong", b"private value", {"Content-Type": "application/json"})
        self.assertEqual(status, 404)
        self.assertNotIn(b"private value", body)
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=3)
        connection.putrequest("POST", "/api/graph-view")
        connection.putheader("Content-Type", "application/json")
        connection.putheader("Content-Length", "invalid")
        connection.endheaders()
        response = connection.getresponse()
        self.assertEqual(response.status, 400)
        self.assertEqual(json.loads(response.read())["problem"]["code"], "invalid_content_length")
        connection.close()


class GuidedReviewHttpBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory()
        cls.review_root = Path(cls.temporary.name) / "guided"
        cls.review_root.mkdir()
        cls.model = json.loads((ROOT / "tests/fixtures/guided-map/v1/bitepacer-golden.json").read_text())
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), handler_for(
            STORE, guided_map_model=cls.model, guided_review_root=cls.review_root,
        ))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.port = cls.server.server_address[1]

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)
        cls.temporary.cleanup()

    def request(self, payload: dict) -> tuple[int, dict[str, str], dict]:
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=3)
        connection.request("POST", "/api/guided-reviews", body=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
        response = connection.getresponse()
        result = response.status, {key: value for key, value in response.getheaders()}, json.loads(response.read())
        connection.close()
        return result

    def test_append_only_guided_review_http_and_stale_rejection(self) -> None:
        request = {
            "schema_version": "kgnote.guided-review-request.v1",
            "learning_unit_id": self.model["learning_unit"]["id"],
            "source_id": self.model["source"]["id"],
            "graph_snapshot_sha256": self.model["graph_snapshot_sha256"],
            "edge_id": "edge_80042c4f448d92b2d8311f064b6189e7259615ff1c0babd38bb817adcf561c4a",
            "response": "主動送出",
            "hint_used": False,
        }
        status, headers, body = self.request(request)
        self.assertEqual(status, 200, body)
        self.assertEqual(body["status"], "recorded")
        self.assertEqual(body["comparison"], "matched_reviewed_phrase")
        self.assertTrue((self.review_root / "reviews" / f"{body['review_id']}.md").is_file())
        for name in SECURITY_HEADERS:
            self.assertIn(name, headers)
        request["graph_snapshot_sha256"] = "0" * 64
        status, _, body = self.request(request)
        self.assertEqual(status, 400)
        self.assertEqual(body["problem"]["code"], "stale_guided_review")

    def test_guided_endpoint_is_not_exposed_without_explicit_configuration(self) -> None:
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler_for(STORE))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            connection = http.client.HTTPConnection("127.0.0.1", server.server_address[1], timeout=3)
            connection.request("POST", "/api/guided-reviews", body=b"{}", headers={"Content-Type": "application/json"})
            response = connection.getresponse()
            self.assertEqual(response.status, 404)
            self.assertEqual(json.loads(response.read())["problem"]["code"], "not_found")
            connection.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
