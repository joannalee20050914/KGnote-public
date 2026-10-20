from __future__ import annotations

import http.client
import json
import shutil
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path

from scripts.serve_graph_view import SECURITY_HEADERS, execute_note_source, handler_for


ROOT = Path(__file__).resolve().parents[1]
STORE = ROOT / "fixtures" / "phase0-obsidian"


class LearningNoteHttpTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.notes_root = Path(self.temporary.name)
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), handler_for(
            STORE, notes_root=self.notes_root, note_writes_enabled=True,
        ))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temporary.cleanup()

    def request(self, method: str, path: str, body: dict | None = None, headers: dict[str, str] | None = None):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_address[1], timeout=3)
        encoded = json.dumps(body).encode() if body is not None else None
        request_headers = dict(headers or {})
        if body is not None:
            request_headers.setdefault("Content-Type", "application/json")
        connection.request(method, path, body=encoded, headers=request_headers)
        response = connection.getresponse()
        result = response.status, dict(response.getheaders()), json.loads(response.read())
        connection.close()
        return result

    @staticmethod
    def payload(save_id: str = "save_http0001", markdown: str = "## 解釋\n\n共同變動不是因果證明。\n") -> dict:
        return {
            "schema_version": "kgnote.learning-note-save.v1",
            "note_id": "note_http", "notebook_id": "notebook_local", "learning_unit_id": "unit_http",
            "title": "HTTP note", "markdown": markdown, "save_id": save_id,
            "source_anchors": [{
                "id": "anchor_primary", "source_id": "src_synthetic_causality_chat",
                "locator": {"kind": "line_range", "value": "L3-L7"}, "label": "原始對話",
            }],
        }

    def test_create_reopen_search_source_and_conflict(self) -> None:
        status, headers, body = self.request("PUT", "/api/notes/note_http", self.payload(), {"If-Match": "*"})
        self.assertEqual(status, 201, body)
        self.assertEqual(body["note"]["revision"], 1)
        etag = headers["ETag"]
        for name in SECURITY_HEADERS:
            self.assertIn(name, headers)

        status, get_headers, body = self.request("GET", "/api/notes/note_http")
        self.assertEqual(status, 200, body)
        self.assertEqual(get_headers["ETag"], etag)
        self.assertEqual(body["note"]["markdown"], self.payload()["markdown"])

        status, _, body = self.request("GET", "/api/notes?notebook_id=notebook_local&q=%E5%9B%A0%E6%9E%9C")
        self.assertEqual(status, 200, body)
        self.assertEqual(body["results"][0]["note_id"], "note_http")

        status, _, body = self.request("GET", "/api/note-sources/src_synthetic_causality_chat?locator=L3-L7")
        self.assertEqual(status, 200, body)
        self.assertEqual(body["document"]["focus"]["locator"]["value"], "L3-L7")
        self.assertIn("Correlation", body["document"]["focus"]["excerpt"])

        status, _, body = self.request(
            "PUT", "/api/notes/note_http", self.payload("save_http0002", "## 新文字\n"),
            {"If-Match": '"' + "0" * 64 + '"'},
        )
        self.assertEqual(status, 412, body)
        self.assertEqual(body["problem"]["code"], "stale_note")

    def test_missing_precondition_and_path_mismatch_are_rejected(self) -> None:
        status, _, body = self.request("PUT", "/api/notes/note_http", self.payload())
        self.assertEqual(status, 400, body)
        self.assertEqual(body["problem"]["code"], "if_match_required")
        payload = self.payload()
        payload["note_id"] = "note_other"
        status, _, body = self.request("PUT", "/api/notes/note_http", payload, {"If-Match": "*"})
        self.assertEqual(status, 400, body)
        self.assertEqual(body["problem"]["code"], "note_path_mismatch")

    def test_write_feature_flag_can_be_disabled_without_disabling_read(self) -> None:
        self.request("PUT", "/api/notes/note_http", self.payload(), {"If-Match": "*"})
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler_for(STORE, notes_root=self.notes_root))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            connection = http.client.HTTPConnection("127.0.0.1", server.server_address[1], timeout=3)
            connection.request("GET", "/api/notes/note_http")
            response = connection.getresponse()
            self.assertEqual(response.status, 200)
            response.read()
            connection.close()
            connection = http.client.HTTPConnection("127.0.0.1", server.server_address[1], timeout=3)
            connection.request("PUT", "/api/notes/note_http", body=b"{}", headers={"Content-Type": "application/json", "If-Match": "*"})
            response = connection.getresponse()
            self.assertEqual(response.status, 405)
            self.assertEqual(json.loads(response.read())["problem"]["code"], "note_writes_disabled")
            connection.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_source_anchor_works_with_zero_concepts_edges_or_evidence(self) -> None:
        zero_graph = self.notes_root / "source-only-store"
        shutil.copytree(STORE / "sources", zero_graph / "sources")
        shutil.copytree(STORE / "raw", zero_graph / "raw")
        for directory in ("concepts", "edges", "evidence", "learning-events"):
            (zero_graph / directory).mkdir()
        status, body = execute_note_source(
            zero_graph, "src_synthetic_causality_chat", "L3-L7",
        )
        self.assertEqual(status, 200, body)
        self.assertEqual(body["document"]["annotations"], [])
        self.assertEqual(body["document"]["focus"]["concept_ids"], [])
        self.assertEqual(body["document"]["focus"]["edge_ids"], [])


if __name__ == "__main__":
    unittest.main()
