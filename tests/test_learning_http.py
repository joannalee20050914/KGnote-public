from __future__ import annotations

import http.client
import copy
import json
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path

from kgnote.learning import load_learning_unit_catalog
from scripts.serve_graph_view import handler_for

ROOT = Path(__file__).resolve().parents[1]


class LearningHttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory(); cls.attempts = Path(cls.temporary.name)
        catalog = load_learning_unit_catalog(ROOT / "web/fixtures/learning-units.json").payload["bundles"]
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), handler_for(ROOT / "fixtures/phase0-obsidian", attempts_root=cls.attempts, learning_units=catalog))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True); cls.thread.start(); cls.port = cls.server.server_address[1]

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown(); cls.server.server_close(); cls.thread.join(timeout=2); cls.temporary.cleanup()

    def get(self, path: str) -> tuple[int, dict]:
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=3); connection.request("GET", path); response = connection.getresponse(); value = response.status, json.loads(response.read()); connection.close(); return value

    def post(self, path: str, value: dict) -> tuple[int, dict]:
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=3); connection.request("POST", path, json.dumps(value), {"Content-Type":"application/json"}); response = connection.getresponse(); result = response.status, json.loads(response.read()); connection.close(); return result

    def test_catalog_bundle_practice_and_empty_due_are_bounded(self) -> None:
        status, catalog = self.get("/api/learning-units"); self.assertEqual(status, 200); self.assertEqual({item["slug"] for item in catalog["units"]}, {"os", "bitepacer", "pvz"})
        status, bundle = self.get("/api/learning-units/os"); self.assertEqual(status, 200); self.assertNotIn("practice_supplement", bundle)
        status, practice = self.get("/api/practice-items?unit=bitepacer"); self.assertEqual(status, 200); self.assertNotIn("canonical_answer", json.dumps(practice))
        self.assertEqual(self.get("/api/due")[1]["items"], [])
        self.assertEqual(self.get("/api/learning-units/unknown")[0], 404)

    def test_sc01_zero_note_catalog_read_and_practice_paths_have_no_note_gate(self) -> None:
        # This server intentionally has no notes_root and no note write capability.
        self.assertEqual(self.get("/api/learning-units/os")[0], 200)
        self.assertEqual(self.get("/api/practice-items?unit=os")[0], 200)
        self.assertEqual(self.get("/api/notes?notebook_id=x&q=x")[0], 404)

    def test_sc02_sc18_soak_reveal_skip_is_separate_from_attempt_and_due(self) -> None:
        status, soak = self.get("/api/soak-items?unit=os"); self.assertEqual(status, 200)
        item=soak["items"][0]
        self.assertIn("answer",item)
        for index,kind in enumerate(("presented","answer_revealed","skipped")):
            request={"schema_version":"kgnote.exposure-save-request.v1","event_id":f"exposure_{index:032x}","exposure_session_id":"soak_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","learning_unit_id":soak["learning_unit_id"],"item_id":item["item_id"],"concept_id":item["concept_id"],"kind":kind,"occurred_at":f"2026-09-20T02:3{index}:00Z","source_refs":item["source_refs"]}
            self.assertIn(self.post("/api/exposures",request)[0],{200,201})
        events=self.get(f"/api/exposures?learning_unit_id={soak['learning_unit_id']}")[1]["events"]
        self.assertEqual({event["kind"] for event in events},{"presented","answer_revealed","skipped"})
        self.assertEqual(self.get(f"/api/attempts?learning_unit_id={soak['learning_unit_id']}")[1]["attempts"],[])
        self.assertEqual(self.get("/api/due")[1]["items"],[])
        practice=self.get("/api/practice-items?unit=os")[1]
        self.assertIn(item["related_practice_item_id"],{candidate["item_id"] for candidate in practice["items"]})
        self.assertNotIn("canonical_answer",json.dumps(practice))
        forged={"schema_version":"kgnote.exposure-save-request.v1","event_id":"exposure_ffffffffffffffffffffffffffffffff","exposure_session_id":"soak_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","learning_unit_id":soak["learning_unit_id"],"item_id":item["item_id"],"concept_id":"concept_forged","kind":"presented","occurred_at":"2026-09-20T02:40:00Z","source_refs":item["source_refs"]}
        self.assertEqual(self.post("/api/exposures",forged)[0],409)

    def test_sc03_exact_resume_context_round_trips_and_enriches_activity(self) -> None:
        bundle=self.get("/api/learning-units/os")[1]; nodes=bundle["structure"]["nodes"]; leaf=next(node for node in nodes if node["parent_id"] is not None); chain=[];current=leaf
        by_id={node["id"]:node for node in nodes}
        while current is not None: chain.insert(0,{"node_id":current["id"],"title":current["title"]});current=by_id.get(current["parent_id"])
        request={"schema_version":"kgnote.resume-context-save-request.v1","event_id":"resume_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","learning_unit_id":bundle["unit"]["unit_id"],"unit_slug":"os","source_scope":{"source_id":bundle["model"]["source"]["id"],"locator":leaf["source_anchors"][0]["locator"]["value"]},"structural_breadcrumb":chain,"selected":{"kind":"structure","id":leaf["id"],"label":leaf["title"]},"unresolved_question":"這個子題和上一層的差別是什麼？","occurred_at":"2026-09-20T03:00:00Z"}
        self.assertEqual(self.post("/api/resume-contexts",request)[0],201)
        status,value=self.get(f"/api/resume-contexts?learning_unit_id={bundle['unit']['unit_id']}");self.assertEqual(status,200)
        self.assertEqual(value["context"]["structural_breadcrumb"],chain);self.assertEqual(value["context"]["unresolved_question"],request["unresolved_question"])
        self.assertIn("latest_attempt",value);self.assertIn("latest_exposure",value)
        stale=copy.deepcopy(request);stale["event_id"]="resume_bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb";stale["structural_breadcrumb"][-1]["title"]="forged"
        self.assertEqual(self.post("/api/resume-contexts",stale)[0],409)
        reordered=copy.deepcopy(request);reordered["event_id"]="resume_cccccccccccccccccccccccccccccccc";reordered["structural_breadcrumb"].reverse()
        self.assertEqual(self.post("/api/resume-contexts",reordered)[0],409)


if __name__ == "__main__":
    unittest.main()
