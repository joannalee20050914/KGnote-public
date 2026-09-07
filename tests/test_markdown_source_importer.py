import hashlib
import json
import socket
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from kgnote.contracts.extraction import (
    ExtractionInputValidationError,
    validate_extraction_input,
)
from kgnote.ingestion.markdown_source import (
    MarkdownSourceImportError,
    SourceMetadata,
    build_extraction_input,
    import_markdown_source,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PHASE0_VAULT = PROJECT_ROOT / "fixtures" / "phase0-obsidian"
PHASE0_SOURCE = PHASE0_VAULT / "raw" / "synthetic-causality-chat.md"


def default_metadata(**overrides):
    values = {
        "source_id": "src_synthetic_causality_chat",
        "source_kind": "chatgpt_conversation",
        "title": "Synthetic causality learning conversation",
        "captured_at": None,
        "locator_basis": "line_range",
    }
    values.update(overrides)
    return SourceMetadata(**values)


def tree_digest(root):
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        digest.update(str(path.relative_to(root)).encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


class MarkdownSourceImporterTest(unittest.TestCase):
    def test_phase0_source_imports_exact_bytes_hash_and_schema(self):
        source_bytes = PHASE0_SOURCE.read_bytes()
        payload = import_markdown_source(PHASE0_SOURCE, metadata=default_metadata())

        validate_extraction_input(payload)
        self.assertEqual(payload["source"]["content"].encode("utf-8"), source_bytes)
        self.assertEqual(
            payload["source"]["content_sha256"],
            hashlib.sha256(source_bytes).hexdigest(),
        )

    def test_repeated_import_is_deterministic(self):
        first = import_markdown_source(PHASE0_SOURCE, metadata=default_metadata())
        second = import_markdown_source(PHASE0_SOURCE, metadata=default_metadata())
        self.assertEqual(first, second)

    def test_import_reads_only_explicit_file_without_network_or_vault_writes(self):
        before = tree_digest(PHASE0_VAULT)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            selected = root / "selected.md"
            sibling = root / "private-sibling.md"
            selected.write_text("# Selected\n\nAllowed content.\n", encoding="utf-8")
            sibling.write_text("PRIVATE_SIBLING_MARKER", encoding="utf-8")

            with mock.patch.object(
                socket,
                "socket",
                side_effect=AssertionError("network access attempted"),
            ):
                payload = import_markdown_source(selected, metadata=default_metadata())

            self.assertEqual(payload["source"]["content"], selected.read_text())
            self.assertNotIn("PRIVATE_SIBLING_MARKER", json.dumps(payload))
        self.assertEqual(tree_digest(PHASE0_VAULT), before)

    def test_malformed_front_matter_is_preserved_as_raw_evidence(self):
        content = "---\ntitle: [broken\n---\n\n# Still immutable evidence\n"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "malformed-frontmatter.md"
            path.write_text(content, encoding="utf-8")
            payload = import_markdown_source(path, metadata=default_metadata())

        self.assertEqual(payload["source"]["content"], content)

    def test_path_failures_have_stable_categories(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cases = []

            missing = root / "missing.md"
            cases.append(("path_not_found", missing))
            cases.append(("not_regular_file", root))

            non_markdown = root / "source.txt"
            non_markdown.write_text("content", encoding="utf-8")
            cases.append(("unsupported_extension", non_markdown))

            invalid_utf8 = root / "invalid.md"
            invalid_utf8.write_bytes(b"private-prefix-\xff-private-suffix")
            cases.append(("invalid_utf8", invalid_utf8))

            empty = root / "empty.md"
            empty.write_text(" \n\t", encoding="utf-8")
            cases.append(("empty_content", empty))

            for expected_code, path in cases:
                with self.subTest(code=expected_code):
                    with self.assertRaises(MarkdownSourceImportError) as raised:
                        import_markdown_source(path, metadata=default_metadata())
                    self.assertEqual(raised.exception.code, expected_code)
                    self.assertNotIn("private-prefix", str(raised.exception))
                    self.assertNotIn("private-suffix", str(raised.exception))

    def test_invalid_metadata_has_safe_stable_category_and_path(self):
        cases = [
            ("invalid_source_id", ("source", "id"), {"source_id": "bad-id"}),
            (
                "invalid_source_kind",
                ("source", "source_kind"),
                {"source_kind": "brain_scan"},
            ),
            ("invalid_title", ("source", "title"), {"title": "   "}),
            (
                "invalid_captured_at",
                ("source", "captured_at"),
                {"captured_at": "yesterday"},
            ),
            (
                "invalid_locator_basis",
                ("source", "locator_basis"),
                {"locator_basis": "paragraph_guess"},
            ),
        ]

        for expected_code, expected_path, overrides in cases:
            with self.subTest(code=expected_code):
                with self.assertRaises(MarkdownSourceImportError) as raised:
                    build_extraction_input(
                        content="PRIVATE_SOURCE_MARKER",
                        metadata=default_metadata(**overrides),
                    )
                self.assertEqual(raised.exception.code, expected_code)
                self.assertEqual(raised.exception.field_path, expected_path)
                self.assertNotIn("PRIVATE_SOURCE_MARKER", str(raised.exception))

    def test_read_failure_has_stable_safe_category(self):
        with mock.patch.object(Path, "read_bytes", side_effect=PermissionError):
            with self.assertRaises(MarkdownSourceImportError) as raised:
                import_markdown_source(PHASE0_SOURCE, metadata=default_metadata())

        self.assertEqual(raised.exception.code, "read_failed")
        self.assertNotIn("Synthetic causality", str(raised.exception))

    def test_direct_contract_failure_reports_stable_category_and_path(self):
        with self.assertRaises(ExtractionInputValidationError) as raised:
            validate_extraction_input({"schema_version": "kgnote.extraction-input.v1"})

        self.assertEqual(raised.exception.code, "invalid_extraction_input")
        self.assertEqual(raised.exception.path, ())
        self.assertEqual(raised.exception.validator, "required")


if __name__ == "__main__":
    unittest.main()
