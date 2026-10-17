from __future__ import annotations

import http.client
import hashlib
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

    def test_a_b_a_revision_tokens_remain_unique_and_original_token_is_stale(self) -> None:
        status, created = self.request("POST", "/api/library/sources", source_request(
            title="ABA", content="# ABA\n\nA\n",
            locator={"kind": "file_name", "value": "aba.md"},
        ))
        self.assertEqual(status, 201)
        source_id = created["source"]["source_id"]
        revision_a1 = created["source"]["current_revision_id"]
        status, second = self.request("POST", "/api/library/sources", source_request(
            source_id=source_id, expected_revision_id=revision_a1,
            title="ABA", content="# ABA\n\nB\n",
            locator={"kind": "file_name", "value": "aba.md"},
        ))
        self.assertEqual(status, 201)
        revision_b = second["source"]["current_revision_id"]
        status, third = self.request("POST", "/api/library/sources", source_request(
            source_id=source_id, expected_revision_id=revision_b,
            title="ABA", content="# ABA\n\nA\n",
            locator={"kind": "file_name", "value": "aba.md"},
        ))
        self.assertEqual(status, 201)
        revision_a2 = third["source"]["current_revision_id"]
        self.assertEqual(len({revision_a1, revision_b, revision_a2}), 3)
        status, current = self.request("GET", f"/api/library/sources/{source_id}")
        self.assertEqual(status, 200)
        self.assertEqual(current["revision"]["previous_revision_id"], revision_b)
        status, stale = self.request("POST", "/api/library/sources", source_request(
            source_id=source_id, expected_revision_id=revision_a1,
            title="ABA", content="# ABA\n\nC\n",
            locator={"kind": "file_name", "value": "aba.md"},
        ))
        self.assertEqual(status, 409)
        self.assertEqual(stale["problem"]["code"], "stale_source_revision")

    def test_bom_prefixed_markdown_round_trips_through_http_and_storage(self) -> None:
        content = "\ufeff# BOM source\n"
        selected_bytes = content.encode("utf-8")
        status, created = self.request("POST", "/api/library/sources", source_request(
            title="BOM source",
            content=content,
            locator={"kind": "file_name", "value": "bom.md"},
        ))
        self.assertEqual(status, 201)
        source = created["source"]
        raw_path = self.library / "sources" / source["source_id"] / "revisions" / f"{source['current_revision_id']}.md"
        self.assertEqual(raw_path.read_bytes(), selected_bytes)
        status, read_back = self.request("GET", f"/api/library/sources/{source['source_id']}")
        self.assertEqual(status, 200)
        self.assertEqual(read_back["content"].encode("utf-8"), selected_bytes)
        self.assertEqual(read_back["revision"]["content_sha256"], hashlib.sha256(selected_bytes).hexdigest())

        for file_name, blank in (("bom-only.md", "\ufeff"), ("bom-blank.md", "\ufeff  \n")):
            status, rejected = self.request("POST", "/api/library/sources", source_request(
                title="Blank BOM", content=blank,
                locator={"kind": "file_name", "value": file_name},
            ))
            self.assertEqual(status, 400)
            self.assertEqual(rejected["problem"]["code"], "empty_source")

        conversation = "\ufeffUser: Question.\n\nAssistant: Answer.\n"
        status, accepted = self.request("POST", "/api/library/sources", source_request(
            title="BOM conversation",
            content=conversation,
            source_kind="chatgpt_conversation",
            locator={"kind": "file_name", "value": "bom-chat.md"},
        ))
        self.assertEqual(status, 201)
        status, exact = self.request("GET", f"/api/library/sources/{accepted['source']['source_id']}")
        self.assertEqual(status, 200)
        self.assertEqual(exact["content"].encode("utf-8"), conversation.encode("utf-8"))
        self.assertEqual([span["role"] for span in exact["revision"]["speaker_spans"]], ["user", "assistant"])

    def test_html_comment_speaker_example_is_not_attributed_through_http(self) -> None:
        content = (
            "## User\nQuestion.\n\n## Assistant\n<!--\nUser: demonstration only\n-->\n"
            "Assistant explanation continues.\n"
        )
        status, accepted = self.request("POST", "/api/library/sources", source_request(
            title="Comment example",
            content=content,
            source_kind="chatgpt_conversation",
            locator={"kind": "file_name", "value": "comment-example.md"},
        ))
        self.assertEqual(status, 201)
        status, exact = self.request("GET", f"/api/library/sources/{accepted['source']['source_id']}")
        self.assertEqual(status, 200)
        self.assertEqual(exact["content"].encode("utf-8"), content.encode("utf-8"))
        self.assertEqual(
            [(span["role"], span["locator"]["value"]) for span in exact["revision"]["speaker_spans"]],
            [("user", "L1-L3"), ("assistant", "L4-L8")],
        )

    def test_lazy_block_quote_speaker_example_is_not_attributed_through_http(self) -> None:
        content = (
            "## User\nQuestion.\n\n## Assistant\n> User: quoted example\n"
            "User: lazy quoted continuation\n\nAssistant: real continuation\n"
        )
        status, accepted = self.request("POST", "/api/library/sources", source_request(
            title="Lazy quote example",
            content=content,
            source_kind="chatgpt_conversation",
            locator={"kind": "file_name", "value": "lazy-quote-example.md"},
        ))
        self.assertEqual(status, 201)
        status, exact = self.request("GET", f"/api/library/sources/{accepted['source']['source_id']}")
        self.assertEqual(status, 200)
        self.assertEqual(exact["content"].encode("utf-8"), content.encode("utf-8"))
        self.assertEqual(
            [(span["role"], span["locator"]["value"]) for span in exact["revision"]["speaker_spans"]],
            [("user", "L1-L3"), ("assistant", "L4-L7"), ("assistant", "L8-L8")],
        )


if __name__ == "__main__":
    unittest.main()
