from __future__ import annotations

import copy
import json
import socket
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest import mock

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from kgnote.review import build_prompt_from_context, build_reviewer_context
from kgnote.visualization import load_graph_view


ROOT = Path(__file__).resolve().parents[1]
STORE = ROOT / "fixtures/phase0-obsidian"


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


class ReviewerContextTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = load_graph_view(STORE).response["view"]

    def test_schema_and_correlation_golden_read_back(self):
        result = build_reviewer_context(self.model, "concept_correlation")
        self.assertEqual(result.status, "ready")
        context = result.context
        self.assertEqual(context["focus"]["label"], "Correlation")
        self.assertEqual(
            [node["id"] for node in context["neighborhood"]["nodes"]],
            ["concept_causation", "concept_confounder", "event_causality_question"],
        )
        self.assertEqual(len(context["neighborhood"]["links"]), 3)
        self.assertEqual(
            [item["id"] for item in context["evidence"]],
            [
                "evidence_apply_confounder",
                "evidence_define_correlation_causation",
                "evidence_question_correlation_causation",
            ],
        )
        self.assertEqual([source["id"] for source in context["sources"]], ["src_synthetic_causality_chat"])
        self.assertEqual(context["previous_confusion"], {"events": [], "links": [], "evidence_ids": []})
        self.assertNotIn("uri_or_path", json.dumps(context))

        schema = load_json(ROOT / "schemas/reviewer-context/v1/reviewer-context.schema.json")
        graph_schema = load_json(ROOT / "schemas/graph-read-model/v1/graph-read-model.schema.json")
        registry = Registry().with_resource(graph_schema["$id"], Resource.from_contents(graph_schema))
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema, registry=registry).validate(context)

    def test_only_explicit_semantics_become_previous_confusion(self):
        explicit = copy.deepcopy(self.model)
        event = next(node for node in explicit["nodes"] if node["kind"] == "learning_event")
        event["event_type"] = "confusion"
        result = build_reviewer_context(explicit, "concept_correlation")
        self.assertEqual([item["id"] for item in result.context["previous_confusion"]["events"]], [event["id"]])
        self.assertEqual(
            result.context["previous_confusion"]["evidence_ids"],
            sorted(event["evidence_ids"]),
        )

        neutral = copy.deepcopy(self.model)
        for node in neutral["nodes"]:
            if node["kind"] == "learning_event":
                node["event_type"] = "explanation"
        self.assertEqual(
            build_reviewer_context(neutral, "concept_correlation").context["previous_confusion"],
            {"events": [], "links": [], "evidence_ids": []},
        )

    def test_confusion_first_prompt_offers_distinction_and_does_not_erase_history(self):
        explicit = copy.deepcopy(self.model)
        event = next(node for node in explicit["nodes"] if node["kind"] == "learning_event")
        event["event_type"] = "confusion"
        before = copy.deepcopy(explicit)
        context = build_reviewer_context(explicit, "concept_correlation").context
        prompt = build_prompt_from_context(context)
        self.assertEqual(prompt["activity_type"], "distinction")
        self.assertEqual(set(prompt["confusion_pair"]), {"concept_correlation", "concept_causation"})
        self.assertIn("Correlation", prompt["question"])
        self.assertIn("Causation", prompt["question"])
        self.assertEqual(explicit, before)
        self.assertEqual(len(context["previous_confusion"]["events"]), 1)

    def test_rejects_unknown_event_focus_and_malformed_model_without_echo(self):
        self.assertEqual(build_reviewer_context(self.model, "concept_missing").problem.code, "unknown_concept")
        self.assertEqual(build_reviewer_context(self.model, "event_causality_question").problem.code, "focus_not_concept")
        malformed = copy.deepcopy(self.model)
        malformed["private learning body"] = "do not echo"
        result = build_reviewer_context(malformed, "concept_correlation")
        self.assertEqual(result.problem.code, "invalid_read_model")
        self.assertNotIn("do not echo", repr(result))

    def test_deterministic_copy_safe_frozen_and_no_io(self):
        original = copy.deepcopy(self.model)
        with mock.patch.object(Path, "write_text", side_effect=AssertionError("write forbidden")), \
             mock.patch.object(Path, "write_bytes", side_effect=AssertionError("write forbidden")), \
             mock.patch.object(socket, "create_connection", side_effect=AssertionError("network forbidden")), \
             mock.patch("urllib.request.urlopen", side_effect=AssertionError("network forbidden")):
            first = build_reviewer_context(self.model, "concept_correlation")
            second = build_reviewer_context(copy.deepcopy(self.model), "concept_correlation")
        self.assertEqual(first, second)
        self.assertEqual(self.model, original)
        changed = first.context
        changed["evidence"].clear()
        self.assertTrue(first.context["evidence"])
        with self.assertRaises(FrozenInstanceError):
            first.status = "rejected"


if __name__ == "__main__":
    unittest.main()
