from __future__ import annotations

import http.client
import json
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path

from scripts.serve_graph_view import handler_for


ROOT = Path(__file__).resolve().parents[1]
STORE = ROOT / "fixtures" / "phase0-obsidian"


def source_request(**changes) -> dict:
    value = {
        "schema_version": "kgnote.source-import.v2",
        "source_id": None,
        "expected_revision_id": None,
        "title": "DNS 入門",
        "content": "# DNS\n\nA resolver maps a name to an address.\n",
        "source_kind": "document",
        "locator": {"kind": "file_name", "value": "dns.md"},
    }
    value.update(changes)
    return value


class SourceLibraryHttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory()
        cls.library = Path(cls.temporary.name) / "source-library"
        cls.server = ThreadingHTTPServer(
            ("127.0.0.1", 0),
            handler_for(STORE, source_library_root=cls.library),
        )
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.port = cls.server.server_address[1]

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)
        cls.temporary.cleanup()

    def request(self, method: str, path: str, value=None, *, content_type: str = "application/json") -> tuple[int, dict]:
        body = value if isinstance(value, bytes) else (json.dumps(value).encode("utf-8") if value is not None else None)
        headers = {"Content-Type": content_type} if body is not None else {}
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=3)
        connection.request(method, path, body=body, headers=headers)
        response = connection.getresponse()
        result = response.status, json.loads(response.read())
        connection.close()
        return result

    def test_single_batch_list_update_and_exact_revision_read_back(self) -> None:
        status, created = self.request("POST", "/api/library/sources", source_request())
        self.assertEqual(status, 201)
        source = created["source"]
        source_id = source["source_id"]
        revision_one = source["current_revision_id"]

        status, listing = self.request("GET", "/api/library/sources")
        self.assertEqual(status, 200)
        self.assertIn(source_id, {item["source_id"] for item in listing["sources"]})

        status, exact = self.request("GET", f"/api/library/sources/{source_id}?revision={revision_one}")
        self.assertEqual(status, 200)
        self.assertEqual(exact["content"], source_request()["content"])
        self.assertEqual(exact["revision"]["revision_id"], revision_one)

        update = source_request(
            source_id=source_id,
            expected_revision_id=revision_one,
            content="# DNS\n\nUpdated source bytes.\n",
        )
        status, updated = self.request("POST", "/api/library/sources", update)
        self.assertEqual(status, 201)
        revision_two = updated["source"]["current_revision_id"]
        self.assertNotEqual(revision_one, revision_two)
        self.assertEqual(self.request("GET", f"/api/library/sources/{source_id}?revision={revision_one}")[1]["content"], source_request()["content"])

        batch = {
            "schema_version": "kgnote.source-import-batch.v1",
            "sources": [
                source_request(title="A", content="# A\n", locator={"kind": "file_name", "value": "a.md"}),
                source_request(title="B", content="# B\n", locator={"kind": "file_name", "value": "b.md"}),
            ],
        }
        status, applied = self.request("POST", "/api/library/sources", batch)
        self.assertEqual(status, 201)
        self.assertEqual(len(applied["results"]), 2)

    def test_stale_malformed_and_disabled_routes_fail_closed_without_echo(self) -> None:
        status, created = self.request("POST", "/api/library/sources", source_request(
            title="安全測試", content="# Safe\n", locator={"kind": "file_name", "value": "safe.md"},
        ))
        self.assertEqual(status, 201)
        source_id = created["source"]["source_id"]
        stale = source_request(
            source_id=source_id,
            expected_revision_id="revision_000000000000000000000000",
            title="安全測試",
            content="# Safe\n\nprivate-value-must-not-echo\n",
            locator={"kind": "file_name", "value": "safe.md"},
        )
        status, rejected = self.request("POST", "/api/library/sources", stale)
        self.assertEqual(status, 409)
        self.assertEqual(rejected["problem"]["code"], "stale_source_revision")
        self.assertNotIn("private-value", json.dumps(rejected))

        status, rejected = self.request("POST", "/api/library/sources", b"\xff")
        self.assertEqual(status, 400)
        self.assertEqual(rejected["problem"]["code"], "invalid_json")
        self.assertEqual(self.request("GET", "/api/library/sources/../private")[0], 400)

        disabled = ThreadingHTTPServer(("127.0.0.1", 0), handler_for(STORE))
        thread = threading.Thread(target=disabled.serve_forever, daemon=True)
        thread.start()
        try:
            connection = http.client.HTTPConnection("127.0.0.1", disabled.server_address[1], timeout=3)
            connection.request("GET", "/api/library/sources")
            response = connection.getresponse()
            self.assertEqual(response.status, 404)
            response.read()
            connection.close()
        finally:
            disabled.shutdown()
            disabled.server_close()
            thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
