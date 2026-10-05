from __future__ import annotations

import copy
import http.client
import json
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path

from scripts.serve_graph_view import handler_for


ROOT = Path(__file__).resolve().parents[1]
STORE = ROOT / "fixtures/phase0-obsidian"
MODEL = json.loads((ROOT / "web/fixtures/os-overview-guided-map.json").read_text())
OVERLAY = json.loads((ROOT / "web/fixtures/os-overview-claim-review-overlay.json").read_text())


class PracticeHttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory()
        cls.attempts_root = Path(cls.temporary.name) / "learning"
        cls.attempts_root.mkdir()
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), handler_for(
            STORE, guided_map_model=MODEL, guided_review_root=Path(cls.temporary.name),
            claim_review_overlay=OVERLAY, attempts_root=cls.attempts_root,
        ))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.port = cls.server.server_address[1]

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown(); cls.server.server_close(); cls.thread.join(timeout=2); cls.temporary.cleanup()

    def request(self, method: str, path: str, payload: dict | None = None) -> tuple[int, dict]:
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=3)
        body = json.dumps(payload).encode() if payload is not None else None
        headers = {"Content-Type": "application/json"} if payload is not None else {}
        connection.request(method, path, body=body, headers=headers)
        response = connection.getresponse()
        result = response.status, json.loads(response.read())
        connection.close()
        return result

    def payload(self, item: dict, *, state: str, response: str) -> dict:
        submitted = state == "submitted"
        return {
            "schema_version": "kgnote.attempt-save-request.v1",
            "attempt_id": "attempt_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "review_item_id": item["item_id"], "item_revision": item["revision"],
            "learning_unit_id": item["learning_unit_id"], "activity_type": item["activity_type"],
            "state": state, "started_at": "2026-09-20T01:00:00+00:00",
            "submitted_at": "2026-09-20T01:01:00+00:00" if submitted else None,
            "raw_response": response, "confidence": None, "hint_events": [], "support_state": "unassisted",
            "answer_exposure_state": "revealed_after_submission" if submitted else "hidden",
            "outcome": "INCORRECT" if submitted else None,
            "correction_feedback": "人工對照 rubric。" if submitted else None,
            "entry_context": {"route": "/practice.html", "from_route": "/learn.html", "entry_kind": "voluntary_practice", "due_id": None},
            "source_refs": item["source_refs"], "claim_refs": [item["claim_ref"]], "evidence_refs": item["evidence_refs"],
        }

    def test_safe_items_submit_reveal_retry_semantics_and_reload_readback(self) -> None:
        status, items_body = self.request("GET", "/api/practice-items")
        self.assertEqual(status, 200)
        serialized = json.dumps(items_body["items"], ensure_ascii=False)
        self.assertNotIn("向核心提出", serialized)
        self.assertFalse(any("interrupt_driver" in item["item_id"] for item in items_body["items"]))
        item = next(item for item in items_body["items"] if item["item_id"] == "item_relation_edge_os_application_system_call")
        draft = self.payload(item, state="draft", response="錯的 draft")
        path = f"/api/attempts/{draft['attempt_id']}"
        self.assertEqual(self.request("PUT", path, draft)[0], 201)
        submitted = self.payload(item, state="submitted", response="不知道")
        status, body = self.request("PUT", path, submitted)
        self.assertEqual(status, 200, body)
        self.assertEqual(body["attempt"]["raw_response"], "不知道")
        self.assertIn("向核心提出", body["reveal"]["canonical_answer"])
        self.assertEqual(self.request("PUT", path, copy.deepcopy(submitted))[1]["status"], "unchanged")
        changed = copy.deepcopy(submitted); changed["raw_response"] = "不同的重送答案"
        self.assertEqual(self.request("PUT", path, changed)[0], 409)
        status, history = self.request("GET", f"/api/attempts?learning_unit_id={item['learning_unit_id']}")
        self.assertEqual(status, 200)
        self.assertEqual(history["attempts"][0]["raw_response"], "不知道")

    def test_stale_and_blocked_refs_fail_without_creating_attempt(self) -> None:
        _, items_body = self.request("GET", "/api/practice-items")
        item = items_body["items"][0]
        stale = self.payload(item, state="draft", response="草稿")
        stale["attempt_id"] = "attempt_bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
        stale["item_revision"] = 999
        status, body = self.request("PUT", f"/api/attempts/{stale['attempt_id']}", stale)
        self.assertEqual(status, 409)
        self.assertEqual(body["problem"]["code"], "stale_practice_item")
        self.assertFalse((self.attempts_root / "attempts" / f"{stale['attempt_id']}.json").exists())


if __name__ == "__main__":
    unittest.main()
