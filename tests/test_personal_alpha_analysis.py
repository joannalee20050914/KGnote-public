from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from kgnote.personal_alpha import (
    PERSONAL_ALPHA_PREVIEW_VERSION,
    PersonalAlphaPreviewError,
    build_learning_workspace_preview,
    materialize_learning_workspace,
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
        self.assertEqual(relation_types, {None})
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

    def test_explicit_source_key_is_portable_across_machine_paths(self):
        with tempfile.TemporaryDirectory() as first_dir, tempfile.TemporaryDirectory() as second_dir:
            first = Path(first_dir) / "network-path.md"
            second = Path(second_dir) / "network-path.md"
            content = self.fixture("hierarchical", "network-path.md").read_bytes()
            first.write_bytes(content)
            second.write_bytes(content)

            path_bound_first = build_learning_workspace_preview(first)
            path_bound_second = build_learning_workspace_preview(second)
            portable_first = build_learning_workspace_preview(
                first, source_key="kgnote-fixture:personal-alpha/network-path"
            )
            portable_second = build_learning_workspace_preview(
                second, source_key="kgnote-fixture:personal-alpha/network-path"
            )

        self.assertNotEqual(
            path_bound_first.payload["source"]["id"], path_bound_second.payload["source"]["id"]
        )
        self.assertEqual(portable_first.payload["source"]["id"], portable_second.payload["source"]["id"])
        self.assertEqual(
            portable_first.payload["planned_artifacts"]["workspace_root"],
            portable_second.payload["planned_artifacts"]["workspace_root"],
        )
        self.assertEqual(portable_first.payload["source"]["identity_basis"], "stable_external_id")

    def test_source_key_rejects_file_paths_and_unscoped_values(self):
        source = self.fixture("hierarchical", "network-path.md")
        for invalid in ("network-path", "/absolute/source.md", "file:source.md"):
            with self.subTest(source_key=invalid), self.assertRaises(PersonalAlphaPreviewError) as error:
                build_learning_workspace_preview(source, source_key=invalid)
            self.assertEqual(error.exception.code, "source_key_invalid")

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

    def test_negated_or_modal_relation_phrase_is_not_promoted(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "adversarial.md"
            source.write_text(
                "# Adversarial\n\n**Client** no longer requires **Server**.\n\n"
                "**Cache** might depend on **Database**.\n",
                encoding="utf-8",
            )
            preview = build_learning_workspace_preview(source)
        relations = preview.payload["relations"]
        self.assertTrue(relations)
        self.assertTrue(all(item["relation"] is None for item in relations))
        self.assertTrue(all(item["edge_class"] == "soft_association" for item in relations))

    def test_multilingual_qualified_relations_fail_closed(self):
        cases = (
            "**Client** 不會需要 **Server**。",
            "**Client** 並非依賴 **Server**。",
            "**Client** 未依賴 **Server**。",
            "**Client** 通常需要 **Server**。",
            "**Client** rarely requires **Server**.",
            "**Client** usually requires **Server**.",
            "**Client** hardly ever requires **Server**.",
            "**Client** requires **Server** only if enabled.",
            "Unless enabled, **Client** requires **Server**.",
            "When recovery mode is enabled, **Client** requires **Server**.",
            "**Client** requires **Server** during recovery.",
            "**Client** does not require **Server**.",
            "**Client** may require **Server**.",
        )
        with tempfile.TemporaryDirectory() as directory:
            for index, statement in enumerate(cases):
                source = Path(directory) / f"case-{index}.md"
                source.write_text(f"# Case\n\n{statement}\n", encoding="utf-8")
                preview = build_learning_workspace_preview(source)
                self.assertTrue(all(row["relation"] is None for row in preview.payload["relations"]), statement)

    def test_multilingual_interrogative_relations_fail_closed(self):
        cases = (
            "**Client** requires **Server**?",
            "**Client** requires **Server**？",
            "- **Client** requires **Server**?",
            "1. **Client** requires **Server**？",
            "Does **Client** require **Server**?",
            "Question: **Client** requires **Server**?",
            "**客戶端**需要**伺服器**？",
            "問題：**客戶端**需要**伺服器**？",
            "## Question\n\n- **Client** requires **Server**.",
            "Question:\n\n- **Client** requires **Server**.",
            "## 問題\n\n- **客戶端**需要**伺服器**。",
            "這是否成立？\n\n- **Client** requires **Server**.",
            "## Questions\n\n- **Client** requires **Server**.\n- **Cache** requires **Database**.",
            "## 問題\n\n1. **客戶端**需要**伺服器**。\n\n2. **快取**需要**資料庫**。",
            "Question:\n\n- **Client** requires **Server**.\n  - **Cache** requires **Database**.",
            "以下是否成立？\n\n- **客戶端**需要**伺服器**。\n- **快取**需要**資料庫**。",
        )
        with tempfile.TemporaryDirectory() as directory:
            for index, statement in enumerate(cases):
                source = Path(directory) / f"question-{index}.md"
                source.write_text(f"# Case\n\n{statement}\n", encoding="utf-8")
                preview = build_learning_workspace_preview(source)
                self.assertTrue(preview.payload["relations"], statement)
                self.assertTrue(
                    all(row["relation"] is None for row in preview.payload["relations"]),
                    statement,
                )
                self.assertTrue(
                    all(row["edge_class"] == "soft_association" for row in preview.payload["relations"]),
                    statement,
                )

    def test_only_complete_unqualified_assertions_create_typed_relations(self):
        cases = (
            ("**Client** requires **Server**.", "requires"),
            ("- **Port** maps to **Service**。", "maps_to"),
            ("**種子**需要**水分**。", "requires"),
            ("**TCP** is part of **Protocol suite**!", "part_of"),
        )
        with tempfile.TemporaryDirectory() as directory:
            for index, (statement, expected) in enumerate(cases):
                source = Path(directory) / f"assertion-{index}.md"
                source.write_text(f"# Case\n\n{statement}\n", encoding="utf-8")
                preview = build_learning_workspace_preview(source)
                typed = [row["relation"] for row in preview.payload["relations"]]
                self.assertEqual(typed, [expected], statement)

    def test_new_markdown_boundary_ends_question_scope(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "question-then-answer.md"
            source.write_text(
                "# Case\n\n## Questions\n\n- **Client** requires **Server**.\n\n"
                "## Answer\n\n- **Cache** requires **Database**.\n",
                encoding="utf-8",
            )
            preview = build_learning_workspace_preview(source)
        relations = [row["relation"] for row in preview.payload["relations"]]
        self.assertEqual(relations, [None, "requires"])

    def test_qualified_relations_never_leak_into_materialized_learner_notes(self):
        statements = (
            "**Client** usually requires **Server**.",
            "When recovery mode is enabled, **Client** requires **Server**.",
            "**Client** 未依賴 **Server**。",
            "**Client** requires **Server**?",
            "- **Client** requires **Server**？",
            "Question: **Client** requires **Server**?",
            "問題：**客戶端**需要**伺服器**？",
            "## Question\n\n- **Client** requires **Server**.",
            "Question:\n\n- **Client** requires **Server**.",
            "## 問題\n\n- **客戶端**需要**伺服器**。",
            "## Questions\n\n- **Client** requires **Server**.\n- **Cache** requires **Database**.",
            "## 問題\n\n1. **客戶端**需要**伺服器**。\n\n2. **快取**需要**資料庫**。",
            "Question:\n\n- **Client** requires **Server**.\n  - **Cache** requires **Database**.",
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for index, statement in enumerate(statements):
                source = root / f"materialized-{index}.md"
                source.write_text(f"# Case\n\n{statement}\n", encoding="utf-8")
                vault = root / f"vault-{index}"
                vault.mkdir()
                preview = build_learning_workspace_preview(source)
                result = materialize_learning_workspace(preview, vault)
                workspace = Path(result.workspace_path)
                learner_files = [workspace / "Relationships.md", *sorted((workspace / "Concepts").glob("*.md"))]
                rendered = "\n".join(path.read_text(encoding="utf-8") for path in learner_files)
                self.assertNotIn("**requires**", rendered, statement)
                self.assertNotIn("**is required by**", rendered, statement)
                self.assertIn("leaves this unresolved", rendered, statement)


if __name__ == "__main__":
    unittest.main()
