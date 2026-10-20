import copy
import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from kgnote.contracts import build_linking_phrase_candidates
from kgnote.pipeline import build_phrase_review_preview


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_ROOT = ROOT / "schemas/linking-phrase/v1"
MAP = json.loads((ROOT / "tests/fixtures/guided-map/v1/bitepacer-golden.json").read_text())
SOURCE_LINES = (ROOT / "web/fixtures/bitepacer-mini-network-lesson.md").read_text().splitlines()


def source_excerpt(locator):
    start, end = (int(part[1:]) for part in locator["value"].split("-"))
    return [{"number": number, "text": SOURCE_LINES[number - 1]} for number in range(start, end + 1)]


def context():
    evidence = {item["id"]: item for item in MAP["evidence"]}
    edges = []
    for item in MAP["propositions"][:2]:
        edges.append({
            "edge_id": item["edge_id"], "edge_class": "canonical",
            "subject_concept_id": item["subject_concept_id"], "subject_label": item["subject_label"],
            "canonical_relation": item["canonical_relation"],
            "object_concept_id": item["object_concept_id"], "object_label": item["object_label"],
            "evidence": [{
                "id": evidence[evidence_id]["id"], "source_id": evidence[evidence_id]["source_id"],
                "locator": evidence[evidence_id]["locator"], "proposition": evidence[evidence_id]["proposition"],
                "review_status": evidence[evidence_id]["review_status"],
                "source_excerpt": source_excerpt(evidence[evidence_id]["locator"]),
            } for evidence_id in item["evidence_ids"]],
        })
    return {
        "schema_version": "kgnote.linking-phrase-context.v1",
        "learning_unit_id": MAP["learning_unit"]["id"],
        "graph_snapshot_sha256": MAP["graph_snapshot_sha256"],
        "display_locale": MAP["learning_unit"]["display_locale"],
        "focus_question": MAP["learning_unit"]["focus_question"], "edges": edges,
    }


def response(value=None):
    value = value or context()
    phrases = {item["edge_id"]: item["linking_phrase"] for item in MAP["propositions"]}
    return json.dumps({"proposals": [
        {"edge_id": edge["edge_id"], "linking_phrase": phrases[edge["edge_id"]]}
        for edge in value["edges"]
    ]}, ensure_ascii=False)


