from __future__ import annotations

import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from kgnote.personal_alpha import read_back_learning_workspace
from scripts.kgnote_alpha import main


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "personal-alpha" / "procedural" / "seed-starting.md"
ALL_FIXTURES = [
    ROOT / "tests" / "fixtures" / "personal-alpha" / "hierarchical" / "network-path.md",
    ROOT / "tests" / "fixtures" / "personal-alpha" / "glossary" / "harmony-glossary.md",
    FIXTURE,
]


class PersonalAlphaCliTests(unittest.TestCase):
    def prepare(self, root: Path) -> tuple[Path, Path]:
        source = root / "my-learning-source.md"
        shutil.copyfile(FIXTURE, source)
        vault = root / "My Obsidian Vault"
        vault.mkdir()
        return source, vault

    def test_one_command_materializes_reports_entry_and_reruns_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            source, vault = self.prepare(Path(directory))
            first_output = io.StringIO()
            first_error = io.StringIO()

            first_code = main(
                [str(source), "--vault", str(vault), "--space", "gardening"],
                stdout=first_output,
                stderr=first_error,
            )

            self.assertEqual(first_code, 0)
            self.assertEqual(first_error.getvalue(), "")
            self.assertIn("Preview only — no files were written", first_output.getvalue())
            self.assertIn("Status: applied", first_output.getvalue())
            self.assertIn("Read-back: passed", first_output.getvalue())
            self.assertIn("Next: Open `", first_output.getvalue())
            entry_notes = list(vault.glob("KGnote Alpha/*/Start Here.md"))
            self.assertEqual(len(entry_notes), 1)

            second_output = io.StringIO()
            second_code = main(
                [str(source), "--vault", str(vault), "--space", "gardening"],
                stdout=second_output,
                stderr=io.StringIO(),
            )
            self.assertEqual(second_code, 0)
            self.assertIn("Status: unchanged", second_output.getvalue())
            self.assertEqual(len(list(vault.glob("KGnote Alpha/*/Start Here.md"))), 1)

    def test_preview_only_writes_nothing_to_destination(self):
        with tempfile.TemporaryDirectory() as directory:
            source, vault = self.prepare(Path(directory))
            output = io.StringIO()

            code = main(
                [str(source), "--vault", str(vault), "--preview-only"],
                stdout=output,
                stderr=io.StringIO(),
            )

            self.assertEqual(code, 0)
            self.assertIn("Preview complete: zero files written", output.getvalue())
            self.assertEqual(list(vault.iterdir()), [])

    def test_same_daily_command_handles_three_distinct_sources_and_reopens_cleanly(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            vault = root / "vault"
            vault.mkdir()
            seen_workspaces: set[Path] = set()

            for fixture in ALL_FIXTURES:
                source_dir = root / fixture.parent.name
                source_dir.mkdir()
                source = source_dir / fixture.name
                shutil.copyfile(fixture, source)
                before = set(vault.glob("KGnote Alpha/*"))
                first_output = io.StringIO()

                first_code = main(
                    [str(source), "--vault", str(vault), "--space", "candidate"],
                    stdout=first_output,
                    stderr=io.StringIO(),
                )

                self.assertEqual(first_code, 0)
                self.assertIn("Status: applied", first_output.getvalue())
                self.assertIn("Read-back: passed", first_output.getvalue())
                created = set(vault.glob("KGnote Alpha/*")) - before
                self.assertEqual(len(created), 1)
                workspace = created.pop()
                seen_workspaces.add(workspace)

                audit = read_back_learning_workspace(workspace)
                manifest = json.loads(
                    (workspace / ".kgnote" / "manifest.json").read_text(encoding="utf-8")
                )
                self.assertEqual(audit["status"], "loaded")
                self.assertEqual((workspace / "Source" / source.name).read_bytes(), source.read_bytes())
                for record_type in ("concepts", "relations", "evidence"):
                    record_ids = manifest["record_ids"][record_type]
                    self.assertEqual(len(record_ids), len(set(record_ids)))

                rerun_output = io.StringIO()
                rerun_code = main(
                    [str(source), "--vault", str(vault), "--space", "candidate"],
                    stdout=rerun_output,
                    stderr=io.StringIO(),
                )
                self.assertEqual(rerun_code, 0)
                self.assertIn("Status: unchanged", rerun_output.getvalue())

            self.assertEqual(len(seen_workspaces), 3)
            self.assertEqual(len(list(vault.glob("KGnote Alpha/*"))), 3)

    def test_input_and_managed_file_errors_are_actionable_without_traceback(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            vault = root / "vault"
            vault.mkdir()
            missing_error = io.StringIO()

            missing_code = main(
                [str(root / "missing.md"), "--vault", str(vault)],
                stdout=io.StringIO(),
                stderr=missing_error,
            )

            self.assertEqual(missing_code, 2)
            self.assertIn("[source_not_found]", missing_error.getvalue())
            self.assertIn("Next:", missing_error.getvalue())
            self.assertNotIn("Traceback", missing_error.getvalue())

            source, another_vault = self.prepare(root)
            self.assertEqual(
                main([str(source), "--vault", str(another_vault)], stdout=io.StringIO(), stderr=io.StringIO()),
                0,
            )
            entry = next(another_vault.glob("KGnote Alpha/*/Start Here.md"))
            entry.write_text(entry.read_text(encoding="utf-8") + "\nmanual edit\n", encoding="utf-8")
            conflict_error = io.StringIO()
            conflict_code = main(
                [str(source), "--vault", str(another_vault)],
                stdout=io.StringIO(),
                stderr=conflict_error,
            )
            self.assertEqual(conflict_code, 3)
            self.assertIn("[managed_file_conflict]", conflict_error.getvalue())
            self.assertIn("My Notes.md", conflict_error.getvalue())
            self.assertNotIn("Traceback", conflict_error.getvalue())


if __name__ == "__main__":
    unittest.main()
