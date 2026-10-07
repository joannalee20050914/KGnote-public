from __future__ import annotations

import copy
import re
import socket
import tempfile
import unittest
from unittest import mock
from pathlib import Path

from kgnote.personal_alpha import (
    build_learning_workspace_preview,
    materialize_learning_workspace,
    project_learner_workspace,
)


ROOT = Path(__file__).resolve().parents[1]
NETWORK_PATH = (
    ROOT / "tests" / "fixtures" / "personal-alpha" / "hierarchical" / "network-path.md"
)
GLOSSARY = ROOT / "tests" / "fixtures" / "personal-alpha" / "glossary" / "harmony-glossary.md"
PROCEDURAL = ROOT / "tests" / "fixtures" / "personal-alpha" / "procedural" / "seed-starting.md"
GOLDEN = ROOT / "tests" / "fixtures" / "personal-alpha" / "golden"

KNOWN_BAD_PRIMARY_PATTERNS = (
    "Unreviewed concept candidate",
    "Signals:",
    "Marked mentions:",
    "concept_candidate_",
    "kgnote_schema",
    "Source SHA-256",
    "Extractor:",
    "projection_version",
)


def primary_body(markdown: str) -> str:
    """Remove YAML and collapsed callouts before checking the normal reading flow."""

    lines = markdown.splitlines()
    if lines and lines[0] == "---":
        end = lines.index("---", 1)
        lines = lines[end + 1 :]
    visible: list[str] = []
    in_collapsed_callout = False
    for line in lines:
        if re.match(r"^> \[![^]]+\]-", line):
            in_collapsed_callout = True
            continue
        if in_collapsed_callout and line.startswith(">"):
            continue
        in_collapsed_callout = False
        visible.append(line)
    return "\n".join(visible)


class PersonalAlphaPresentationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.vault = self.root / "vault"
        self.vault.mkdir()
        preview = build_learning_workspace_preview(NETWORK_PATH, space="networking")
        result = materialize_learning_workspace(preview, self.vault)
        self.workspace = Path(result.workspace_path)

    def read(self, relative: str) -> str:
        return (self.workspace / relative).read_text(encoding="utf-8")

    def concept_note(self, title: str) -> tuple[Path, str]:
        for path in (self.workspace / "Concepts").glob("*.md"):
            text = path.read_text(encoding="utf-8")
            if f"# {title}\n" in text:
                return path, text
        self.fail(f"No generated Concept note found for {title}")

    def test_golden_fixtures_are_independent_hand_authored_oracles(self):
        expected = {
            "network-path-start-here.md": (
                "# How a browser reaches a local service",
                "## Learning path",
                "## Key concepts",
                "## Key relationships",
                "## Continue",
                "## My notes",
            ),
            "network-path-port.md": (
                "# Port",
                "## In this material",
                "## Related concepts",
                "[!quote]- Source evidence",
            ),
            "network-path-relationships.md": (
                "# Key relationships",
                "## HTTP request → network connection",
                "## Port → service endpoint",
                "## HTTP response ↔ status code",
            ),
        }
        for filename, ordered in expected.items():
            text = (GOLDEN / filename).read_text(encoding="utf-8")
            offsets = [text.index(fragment) for fragment in ordered]
            self.assertEqual(offsets, sorted(offsets), filename)

    def test_start_here_is_a_learning_entry_not_a_debug_dashboard(self):
        text = self.read("Start Here.md")
        body = primary_body(text)
        for required in (
            "Learning goal",
            "Learning path",
            "Start reading",
            "Key concepts",
            "Key relationships",
            "Continue",
            "My notes",
        ):
            self.assertIn(required, body)
        self.assertLess(body.index("Learning goal"), body.index("Learning path"))
        self.assertNotIn("[[Evidence|", body)
        for forbidden in KNOWN_BAD_PRIMARY_PATTERNS:
            self.assertNotIn(forbidden, body)

    def test_port_teaches_source_scoped_meaning_before_audit_details(self):
        _, text = self.concept_note("Port")
        body = primary_body(text)
        self.assertIn("unreviewed candidate connecting **Port**", body)
        self.assertIn("This source does not provide a broader standalone definition", body)
        self.assertIn("## In this material", body)
        self.assertIn("## Related concepts", body)
        self.assertNotIn("identifies the host", body)
        self.assertIn("[[service endpoint]] — has an unreviewed source-linked candidate", body)
        self.assertIn("[!quote]- Source evidence", text)
        for forbidden in (
            "## Why it is included",
            "Signals:",
            "Marked mentions:",
            "Unreviewed concept candidate",
        ):
            self.assertNotIn(forbidden, body)

    def test_relationships_lead_with_readable_propositions_and_plain_uncertainty(self):
        text = self.read("Relationships.md")
        body = primary_body(text)
        self.assertIn("# Key relationships", body)
        self.assertIn("HTTP request", body)
        self.assertIn("network connection", body)
        self.assertIn("Port", body)
        self.assertIn("service endpoint", body)
        self.assertNotIn("**requires**", body)
        self.assertNotIn("**maps to**", body)
        self.assertIn(
            "does not establish a more precise relationship", body.replace("**", "")
        )
        self.assertNotIn("- Status:", body)
        self.assertNotIn("- Why included:", body)

    def test_evidence_is_reachable_but_not_a_mandatory_learning_path_step(self):
        start = primary_body(self.read("Start Here.md"))
        self.assertTrue((self.workspace / "Evidence.md").is_file())
        learning_path = start.split("## Learning path", 1)[1].split("## Key concepts", 1)[0]
        self.assertNotIn("Evidence", learning_path)
        self.assertNotIn("Structure", learning_path)

    def test_projected_paths_are_human_readable_and_continuation_is_user_owned(self):
        expected = {
            "IP address.md",
            "network connection.md",
            "HTTP request.md",
            "Port.md",
            "service endpoint.md",
            "HTTP response.md",
            "status code.md",
        }
        self.assertTrue(expected.issubset({path.name for path in (self.workspace / "Concepts").glob("*.md")}))
        continuation = self.workspace / "Continue Here.md"
        self.assertTrue(continuation.is_file())
        text = continuation.read_text(encoding="utf-8")
        for field in (
            "Resume link:",
            "Current note:",
            "Current section:",
            "Next:",
            "Question to revisit:",
        ):
            self.assertIn(field, text)
        self.assertIn("never infers progress from recency, clicks, or time", text)
        self.assertIn("heading or block link", text)


class LearnerProjectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.preview = build_learning_workspace_preview(NETWORK_PATH, space="networking")

    def test_projection_is_pure_deterministic_copy_safe_and_identity_preserving(self):
        payload = copy.deepcopy(self.preview.as_dict())
        original = copy.deepcopy(payload)
        with (
            mock.patch("builtins.open", side_effect=AssertionError("unexpected file I/O")),
            mock.patch.object(
                socket,
                "create_connection",
                side_effect=AssertionError("unexpected network I/O"),
            ),
        ):
            first = project_learner_workspace(payload)
            second = project_learner_workspace(payload)
        self.assertEqual(payload, original)
        self.assertEqual(first.as_dict(), second.as_dict())
        model = first.as_dict()
        self.assertEqual(
            model["canonical_ids"]["concepts"],
            [item["id"] for item in payload["concepts"]],
        )
        self.assertEqual(
            model["canonical_ids"]["relations"],
            [item["id"] for item in payload["relations"]],
        )
        self.assertEqual(
            model["canonical_ids"]["evidence"],
            [item["id"] for item in payload["evidence"]],
        )
        model["concepts"].clear()
        self.assertTrue(first.as_dict()["concepts"])

    def test_projection_groups_duplicate_learner_evidence_without_deleting_ids(self):
        model = project_learner_workspace(self.preview.payload).as_dict()
        grouped_ids = [
            evidence_id
            for group in model["evidence_groups"]
            for evidence_id in group["evidence_ids"]
        ]
        self.assertEqual(
            sorted(grouped_ids),
            sorted(item["id"] for item in self.preview.payload["evidence"]),
        )
        self.assertLess(len(model["evidence_groups"]), len(grouped_ids))

    def test_projected_filenames_handle_illegal_reserved_casefold_and_unicode_collisions(self):
        payload = self.preview.as_dict()
        labels = [
            "Port/HTTP",
            "CON",
            "Alpha",
            "alpha",
            "Café",
            "Cafe\u0301",
            "Index",
        ]
        for concept, label in zip(payload["concepts"], labels, strict=True):
            concept["canonical_name_candidate"] = label
        model = project_learner_workspace(payload).as_dict()
        paths = {item["label"]: item["path"] for item in model["concepts"]}
        self.assertEqual(paths["Port/HTTP"], "Concepts/Port-HTTP.md")
        self.assertEqual(paths["CON"], "Concepts/CON concept.md")
        self.assertIn(" — ", paths["Alpha"])
        self.assertIn(" — ", paths["alpha"])
        self.assertIn(" — ", paths["Café"])
        self.assertIn(" — ", paths["Cafe\u0301"])
        self.assertIn(" — ", paths["Index"])
        keys = [
            path.encode("utf-8").decode("utf-8").casefold()
            for path in paths.values()
        ]
        self.assertEqual(len(keys), len(set(keys)))

    def test_three_source_shapes_keep_distinct_navigation_semantics(self):
        hierarchical = project_learner_workspace(self.preview.payload).as_dict()
        glossary = project_learner_workspace(
            build_learning_workspace_preview(GLOSSARY).payload
        ).as_dict()
        procedural = project_learner_workspace(
            build_learning_workspace_preview(PROCEDURAL).payload
        ).as_dict()

        self.assertEqual(hierarchical["source_shape"], "hierarchical")
        self.assertTrue(hierarchical["structure_inline"])
        self.assertTrue(hierarchical["structure"])
        self.assertTrue(
            all(not item["knowledge_edge_created"] for item in hierarchical["structure"])
        )
        self.assertEqual(glossary["source_shape"], "heading_free")
        self.assertEqual(glossary["structure"], [])
        self.assertEqual(glossary["source"]["title"], "Harmony glossary")
        glossary_explanations = {
            item["label"]: item["explanation"] for item in glossary["concepts"]
        }
        self.assertIn("is a three-note chord", glossary_explanations["Triad"])
        self.assertIn("refers to notes heard", glossary_explanations["Chord"])
        self.assertNotIn("causes", {item["relation"] for item in glossary["relationships"]})
        self.assertEqual(procedural["source_shape"], "procedural")
        self.assertIn("Fill a tray", procedural["learning_path"][0])
        self.assertIn("Record temperature and germination together", procedural["learning_path"][-1])
        self.assertNotIn("causes", {item["relation"] for item in procedural["relationships"]})

    def test_definition_and_unreviewed_relation_do_not_leak_as_settled_truth(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "adversarial.md"
            source.write_text(
                "# Systems\n\n**Cache** and **Database** are components.\n\n"
                "**Database**: stores durable records.\n\n**Client** requires **Server**.\n",
                encoding="utf-8",
            )
            preview = build_learning_workspace_preview(source)
            vault = root / "vault"
            vault.mkdir()
            result = materialize_learning_workspace(preview, vault)
            workspace = Path(result.workspace_path)
            cache_note = next(
                path for path in (workspace / "Concepts").glob("*.md")
                if "# Cache\n" in path.read_text(encoding="utf-8")
            ).read_text(encoding="utf-8")
            relationships = (workspace / "Relationships.md").read_text(encoding="utf-8")
            client_note = next(
                path for path in (workspace / "Concepts").glob("*.md")
                if "# Client\n" in path.read_text(encoding="utf-8")
            ).read_text(encoding="utf-8")
            server_note = next(
                path for path in (workspace / "Concepts").glob("*.md")
                if "# Server\n" in path.read_text(encoding="utf-8")
            ).read_text(encoding="utf-8")
        self.assertNotIn("stores durable records", cache_note)
        self.assertIn("still unreviewed", relationships)
        self.assertNotIn("## Client → Server", relationships)
        self.assertNotIn("]] **requires** [[", relationships)
        self.assertIn("unreviewed candidate", client_note)
        self.assertIn("unreviewed candidate", server_note)
        self.assertNotIn("**Client** requires **Server**", primary_body(client_note))
        self.assertNotIn("**Server** is required by **Client**", primary_body(server_note))

        approved = copy.deepcopy(preview.payload)
        for relation in approved["relations"]:
            if relation["subject_label"] == "Client" and relation["object_label"] == "Server":
                relation["review_status"] = "verified"
        projection = project_learner_workspace(approved).as_dict()
        client = next(item for item in projection["concepts"] if item["label"] == "Client")
        self.assertIn("**Client** requires **Server**", client["explanation"])


if __name__ == "__main__":
    unittest.main()
