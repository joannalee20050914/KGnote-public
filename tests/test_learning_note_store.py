from __future__ import annotations

import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest import mock

from kgnote.notes import read_note, save_note, search_notes


def request(*, save_id: str = "save_12345678", markdown: str = "## 解釋\n\nCorrelation 不等於 causation。\n", notebook: str = "notebook_local") -> dict:
    return {
        "schema_version": "kgnote.learning-note-save.v1",
        "note_id": "note_causality",
        "notebook_id": notebook,
        "learning_unit_id": "unit_causality",
        "title": "Correlation 與 causation",
        "source_anchors": [{
            "id": "anchor_primary", "source_id": "src_synthetic_causality_chat",
            "locator": {"kind": "line_range", "value": "L3-L7"}, "label": "原始因果對話",
        }],
        "markdown": markdown,
        "save_id": save_id,
    }


class LearningNoteStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_create_reopen_update_and_response_loss_retry(self) -> None:
        first_request = request()
        first = save_note(self.root, first_request, if_match="*", saved_at="2026-09-19T10:00:00+08:00")
        retry = save_note(self.root, first_request, if_match="*", saved_at="2026-09-19T10:01:00+08:00")
        self.assertEqual((first.status, retry.status), ("saved", "unchanged"))
        self.assertEqual(first.payload["note"]["revision"], 1)
        self.assertEqual(retry.payload["etag"], first.payload["etag"])
        reopened = read_note(self.root, "note_causality")
        self.assertEqual(reopened.status, "ready")
        self.assertEqual(reopened.payload["note"]["markdown"], first_request["markdown"])

        second_request = request(save_id="save_87654321", markdown="## 解釋\n\n第三變數可能同時影響兩者。\n")
        second = save_note(self.root, second_request, if_match=reopened.payload["etag"], saved_at="2026-09-19T11:00:00+08:00")
        self.assertEqual(second.status, "saved")
        self.assertEqual(second.payload["note"]["revision"], 2)
        self.assertNotEqual(second.payload["etag"], first.payload["etag"])

    def test_stale_etag_and_reused_save_id_never_overwrite(self) -> None:
        initial = save_note(self.root, request(), if_match="*", saved_at="2026-09-19T10:00:00Z")
        changed = request(markdown="## 不同內容\n", save_id="save_12345678")
        reused = save_note(self.root, changed, if_match=initial.payload["etag"], saved_at="2026-09-19T10:01:00Z")
        self.assertEqual((reused.status, reused.problem_code), ("conflict", "save_id_reused"))
        stale = save_note(self.root, request(save_id="save_99999999"), if_match='"' + "0" * 64 + '"')
        self.assertEqual((stale.status, stale.problem_code), ("conflict", "stale_note"))
        self.assertEqual(read_note(self.root, "note_causality").payload["note"]["revision"], 1)

    def test_concurrent_writers_with_one_etag_produce_one_save_and_one_conflict(self) -> None:
        initial = save_note(self.root, request(), if_match="*", saved_at="2026-09-19T10:00:00Z")
        commands = [
            request(save_id="save_parallel1", markdown="## writer one\n"),
            request(save_id="save_parallel2", markdown="## writer two\n"),
        ]
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(
                lambda command: save_note(
                    self.root, command, if_match=initial.payload["etag"], saved_at="2026-09-19T11:00:00Z",
                ),
                commands,
            ))
        self.assertEqual(sorted(result.status for result in results), ["conflict", "saved"])
        self.assertEqual(read_note(self.root, "note_causality").payload["note"]["revision"], 2)

    def test_atomic_replace_failure_preserves_previous_bytes(self) -> None:
        initial = save_note(self.root, request(), if_match="*", saved_at="2026-09-19T10:00:00Z")
        path = self.root / "notes" / "note_causality.md"
        before = path.read_bytes()
        with mock.patch("kgnote.notes.store.os.replace", side_effect=OSError("disk failure")):
            failed = save_note(
                self.root, request(save_id="save_failure01", markdown="## should not appear\n"),
                if_match=initial.payload["etag"], saved_at="2026-09-19T11:00:00Z",
            )
        self.assertEqual((failed.status, failed.problem_code), ("failed", "note_write_failed"))
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(list((self.root / "notes").glob("*.tmp")), [])

    def test_notebook_scoped_literal_search_returns_heading_and_source(self) -> None:
        saved = save_note(self.root, request(), if_match="*", saved_at="2026-09-19T10:00:00Z")
        self.assertEqual(saved.status, "saved")
        hits = search_notes(self.root, "notebook_local", "causation")
        self.assertEqual(hits.status, "ready")
        self.assertGreaterEqual(len(hits.payload["results"]), 1)
        self.assertEqual(hits.payload["results"][0]["note_id"], "note_causality")
        self.assertTrue(hits.payload["results"][0]["source_anchors"])
        self.assertEqual(search_notes(self.root, "another_notebook", "causation").payload["results"], [])

    def test_malicious_markdown_and_unsafe_directory_fail_closed(self) -> None:
        bad = request(markdown="<img src=https://tracker.test/x>")
        self.assertEqual(save_note(self.root, bad, if_match="*").problem_code, "raw_html_not_allowed")
        (self.root / "elsewhere").mkdir()
        (self.root / "notes").symlink_to(self.root / "elsewhere", target_is_directory=True)
        self.assertEqual(save_note(self.root, request(), if_match="*").problem_code, "unsafe_notes_directory")


if __name__ == "__main__":
    unittest.main()