class LinkingPhraseCandidateContractTests(unittest.TestCase):
    def build(self, value=None, raw=None):
        value = value or context()
        return build_linking_phrase_candidates(
            value, raw if raw is not None else response(value), provider="fixture-provider",
            model="fixture-model", prompt_version="linking-phrase.prompt.v1",
            generated_at="2026-09-16T20:00:00+08:00",
        )

    def test_schemas_and_bitepacer_candidate_read_back(self):
        for name in (
            "context.schema.json", "response.schema.json", "candidate-set.schema.json",
            "decisions.schema.json", "reviewed-set.schema.json",
        ):
            Draft202012Validator.check_schema(json.loads((SCHEMA_ROOT / name).read_text()))
        result = self.build()
        self.assertEqual(result.status, "accepted")
        payload = result.payload
        Draft202012Validator(json.loads((SCHEMA_ROOT / "candidate-set.schema.json").read_text())).validate(payload)
        self.assertEqual(len(payload["candidates"]), 2)
        self.assertTrue(all(item["review_status"] == "pending" for item in payload["candidates"]))
        self.assertEqual(payload["candidates"][0]["subject_label"], "連接埠")
        self.assertEqual(payload["candidates"][0]["object_label"], "Flask 路由")
        self.assertEqual(payload["candidates"][0]["evidence_ids"], context()["edges"][0]["evidence"] and [item["id"] for item in context()["edges"][0]["evidence"]])
        self.assertEqual(len(payload["context_sha256"]), 64)
        self.assertEqual(len(payload["raw_response_sha256"]), 64)

    def test_response_cannot_forge_context_and_set_must_match(self):
        original = json.loads(response())
        variants = []
        forged = copy.deepcopy(original); forged["proposals"][0]["subject_label"] = "反轉"; variants.append((forged, "invalid_response"))
        duplicate = copy.deepcopy(original); duplicate["proposals"][1]["edge_id"] = duplicate["proposals"][0]["edge_id"]; variants.append((duplicate, "duplicate_edge_proposal"))
        missing = copy.deepcopy(original); missing["proposals"].pop(); variants.append((missing, "proposal_set_mismatch"))
        extra = copy.deepcopy(original); extra["proposals"].append({"edge_id": "edge_extra", "linking_phrase": "額外關係"}); variants.append((extra, "proposal_set_mismatch"))
        generic = copy.deepcopy(original); generic["proposals"][0]["linking_phrase"] = "相關"; variants.append((generic, "generic_linking_phrase"))
        for body, code in variants:
            with self.subTest(code=code):
                result = self.build(raw=json.dumps(body, ensure_ascii=False))
                self.assertEqual(result.status, "rejected")
                self.assertEqual(result.problem_code, code)
                self.assertIsNone(result.payload)

    def test_context_and_output_are_deterministic_copy_safe_and_staging_only(self):
        value = context()
        original = copy.deepcopy(value)
        first = self.build(value).payload
        second = self.build(value).payload
        self.assertEqual(first, second)
        first["candidates"][0]["subject_label"] = "mutated"
        self.assertNotEqual(first, second)
        self.assertEqual(value, original)
        self.assertTrue(all(item["review_status"] == "pending" for item in second["candidates"]))

        value["edges"].reverse()
        result = self.build(value, response(value))
        self.assertEqual(result.problem_code, "non_deterministic_context")

        value = context()
        value["edges"][0]["evidence"][0]["source_excerpt"][0]["number"] += 1
        result = self.build(value, response(value))
        self.assertEqual(result.problem_code, "evidence_excerpt_drift")

    def test_malformed_generic_and_invalid_provenance_fail_closed(self):
        self.assertEqual(self.build(raw="{bad").problem_code, "invalid_json")
        self.assertEqual(self.build(raw='{"proposals":[],"proposals":[]}').problem_code, "invalid_json")
        result = build_linking_phrase_candidates(
            context(), response(), provider="", model="fixture", prompt_version="v1",
            generated_at="not-a-date",
        )
        self.assertEqual(result.problem_code, "invalid_provenance")

    def test_human_review_actions_are_complete_and_evidence_gated(self):
        candidate_set = self.build().payload
        edge_ids = [item["edge_id"] for item in candidate_set["candidates"]]
        decisions = {
            "candidate_set_id": candidate_set["id"],
            "decisions": [
                {"edge_id": edge_ids[0], "action": "accept"},
                {"edge_id": edge_ids[1], "action": "correct", "corrected_linking_phrase": "由……轉送到"},
            ],
        }
        reviewed = build_phrase_review_preview(
            candidate_set, decisions, reviewed_at="2026-09-16T21:00:00+08:00",
        )
        self.assertEqual(reviewed.payload["summary"], {
            "accepted": 1, "corrected": 1, "rejected": 0, "guided_map_ready": 2,
        })
        self.assertTrue(all(
            item["guided_map_promotion_eligible"] for item in reviewed.payload["decisions"]
        ))

        unreviewed = copy.deepcopy(candidate_set)
        unreviewed["candidates"][0]["evidence_review_statuses"] = ["unreviewed"]
        pending = build_phrase_review_preview(
            unreviewed, decisions, reviewed_at="2026-09-16T21:00:00+08:00",
        )
        self.assertEqual(pending.payload["summary"]["guided_map_ready"], 1)
        self.assertFalse(pending.payload["decisions"][0]["guided_map_promotion_eligible"])

        rejected_decisions = {
            "candidate_set_id": candidate_set["id"],
            "decisions": [{"edge_id": edge_id, "action": "reject"} for edge_id in edge_ids],
        }
        rejected = build_phrase_review_preview(
            candidate_set, rejected_decisions, reviewed_at="2026-09-16T21:00:00+08:00",
        )
        self.assertEqual(rejected.payload["summary"]["rejected"], 2)
        self.assertTrue(all(item["effective_linking_phrase"] is None for item in rejected.payload["decisions"]))

    def test_human_review_rejects_partial_duplicate_and_generic_decisions(self):
        candidate_set = self.build().payload
        edge_ids = [item["edge_id"] for item in candidate_set["candidates"]]
        invalid = (
            [{"edge_id": edge_ids[0], "action": "accept"}],
            [{"edge_id": edge_ids[0], "action": "accept"}] * 2,
            [
                {"edge_id": edge_ids[0], "action": "correct", "corrected_linking_phrase": "相關"},
                {"edge_id": edge_ids[1], "action": "accept"},
            ],
        )
        for decisions in invalid:
            with self.subTest(decisions=decisions), self.assertRaises(ValueError):
                build_phrase_review_preview(
                    candidate_set,
                    {"candidate_set_id": candidate_set["id"], "decisions": decisions},
                    reviewed_at="2026-09-16T21:00:00+08:00",
                )


if __name__ == "__main__":
    unittest.main()
