from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from kgnote.personal_alpha import (
    PERSONAL_ALPHA_PREVIEW_VERSION,
    PersonalAlphaPreviewError,
    build_learning_workspace_preview,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "personal-alpha"


class PersonalAlphaAnalysisTests(unittest.TestCase):
    def fixture(self, category: str, name: str) -> Path:
        return FIXTURES / category / name

    def test_hierarchical_preview_is_deterministic_zero_write_and_source_grounded(self):
        source = self.fixture("hierarchical", "network-path.md")
        before = source.read_bytes()

        first = build_learning_workspace_preview(source, space="networking")
        second = build_learning_workspace_preview(source, space="networking")

        self.assertEqual(first.as_dict(), second.as_dict())
        self.assertEqual(first.markdown, second.markdown)
        self.assertEqual(source.read_bytes(), before)
        self.assertEqual(first.payload["schema_version"], PERSONAL_ALPHA_PREVIEW_VERSION)
        self.assertEqual(first.payload["writes_performed"], 0)
        self.assertEqual(first.payload["external_calls"], 0)
        self.assertEqual(
            first.payload["source"]["content_sha256"], hashlib.sha256(before).hexdigest()
        )

        structure = first.payload["structure"]
        self.assertEqual([node["title"] for node in structure[:3]], [
            "How a browser reaches a local service",
            "Addressing the service",
            "Selecting the process",
        ])
        self.assertEqual(structure[1]["parent_id"], structure[0]["id"])
        self.assertEqual(structure[2]["parent_id"], structure[1]["id"])
        self.assertTrue(all(node["knowledge_edge_created"] is False for node in structure))

        relations = first.payload["relations"]
        relation_types = {item["relation"] for item in relations}
        self.assertIn("requires", relation_types)
        self.assertIn("maps_to", relation_types)
        self.assertIn(None, relation_types)
        self.assertTrue(all(item["review_status"] == "unreviewed" for item in relations))
        self.assertIn("Preview only", first.markdown)
        self.assertIn("Major topics and sections", first.markdown)
        self.assertIn("Important concept candidates", first.markdown)
        self.assertIn("Relationship candidates", first.markdown)
        self.assertIn("Needs review", first.markdown)

    def test_three_materially_different_markdown_shapes_share_one_contract(self):
        paths = [
            self.fixture("hierarchical", "network-path.md"),
            self.fixture("glossary", "harmony-glossary.md"),
            self.fixture("procedural", "seed-starting.md"),
        ]
        previews = [build_learning_workspace_preview(path) for path in paths]

        self.assertEqual({preview.payload["schema_version"] for preview in previews}, {
            PERSONAL_ALPHA_PREVIEW_VERSION
        })
        self.assertEqual(len({preview.payload["source"]["id"] for preview in previews}), 3)
        self.assertGreater(len(previews[0].payload["structure"]), 2)
        self.assertEqual(previews[1].payload["structure"], [])
        self.assertTrue(any(
            item["code"] == "no_heading_structure"
            for item in previews[1].payload["uncertainties"]
        ))
        procedural_names = {
            item["canonical_name_candidate"].casefold()
            for item in previews[2].payload["concepts"]
        }
        self.assertNotIn("fake concept", procedural_names)
        self.assertNotIn("fake result", procedural_names)
        self.assertIn("germination", procedural_names)
        self.assertTrue(all(preview.payload["planned_artifacts"]["entry_note"].endswith(
            "/Start Here.md"
        ) for preview in previews))

    def test_every_concept_and_relation_resolves_to_exact_source_evidence(self):
        source = self.fixture("procedural", "seed-starting.md")
        lines = source.read_text(encoding="utf-8").splitlines()
        preview = build_learning_workspace_preview(source)
        evidence_by_id = {item["id"]: item for item in preview.payload["evidence"]}

        for evidence in evidence_by_id.values():
            locator = evidence["locator"]["value"]
            start_text, end_text = locator.split("-")
            start = int(start_text.removeprefix("L"))
            end = int(end_text.removeprefix("L"))
            self.assertGreaterEqual(start, 1)
            self.assertLessEqual(end, len(lines))
            self.assertEqual(start, end)
            self.assertEqual(evidence["excerpt"], lines[start - 1].strip())
            self.assertEqual(evidence["source_id"], preview.payload["source"]["id"])

        for concept in preview.payload["concepts"]:
            self.assertTrue(concept["evidence_ids"])
            self.assertTrue(all(item in evidence_by_id for item in concept["evidence_ids"]))
            self.assertEqual(concept["identity_status"], "source_scoped_candidate")
        for relation in preview.payload["relations"]:
            self.assertEqual(len(relation["evidence_ids"]), 1)
            self.assertIn(relation["evidence_ids"][0], evidence_by_id)
            if relation["relation"] is None:
                self.assertEqual(relation["edge_class"], "soft_association")
                self.assertEqual(relation["confidence"], "unresolved")

    def test_malformed_sources_fail_with_actionable_codes_and_no_destination(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            empty = root / "empty.md"
            empty.write_text(" \n", encoding="utf-8")
            wrong_extension = root / "lesson.txt"
            wrong_extension.write_text("lesson", encoding="utf-8")

            with self.assertRaises(PersonalAlphaPreviewError) as empty_error:
                build_learning_workspace_preview(empty)
            self.assertEqual(empty_error.exception.code, "source_empty")
            self.assertIn("non-empty", empty_error.exception.action)

            with self.assertRaises(PersonalAlphaPreviewError) as extension_error:
                build_learning_workspace_preview(wrong_extension)
            self.assertEqual(extension_error.exception.code, "source_extension_not_markdown")
            self.assertIn("Markdown", extension_error.exception.action)

            with self.assertRaises(PersonalAlphaPreviewError) as missing_error:
                build_learning_workspace_preview(root / "missing.md")
            self.assertEqual(missing_error.exception.code, "source_not_found")
            self.assertEqual(sorted(path.name for path in root.iterdir()), ["empty.md", "lesson.txt"])


if __name__ == "__main__":
    unittest.main()
