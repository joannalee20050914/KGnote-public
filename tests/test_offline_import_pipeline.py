import hashlib
import os
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from kgnote.ingestion import SourceMetadata
from kgnote.pipeline import apply_offline_import, build_offline_import_preview


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PHASE0 = PROJECT_ROOT / "fixtures/phase0-obsidian"
SOURCE = PHASE0 / "raw/synthetic-causality-chat.md"
RESPONSE = PROJECT_ROOT / "tests/fixtures/extraction/v1/valid/raw_response.json"
DIRECTORIES = ("sources", "concepts", "evidence", "learning-events", "edges", "raw")
GENERATED_AT = "2026-09-07T00:00:00+08:00"


def tree_digest(root):
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        digest.update(str(path.relative_to(root)).encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


class OfflineImportPipelineTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.metadata = SourceMetadata(
            source_id="src_synthetic_causality_chat",
            source_kind="chatgpt_conversation",
            title="Synthetic causality learning conversation",
            captured_at=None,
            locator_basis="line_range",
        )

    def make_store(self, root):
        root = Path(root)
        for directory in DIRECTORIES:
            (root / directory).mkdir()
        return root

    def preview(self, root):
        return build_offline_import_preview(
            source_path=SOURCE, response_path=RESPONSE, metadata=self.metadata,
            extractor_version="fixture-replay.v1", generated_at=GENERATED_AT,
            store_root=root,
        )

    def test_full_offline_apply_read_back_second_run_and_obsidian_links(self):
        phase0_before = tree_digest(PHASE0)
        with tempfile.TemporaryDirectory() as temporary, mock.patch(
            "socket.create_connection", side_effect=AssertionError("network forbidden")
        ), mock.patch.dict(os.environ, {}, clear=True):
            root = self.make_store(temporary)
            first_preview = self.preview(root)
            self.assertEqual(first_preview.status, "planned")
            self.assertEqual({item["operation"] for item in first_preview.plan.items}, {"CREATE"})
            self.assertEqual(len(first_preview.plan.items), 11)
            self.assertNotIn(SOURCE.read_text(), repr(first_preview))

            first = apply_offline_import(
                first_preview, approved_digest=first_preview.approval_digest
            )
            self.assertEqual(first.status, "applied")
            self.assertEqual(first.raw_write_count, 1)
            self.assertEqual(first.write_count, 12)
            self.assertEqual(len(first.audit_snapshot.records), 11)
            raw_copy = root / first_preview.raw_relative_path
            self.assertEqual(raw_copy.read_bytes(), SOURCE.read_bytes())

            second_preview = self.preview(root)
            self.assertEqual(second_preview.status, "planned")
            self.assertEqual({item["operation"] for item in second_preview.plan.items}, {"UNCHANGED"})
            before_second = tree_digest(root)
            second = apply_offline_import(
                second_preview, approved_digest=second_preview.approval_digest
            )
            self.assertEqual(second.status, "applied")
            self.assertEqual(second.write_count, 0)
            self.assertEqual(second.raw_write_count, 0)
            self.assertEqual(tree_digest(root), before_second)

            markdown_files = [path for path in root.rglob("*.md") if ".obsidian" not in path.parts]
            known_links = {
                path.relative_to(root).with_suffix("").as_posix() for path in markdown_files
            } | {path.stem for path in markdown_files}
            stems = [path.stem for path in markdown_files]
            self.assertEqual(len(stems), len(set(stems)))
            links = []
            for path in markdown_files:
                links.extend(re.findall(r"\[\[([^]|]+)", path.read_text(encoding="utf-8")))
            self.assertTrue(links)
            self.assertEqual(sorted(link for link in links if link not in known_links), [])
            self.assertFalse((root / ".obsidian").exists())
        self.assertEqual(tree_digest(PHASE0), phase0_before)

    def test_approval_and_raw_conflict_fail_before_canonical_writes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = self.make_store(temporary)
            preview = self.preview(root)
            denied = apply_offline_import(preview, approved_digest=None)
            self.assertEqual(denied.problem_code, "approval_required")
            self.assertEqual(list((root / "sources").iterdir()), [])
            self.assertEqual(list((root / "raw").iterdir()), [])

            (root / preview.raw_relative_path).write_text("different", encoding="utf-8")
            conflict = self.preview(root)
            self.assertEqual(conflict.status, "rejected")
            self.assertEqual(conflict.problem_code, "raw_source_conflict")
            self.assertEqual(list((root / "sources").iterdir()), [])


if __name__ == "__main__":
    unittest.main()
