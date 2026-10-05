from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from kgnote.personal_alpha import (
    PersonalAlphaMaterializationError,
    build_learning_workspace_preview,
    materialize_learning_workspace,
    read_back_manual_continuation,
    read_back_learning_workspace,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "personal-alpha" / "hierarchical" / "network-path.md"
ALL_FIXTURES = [
    FIXTURE,
    ROOT / "tests" / "fixtures" / "personal-alpha" / "glossary" / "harmony-glossary.md",
    ROOT / "tests" / "fixtures" / "personal-alpha" / "procedural" / "seed-starting.md",
]


class PersonalAlphaWorkspaceTests(unittest.TestCase):
    def make_source(self, root: Path) -> Path:
        source = root / "selected-learning-source.md"
        shutil.copyfile(FIXTURE, source)
        return source

    def manifest(self, workspace: Path) -> dict:
        return json.loads((workspace / ".kgnote" / "manifest.json").read_text(encoding="utf-8"))

    def test_materialize_reopen_links_source_bytes_and_idempotent_rerun(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.make_source(root)
            destination = root / "vault"
            destination.mkdir()
            preview = build_learning_workspace_preview(source, space="networking")

            first = materialize_learning_workspace(preview, destination)
            workspace = Path(first.workspace_path)
            audit = read_back_learning_workspace(workspace)
            second = materialize_learning_workspace(preview, destination)

            self.assertEqual(first.status, "applied")
            self.assertTrue(first.read_back)
            self.assertGreater(first.created_files, 6)
            self.assertEqual(audit["status"], "loaded")
            self.assertGreater(audit["checked_links"], 12)
            self.assertEqual(audit["record_counts"]["concepts"], len(preview.payload["concepts"]))
            self.assertEqual(
                (workspace / "Source" / source.name).read_bytes(), source.read_bytes()
            )
            entry = (workspace / "Start Here.md").read_text(encoding="utf-8")
            self.assertIn("Learning goal", entry)
            self.assertIn("Learning path", entry)
            self.assertIn("Key concepts", entry)
            self.assertIn("Key relationships", entry)
            self.assertIn("Start reading the original material", entry)
            self.assertTrue((workspace / "My Notes.md").is_file())
            self.assertTrue((workspace / "Continue Here.md").is_file())
            self.assertEqual(second.status, "unchanged")
            self.assertEqual(second.created_files, 0)
            self.assertEqual(second.updated_files, 0)
            self.assertEqual(
                second.unchanged_files,
                len(self.manifest(workspace)["managed_files"]) + 1,
            )
            self.assertFalse(any(destination.glob(".kgnote-transaction-*")))

    def test_all_three_markdown_shapes_materialize_and_reopen_without_source_links_leaking(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            destination = root / "vault"
            destination.mkdir()

            for fixture in ALL_FIXTURES:
                source = root / fixture.name
                shutil.copyfile(fixture, source)
                preview = build_learning_workspace_preview(source)
                result = materialize_learning_workspace(preview, destination)
                audit = read_back_learning_workspace(result.workspace_path)
                self.assertEqual(result.status, "applied")
                self.assertGreater(audit["checked_links"], 0)
                self.assertEqual(
                    Path(result.workspace_path, "Source", source.name).read_bytes(),
                    source.read_bytes(),
                )
                start = Path(result.workspace_path, "Start Here.md").read_text(encoding="utf-8")
                learning_path = start.split("## Learning path", 1)[1].split(
                    "## Key concepts", 1
                )[0]
                self.assertNotIn("[[Evidence|", learning_path)
                self.assertNotIn("[[Structure|", learning_path)
                self.assertNotIn("Important concept candidates", start)
                self.assertNotIn("Source SHA-256", start)
                if fixture.name == "harmony-glossary.md":
                    evidence = Path(result.workspace_path, "Evidence.md").read_text(encoding="utf-8")
                    self.assertIn(r"\[\[Voice leading\]\]", evidence)
                    structure = Path(result.workspace_path, "Structure.md").read_text(encoding="utf-8")
                    self.assertIn("Read the whole immutable source", structure)
                    self.assertNotIn("subsection", structure)
                if fixture.name == "seed-starting.md":
                    self.assertIn("Fill a tray with seed-starting mix.", learning_path)
                    self.assertIn(
                        "Record temperature and germination together", learning_path
                    )

    def test_source_update_preserves_user_notes_and_removes_no_unmanaged_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.make_source(root)
            destination = root / "vault"
            destination.mkdir()
            first_preview = build_learning_workspace_preview(source)
            first = materialize_learning_workspace(first_preview, destination)
            workspace = Path(first.workspace_path)
            notes = workspace / "My Notes.md"
            notes_bytes = b"# My real notes\n\nKeep this observation.\n"
            notes.write_bytes(notes_bytes)
            continuation = workspace / "Continue Here.md"
            continuation_bytes = (
                "# Continue Here\n\n## Current position\n\n"
                "- Resume link: [[Concepts/Port#Related concepts|Resume at my recorded position]]\n"
                "- Current note: Concepts/Port\n"
                "- Current section: Related concepts\n"
                "- Next: Read the source evidence\n"
                "- Question to revisit: Why this endpoint?\n"
            ).encode("utf-8")
            continuation.write_bytes(continuation_bytes)
            attachment_bytes = b'{"nodes": [], "edges": []}\n'
            attachment = workspace / "drawing.canvas"
            attachment.write_bytes(attachment_bytes)

            same_input = materialize_learning_workspace(first_preview, destination)
            self.assertEqual(same_input.status, "unchanged")
            self.assertEqual(notes.read_bytes(), notes_bytes)
            self.assertEqual(continuation.read_bytes(), continuation_bytes)
            self.assertEqual(attachment.read_bytes(), attachment_bytes)
            self.assertEqual(
                read_back_manual_continuation(workspace)["target_kind"], "heading"
            )

            source.write_text(
                source.read_text(encoding="utf-8")
                + "\n## A new supported detail\n\n**Browser** requires **DNS lookup** in this added example.\n",
                encoding="utf-8",
            )
            second_preview = build_learning_workspace_preview(source)
            second = materialize_learning_workspace(second_preview, destination)

            self.assertEqual(second.status, "applied")
            self.assertGreater(second.updated_files, 0)
            self.assertEqual(notes.read_bytes(), notes_bytes)
            self.assertEqual(continuation.read_bytes(), continuation_bytes)
            self.assertEqual(attachment.read_bytes(), attachment_bytes)
            self.assertEqual(
                read_back_learning_workspace(workspace)["source_sha256"],
                second_preview.payload["source"]["content_sha256"],
            )
            concept_ids = self.manifest(workspace)["record_ids"]["concepts"]
            self.assertEqual(len(concept_ids), len(set(concept_ids)))

    def test_manual_continuation_requires_complete_exact_heading_or_block_target(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.make_source(root)
            destination = root / "vault"
            destination.mkdir()
            result = materialize_learning_workspace(
                build_learning_workspace_preview(source), destination
            )
            workspace = Path(result.workspace_path)
            continuation = workspace / "Continue Here.md"

            with self.assertRaises(PersonalAlphaMaterializationError) as empty:
                read_back_manual_continuation(workspace)
            self.assertEqual(empty.exception.code, "continuation_not_recorded")

            continuation.write_text(
                "# Continue Here\n\n## Current position\n\n"
                "- Resume link: [[Concepts/Port#Related concepts|Resume at my recorded position]]\n"
                "- Current note: Concepts/Port\n"
                "- Current section: Related concepts\n"
                "- Next: Read the source evidence\n"
                "- Question to revisit: Why this endpoint?\n",
                encoding="utf-8",
            )
            recorded = read_back_manual_continuation(workspace)
            self.assertEqual(recorded["status"], "recorded")
            self.assertEqual(recorded["section"], "Related concepts")
            self.assertTrue(recorded["target_path"].endswith("Concepts/Port.md"))

            own_note = workspace / "Lab note.md"
            own_note.write_text("# Lab note\n\nResume this paragraph. ^next-check\n", encoding="utf-8")
            continuation.write_text(
                "# Continue Here\n\n## Current position\n\n"
                "- Resume link: [[Lab note#^next-check|Resume at my recorded position]]\n"
                "- Current note: Lab note\n"
                "- Current section: ^next-check\n"
                "- Next: Compare the observation\n"
                "- Question to revisit: Is the result repeatable?\n",
                encoding="utf-8",
            )
            block = read_back_manual_continuation(workspace)
            self.assertEqual(block["target_kind"], "block")
            self.assertTrue(block["target_path"].endswith("Lab note.md"))

            continuation.write_text(
                continuation.read_text(encoding="utf-8").replace(
                    "#^next-check", "#A heading that does not exist"
                ).replace(
                    "- Current section: ^next-check",
                    "- Current section: A heading that does not exist",
                ),
                encoding="utf-8",
            )
            with self.assertRaises(PersonalAlphaMaterializationError) as stale:
                read_back_manual_continuation(workspace)
            self.assertEqual(stale.exception.code, "continuation_anchor_stale")

    def test_evidence_states_heading_jump_and_document_only_line_limit_honestly(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            destination = root / "vault"
            destination.mkdir()
            rendered: dict[str, str] = {}
            for fixture in (FIXTURE, ALL_FIXTURES[1]):
                source = root / fixture.name
                shutil.copyfile(fixture, source)
                result = materialize_learning_workspace(
                    build_learning_workspace_preview(source), destination
                )
                workspace = Path(result.workspace_path)
                rendered[fixture.name] = (workspace / "Evidence.md").read_text(encoding="utf-8")
                self.assertEqual(read_back_learning_workspace(workspace)["status"], "loaded")

            hierarchical = rendered[FIXTURE.name]
            self.assertIn("Open containing section", hierarchical)
            self.assertIn("line range identifies the exact excerpt", hierarchical)
            self.assertNotIn("exact-line jumping", hierarchical)

            heading_free = rendered[ALL_FIXTURES[1].name]
            self.assertIn("Open the source document", heading_free)
            self.assertIn("link opens the document only", heading_free)
            self.assertIn("does not claim exact-line jumping", heading_free)

    def test_new_readable_concept_path_never_overwrites_user_owned_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.make_source(root)
            destination = root / "vault"
            destination.mkdir()
            preview = build_learning_workspace_preview(source)
            first = materialize_learning_workspace(preview, destination)
            workspace = Path(first.workspace_path)
            port = workspace / "Concepts" / "Port.md"
            manifest = self.manifest(workspace)
            row = next(item for item in manifest["managed_files"] if item["path"] == "Concepts/Port.md")
            manifest["managed_files"].remove(row)
            (workspace / ".kgnote" / "manifest.json").write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            port.write_text("# My own Port note\n", encoding="utf-8")

            with self.assertRaises(PersonalAlphaMaterializationError) as caught:
                materialize_learning_workspace(preview, destination)

            self.assertEqual(caught.exception.code, "user_owned_path_collision")
            self.assertEqual(port.read_text(encoding="utf-8"), "# My own Port note\n")

    def test_local_edit_to_generated_file_fails_closed_without_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.make_source(root)
            destination = root / "vault"
            destination.mkdir()
            preview = build_learning_workspace_preview(source)
            result = materialize_learning_workspace(preview, destination)
            workspace = Path(result.workspace_path)
            entry = workspace / "Start Here.md"
            entry.write_text(entry.read_text(encoding="utf-8") + "\nMy direct edit.\n", encoding="utf-8")

            with self.assertRaises(PersonalAlphaMaterializationError) as caught:
                materialize_learning_workspace(preview, destination)

            self.assertEqual(caught.exception.code, "managed_file_conflict")
            self.assertIn("My direct edit.", entry.read_text(encoding="utf-8"))
            self.assertFalse(any(destination.glob(".kgnote-transaction-*")))

    def test_injected_update_failure_rolls_back_to_previous_complete_workspace(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.make_source(root)
            destination = root / "vault"
            destination.mkdir()
            original_preview = build_learning_workspace_preview(source)
            original = materialize_learning_workspace(original_preview, destination)
            workspace = Path(original.workspace_path)
            original_manifest = (workspace / ".kgnote" / "manifest.json").read_bytes()
            original_source = (workspace / "Source" / source.name).read_bytes()

            source.write_text(source.read_text(encoding="utf-8") + "\n**A** requires **B**.\n", encoding="utf-8")
            changed_preview = build_learning_workspace_preview(source)

            def fail_after_backup(point: str) -> None:
                if point == "after_backup":
                    raise OSError("injected failure")

            with self.assertRaises(PersonalAlphaMaterializationError) as caught:
                materialize_learning_workspace(
                    changed_preview, destination, failure_injector=fail_after_backup
                )

            self.assertEqual(caught.exception.code, "materialization_failed_rolled_back")
            self.assertEqual(
                (workspace / ".kgnote" / "manifest.json").read_bytes(), original_manifest
            )
            self.assertEqual((workspace / "Source" / source.name).read_bytes(), original_source)
            self.assertEqual(
                read_back_learning_workspace(workspace)["source_sha256"],
                original_preview.payload["source"]["content_sha256"],
            )
            self.assertFalse(any(destination.glob(".kgnote-transaction-*")))

    def test_injected_new_workspace_failure_leaves_no_partial_target(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.make_source(root)
            destination = root / "vault"
            destination.mkdir()
            preview = build_learning_workspace_preview(source)
            workspace_relative = Path(preview.payload["planned_artifacts"]["workspace_root"])

            def fail_after_commit(point: str) -> None:
                if point == "after_commit":
                    raise OSError("injected failure")

            with self.assertRaises(PersonalAlphaMaterializationError) as caught:
                materialize_learning_workspace(
                    preview, destination, failure_injector=fail_after_commit
                )

            self.assertEqual(caught.exception.code, "materialization_failed_rolled_back")
            self.assertFalse((destination / workspace_relative).exists())
            self.assertFalse(any(destination.glob(".kgnote-transaction-*")))

    def test_changed_source_after_preview_and_corrupt_snapshot_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.make_source(root)
            destination = root / "vault"
            destination.mkdir()
            preview = build_learning_workspace_preview(source)
            source.write_text(source.read_text(encoding="utf-8") + "\nchanged\n", encoding="utf-8")

            with self.assertRaises(PersonalAlphaMaterializationError) as changed:
                materialize_learning_workspace(preview, destination)
            self.assertEqual(changed.exception.code, "source_changed_after_preview")
            self.assertEqual(list(destination.iterdir()), [])

            current = build_learning_workspace_preview(source)
            result = materialize_learning_workspace(current, destination)
            workspace = Path(result.workspace_path)
            snapshot = workspace / "Source" / source.name
            snapshot.write_text("corrupt", encoding="utf-8")
            with self.assertRaises(PersonalAlphaMaterializationError) as corrupt:
                read_back_learning_workspace(workspace)
            self.assertEqual(corrupt.exception.code, "managed_file_conflict")


if __name__ == "__main__":
    unittest.main()
