from __future__ import annotations

import hashlib
import io
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from kgnote.obsidian_native import (
    NativeSpikeError,
    augment_native_workspace,
    build_native_canvas,
    validate_markdown_subpath,
    validate_native_workspace,
)
from kgnote.personal_alpha import (
    build_learning_workspace_preview,
    materialize_learning_workspace,
    read_back_learning_workspace,
    read_back_manual_continuation,
)
from scripts.kgnote_obsidian_spike import main as native_main


ROOT = Path(__file__).resolve().parents[1]
HIERARCHICAL = ROOT / "tests" / "fixtures" / "personal-alpha" / "hierarchical" / "network-path.md"
GLOSSARY = ROOT / "tests" / "fixtures" / "personal-alpha" / "glossary" / "harmony-glossary.md"
PROCEDURAL = ROOT / "tests" / "fixtures" / "personal-alpha" / "procedural" / "seed-starting.md"


class ObsidianNativeArtifactTests(unittest.TestCase):
    def preview(self, source: Path, space: str):
        return build_learning_workspace_preview(source, space=space)

    def materialized(self, root: Path, source: Path = HIERARCHICAL, space: str = "networking"):
        preview = self.preview(source, space)
        result = materialize_learning_workspace(preview, root)
        workspace = Path(result.workspace_path)
        augment_native_workspace(preview, workspace)
        return preview, workspace

    def rewrite_canvas(self, workspace: Path, value) -> None:
        canvas = workspace / "Learning Structure.canvas"
        if isinstance(value, str):
            content = value.encode("utf-8")
        else:
            content = (
                json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
            ).encode("utf-8")
        canvas.write_bytes(content)
        manifest_path = workspace / ".kgnote" / "native-manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        row = next(
            item
            for item in manifest["managed_files"]
            if item["path"] == "Learning Structure.canvas"
        )
        row["sha256"] = hashlib.sha256(content).hexdigest()
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )

    def test_hierarchical_canvas_is_deterministic_three_level_and_typed(self):
        preview = self.preview(HIERARCHICAL, "networking")
        first = build_native_canvas(preview.payload)
        second = build_native_canvas(preview.payload)
        self.assertEqual(first, second)
        self.assertEqual(first["source_shape"], "hierarchical")
        canvas = first["canvas"]
        subpaths = {
            node.get("subpath")
            for node in canvas["nodes"]
            if node["type"] == "file" and node.get("subpath")
        }
        self.assertIn("#How a browser reaches a local service", subpaths)
        self.assertIn("#Addressing the service", subpaths)
        self.assertIn("#Selecting the process", subpaths)
        self.assertTrue(
            {"opens_source", "contains_topic", "contains_subtopic"}.issubset(
                set(first["edge_kinds"].values())
            )
        )
        self.assertTrue(all("kgnoteOrganizationKind" not in edge for edge in canvas["edges"]))
        self.assertTrue(all(edge["toEnd"] == "arrow" for edge in canvas["edges"]))

    def test_native_cli_source_key_keeps_vault_identity_across_worktrees(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            outputs: list[str] = []
            workspaces: list[str] = []
            source_ids: list[str] = []
            for name in ("worktree-a", "worktree-b"):
                source = root / name / "tests" / "network-path.md"
                source.parent.mkdir(parents=True)
                shutil.copyfile(HIERARCHICAL, source)
                destination = root / f"{name}-vault"
                destination.mkdir()
                stdout = io.StringIO()
                self.assertEqual(
                    native_main(
                        [
                            str(source),
                            "--vault",
                            str(destination),
                            "--space",
                            "personal-alpha-trial",
                            "--source-key",
                            "kgnote-fixture:personal-alpha/network-path",
                        ],
                        stdout=stdout,
                        stderr=io.StringIO(),
                    ),
                    0,
                )
                outputs.append(stdout.getvalue())
                workspace = next(destination.glob("KGnote Alpha/*"))
                workspaces.append(workspace.name)
                manifest = json.loads(
                    (workspace / ".kgnote" / "manifest.json").read_text(encoding="utf-8")
                )
                self.assertEqual(manifest["source"]["identity_basis"], "stable_external_id")
                source_ids.append(manifest["source"]["id"])

        self.assertEqual(workspaces[0], workspaces[1])
        self.assertEqual(source_ids[0], source_ids[1])
        self.assertNotIn(str(root), "\n".join(workspaces))
        self.assertTrue(all("Read-back: passed" in output for output in outputs))

    def test_heading_free_glossary_stays_flat_without_invented_hierarchy(self):
        model = build_native_canvas(self.preview(GLOSSARY, "music").payload)
        self.assertEqual(model["source_shape"], "heading_free")
        self.assertEqual(
            set(model["edge_kinds"].values()),
            {"opens_source", "concept_reference"},
        )
        self.assertFalse(
            {"contains_topic", "contains_subtopic"}
            & set(model["edge_kinds"].values())
        )
        self.assertTrue(all(node["type"] == "file" for node in model["canvas"]["nodes"]))

    def test_procedural_canvas_expresses_order_without_canonical_causality(self):
        model = build_native_canvas(self.preview(PROCEDURAL, "gardening").payload)
        self.assertEqual(model["source_shape"], "procedural")
        self.assertIn("next_step", set(model["edge_kinds"].values()))
        self.assertNotIn("causes", json.dumps(model, ensure_ascii=False))
        text = "\n".join(
            node["text"] for node in model["canvas"]["nodes"] if node["type"] == "text"
        )
        self.assertIn("Fill a tray with seed-starting mix.", text)
        self.assertIn("Record temperature and germination together", text)

    def test_augmentation_adds_only_discoverability_markdown_and_reruns_byte_identically(self):
        with tempfile.TemporaryDirectory() as directory:
            vault = Path(directory)
            preview = self.preview(HIERARCHICAL, "networking")
            workspace_result = materialize_learning_workspace(preview, vault)
            workspace = Path(workspace_result.workspace_path)
            markdown_before = {
                path.relative_to(workspace).as_posix(): path.read_bytes()
                for path in workspace.rglob("*.md")
            }

            first = augment_native_workspace(preview, workspace)
            canvas_first = Path(first.canvas_path).read_bytes()
            guide_first = Path(first.guide_path).read_bytes()
            second = augment_native_workspace(preview, workspace)

            self.assertEqual(first.status, "applied")
            self.assertEqual(second.status, "unchanged")
            self.assertEqual(Path(second.canvas_path).read_bytes(), canvas_first)
            self.assertEqual(Path(second.guide_path).read_bytes(), guide_first)
            for relative, content in markdown_before.items():
                if relative == "Start Here.md":
                    continue
                self.assertEqual((workspace / relative).read_bytes(), content)
            start = (workspace / "Start Here.md").read_text(encoding="utf-8")
            ordered = (
                "## Learning path",
                "## Key concepts",
                "## Key relationships",
                "## Continue",
                "## My notes",
                "## Optional Canvas",
            )
            offsets = [start.index(value) for value in ordered]
            self.assertEqual(offsets, sorted(offsets))
            self.assertIn("[[Learning Structure.canvas|", start)
            self.assertEqual(
                (workspace / ".obsidian" / "appearance.json").read_text(encoding="utf-8"),
                '{\n  "cssSnippets": ["kgnote-reading"]\n}\n',
            )
            css = (workspace / ".obsidian" / "snippets" / "kgnote-reading.css").read_text(
                encoding="utf-8"
            )
            self.assertIn(".markdown-reading-view .metadata-container", css)
            manifest = json.loads(
                (workspace / ".kgnote" / "native-manifest.json").read_text(encoding="utf-8")
            )
            self.assertEqual(manifest["canonical_digest"], first.canonical_digest)
            self.assertEqual(manifest["markdown_digest"], first.markdown_digest)
            self.assertEqual(manifest["vault_root"], ".")
            audit = validate_native_workspace(preview, workspace)
            self.assertEqual(audit["vault_root"], str(workspace.resolve()))
            self.assertTrue(audit["canvas_discoverable"])
            self.assertTrue(audit["reading_view_configured"])

    def test_documented_native_command_reports_exact_vault_root_and_reruns_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            first_output = io.StringIO()
            first_code = native_main(
                [str(HIERARCHICAL), "--vault", str(parent), "--space", "networking"],
                stdout=first_output,
                stderr=io.StringIO(),
            )
            self.assertEqual(first_code, 0)
            workspace = next(parent.glob("KGnote Alpha/*"))
            self.assertIn(f"Obsidian vault root: {workspace.resolve()}", first_output.getvalue())
            self.assertIn("native Obsidian and human smoke remain pending", first_output.getvalue())

            first_bytes = {
                path.relative_to(workspace).as_posix(): path.read_bytes()
                for path in workspace.rglob("*")
                if path.is_file()
            }
            second_output = io.StringIO()
            second_code = native_main(
                [str(HIERARCHICAL), "--vault", str(parent), "--space", "networking"],
                stdout=second_output,
                stderr=io.StringIO(),
            )
            self.assertEqual(second_code, 0)
            self.assertIn("Markdown status: unchanged", second_output.getvalue())
            self.assertIn("Native status: unchanged", second_output.getvalue())
            self.assertEqual(
                first_bytes,
                {
                    path.relative_to(workspace).as_posix(): path.read_bytes()
                    for path in workspace.rglob("*")
                    if path.is_file()
                },
            )

    def test_semantic_validator_reads_back_all_three_shapes(self):
        with tempfile.TemporaryDirectory() as directory:
            vault = Path(directory)
            for source, space, shape in (
                (HIERARCHICAL, "networking", "hierarchical"),
                (GLOSSARY, "music", "heading_free"),
                (PROCEDURAL, "gardening", "procedural"),
            ):
                preview, workspace = self.materialized(vault, source, space)
                audit = validate_native_workspace(preview, workspace)
                self.assertEqual(audit["status"], "loaded")
                self.assertEqual(audit["source_shape"], shape)
                self.assertGreater(audit["checked_files"], 0)
                if shape == "hierarchical":
                    self.assertGreaterEqual(audit["checked_anchors"], 3)
                if shape == "procedural":
                    self.assertGreater(audit["checked_text_links"], 0)

    def test_integrated_trial_flow_reads_back_and_preserves_all_three_shapes(self):
        """Exercise the documented preparation command as one reopenable product flow."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for fixture, space, shape in (
                (HIERARCHICAL, "networking", "hierarchical"),
                (GLOSSARY, "music", "heading-free"),
                (PROCEDURAL, "gardening", "procedural"),
            ):
                with self.subTest(shape=shape):
                    source = root / shape / fixture.name
                    source.parent.mkdir()
                    shutil.copyfile(fixture, source)
                    parent = root / f"{shape}-candidate"
                    parent.mkdir()

                    output = io.StringIO()
                    self.assertEqual(
                        native_main(
                            [str(source), "--vault", str(parent), "--space", space],
                            stdout=output,
                            stderr=io.StringIO(),
                        ),
                        0,
                    )
                    workspace = next(parent.glob("KGnote Alpha/*"))
                    self.assertIn(
                        f"Obsidian vault root: {workspace.resolve()}", output.getvalue()
                    )

                    start = (workspace / "Start Here.md").read_text(encoding="utf-8")
                    for heading in (
                        "## Learning path",
                        "## Key concepts",
                        "## Key relationships",
                        "## Continue",
                        "## My notes",
                        "## Optional Canvas",
                    ):
                        self.assertIn(heading, start)
                    self.assertIn("[[Continue Here|", start)
                    self.assertIn("[[Learning Structure.canvas|", start)
                    self.assertTrue((workspace / "Relationships.md").is_file())
                    self.assertTrue((workspace / "Evidence.md").is_file())
                    self.assertTrue(any((workspace / "Concepts").glob("*.md")))

                    notes = workspace / "My Notes.md"
                    continuation = workspace / "Continue Here.md"
                    unmanaged = workspace / "Trial observation.md"
                    notes.write_bytes(b"# My notes\n\nA learner-owned trial note.\n")
                    continuation.write_bytes(
                        b"# Continue Here\n\n## Current position\n\n"
                        b"- Resume link: [[Start Here#Learning path|Resume at my recorded position]]\n"
                        b"- Current note: Start Here\n"
                        b"- Current section: Learning path\n"
                        b"- Next: Continue with the first source section.\n"
                        b"- Question to revisit: Which relationship needs source checking?\n"
                    )
                    unmanaged.write_bytes(b"# Trial observation\n\nKeep this byte-for-byte.\n")
                    preserved = {
                        path.name: path.read_bytes()
                        for path in (notes, continuation, unmanaged)
                    }

                    markdown_audit = read_back_learning_workspace(workspace)
                    native_audit = validate_native_workspace(
                        self.preview(source, space), workspace
                    )
                    continuation_audit = read_back_manual_continuation(workspace)
                    self.assertEqual(markdown_audit["status"], "loaded")
                    self.assertEqual(native_audit["source_shape"], shape.replace("-", "_"))
                    self.assertEqual(continuation_audit["status"], "recorded")
                    self.assertEqual(continuation_audit["section"], "Learning path")

                    rerun = io.StringIO()
                    self.assertEqual(
                        native_main(
                            [str(source), "--vault", str(parent), "--space", space],
                            stdout=rerun,
                            stderr=io.StringIO(),
                        ),
                        0,
                    )
                    self.assertIn("Markdown status: unchanged", rerun.getvalue())
                    self.assertIn("Native status: unchanged", rerun.getvalue())

                    source.write_text(
                        source.read_text(encoding="utf-8")
                        + "\n\nA source-supported trial update.\n",
                        encoding="utf-8",
                    )
                    updated = io.StringIO()
                    self.assertEqual(
                        native_main(
                            [str(source), "--vault", str(parent), "--space", space],
                            stdout=updated,
                            stderr=io.StringIO(),
                        ),
                        0,
                    )
                    self.assertIn("Markdown status: applied", updated.getvalue())
                    for path in (notes, continuation, unmanaged):
                        self.assertEqual(path.read_bytes(), preserved[path.name])
                    self.assertEqual(
                        read_back_manual_continuation(workspace)["status"], "recorded"
                    )
                    self.assertEqual(
                        validate_native_workspace(self.preview(source, space), workspace)[
                            "status"
                        ],
                        "loaded",
                    )

    def test_heading_and_block_anchor_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            note = Path(directory) / "note.md"
            note.write_text("# Exact heading\n\nA block line ^block-1\n", encoding="utf-8")
            validate_markdown_subpath(note, "#Exact heading")
            validate_markdown_subpath(note, "#^block-1")
            with self.assertRaises(NativeSpikeError) as invalid:
                validate_markdown_subpath(note, "#^not valid")
            self.assertEqual(invalid.exception.code, "canvas_block_id_invalid")
            with self.assertRaises(NativeSpikeError) as stale:
                validate_markdown_subpath(note, "#Missing heading")
            self.assertEqual(stale.exception.code, "canvas_heading_anchor_stale")

    def test_malformed_dangling_stale_and_duplicate_canvas_fail_closed(self):
        cases = ("malformed", "dangling", "stale", "duplicate")
        for case in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as directory:
                preview, workspace = self.materialized(Path(directory))
                if case == "malformed":
                    self.rewrite_canvas(workspace, "{")
                    expected = "canvas_json_malformed"
                else:
                    canvas = json.loads(
                        (workspace / "Learning Structure.canvas").read_text(encoding="utf-8")
                    )
                    if case == "dangling":
                        canvas["edges"][0]["toNode"] = "node-missing"
                        expected = "canvas_edge_dangling"
                    elif case == "stale":
                        node = next(item for item in canvas["nodes"] if item.get("subpath"))
                        node["subpath"] = "#Missing heading"
                        expected = "canvas_heading_anchor_stale"
                    else:
                        canvas["nodes"][1]["id"] = canvas["nodes"][0]["id"]
                        expected = "canvas_duplicate_node_id"
                    self.rewrite_canvas(workspace, canvas)
                with self.assertRaises(NativeSpikeError) as caught:
                    validate_native_workspace(preview, workspace)
                self.assertEqual(caught.exception.code, expected)

    def test_absolute_traversal_and_symlink_paths_fail_closed(self):
        for unsafe in ("/tmp/outside.md", "../outside.md"):
            with self.subTest(path=unsafe), tempfile.TemporaryDirectory() as directory:
                preview, workspace = self.materialized(Path(directory))
                canvas = json.loads(
                    (workspace / "Learning Structure.canvas").read_text(encoding="utf-8")
                )
                canvas["nodes"][0]["file"] = unsafe
                self.rewrite_canvas(workspace, canvas)
                with self.assertRaises(NativeSpikeError) as caught:
                    validate_native_workspace(preview, workspace)
                self.assertEqual(caught.exception.code, "canvas_path_invalid")

        with tempfile.TemporaryDirectory() as directory:
            preview, workspace = self.materialized(Path(directory))
            outside = Path(directory) / "outside.md"
            outside.write_text("# outside\n", encoding="utf-8")
            os.symlink(outside, workspace / "unsafe-link.md")
            with self.assertRaises(NativeSpikeError) as caught:
                validate_native_workspace(preview, workspace)
            self.assertEqual(caught.exception.code, "workspace_symlink_unsafe")

    def test_native_user_collision_fails_without_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            vault = Path(directory)
            preview = self.preview(HIERARCHICAL, "networking")
            result = materialize_learning_workspace(preview, vault)
            workspace = Path(result.workspace_path)
            collision = workspace / "Learning Structure.canvas"
            collision.write_text("my canvas\n", encoding="utf-8")
            with self.assertRaises(NativeSpikeError) as caught:
                augment_native_workspace(preview, workspace)
            self.assertEqual(caught.exception.code, "native_user_collision")
            self.assertEqual(collision.read_text(encoding="utf-8"), "my canvas\n")

    def test_injected_native_write_failure_rolls_back_and_rerun_recovers(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.md"
            shutil.copyfile(HIERARCHICAL, source)
            preview = self.preview(source, "networking")
            result = materialize_learning_workspace(preview, root)
            workspace = Path(result.workspace_path)
            augment_native_workspace(preview, workspace)
            source.write_text(
                source.read_text(encoding="utf-8")
                + "\n## One more section\n\nA source-supported addition.\n",
                encoding="utf-8",
            )
            updated = self.preview(source, "networking")
            materialize_learning_workspace(updated, root)
            markdown_before = {
                path.relative_to(workspace).as_posix(): path.read_bytes()
                for path in workspace.rglob("*.md")
                if path.name != "Canvas Guide.md"
            }

            def fail_after_backup(point: str) -> None:
                if point == "after_backup":
                    raise OSError("injected native failure")

            with self.assertRaises(NativeSpikeError) as caught:
                augment_native_workspace(
                    updated, workspace, failure_injector=fail_after_backup
                )
            self.assertEqual(
                caught.exception.code, "native_augmentation_failed_rolled_back"
            )
            for relative, content in markdown_before.items():
                self.assertEqual((workspace / relative).read_bytes(), content)
            applied = augment_native_workspace(updated, workspace)
            self.assertEqual(applied.status, "applied")
            self.assertEqual(
                validate_native_workspace(updated, workspace)["status"], "loaded"
            )

    def test_recovery_keeps_complete_committed_target_when_backup_coexists(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            preview, workspace = self.materialized(root)
            transaction = workspace.parent / f".kgnote-native-transaction-{str(preview.payload['source']['id'])[-16:]}"
            transaction.mkdir()
            shutil.copytree(workspace, transaction / "backup")
            marker = workspace / "committed-after-crash.txt"
            marker.write_text("new committed target\n", encoding="utf-8")
            result = augment_native_workspace(preview, workspace)
            self.assertTrue(result.recovered_interrupted_transaction)
            self.assertEqual("new committed target\n", marker.read_text(encoding="utf-8"))
            self.assertFalse(transaction.exists())

    def test_ambiguous_recovery_preserves_both_target_and_backup(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            preview, workspace = self.materialized(root)
            transaction = workspace.parent / f".kgnote-native-transaction-{str(preview.payload['source']['id'])[-16:]}"
            transaction.mkdir()
            shutil.copytree(workspace, transaction / "backup")
            (workspace / "Learning Structure.canvas").write_text("corrupt", encoding="utf-8")
            with self.assertRaises(NativeSpikeError) as caught:
                augment_native_workspace(preview, workspace)
            self.assertEqual("native_recovery_ambiguous", caught.exception.code)
            self.assertTrue(workspace.exists())
            self.assertTrue((transaction / "backup").exists())


if __name__ == "__main__":
    unittest.main()
